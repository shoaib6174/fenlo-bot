"""Unit tests for dashboard WebSocket components — registry, events, broadcaster."""

from unittest.mock import AsyncMock

import pytest

from app.core.dashboard_connection_registry import (
    MAX_CONNECTIONS_PER_USER,
    MAX_CONNECTIONS_PER_WORKSPACE,
    ConnectionLimitExceeded,
    DashboardConnectionRegistry,
)
from app.core.dashboard_events import (
    EventPriority,
    project_conversation_started,
    project_escalation_event,
    project_message_event,
    project_metrics_update,
)

# ---------------------------------------------------------------------------
# Connection Registry Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDashboardConnectionRegistry:
    """Test Redis-backed connection tracking."""

    async def test_register_generates_unique_connection_id(self):
        """Each registration should produce a unique ID containing workspace_id."""
        redis = AsyncMock()
        redis.scard = AsyncMock(return_value=0)
        redis.sadd = AsyncMock()
        redis.expire = AsyncMock()
        redis.hset = AsyncMock()

        registry = DashboardConnectionRegistry(redis_client=redis)
        id1 = await registry.register("ws-1", "user-1")
        id2 = await registry.register("ws-1", "user-1")

        assert id1 != id2
        assert id1.startswith("ws-1:")
        assert id2.startswith("ws-1:")

    async def test_register_enforces_workspace_limit(self):
        """51st connection should raise ConnectionLimitExceeded."""
        redis = AsyncMock()
        redis.scard = AsyncMock(return_value=MAX_CONNECTIONS_PER_WORKSPACE)

        registry = DashboardConnectionRegistry(redis_client=redis)

        with pytest.raises(ConnectionLimitExceeded, match="50"):
            await registry.register("ws-1", "user-1")

    async def test_register_enforces_user_limit(self):
        """4th connection from same user should raise ConnectionLimitExceeded."""
        redis = AsyncMock()
        # Workspace has room, but user is at limit
        redis.scard = AsyncMock(side_effect=[5, MAX_CONNECTIONS_PER_USER])

        registry = DashboardConnectionRegistry(redis_client=redis)

        with pytest.raises(ConnectionLimitExceeded, match="3"):
            await registry.register("ws-1", "user-1")

    async def test_unregister_removes_from_redis(self):
        """Unregister should clean up all Redis keys."""
        redis = AsyncMock()
        redis.hgetall = AsyncMock(return_value={"workspace_id": "ws-1", "user_id": "user-1"})
        redis.srem = AsyncMock()
        redis.delete = AsyncMock()

        registry = DashboardConnectionRegistry(redis_client=redis)
        await registry.unregister("ws-1:abc123")

        redis.srem.assert_any_await("ws_connections:ws-1", "ws-1:abc123")
        redis.srem.assert_any_await("ws_user_connections:user-1", "ws-1:abc123")
        redis.delete.assert_awaited_once_with("ws_conn_meta:ws-1:abc123")

    async def test_heartbeat_refreshes_ttl(self):
        """Heartbeat should call expire on the metadata key."""
        redis = AsyncMock()
        redis.expire = AsyncMock()

        registry = DashboardConnectionRegistry(redis_client=redis)
        await registry.heartbeat("ws-1:abc123")

        redis.expire.assert_awaited_once_with("ws_conn_meta:ws-1:abc123", 7200)

    async def test_graceful_degradation_without_redis(self):
        """Without Redis, registration should succeed with local tracking."""
        registry = DashboardConnectionRegistry(redis_client=None)

        conn_id = await registry.register("ws-1", "user-1")
        assert conn_id.startswith("ws-1:")

        count = await registry.get_connection_count("ws-1")
        assert count == 1

        await registry.unregister(conn_id)
        count = await registry.get_connection_count("ws-1")
        assert count == 0

    async def test_redis_error_falls_back_to_local(self):
        """On Redis error during register, should fall back to local tracking."""
        redis = AsyncMock()
        redis.scard = AsyncMock(side_effect=Exception("Redis down"))

        registry = DashboardConnectionRegistry(redis_client=redis)
        conn_id = await registry.register("ws-1", "user-1")

        # Should succeed despite Redis failure
        assert conn_id.startswith("ws-1:")
        assert conn_id in registry._local_connections


