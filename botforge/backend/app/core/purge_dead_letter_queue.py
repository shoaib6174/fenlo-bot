"""Dead letter queue for failed purge operations requiring manual intervention."""

import json
from datetime import UTC, datetime

import structlog

from app.core.redis import get_redis_client

logger = structlog.get_logger(__name__)

DLQ_KEY = "purge_dlq"
DLQ_TTL = 2592000  # 30 days


class PurgeDeadLetterQueue:
    """Redis-backed DLQ for purge operations that failed and couldn't roll back."""

    def __init__(self):
        self.redis = get_redis_client()

    async def add(self, workspace_id: str, failure_details: dict) -> None:
        """Add a failed purge to the dead letter queue."""
        if not self.redis:
            logger.error(
                "purge_dlq.no_redis",
                workspace_id=workspace_id,
                details=failure_details,
            )
            return

        entry = json.dumps(
            {
                "workspace_id": workspace_id,
                "failure_details": failure_details,
                "timestamp": datetime.now(UTC).isoformat(),
                "requires_manual_intervention": True,
            }
        )
        await self.redis.lpush(DLQ_KEY, entry)
        await self.redis.expire(DLQ_KEY, DLQ_TTL)

        logger.warning(
            "purge_dlq.added",
            workspace_id=workspace_id,
        )

    async def get_all(self) -> list[dict]:
        """Get all failed purges requiring manual intervention."""
        if not self.redis:
            return []

        items = await self.redis.lrange(DLQ_KEY, 0, -1)
        return [json.loads(item) for item in items]

    async def remove(self, index: int) -> None:
        """Remove a specific entry from the DLQ after manual resolution."""
        if not self.redis:
            return

        items = await self.redis.lrange(DLQ_KEY, 0, -1)
        if 0 <= index < len(items):
            await self.redis.lrem(DLQ_KEY, 1, items[index])
