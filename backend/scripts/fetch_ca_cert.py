"""Fetch the corporate CA certificate from Active Directory into a PEM bundle.

The application authenticates users with an LDAPS *simple* bind, which puts the
password on the wire, so `ldap_client._build_server_pool` refuses to connect unless
it can validate the domain controller certificate against a CA bundle. This script
produces that bundle.

Active Directory Certificate Services publishes its own CA certificates inside the
directory, under `CN=AIA,CN=Public Key Services,CN=Services,CN=Configuration`. The
domain controller certificate points there through its Authority Information Access
extension, so the bundle can be built from the directory itself rather than obtained
out of band.

The read is done over LDAPS with certificate validation *disabled*, because the bundle
needed to validate the connection is the thing being fetched. That is the one
compromise here and it is confined to this script: the application path keeps
`ssl.CERT_REQUIRED`. See `_connect` for what it does and does not protect.

Run again when the CA renews; both the old and the new certificate end up in the
bundle, so sign-in keeps working across the rollover.

    python scripts/fetch_ca_cert.py
    python scripts/fetch_ca_cert.py --user CORP\\jsmith
"""

from __future__ import annotations

import argparse
import hashlib
import ssl
import sys
from base64 import b64encode
from getpass import getpass
from pathlib import Path

from ldap3 import LEVEL, SIMPLE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException

from app.core.config import get_settings

settings = get_settings()

AIA_CONTAINER = "CN=AIA,CN=Public Key Services,CN=Services,CN=Configuration"
CA_FILTER = "(objectClass=certificationAuthority)"
DEFAULT_OUTPUT = Path("certs/corp-ca.pem")


class FetchError(Exception):
    """Raised with a message intended for the operator."""


def aia_dn() -> str:
    base_dn = settings.ldap_base_dn.strip()
    if not base_dn:
        raise FetchError("LDAP_BASE_DN is not set; cannot locate the AIA container")
    return f"{AIA_CONTAINER},{base_dn}"


def _connect(user: str, password: str) -> Connection:
    """Bind to a domain controller, trying each one in turn.

    This is the one bind in the codebase that does not validate the domain controller
    certificate, because the bundle needed to validate it is what we are here to fetch.
    The channel is still encrypted, so the password is not in clear, but the server is
    unauthenticated for the duration of this single read.

    NTLM would avoid sending the password at all, but ldap3 computes the NTLM response
    with MD4, which OpenSSL 3 no longer offers by default, so it is not available here.
    Run this on the corporate network, and treat a `write_bundle` result that fails to
    validate the domain controller certificate as a reason to distrust the fetch.
    """
    servers = settings.ldap_servers_list
    if not servers:
        raise FetchError("LDAP_SERVERS is not set; nothing to connect to")

    failures: list[str] = []
    for host in servers:
        try:
            server = Server(
                host,
                port=settings.ldap_port,
                use_ssl=settings.ldap_use_ssl,
                tls=Tls(validate=ssl.CERT_NONE) if settings.ldap_use_ssl else None,
                connect_timeout=settings.ldap_timeout_seconds,
            )
            connection = Connection(
                server,
                user=user,
                password=password,
                authentication=SIMPLE,
                auto_bind=True,
                receive_timeout=settings.ldap_timeout_seconds,
                raise_exceptions=False,
            )
        except LDAPException as exc:
            failures.append(f"{host}: {exc}")
            continue

        print(f"Bound to {host} as {user}")
        return connection

    raise FetchError("Could not bind to any domain controller:\n  " + "\n  ".join(failures))


def _read_ca_certificates(connection: Connection) -> list[bytes]:
    """Return every DER-encoded CA certificate published in the AIA container."""
    container = aia_dn()
    found = connection.search(
        search_base=container,
        search_filter=CA_FILTER,
        search_scope=LEVEL,
        attributes=["cACertificate", "cn"],
    )
    if not found:
        raise FetchError(
            f"Search of {container} failed: {connection.result.get('description')} "
            f"- {connection.result.get('message', '').strip()}"
        )
    if not connection.entries:
        raise FetchError(f"No certificationAuthority entries under {container}")

    certificates: list[bytes] = []
    for entry in connection.entries:
        name = entry["cn"].value if "cn" in entry else "<unnamed>"
        values = entry["cACertificate"].raw_values or []
        if not values:
            print(f"  {name}: no cACertificate value, skipping")
            continue
        for der in values:
            print(f"  {name}: found certificate ({len(der)} bytes)")
            certificates.append(der)

    if not certificates:
        raise FetchError(f"Entries exist under {container} but none carry a cACertificate")
    return certificates


