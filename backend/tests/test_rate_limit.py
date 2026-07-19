import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db import engine
from backend.models import Tag, ContactEvent


@pytest.mark.asyncio
async def test_contact_rate_limiting(client, user_a):
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Rate Limited Item")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    tag_id = tag.id

    for i in range(5):
        response = await client.post(f"/t/{tag_id}/contact", json={
            "finder_phone": f"+1555000000{i}"
        })
        assert response.status_code == 200, f"Request {i + 1} failed"
        assert response.json()["message"] == "Message sent!"

    response = await client.post(f"/t/{tag_id}/contact", json={
        "finder_phone": "+15550000005"
    })
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]

    async with AsyncSession(engine) as session:
        result = await session.exec(
            select(ContactEvent)
            .where(ContactEvent.tag_id == tag_id)
            .order_by(ContactEvent.created_at)
        )
        events = result.all()
        assert len(events) == 6, "Expected exactly 6 logged contact events"
        for i in range(5):
            assert events[i].is_blocked is False, f"Event {i} should not be blocked"
        assert events[5].is_blocked is True, "The 6th event should be blocked"
