import pytest
import logging
from datetime import datetime, timedelta, timezone
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db import engine
from backend.models import Tag, ContactEvent, RateLimitEvent


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_log_scrubbing_no_phone_numbers(client, user_a, caplog):
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Keys")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    caplog.set_level(logging.INFO)
    await client.post(f"/t/{tag.id}/contact", json={
        "finder_phone": "+15559876543",
        "message": "Found them"
    })

    from backend.utils.logging_setup import JsonFormatter
    formatter = JsonFormatter()

    formatted_logs = "\n".join(formatter.format(record) for record in caplog.records)

    assert "15559876543" not in formatted_logs
    assert "1111111111" not in formatted_logs


@pytest.mark.asyncio
async def test_outage_graceful_degradation(client, user_a):
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Keys")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    response = await client.post(f"/t/{tag.id}/contact", json={
        "finder_phone": "+15559876543",
        "message": "hello"
    })

    assert response.status_code == 200

    async with AsyncSession(engine) as session:
        result = await session.exec(
            select(ContactEvent)
            .where(ContactEvent.tag_id == tag.id)
            .order_by(ContactEvent.created_at.desc())
        )
        event = result.first()
        assert event is not None
        assert event.is_blocked is False
