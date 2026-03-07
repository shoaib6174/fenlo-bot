"""
Action Dispatcher — Event-to-Webhook Matching Engine

Subscribes to event bus events and creates webhook outbox entries
when matching active webhook actions are found.

Architecture (S49 Spec Panel C-01):
  Event Bus → ActionDispatcher (sync: match + DB write) → WebhookOutbox (pending)
                                                         ↓
                                           ARQ Worker (async: HTTP POST + retry)

This dispatcher runs synchronously in the event handler context.
It performs fast DB read + write operations to queue webhooks for delivery.
The actual HTTP POST happens asynchronously in the ARQ worker to avoid blocking
the conversation pipeline.
"""

import json
import time
from typing import Any
from uuid import UUID

import structlog
from arq.connections import ArqRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.models.channel import WebhookAction, WebhookOutbox

logger = structlog.get_logger(__name__)


class ActionDispatcher:
    """
    Event-to-webhook action matcher.

    Subscribes to all events on the event bus. For each event:
    1. Queries WebhookAction table for matching active actions in the workspace
    2. For each match, inserts a WebhookOutbox entry with status=pending
    3. Enqueues an ARQ job to deliver the webhook (fast path)

    The sweep cron (worker.py) provides a fallback if the ARQ enqueue fails.
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_session_factory: Any,
        arq_pool: ArqRedis | None = None,
    ):
        """
        Initialize action dispatcher.

        Args:
            event_bus: Event bus instance to subscribe to
            db_session_factory: Async session factory for DB queries
            arq_pool: ARQ Redis pool for enqueuing webhook jobs (optional)
        """
        self.event_bus = event_bus
        self.db_session_factory = db_session_factory
        self.arq_pool = arq_pool

    async def start(self) -> None:
        """
        Start listening to all events.

        This should be called during application startup (main.py lifespan).
        """
        # Subscribe to all common event types
        # NOTE: This uses a wildcard pattern - we match event_type at runtime
        # For now, subscribe to each known event type individually
        from app.core.event_bus import EventTypes

        event_types = [
            EventTypes.MESSAGE_CREATED,
            EventTypes.CONVERSATION_STARTED,
            EventTypes.CONVERSATION_ESCALATED,
            EventTypes.SENTIMENT_NEGATIVE,
            EventTypes.LEAD_QUALIFIED,
            EventTypes.TOKEN_BUDGET_WARNING,
            EventTypes.TOKEN_BUDGET_EXHAUSTED,
            EventTypes.DOCUMENT_UPLOADED,
            EventTypes.DOCUMENT_PROCESSED,
            EventTypes.KNOWLEDGE_GAP_DETECTED,
            EventTypes.QUALITY_ALERT,
            # Webhook events themselves are not dispatched to avoid loops
            # EventTypes.WEBHOOK_DELIVERED,
            # EventTypes.WEBHOOK_FAILED,
        ]

        for event_type in event_types:
            await self.event_bus.subscribe(event_type, self._handle_event)

        logger.info(
            "action_dispatcher.started",
            subscribed_events=len(event_types),
        )

    async def _handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Handle an incoming event from the event bus.

        This is the core dispatch logic:
        1. Extract workspace_id from event data
        2. Query WebhookAction for matches (trigger_event == event_type, is_active=True)
        3. For each match, create a WebhookOutbox entry
        4. Enqueue ARQ job for immediate delivery (fast path)

        Args:
            event_type: Type of event (e.g., "message.created")
            data: Event payload with workspace_id and other context
        """
        start_time = time.time()

        # Extract workspace_id (required for scoping)
        workspace_id_str = data.get("workspace_id")
        if not workspace_id_str:
            logger.warning(
                "action_dispatcher.no_workspace_id",
                event_type=event_type,
            )
            return

        try:
            workspace_id = UUID(workspace_id_str)
        except (ValueError, TypeError):
            logger.warning(
                "action_dispatcher.invalid_workspace_id",
                event_type=event_type,
                workspace_id=workspace_id_str,
            )
            return

        async with self.db_session_factory() as session:
            try:
                # Find matching active webhook actions
                matching_actions = await self._find_matching_actions(
                    session, event_type, workspace_id
                )

                if not matching_actions:
                    logger.debug(
                        "action_dispatcher.no_matches",
                        event_type=event_type,
                        workspace_id=str(workspace_id),
                    )
                    return

                # Create outbox entries (fan-out: N actions → N outbox entries)
                outbox_ids = await self._create_outbox_entries(
                    session, matching_actions, event_type, workspace_id, data
                )

                await session.commit()

                # Enqueue ARQ jobs for immediate delivery (fast path)
                if self.arq_pool:
                    for outbox_id in outbox_ids:
                        try:
                            await self.arq_pool.enqueue_job(
                                "send_webhook",
                                str(outbox_id),
                                _defer_by=0,  # Immediate pickup for webhooks
                            )
                        except Exception as e:
                            logger.warning(
                                "action_dispatcher.enqueue_failed",
                                outbox_id=str(outbox_id),
                                error=str(e),
                                msg="Webhook will be picked up by sweep cron instead",
                            )

                duration_ms = round((time.time() - start_time) * 1000, 2)
                logger.info(
                    "action_dispatcher.dispatched",
                    event_type=event_type,
                    workspace_id=str(workspace_id),
                    matches=len(matching_actions),
                    outbox_entries=len(outbox_ids),
                    duration_ms=duration_ms,
                )

            except Exception as e:
                await session.rollback()
                logger.error(
                    "action_dispatcher.error",
                    event_type=event_type,
                    workspace_id=str(workspace_id),
                    error=str(e),
                    exc_info=True,
                )

    async def _find_matching_actions(
        self, session: AsyncSession, event_type: str, workspace_id: UUID
    ) -> list[WebhookAction]:
        """
        Find active webhook actions matching the event type and workspace.

        Args:
            session: DB session
            event_type: Event type to match
            workspace_id: Workspace ID for scoping

        Returns:
            List of matching WebhookAction instances
        """
        stmt = select(WebhookAction).where(
            WebhookAction.workspace_id == workspace_id,
            WebhookAction.trigger_event == event_type,
            WebhookAction.is_active == True,  # noqa: E712
        )

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def _create_outbox_entries(
        self,
        session: AsyncSession,
        actions: list[WebhookAction],
        event_type: str,
        workspace_id: UUID,
        event_data: dict[str, Any],
    ) -> list[UUID]:
        """
        Create webhook outbox entries for each matching action.

        This implements the fan-out pattern: N matching actions → N outbox entries.
        Each entry is delivered independently with its own retry lifecycle.

        Args:
            session: DB session
            actions: List of matching webhook actions
            event_type: Event type that triggered this
            workspace_id: Workspace ID for scoping
            event_data: Full event payload for template rendering

        Returns:
            List of created outbox entry IDs
        """
        outbox_ids = []

        for action in actions:
            # Render payload template (safe substitution)
            payload = self._render_payload_template(action, event_type, event_data)

            # Extract target URL from config
            target_url = action.config.get("url", "")
            if not target_url:
                logger.warning(
                    "action_dispatcher.no_target_url",
                    action_id=str(action.id),
                    event_type=event_type,
                )
                continue

            # Create outbox entry
            outbox = WebhookOutbox(
                workspace_id=workspace_id,
                event_type=event_type,
                payload=payload,
                target_url=target_url,
                status="pending",
                retry_count=0,
                max_retries=3,  # TODO: Use config.webhook_max_retries
            )

            session.add(outbox)
            await session.flush()  # Get the ID

            outbox_ids.append(outbox.id)

        return outbox_ids

    def _render_payload_template(
        self,
        action: WebhookAction,
        event_type: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Render payload template with event data.

        Uses Python str.format_map() with safe substitution (S49 Spec Panel R-03).
        Unknown variables are left as literal text (no KeyError).

        Available template variables:
        - {event_type}
        - {workspace_id}
        - {conversation_id}
        - {lead_score}
        - {timestamp}
        - {message_content}
        - {sentiment}
        - {intent}

        Args:
            action: Webhook action with payload template
            event_type: Event type
            event_data: Event payload

        Returns:
            Rendered payload as dict
        """
        # Get payload template from config
        template_str = action.config.get("payload_template")

        if not template_str:
            # No template — use raw event data
            return event_data

        # Build template variables
        template_vars = {
            "event_type": event_type,
            "workspace_id": event_data.get("workspace_id", ""),
            "conversation_id": event_data.get("conversation_id", ""),
            "lead_score": event_data.get("lead_score", ""),
            "timestamp": str(int(time.time())),
            "message_content": event_data.get("message", ""),
            "sentiment": event_data.get("sentiment", ""),
            "intent": event_data.get("intent", ""),
        }

        # Render template (safe substitution)
        try:
            # Create a SafeDict that returns the key itself for missing values
            class SafeDict(dict):
                def __missing__(self, key):
                    return f"{{{key}}}"  # Leave unknown variables as literals

            rendered = template_str.format_map(SafeDict(template_vars))

            # Parse as JSON if possible, otherwise return as string
            try:
                return json.loads(rendered)
            except json.JSONDecodeError:
                logger.warning(
                    "action_dispatcher.template_render_invalid_json",
                    action_id=str(action.id),
                    template=template_str,
                    msg="Payload template did not produce valid JSON — using raw event data",
                )
                return event_data

        except Exception as e:
            logger.warning(
                "action_dispatcher.template_render_error",
                action_id=str(action.id),
                error=str(e),
                msg="Template rendering failed — using raw event data",
            )
            return event_data
