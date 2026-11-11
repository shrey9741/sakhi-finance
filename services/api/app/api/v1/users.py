from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.modules.identity.models import User
from app.modules.profiles.models import UserProfile

router = APIRouter(prefix="/users", tags=["users"])


class UserMe(BaseModel):
    id: str
    status: str
    preferred_language: str | None
    onboarding_completed: bool


@router.get("/me", response_model=UserMe)
async def me(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> UserMe:
    profile = await session.get(UserProfile, user.id)
    return UserMe(
        id=str(user.id),
        status=user.status,
        preferred_language=profile.preferred_language if profile else None,
        onboarding_completed=bool(profile and profile.onboarding_completed_at),
    )