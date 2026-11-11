from dataclasses import dataclass

from redis.asyncio import Redis

# INCR and EXPIRE run atomically in one Lua script, so a crash between them
# can never leave a counter without an expiry.
_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
local ttl = redis.call('TTL', KEYS[1])
if ttl < 0 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
  ttl = tonumber(ARGV[1])
end
return {count, ttl}
"""


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int


class RateLimiter:
    """Fixed-window counter. The window starts at the first hit for a key."""

    def __init__(self, redis: Redis) -> None:
        self._script = redis.register_script(_SCRIPT)

    async def hit(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        count, ttl = await self._script(keys=[key], args=[window_seconds])
        return RateLimitResult(allowed=int(count) <= limit, retry_after=max(int(ttl), 1))