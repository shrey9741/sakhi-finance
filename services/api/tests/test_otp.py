from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.identity.errors import InvalidOtpError, InvalidPhoneError, OtpCooldownError
from app.modules.identity.models import OtpChallenge, UserIdentity
from app.modules.identity.otp_service import OtpService
from app.modules.profiles.models import UserProfile

PHONE = "9876543210"


class FakeProvider:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send(self, phone_e164: str, code: str) -> None:
        self.sent.append((phone_e164, code))


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += timedelta(seconds=seconds)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def service(session: AsyncSession, provider: FakeProvider, clock: Clock) -> OtpService:
    return OtpService(session, provider, Settings(), clock)


async def test_request_sends_six_digit_code(service: OtpService, provider: FakeProvider) -> None:
    await service.request_otp(PHONE)
    phone, code = provider.sent[0]
    assert phone == "+919876543210"
    assert len(code) == 6 and code.isdigit()


async def test_code_not_stored_in_plaintext(
    service: OtpService, provider: FakeProvider, session: AsyncSession
) -> None:
    await service.request_otp(PHONE)
    code = provider.sent[0][1]
    row = await session.scalar(select(OtpChallenge))
    assert row is not None
    assert code not in row.code_hash
    assert "9876543210" not in row.phone_hash


async def test_verify_creates_user_profile_identity(
    service: OtpService, provider: FakeProvider, session: AsyncSession
) -> None:
    await service.request_otp(PHONE)
    user_id = await service.verify_otp(PHONE, provider.sent[0][1])
    identity = await session.scalar(select(UserIdentity))
    assert identity is not None and identity.user_id == user_id
    assert identity.verified_at is not None
    profile_count = await session.scalar(select(func.count()).select_from(UserProfile))
    assert profile_count == 1


async def test_same_phone_returns_same_user(
    service: OtpService, provider: FakeProvider, clock: Clock
) -> None:
    await service.request_otp(PHONE)
    first = await service.verify_otp(PHONE, provider.sent[0][1])
    clock.advance(61)
    await service.request_otp(PHONE)
    second = await service.verify_otp(PHONE, provider.sent[1][1])
    assert first == second


async def test_lockout_after_max_attempts(service: OtpService, provider: FakeProvider) -> None:
    await service.request_otp(PHONE)
    code = provider.sent[0][1]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        with pytest.raises(InvalidOtpError):
            await service.verify_otp(PHONE, wrong)
    with pytest.raises(InvalidOtpError):
        await service.verify_otp(PHONE, code)


async def test_expired_code_rejected(
    service: OtpService, provider: FakeProvider, clock: Clock
) -> None:
    await service.request_otp(PHONE)
    clock.advance(301)
    with pytest.raises(InvalidOtpError):
        await service.verify_otp(PHONE, provider.sent[0][1])


async def test_code_is_single_use(service: OtpService, provider: FakeProvider) -> None:
    await service.request_otp(PHONE)
    code = provider.sent[0][1]
    await service.verify_otp(PHONE, code)
    with pytest.raises(InvalidOtpError):
        await service.verify_otp(PHONE, code)


async def test_resend_cooldown(service: OtpService, clock: Clock) -> None:
    await service.request_otp(PHONE)
    with pytest.raises(OtpCooldownError) as exc:
        await service.request_otp(PHONE)
    assert exc.value.retry_after > 0
    clock.advance(61)
    await service.request_otp(PHONE)


async def test_invalid_phone_rejected(service: OtpService) -> None:
    with pytest.raises(InvalidPhoneError):
        await service.request_otp("12345")