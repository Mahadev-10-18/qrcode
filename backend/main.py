import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from .routes import tags, public, auth, jobs, google_auth
from .routers import tags_pdf
from .db import ensure_db_initialized
from .utils.logging_setup import setup_logging
from .utils.sentry import init_sentry
from .utils.security import SecurityHeadersMiddleware, RequestSizeLimitMiddleware, TimeoutMiddleware
from .config import settings

setup_logging()
init_sentry()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .utils.cache import cache
    await cache.connect()
    await ensure_db_initialized()
    yield


app = FastAPI(lifespan=lifespan)

allowed_origins = [settings.frontend_url] if settings.frontend_url else []
if settings.is_production and not allowed_origins:
    raise RuntimeError("FRONTEND_URL must be set in production to restrict allowed CORS origins.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=100_000)
app.add_middleware(TimeoutMiddleware, timeout_seconds=30)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    logger.warning(
        "Validation error for %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    error_payload = [
        {"loc": err.get("loc"), "type": err.get("type"), "msg": err.get("msg")}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation failed.", "errors": error_payload},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc: StarletteHTTPException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    logger.error(
        "Unhandled exception processing request %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if settings.secret_key == "changeme":
    logger.warning("Using default SECRET_KEY. Set SECRET_KEY in production to protect JWT tokens.")
if settings.is_production and settings.secret_key in {"", "changeme"}:
    raise RuntimeError("SECRET_KEY must be set to a strong value in production.")


@app.get("/health")
async def health():
    from .db import engine
    from .utils.cache import cache

    db_up = False
    cache_up = False

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_up = True
    except Exception:
        pass

    try:
        if cache.redis_client:
            await cache.redis_client.ping()
        cache_up = True
    except Exception:
        pass

    if db_up and cache_up:
        return {"status": "ok", "database": "up", "cache": "up"}

    body = {"status": "unhealthy"}
    if not db_up:
        body["database"] = "down"
    if not cache_up:
        body["cache"] = "down"
    return JSONResponse(content=body, status_code=503)


if not settings.is_production:

    @app.get("/debug-sentry")
    async def debug_sentry():
        raise RuntimeError("Sentry debug endpoint triggered")


app.include_router(tags.router)
app.include_router(public.router)
app.include_router(tags_pdf.router)
app.include_router(auth.router)
app.include_router(google_auth.router)
app.include_router(jobs.router)
