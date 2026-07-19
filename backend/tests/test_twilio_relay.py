import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db import engine
from backend.models import Tag, ContactEvent


@pytest.mark.asyncio
async def test_contact_stores_finder_info(client, user_a):
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="My lost keys")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    response = await client.post(f"/t/{tag.id}/contact", json={
        "finder_phone": "+15559876543",
        "message": "Found at Main St Coffee"
    })

    assert response.status_code == 200
    assert response.json()["message"] == "Message sent!"

    async with AsyncSession(engine) as session:
        result = await session.exec(select(ContactEvent).where(ContactEvent.tag_id == tag.id))
        event = result.first()
        assert event is not None
        assert event.finder_phone == "+15559876543"
        assert event.message == "Found at Main St Coffee"
        assert event.owner_phone == "1111111111"
        assert event.is_blocked is False


@pytest.mark.asyncio
async def test_contact_without_message(client, user_b):
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_b.id, label="My lost dog")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    response = await client.post(f"/t/{tag.id}/contact", json={
        "finder_phone": "+15559876543",
    })

    assert response.status_code == 200
    assert response.json()["message"] == "Message sent!"

    async with AsyncSession(engine) as session:
        result = await session.exec(select(ContactEvent).where(ContactEvent.tag_id == tag.id))
        event = result.first()
        assert event is not None
        assert event.finder_phone == "+15559876543"
        assert event.owner_phone == "2222222222"


@pytest.mark.asyncio
async def test_contact_invalid_phone(client, user_a):
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Invalid Phone")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    response = await client.post(f"/t/{tag.id}/contact", json={
        "finder_phone": "not-a-phone"
    })
    assert response.status_code == 422
