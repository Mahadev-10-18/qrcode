import asyncio
from pathlib import Path
from sqlmodel import SQLModel
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# Load .env from the project root if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass  # dotenv optional; env vars can be set externally

from .config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_DB_PATH = BASE_DIR / "test.db"

if settings.use_sqlite:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{SQLITE_DB_PATH.as_posix()}",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
else:
    use_null_pool = settings.app_env.lower() == "test"
    engine_kwargs = {
        "url": settings.postgres_url,
        "echo": False,
        "future": True,
        "connect_args": {"ssl": True if settings.database_ssl else False},
    }
    if use_null_pool:
        engine_kwargs["poolclass"] = NullPool
    engine = create_async_engine(**engine_kwargs)


_db_initialized = False
_db_init_lock = asyncio.Lock()


def _validate_schema(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = inspector.get_table_names()
    missing_tables = [name for name in SQLModel.metadata.tables if name not in existing_tables]
    if missing_tables:
        raise RuntimeError(
            "Database schema is not initialized or migrated. "
            f"Missing tables: {', '.join(missing_tables)}. "
            "Run `python migrate.py` or set ENABLE_DB_AUTO_CREATE=True for local development."
        )


def _auto_migrate(sync_conn) -> None:
    inspector = inspect(sync_conn)
    existing_tables = inspector.get_table_names()

    if "auditlog" not in existing_tables:
        sync_conn.execute(text("""
            CREATE TABLE IF NOT EXISTS auditlog (
                id UUID PRIMARY KEY,
                user_id VARCHAR,
                action VARCHAR NOT NULL,
                resource_type VARCHAR,
                resource_id VARCHAR,
                detail VARCHAR,
                ip_address VARCHAR,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
            )
        """))
        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_auditlog_user_id ON auditlog (user_id)"))
        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_auditlog_action ON auditlog (action)"))

    has_reset_token = False
    if "user" in existing_tables:
        cols = [c["name"] for c in inspector.get_columns("user")]
        if "email_verified" not in cols:
            sync_conn.execute(text("ALTER TABLE \"user\" ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE"))
        if "verification_token" not in cols:
            sync_conn.execute(text("ALTER TABLE \"user\" ADD COLUMN verification_token VARCHAR"))
        if "reset_token" not in cols:
            sync_conn.execute(text("ALTER TABLE \"user\" ADD COLUMN reset_token VARCHAR"))
            has_reset_token = True
        if "reset_token_expires" not in cols:
            sync_conn.execute(text("ALTER TABLE \"user\" ADD COLUMN reset_token_expires TIMESTAMP WITHOUT TIME ZONE"))

    if has_reset_token:
        sync_conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_reset_token ON \"user\" (reset_token)"))

    if "contactevent" in existing_tables:
        cols = [c["name"] for c in inspector.get_columns("contactevent")]
        if "finder_phone" not in cols:
            sync_conn.execute(text("ALTER TABLE contactevent ADD COLUMN finder_phone VARCHAR"))
        if "owner_phone" not in cols:
            sync_conn.execute(text("ALTER TABLE contactevent ADD COLUMN owner_phone VARCHAR"))
        if "message" not in cols:
            sync_conn.execute(text("ALTER TABLE contactevent ADD COLUMN message VARCHAR"))


async def init_db() -> None:
    """Validate or initialize database schema when the app starts."""
    async with engine.begin() as conn:
        if settings.enable_db_autocreate:
            await conn.run_sync(SQLModel.metadata.create_all)
            await conn.run_sync(_auto_migrate)
        else:
            await conn.run_sync(_validate_schema)


async def ensure_db_initialized() -> None:
    global _db_initialized
    if _db_initialized:
        return
    async with _db_init_lock:
        if _db_initialized:
            return
        await init_db()
        _db_initialized = True
