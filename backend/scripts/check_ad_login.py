"""Report what the application actually sees when one account signs in.

A failed sign-in tells you very little from the outside. Three quite different faults
all surface as the same HTTP 403 "not a member of a group that grants access":

* the account genuinely is not in either entitlement group;
* the account is in them, but the directory will not let it read its own group
  membership, so the lookup comes back empty;
* LDAP_GROUP_GENERAL / LDAP_GROUP_CONFIDENTIAL name groups that do not exist, so
  nothing could ever match.

This walks the same path as `ldap_client.authenticate` and prints each stage, then
checks the configured group names against the directory to separate the last case from
the first two. Use it before asking anyone to change group membership, and to diagnose a
tester who cannot get in.

Needs a terminal: the password is read with getpass, so run it from a real shell rather
than a tool that captures stdout.

    PYTHONPATH=. python scripts/check_ad_login.py --user 'CORP\\jsmith'

`--for` binds as one account and reads another's membership, which is the only thing the
LDAP_BIND_DN service account is used for and the one path a plain run cannot exercise:

    PYTHONPATH=. python scripts/check_ad_login.py --user 'CORP\\#IDM-SRVC' --for jsmith
"""

from __future__ import annotations

import argparse
import sys
from getpass import getpass

from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars

from app.auth import ldap_client
from app.auth.dependencies import entitlements_for
from app.core.config import get_settings

settings = get_settings()


def _find_group(connection, group_name: str) -> list[dict[str, str]] | None:
    """Look a group up by cn, sAMAccountName or name. None if the search itself failed.

    Searching all three matters: the app matches on sAMAccountName, so a group whose CN
    carries the intended name while its sAMAccountName differs exists but will never grant
    anything. Reporting both attributes makes that visible instead of reading as absence.
    """
    safe_name = escape_filter_chars(group_name)
    try:
        found = connection.search(
            search_base=settings.ldap_base_dn,
            search_filter=(
                f"(&(objectClass=group)(|(cn={safe_name})"
                f"(sAMAccountName={safe_name})(name={safe_name})))"
            ),
            attributes=["cn", "sAMAccountName", "distinguishedName"],
            size_limit=5,
        )
    except LDAPException:
        return None
    if not found:
        return None
    return [
        {
            "cn": str(entry["cn"].value or ""),
            "sam": str(entry["sAMAccountName"].value or ""),
            "dn": str(entry["distinguishedName"].value or ""),
        }
        for entry in connection.entries
    ]


def _report_configured_groups(connection) -> bool:
    """Print the state of each configured entitlement group.

    Returns True when every configured group exists under the name the app actually
    compares, which is what separates "your config is wrong" from "this user is not a
    member" when no entitlements come out.
    """
    all_usable = True

    print("\nConfigured entitlement groups:")
    for label, name in (
        ("LDAP_GROUP_GENERAL", settings.ldap_group_general),
        ("LDAP_GROUP_CONFIDENTIAL", settings.ldap_group_confidential),
    ):
        if not name:
            print(f"  {label:25} (not set)")
            all_usable = False
            continue

        matches = _find_group(connection, name)
        if matches is None:
            print(f"  {label:25} {name!r}: could not be checked - the search failed")
            all_usable = False
            continue
        if not matches:
            print(f"  {label:25} {name!r}: NOT FOUND - matches no group by cn or sAMAccountName")
            all_usable = False
            continue

        for match in matches:
            # Only the sAMAccountName is compared at sign-in, so say so when the CN is what
            # matched.
            if match["sam"].casefold() == name.casefold():
                note = "sAMAccountName matches - this is the name the app compares"
            else:
                note = f"WRONG NAME IN CONFIG - use sAMAccountName {match['sam']!r} instead"
                all_usable = False
            print(f"  {label:25} {name!r}: found (cn={match['cn']!r}) - {note}")

    return all_usable


def _report_group_read(connection, subject: str, user_dn: str, is_self: bool) -> list[str]:
    """Print the groups readable for `user_dn` over `connection`, and say what that means."""
    group_names = ldap_client._search_groups(connection, user_dn)

    whose = "its own" if is_self else f"{subject}'s"
    print(f"\nGroups readable over this connection ({whose} membership): {len(group_names)}")

    if group_names:
        for name in sorted(group_names):
            print(f"  {name}")
        return group_names

    if is_self:
        print(
            "  none returned. Either this account is in no groups, or the directory will\n"
            "  not let it read its own membership. For a service account, being in no\n"
            "  groups is normal and says nothing either way - use --for to test whether it\n"
            "  can read somebody else's. For a normal user you know is in a group, it is\n"
            "  the directory refusing the read, and the service-account fallback in\n"
            "  _resolve_groups is what covers it."
        )
    else:
        print(
            f"  none returned. This account cannot read {subject}'s membership, so it is no\n"
            "  use as the LDAP_BIND_DN fallback. IT would need to grant it read access to\n"
            "  group membership."
        )
    return group_names


