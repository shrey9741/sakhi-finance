import hashlib
import secrets
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.identity.models import User, UserSession


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SessionService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._session = session
        self._settings = settings
        self._clock = clock

    @staticmethod
    def _hash(token: str) -> str:
        # The token is 256 bits of randomness, so a plain SHA-256 is sufficient.
        return hashlib.sha256(token.encode()).hexdigest()

    async def create(self, user_id: uuid.UUID) -> str:
        token = secrets.token_urlsafe(32)
        now = self._clock()
        self._session.add(
            UserSession(
                user_id=user_id,
                token_hash=self._hash(token),
                created_at=now,
                expires_at=now + timedelta(days=self._settings.session_ttl_days),
            )
        )
        await self._session.commit()
        return token

    async def get_user(self, token: str) -> User | None:
        return await self._session.scalar(
            select(User)
            .join(UserSession, UserSession.user_id == User.id)
            .where(
                UserSession.token_hash == self._hash(token),
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > self._clock(),
                User.status == "active",
            )
        )

    async def revoke(self, token: str) -> None:
        await self._session.execute(
            update(UserSession)
            .where(UserSession.token_hash == self._hash(token), UserSession.revoked_at.is_(None))
            .values(revoked_at=self._clock())
        )
        await self._session.commit()