import logging
import uuid
from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from ..models import Tag, TagStatus, ContactEvent, ContactRequest, User
from ..db import engine
from ..utils.audit import log_audit
from ..utils.rate_limit import check_rate_limit, get_client_ip
from ..utils.email import send_email, build_contact_alert_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/t", tags=["public"])


@router.get("/{tag_id}")
async def public_tag_view(tag_id: uuid.UUID):
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.id == tag_id))
        tag = result.one_or_none()
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
        if tag.status != TagStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
        return {"label": tag.label, "cta": "Contact the owner"}


@router.post("/{tag_id}/contact")
async def public_contact(tag_id: uuid.UUID, contact_req: ContactRequest, request: Request, background_tasks: BackgroundTasks):
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.id == tag_id))
        tag = result.one_or_none()
        if not tag or tag.status != TagStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

        user_result = await session.exec(select(User).where(User.id == tag.owner_id))
        owner = user_result.one_or_none()
        if not owner or (not owner.phone_number and not owner.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner cannot be contacted")

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
                    finder_contact_method="text",
                    is_blocked=True,
                    finder_phone=contact_req.finder_phone,
                    owner_phone=owner.phone_number,
                    message=contact_req.message,
                )
                session.add(blocked_event)
                await session.commit()
            raise e

        tag_id_str = str(tag.id)
        tag_label = tag.label
        owner_email = owner.email
        finder_phone = contact_req.finder_phone
        finder_message = contact_req.message

        event = ContactEvent(
            tag_id=tag.id,
            finder_contact_method="text",
            finder_phone=contact_req.finder_phone,
            owner_phone=owner.phone_number,
            message=contact_req.message,
        )
        session.add(event)
        await session.commit()

        await log_audit(
            action="contact.request",
            resource_type="tag",
            resource_id=tag_id_str,
            detail="contact request sent",
            ip_address=get_client_ip(request),
        )

    return JSONResponse(content={"message": "Message sent!"})
