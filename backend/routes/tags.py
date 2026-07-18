from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
import io
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from uuid import UUID
from ..models import Tag, TagStatus, TagCreate, TagUpdate
from ..auth_stub import get_current_user
from ..db import engine
from ..utils.rate_limit import get_client_ip, check_rate_limit
from ..utils.cache import cache

router = APIRouter(prefix="/tags", tags=["tags"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Tag)
async def create_tag(tag_in: TagCreate, request: Request, current_user=Depends(get_current_user)):
    ip = get_client_ip(request)
    # tag creation rate limit: 10 attempts per IP per 60 minutes
    await check_rate_limit(
        key=f"ip:{ip}:tag_create",
        limit=10,
        window_minutes=60,
        error_msg="Tag creation limit exceeded. Please try again later."
    )
    async with AsyncSession(engine) as session:
        tag = Tag(label=tag_in.label, owner_id=current_user.id)
        session.add(tag)

        await session.commit()
        await session.refresh(tag)
        return tag


@router.get("/", response_model=list[Tag])
async def list_tags(current_user=Depends(get_current_user)):
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.owner_id == current_user.id))
        return result.all()


@router.patch("/{tag_id}", response_model=Tag)
async def update_tag(
    tag_id: UUID,
    tag_in: TagUpdate,
    current_user=Depends(get_current_user),
):
    if tag_in.status and tag_in.status not in {TagStatus.ACTIVE, TagStatus.PAUSED, TagStatus.LOST_CONFIRMED}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid status")
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
        return tag


@router.get("/{tag_id}/qr")
async def get_tag_qr(tag_id: UUID, current_user=Depends(get_current_user)):
    async with AsyncSession(engine) as session:
        result = await session.exec(select(Tag).where(Tag.id == tag_id))
        tag = result.one_or_none()
        if not tag or tag.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

        cache_key = f"qr:{tag_id}"
        cached_data = await cache.get(cache_key)
        if cached_data:
            return Response(content=cached_data, media_type="image/png", headers={"X-Cache": "HIT"})

        from ..config import settings
        domain = settings.app_domain

        url = f"{domain}/t/{tag.id}"
        qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_bytes = buf.getvalue()

        await cache.set(cache_key, qr_bytes)
        return Response(content=qr_bytes, media_type="image/png", headers={"X-Cache": "MISS"})
