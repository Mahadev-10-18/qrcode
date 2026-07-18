from fastapi import Header, HTTPException, status
import uuid
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from .db import engine
from .models import User


async def get_current_user(x_user_id: str = Header(...)):
    """Very simple stub auth: expects an `X-User-Id` header containing a UUID.
    Returns the User object from the DB or raises 401.
    In later phases this will be replaced by proper JWT validation.
    """
    try:
        user_uuid = uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user header")
    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.id == user_uuid))
        user = result.one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
