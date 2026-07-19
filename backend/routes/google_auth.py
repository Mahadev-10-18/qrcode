import secrets
import logging
import httpx
import urllib.parse
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import User
from ..db import engine
from ..config import settings
from ..auth_stub import create_access_token, create_refresh_token
from ..utils.audit import log_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/google", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/login")
async def google_login(request: Request):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")

    state = secrets.token_urlsafe(32)
    redirect_uri = f"{settings.frontend_url.rstrip('/')}/api/auth/google/callback"

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"

    response = RedirectResponse(url=auth_url)
    response.set_cookie(
        key="google_oauth_state",
        value=state,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=600,
        path="/",
    )
    return response


@router.get("/callback")
async def google_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")

    stored_state = request.cookies.get("google_oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state parameter")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    redirect_uri = f"{settings.frontend_url.rstrip('/')}/api/auth/google/callback"

    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

        if token_resp.status_code != 200:
            logger.error("Google token exchange failed: %s", token_resp.text)
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

        token_data = token_resp.json()
        access_token_google = token_data.get("access_token")

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token_google}"},
        )

        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        user_info = userinfo_resp.json()

    google_email = user_info.get("email")
    google_sub = user_info.get("id")
    if not google_email:
        raise HTTPException(status_code=400, detail="Google account must have an email address")

    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.email == google_email))
        user = result.one_or_none()

        if not user:
            user = User(
                email=google_email,
                phone_number=None,
                hashed_password=None,
                email_verified=True,
                plan="free",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            await log_audit(
                action="user.signup_google",
                user_id=str(user.id),
                resource_type="user",
                resource_id=str(user.id),
                ip_address=request.client.host if request.client else None,
            )
        else:
            if not user.email_verified:
                user.email_verified = True
                session.add(user)
                await session.commit()

            await log_audit(
                action="user.login_google",
                user_id=str(user.id),
                resource_type="user",
                resource_id=str(user.id),
                ip_address=request.client.host if request.client else None,
            )

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})

    frontend_url = settings.frontend_url.rstrip("/")
    response = RedirectResponse(url=f"{frontend_url}/dashboard")
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
    response.delete_cookie("google_oauth_state", path="/")
    return response
