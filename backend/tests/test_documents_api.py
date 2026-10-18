import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user, require_general_group
from app.core.config import get_settings
from app.main import app

settings = get_settings()

RESOURCE_ID = "0000540b-cfc3-4cd9-922b-63cad9aab03a"


@pytest.fixture(autouse=True)
def _no_auth_bypass(monkeypatch):
    """Entitlement assertions are vacuous while the bypass is on.

    `_require` returns early when AUTH_BYPASS_ENABLED is set, so a suite that inherits it
    from the environment file would pass whether or not the checks work.
    """
    monkeypatch.setattr(settings, "auth_bypass_enabled", False)


def _override_user(groups: list[str]) -> None:
    user = type(
        "User",
        (),
        {
            "username": "test.user@dux.local",
            "display_name": "Test User",
            "email": "test.user@dux.local",
            "groups": groups,
        },
    )()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_general_group] = lambda: user


@pytest.fixture
def general_client():
    _override_user(["general"])
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def confidential_client():
    _override_user(["general", "confidential"])
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _document_is_in_option(monkeypatch):
    """Answer the option-membership check without a database.

    Default to True so the existing route tests exercise what they are about; the tests
    that care about the check override it.
    """
    monkeypatch.setattr(
        "app.api.routes.documents.document_belongs_to_option",
        lambda _option, _resource_id: True,
    )


def test_general_documents_route_requires_supported_option(general_client) -> None:
    response = general_client.get("/api/documents/unknown-option")

    assert response.status_code == 404
    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["message"] == "Not Found"


# Every option below must reach the handler rather than the SPA catch-all in
# app.main, which answers any unmatched /api/... GET with a bare "Not Found". The
# handler's own "Document not indexed" message is what proves the route matched -
# the two-segment supplier-invoice options previously did not.
@pytest.mark.parametrize(
    "option",
    [
        "ar-registration",
        "supplier-invoices/general",
        "supplier-invoices/expenses",
    ],
)
@pytest.mark.parametrize("action", ["view", "download"])
def test_document_action_routes_reach_the_handler(
    general_client,
    monkeypatch,
    option: str,
    action: str,
) -> None:
    monkeypatch.setattr(
        "app.api.routes.documents.get_document_path",
        lambda _resource_id: None,
    )

    response = general_client.get(
        f"/api/documents/{option}/{RESOURCE_ID}/{action}",
        params={"resourceName": "invoice.pdf"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Document not indexed"


@pytest.mark.parametrize("action", ["view", "download"])
def test_document_action_routes_reject_unknown_options(
    general_client,
    monkeypatch,
    action: str,
) -> None:
    monkeypatch.setattr(
        "app.api.routes.documents.get_document_path",
        lambda _resource_id: "e:\\some\\path",
    )

    response = general_client.get(
        f"/api/documents/supplier-invoices/unknown/{RESOURCE_ID}/{action}",
        params={"resourceName": "invoice.pdf"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Unsupported option"


# The entitlement check tests the option named in the URL, which the caller chooses. If
# the document is not also tied to that option, naming a General option is enough to pull
# a Confidential document down, because a resource id on its own resolves to a path. The
# document must not be served no matter how resolvable its path is.
@pytest.mark.parametrize("action", ["view", "download"])
def test_document_not_served_through_an_option_it_does_not_belong_to(
    general_client,
    monkeypatch,
    action: str,
) -> None:
    monkeypatch.setattr(
        "app.api.routes.documents.document_belongs_to_option",
        lambda _option, _resource_id: False,
    )

    def _fail_if_called(_resource_id):
        raise AssertionError("path resolved before membership was confirmed")

    monkeypatch.setattr("app.api.routes.documents.get_document_path", _fail_if_called)

    response = general_client.get(
        f"/api/documents/supplier-invoices/general/{RESOURCE_ID}/{action}",
        params={"resourceName": "invoice.pdf"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Document not found for this option"


@pytest.mark.parametrize("action", ["view", "download"])
def test_confidential_document_requires_the_confidential_entitlement(
    general_client,
    monkeypatch,
    action: str,
) -> None:
    monkeypatch.setattr(
        "app.api.routes.documents.get_document_path",
        lambda _resource_id: "e:\\some\\path",
    )

    response = general_client.get(
        f"/api/documents/supplier-invoices/confidential/{RESOURCE_ID}/{action}",
        params={"resourceName": "invoice.pdf"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize("action", ["view", "download"])
def test_confidential_access_is_logged(
    confidential_client,
    monkeypatch,
    caplog,
    action: str,
) -> None:
    """docs/app-spec.md section 7: user, resource id, timestamp and action."""
    monkeypatch.setattr(
        "app.api.routes.documents.get_document_path",
        lambda _resource_id: None,
    )

    with caplog.at_level("INFO", logger="app.api.routes.documents"):
        confidential_client.get(
            f"/api/documents/supplier-invoices/confidential/{RESOURCE_ID}/{action}",
            params={"resourceName": "invoice.pdf"},
        )

    # Logged before the path lookup can fail, so an unreadable file still leaves a record
    # of the attempt.
    assert any(
        action in record.message
        and RESOURCE_ID in str(record.args)
        and "test.user@dux.local" in str(record.args)
        for record in caplog.records
    ), caplog.text
