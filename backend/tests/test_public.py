import uuid
import pytest
from fastapi import status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db import engine
from backend.models import Tag, TagStatus


@pytest.mark.asyncio
async def test_public_tag_view_no_pii(client, user_a, auth_headers):
    headers = auth_headers(user_a)
    resp = await client.post("/tags/", json={"label": "MyItem"}, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED
    tag_id = resp.json()["id"]

    public_resp = await client.get(f"/t/{tag_id}")
    assert public_resp.status_code == status.HTTP_200_OK
    data = public_resp.json()
    assert data["label"] == "MyItem"
    assert "cta" in data

    # PII must not appear anywhere in the raw response body
    raw = public_resp.text
    assert user_a.email not in raw, "email leaked in public response"
    assert user_a.phone_number not in raw, "phone_number leaked in public response"
    assert str(user_a.id) not in raw, "user id leaked in public response"


@pytest.mark.asyncio
async def test_public_tag_404_for_paused(client, user_a, auth_headers):
    headers = auth_headers(user_a)
    resp = await client.post("/tags/", json={"label": "PausedItem"}, headers=headers)
    assert resp.status_code == status.HTTP_201_CREATED
    tag_id = resp.json()["id"]

    # Directly flip status in DB
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.id == uuid.UUID(tag_id)))
        tag = result.one()
        tag.status = TagStatus.PAUSED
        session.add(tag)
        await session.commit()

    public_resp = await client.get(f"/t/{tag_id}")
    assert public_resp.status_code == status.HTTP_404_NOT_FOUND
