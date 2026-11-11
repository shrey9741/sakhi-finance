import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://sakhi:sakhi_dev_only@localhost:5433/sakhi_test",
)
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
# Must be set before any app module reads settings.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    api_dir = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=api_dir, check=True
    )


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as conn:
        trans = await conn.begin()
        async with AsyncSession(
            bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False
        ) as s:
            yield s
        await trans.rollback()
    await engine.dispose()


@pytest.fixture
async def redis_client() -> AsyncIterator[Redis]:
    client = Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()