# ---------------------------------------------------------------------------
# Event Projection Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDashboardEventProjections:
    """Test event projection helpers."""

    async def test_message_event_truncates_preview(self):
        """Message preview should be capped at 100 chars."""
        data = {"response": "A" * 200, "conversation_id": "c1", "sentiment": "positive"}
        event = project_message_event(data)

        assert event["type"] == "message"
        assert event["priority"] == EventPriority.NORMAL
        assert len(event["preview"]) == 100

    async def test_message_event_handles_empty_response(self):
        """Empty response should produce empty preview."""
        event = project_message_event({"response": None, "conversation_id": "c1"})
        assert event["preview"] == ""

    async def test_conversation_started_has_high_priority(self):
        """Conversation started events should be HIGH priority."""
        event = project_conversation_started({"conversation_id": "c1", "channel": "web"})

        assert event["type"] == "conversation_started"
        assert event["priority"] == EventPriority.HIGH
        assert event["channel"] == "web"

    async def test_escalation_event_has_critical_priority(self):
        """Escalation events should be CRITICAL priority."""
        event = project_escalation_event({"conversation_id": "c1", "reason": "negative_sentiment"})

        assert event["type"] == "escalation"
        assert event["priority"] == EventPriority.CRITICAL
        assert event["reason"] == "negative_sentiment"

    async def test_metrics_update_has_low_priority(self):
        """Metrics updates should be LOW priority (safe to drop)."""
        event = project_metrics_update({"active_conversations": 5, "messages_last_minute": 12})

        assert event["type"] == "metrics_update"
        assert event["priority"] == EventPriority.LOW

    async def test_priority_ordering(self):
        """CRITICAL < HIGH < NORMAL < LOW (lower number = higher priority)."""
        assert EventPriority.CRITICAL < EventPriority.HIGH
        assert EventPriority.HIGH < EventPriority.NORMAL
        assert EventPriority.NORMAL < EventPriority.LOW


# ---------------------------------------------------------------------------
# Broadcaster Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDashboardBroadcaster:
    """Test the DashboardBroadcaster event dispatch."""

    async def test_broadcast_sends_to_all_workspace_clients(self):
        """Broadcast should send event to all connected WebSocket clients."""
        from app.api.dashboard_ws import DashboardBroadcaster

        broadcaster = DashboardBroadcaster()

        ws1 = AsyncMock()
        ws2 = AsyncMock()

        # Manually add connections
        broadcaster._connections["ws-1"].add(ws1)
        broadcaster._connections["ws-1"].add(ws2)

        event = {"type": "message", "data": "test"}
        await broadcaster.broadcast("ws-1", event)

        ws1.send_json.assert_awaited_once_with(event)
        ws2.send_json.assert_awaited_once_with(event)

    async def test_broadcast_removes_dead_connections(self):
        """Dead connections should be cleaned up on send failure."""
        from fastapi import WebSocketDisconnect

        from app.api.dashboard_ws import DashboardBroadcaster

        broadcaster = DashboardBroadcaster()

        ws_alive = AsyncMock()
        ws_dead = AsyncMock()
        ws_dead.send_json = AsyncMock(side_effect=WebSocketDisconnect())

        broadcaster._connections["ws-1"].add(ws_alive)
        broadcaster._connections["ws-1"].add(ws_dead)
        broadcaster._connection_ids[id(ws_dead)] = "ws-1:dead"

        await broadcaster.broadcast("ws-1", {"type": "test"})

        # Dead connection should be removed
        assert ws_dead not in broadcaster._connections.get("ws-1", set())
        ws_alive.send_json.assert_awaited_once()

    async def test_handle_event_projects_and_broadcasts(self):
        """handle_event should project raw event data and broadcast."""
        from app.api.dashboard_ws import DashboardBroadcaster

        broadcaster = DashboardBroadcaster()

        ws = AsyncMock()
        broadcaster._connections["ws-1"].add(ws)

        await broadcaster.handle_event(
            "message.created",
            {
                "workspace_id": "ws-1",
                "conversation_id": "c1",
                "response": "Hello there",
                "sentiment": "positive",
                "quality_score": 0.9,
                "intent": "faq",
            },
        )

        ws.send_json.assert_awaited_once()
        sent_event = ws.send_json.call_args[0][0]
        assert sent_event["type"] == "message"
        assert sent_event["preview"] == "Hello there"
        assert sent_event["sentiment"] == "positive"

    async def test_handle_event_ignores_unknown_event_types(self):
        """Unknown event types should be silently ignored."""
        from app.api.dashboard_ws import DashboardBroadcaster

        broadcaster = DashboardBroadcaster()
        ws = AsyncMock()
        broadcaster._connections["ws-1"].add(ws)

        await broadcaster.handle_event("unknown.event", {"workspace_id": "ws-1"})

        ws.send_json.assert_not_awaited()

    async def test_handle_event_ignores_missing_workspace(self):
        """Events without workspace_id should be ignored."""
        from app.api.dashboard_ws import DashboardBroadcaster

        broadcaster = DashboardBroadcaster()
        await broadcaster.handle_event("message.created", {"response": "hello"})
        # No error — silently skipped
