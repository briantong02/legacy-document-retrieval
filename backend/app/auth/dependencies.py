from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status

from app.core.config import get_settings

# Entitlement tokens. These, not raw Active Directory group names, are what travels in
# the session cookie and over the wire: a user can belong to a large number of AD groups
# and the full list would not fit in a signed cookie, nor does the browser need to know
# how the directory is organised.
GENERAL = "general"
CONFIDENTIAL = "confidential"


@dataclass
class CurrentUser:
    username: str
    display_name: str
    email: str | None
    groups: list[str]


settings = get_settings()


def entitlements_for(group_names: list[str]) -> list[str]:
    """Map Active Directory group names onto the application's entitlement tokens.

    Comparison is case-insensitive because Active Directory group names are.
    """
    held = {name.strip().casefold() for name in group_names if name and name.strip()}

    entitlements = []
    if settings.ldap_group_general and settings.ldap_group_general.casefold() in held:
        entitlements.append(GENERAL)
    if settings.ldap_group_confidential and settings.ldap_group_confidential.casefold() in held:
        # Confidential is a superset of General (see docs/app-spec.md section 5.2).
        if GENERAL not in entitlements:
            entitlements.append(GENERAL)
        entitlements.append(CONFIDENTIAL)

    return entitlements


def bypass_user() -> CurrentUser:
    """The stand-in identity used when AUTH_BYPASS_ENABLED is set."""
    return CurrentUser(
        username=settings.auth_bypass_username,
        display_name=settings.auth_bypass_display_name,
        email=settings.auth_bypass_email or None,
        groups=settings.auth_bypass_groups_list,
    )


def get_current_user(request: Request) -> CurrentUser:
    if settings.auth_bypass_enabled:
        return bypass_user()

    stored: Any = request.session.get("user")
    if not isinstance(stored, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    username = stored.get("username")
    if not isinstance(username, str) or not username.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    display_name = stored.get("display_name")
    email = stored.get("email")
    groups = stored.get("entitlements")

    return CurrentUser(
        username=username,
        display_name=display_name if isinstance(display_name, str) and display_name else username,
        email=email if isinstance(email, str) and email else None,
        groups=[str(group) for group in groups] if isinstance(groups, list) else [],
    )


def _require(user: CurrentUser, entitlement: str) -> CurrentUser:
    if settings.auth_bypass_enabled:
        return user

    if entitlement not in user.groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorised for this option",
        )
    return user


def require_general_group(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return _require(user, GENERAL)


def require_confidential_group(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    return _require(user, CONFIDENTIAL)
