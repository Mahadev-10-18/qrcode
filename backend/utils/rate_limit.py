from datetime import datetime, timedelta, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
from fastapi import Request, HTTPException, status
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db import engine
from ..models import RateLimitEvent
from ..utils.cache import cache


def get_client_ip(request: Request) -> str:
    if not request:
        return "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit(key: str, limit: int, window_minutes: int, error_msg: str = "Rate limit exceeded.") -> None:
    # Use Redis for rate limiting when available (horizontally scalable)
    if cache.redis_client:
        await _check_rate_limit_redis(key, limit, window_minutes, error_msg)
    else:
        await _check_rate_limit_db(key, limit, window_minutes, error_msg)


async def _check_rate_limit_redis(key: str, limit: int, window_minutes: int, error_msg: str) -> None:
    redis = cache.redis_client
    window_seconds = window_minutes * 60
    now = int(_utcnow().timestamp())
    window_key = f"rl:{key}:{now // window_seconds}"

    pipe = redis.pipeline()
    pipe.incr(window_key)
    pipe.expire(window_key, window_seconds + 60)
    count, _ = await pipe.execute()

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error_msg
        )


async def _check_rate_limit_db(key: str, limit: int, window_minutes: int, error_msg: str) -> None:
    async with AsyncSession(engine) as session:
        cutoff = _utcnow() - timedelta(minutes=window_minutes)
        stmt = select(func.count(RateLimitEvent.id)).where(
            RateLimitEvent.key == key,
            RateLimitEvent.created_at >= cutoff
        )
        res = await session.exec(stmt)
        count = res.one()

        event = RateLimitEvent(key=key)
        session.add(event)
        await session.commit()

        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=error_msg
            )
