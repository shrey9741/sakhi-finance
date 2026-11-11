from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Reject state-changing requests that come from a browser origin we don't trust."""

    async def dispatch(self, request, call_next):
        if request.method not in _SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin is not None and origin not in get_settings().allowed_origins:
                return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
        return await call_next(request)