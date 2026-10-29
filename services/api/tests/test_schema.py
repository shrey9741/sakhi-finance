import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.profiles.models import UserProfile


async def test_pgvector_enabled_by_migration(session: AsyncSession) -> None:
    count = await session.scalar(text("SELECT count(*) FROM pg_extension WHERE extname='vector'"))
    assert count == 1


async def test_user_defaults(session: AsyncSession) -> None:
    user = User()
    session.add(user)
    await session.flush()
    await session.refresh(user)
    assert user.id is not None
    assert user.status == "active"
    assert user.created_at is not None


async def test_invalid_user_status_rejected(session: AsyncSession) -> None:
    session.add(User(status="bogus"))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_invalid_language_rejected(session: AsyncSession) -> None:
    user = User()
    session.add(user)
    await session.flush()
    session.add(UserProfile(user_id=user.id, preferred_language="fr-FR"))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_profile_deleted_with_user(session: AsyncSession) -> None:
    user = User()
    session.add(user)
    await session.flush()
    session.add(UserProfile(user_id=user.id))
    await session.flush()
    await session.delete(user)
    await session.flush()
    count = await session.scalar(select(func.count()).select_from(UserProfile))
    assert count == 0