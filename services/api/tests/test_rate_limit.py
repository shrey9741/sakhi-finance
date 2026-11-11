import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_rate_limiter, get_otp_provider
from app.core.config import Settings
from app.core.rate_limit import RateLimiter
from app.db.session import get_session
from app.main import app
from app.modules.identity.rate_limits import (
    AuthRateLimiter,
    RateLimiterUnavailable,
    RateLimitExceeded,
)

BASE = "/api/v1"
PHONE_A = "9876543210"
PHONE_B = "9123456780"


class FakeProvider:
    async def send(self, phone_e164: str, code: str) -> None:
        pass


def make(redis: Redis, **overrides: int) -> AuthRateLimiter:
    return AuthRateLimiter(RateLimiter(redis), Settings(**overrides))


# ---- RateLimiter ----


async def test_blocks_after_limit(redis_client: Redis) -> None:
    limiter = RateLimiter(redis_client)
    for _ in range(3):
        assert (await limiter.hit("k", 3, 60)).allowed
    blocked = await limiter.hit("k", 3, 60)
    assert not blocked.allowed
    assert 1 <= blocked.retry_after <= 60


async def test_expiry_is_always_set(redis_client: Redis) -> None:
    await RateLimiter(redis_client).hit("k", 3, 60)
    ttl = await redis_client.ttl("k")
    assert 0 < ttl <= 60


async def test_window_resets(redis_client: Redis) -> None:
    limiter = RateLimiter(redis_client)
    assert (await limiter.hit("k", 1, 1)).allowed
    assert not (await limiter.hit("k", 1, 1)).allowed
    await asyncio.sleep(1.2)
    assert (await limiter.hit("k", 1, 1)).allowed


# ---- AuthRateLimiter ----


async def test_phone_limit_is_per_phone(redis_client: Redis) -> None:
    rl = make(redis_client, rate_limit_otp_request_per_phone=2, rate_limit_otp_request_per_ip=100)
    await rl.check_otp_request("1.1.1.1", PHONE_A)
    await rl.check_otp_request("1.1.1.1", PHONE_A)
    with pytest.raises(RateLimitExceeded):
        await rl.check_otp_request("1.1.1.1", PHONE_A)
    await rl.check_otp_request("1.1.1.1", PHONE_B)


async def test_ip_limit_applies_across_phones(redis_client: Redis) -> None:
    rl = make(redis_client, rate_limit_otp_request_per_ip=2, rate_limit_otp_request_per_phone=100)
    await rl.check_otp_request("2.2.2.2", PHONE_A)
    await rl.check_otp_request("2.2.2.2", PHONE_B)
    with pytest.raises(RateLimitExceeded):
        await rl.check_otp_request("2.2.2.2", "9000000001")
    await rl.check_otp_request("3.3.3.3", PHONE_A)


async def test_global_cap(redis_client: Redis) -> None:
    rl = make(redis_client, rate_limit_otp_daily_global_cap=1)
    await rl.check_otp_request("4.4.4.4", PHONE_A)
    with pytest.raises(RateLimitExceeded):
        await rl.check_otp_request("5.5.5.5", PHONE_B)


async def test_phone_number_not_stored_raw_in_redis(redis_client: Redis) -> None:
    await make(redis_client).check_otp_request("6.6.6.6", PHONE_A)
    keys = await redis_client.keys("*")
    assert keys
    assert not any(PHONE_A in key for key in keys)


async def test_request_fails_closed_when_redis_down() -> None:
    dead = Redis.from_url("redis://127.0.0.1:6399/0", socket_connect_timeout=0.5)
    rl = AuthRateLimiter(RateLimiter(dead), Settings())
    with pytest.raises(RateLimiterUnavailable):
        await rl.check_otp_request("7.7.7.7", PHONE_A)
    await dead.aclose()


async def test_verify_fails_open_when_redis_down() -> None:
    dead = Redis.from_url("redis://127.0.0.1:6399/0", socket_connect_timeout=0.5)
    rl = AuthRateLimiter(RateLimiter(dead), Settings())
    await rl.check_otp_verify("8.8.8.8")  # must not raise
    await dead.aclose()


# ---- Through the API ----


@pytest.fixture
async def limited_client(
    session: AsyncSession, redis_client: Redis
) -> AsyncIterator[httpx.AsyncClient]:
    async def _session() -> AsyncSession:
        return session

    async def _provider() -> FakeProvider:
        return FakeProvider()

    async def _limiter() -> AuthRateLimiter:
        return make(redis_client, rate_limit_otp_request_per_phone=1)

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_otp_provider] = _provider
    app.dependency_overrides[get_auth_rate_limiter] = _limiter
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_api_returns_429_with_retry_after(limited_client: httpx.AsyncClient) -> None:
    first = await limited_client.post(f"{BASE}/auth/otp/request", json={"phone_number": PHONE_A})
    assert first.status_code == 202
    second = await limited_client.post(f"{BASE}/auth/otp/request", json={"phone_number": PHONE_A})
    assert second.status_code == 429
    assert "Too many requests" in second.json()["detail"]
    assert int(second.headers["retry-after"]) > 0


async def test_api_returns_503_when_limiter_unavailable(session: AsyncSession) -> None:
    dead = Redis.from_url("redis://127.0.0.1:6399/0", socket_connect_timeout=0.5)

    async def _session() -> AsyncSession:
        return session

    async def _provider() -> FakeProvider:
        return FakeProvider()

    async def _limiter() -> AuthRateLimiter:
        return AuthRateLimiter(RateLimiter(dead), Settings())

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_otp_provider] = _provider
    app.dependency_overrides[get_auth_rate_limiter] = _limiter
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/otp/request", json={"phone_number": PHONE_A})
    app.dependency_overrides.clear()
    await dead.aclose()
    assert r.status_code == 503
