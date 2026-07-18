import pytest
import os
from unittest.mock import patch
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.db import engine
from backend.models import Tag, User, ContactEvent

@pytest.mark.asyncio
async def test_contact_creates_twilio_session(client, user_a):
    # Setup test credentials in environment
    os.environ["TWILIO_ACCOUNT_SID"] = "AC" + "0" * 32
    os.environ["TWILIO_AUTH_TOKEN"] = "0" * 32
    os.environ["TWILIO_PROXY_SERVICE_SID"] = "KS" + "0" * 32
    
    # Create a tag for user_a
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="My lost keys")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)
        
    tag_id = tag.id
    
    # Mock to simulate Twilio API
    with patch("backend.routes.public.Client") as MockClient:
        mock_instance = MockClient.return_value
        mock_proxy = mock_instance.proxy.v1.services.return_value
        mock_sessions = mock_proxy.sessions
        
        # Mock session creation
        mock_session_obj = mock_sessions.create.return_value
        mock_session_obj.sid = "KC12345678901234567890123456789012"
        
        response = await client.post(f"/t/{tag_id}/contact", json={
            "method": "text",
            "finder_phone": "+15559876543"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Contact request recorded."
        assert data["relay_session_id"] == "KC12345678901234567890123456789012"
        
        # Verify participants were created
        mock_participants = mock_sessions.return_value.participants
        assert mock_participants.create.call_count == 2
        calls = mock_participants.create.call_args_list
        identifiers = [call.kwargs.get("identifier") for call in calls]
        
        # user_a phone number in conftest.py is "1111111111"
        assert "1111111111" in identifiers
        assert "+15559876543" in identifiers

    # Verify DB state
    async with AsyncSession(engine) as session:
        result = await session.exec(select(ContactEvent).where(ContactEvent.tag_id == tag_id))
        event = result.first()
        assert event is not None
        assert event.relay_session_id == "KC12345678901234567890123456789012"
        assert event.finder_contact_method == "text"


@pytest.mark.asyncio
async def test_contact_creates_twilio_voice_session(client, user_b):
    # Setup test credentials in environment
    os.environ["TWILIO_ACCOUNT_SID"] = "AC" + "0" * 32
    os.environ["TWILIO_AUTH_TOKEN"] = "0" * 32
    os.environ["TWILIO_PROXY_SERVICE_SID"] = "KS" + "0" * 32
    
    # Create a tag for user_b
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_b.id, label="My lost dog")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)
        
    tag_id = tag.id
    
    # Mock to simulate Twilio API
    with patch("backend.routes.public.Client") as MockClient:
        mock_instance = MockClient.return_value
        mock_proxy = mock_instance.proxy.v1.services.return_value
        mock_sessions = mock_proxy.sessions
        
        # Mock session creation
        mock_session_obj = mock_sessions.create.return_value
        mock_session_obj.sid = "KC99999999999999999999999999999999"
        
        response = await client.post(f"/t/{tag_id}/contact", json={
            "method": "call",
            "finder_phone": "+15559876543"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Contact request recorded."
        assert data["relay_session_id"] == "KC99999999999999999999999999999999"
        
        # Verify participants were created
        mock_participants = mock_sessions.return_value.participants
        assert mock_participants.create.call_count == 2
        calls = mock_participants.create.call_args_list
        identifiers = [call.kwargs.get("identifier") for call in calls]
        
        # user_b phone number in conftest.py is "2222222222"
        assert "2222222222" in identifiers
        assert "+15559876543" in identifiers

    # Verify DB state
    async with AsyncSession(engine) as session:
        result = await session.exec(select(ContactEvent).where(ContactEvent.tag_id == tag_id))
        event = result.first()
        assert event is not None
        assert event.relay_session_id == "KC99999999999999999999999999999999"
        assert event.finder_contact_method == "call"


@pytest.mark.asyncio
async def test_contact_invalid_method(client, user_a):
    async with AsyncSession(engine) as session:
        tag = Tag(owner_id=user_a.id, label="Invalid Method Item")
        session.add(tag)
        await session.commit()
        await session.refresh(tag)
        
    response = await client.post(f"/t/{tag.id}/contact", json={
        "method": "email",
        "finder_phone": "+15559876543"
    })
    assert response.status_code == 400
    assert "Invalid contact method" in response.json()["detail"]

