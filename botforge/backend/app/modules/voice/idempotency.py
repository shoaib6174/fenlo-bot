"""Webhook idempotency using Redis SET NX (atomic check-and-set).

Prevents duplicate processing of Vapi webhook events. Uses SHA-256 hash
of (event_type, event_id, timestamp) as the dedup key with 24h TTL.

On Redis failure, allows processing (accepted risk of duplicates —
better than dropping events).
"""

import hashlib

import structlog
from redis.exceptions import RedisError

from app.core.redis import get_redis_client

logger = structlog.get_logger()

_IDEM_TTL = 86400  # 24 hours


async def check_idempotency(event_type: str, event_id: str, timestamp: str) -> bool:
    """Check whether this webhook event was already processed.

    Uses Redis SET NX (atomic) to eliminate race conditions between
    concurrent webhook deliveries.

    Args:
        event_type: Vapi event type (e.g. "status-update").
        event_id: Unique event/call identifier.
        timestamp: Event timestamp string.

    Returns:
        True if this is a duplicate (already processed) — skip it.
        False if this is a new event — process it.
    """
    key_hash = hashlib.sha256(f"{event_type}:{event_id}:{timestamp}".encode()).hexdigest()
    redis_key = f"voice:idem:{key_hash}"

    redis = get_redis_client()
    if redis is None:
        logger.warning(
            "webhook.idempotency_redis_unavailable",
            reason="no_client",
            type=event_type,
        )
        return False  # Redis not configured — allow processing

    try:
        # SET NX: returns True if key was set (new event),
        # None/False if key already exists (duplicate)
        was_set = await redis.set(redis_key, "1", ex=_IDEM_TTL, nx=True)
        if not was_set:
            logger.info(
                "webhook.duplicate_skipped",
                key=key_hash[:16],
                type=event_type,
                event_id=event_id,
            )
            return True  # Duplicate — key already existed
        return False  # New event — key was just set
    except RedisError as e:
        logger.warning(
            "webhook.idempotency_redis_error",
            error=str(e),
            type=event_type,
        )
        return False  # Redis error — allow processing
