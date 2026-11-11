from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.api.deps import get_auth_rate_limiter, get_otp_service, get_session_service
from app.core.config import Settings, get_settings
from app.modules.identity.errors import InvalidOtpError, InvalidPhoneError, OtpCooldownError
from app.modules.identity.otp_service import OtpService
from app.modules.identity.rate_limits import (
    AuthRateLimiter,
    RateLimiterUnavailable,
    RateLimitExceeded,
)
from app.modules.identity.session_service import SessionService

router = APIRouter(prefix="/auth", tags=["auth"])


class OtpRequestIn(BaseModel):
    phone_number: str = Field(max_length=20)


class OtpVerifyIn(BaseModel):
    phone_number: str = Field(max_length=20)
    otp: str = Field(pattern=r"^\d{6}$")


def _client_ip(request: Request) -> str:
    # Behind a proxy, run uvicorn with --proxy-headers and a trusted forwarded-allow-ips.
    return request.client.host if request.client else "unknown"


def _too_many(exc: RateLimitExceeded) -> HTTPException:
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Too many requests. Please try again later.",
        headers={"Retry-After": str(exc.retry_after)},
    )


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def request_otp(
    body: OtpRequestIn,
    request: Request,
    service: OtpService = Depends(get_otp_service),
    limiter: AuthRateLimiter = Depends(get_auth_rate_limiter),
) -> dict[str, str]:
    try:
        await limiter.check_otp_request(_client_ip(request), body.phone_number)
    except RateLimitExceeded as exc:
        raise _too_many(exc)
    except RateLimiterUnavailable:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service temporarily unavailable")

    try:
        await service.request_otp(body.phone_number)
    except InvalidPhoneError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid phone number")
    except OtpCooldownError as exc:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Please wait before requesting another code",
            headers={"Retry-After": str(exc.retry_after)},
        )
    return {"status": "otp_requested"}


@router.post("/otp/verify")
async def verify_otp(
    body: OtpVerifyIn,
    request: Request,
    response: Response,
    otp_service: OtpService = Depends(get_otp_service),
    session_service: SessionService = Depends(get_session_service),
    limiter: AuthRateLimiter = Depends(get_auth_rate_limiter),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    try:
        await limiter.check_otp_verify(_client_ip(request))
    except RateLimitExceeded as exc:
        raise _too_many(exc)

    try:
        user_id = await otp_service.verify_otp(body.phone_number, body.otp)
    except (InvalidPhoneError, InvalidOtpError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired code")
    token = await session_service.create(user_id)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"status": "ok"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
    sessions: SessionService = Depends(get_session_service),
) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await sessions.revoke(token)
    response.delete_cookie(settings.session_cookie_name, path="/")