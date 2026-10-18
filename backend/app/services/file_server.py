from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.utils.document_utils import infer_content_type
from app.utils.path_utils import resolve_path


def build_document_response(
    *,
    document_path: str,
    resource_name: str,
    as_download: bool,
) -> FileResponse:
    settings = get_settings()
    try:
        local_path = resolve_path(
            document_path=document_path,
            canonical_root=settings.doc_root_canonical,
            local_root=settings.doc_root_local,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "invalid_document_path",
                "message": "Document path cannot be resolved",
            },
        ) from exc

    file_path = Path(local_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file cannot be located")

    content_type = infer_content_type(resource_name)

    return FileResponse(
        file_path,
        media_type=content_type,
        filename=resource_name if as_download else None,
    )
