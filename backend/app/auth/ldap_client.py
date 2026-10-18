"""Active Directory authentication over LDAPS.

The application authenticates a user by performing a simple bind against a domain
controller with the credentials the user typed, then reads their identity and group
membership from the directory. Nothing is persisted; the caller stores the resulting
identity in the session cookie.
"""

import logging
import ssl
from dataclasses import dataclass

from ldap3 import ALL, SIMPLE, Connection, Server, ServerPool, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Matches nested group membership as well as direct membership.
# https://learn.microsoft.com/en-us/windows/win32/adsi/search-filter-syntax
LDAP_MATCHING_RULE_IN_CHAIN = "1.2.840.113556.1.4.1941"

USER_ATTRIBUTES = ["distinguishedName", "displayName", "mail", "sAMAccountName"]


class LdapAuthError(Exception):
    """Raised when a user cannot be authenticated against the directory."""


class LdapConfigError(Exception):
    """Raised when the directory settings are missing or unusable."""


class LdapUnavailableError(Exception):
    """Raised when no domain controller could be reached."""


@dataclass(frozen=True)
class LdapIdentity:
    username: str
    display_name: str
    email: str | None
    dn: str
    group_names: list[str]


def normalise_username(raw: str) -> str:
    """Reduce the accepted login forms to a bare sAMAccountName.

    Accepts ``CORP\\jsmith``, ``jsmith@corp.local`` and ``jsmith``.
    """
    value = (raw or "").strip()
    if not value:
        return ""

    if "\\" in value:
        value = value.rsplit("\\", 1)[1]
    elif "/" in value:
        value = value.rsplit("/", 1)[1]
    elif "@" in value:
        value = value.split("@", 1)[0]

    return value.strip()


def _ensure_configured() -> None:
    missing = [
        name
        for name, value in (
            ("LDAP_SERVERS", settings.ldap_servers_list),
            ("LDAP_BASE_DN", settings.ldap_base_dn),
            ("LDAP_DOMAIN_NETBIOS", settings.ldap_domain_netbios),
        )
        if not value
    ]
    if missing:
        raise LdapConfigError(
            f"Active Directory authentication is not configured: {', '.join(missing)} missing"
        )


def _build_server_pool() -> ServerPool:
    tls = None
    if settings.ldap_use_ssl:
        if not settings.ldap_ca_cert_file:
            raise LdapConfigError(
                "LDAP_CA_CERT_FILE must be set when LDAP_USE_SSL is enabled; "
                "the domain controller certificate has to be validated"
            )
        try:
            tls = Tls(
                ca_certs_file=settings.ldap_ca_cert_file,
                validate=ssl.CERT_REQUIRED,
                version=ssl.PROTOCOL_TLS_CLIENT,
            )
        except LDAPException as exc:
            # Unreadable or invalid CA bundle. Fail closed rather than fall back to
            # an unvalidated connection - a simple bind sends the user's password.
            raise LdapConfigError(f"LDAP_CA_CERT_FILE is unusable: {exc}") from exc

    try:
        servers = [
            Server(
                host,
                port=settings.ldap_port,
                use_ssl=settings.ldap_use_ssl,
                tls=tls,
                get_info=ALL,
                connect_timeout=settings.ldap_timeout_seconds,
            )
            for host in settings.ldap_servers_list
        ]
        return ServerPool(servers, pool_strategy="FIRST", active=True, exhaust=False)
    except LDAPException as exc:
        raise LdapConfigError(f"Invalid directory server settings: {exc}") from exc


def _bind(pool: ServerPool, user: str, password: str) -> Connection:
    try:
        connection = Connection(
            pool,
            user=user,
            password=password,
            authentication=SIMPLE,
            auto_bind=False,
            receive_timeout=settings.ldap_timeout_seconds,
            raise_exceptions=False,
        )
    except LDAPException as exc:
        raise LdapUnavailableError("Unable to reach a domain controller") from exc

    try:
        bound = connection.bind()
    except LDAPException as exc:
        raise LdapUnavailableError("Unable to reach a domain controller") from exc

    if not bound:
        raise LdapAuthError("Invalid username or password")

    # A simple bind with an empty password can succeed as an anonymous bind on some
    # directory servers. Passwords are rejected before we get here, but confirm the
    # connection really carries an identity before trusting it.
    try:
        whoami = connection.extend.standard.who_am_i()
    except LDAPException:
        whoami = None

    if whoami is not None and not str(whoami).strip():
        connection.unbind()
        raise LdapAuthError("Invalid username or password")

    return connection


