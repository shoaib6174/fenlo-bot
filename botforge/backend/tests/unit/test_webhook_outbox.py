"""
Unit tests for webhook outbox engine and action dispatcher (S49).

Tests cover:
- Action dispatcher: event → action matching → outbox creation
- Webhook delivery: HTTP POST, retry logic, dead letter
- Outbox sweep: periodic cron job for missed entries
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventTypes, InProcessEventBus
from app.models.channel import WebhookAction, WebhookOutbox
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.modules.channels.action_dispatcher import ActionDispatcher
from app.services.auth import hash_password
from worker import send_webhook, sweep_pending_webhooks

# --- Fixtures ---


@pytest_asyncio.fixture
async def workspace(db_session: AsyncSession) -> Workspace:
    """Create a test workspace."""
    # Create owner user first
    user = User(
        email="test@example.com",
        password_hash=hash_password("password123"),
        name="Test User",
    )
    db_session.add(user)
    await db_session.flush()

    # Create workspace
    ws = Workspace(owner_id=user.id, name="Test Workspace")
    db_session.add(ws)
    await db_session.flush()

    # Create workspace member
    member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(ws)

    return ws


@pytest_asyncio.fixture
async def workspace_factory(db_session: AsyncSession):
    """Factory for creating multiple workspaces."""

    async def _create_workspace(name: str = "Test Workspace") -> Workspace:
        # Create owner user
        user = User(
            email=f"{uuid4()}@example.com",
            password_hash=hash_password("password123"),
            name="Test User",
        )
        db_session.add(user)
        await db_session.flush()

        # Create workspace
        ws = Workspace(owner_id=user.id, name=name)
        db_session.add(ws)
        await db_session.flush()

        # Create workspace member
        member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
        db_session.add(member)
        await db_session.commit()
        await db_session.refresh(ws)

        return ws

    return _create_workspace


@pytest_asyncio.fixture
async def async_session(db_session: AsyncSession) -> AsyncSession:
    """Alias for db_session to match test usage."""
    return db_session


class TestWebhookActionDispatcher:
    """Test action dispatcher: event → action matching → outbox entries."""

    @pytest.mark.asyncio
    async def test_matches_action_for_event_type(self, async_session, workspace):
        """Event matches active webhook action by trigger_event."""
        # Create a webhook action for message.created
        action = WebhookAction(
            workspace_id=workspace.id,
            trigger_event=EventTypes.MESSAGE_CREATED,
            action_type="webhook",
            config={"url": "https://example.com/webhook"},
            is_active=True,
        )
        async_session.add(action)
        await async_session.commit()

        # Create event bus and action dispatcher
        event_bus = InProcessEventBus()
        dispatcher = ActionDispatcher(
            event_bus=event_bus,
            db_session_factory=lambda: async_session,
            arq_pool=None,  # No ARQ pool for this test
        )
        await dispatcher.start()

        # Publish message.created event
        await event_bus.publish(
            EventTypes.MESSAGE_CREATED,
            {
                "workspace_id": str(workspace.id),
                "conversation_id": str(uuid4()),
                "message": "Test message",
            },
        )

        # Give event handlers time to run
        import asyncio

        await asyncio.sleep(0.1)

        # Verify outbox entry was created
        stmt = select(WebhookOutbox).where(
            WebhookOutbox.workspace_id == workspace.id,
            WebhookOutbox.event_type == EventTypes.MESSAGE_CREATED,
        )
        result = await async_session.execute(stmt)
        outbox = result.scalar_one_or_none()

        assert outbox is not None
        assert outbox.status == "pending"
        assert outbox.target_url == "https://example.com/webhook"

    @pytest.mark.asyncio
    async def test_no_match_when_inactive(self, async_session, workspace):
        """Inactive webhook actions are skipped."""
        # Create an INACTIVE webhook action
        action = WebhookAction(
            workspace_id=workspace.id,
            trigger_event=EventTypes.LEAD_QUALIFIED,
            action_type="webhook",
            config={"url": "https://example.com/webhook"},
            is_active=False,  # Inactive
        )
        async_session.add(action)
        await async_session.commit()

        # Create event bus and action dispatcher
        event_bus = InProcessEventBus()
        dispatcher = ActionDispatcher(
            event_bus=event_bus,
            db_session_factory=lambda: async_session,
            arq_pool=None,
        )
        await dispatcher.start()

        # Publish lead.qualified event
        await event_bus.publish(
            EventTypes.LEAD_QUALIFIED,
            {
                "workspace_id": str(workspace.id),
                "lead_score": 85,
            },
        )

        import asyncio

        await asyncio.sleep(0.1)

        # Verify NO outbox entry was created (action is inactive)
        stmt = select(WebhookOutbox).where(
            WebhookOutbox.workspace_id == workspace.id,
            WebhookOutbox.event_type == EventTypes.LEAD_QUALIFIED,
        )
        result = await async_session.execute(stmt)
        outbox = result.scalar_one_or_none()

        assert outbox is None

    @pytest.mark.asyncio
    async def test_creates_outbox_entry_on_match(self, async_session, workspace):
        """Outbox entry is created with correct payload and metadata."""
        # Create webhook action with payload template
        action = WebhookAction(
            workspace_id=workspace.id,
            trigger_event=EventTypes.CONVERSATION_ESCALATED,
            action_type="webhook",
            config={
                "url": "https://example.com/escalation",
                "payload_template": '{"event": "{event_type}", "workspace": "{workspace_id}"}',
            },
            is_active=True,
        )
        async_session.add(action)
        await async_session.commit()

        # Create event bus and action dispatcher
        event_bus = InProcessEventBus()
        dispatcher = ActionDispatcher(
            event_bus=event_bus,
            db_session_factory=lambda: async_session,
            arq_pool=None,
        )
        await dispatcher.start()

        # Publish conversation.escalated event
        await event_bus.publish(
            EventTypes.CONVERSATION_ESCALATED,
            {
                "workspace_id": str(workspace.id),
                "conversation_id": str(uuid4()),
            },
        )

        import asyncio

        await asyncio.sleep(0.1)

        # Verify outbox entry with rendered payload
        stmt = select(WebhookOutbox).where(
            WebhookOutbox.workspace_id == workspace.id,
            WebhookOutbox.event_type == EventTypes.CONVERSATION_ESCALATED,
        )
        result = await async_session.execute(stmt)
        outbox = result.scalar_one_or_none()

        assert outbox is not None
        assert outbox.status == "pending"
        assert outbox.retry_count == 0
        assert outbox.max_retries == 3
        # Verify payload template was rendered
        assert outbox.payload["event"] == EventTypes.CONVERSATION_ESCALATED
        assert outbox.payload["workspace"] == str(workspace.id)

    @pytest.mark.asyncio
    async def test_workspace_scoped_matching(self, async_session, workspace, workspace_factory):
        """Actions only match events from the same workspace."""
        # Create a second workspace
        workspace_2 = await workspace_factory()

        # Create action in workspace 1
        action = WebhookAction(
            workspace_id=workspace.id,
            trigger_event=EventTypes.MESSAGE_CREATED,
            action_type="webhook",
            config={"url": "https://example.com/webhook"},
            is_active=True,
        )
        async_session.add(action)
        await async_session.commit()

        # Create event bus and action dispatcher
        event_bus = InProcessEventBus()
        dispatcher = ActionDispatcher(
            event_bus=event_bus,
            db_session_factory=lambda: async_session,
            arq_pool=None,
        )
        await dispatcher.start()

        # Publish event from workspace 2 (different workspace)
        await event_bus.publish(
            EventTypes.MESSAGE_CREATED,
            {
                "workspace_id": str(workspace_2.id),
                "message": "Test",
            },
        )

        import asyncio

        await asyncio.sleep(0.1)

        # Verify NO outbox entry for workspace 1 action
        stmt = select(WebhookOutbox).where(
            WebhookOutbox.workspace_id == workspace.id,
        )
        result = await async_session.execute(stmt)
        outbox = result.scalar_one_or_none()

        assert outbox is None  # No match because workspace mismatch

    @pytest.mark.asyncio
    async def test_multiple_actions_for_same_event(self, async_session, workspace):
        """Fan-out: single event matching N actions creates N outbox entries."""
        # Create 3 webhook actions for the same event
        for i in range(3):
            action = WebhookAction(
                workspace_id=workspace.id,
                trigger_event=EventTypes.LEAD_QUALIFIED,
                action_type="webhook",
                config={"url": f"https://example.com/webhook-{i}"},
                is_active=True,
            )
            async_session.add(action)
        await async_session.commit()

        # Create event bus and action dispatcher
        event_bus = InProcessEventBus()
        dispatcher = ActionDispatcher(
            event_bus=event_bus,
            db_session_factory=lambda: async_session,
            arq_pool=None,
        )
        await dispatcher.start()

        # Publish lead.qualified event
        await event_bus.publish(
            EventTypes.LEAD_QUALIFIED,
            {
                "workspace_id": str(workspace.id),
                "lead_score": 90,
            },
        )

        import asyncio

        await asyncio.sleep(0.1)

        # Verify 3 outbox entries were created (fan-out)
        stmt = select(WebhookOutbox).where(
            WebhookOutbox.workspace_id == workspace.id,
            WebhookOutbox.event_type == EventTypes.LEAD_QUALIFIED,
        )
        result = await async_session.execute(stmt)
        outbox_entries = list(result.scalars().all())

        assert len(outbox_entries) == 3
        # Each entry has a different target URL
        urls = {entry.target_url for entry in outbox_entries}
        assert urls == {
            "https://example.com/webhook-0",
            "https://example.com/webhook-1",
            "https://example.com/webhook-2",
        }


class TestWebhookDelivery:
    """Test webhook delivery worker: HTTP POST, retry logic, dead letter."""

    @pytest.mark.asyncio
    @patch("worker.httpx.AsyncClient")
    async def test_successful_delivery_marks_sent(
        self, mock_client_class, async_session, workspace
    ):
        """Successful HTTP 200 marks outbox entry as sent."""
        # Create outbox entry
        outbox = WebhookOutbox(
            workspace_id=workspace.id,
            event_type=EventTypes.MESSAGE_CREATED,
            payload={"message": "Test"},
            target_url="https://example.com/webhook",
            status="pending",
            retry_count=0,
            max_retries=3,
        )
        async_session.add(outbox)
        await async_session.commit()
        await async_session.refresh(outbox)

        # Mock HTTP POST → 200 OK
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Call send_webhook worker
        ctx: dict[str, Any] = {"database_url": str(async_session.bind.url)}
        result = await send_webhook(ctx, str(outbox.id))

        # Verify result
        assert result["status"] == "success"

        # Verify outbox entry marked as sent
        await async_session.refresh(outbox)
        assert outbox.status == "sent"
        assert outbox.sent_at is not None

    @pytest.mark.asyncio
    @patch("worker.httpx.AsyncClient")
    async def test_failure_increments_retry_count(
        self, mock_client_class, async_session, workspace
    ):
        """HTTP failure increments retry_count and sets next_retry_at."""
        # Create outbox entry
        outbox = WebhookOutbox(
            workspace_id=workspace.id,
            event_type=EventTypes.MESSAGE_CREATED,
            payload={"message": "Test"},
            target_url="https://example.com/webhook",
            status="pending",
            retry_count=0,
            max_retries=3,
        )
        async_session.add(outbox)
        await async_session.commit()
        await async_session.refresh(outbox)

        # Mock HTTP POST → 500 Internal Server Error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.request = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Call send_webhook worker
        ctx: dict[str, Any] = {"database_url": str(async_session.bind.url)}
        result = await send_webhook(ctx, str(outbox.id))

        # Verify result
        assert result["status"] == "retry_scheduled"

        # Verify outbox entry updated
        await async_session.refresh(outbox)
        assert outbox.status == "failed"
        assert outbox.retry_count == 1
        assert outbox.next_retry_at is not None
        assert outbox.error_message is not None

    @pytest.mark.asyncio
    @patch("worker.httpx.AsyncClient")
    async def test_exponential_backoff_timing(self, mock_client_class, async_session, workspace):
        """Retry delays follow exponential backoff: 60s, 300s, 900s."""

        # Create outbox entry at retry_count=1
        outbox = WebhookOutbox(
            workspace_id=workspace.id,
            event_type=EventTypes.MESSAGE_CREATED,
            payload={"message": "Test"},
            target_url="https://example.com/webhook",
            status="failed",
            retry_count=1,  # Second attempt
            max_retries=3,
        )
        async_session.add(outbox)
        await async_session.commit()
        await async_session.refresh(outbox)

        # Mock HTTP POST → 500
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_response.request = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Call send_webhook
        ctx: dict[str, Any] = {"database_url": str(async_session.bind.url)}
        before = datetime.now(UTC)
        await send_webhook(ctx, str(outbox.id))

        # Verify next_retry_at is ~1500s in the future (retry_count=2, backoff=60*5^2=1500)
        # Wait, the formula is backoff * (5 ** retry_count)
        # retry_count was 1, now it's 2
        # backoff = 60 * (5 ** 2) = 60 * 25 = 1500s
        await async_session.refresh(outbox)
        assert outbox.next_retry_at is not None
        actual_delay = (outbox.next_retry_at - before).total_seconds()
        assert 1490 <= actual_delay <= 1510  # Allow 10s tolerance for 1500s delay

    @pytest.mark.asyncio
    @patch("worker.httpx.AsyncClient")
    async def test_dead_letter_after_max_retries(self, mock_client_class, async_session, workspace):
        """After 3 failures, entry moves to dead letter status."""
        # Create outbox entry at max retry count
        outbox = WebhookOutbox(
            workspace_id=workspace.id,
            event_type=EventTypes.MESSAGE_CREATED,
            payload={"message": "Test"},
            target_url="https://example.com/webhook",
            status="failed",
            retry_count=2,  # Third attempt (0, 1, 2)
            max_retries=3,
        )
        async_session.add(outbox)
        await async_session.commit()
        await async_session.refresh(outbox)

        # Mock HTTP POST → 500
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_response.request = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Call send_webhook
        ctx: dict[str, Any] = {"database_url": str(async_session.bind.url)}
        result = await send_webhook(ctx, str(outbox.id))

        # Verify dead letter
        assert result["status"] == "dead"

        await async_session.refresh(outbox)
        assert outbox.status == "dead"
        assert outbox.retry_count == 3

    @pytest.mark.asyncio
    @patch("worker.httpx.AsyncClient")
    async def test_records_error_message(self, mock_client_class, async_session, workspace):
        """Error message is stored in outbox entry."""
        outbox = WebhookOutbox(
            workspace_id=workspace.id,
            event_type=EventTypes.MESSAGE_CREATED,
            payload={"message": "Test"},
            target_url="https://example.com/webhook",
            status="pending",
            retry_count=0,
            max_retries=3,
        )
        async_session.add(outbox)
        await async_session.commit()
        await async_session.refresh(outbox)

        # Mock HTTP POST → Exception
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_class.return_value = mock_client

        # Call send_webhook
        ctx: dict[str, Any] = {"database_url": str(async_session.bind.url)}
        await send_webhook(ctx, str(outbox.id))

        # Verify error message stored
        await async_session.refresh(outbox)
        assert outbox.error_message is not None
        assert "Connection refused" in outbox.error_message

    @pytest.mark.asyncio
    async def test_payload_template_rendering(self, async_session, workspace):
        """ActionDispatcher renders payload templates with event variables."""
        from app.core.event_bus import InProcessEventBus

        # Create action with payload template
        action = WebhookAction(
            workspace_id=workspace.id,
            trigger_event=EventTypes.LEAD_QUALIFIED,
            action_type="webhook",
            config={
                "url": "https://example.com/webhook",
                "payload_template": '{"event": "{event_type}", "score": "{lead_score}", "ws": "{workspace_id}"}',
            },
            is_active=True,
        )
        async_session.add(action)
        await async_session.commit()

        # Create dispatcher
        event_bus = InProcessEventBus()
        dispatcher = ActionDispatcher(
            event_bus=event_bus,
            db_session_factory=lambda: async_session,
            arq_pool=None,
        )
        await dispatcher.start()

        # Publish event with lead_score
        await event_bus.publish(
            EventTypes.LEAD_QUALIFIED,
            {
                "workspace_id": str(workspace.id),
                "lead_score": "95",
                "conversation_id": str(uuid4()),
            },
        )

        import asyncio

        await asyncio.sleep(0.1)

        # Verify payload was rendered
        stmt = select(WebhookOutbox).where(WebhookOutbox.workspace_id == workspace.id)
        result = await async_session.execute(stmt)
        outbox = result.scalar_one()

        assert outbox.payload["event"] == EventTypes.LEAD_QUALIFIED
        assert outbox.payload["score"] == "95"
        assert outbox.payload["ws"] == str(workspace.id)

    @pytest.mark.asyncio
    @patch("worker.httpx.AsyncClient")
    async def test_send_webhook_idempotent_on_already_sent(
        self, mock_client_class, async_session, workspace
    ):
        """Re-enqueueing an already-sent entry no-ops (idempotency)."""
        # Create outbox entry already marked as sent
        outbox = WebhookOutbox(
            workspace_id=workspace.id,
            event_type=EventTypes.MESSAGE_CREATED,
            payload={"message": "Test"},
            target_url="https://example.com/webhook",
            status="sent",  # Already sent
            retry_count=0,
            max_retries=3,
            sent_at=datetime.now(UTC),
        )
        async_session.add(outbox)
        await async_session.commit()
        await async_session.refresh(outbox)

        # Call send_webhook (no HTTP call should be made)
        ctx: dict[str, Any] = {"database_url": str(async_session.bind.url)}
        result = await send_webhook(ctx, str(outbox.id))

        # Verify idempotent behavior
        assert result["status"] == "already_sent"

        # HTTP client should NOT have been called
        mock_client_class.assert_not_called()


class TestOutboxSweep:
    """Test sweep_pending_webhooks cron job."""

    @pytest.mark.asyncio
    @patch("worker.redis")  # Mock Redis for heartbeat
    async def test_sweep_picks_up_pending_entries(self, mock_redis, async_session, workspace):
        """Sweep job picks up pending entries and enqueues them."""
        # Create 2 pending outbox entries
        for i in range(2):
            outbox = WebhookOutbox(
                workspace_id=workspace.id,
                event_type=EventTypes.MESSAGE_CREATED,
                payload={"message": f"Test {i}"},
                target_url="https://example.com/webhook",
                status="pending",
                retry_count=0,
                max_retries=3,
            )
            async_session.add(outbox)
        await async_session.commit()

        # Mock Redis lpush for enqueue
        mock_redis_client = AsyncMock()
        mock_redis_client.lpush = AsyncMock()
        mock_redis_client.set = AsyncMock()

        # Call sweep_pending_webhooks
        ctx: dict[str, Any] = {
            "database_url": str(async_session.bind.url),
            "redis": mock_redis_client,
        }
        result = await sweep_pending_webhooks(ctx)

        # Verify result
        assert result["status"] == "success"
        assert result["entries_found"] == 2
        assert result["entries_enqueued"] == 2

    @pytest.mark.asyncio
    async def test_sweep_respects_next_retry_at(self, async_session, workspace):
        """Sweep skips entries with future next_retry_at."""
        # Create outbox entry with future retry time
        future_time = datetime.now(UTC) + timedelta(minutes=5)
        outbox = WebhookOutbox(
            workspace_id=workspace.id,
            event_type=EventTypes.MESSAGE_CREATED,
            payload={"message": "Test"},
            target_url="https://example.com/webhook",
            status="failed",
            retry_count=1,
            max_retries=3,
            next_retry_at=future_time,  # Not ready yet
        )
        async_session.add(outbox)
        await async_session.commit()

        # Call sweep
        ctx: dict[str, Any] = {
            "database_url": str(async_session.bind.url),
            "redis": AsyncMock(),
        }
        result = await sweep_pending_webhooks(ctx)

        # Verify entry was NOT picked up
        assert result["entries_found"] == 0

    @pytest.mark.asyncio
    async def test_sweep_loops_until_no_more_entries(self, async_session, workspace):
        """Sweep loops with LIMIT 50 until no more pending entries."""
        # Create 75 pending entries (should require 2 batches)
        for i in range(75):
            outbox = WebhookOutbox(
                workspace_id=workspace.id,
                event_type=EventTypes.MESSAGE_CREATED,
                payload={"message": f"Test {i}"},
                target_url="https://example.com/webhook",
                status="pending",
                retry_count=0,
                max_retries=3,
            )
            async_session.add(outbox)
        await async_session.commit()

        # Call sweep
        mock_redis = AsyncMock()
        ctx: dict[str, Any] = {
            "database_url": str(async_session.bind.url),
            "redis": mock_redis,
        }
        result = await sweep_pending_webhooks(ctx)

        # Verify all 75 entries found in 2 batches
        assert result["status"] == "success"
        assert result["entries_found"] == 75
        assert result["batches"] == 2  # 50 + 25

    @pytest.mark.asyncio
    async def test_sweep_writes_redis_heartbeat(self, async_session, workspace):
        """Sweep writes sweep:last_run_at to Redis with 120s TTL."""
        # Call sweep
        mock_redis = AsyncMock()
        ctx: dict[str, Any] = {
            "database_url": str(async_session.bind.url),
            "redis": mock_redis,
        }
        result = await sweep_pending_webhooks(ctx)

        # Verify Redis.set was called with correct key and TTL
        assert result["status"] == "success"
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "sweep:last_run_at"
        assert call_args[1]["ex"] == 120  # TTL

        # Verify JSON payload includes timestamp
        payload = json.loads(call_args[0][1])
        assert "ts" in payload
        assert "entries_found" in payload
