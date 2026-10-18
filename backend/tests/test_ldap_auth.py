import pytest
from fastapi.testclient import TestClient

from app.auth import ldap_client, throttle
from app.auth.dependencies import entitlements_for
from app.auth.ldap_client import LdapIdentity, normalise_username
from app.core.config import get_settings
from app.main import app

settings = get_settings()


@pytest.fixture(autouse=True)
def _reset_state():
    throttle.clear_all()
    original = (settings.ldap_group_general, settings.ldap_group_confidential)
    settings.ldap_group_general = "DUX_Vault_General"
    settings.ldap_group_confidential = "DUX_Vault_Confidential"
    yield
    settings.ldap_group_general, settings.ldap_group_confidential = original
    throttle.clear_all()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "auth_bypass_enabled", False)
    # https, because SESSION_COOKIE_SECURE is on: the client would silently drop the
    # session cookie over plain http, and the sign-in round-trip tests below would fail
    # for a reason that has nothing to do with authentication. This also matches how the
    # app is actually served.
    return TestClient(app, base_url="https://testserver")


def _identity(*group_names: str) -> LdapIdentity:
    return LdapIdentity(
        username="jsmith",
        display_name="B Tong",
        email="jsmith@corp.local",
        dn="CN=B Tong,OU=Users,DC=corp,DC=local",
        group_names=list(group_names),
    )


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("CORP\\jsmith", "jsmith"),
        ("corp\\jsmith", "jsmith"),
        ("jsmith@corp.local", "jsmith"),
        ("jsmith", "jsmith"),
        ("  CORP\\jsmith  ", "jsmith"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_normalise_username(raw: str, expected: str) -> None:
    assert normalise_username(raw) == expected


def test_empty_password_is_rejected_without_binding(monkeypatch) -> None:
    """A simple bind with an empty password can succeed as an anonymous bind."""

    def fail(*args, **kwargs):
        raise AssertionError("must not reach the directory")

    monkeypatch.setattr(ldap_client, "_build_server_pool", fail)

    for password in ("", "   "):
        with pytest.raises(ldap_client.LdapAuthError):
            ldap_client.authenticate("CORP\\jsmith", password)


def test_unusable_ca_bundle_fails_closed(monkeypatch) -> None:
    """A bad CA file must not fall back to an unvalidated connection."""
    monkeypatch.setattr(settings, "ldap_servers", "dc1.corp.local")
    monkeypatch.setattr(settings, "ldap_base_dn", "DC=corp,DC=local")
    monkeypatch.setattr(settings, "ldap_domain_netbios", "CORP")
    monkeypatch.setattr(settings, "ldap_use_ssl", True)
    monkeypatch.setattr(settings, "ldap_ca_cert_file", "/nonexistent/ca.pem")

    with pytest.raises(ldap_client.LdapConfigError):
        ldap_client.authenticate("CORP\\jsmith", "secret")


def test_ssl_without_ca_bundle_is_a_config_error(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ldap_servers", "dc1.corp.local")
    monkeypatch.setattr(settings, "ldap_base_dn", "DC=corp,DC=local")
    monkeypatch.setattr(settings, "ldap_domain_netbios", "CORP")
    monkeypatch.setattr(settings, "ldap_use_ssl", True)
    monkeypatch.setattr(settings, "ldap_ca_cert_file", "")

    with pytest.raises(ldap_client.LdapConfigError):
        ldap_client.authenticate("CORP\\jsmith", "secret")


def test_missing_directory_settings_is_a_config_error(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ldap_servers", "")

    with pytest.raises(ldap_client.LdapConfigError):
        ldap_client.authenticate("CORP\\jsmith", "secret")


USER_DN = "CN=B Tong,DC=corp,DC=local"


class _FakeConnection:
    def __init__(self, name: str) -> None:
        self.name = name
        self.unbound = False

    def unbind(self) -> None:
        self.unbound = True


def _group_reads(monkeypatch, results: dict[str, list[str]]) -> list[str]:
    """Stub _search_groups per connection, recording the order it was called in."""
    calls: list[str] = []

    def search(connection, user_dn):
        assert user_dn == USER_DN
        calls.append(connection.name)
        return results[connection.name]

    monkeypatch.setattr(ldap_client, "_search_groups", search)
    return calls


def _service_bind(monkeypatch, connection: _FakeConnection) -> list[str]:
    bound: list[str] = []

    def bind(pool, user, password):
        bound.append(user)
        return connection

    monkeypatch.setattr(ldap_client, "_bind", bind)
    return bound


# The user's own connection is the default path. A configured service account must stay out
# of it, or one account's credentials become a single point of failure for all sign-ins.
def test_groups_are_read_over_the_users_own_connection(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ldap_bind_dn", "CORP\\#IDM-SRVC")
    monkeypatch.setattr(settings, "ldap_bind_password", "correct")
    user_connection = _FakeConnection("user")
    calls = _group_reads(monkeypatch, {"user": ["#IDM-GENERAL"]})
    bound = _service_bind(monkeypatch, _FakeConnection("service"))

    groups = ldap_client._resolve_groups(object(), user_connection, USER_DN)

    assert groups == ["#IDM-GENERAL"]
    assert calls == ["user"]
    assert bound == [], "the service account was bound despite the user's own read working"


# An empty read means either "in no groups" or "not allowed to look", and they cannot be
# told apart here - so retry with the account that is allowed to.
def test_an_empty_read_falls_back_to_the_service_account(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ldap_bind_dn", "CORP\\#IDM-SRVC")
    monkeypatch.setattr(settings, "ldap_bind_password", "correct")
    service_connection = _FakeConnection("service")
    calls = _group_reads(monkeypatch, {"user": [], "service": ["#IDM-CONFIDENTIAL"]})
    bound = _service_bind(monkeypatch, service_connection)

    groups = ldap_client._resolve_groups(object(), _FakeConnection("user"), USER_DN)

    assert groups == ["#IDM-CONFIDENTIAL"]
    assert calls == ["user", "service"], "the user's own connection should be tried first"
    assert bound == ["CORP\\#IDM-SRVC"]
    assert service_connection.unbound, "the service connection was left open"


def test_an_empty_read_without_a_service_account_stays_empty(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ldap_bind_dn", "")
    calls = _group_reads(monkeypatch, {"user": []})

    def fail(*_args):
        raise AssertionError("bound without a service account configured")

    monkeypatch.setattr(ldap_client, "_bind", fail)

    assert ldap_client._resolve_groups(object(), _FakeConnection("user"), USER_DN) == []
    assert calls == ["user"]


def test_service_account_bind_failure_is_a_config_error(monkeypatch) -> None:
    """A bad service-account password must not be reported as the user's own.

    Both binds go through the same helper, so without the re-raise in
    ``_resolve_groups`` this surfaces as a 401 against the signing-in user and
    consumes their throttle allowance.
    """
    monkeypatch.setattr(settings, "ldap_bind_dn", "CORP\\#IDM-SRVC")
    monkeypatch.setattr(settings, "ldap_bind_password", "wrong")
    # Only an empty read reaches the fallback, so the service bind is never attempted
    # without this.
    _group_reads(monkeypatch, {"user": []})

    def reject(pool, user, password):
        raise ldap_client.LdapAuthError("Invalid username or password")

    monkeypatch.setattr(ldap_client, "_bind", reject)

    with pytest.raises(ldap_client.LdapConfigError):
        ldap_client._resolve_groups(object(), _FakeConnection("user"), USER_DN)


def test_entitlements_are_case_insensitive() -> None:
    assert entitlements_for(["dux_vault_general"]) == ["general"]


def test_confidential_implies_general() -> None:
    assert entitlements_for(["DUX_Vault_Confidential"]) == ["general", "confidential"]


def test_unrelated_groups_grant_nothing() -> None:
    assert entitlements_for(["Domain Users", "Finance"]) == []


def test_login_succeeds_and_sets_session(client, monkeypatch) -> None:
    monkeypatch.setattr(ldap_client, "authenticate", lambda u, p: _identity("DUX_Vault_General"))

    response = client.post(
        "/api/auth/login", json={"username": "CORP\\jsmith", "password": "secret"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["username"] == "jsmith"
    assert payload["data"]["groups"] == ["general"]

    # The session cookie now authenticates subsequent requests.
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["groups"] == ["general"]


def test_login_under_bypass_does_not_touch_the_directory(monkeypatch) -> None:
    """With the bypass on there is no directory, so the form must still succeed."""
    monkeypatch.setattr(settings, "auth_bypass_enabled", True)

    def fail(*args, **kwargs):
        raise AssertionError("must not reach the directory under bypass")

    monkeypatch.setattr(ldap_client, "authenticate", fail)

    response = TestClient(app).post(
        "/api/auth/login", json={"username": "CORP\\tongbr", "password": "anything"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["username"] == settings.auth_bypass_username
    assert response.json()["data"]["groups"] == ["general", "confidential"]


def test_login_rejects_bad_credentials(client, monkeypatch) -> None:
    def reject(username: str, password: str):
        raise ldap_client.LdapAuthError("nope")

    monkeypatch.setattr(ldap_client, "authenticate", reject)

    response = client.post("/api/auth/login", json={"username": "CORP\\jsmith", "password": "wrong"})

    assert response.status_code == 401
    assert "wrong" not in response.text


def test_login_denies_user_without_entitlement_groups(client, monkeypatch) -> None:
    monkeypatch.setattr(ldap_client, "authenticate", lambda u, p: _identity("Domain Users"))

    response = client.post(
        "/api/auth/login", json={"username": "CORP\\jsmith", "password": "secret"}
    )

    assert response.status_code == 403


def test_login_throttles_after_max_attempts(client, monkeypatch) -> None:
    def reject(username: str, password: str):
        raise ldap_client.LdapAuthError("nope")

    monkeypatch.setattr(ldap_client, "authenticate", reject)

    body = {"username": "CORP\\jsmith", "password": "wrong"}
    for _ in range(settings.login_max_attempts):
        assert client.post("/api/auth/login", json=body).status_code == 401

    # The next attempt is refused locally, before it can consume an AD lockout attempt.
    assert client.post("/api/auth/login", json=body).status_code == 429


def test_directory_outage_returns_503(client, monkeypatch) -> None:
    def unavailable(username: str, password: str):
        raise ldap_client.LdapUnavailableError("no DC")

    monkeypatch.setattr(ldap_client, "authenticate", unavailable)

    response = client.post(
        "/api/auth/login", json={"username": "CORP\\jsmith", "password": "secret"}
    )

    assert response.status_code == 503


def test_logout_clears_the_session(client, monkeypatch) -> None:
    monkeypatch.setattr(ldap_client, "authenticate", lambda u, p: _identity("DUX_Vault_General"))

    client.post("/api/auth/login", json={"username": "jsmith", "password": "secret"})
    assert client.get("/api/auth/me").status_code == 200

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_confidential_route_is_denied_without_entitlement(client, monkeypatch) -> None:
    """Regression: the guard must fail closed, not skip when config is blank."""
    monkeypatch.setattr(ldap_client, "authenticate", lambda u, p: _identity("DUX_Vault_General"))
    client.post("/api/auth/login", json={"username": "jsmith", "password": "secret"})

    response = client.get(
        "/api/documents/supplier-invoices/confidential",
        params={"supplierNumber": "1"},
    )
    assert response.status_code == 403
