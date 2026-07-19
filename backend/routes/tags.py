from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
import io
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from uuid import UUID
from ..models import Tag, TagStatus, TagCreate, TagUpdate, ContactEvent
from ..auth_stub import get_current_user
from ..db import engine
from ..utils.rate_limit import get_client_ip, check_rate_limit
from ..utils.cache import cache
from ..utils.audit import log_audit

router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Tag)
async def create_tag(tag_in: TagCreate, request: Request, response: Response, current_user=Depends(get_current_user)):
    ip = get_client_ip(request)
    # tag creation rate limit: 10 attempts per IP per 60 minutes
    await check_rate_limit(
        key=f"ip:{ip}:tag_create",
        limit=10,
        window_minutes=60,
        error_msg="Tag creation limit exceeded. Please try again later."
    )

    # Free-tier enforcement: max 2 active tags
    if current_user.plan == "free":
        async with AsyncSession(engine) as session:
            result = await session.exec(
                select(Tag).where(
                    Tag.owner_id == current_user.id,
                    Tag.status == TagStatus.ACTIVE
                )
            )
            active_count = len(result.all())
            if active_count >= 2:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Free plan is limited to 2 active tags. Upgrade to create more."
                )

    async with AsyncSession(engine) as session:
        tag = Tag(label=tag_in.label, owner_id=current_user.id)
        session.add(tag)

        await session.commit()
        await session.refresh(tag)
        response.headers["X-Tag-Usage-Warning"] = "This code represents ONE item - create a separate tag per physical item, don't reuse this code elsewhere."

        await log_audit(
            action="tag.create",
            user_id=str(current_user.id),
            resource_type="tag",
            resource_id=str(tag.id),
            detail=f"Label: {tag.label}",
            ip_address=ip,
        )
        return tag


@router.get("/")
async def list_tags(
    request: Request,
    current_user=Depends(get_current_user),
    page: int = 1,
    per_page: int = 50,
):
    await check_rate_limit(
        key=f"user:{current_user.id}:list_tags",
        limit=60,
        window_minutes=60,
        error_msg="Too many requests. Try again later."
    )
    async with AsyncSession(engine) as session:
        stmt = select(Tag).where(Tag.owner_id == current_user.id).order_by(Tag.created_at.desc())
        total_stmt = select(Tag).where(Tag.owner_id == current_user.id)
        total_result = await session.exec(total_stmt)
        total = len(total_result.all())
        offset = (page - 1) * per_page
        result = await session.exec(stmt.offset(offset).limit(per_page))
        items = result.all()
        return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.patch("/{tag_id}", response_model=Tag)
async def update_tag(
    tag_id: UUID,
    tag_in: TagUpdate,
    request: Request,
    current_user=Depends(get_current_user),
):
    await check_rate_limit(
        key=f"user:{current_user.id}:update_tag",
        limit=30,
        window_minutes=60,
        error_msg="Too many tag updates. Try again later."
    )
    if tag_in.status and tag_in.status not in {TagStatus.ACTIVE, TagStatus.PAUSED, TagStatus.LOST_CONFIRMED}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid status")
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.id == tag_id))
        tag = result.one_or_none()
        if not tag or tag.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

        # Invalidate cache if status or label changes
        if tag_in.label is not None or tag_in.status is not None:
            await cache.delete(f"qr:{tag_id}")

        if tag_in.label is not None:
            tag.label = tag_in.label
        if tag_in.status is not None:
            tag.status = tag_in.status
        session.add(tag)
        await session.commit()
        await session.refresh(tag)

        await log_audit(
            action="tag.update",
            user_id=str(current_user.id),
            resource_type="tag",
            resource_id=str(tag_id),
            detail=f"status={tag_in.status}, label={tag_in.label}",
            ip_address=get_client_ip(request),
        )
        return tag


@router.get("/{tag_id}/qr")
async def get_tag_qr(tag_id: UUID, request: Request, current_user=Depends(get_current_user)):
    await check_rate_limit(
        key=f"user:{current_user.id}:qr_view",
        limit=60,
        window_minutes=60,
        error_msg="Too many QR view requests. Try again later."
    )
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.id == tag_id))
        tag = result.one_or_none()
        if not tag or tag.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

        cache_key = f"qr:{tag_id}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            return Response(
                content=cached_data,
                media_type="image/png",
                headers={
                    "X-Cache": "HIT",
                    "X-Tag-Usage-Warning": "This code represents ONE item - create a separate tag per physical item, don't reuse this code elsewhere."
                }
            )

        from ..config import settings
        url = f"{settings.effective_qr_url}/t/{tag.id}"
        qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_bytes = buf.getvalue()

        await cache.set(cache_key, qr_bytes)
        return Response(
            content=qr_bytes,
            media_type="image/png",
            headers={
                "X-Cache": "MISS",
                "X-Tag-Usage-Warning": "This code represents ONE item - create a separate tag per physical item, don't reuse this code elsewhere."
            }
        )


@router.get("/messages")
async def get_owner_messages(request: Request, current_user=Depends(get_current_user)):
    await check_rate_limit(
        key=f"user:{current_user.id}:messages",
        limit=30,
        window_minutes=60,
        error_msg="Too many requests. Try again later."
    )
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.owner_id == current_user.id))
        tags = result.all()
        tag_ids = [t.id for t in tags]

        if not tag_ids:
            return {"messages": []}

        contact_result = await session.exec(
            select(ContactEvent)
            .where(ContactEvent.tag_id.in_(tag_ids))
            .where(ContactEvent.is_blocked == False)
            .order_by(ContactEvent.created_at.desc())
        )
        events = contact_result.all()

        tag_map = {t.id: t.label for t in tags}
        messages = []
        for e in events:
            messages.append({
                "id": str(e.id),
                "tag_id": str(e.tag_id),
                "tag_label": tag_map.get(e.tag_id, "Unknown"),
                "finder_phone": e.finder_phone,
                "message": e.message or "",
                "created_at": e.created_at.isoformat() if e.created_at else None,
            })

        return {"messages": messages}
