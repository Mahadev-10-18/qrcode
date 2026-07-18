"""
conftest.py — shared fixtures for all backend tests.
"""
import os
# Set default dummy environment variables for tests before any backend modules are imported
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC" + "0" * 32)
os.environ.setdefault("TWILIO_AUTH_TOKEN", "0" * 32)
os.environ.setdefault("TWILIO_PROXY_SERVICE_SID", "KS" + "0" * 32)

import uuid
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.main import app

from backend.db import engine
from backend.models import User

pytest_plugins = ["pytest_asyncio"]


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


async def _make_user(email: str, phone: str) -> User:
    async with AsyncSession(engine) as session:
        u = User(email=email, phone_number=phone)
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


from sqlalchemy import text

@pytest_asyncio.fixture(autouse=True)
async def clear_rate_limits():
    async with AsyncSession(engine) as session:
        await session.execute(text("DELETE FROM ratelimitevent"))
        await session.commit()

