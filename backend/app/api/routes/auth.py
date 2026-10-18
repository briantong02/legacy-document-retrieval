import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.auth import ldap_client, throttle
from app.auth.dependencies import (
    CurrentUser,
    bypass_user,
    entitlements_for,
    get_current_user,
)
from app.core.config import get_settings
from app.schemas.documents import CurrentUserResponse
from app.utils.api_responses import success_envelope

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

INVALID_CREDENTIALS = "Invalid username or password"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)


def _client_key(request: Request) -> str:
    return f"ip:{request.client.host}" if request.client else ""


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)) -> dict[str, object]:
    return success_envelope(
        CurrentUserResponse(
            username=user.username,
            displayName=user.display_name,
            email=user.email,
            groups=user.groups,
        )
    )


@router.post("/login")
def login(request: Request, payload: LoginRequest) -> dict[str, object]:
    # Mirror get_current_user: when the bypass is on there is no directory to bind
    # against, so accept any credentials and return the stand-in identity. Without
    # this the login form is a dead end in local development.
    if settings.auth_bypass_enabled:
        user = bypass_user()
        return success_envelope(
            CurrentUserResponse(
                username=user.username,
                displayName=user.display_name,
                email=user.email,
                groups=user.groups,
            )
        )

    sam_account_name = ldap_client.normalise_username(payload.username)
    user_key = f"user:{sam_account_name.casefold()}" if sam_account_name else ""
    ip_key = _client_key(request)

    if throttle.is_throttled(user_key, ip_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-in attempts. Please wait a few minutes and try again.",
        )

    try:
        identity = ldap_client.authenticate(payload.username, payload.password)
    except ldap_client.LdapAuthError:
        throttle.record_failure(user_key, ip_key)
        logger.warning("Failed sign-in for %s", sam_account_name or "<empty>")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
        ) from None
    except ldap_client.LdapConfigError as exc:
        logger.error("Directory authentication is misconfigured: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Active Directory authentication is not configured",
        ) from None
    except ldap_client.LdapUnavailableError:
        logger.exception("No domain controller could be reached")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The directory service is unavailable. Please try again shortly.",
        ) from None

    entitlements = entitlements_for(identity.group_names)
    if not entitlements:
        logger.warning("Sign-in denied for %s: no entitlement groups", identity.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of a group that grants access to this application.",
        )

    matched = [
        name
        for name in identity.group_names
        if name.casefold()
        in {
            settings.ldap_group_general.casefold(),
            settings.ldap_group_confidential.casefold(),
        }
    ]

    throttle.reset(user_key, ip_key)

    request.session.clear()
    request.session["user"] = {
        "username": identity.username,
        "display_name": identity.display_name,
        "email": identity.email,
        "entitlements": entitlements,
        # Retained for audit logging; deliberately not sent to the browser.
        "ad_groups_matched": matched,
    }

    logger.info("Sign-in for %s with entitlements %s", identity.username, entitlements)

    return success_envelope(
        CurrentUserResponse(
            username=identity.username,
            displayName=identity.display_name,
            email=identity.email,
            groups=entitlements,
        )
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
