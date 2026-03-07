"""
Dashboard real-time WebSocket + SSE fallback endpoints.

WebSocket:  /api/v1/dashboard/live?token=JWT
SSE:        /api/v1/dashboard/live-sse?token=JWT

Events are published by the DashboardBroadcaster, which subscribes to
the application EventBus and projects events into dashboard-ready payloads.
"""

import asyncio
import json
from collections import defaultdict
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_from_token
from app.core.dashboard_connection_registry import (
    ConnectionLimitExceeded,
    DashboardConnectionRegistry,
)
from app.core.dashboard_events import (
    EventPriority,
    project_conversation_started,
    project_escalation_event,
    project_message_event,
)
from app.core.redis import get_redis_client
from app.dependencies import get_db
from app.models.conversation import Conversation

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["dashboard-live"])


# ---------------------------------------------------------------------------
# Broadcaster — connects EventBus → WebSocket clients
# ---------------------------------------------------------------------------


class DashboardBroadcaster:
    """Broadcasts dashboard events to connected WebSocket clients."""

    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)  # workspace_id → WebSockets
        self._registry = DashboardConnectionRegistry(get_redis_client())
        self._connection_ids: dict[int, str] = {}  # id(ws) → connection_id

    @property
    def registry(self) -> DashboardConnectionRegistry:
        return self._registry

    async def connect(self, workspace_id: str, user_id: str, websocket: WebSocket) -> str:
        """Register a WebSocket connection. Returns connection_id."""
        connection_id = await self._registry.register(workspace_id, user_id)
        self._connections[workspace_id].add(websocket)
        self._connection_ids[id(websocket)] = connection_id
        self._registry._local_connections[connection_id] = websocket
        return connection_id

    async def disconnect(self, workspace_id: str, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        self._connections[workspace_id].discard(websocket)
        if not self._connections[workspace_id]:
            del self._connections[workspace_id]

        connection_id = self._connection_ids.pop(id(websocket), None)
        if connection_id:
            await self._registry.unregister(connection_id)

    async def broadcast(self, workspace_id: str, event: dict[str, Any]) -> None:
        """Send event to all connected clients for a workspace."""
        clients = list(self._connections.get(workspace_id, []))
        if not clients:
            return

        dead = []
        for ws in clients:
            try:
                await ws.send_json(event)
            except (WebSocketDisconnect, RuntimeError):
                dead.append(ws)
            except Exception as e:
                logger.debug("dashboard_broadcast.send_failed", error=str(e))
                dead.append(ws)

        # Cleanup dead connections
        for ws in dead:
            await self.disconnect(workspace_id, ws)

    async def handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        """EventBus handler — project and broadcast dashboard events."""
        workspace_id = data.get("workspace_id")
        if not workspace_id:
            return

        # Project event based on type
        from app.core.event_bus import EventTypes

        projectors = {
            EventTypes.MESSAGE_CREATED: project_message_event,
            EventTypes.CONVERSATION_STARTED: project_conversation_started,
            EventTypes.CONVERSATION_ESCALATED: project_escalation_event,
        }

        projector = projectors.get(event_type)
        if not projector:
            return

        dashboard_event = projector(data)
        await self.broadcast(workspace_id, dashboard_event)

    def get_connection_id(self, websocket: WebSocket) -> str | None:
        """Get the connection_id for a WebSocket instance."""
        return self._connection_ids.get(id(websocket))


# Module-level singleton
_broadcaster: DashboardBroadcaster | None = None


def get_broadcaster() -> DashboardBroadcaster:
    """Get or create the dashboard broadcaster singleton."""
    global _broadcaster  # noqa: PLW0603
    if _broadcaster is None:
        _broadcaster = DashboardBroadcaster()
    return _broadcaster


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/api/v1/dashboard/live")
async def dashboard_live_feed(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Real-time dashboard feed via WebSocket.

    Auth: Pass JWT token as query parameter.
    Events: message, conversation_started, escalation, metrics_update
    Client can send "ping" to receive "pong" keepalive.
    """
    await websocket.accept()

    from app.main import active_websockets

    active_websockets.add(websocket)

    broadcaster = get_broadcaster()
    workspace_id: str | None = None

    try:
        # Authenticate
        user = await get_current_user_from_token(token, db)
        workspace_id = str(user.workspace_id)

        # Register connection (enforces limits)
        connection_id = await broadcaster.connect(workspace_id, str(user.id), websocket)

        # Send initial metrics snapshot
        snapshot = await _get_metrics_snapshot(workspace_id, db)
        await websocket.send_json(snapshot)

        # Heartbeat task
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(30)
                await broadcaster.registry.heartbeat(connection_id)

        heartbeat_task = asyncio.create_task(heartbeat_loop())

        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            pass
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    except ConnectionLimitExceeded as e:
        try:
            await websocket.send_json({"error": str(e)})
            await websocket.close(code=1008)
        except Exception:
            pass
    except Exception as e:
        logger.warning("dashboard_ws.auth_failed", error=str(e))
        try:
            await websocket.send_json({"error": "unauthorized"})
            await websocket.close(code=1008)
        except Exception:
            pass
    finally:
        active_websockets.discard(websocket)
        if workspace_id:
            await broadcaster.disconnect(workspace_id, websocket)


# ---------------------------------------------------------------------------
# SSE fallback endpoint
# ---------------------------------------------------------------------------


@router.get("/api/v1/dashboard/live-sse")
async def dashboard_live_sse(
    request: Request,
    token: str = Query(..., description="JWT authentication token"),
    db: AsyncSession = Depends(get_db),
):
    """
    SSE fallback for browsers that can't use WebSocket.

    Uses asyncio.Queue to bridge between EventBus callbacks and SSE generator.
    """
    # Authenticate
    user = await get_current_user_from_token(token, db)
    workspace_id = str(user.workspace_id)

    async def event_generator():
        event_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=100)

        async def on_event(event_type: str, data: dict[str, Any]) -> None:
            """EventBus callback — push dashboard event into queue."""
            if data.get("workspace_id") != workspace_id:
                return

            from app.core.event_bus import EventTypes

            projectors = {
                EventTypes.MESSAGE_CREATED: project_message_event,
                EventTypes.CONVERSATION_STARTED: project_conversation_started,
                EventTypes.CONVERSATION_ESCALATED: project_escalation_event,
            }
            projector = projectors.get(event_type)
            if not projector:
                return

            try:
                event_queue.put_nowait(projector(data))
            except asyncio.QueueFull:
                logger.warning("dashboard_sse.queue_full", workspace_id=workspace_id)

        # Subscribe to events
        from app.core.event_bus import EventTypes

        event_bus = request.app.state.event_bus

        event_types = [
            EventTypes.MESSAGE_CREATED,
            EventTypes.CONVERSATION_STARTED,
            EventTypes.CONVERSATION_ESCALATED,
        ]
        for et in event_types:
            await event_bus.subscribe(et, on_event)

        try:
            # Send initial metrics
            snapshot = await _get_metrics_snapshot(workspace_id, db)
            yield f"data: {json.dumps(snapshot)}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=30)
                    yield f"data: {json.dumps(event)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            for et in event_types:
                await event_bus.unsubscribe(et, on_event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_metrics_snapshot(workspace_id: str, db: AsyncSession) -> dict[str, Any]:
    """Build initial metrics snapshot for a workspace."""
    try:
        active_count = (
            await db.scalar(
                select(func.count(Conversation.id)).where(
                    Conversation.workspace_id == workspace_id,
                    Conversation.status == "active",
                )
            )
        ) or 0

        return {
            "type": "metrics",
            "priority": EventPriority.LOW,
            "active_conversations": active_count,
        }
    except Exception as e:
        logger.warning("dashboard_ws.snapshot_error", error=str(e))
        return {"type": "metrics", "priority": EventPriority.LOW, "active_conversations": 0}
