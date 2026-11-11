from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import auth, health, users
from app.core.redis import close_redis_client
from app.middleware.csrf import OriginCheckMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_redis_client()


app = FastAPI(title="Sakhi Finance API", version="0.1.0", lifespan=lifespan)
app.add_middleware(OriginCheckMiddleware)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")