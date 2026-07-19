import secrets
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import JSONResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from jose import JWTError, jwt
import uuid

from ..models import User, LoginData, SignupData, ForgotPasswordData, ResetPasswordData
from ..db import engine
from ..utils.rate_limit import get_client_ip, check_rate_limit
from ..utils.audit import log_audit
from ..auth_stub import (
    get_current_user,
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
)
from ..config import settings
from ..utils.email import send_email, build_verification_email, build_password_reset_email

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(request: Request, signup_data: SignupData):
    ip = get_client_ip(request)
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

        verification_token = secrets.token_urlsafe(32)
        new_user = User(
            email=signup_data.email,
            phone_number=signup_data.phone_number,
            hashed_password=get_password_hash(signup_data.password),
            verification_token=verification_token,
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        verify_url = f"{settings.app_domain}/auth/verify-email?token={verification_token}"
        await send_email(
            to=new_user.email,
            subject="Verify your email",
            html_body=build_verification_email(verify_url),
        )

        await log_audit(
            action="user.signup",
            user_id=str(new_user.id),
            resource_type="user",
            resource_id=str(new_user.id),
            ip_address=ip,
        )

        access_token = create_access_token({"sub": str(new_user.id)})
        refresh_token = create_refresh_token({"sub": str(new_user.id)})
        response = JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "access_token": access_token,
                "token_type": "bearer",
                "user": {"id": str(new_user.id), "email": new_user.email, "plan": new_user.plan},
            },
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.is_production,
            samesite="none" if settings.is_production else "lax",
            max_age=settings.refresh_token_expire_minutes * 60,
            path="/",
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.is_production,
            samesite="none" if settings.is_production else "lax",
            max_age=settings.access_token_expire_minutes * 60,
            path="/",
        )
        return response


@router.post("/login")
async def login(request: Request, login_data: LoginData):
    ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ip:{ip}:login",
        limit=5,
        window_minutes=15,
        error_msg="Too many login attempts. Please try again after 15 minutes."
    )

    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.email == login_data.email))
        user = result.one_or_none()
        if not user or not user.hashed_password or not verify_password(login_data.password, user.hashed_password):
            if user:
                await check_rate_limit(
                    key=f"user:{user.id}:failed_login",
                    limit=10,
                    window_minutes=30,
                    error_msg="Account temporarily locked due to too many failed attempts. Try again later."
                )
                await check_rate_limit(
                    key=f"user:{user.email}:failed_login",
                    limit=10,
                    window_minutes=30,
                    error_msg="Account temporarily locked due to too many failed attempts. Try again later."
                )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        await log_audit(
            action="user.login",
            user_id=str(user.id),
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip,
        )

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        response = JSONResponse(
            content={
                "access_token": access_token,
                "token_type": "bearer",
                "user": {"id": str(user.id), "email": user.email, "plan": user.plan},
            }
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.is_production,
            samesite="none" if settings.is_production else "lax",
            max_age=settings.refresh_token_expire_minutes * 60,
            path="/",
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.is_production,
            samesite="none" if settings.is_production else "lax",
            max_age=settings.access_token_expire_minutes * 60,
            path="/",
        )
        return response


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "phone_number": current_user.phone_number,
        "plan": current_user.plan,
        "email_verified": current_user.email_verified,
    }


@router.post("/refresh")
async def refresh_token(request: Request):
    ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ip:{ip}:refresh",
        limit=10,
        window_minutes=15,
        error_msg="Too many token refresh attempts. Try again later."
    )

    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        user_uuid = uuid.UUID(user_id)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.id == user_uuid))
        user = result.one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {"id": str(user.id), "email": user.email, "plan": user.plan},
        }
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=settings.refresh_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    return response


@router.get("/verify-email")
async def verify_email(token: str, request: Request):
    ip = get_client_ip(request)
    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.verification_token == token))
        user = result.one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired verification token")

        user.email_verified = True
        user.verification_token = None
        session.add(user)
        await session.commit()

        await log_audit(
            action="user.verify_email",
            user_id=str(user.id),
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip,
        )

    return {"detail": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(request: Request, current_user: User = Depends(get_current_user)):
    ip = get_client_ip(request)
    if current_user.email_verified:
        return {"detail": "Email already verified"}

    await check_rate_limit(
        key=f"user:{current_user.id}:resend_verify",
        limit=3,
        window_minutes=60,
        error_msg="Too many verification email requests. Try again later."
    )

    verification_token = secrets.token_urlsafe(32)
    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.id == current_user.id))
        user = result.one_or_none()
        if user:
            user.verification_token = verification_token
            session.add(user)
            await session.commit()

    verify_url = f"{settings.app_domain}/auth/verify-email?token={verification_token}"
    await send_email(
        to=current_user.email,
        subject="Verify your email",
        html_body=build_verification_email(verify_url),
    )

    await log_audit(
        action="user.resend_verification",
        user_id=str(current_user.id),
        resource_type="user",
        resource_id=str(current_user.id),
        ip_address=ip,
    )

    return {"detail": "Verification email sent"}


@router.post("/forgot-password")
async def forgot_password(request: Request, data: ForgotPasswordData):
    ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ip:{ip}:forgot_password",
        limit=3,
        window_minutes=60,
        error_msg="Too many password reset requests. Try again later."
    )

    reset_token = secrets.token_urlsafe(32)
    expires = _utcnow() + timedelta(minutes=settings.reset_token_expire_minutes)

    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.email == data.email))
        user = result.one_or_none()
        if user:
            user.reset_token = reset_token
            user.reset_token_expires = expires
            session.add(user)
            await session.commit()

            reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={reset_token}"
            await send_email(
                to=user.email,
                subject="Reset your password",
                html_body=build_password_reset_email(reset_url),
            )

            await log_audit(
                action="user.forgot_password",
                user_id=str(user.id),
                resource_type="user",
                resource_id=str(user.id),
                ip_address=ip,
            )

    return {"detail": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(request: Request, data: ResetPasswordData):
    ip = get_client_ip(request)
    await check_rate_limit(
        key=f"ip:{ip}:reset_password",
        limit=5,
        window_minutes=60,
        error_msg="Too many password reset attempts. Try again later."
    )

    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.reset_token == data.token))
        user = result.one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

        if not user.reset_token_expires or _utcnow() > user.reset_token_expires:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired")

        user.hashed_password = get_password_hash(data.password)
        user.reset_token = None
        user.reset_token_expires = None
        session.add(user)
        await session.commit()

        await log_audit(
            action="user.reset_password",
            user_id=str(user.id),
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip,
        )

    return {"detail": "Password has been reset successfully"}


@router.post("/logout")
async def logout():
    response = JSONResponse(content={"detail": "Logged out"})
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("access_token", path="/")
    return response
