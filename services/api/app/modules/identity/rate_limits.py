import hashlib
import hmac
import logging

from redis.exceptions import RedisError

from app.core.config import Settings
from app.core.rate_limit import RateLimiter
from app.modules.identity.errors import InvalidPhoneError
from app.modules.identity.phone import normalize_phone

logger = logging.getLogger(__name__)

HOUR = 3600
TEN_MINUTES = 600
DAY = 86400


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Rate limit exceeded")
        self.retry_after = retry_after


class RateLimiterUnavailable(Exception):
    """Redis could not be reached, so limits cannot be checked."""


class AuthRateLimiter:
    def __init__(self, limiter: RateLimiter, settings: Settings) -> None:
        self._limiter = limiter
        self._settings = settings

    def _phone_digest(self, raw_phone: str) -> str | None:
        try:
            phone = normalize_phone(raw_phone)
        except InvalidPhoneError:
            return None  # the OTP service will reject it; the IP limit still applies
        key = self._settings.otp_hmac_secret.encode()
        return hmac.new(key, f"rl-phone:{phone}".encode(), hashlib.sha256).hexdigest()

    async def _enforce(self, key: str, limit: int, window: int) -> None:
        result = await self._limiter.hit(key, limit, window)
        if not result.allowed:
            raise RateLimitExceeded(result.retry_after)

    async def check_otp_request(self, ip: str, raw_phone: str) -> None:
        """Fails closed: if Redis is down, no SMS is sent."""
        s = self._settings
        try:
            await self._enforce(f"rl:otp-req:ip:{ip}", s.rate_limit_otp_request_per_ip, HOUR)
            digest = self._phone_digest(raw_phone)
            if digest is not None:
                await self._enforce(
                    f"rl:otp-req:phone:{digest}", s.rate_limit_otp_request_per_phone, HOUR
                )
            await self._enforce("rl:otp-req:global", s.rate_limit_otp_daily_global_cap, DAY)
        except (RedisError, OSError) as exc:
            logger.error("Rate limiter unavailable: %s", type(exc).__name__)
            raise RateLimiterUnavailable from exc

    async def check_otp_verify(self, ip: str) -> None:
        """Fails open: the per-code attempt lockout in Postgres still applies."""
        try:
            await self._enforce(
                f"rl:otp-verify:ip:{ip}", self._settings.rate_limit_otp_verify_per_ip, TEN_MINUTES
            )
        except (RedisError, OSError) as exc:
            logger.warning("Rate limiter unavailable on verify: %s", type(exc).__name__)