import hashlib
import hmac
import secrets
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.identity.errors import InvalidOtpError, OtpCooldownError
from app.modules.identity.models import OtpChallenge, User, UserIdentity
from app.modules.identity.phone import normalize_phone
from app.modules.identity.providers import OtpProvider
from app.modules.profiles.models import UserProfile


def _utcnow() -> datetime:
    return datetime.now(UTC)


class OtpService:
    def __init__(
        self,
        session: AsyncSession,
        provider: OtpProvider,
        settings: Settings,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._session = session
        self._provider = provider
        self._settings = settings
        self._clock = clock
        self._key = settings.otp_hmac_secret.encode()

    def _hmac(self, message: str) -> str:
        return hmac.new(self._key, message.encode(), hashlib.sha256).hexdigest()

    def _phone_hash(self, phone: str) -> str:
        return self._hmac(f"phone:{phone}")

    def _code_hash(self, phone_hash: str, code: str) -> str:
        return self._hmac(f"code:{phone_hash}:{code}")

    async def request_otp(self, raw_phone: str) -> None:
        phone = normalize_phone(raw_phone)
        phone_hash = self._phone_hash(phone)
        now = self._clock()

        last_created = await self._session.scalar(
            select(OtpChallenge.created_at)
            .where(OtpChallenge.phone_hash == phone_hash)
            .order_by(OtpChallenge.created_at.desc())
            .limit(1)
        )
        if last_created is not None:
            wait = (
                last_created + timedelta(seconds=self._settings.otp_resend_cooldown_seconds) - now
            ).total_seconds()
            if wait > 0:
                raise OtpCooldownError(retry_after=int(wait) + 1)

        code = f"{secrets.randbelow(10**6):06d}"
        self._session.add(
            OtpChallenge(
                phone_hash=phone_hash,
                code_hash=self._code_hash(phone_hash, code),
                expires_at=now + timedelta(seconds=self._settings.otp_ttl_seconds),
                created_at=now,
            )
        )
        # Commit before sending so a delivered code always has a stored challenge.
        await self._session.commit()
        await self._provider.send(phone, code)

    async def verify_otp(self, raw_phone: str, code: str) -> uuid.UUID:
        phone = normalize_phone(raw_phone)
        phone_hash = self._phone_hash(phone)
        now = self._clock()

        challenge = await self._session.scalar(
            select(OtpChallenge)
            .where(
                OtpChallenge.phone_hash == phone_hash,
                OtpChallenge.consumed_at.is_(None),
                OtpChallenge.expires_at > now,
            )
            .order_by(OtpChallenge.created_at.desc())
            .limit(1)
            .with_for_update()
        )
        if challenge is None or challenge.attempts >= self._settings.otp_max_attempts:
            raise InvalidOtpError

        challenge.attempts += 1
        if not hmac.compare_digest(challenge.code_hash, self._code_hash(phone_hash, code)):
            await self._session.commit()  # persist the failed attempt
            raise InvalidOtpError

        challenge.consumed_at = now
        user_id = await self._get_or_create_user(phone, now)
        await self._session.commit()
        return user_id

    async def _get_or_create_user(self, phone: str, now: datetime) -> uuid.UUID:
        identity = await self._session.scalar(
            select(UserIdentity).where(UserIdentity.phone_e164 == phone)
        )
        if identity is not None:
            user = await self._session.get(User, identity.user_id)
            if user is None or user.status != "active":
                raise InvalidOtpError
            return user.id

        user = User()
        self._session.add(user)
        await self._session.flush()
        self._session.add(UserProfile(user_id=user.id))
        self._session.add(UserIdentity(user_id=user.id, phone_e164=phone, verified_at=now))
        await self._session.flush()
        return user.id
