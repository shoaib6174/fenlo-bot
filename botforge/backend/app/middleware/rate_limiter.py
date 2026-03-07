"""Per-IP rate limiting for unauthenticated endpoints.

Protects against:
- Brute force login attempts
- Registration spam
- Health check abuse
"""

from fastapi import HTTPException, Request

from app.core.redis import ResilientRedis


class RateLimiter:
    """Per-IP rate limiter using Redis.

    Design:
    - 20 req/min per IP for unauthenticated endpoints
    - Redis INCR with 60s TTL
    - In-memory fallback via ResilientRedis
    """

    def __init__(self, redis: ResilientRedis, limit: int = 20, window: int = 60):
        """
        Args:
            redis: ResilientRedis instance
            limit: Max requests per window
            window: Time window in seconds
        """
        self.redis = redis
        self.limit = limit
        self.window = window

    async def check_rate_limit(self, request: Request) -> None:
        """Check if IP is within rate limit.

        Args:
            request: FastAPI request

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:ip:{ip}"

        # Increment counter
        count = await self.redis.incr(key)

        # Set expiry on first request
        if count == 1:
            await self.redis.expire(key, self.window)

        # Check limit
        if count > self.limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "RATE_LIMITED",
                    "message": f"Too many requests. Try again in {self.window} seconds.",
                },
            )


# Dependency for FastAPI routes
async def ip_rate_limit(request: Request):
    """Dependency to enforce per-IP rate limiting.

    Usage:
        @router.post("/auth/login", dependencies=[Depends(ip_rate_limit)])
    """
    from app.core.redis import get_resilient_redis

    redis = get_resilient_redis()
    limiter = RateLimiter(redis)
    await limiter.check_rate_limit(request)
