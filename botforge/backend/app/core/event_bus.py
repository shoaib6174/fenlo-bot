"""
Event bus with swappable backend (in-process now, Redis Streams later).

This module provides a protocol-based event bus that allows subscribers
to react to events without tight coupling. The backend can be swapped
from in-process (single instance) to Redis Streams (multi-instance)
without changing subscriber code.
"""

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Protocol

import structlog

if TYPE_CHECKING:
    from app.config import Settings

logger = structlog.get_logger()


EventHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


class EventBus(Protocol):
    """
    Protocol for event bus implementations.

    Allows swapping between in-process and distributed backends
    without changing consumer code.
    """

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event_type: Type of event (e.g., "message.created")
            data: Event payload
        """
        ...

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Async function to call when event is published
        """
        ...

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        ...


class InProcessEventBus:
    """
    In-process event bus for single-instance deployments.

    Events are delivered to handlers in the same process.
    This is suitable for development and single-instance production.

    For multi-instance production, use RedisStreamsEventBus.
    """

    def __init__(self):
        """Initialize in-process event bus."""
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Publish event to all subscribers in this process.

        Handlers are called concurrently. If a handler raises an exception,
        it's logged but doesn't prevent other handlers from executing.

        Args:
            event_type: Type of event
            data: Event payload
        """
        async with self._lock:
            handlers = self._subscribers.get(event_type, []).copy()

        if not handlers:
            logger.debug("event_published_no_subscribers", event_type=event_type)
            return

        logger.debug(
            "event_published",
            event_type=event_type,
            subscriber_count=len(handlers),
            data_keys=list(data.keys()),
        )

        # Call all handlers concurrently
        tasks = []
        for handler in handlers:
            tasks.append(self._safe_call_handler(handler, event_type, data))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call_handler(
        self, handler: EventHandler, event_type: str, data: dict[str, Any]
    ) -> None:
        """
        Call handler with exception safety.

        Args:
            handler: Event handler function
            event_type: Type of event
            data: Event payload
        """
        try:
            await handler(event_type, data)
        except Exception as e:
            logger.error(
                "event_handler_error",
                event_type=event_type,
                handler=handler.__name__,
                error=str(e),
                exc_info=True,
            )

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Async function to call when event is published
        """
        async with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.debug(
                    "event_subscriber_added",
                    event_type=event_type,
                    handler=handler.__name__,
                    total_subscribers=len(self._subscribers[event_type]),
                )

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        async with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                logger.debug(
                    "event_subscriber_removed",
                    event_type=event_type,
                    handler=handler.__name__,
                    remaining_subscribers=len(self._subscribers[event_type]),
                )


class RedisStreamsEventBus:
    """
    Redis Streams-based event bus for multi-instance deployments.

    This implementation will be completed in Stage 2+ when scaling
    to multiple backend instances. The interface matches EventBus protocol
    so swapping is transparent to consumers.

    For now, this is a placeholder that raises NotImplementedError.
    """

    def __init__(self, redis_url: str):
        """
        Initialize Redis Streams event bus.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        # TODO: Initialize Redis connection pool
        raise NotImplementedError(
            "RedisStreamsEventBus will be implemented in Stage 2+ for multi-instance scaling"
        )

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish event to Redis stream."""
        raise NotImplementedError("Redis Streams backend not yet implemented")

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to Redis stream."""
        raise NotImplementedError("Redis Streams backend not yet implemented")

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from Redis stream."""
        raise NotImplementedError("Redis Streams backend not yet implemented")


def create_event_bus(settings: "Settings") -> EventBus:
    """
    Factory function to create appropriate event bus backend.

    Args:
        settings: Application settings

    Returns:
        EventBus implementation (InProcess or RedisStreams)
    """
    # For Phase 1, always use in-process
    # In Stage 2+, check settings.event_bus_backend
    backend = getattr(settings, "event_bus_backend", "in_process")

    if backend == "redis":
        return RedisStreamsEventBus(settings.redis_url)

    return InProcessEventBus()


# Common event types
class EventTypes:
    """Standard event type constants."""

    MESSAGE_CREATED = "message.created"
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_ESCALATED = "conversation.escalated"
    SENTIMENT_NEGATIVE = "sentiment.negative"
    LEAD_QUALIFIED = "lead.qualified"
    TOKEN_BUDGET_WARNING = "token.budget_warning"
    TOKEN_BUDGET_EXHAUSTED = "token.budget_exhausted"
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed"
    KNOWLEDGE_GAP_DETECTED = "knowledge_gap.detected"
    # Phase 4: Webhooks & Channels
    WEBHOOK_DELIVERY_REQUIRED = "webhook.delivery_required"
    WEBHOOK_DELIVERED = "webhook.delivered"
    WEBHOOK_FAILED = "webhook.failed"
    HANDOFF_INITIATED = "handoff.initiated"
    MESSAGE_DELIVERY_STATUS = "message.delivery_status"
    # Phase 8: Zapier integration
    QUALITY_ALERT = "quality.alert"


class EventPublishStep:
    """
    Pipeline step that publishes message.created event.

    This step should run near the end of the pipeline after all
    metadata (sentiment, intent, quality_score) has been computed.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initialize event publish step.

        Args:
            event_bus: Event bus instance to publish to
        """
        self.event_bus = event_bus

    async def execute(self, context) -> Any:
        """
        Publish message.created event with full context.

        Args:
            context: Message context from pipeline

        Returns:
            Unmodified context
        """

        # Only publish if we have a response
        if not context.response:
            return context

        event_data = {
            "workspace_id": str(context.workspace_id),
            "user_id": str(context.user_id) if context.user_id else None,
            "conversation_id": str(context.conversation_id) if context.conversation_id else None,
            "message": context.metadata.get("original_message", context.message),
            "response": context.response,
            "sentiment": context.sentiment,
            "intent": context.intent,
            "quality_score": context.quality_score,
            "tokens_used": context.tokens_used,
            "provider_used": context.provider_used,
            "lead_score": context.lead_score,
        }

        # Publish asynchronously (don't wait for subscribers)
        asyncio.create_task(self.event_bus.publish(EventTypes.MESSAGE_CREATED, event_data))

        return context
