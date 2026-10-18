"""Regression cover for the optional filters on options 2, 4, 5 and 6.

The date is supplied by a date picker as an ISO string. Leaving it blank used to raise a
500: SQL Server's CONCAT turns NULL into an empty string, so the query built the literal
'20--' and CONVERT failed with error 241.

Each of these options also takes an optional document or invoice number that may not be
combined with the date - see the exclusivity cases at the end of this module.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.routes import documents as documents_route
from app.auth.dependencies import (
    get_current_user,
    require_confidential_group,
    require_general_group,
)
from app.db.queries.ar_remittances import SEARCH_SQL as AR_REMITTANCES_SQL
from app.db.queries.supplier_invoices import (
    CONFIDENTIAL_SQL,
    EXPENSES_SQL,
    GENERAL_SQL,
)
from app.main import app

ROUTES = [
    "/api/documents/supplier-invoices/confidential",
    "/api/documents/supplier-invoices/expenses",
    "/api/documents/supplier-invoices/general",
]


@pytest.fixture
def client(monkeypatch):
    user = type(
        "User",
        (),
        {
            "username": "test.user",
            "display_name": "Test User",
            "email": "test.user@dux.local",
            "groups": ["general", "confidential"],
        },
    )()
    for dependency in (
        get_current_user,
        require_general_group,
        require_confidential_group,
    ):
        app.dependency_overrides[dependency] = lambda: user

    captured: dict[str, object] = {}

    def fake_run_search(option, filters):
        captured["option"] = option
        captured["filters"] = dict(filters)
        return []

    monkeypatch.setattr(documents_route, "run_search", fake_run_search)

    yield TestClient(app), captured
    app.dependency_overrides.clear()


@pytest.mark.parametrize("route", ROUTES)
def test_search_without_a_date_succeeds(client, route: str) -> None:
    """The default search leaves the date blank - this used to be a 500."""
    http, captured = client

    response = http.get(route, params={"supplierNumber": "128679"})

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured["filters"]["fromDate"] is None


@pytest.mark.parametrize("route", ROUTES)
def test_search_passes_an_iso_date_through(client, route: str) -> None:
    http, captured = client

    response = http.get(route, params={"supplierNumber": "128679", "fromDate": "2020-01-01"})

    assert response.status_code == 200
    assert captured["filters"]["fromDate"] == "2020-01-01"


@pytest.mark.parametrize("route", ROUTES)
def test_search_rejects_a_non_iso_date(client, route: str) -> None:
    """The old ddmmyy format is no longer accepted."""
    http, _ = client

    response = http.get(route, params={"supplierNumber": "128679", "fromDate": "010120"})

    assert response.status_code == 400


@pytest.mark.parametrize("sql", [CONFIDENTIAL_SQL, EXPENSES_SQL, GENERAL_SQL])
def test_query_never_rebuilds_the_parameter_date(sql) -> None:
    """Guards the exact defect: :from_date must be compared, never fed through CONCAT.

    CONCAT renders NULL as an empty string, so any CONCAT over :from_date reintroduces the
    '20--' literal that made CONVERT fail whenever the filter was omitted.
    """
    statement = str(sql)

    assert ":from_date" in statement
    concat_over_parameter = "TRIM(:from_date)" in statement
    assert not concat_over_parameter, "parameter date must not be rebuilt in SQL"


@pytest.mark.parametrize("sql", [CONFIDENTIAL_SQL, EXPENSES_SQL, GENERAL_SQL])
def test_query_tolerates_malformed_stored_dates(sql) -> None:
    """A corrupt M3_Date must yield NULL, not abort the query, and must sort last."""
    statement = str(sql)

    assert "TRY_CONVERT" in statement
    assert "CONVERT(\n" not in statement.replace("TRY_CONVERT", "")
    assert "CASE WHEN d.m3_date_value IS NULL THEN 1 ELSE 0 END" in statement


# The optional date and the optional number are mutually exclusive on both the remittance
# and the supplier invoice options. The form disables one input as soon as the other is
# filled, so these cases only arise when the API is called directly.

REMITTANCE_ROUTE = "/api/documents/ar-remittances"


def test_remittances_accept_a_creation_date_alone(client) -> None:
    http, captured = client

    response = http.get(
        REMITTANCE_ROUTE,
        params={"payerNumber": "H14824", "createdAfter": "2025-06-02"},
    )

    assert response.status_code == 200
    assert captured["filters"]["createdAfter"] == "2025-06-02"
    assert captured["filters"]["documentNumber"] is None


def test_remittances_accept_a_document_number_alone(client) -> None:
    http, captured = client

    response = http.get(
        REMITTANCE_ROUTE,
        params={"payerNumber": "H14824", "documentNumber": "123456"},
    )

    assert response.status_code == 200
    assert captured["filters"]["documentNumber"] == "123456"
    assert captured["filters"]["createdAfter"] is None


def test_remittances_accept_neither_filter(client) -> None:
    http, captured = client

    response = http.get(REMITTANCE_ROUTE, params={"payerNumber": "H14824"})

    assert response.status_code == 200
    assert captured["filters"]["createdAfter"] is None
    assert captured["filters"]["documentNumber"] is None


def test_remittances_reject_both_filters(client) -> None:
    http, _ = client

    response = http.get(
        REMITTANCE_ROUTE,
        params={
            "payerNumber": "H14824",
            "createdAfter": "2025-06-02",
            "documentNumber": "123456",
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["error"]["message"] == "Enter either Creation Date or Document#, not both"
    )


@pytest.mark.parametrize("route", ROUTES)
def test_invoices_accept_an_invoice_number_alone(client, route: str) -> None:
    http, captured = client

    response = http.get(route, params={"supplierNumber": "128679", "invoiceNumber": "INV-001"})

    assert response.status_code == 200
    assert captured["filters"]["invoiceNumber"] == "INV-001"
    assert captured["filters"]["fromDate"] is None


@pytest.mark.parametrize("route", ROUTES)
def test_invoices_reject_both_filters(client, route: str) -> None:
    http, _ = client

    response = http.get(
        route,
        params={
            "supplierNumber": "128679",
            "fromDate": "2020-01-01",
            "invoiceNumber": "INV-001",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Enter either M3 Date or Invoice#, not both"


def test_remittance_query_filters_on_the_document_number() -> None:
    statement = str(AR_REMITTANCES_SQL)

    assert ":document_no IS NULL OR [M3_CINO] = :document_no" in statement


@pytest.mark.parametrize("sql", [CONFIDENTIAL_SQL, EXPENSES_SQL, GENERAL_SQL])
def test_invoice_query_filters_on_the_invoice_number(sql) -> None:
    statement = str(sql)

    assert ":invoice_no IS NULL OR [M3_Supplier_Invoice_No] = :invoice_no" in statement
