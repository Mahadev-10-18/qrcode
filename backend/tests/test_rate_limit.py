import pytest
import os
from unittest.mock import patch
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db import engine
from backend.models import Tag, ContactEvent


@pytest.mark.asyncio
async def test_contact_rate_limiting(client, user_a):
    # Setup test credentials in environment
    os.environ["TWILIO_ACCOUNT_SID"] = "AC" + "0" * 32
    os.environ["TWILIO_AUTH_TOKEN"] = "0" * 32
    os.environ["TWILIO_PROXY_SERVICE_SID"] = "KS" + "0" * 32

    # Create a tag for user_a
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Rate Limited Item")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    tag_id = tag.id

    with patch("backend.routes.public.Client") as MockClient:
        mock_instance = MockClient.return_value
        mock_proxy = mock_instance.proxy.v1.services.return_value
        mock_sessions = mock_proxy.sessions
        mock_session_obj = mock_sessions.create.return_value
        mock_session_obj.sid = "KC12345678901234567890123456789012"

        # 5 requests should all succeed
        for i in range(5):
            response = await client.post(f"/t/{tag_id}/contact", json={
                "method": "text",
                "finder_phone": f"+1555000000{i}"
            })
            assert response.status_code == 200, f"Request {i + 1} failed"
            assert response.json()["message"] == "Contact request recorded."

        # 6th request should fail with 429 Too Many Requests
        response = await client.post(f"/t/{tag_id}/contact", json={
            "method": "text",
            "finder_phone": "+15550000005"
        })
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]

    # Verify DB logs
    async with AsyncSession(engine) as session:
        result = await session.exec(
            select(ContactEvent)
            .where(ContactEvent.tag_id == tag_id)
            .order_index_by(ContactEvent.created_at) if hasattr(ContactEvent, "order_index_by")
            else select(ContactEvent).where(ContactEvent.tag_id == tag_id).order_by(ContactEvent.created_at)
        )
        events = result.all()
        assert len(events) == 6, "Expected exactly 6 logged contact events"
        for i in range(5):
            assert events[i].is_blocked is False, f"Event {i} should not be blocked"
        assert events[5].is_blocked is True, "The 6th event should be blocked"
