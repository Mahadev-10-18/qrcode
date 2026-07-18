from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .routes import tags, public, auth, jobs
from .routers import tags_pdf
from .db import init_db
from .utils.logging_setup import setup_logging
from .utils.sentry import init_sentry

setup_logging()
init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .utils.cache import cache
    await cache.connect()
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


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


@app.get("/debug-sentry")
async def debug_sentry():
    raise RuntimeError("Test Sentry exception — safe to ignore")


app.include_router(tags.router)
app.include_router(public.router)
app.include_router(tags_pdf.router)
app.include_router(auth.router)
app.include_router(jobs.router)
