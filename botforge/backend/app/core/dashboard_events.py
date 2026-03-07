"""
Dashboard event projections and priority system.

Defines event priority levels and helper functions to build
dashboard-ready event payloads from raw event bus data.
"""

from enum import IntEnum
from typing import Any


class EventPriority(IntEnum):
    """Event priority levels for backpressure handling."""

    CRITICAL = 1  # escalation, conversation_ended — NEVER drop
    HIGH = 2  # conversation_started, handoff_requested
    NORMAL = 3  # message, sentiment_update
    LOW = 4  # metrics, analytics_update


def project_message_event(data: dict[str, Any]) -> dict[str, Any]:
    """Build a dashboard event from a message.created event."""
    return {
        "type": "message",
        "priority": EventPriority.NORMAL,
        "conversation_id": data.get("conversation_id"),
        "preview": (data.get("response") or "")[:100],
        "sentiment": data.get("sentiment"),
        "quality_score": data.get("quality_score"),
        "intent": data.get("intent"),
    }


def project_conversation_started(data: dict[str, Any]) -> dict[str, Any]:
    """Build a dashboard event from a conversation.started event."""
    return {
        "type": "conversation_started",
        "priority": EventPriority.HIGH,
        "conversation_id": data.get("conversation_id"),
        "channel": data.get("channel"),
    }


def project_escalation_event(data: dict[str, Any]) -> dict[str, Any]:
    """Build a dashboard event from a conversation.escalated event."""
    return {
        "type": "escalation",
        "priority": EventPriority.CRITICAL,
        "conversation_id": data.get("conversation_id"),
        "reason": data.get("reason"),
    }


def project_metrics_update(data: dict[str, Any]) -> dict[str, Any]:
    """Build a low-priority metrics refresh event."""
    return {
        "type": "metrics_update",
        "priority": EventPriority.LOW,
        "active_conversations": data.get("active_conversations"),
        "messages_last_minute": data.get("messages_last_minute"),
    }
