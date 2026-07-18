from pathlib import Path
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# Load .env from the project root if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass  # dotenv optional; env vars can be set externally

from .config import settings

if settings.use_sqlite:
    engine = create_async_engine(
        "sqlite+aiosqlite:///./test.db",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_async_engine(
        settings.postgres_url,
        echo=False,
        future=True,
        connect_args={"ssl": False},
        poolclass=NullPool,
    )


async def init_db() -> None:
    """Create tables if they do not exist. Called on app startup."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
