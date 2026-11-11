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

    # Sessions and CSRF
    session_cookie_name: str = "sakhi_session"
    session_ttl_days: int = 30
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Rate limits (fixed windows)
    rate_limit_otp_request_per_phone: int = 5  # per hour
    rate_limit_otp_request_per_ip: int = 20  # per hour
    rate_limit_otp_verify_per_ip: int = 30  # per 10 minutes
    rate_limit_otp_daily_global_cap: int = 2000  # SMS budget guard, per 24 hours

    @property
    def cookie_secure(self) -> bool:
        return self.app_env != "development"

    @model_validator(mode="after")
    def _require_real_secret_outside_dev(self) -> Self:
        if self.app_env != "development" and self.otp_hmac_secret == _DEV_OTP_SECRET:
            raise ValueError("OTP_HMAC_SECRET must be set outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()