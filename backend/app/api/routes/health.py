from datetime import UTC, datetime

from fastapi import APIRouter

from app.schemas.documents import HealthResponse
from app.utils.api_responses import success_envelope

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, object]:
    return success_envelope(HealthResponse(status="ok", timestamp=datetime.now(UTC)))
