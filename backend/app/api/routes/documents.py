import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import (
    CurrentUser,
    require_confidential_group,
    require_general_group,
)
from app.db.document_repository import (
    document_belongs_to_option,
    get_document_path,
    run_search,
)
from app.services.file_server import build_document_response
from app.utils.api_responses import success_envelope
from app.utils.document_utils import reject_combined_filters, validate_iso_date

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

GENERAL_OPTIONS = {
    "ar-registration",
    "ar-remittances",
    "supplier-master-forms",
    "supplier-invoices/expenses",
    "supplier-invoices/general",
}
CONFIDENTIAL_OPTION = "supplier-invoices/confidential"


@router.get("/ar-registration")
def search_ar_registration(
    customerNumber: str = Query(...),
    _: CurrentUser = Depends(require_general_group),
) -> dict[str, object]:
    rows = run_search("ar-registration", {"customerNumber": customerNumber})
    return success_envelope(rows)


@router.get("/ar-remittances")
def search_ar_remittances(
    payerNumber: str = Query(...),
    createdAfter: str | None = Query(default=None),
    documentNumber: str | None = Query(default=None),
    _: CurrentUser = Depends(require_general_group),
) -> dict[str, object]:
    reject_combined_filters(createdAfter, "Creation Date", documentNumber, "Document#")
    rows = run_search(
        "ar-remittances",
        {
            "payerNumber": payerNumber,
            "createdAfter": validate_iso_date(createdAfter, "created date"),
            "documentNumber": documentNumber,
        },
    )
    return success_envelope(rows)


@router.get("/supplier-master-forms")
def search_supplier_master_forms(
    supplierNumber: str = Query(...),
    _: CurrentUser = Depends(require_general_group),
) -> dict[str, object]:
    rows = run_search("supplier-master-forms", {"supplierNumber": supplierNumber})
    return success_envelope(rows)


@router.get("/supplier-invoices/confidential")
def search_confidential_documents(
    supplierNumber: str = Query(...),
    fromDate: str | None = Query(default=None),
    invoiceNumber: str | None = Query(default=None),
    _: CurrentUser = Depends(require_confidential_group),
) -> dict[str, object]:
    reject_combined_filters(fromDate, "M3 Date", invoiceNumber, "Invoice#")
    rows = run_search(
        CONFIDENTIAL_OPTION,
        {
            "supplierNumber": supplierNumber,
            "fromDate": validate_iso_date(fromDate, "from date"),
            "invoiceNumber": invoiceNumber,
        },
    )
    return success_envelope(rows)


@router.get("/supplier-invoices/expenses")
def search_expense_documents(
    supplierNumber: str = Query(...),
    fromDate: str | None = Query(default=None),
    invoiceNumber: str | None = Query(default=None),
    _: CurrentUser = Depends(require_general_group),
) -> dict[str, object]:
    reject_combined_filters(fromDate, "M3 Date", invoiceNumber, "Invoice#")
    rows = run_search(
        "supplier-invoices/expenses",
        {
            "supplierNumber": supplierNumber,
            "fromDate": validate_iso_date(fromDate, "from date"),
            "invoiceNumber": invoiceNumber,
        },
    )
    return success_envelope(rows)


@router.get("/supplier-invoices/general")
def search_general_documents(
    supplierNumber: str = Query(...),
    fromDate: str | None = Query(default=None),
    invoiceNumber: str | None = Query(default=None),
    _: CurrentUser = Depends(require_general_group),
) -> dict[str, object]:
    reject_combined_filters(fromDate, "M3 Date", invoiceNumber, "Invoice#")
    rows = run_search(
        "supplier-invoices/general",
        {
            "supplierNumber": supplierNumber,
            "fromDate": validate_iso_date(fromDate, "from date"),
            "invoiceNumber": invoiceNumber,
        },
    )
    return success_envelope(rows)


# The option is matched with the `path` converter because three of the six options are
# themselves two segments (`supplier-invoices/general` and siblings). A bare `{option}`
# compiles to `[^/]+`, so those URLs never reached the handler and fell through to the
# SPA catch-all as a bare 404. The trailing literal `/view` keeps the match anchored, and
# the allowlist check below remains the validation gate.
def _authorise_document(
    option: str,
    resource_id: str,
    user: CurrentUser,
    action: str,
) -> str:
    """Check the caller may have this document through this option, and resolve its path.

    Shared by view and download so the checks cannot drift apart between them.
    """
    if option == CONFIDENTIAL_OPTION:
        require_confidential_group(user)
    elif option not in GENERAL_OPTIONS:
        raise HTTPException(status_code=404, detail="Unsupported option")

    # The option is only a claim by the caller, and the entitlement check above tested
    # that claim rather than this document. Without confirming the resource is actually
    # served by the option, being entitled to any one option would be enough to fetch
    # every document, Confidential included - the resource id alone resolves a path.
    # 404 rather than 403: whether the id exists under some other option is not the
    # caller's business.
    if not document_belongs_to_option(option, resource_id):
        raise HTTPException(status_code=404, detail="Document not found for this option")

    if option == CONFIDENTIAL_OPTION:
        # Required by docs/app-spec.md section 7: user, resource id, timestamp, action.
        # The timestamp comes from the log record. Denied attempts are already logged by
        # the HTTPException handler in app/main.py.
        #
        # Logged here, once access has been granted and before the path is resolved, so
        # that a document missing from disk still leaves a record that it was released to
        # this user.
        logger.info(
            "Confidential document %s: user=%s resource_id=%s",
            action,
            user.username,
            resource_id,
        )

    document_path = get_document_path(resource_id)
    if not document_path:
        raise HTTPException(status_code=404, detail="Document not indexed")

    return document_path


@router.get("/{option:path}/{resource_id}/view")
def view_document(
    option: str,
    resource_id: str,
    resourceName: str = Query(...),
    user: CurrentUser = Depends(require_general_group),
):
    document_path = _authorise_document(option, resource_id, user, "view")
    return build_document_response(
        document_path=document_path,
        resource_name=resourceName,
        as_download=False,
    )


@router.get("/{option:path}/{resource_id}/download")
def download_document(
    option: str,
    resource_id: str,
    resourceName: str = Query(...),
    user: CurrentUser = Depends(require_general_group),
):
    document_path = _authorise_document(option, resource_id, user, "download")
    return build_document_response(
        document_path=document_path,
        resource_name=resourceName,
        as_download=True,
    )