def _to_pem(der: bytes) -> str:
    body = b64encode(der).decode("ascii")
    lines = [body[index : index + 64] for index in range(0, len(body), 64)]
    return "-----BEGIN CERTIFICATE-----\n" + "\n".join(lines) + "\n-----END CERTIFICATE-----\n"


def _describe(der: bytes) -> str:
    """Summarise a certificate for the operator, without requiring a crypto library."""
    fingerprint = hashlib.sha256(der).hexdigest()
    pairs = [fingerprint[index : index + 2].upper() for index in range(0, len(fingerprint), 2)]
    return "SHA256:" + ":".join(pairs)


def write_bundle(certificates: list[bytes], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    # Deduplicate while preserving order, so re-running after a renewal keeps the old
    # certificate alongside the new one instead of doubling it up.
    seen: set[bytes] = set()
    unique = [der for der in certificates if not (der in seen or seen.add(der))]

    output.write_text("".join(_to_pem(der) for der in unique), encoding="ascii")
    output.chmod(0o600)

    print(f"\nWrote {len(unique)} certificate(s) to {output}")
    for der in unique:
        print(f"  {_describe(der)}")


def verify_bundle(output: Path) -> bool:
    """Open a validated LDAPS connection to every DC using the new bundle.

    This is the check that matters: it runs the same `Tls` configuration as
    `ldap_client._build_server_pool`, against each host in `LDAP_SERVERS`, so a bundle
    that satisfies one domain controller but not its failover siblings is caught here
    rather than during a sign-in.
    """
    print(f"\nValidating {output} against each domain controller:")
    tls = Tls(
        ca_certs_file=str(output),
        validate=ssl.CERT_REQUIRED,
        version=ssl.PROTOCOL_TLS_CLIENT,
    )

    all_ok = True
    for host in settings.ldap_servers_list:
        server = Server(
            host,
            port=settings.ldap_port,
            use_ssl=True,
            tls=tls,
            connect_timeout=settings.ldap_timeout_seconds,
        )
        # An anonymous bind is enough: the TLS handshake happens first, and it is the
        # handshake that exercises certificate validation.
        connection = Connection(server, receive_timeout=settings.ldap_timeout_seconds)
        try:
            connection.open()
        except LDAPException as exc:
            print(f"  {host}: FAILED - {exc}")
            all_ok = False
        else:
            print(f"  {host}: OK")
            connection.unbind()

    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user",
        help=(
            "Bind account in NETBIOS form, e.g. CORP\\jsmith. "
            "Defaults to LDAP_BIND_DN; the password is prompted for."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write the PEM bundle (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    if args.user:
        user = args.user
        password = getpass(f"Password for {user}: ")
    elif settings.ldap_bind_dn and settings.ldap_bind_password:
        user = settings.ldap_bind_dn
        password = settings.ldap_bind_password
        print(f"Using LDAP_BIND_DN ({user}) from configuration")
    else:
        raise FetchError(
            "No credentials available. Set LDAP_BIND_DN and LDAP_BIND_PASSWORD, "
            "or pass --user CORP\\yourname to be prompted."
        )

    connection = _connect(user, password)
    try:
        print(f"Reading {aia_dn()}")
        certificates = _read_ca_certificates(connection)
    finally:
        connection.unbind()

    write_bundle(certificates, args.output)

    if not verify_bundle(args.output):
        print(
            "\nThe bundle did not validate every domain controller. Do not trust it: "
            "re-run on the corporate network, and check that LDAP_SERVERS uses the "
            "fully-qualified names in the certificate SAN.",
            file=sys.stderr,
        )
        return 1

    print(f"\nDone. LDAP_CA_CERT_FILE={args.output} is ready to use.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except FetchError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