def _search_user(connection: Connection, sam_account_name: str) -> dict[str, object]:
    safe_name = escape_filter_chars(sam_account_name)
    try:
        found = connection.search(
            search_base=settings.ldap_base_dn,
            search_filter=f"(&(objectCategory=person)(sAMAccountName={safe_name}))",
            attributes=USER_ATTRIBUTES,
            size_limit=2,
        )
    except LDAPException as exc:
        raise LdapUnavailableError("Directory search failed") from exc

    if not found or not connection.entries:
        raise LdapAuthError("User not found in the directory")

    entry = connection.entries[0]
    return {attribute: entry[attribute].value for attribute in USER_ATTRIBUTES}


def _search_groups(connection: Connection, user_dn: str) -> list[str]:
    safe_dn = escape_filter_chars(user_dn)
    try:
        found = connection.search(
            search_base=settings.ldap_base_dn,
            search_filter=f"(member:{LDAP_MATCHING_RULE_IN_CHAIN}:={safe_dn})",
            attributes=["sAMAccountName"],
        )
    except LDAPException as exc:
        raise LdapUnavailableError("Group search failed") from exc

    if not found:
        logger.warning("Group search returned no result for %s", user_dn)
        return []

    names = []
    for entry in connection.entries:
        value = entry["sAMAccountName"].value
        if isinstance(value, str) and value.strip():
            names.append(value.strip())
    return names


def _first_string(value: object, fallback: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list) and value:
        return _first_string(value[0], fallback)
    return fallback


def authenticate(username: str, password: str) -> LdapIdentity:
    """Bind as the given user and return their directory identity.

    Raises ``LdapAuthError`` for bad credentials, ``LdapConfigError`` when the
    directory settings are incomplete, and ``LdapUnavailableError`` when no domain
    controller can be reached.
    """
    sam_account_name = normalise_username(username)
    if not sam_account_name:
        raise LdapAuthError("Invalid username or password")

    # Never bind with an empty password: most directory servers treat that as a
    # request for an anonymous bind and return success.
    if not password or not password.strip():
        raise LdapAuthError("Invalid username or password")

    _ensure_configured()
    pool = _build_server_pool()

    bind_user = f"{settings.ldap_domain_netbios}\\{sam_account_name}"
    connection = _bind(pool, bind_user, password)

    try:
        attributes = _search_user(connection, sam_account_name)
        user_dn = _first_string(attributes.get("distinguishedName"))
        if not user_dn:
            raise LdapAuthError("User has no distinguished name")

        group_names = _resolve_groups(pool, connection, user_dn)
    finally:
        connection.unbind()

    directory_name = _first_string(attributes.get("sAMAccountName"), sam_account_name)
    return LdapIdentity(
        username=directory_name,
        display_name=_first_string(attributes.get("displayName"), directory_name),
        email=_first_string(attributes.get("mail")) or None,
        dn=user_dn,
        group_names=group_names,
    )


def _resolve_groups(pool: ServerPool, user_connection: Connection, user_dn: str) -> list[str]:
    """Read the user's groups over their own connection, falling back to the service account.

    Active Directory lets an authenticated user read group membership by default, so the
    user's own connection is tried first and is all most directories need. An empty result
    is ambiguous, though - it means either that the user is in no groups, or that the
    directory will not let them look - and the two are indistinguishable from here. So when
    a service account is configured, an empty result is retried through it.

    Falling back rather than choosing matters on both sides: a user whose own read is
    refused is covered without having to route everyone through one account, and a broken
    service account degrades only the users who actually need it instead of turning every
    sign-in into an HTTP 500.
    """
    groups = _search_groups(user_connection, user_dn)
    if groups or not settings.ldap_bind_dn:
        return groups

    try:
        service_connection = _bind(pool, settings.ldap_bind_dn, settings.ldap_bind_password)
    except LdapAuthError as exc:
        # The service account's own credentials are wrong, expired or empty. That is a
        # deployment fault, not the signing-in user's: reporting it as an auth failure
        # would blame their password and burn their sign-in throttle allowance.
        raise LdapConfigError(
            f"Service account bind failed for {settings.ldap_bind_dn}"
        ) from exc

    try:
        return _search_groups(service_connection, user_dn)
    finally:
        service_connection.unbind()
