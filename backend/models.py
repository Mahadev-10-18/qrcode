import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship
from pydantic import EmailStr, field_validator
from enum import Enum
import re
import html


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    email: EmailStr = Field(index=True, nullable=False, unique=True)
    phone_number: Optional[str] = Field(default=None, nullable=True)
    hashed_password: Optional[str] = Field(default=None, nullable=True)
    plan: str = Field(default="free")
    created_at: datetime = Field(default_factory=_utcnow)
    email_verified: bool = Field(default=False)
    verification_token: Optional[str] = Field(default=None, nullable=True)
    reset_token: Optional[str] = Field(default=None, nullable=True, index=True)
    reset_token_expires: Optional[datetime] = Field(default=None, nullable=True)
    tags: List["Tag"] = Relationship(back_populates="owner")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = re.sub(r"[\s\-\(\)]", "", v)
            if not re.match(r"^\+?[1-9]\d{4,14}$", cleaned):
                raise ValueError("Phone number must be in E.164 format (e.g. +15551234567)")
            return cleaned
        return v


class TagStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    LOST_CONFIRMED = "lost_confirmed"


class Tag(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    owner_id: uuid.UUID = Field(foreign_key="user.id")
    label: str
    status: str = Field(default=TagStatus.ACTIVE)
    created_at: datetime = Field(default_factory=_utcnow)
    owner: Optional[User] = Relationship(back_populates="tags")

    @field_validator("label")
    @classmethod
    def clean_label(cls, v: str) -> str:
        if v is not None:
            if len(v) > 100:
                raise ValueError("Label must be 100 characters or less")
            return html.escape(v)
        return v


class TagCreate(SQLModel):
    label: str

    @field_validator("label")
    @classmethod
    def clean_label(cls, v: str) -> str:
        if v is not None:
            if len(v) > 100:
                raise ValueError("Label must be 100 characters or less")
            return html.escape(v)
        return v


class TagUpdate(SQLModel):
    label: Optional[str] = None
    status: Optional[str] = None

    @field_validator("label")
    @classmethod
    def clean_label(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) > 100:
                raise ValueError("Label must be 100 characters or less")
            return html.escape(v)
        return v


class ContactRequest(SQLModel):
    finder_phone: str
    message: str = ""

    @field_validator("finder_phone")
    @classmethod
    def validate_finder_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^\+?[1-9]\d{4,14}$", cleaned):
            raise ValueError("Phone number must be in E.164 format (e.g. +15551234567)")
        return cleaned

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("Message must be 500 characters or less")
        return v


class ContactEvent(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    tag_id: uuid.UUID = Field(foreign_key="tag.id")
    finder_contact_method: str = Field(index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    relay_session_id: Optional[str] = Field(default=None, nullable=True)
    message: Optional[str] = Field(default=None, nullable=True)
    is_blocked: bool = Field(default=False)
    finder_phone: Optional[str] = Field(default=None, nullable=True)
    owner_phone: Optional[str] = Field(default=None, nullable=True)


class RateLimitEvent(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    key: str = Field(index=True, nullable=False)
    created_at: datetime = Field(default_factory=_utcnow)


class AuditLog(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    user_id: Optional[str] = Field(default=None, index=True, nullable=True)
    action: str = Field(index=True, nullable=False)
    resource_type: Optional[str] = Field(default=None, nullable=True)
    resource_id: Optional[str] = Field(default=None, nullable=True)
    detail: Optional[str] = Field(default=None, nullable=True)
    ip_address: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=_utcnow)


class LoginData(SQLModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class SignupData(SQLModel):
    email: EmailStr
    phone_number: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class ForgotPasswordData(SQLModel):
    email: EmailStr


class ResetPasswordData(SQLModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class Job(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, nullable=False)
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=_utcnow)
    result: Optional[bytes] = Field(default=None, nullable=True)