def main() -> int:
    parser = argparse.ArgumentParser(description="Check one AD account against this app.")
    parser.add_argument(
        "--user",
        required=True,
        help="Account to bind as, e.g. 'CORP\\jsmith', 'jsmith@corp.example.com' or 'jsmith'",
    )
    parser.add_argument(
        "--for",
        dest="subject",
        help=(
            "Resolve groups for this account instead of the one binding. Use it to test "
            "whether a service account can read somebody else's membership, which is the "
            "only thing LDAP_BIND_DN is for."
        ),
    )
    args = parser.parse_args()

    sam_account_name = ldap_client.normalise_username(args.user)
    if not sam_account_name:
        print(f"error: {args.user!r} does not reduce to a username", file=sys.stderr)
        return 1

    subject_name = sam_account_name
    if args.subject:
        subject_name = ldap_client.normalise_username(args.subject)
        if not subject_name:
            print(f"error: {args.subject!r} does not reduce to a username", file=sys.stderr)
            return 1
    is_self = subject_name.casefold() == sam_account_name.casefold()

    print(f"Username {args.user!r} normalises to {sam_account_name!r}")
    password = getpass(f"Password for {args.user}: ")

    try:
        pool = ldap_client._build_server_pool()
    except ldap_client.LdapConfigError as exc:
        print(f"\nDirectory config is unusable -> the app would return 500\n  {exc}")
        return 1

    bind_user = f"{settings.ldap_domain_netbios}\\{sam_account_name}"
    print(f"Binding as {bind_user}")
    try:
        connection = ldap_client._bind(pool, bind_user, password)
    except ldap_client.LdapAuthError as exc:
        print(f"\nBind rejected -> the app would return 401\n  {exc}")
        return 1
    except ldap_client.LdapUnavailableError as exc:
        print(f"\nNo domain controller reachable -> the app would return 503\n  {exc}")
        return 1

    print("Bind succeeded - the password and the CA bundle are both good.")

    try:
        attributes = ldap_client._search_user(connection, subject_name)
        user_dn = ldap_client._first_string(attributes.get("distinguishedName"))
        heading = "Directory identity" if is_self else f"Directory identity of {subject_name}"
        print(f"\n{heading}:")
        print(f"  sAMAccountName {ldap_client._first_string(attributes.get('sAMAccountName'))}")
        print(f"  displayName    {ldap_client._first_string(attributes.get('displayName'))}")
        print(f"  mail           {ldap_client._first_string(attributes.get('mail')) or '(none)'}")
        print(f"  DN             {user_dn}")

        group_names = _report_group_read(connection, subject_name, user_dn, is_self)
        groups_usable = _report_configured_groups(connection)
    except ldap_client.LdapAuthError as exc:
        # _search_user raises this when the subject is not in the directory at all.
        print(f"\nCould not look up {subject_name!r}: {exc}", file=sys.stderr)
        return 1
    finally:
        connection.unbind()

    entitlements = entitlements_for(group_names)
    whose = "" if is_self else f" to {subject_name}"
    print(f"\nEntitlements the app would grant{whose}: {entitlements or '(none)'}")
    if entitlements:
        print("Sign-in would succeed.")
        if "confidential" in entitlements:
            print(
                "All six options are visible, so this account cannot be used to check that\n"
                "Confidential documents are blocked - that needs a General-only account."
            )
        else:
            print("General only: option 4 (Confidential) should be refused.")
    else:
        print("Sign-in would be refused with 403 - the password itself having been accepted.")
        if not group_names:
            print(
                "  No groups came back at all, so either there is no membership to find or\n"
                "  the read was refused. See the note above."
            )
        elif groups_usable:
            # The groups exist under the name the app compares, and the membership list was
            # read successfully - so nothing is misconfigured; the account is simply not in
            # them.
            print(
                f"  Both entitlement groups exist and {subject_name}'s membership was read\n"
                "  successfully - this account is just not in either of them. Nothing is\n"
                "  misconfigured; ask whoever administers Active Directory to add it."
            )
        else:
            print(
                "  Membership was read, but at least one configured group name is unusable\n"
                "  (see above), so no membership could ever match it. Fix the name first."
            )

    if not is_self:
        print(
            f"\nThis was a read of {subject_name}'s membership over {bind_user}'s connection,\n"
            "which is what the LDAP_BIND_DN fallback does. Groups above means the fallback\n"
            "works; none means it does not."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
