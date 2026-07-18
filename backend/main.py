from .db import init_db
from .routers import tags_pdf
from .routes import tags, public, auth, jobs
from fastapi import FastAPI

from .utils.logging_setup import setup_logging
setup_logging()

# Import routers from correct modules


app = FastAPI()

# Health endpoint


@app.get("/health")
async def health():
    return {"status": "ok"}

# Include routers
app.include_router(tags.router)
app.include_router(public.router)
app.include_router(tags_pdf.router)
app.include_router(auth.router)
app.include_router(jobs.router)


# Initialize DB on startup
@app.on_event("startup")
async def on_startup():
    from .utils.cache import cache
    await cache.connect()
    await init_db()
