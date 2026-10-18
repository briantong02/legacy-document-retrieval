from datetime import date

from fastapi import HTTPException


def infer_content_type(file_name: str) -> str:
    lowered = file_name.lower()
    if lowered.endswith(".pdf"):
        return "application/pdf"
    if lowered.endswith(".xlsx"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "application/octet-stream"


def validate_iso_date(value: str | None, label: str) -> str | None:
    if not value:
        return None
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {label}") from exc
    return value


def reject_combined_filters(
    first_value: str | None,
    first_label: str,
    second_value: str | None,
    second_label: str,
) -> None:
    """Reject a pair of filters that may only ever be used one at a time.

    The form disables one input as soon as the other is filled, so this can only be hit by
    calling the API directly. It stays because the UI is not a security boundary.
    """
    if (first_value or "").strip() and (second_value or "").strip():
        raise HTTPException(
            status_code=400,
            detail=f"Enter either {first_label} or {second_label}, not both",
        )
