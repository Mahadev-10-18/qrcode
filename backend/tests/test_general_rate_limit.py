import pytest
from fastapi import status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime, timedelta

from backend.db import engine
from backend.models import RateLimitEvent, User, Tag

@pytest.mark.asyncio
async def test_login_rate_limiting_block_and_reset(client):
    email = "login_test@example.com"
    
    # 5 attempts should go through (either returning 401 because user not exists, but NOT 429)
    for _ in range(5):
        response = await client.post("/auth/login", json={"email": email})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED or response.status_code == 200
        
    # The 6th attempt must fail with 429
    response = await client.post("/auth/login", json={"email": email})
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Too many login attempts" in response.json()["detail"]

    # Confirm the limit resets after window (we shift RateLimitEvent timestamps to 16 mins ago)
    async with AsyncSession(engine) as session:
        result = await session.exec(select(RateLimitEvent))
        events = result.all()
        for event in events:
            event.created_at = datetime.utcnow() - timedelta(minutes=16)
            session.add(event)
        await session.commit()

    # The 7th attempt should go through (no longer 429)
    response = await client.post("/auth/login", json={"email": email})
    assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_signup_rate_limiting(client):
    import uuid
    suffix = uuid.uuid4().hex[:6]
    # signup limit is 3 per hour
    for i in range(3):
        response = await client.post("/auth/signup", json={"email": f"signup_{suffix}_{i}@example.com", "phone_number": "+15550000000"})
        assert response.status_code == status.HTTP_201_CREATED

    # 4th signup attempt must return 429
    response = await client.post("/auth/signup", json={"email": f"signup_{suffix}_4@example.com", "phone_number": "+15550000000"})
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Too many signup attempts" in response.json()["detail"]



@pytest.mark.asyncio
async def test_tag_creation_rate_limiting(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}
    
    # tag limit is 10 per hour
    for i in range(10):
        response = await client.post("/tags/", json={"label": f"tag_{i}"}, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED

    # 11th creation attempt must return 429
    response = await client.post("/tags/", json={"label": "tag_11"}, headers=headers)
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Tag creation limit exceeded" in response.json()["detail"]
