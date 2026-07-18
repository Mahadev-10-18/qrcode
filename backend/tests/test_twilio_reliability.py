import pytest
import os
import logging
from unittest.mock import patch
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from twilio.base.exceptions import TwilioRestException

from backend.db import engine
from backend.models import Tag, ContactEvent


@pytest.mark.asyncio
async def test_transient_failure_and_retry_success(client, user_a):
    os.environ["TWILIO_ACCOUNT_SID"] = "AC" + "0" * 32
    os.environ["TWILIO_AUTH_TOKEN"] = "0" * 32
    os.environ["TWILIO_PROXY_SERVICE_SID"] = "KS" + "0" * 32

    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Keys")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    # Mock Twilio Client
    with patch("backend.routes.public.Client") as MockClient, \
            patch("asyncio.sleep", return_value=None) as mock_sleep:

        mock_instance = MockClient.return_value
        mock_proxy = mock_instance.proxy.v1.services.return_value
        mock_sessions = mock_proxy.sessions

        mock_session_obj = mock_sessions.create.return_value
        mock_session_obj.sid = "KC_SUCCESS"

        # 2 failures followed by 1 success
        err = TwilioRestException(status=500, uri="/Sessions", msg="Transient Server Error")
        mock_sessions.create.side_effect = [err, err, mock_session_obj]

        response = await client.post(f"/t/{tag.id}/contact", json={
            "method": "text",
            "finder_phone": "+15559876543"
        })

        assert response.status_code == 200
        assert response.json()["relay_session_id"] == "KC_SUCCESS"
        assert mock_sessions.create.call_count == 3
        assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_permanent_failure_no_retries(client, user_a):
    os.environ["TWILIO_ACCOUNT_SID"] = "AC" + "0" * 32
    os.environ["TWILIO_AUTH_TOKEN"] = "0" * 32
    os.environ["TWILIO_PROXY_SERVICE_SID"] = "KS" + "0" * 32

    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Keys")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    with patch("backend.routes.public.Client") as MockClient, \
            patch("asyncio.sleep", return_value=None) as mock_sleep:

        mock_instance = MockClient.return_value
        mock_proxy = mock_instance.proxy.v1.services.return_value
        mock_sessions = mock_proxy.sessions

        # Raise 400 Bad Request (permanent failure)
        err = TwilioRestException(status=400, uri="/Sessions", msg="Permanent client error")
        mock_sessions.create.side_effect = err

        response = await client.post(f"/t/{tag.id}/contact", json={
            "method": "text",
            "finder_phone": "+15559876543"
        })

        # Should raise 503 since retries immediately abort and fail gracefully
        assert response.status_code == 503
        assert mock_sessions.create.call_count == 1
        assert mock_sleep.call_count == 0


@pytest.mark.asyncio
async def test_log_scrubbing_no_phone_numbers(client, user_a, caplog):
    os.environ["TWILIO_ACCOUNT_SID"] = "AC" + "0" * 32
    os.environ["TWILIO_AUTH_TOKEN"] = "0" * 32
    os.environ["TWILIO_PROXY_SERVICE_SID"] = "KS" + "0" * 32

    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Keys")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    # Force a permanent failure, print logs during request
    with patch("backend.routes.public.Client") as MockClient:
        mock_instance = MockClient.return_value
        mock_proxy = mock_instance.proxy.v1.services.return_value
        mock_sessions = mock_proxy.sessions
        err = TwilioRestException(status=400, uri="/Sessions", msg="Invalid phone +15559876543 or 1111111111")
        mock_sessions.create.side_effect = err

        caplog.set_level(logging.WARNING)
        await client.post(f"/t/{tag.id}/contact", json={
            "method": "text",
            "finder_phone": "+15559876543"
        })

    # Verify that phone numbers are not present in logs formatted by our JsonFormatter
    from backend.utils.logging_setup import JsonFormatter
    formatter = JsonFormatter()

    formatted_logs = "\n".join(formatter.format(record) for record in caplog.records)

    assert "1111111111" not in formatted_logs
    assert "5559876543" not in formatted_logs
    # Check that they were scrubbed
    assert "[SCRUBBED_PHONE]" in formatted_logs


@pytest.mark.asyncio
async def test_outage_graceful_degradation(client, user_a):
    os.environ["TWILIO_ACCOUNT_SID"] = "AC" + "0" * 32
    os.environ["TWILIO_AUTH_TOKEN"] = "0" * 32
    os.environ["TWILIO_PROXY_SERVICE_SID"] = "KS" + "0" * 32

    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Keys")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

    with patch("backend.routes.public.Client") as MockClient, \
            patch("asyncio.sleep", return_value=None):

        mock_instance = MockClient.return_value
        mock_proxy = mock_instance.proxy.v1.services.return_value
        mock_sessions = mock_proxy.sessions

        # Constantly failing transiently (500)
        err = TwilioRestException(status=500, uri="/Sessions", msg="Server unavailable")
        mock_sessions.create.side_effect = err

        response = await client.post(f"/t/{tag.id}/contact", json={
            "method": "text",
            "finder_phone": "+15559876543"
        })

        assert response.status_code == 503
        assert "couldn't reach the owner right now, try again shortly" in response.json()["detail"]
        assert mock_sessions.create.call_count == 3

        # Verify ContactEvent created and marked failed in DB
        async with AsyncSession(engine) as session:
            result = await session.exec(
                select(ContactEvent)
                .where(ContactEvent.tag_id == tag.id)
                .order_by(ContactEvent.created_at.desc())
            )
            event = result.first()
            assert event is not None
            assert event.is_failed is True
            assert event.relay_session_id is None
