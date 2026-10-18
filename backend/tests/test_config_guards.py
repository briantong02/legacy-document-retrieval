import pytest

from app.core.config import DEFAULT_SESSION_SECRET, Settings

SAFE = {
    "app_env": "production",
    "session_secret": "a-real-secret-value-long-enough",
    "session_cookie_secure": True,
    "auth_bypass_enabled": False,
}


def _settings(**overrides) -> Settings:
    # Explicit kwargs win over the env file, so these cases do not depend on whatever
    # .env.development happens to hold.
    return Settings(**{**SAFE, **overrides})


def test_safe_production_config_starts_without_warnings() -> None:
    assert _settings().validate_for_runtime() == []


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"auth_bypass_enabled": True}, "AUTH_BYPASS_ENABLED"),
        ({"session_secret": DEFAULT_SESSION_SECRET}, "SESSION_SECRET"),
        ({"session_cookie_secure": False}, "SESSION_COOKIE_SECURE"),
    ],
)
def test_production_refuses_unsafe_config(overrides: dict, expected: str) -> None:
    with pytest.raises(RuntimeError, match=expected):
        _settings(**overrides).validate_for_runtime()


def test_production_reports_every_fault_at_once() -> None:
    with pytest.raises(RuntimeError) as error:
        _settings(
            auth_bypass_enabled=True,
            session_secret=DEFAULT_SESSION_SECRET,
            session_cookie_secure=False,
        ).validate_for_runtime()

    message = str(error.value)
    for setting in ("AUTH_BYPASS_ENABLED", "SESSION_SECRET", "SESSION_COOKIE_SECURE"):
        assert setting in message, message


# Development has to keep working, so the same faults only warn there. The bypass message
# names the entitlements it hands out, because that is the part that surprises people.
def test_development_warns_instead_of_refusing() -> None:
    warnings = _settings(
        app_env="development",
        auth_bypass_enabled=True,
        session_secret=DEFAULT_SESSION_SECRET,
        session_cookie_secure=False,
    ).validate_for_runtime()

    assert any("AUTH_BYPASS_ENABLED" in warning for warning in warnings)
    assert any("confidential" in warning for warning in warnings)
    assert any("SESSION_SECRET" in warning for warning in warnings)
    # Not flagged outside production: local development is served over plain HTTP.
    assert not any("SESSION_COOKIE_SECURE" in warning for warning in warnings)


@pytest.mark.parametrize("value", ["prod", "production", "PRODUCTION", " Production "])
def test_production_is_recognised_by_name(value: str) -> None:
    assert _settings(app_env=value).is_production is True


@pytest.mark.parametrize("value", ["development", "dev", "staging", ""])
def test_other_environments_are_not_production(value: str) -> None:
    assert _settings(app_env=value).is_production is False
