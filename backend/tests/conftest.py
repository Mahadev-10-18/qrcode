"""
conftest.py — shared fixtures for all backend tests.
"""
import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC" + "0" * 32)
os.environ.setdefault("TWILIO_AUTH_TOKEN", "0" * 32)
os.environ.setdefault("TWILIO_PROXY_SERVICE_SID", "KS" + "0" * 32)
os.environ.setdefault("ENABLE_DB_AUTO_CREATE", "True")
os.environ["SMTP_HOST"] = ""

from sqlalchemy import delete
from backend.models import User, RateLimitEvent
from backend.db import engine, ensure_db_initialized
from backend.main import app
from backend.auth_stub import create_access_token
from sqlmodel.ext.asyncio.session import AsyncSession
from httpx import AsyncClient, ASGITransport
import pytest_asyncio
import pytest
import uuid


@pytest.fixture
def auth_headers():
    def _auth_headers(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}

    return _auth_headers


pytest_plugins = ["pytest_asyncio"]


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test",
        headers={"X-Requested-With": "XMLHttpRequest"}
    ) as ac:
        yield ac


async def _make_user(email: str, phone: str, plan: str = "free") -> User:
    async with AsyncSession(engine) as session:
        u = User(email=email, phone_number=phone, plan=plan)
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u


@pytest_asyncio.fixture
async def user_a():
    return await _make_user(f"a_{uuid.uuid4().hex[:6]}@example.com", "1111111111")


@pytest_asyncio.fixture
async def user_b():
    return await _make_user(f"b_{uuid.uuid4().hex[:6]}@example.com", "2222222222")


@pytest_asyncio.fixture
async def paid_user():
    return await _make_user(f"paid_{uuid.uuid4().hex[:6]}@example.com", "3333333333", "paid")


@pytest_asyncio.fixture(autouse=True)
async def init_database():
    os.environ.setdefault("APP_ENV", "test")
    await ensure_db_initialized()


@pytest_asyncio.fixture(autouse=True)
async def clear_rate_limits(init_database):
    async with AsyncSession(engine) as session:
        await session.exec(delete(RateLimitEvent))
        await session.commit()

