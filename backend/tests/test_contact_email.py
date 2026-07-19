import pytest
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from backend.db import engine
from backend.models import Tag, ContactEvent


@pytest.mark.asyncio
async def test_contact_email_privacy_invariant(client, user_a, monkeypatch):
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Privacy Test Item")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    captured = {}

    async def mock_send_email(to, subject, html_body):
        captured["to"] = to
        captured["subject"] = subject
        captured["html_body"] = html_body

    monkeypatch.setattr("backend.routes.public.send_email", mock_send_email)

    finder_phone = "+15551112222"
    finder_message = "Found at the park near the bench"

    response = await client.post(f"/t/{tag.id}/contact", json={
        "finder_phone": finder_phone,
        "message": finder_message,
    })

    assert response.status_code == 200

    # No email should be sent for contact requests, as they go directly to the owner's dashboard inbox
    assert not captured

    async with AsyncSession(engine) as session:
        result = await session.exec(select(ContactEvent).where(ContactEvent.tag_id == tag.id))
        event = result.first()
        assert event is not None
        assert event.finder_phone == finder_phone
        assert event.message == finder_message
