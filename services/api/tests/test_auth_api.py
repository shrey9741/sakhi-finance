from collections.abc import AsyncIterator

import httpx
import pytest
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_rate_limiter, get_otp_provider
from app.core.config import Settings
from app.core.rate_limit import RateLimiter
from app.db.session import get_session
from app.main import app
from app.modules.identity.models import UserSession
from app.modules.identity.rate_limits import AuthRateLimiter

PHONE = "9876543210"
BASE = "/api/v1"


class FakeProvider:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send(self, phone_e164: str, code: str) -> None:
        self.sent.append((phone_e164, code))


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
async def client(
    session: AsyncSession, provider: FakeProvider, redis_client: Redis
) -> AsyncIterator[httpx.AsyncClient]:
    async def _session() -> AsyncSession:
        return session

    async def _provider() -> FakeProvider:
        return provider

    async def _limiter() -> AuthRateLimiter:
        return AuthRateLimiter(RateLimiter(redis_client), Settings())

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_otp_provider] = _provider
    app.dependency_overrides[get_auth_rate_limiter] = _limiter
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def login(client: httpx.AsyncClient, provider: FakeProvider) -> httpx.Response:
    r = await client.post(f"{BASE}/auth/otp/request", json={"phone_number": PHONE})
    assert r.status_code == 202
    code = provider.sent[-1][1]
    return await client.post(f"{BASE}/auth/otp/verify", json={"phone_number": PHONE, "otp": code})


async def test_full_login_and_logout_flow(client: httpx.AsyncClient, provider: FakeProvider) -> None:
    r = await login(client, provider)
    assert r.status_code == 200

    me = await client.get(f"{BASE}/users/me")
    assert me.status_code == 200
    assert me.json()["preferred_language"] == "or-IN"
    assert me.json()["onboarding_completed"] is False

    out = await client.post(f"{BASE}/auth/logout")
    assert out.status_code == 204
    assert (await client.get(f"{BASE}/users/me")).status_code == 401


async def test_me_requires_auth(client: httpx.AsyncClient) -> None:
    assert (await client.get(f"{BASE}/users/me")).status_code == 401


async def test_wrong_code_gives_generic_401_and_no_cookie(
    client: httpx.AsyncClient, provider: FakeProvider
) -> None:
    await client.post(f"{BASE}/auth/otp/request", json={"phone_number": PHONE})
    code = provider.sent[-1][1]
    wrong = "000000" if code != "000000" else "111111"
    r = await client.post(f"{BASE}/auth/otp/verify", json={"phone_number": PHONE, "otp": wrong})
    assert r.status_code == 401
    assert "set-cookie" not in r.headers


async def test_cookie_flags(client: httpx.AsyncClient, provider: FakeProvider) -> None:
    r = await login(client, provider)
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


async def test_session_token_not_stored_raw(
    client: httpx.AsyncClient, provider: FakeProvider, session: AsyncSession
) -> None:
    await login(client, provider)
    token = client.cookies.get("sakhi_session")
    assert token
    stored = await session.scalar(select(UserSession.token_hash))
    assert stored is not None and stored != token


async def test_resend_cooldown_returns_429(client: httpx.AsyncClient) -> None:
    first = await client.post(f"{BASE}/auth/otp/request", json={"phone_number": PHONE})
    assert first.status_code == 202
    second = await client.post(f"{BASE}/auth/otp/request", json={"phone_number": PHONE})
    assert second.status_code == 429
    assert int(second.headers["retry-after"]) > 0


async def test_untrusted_origin_rejected(client: httpx.AsyncClient) -> None:
    r = await client.post(
        f"{BASE}/auth/otp/request",
        json={"phone_number": PHONE},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403