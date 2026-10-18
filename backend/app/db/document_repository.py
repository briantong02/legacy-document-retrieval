from collections.abc import Mapping

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.queries.ar_registrations import SEARCH_SQL as AR_REGISTRATION_SQL
from app.db.queries.ar_remittances import SEARCH_SQL as AR_REMITTANCES_SQL
from app.db.queries.supplier_invoices import (
    CONFIDENTIAL_SQL,
    EXPENSES_SQL,
    GENERAL_SQL,
)
from app.db.queries.supplier_master_forms import SEARCH_SQL as SUPPLIER_MASTER_FORMS_SQL
from app.db.session import docmgmt_engine, idm_engine

OPTION_QUERY_MAP = {
    "ar-registration": AR_REGISTRATION_SQL,
    "ar-remittances": AR_REMITTANCES_SQL,
    "supplier-master-forms": SUPPLIER_MASTER_FORMS_SQL,
    "supplier-invoices/confidential": CONFIDENTIAL_SQL,
    "supplier-invoices/expenses": EXPENSES_SQL,
    "supplier-invoices/general": GENERAL_SQL,
}

# The IDM view backing each option. Every option draws from exactly one view, which is
# what lets a resource id be tied back to the option that is allowed to serve it - see
# document_belongs_to_option.
OPTION_TABLE_MAP = {
    "ar-registration": "DUX_AR_Registrations",
    "ar-remittances": "DUX_AR_Remittances",
    "supplier-master-forms": "DUX_Supplier_Master_Forms",
    "supplier-invoices/confidential": "DuxSupplierInvoice_Con",
    "supplier-invoices/expenses": "DuxSupplierInvoice_Exp",
    "supplier-invoices/general": "DuxSupplierInvoice_Gen",
}


def _is_missing_object_error(error: Exception) -> bool:
    message = str(error)
    return "Invalid object name" in message or "42S02" in message


def run_search(option: str, filters: Mapping[str, str]) -> list[dict[str, str | None]]:
    sql = OPTION_QUERY_MAP.get(option)
    if sql is None:
        raise ValueError(f"Unsupported option: {option}")

    params = {
        "customer_no": (filters.get("customerNumber") or "").strip() or None,
        "payer_no": (filters.get("payerNumber") or "").strip() or None,
        "supplier_no": (filters.get("supplierNumber") or "").strip() or None,
        "created_after": (filters.get("createdAfter") or "").strip() or None,
        "from_date": (filters.get("fromDate") or "").strip() or None,
        "document_no": (filters.get("documentNumber") or "").strip() or None,
        "invoice_no": (filters.get("invoiceNumber") or "").strip() or None,
    }

    try:
        with idm_engine.connect() as connection:
            rows = connection.execute(sql, params).mappings().all()
    except DBAPIError as exc:
        if exc.orig and _is_missing_object_error(exc.orig):
            return []
        raise

    return [dict(row) for row in rows]


def document_belongs_to_option(option: str, resource_id: str) -> bool:
    """Is this resource actually served by this option?

    The option in a view or download URL is a claim made by the caller, and the
    entitlement check runs against that claim. Without this the claim is never tested:
    a caller entitled only to the General options could name one of them and pass any
    resource id, including a Confidential document's, because the resource id alone is
    enough to resolve a path. Confirming membership is what gives the entitlement check
    on the option its meaning.
    """
    table = OPTION_TABLE_MAP.get(option)
    if table is None:
        return False

    # The table name comes from OPTION_TABLE_MAP, never from the request; the resource id
    # is bound.
    sql = text(f"SELECT TOP 1 1 FROM [idm].[{table}] WHERE [RESOURCEID] = :resource_id")  # noqa: S608
    try:
        with idm_engine.connect() as connection:
            return connection.execute(sql, {"resource_id": resource_id}).first() is not None
    except DBAPIError as exc:
        if exc.orig and _is_missing_object_error(exc.orig):
            return False
        raise


def get_document_path(resource_id: str) -> str | None:
    sql = text(
        """
        SELECT TOP 1 DocumentPath
        FROM dbo.Document
        WHERE ResourceId = :resource_id
        """
    )
    try:
        with docmgmt_engine.connect() as connection:
            row = connection.execute(sql, {"resource_id": resource_id}).mappings().first()
    except DBAPIError as exc:
        if exc.orig and _is_missing_object_error(exc.orig):
            return None
        raise

    if not row:
        return None
    return row.get("DocumentPath")
