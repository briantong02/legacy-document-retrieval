import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.utils.api_responses import error_envelope

settings = get_settings()
configure_logging(
    settings.log_level,
    json_logs=settings.app_env.lower() in {"prod", "production"},
)
logger = logging.getLogger(__name__)

# Before anything is served: a misconfiguration that leaves the app unauthenticated should
# stop the process in production, and be loud in the log everywhere else.
for warning in settings.validate_for_runtime():
    logger.warning("INSECURE CONFIGURATION: %s", warning)

app = FastAPI(title=settings.app_name)


def _status_to_error_code(status_code: int) -> str:
    if status_code == 400:
        return "bad_request"
    if status_code == 401:
        return "unauthorized"
    if status_code == 403:
        return "forbidden"
    if status_code == 404:
        return "not_found"
    if status_code == 409:
        return "conflict"
    if status_code == 422:
        return "validation_error"
    if status_code >= 500:
        return "internal_server_error"
    return "http_error"


def _log_http_error(request: Request, status_code: int, code: str, message: str) -> None:
    path = f"{request.method} {request.url.path}"
    if request.url.query:
        path = f"{path}?{request.url.query}"

    log_message = f"{path} -> {status_code} {code}: {message}"
    if status_code >= 500:
        logger.error(log_message)
    else:
        logger.warning(log_message)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        message = str(detail.get("message") or detail.get("detail") or "Request failed")
        details = detail.get("details")
        code = str(detail.get("code") or _status_to_error_code(exc.status_code))
    elif isinstance(detail, list):
        message = "Request failed"
        details = detail
        code = _status_to_error_code(exc.status_code)
    else:
        message = str(detail or "Request failed")
        details = None
        code = _status_to_error_code(exc.status_code)

    _log_http_error(_, exc.status_code, code, message)

    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(code=code, message=message, details=details),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    _log_http_error(request, 422, "validation_error", "Request validation failed")
    return JSONResponse(
        status_code=422,
        content=error_envelope(
            code="validation_error",
            message="Request validation failed",
            details=exc.errors(),
        ),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception while serving request", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=error_envelope(
            code="internal_server_error",
            message="An unexpected error occurred",
            details=None,
        ),
    )


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    session_cookie=settings.session_cookie_name,
    https_only=settings.session_cookie_secure,
    same_site=settings.session_cookie_samesite_value,
    max_age=settings.session_max_age_seconds,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(documents_router, prefix=settings.api_prefix)


static_assets = settings.static_path / "assets"
if static_assets.exists():
    app.mount("/assets", StaticFiles(directory=static_assets), name="assets")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    index_file = settings.static_path / "index.html"
    if full_path.startswith("api/") or not index_file.exists():
        return JSONResponse(
            status_code=404,
            content=error_envelope(code="not_found", message="Not Found"),
        )
    return FileResponse(Path(index_file))
