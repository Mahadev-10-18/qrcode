import datetime
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db import engine
from ..models import RateLimitEvent

def get_client_ip(request: Request) -> str:
    if not request:
        return "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def check_rate_limit(key: str, limit: int, window_minutes: int, error_msg: str = "Rate limit exceeded.") -> None:
    async with AsyncSession(engine) as session:
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        stmt = select(func.count(RateLimitEvent.id)).where(
            RateLimitEvent.key == key,
            RateLimitEvent.created_at >= cutoff
        )
        res = await session.exec(stmt)
        count = res.one()
        
        # Log this attempt
        event = RateLimitEvent(key=key)
        session.add(event)
        await session.commit()
        
        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg
            )
