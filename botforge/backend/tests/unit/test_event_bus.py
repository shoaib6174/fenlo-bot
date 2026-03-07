"""Unit tests for EventBus."""

import asyncio
from typing import Any

import pytest

from app.core.event_bus import EventTypes, InProcessEventBus


@pytest.mark.asyncio
class TestInProcessEventBus:
    """Test InProcessEventBus behavior."""

    async def test_publish_calls_subscriber(self):
        """Test that publishing an event calls subscribed handler."""
        bus = InProcessEventBus()
        received_events = []

        async def handler(event_type: str, data: dict[str, Any]):
            received_events.append((event_type, data))

        await bus.subscribe("test.event", handler)
        await bus.publish("test.event", {"key": "value"})

        # Give async tasks time to complete
        await asyncio.sleep(0.1)

        assert len(received_events) == 1
        assert received_events[0][0] == "test.event"
        assert received_events[0][1]["key"] == "value"

    async def test_multiple_subscribers(self):
        """Test that multiple subscribers all receive events."""
        bus = InProcessEventBus()
        received_1 = []
        received_2 = []

        async def handler1(event_type: str, data: dict[str, Any]):
            received_1.append(data)

        async def handler2(event_type: str, data: dict[str, Any]):
            received_2.append(data)

        await bus.subscribe("test.event", handler1)
        await bus.subscribe("test.event", handler2)
        await bus.publish("test.event", {"msg": "hello"})

        await asyncio.sleep(0.1)

        assert len(received_1) == 1
        assert len(received_2) == 1
        assert received_1[0]["msg"] == "hello"
        assert received_2[0]["msg"] == "hello"

    async def test_no_subscriber_no_error(self):
        """Test that publishing with no subscribers doesn't error."""
        bus = InProcessEventBus()

        # Should not raise
        await bus.publish("nonexistent.event", {"data": "value"})

    async def test_subscriber_error_doesnt_block(self):
        """Test that error in one subscriber doesn't prevent others."""
        bus = InProcessEventBus()
        received = []

        async def failing_handler(event_type: str, data: dict[str, Any]):
            raise ValueError("Handler failed")

        async def working_handler(event_type: str, data: dict[str, Any]):
            received.append(data)

        await bus.subscribe("test.event", failing_handler)
        await bus.subscribe("test.event", working_handler)
        await bus.publish("test.event", {"msg": "test"})

        await asyncio.sleep(0.1)

        # Working handler should have received event despite failing handler
        assert len(received) == 1

    async def test_event_data_passed_correctly(self):
        """Test that complex event data is passed correctly."""
        bus = InProcessEventBus()
        received = []

        async def handler(event_type: str, data: dict[str, Any]):
            received.append(data)

        await bus.subscribe("test.event", handler)

        complex_data = {
            "string": "value",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
            "none": None,
        }

        await bus.publish("test.event", complex_data)
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0] == complex_data

    async def test_unsubscribe_works(self):
        """Test that unsubscribe removes handler."""
        bus = InProcessEventBus()
        received = []

        async def handler(event_type: str, data: dict[str, Any]):
            received.append(data)

        await bus.subscribe("test.event", handler)
        await bus.publish("test.event", {"msg": "first"})
        await asyncio.sleep(0.1)

        await bus.unsubscribe("test.event", handler)
        await bus.publish("test.event", {"msg": "second"})
        await asyncio.sleep(0.1)

        # Should only receive first event
        assert len(received) == 1
        assert received[0]["msg"] == "first"

    async def test_multiple_event_types(self):
        """Test subscribing to different event types."""
        bus = InProcessEventBus()
        received_type_a = []
        received_type_b = []

        async def handler_a(event_type: str, data: dict[str, Any]):
            received_type_a.append(data)

        async def handler_b(event_type: str, data: dict[str, Any]):
            received_type_b.append(data)

        await bus.subscribe("event.a", handler_a)
        await bus.subscribe("event.b", handler_b)

        await bus.publish("event.a", {"type": "a"})
        await bus.publish("event.b", {"type": "b"})
        await asyncio.sleep(0.1)

        assert len(received_type_a) == 1
        assert len(received_type_b) == 1
        assert received_type_a[0]["type"] == "a"
        assert received_type_b[0]["type"] == "b"

    async def test_same_handler_subscribed_once(self):
        """Test that same handler isn't added twice."""
        bus = InProcessEventBus()
        call_count = 0

        async def handler(event_type: str, data: dict[str, Any]):
            nonlocal call_count
            call_count += 1

        await bus.subscribe("test.event", handler)
        await bus.subscribe("test.event", handler)  # Subscribe again

        await bus.publish("test.event", {"msg": "test"})
        await asyncio.sleep(0.1)

        # Should only be called once
        assert call_count == 1

    async def test_event_types_constants(self):
        """Test that EventTypes constants are defined."""
        assert EventTypes.MESSAGE_CREATED == "message.created"
        assert EventTypes.CONVERSATION_STARTED == "conversation.started"
        assert EventTypes.SENTIMENT_NEGATIVE == "sentiment.negative"
        assert EventTypes.TOKEN_BUDGET_WARNING == "token.budget_warning"

    async def test_concurrent_publishing(self):
        """Test that concurrent publishes work correctly."""
        bus = InProcessEventBus()
        received = []

        async def handler(event_type: str, data: dict[str, Any]):
            await asyncio.sleep(0.01)  # Simulate work
            received.append(data["id"])

        await bus.subscribe("test.event", handler)

        # Publish multiple events concurrently
        tasks = [bus.publish("test.event", {"id": i}) for i in range(10)]
        await asyncio.gather(*tasks)
        await asyncio.sleep(0.2)

        # All events should be received
        assert len(received) == 10
        assert set(received) == set(range(10))
