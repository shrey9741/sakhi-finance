from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimiter
from app.core.redis import get_redis_client
from app.db.session import get_session
from app.modules.identity.models import User
from app.modules.identity.otp_service import OtpService
from app.modules.identity.providers import ConsoleOtpProvider, OtpProvider
from app.modules.identity.rate_limits import AuthRateLimiter
from app.modules.identity.session_service import SessionService


async def get_otp_provider(settings: Settings = Depends(get_settings)) -> OtpProvider:
    # Swap for a real SMS provider here when one is chosen.
    return ConsoleOtpProvider(settings)


async def get_otp_service(
    session: AsyncSession = Depends(get_session),
    provider: OtpProvider = Depends(get_otp_provider),
    settings: Settings = Depends(get_settings),
) -> OtpService:
    return OtpService(session, provider, settings)


async def get_session_service(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SessionService:
    return SessionService(session, settings)


async def get_auth_rate_limiter(
    settings: Settings = Depends(get_settings),
) -> AuthRateLimiter:
    return AuthRateLimiter(RateLimiter(get_redis_client()), settings)


async def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
    sessions: SessionService = Depends(get_session_service),
) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    user = await sessions.get_user(token) if token else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user