from functools import lru_cache
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_OTP_SECRET = "dev-only-insecure-secret"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://sakhi:sakhi_dev_only@localhost:5433/sakhi"
    redis_url: str = "redis://localhost:6379/0"

    # OTP
    otp_hmac_secret: str = _DEV_OTP_SECRET
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60

    @model_validator(mode="after")
    def _require_real_secret_outside_dev(self) -> Self:
        if self.app_env != "development" and self.otp_hmac_secret == _DEV_OTP_SECRET:
            raise ValueError("OTP_HMAC_SECRET must be set outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()