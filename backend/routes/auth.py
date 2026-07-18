from fastapi import APIRouter, HTTPException, status, Request, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid

from ..models import User, LoginData, SignupData
from ..db import engine
from ..utils.rate_limit import get_client_ip, check_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: Request, signup_data: SignupData):
    ip = get_client_ip(request)
    # signup rate limit: 3 attempts per IP per 60 minutes
    await check_rate_limit(
        key=f"ip:{ip}:signup",
        limit=3,
        window_minutes=60,
        error_msg="Too many signup attempts. Please try again later."
    )
    
    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.email == signup_data.email))
        existing_user = result.one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
            
        new_user = User(email=signup_data.email, phone_number=signup_data.phone_number)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return {"id": str(new_user.id), "email": new_user.email}


@router.post("/login")
async def login(request: Request, login_data: LoginData):
    ip = get_client_ip(request)
    # login rate limit: 5 attempts per IP per 15 minutes
    await check_rate_limit(
        key=f"ip:{ip}:login",
        limit=5,
        window_minutes=15,
        error_msg="Too many login attempts. Please try again after 15 minutes."
    )
    
    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.email == login_data.email))
        user = result.one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email")
            
        # Return the user ID as token (stub JWT simulation)
        return {"x_user_id": str(user.id)}
