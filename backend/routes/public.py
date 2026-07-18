from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import uuid
import os
from ..models import Tag, TagStatus, ContactEvent, ContactRequest, User
from ..db import engine
from twilio.rest import Client
import os

router = APIRouter(prefix="/t", tags=["public"])

@router.get("/{tag_id}")
async def public_tag_view(tag_id: uuid.UUID):
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.id == tag_id))
        tag = result.one_or_none()
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
        if tag.status != TagStatus.ACTIVE:
            # hide paused or lost tags from the public
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
        return {"label": tag.label, "cta": "Contact the owner"}

import logging
import asyncio
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

async def execute_twilio_with_retry(client, proxy_service_sid, tag_id, owner_phone, finder_phone) -> str:
    max_attempts = 3
    backoff_delays = [1, 2, 4]
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"Twilio relay creation attempt {attempt + 1} for tag {tag_id}")
            
            # Wrap blocking Twilio REST calls in asyncio.to_thread
            proxy_session = await asyncio.to_thread(
                client.proxy.v1.services(proxy_service_sid).sessions.create,
                unique_name=f"Relay_{tag_id}_{uuid.uuid4().hex[:8]}"
            )
            
            await asyncio.to_thread(
                client.proxy.v1.services(proxy_service_sid).sessions(proxy_session.sid).participants.create,
                identifier=owner_phone
            )
            
            await asyncio.to_thread(
                client.proxy.v1.services(proxy_service_sid).sessions(proxy_session.sid).participants.create,
                identifier=finder_phone
            )
            
            logger.info(f"Twilio relay session {proxy_session.sid} successfully created")
            return proxy_session.sid
            
        except Exception as e:
            is_transient = True
            if isinstance(e, TwilioRestException):
                # 4xx exceptions (except 429) are permanent failures (unauthorized, invalid numbers, etc.)
                if 400 <= e.status < 500 and e.status != 429:
                    is_transient = False
                    
            logger.warning(
                f"Twilio relay attempt {attempt + 1} failed (transient: {is_transient}): {str(e)}"
            )
            
            if not is_transient or attempt == max_attempts - 1:
                raise e
                
            await asyncio.sleep(backoff_delays[attempt])


@router.post("/{tag_id}/contact")
async def public_contact(tag_id: uuid.UUID, contact_req: ContactRequest):
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.id == tag_id))
        tag = result.one_or_none()
        if not tag or tag.status != TagStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
            
        if contact_req.method not in ("text", "call"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact method. Choose 'text' or 'call'.")
            
        user_result = await session.exec(select(User).where(User.id == tag.owner_id))
        owner = user_result.one_or_none()
        if not owner or not owner.phone_number:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner cannot be contacted")
            
        # Rate limit check: 5 attempts per tag per rolling hour
        from ..utils.rate_limit import check_rate_limit
        try:
            await check_rate_limit(
                key=f"tag:{tag.id}:contact",
                limit=5,
                window_minutes=60,
                error_msg="Rate limit exceeded. Max 5 contacts per hour."
            )
        except HTTPException as e:
            if e.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                blocked_event = ContactEvent(
                    tag_id=tag.id,
                    finder_contact_method=contact_req.method,
                    is_blocked=True
                )
                session.add(blocked_event)
                await session.commit()
            raise e


            
        from ..config import settings
        
        account_sid = settings.twilio_account_sid
        auth_token = settings.twilio_auth_token
        proxy_service_sid = settings.twilio_proxy_service_sid

        client = Client(account_sid, auth_token)
        relay_session_sid = None
        is_failed = False
        
        logger.info(f"Initiated contact request for tag {tag.id}")
        
        try:
            relay_session_sid = await execute_twilio_with_retry(
                client=client,
                proxy_service_sid=proxy_service_sid,
                tag_id=tag.id,
                owner_phone=owner.phone_number,
                finder_phone=contact_req.finder_phone
            )
        except Exception as e:
            # Retries exhausted or failed permanently
            logger.error(f"Twilio relay service exhausted or failed permanently for tag {tag.id}: {str(e)}", exc_info=True)
            is_failed = True
            
        event = ContactEvent(
            tag_id=tag.id, 
            finder_contact_method=contact_req.method,
            relay_session_id=relay_session_sid,
            is_failed=is_failed
        )
        session.add(event)
        await session.commit()
        
        if is_failed:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="couldn't reach the owner right now, try again shortly"
            )
            
        return JSONResponse(content={"message": "Contact request recorded.", "relay_session_id": relay_session_sid})

