"""
Redis-backed connection registry for dashboard WebSocket connections.

Tracks active connections per workspace and per user in Redis sets.
Supports multi-worker deployments (connection state shared via Redis).
Gracefully degrades when Redis is unavailable.
"""

import os
import secrets
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)

# Limits
MAX_CONNECTIONS_PER_WORKSPACE = 50
MAX_CONNECTIONS_PER_USER = 3
CONNECTION_TTL = 7200  # 2 hours


class ConnectionLimitExceeded(Exception):
    """Raised when workspace or user connection limit is reached."""


class DashboardConnectionRegistry:
    """Redis-backed connection tracking for dashboard WebSocket clients."""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._local_connections: dict[str, object] = {}  # connection_id → WebSocket

    async def register(self, workspace_id: str, user_id: str) -> str:
        """Register a new connection. Returns connection_id. Raises ConnectionLimitExceeded."""
        if self.redis is None:
            # Without Redis, allow connection with local tracking only
            connection_id = f"{workspace_id}:{secrets.token_urlsafe(16)}"
            self._local_connections[connection_id] = {
                "workspace_id": workspace_id,
                "user_id": user_id,
            }
            return connection_id

        try:
            # Check workspace limit
            ws_key = f"ws_connections:{workspace_id}"
            conn_count = await self.redis.scard(ws_key)
            if conn_count >= MAX_CONNECTIONS_PER_WORKSPACE:
                raise ConnectionLimitExceeded(
                    f"Max {MAX_CONNECTIONS_PER_WORKSPACE} connections per workspace"
                )

            # Check user limit
            user_key = f"ws_user_connections:{user_id}"
            user_conns = await self.redis.scard(user_key)
            if user_conns >= MAX_CONNECTIONS_PER_USER:
                raise ConnectionLimitExceeded(
                    f"Max {MAX_CONNECTIONS_PER_USER} connections per user"
                )

            # Generate unique connection ID
            connection_id = f"{workspace_id}:{secrets.token_urlsafe(16)}"

            # Register in Redis with TTL
            await self.redis.sadd(ws_key, connection_id)
            await self.redis.expire(ws_key, CONNECTION_TTL)

            await self.redis.sadd(user_key, connection_id)
            await self.redis.expire(user_key, CONNECTION_TTL)

            # Store metadata
            meta_key = f"ws_conn_meta:{connection_id}"
            await self.redis.hset(
                meta_key,
                mapping={
                    "workspace_id": workspace_id,
                    "user_id": user_id,
                    "connected_at": datetime.now(UTC).isoformat(),
                    "worker_id": str(os.getpid()),
                },
            )
            await self.redis.expire(meta_key, CONNECTION_TTL)

            logger.info(
                "dashboard_registry.registered",
                connection_id=connection_id,
                workspace_id=workspace_id,
            )
            return connection_id

        except ConnectionLimitExceeded:
            raise
        except Exception as e:
            # Degrade gracefully — allow connection without Redis tracking
            logger.warning("dashboard_registry.redis_error", error=str(e))
            connection_id = f"{workspace_id}:{secrets.token_urlsafe(16)}"
            self._local_connections[connection_id] = {
                "workspace_id": workspace_id,
                "user_id": user_id,
            }
            return connection_id

    async def unregister(self, connection_id: str) -> None:
        """Remove connection from registry."""
        self._local_connections.pop(connection_id, None)

        if self.redis is None:
            return

        try:
            meta_key = f"ws_conn_meta:{connection_id}"
            meta = await self.redis.hgetall(meta_key)
            if not meta:
                return

            workspace_id = meta.get("workspace_id")
            user_id = meta.get("user_id")

            if workspace_id:
                await self.redis.srem(f"ws_connections:{workspace_id}", connection_id)
            if user_id:
                await self.redis.srem(f"ws_user_connections:{user_id}", connection_id)
            await self.redis.delete(meta_key)

            logger.info("dashboard_registry.unregistered", connection_id=connection_id)
        except Exception as e:
            logger.warning("dashboard_registry.unregister_error", error=str(e))

    async def heartbeat(self, connection_id: str) -> None:
        """Refresh connection TTL."""
        if self.redis is None:
            return
        try:
            await self.redis.expire(f"ws_conn_meta:{connection_id}", CONNECTION_TTL)
        except Exception:
            pass  # Best-effort

    async def get_connection_count(self, workspace_id: str) -> int:
        """Get current connection count for workspace."""
        if self.redis is None:
            return sum(
                1
                for v in self._local_connections.values()
                if isinstance(v, dict) and v.get("workspace_id") == workspace_id
            )
        try:
            return await self.redis.scard(f"ws_connections:{workspace_id}")
        except Exception:
            return 0
