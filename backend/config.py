import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
import urllib.parse

_PROD_FORBIDDEN_DEFAULTS = {
    "secret_key": {"changeme", ""},
}

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    postgres_user: str = Field(default="postgres", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", validation_alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="127.0.0.1", validation_alias="POSTGRES_HOST")
    postgres_port: str = Field(default="5432", validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="lostitem", validation_alias="POSTGRES_DB")
    use_sqlite: bool = Field(default=False, validation_alias="USE_SQLITE")
    database_url: str = Field(default="", validation_alias="DATABASE_URL")
    database_ssl: bool = Field(default=False, validation_alias="DATABASE_SSL")

    twilio_account_sid: str = Field(default="", validation_alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", validation_alias="TWILIO_AUTH_TOKEN")
    twilio_proxy_service_sid: str = Field(default="", validation_alias="TWILIO_PROXY_SERVICE_SID")
    twilio_phone_number: str = Field(default="", validation_alias="TWILIO_PHONE_NUMBER")

    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_domain: str = Field(default="http://localhost", validation_alias="APP_DOMAIN")
    frontend_url: str = Field(default="http://localhost", validation_alias="FRONTEND_URL")
    redis_url: str = Field(default="memory", validation_alias="REDIS_URL")
    secret_key: str = Field(default="changeme", validation_alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_minutes: int = Field(default=60 * 24 * 7, validation_alias="REFRESH_TOKEN_EXPIRE_MINUTES")
    enable_db_autocreate: bool = Field(default=False, validation_alias="ENABLE_DB_AUTO_CREATE")
    allow_legacy_auth: bool = Field(default=False, validation_alias="ALLOW_LEGACY_AUTH")
    verification_token_expire_hours: int = Field(default=48, validation_alias="VERIFICATION_TOKEN_EXPIRE_HOURS")
    reset_token_expire_minutes: int = Field(default=60, validation_alias="RESET_TOKEN_EXPIRE_MINUTES")
    email_from: str = Field(default="noreply@tagmasterpro.com", validation_alias="EMAIL_FROM")
    smtp_host: str = Field(default="", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASSWORD")
    sentry_dsn: str = Field(default="", validation_alias="SENTRY_DSN")

    google_client_id: str = Field(default="", validation_alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", validation_alias="GOOGLE_CLIENT_SECRET")
    qr_base_url: str = Field(default="", validation_alias="QR_BASE_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @model_validator(mode="after")
    def _enforce_production_security(self) -> "Settings":
        if not self.is_production:
            return self

        bad = _PROD_FORBIDDEN_DEFAULTS
        for field_name, forbidden_values in bad.items():
            val = getattr(self, field_name, None)
            if val in forbidden_values:
                raise ValueError(
                    f"{field_name} must be set to a real value in production. "
                    f"Current value is a known insecure default."
                )

        if not self.app_domain.startswith("https://"):
            raise ValueError("APP_DOMAIN must use HTTPS in production.")

        if not self.frontend_url.startswith("https://"):
            raise ValueError("FRONTEND_URL must use HTTPS in production.")

        if self.enable_db_autocreate:
            raise ValueError("ENABLE_DB_AUTO_CREATE must be False in production. Use Alembic migrations instead.")

        if self.allow_legacy_auth:
            raise ValueError("ALLOW_LEGACY_AUTH must be False in production.")

        return self

    @property
    def postgres_url(self) -> str:
        if self.database_url:
            url = self.database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        encoded_password = urllib.parse.quote_plus(self.postgres_password)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{encoded_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def effective_qr_url(self) -> str:
        """URL base for QR codes. Uses QR_BASE_URL if set, else FRONTEND_URL."""
        return (self.qr_base_url or self.frontend_url).rstrip("/")


settings = Settings()
