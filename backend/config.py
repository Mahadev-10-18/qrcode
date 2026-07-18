from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import urllib.parse

class Settings(BaseSettings):
    postgres_user: str = Field(default="postgres", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", validation_alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="127.0.0.1", validation_alias="POSTGRES_HOST")
    postgres_port: str = Field(default="5432", validation_alias="POSTGRES_PORT")
    postgres_db: str = Field(default="lostitem", validation_alias="POSTGRES_DB")
    use_sqlite: bool = Field(default=False, validation_alias="USE_SQLITE")

    # Required settings (will fail if missing)
    twilio_account_sid: str = Field(..., validation_alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(..., validation_alias="TWILIO_AUTH_TOKEN")
    twilio_proxy_service_sid: str = Field(..., validation_alias="TWILIO_PROXY_SERVICE_SID")

    app_domain: str = Field(default="http://localhost", validation_alias="APP_DOMAIN")
    domain: str = Field(default="example.com", validation_alias="DOMAIN")
    redis_url: str = Field(default="memory", validation_alias="REDIS_URL")


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def postgres_url(self) -> str:
        encoded_password = urllib.parse.quote_plus(self.postgres_password)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{encoded_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

settings = Settings()
