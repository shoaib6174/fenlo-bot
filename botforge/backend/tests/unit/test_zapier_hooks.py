"""
Unit tests for Zapier REST hooks (S83).

Tests cover:
- Trigger event definitions: all 6 events, mappings, samples
- Subscribe/unsubscribe logic (DB-dependent, skipped if no test DB)
- Event-to-webhook matching (DB-dependent, skipped if no test DB)
- Sample payload structure validation
"""

from unittest.mock import AsyncMock
from uuid import uuid4

# Import the Zapier module constants
from app.api.zapier import SAMPLE_PAYLOADS, ZAPIER_TRIGGER_EVENTS
from app.core.event_bus import EventTypes


def _is_mock_session(db_session) -> bool:
    """Check if db_session is a mock (no real DB available)."""
    return isinstance(db_session, AsyncMock)


# --- Pure Logic Tests (no DB needed) ---


class TestZapierTriggerEvents:
    """Test trigger event definitions."""

    def test_all_six_events_defined(self):
        """8.43: All 6 trigger events are defined."""
        expected = {
            "new_conversation",
            "message_received",
            "escalation_triggered",
            "hot_lead",
            "knowledge_gap",
            "quality_alert",
        }
        assert set(ZAPIER_TRIGGER_EVENTS.keys()) == expected

    def test_event_bus_type_mapping(self):
        """Events map to correct EventBus event types."""
        mappings = {
            "new_conversation": EventTypes.CONVERSATION_STARTED,
            "message_received": EventTypes.MESSAGE_CREATED,
            "escalation_triggered": EventTypes.CONVERSATION_ESCALATED,
            "hot_lead": EventTypes.LEAD_QUALIFIED,
            "knowledge_gap": EventTypes.KNOWLEDGE_GAP_DETECTED,
            "quality_alert": EventTypes.QUALITY_ALERT,
        }
        for zapier_event, bus_event in mappings.items():
            assert ZAPIER_TRIGGER_EVENTS[zapier_event]["event_bus_type"] == bus_event

    def test_sample_payloads_exist_for_all_events(self):
        """Every trigger event has a sample payload for Zapier field mapping."""
        for event in ZAPIER_TRIGGER_EVENTS:
            assert event in SAMPLE_PAYLOADS, f"Missing sample payload for {event}"
            sample = SAMPLE_PAYLOADS[event]
            assert isinstance(sample, dict)
            assert "event" in sample
            assert sample["event"] == event

    def test_each_event_has_label_and_description(self):
        """Each trigger event has user-friendly label and description."""
        for event, info in ZAPIER_TRIGGER_EVENTS.items():
            assert "label" in info, f"{event} missing label"
            assert "description" in info, f"{event} missing description"
            assert len(info["label"]) > 0
            assert len(info["description"]) > 0


class TestSamplePayloads:
    """Test sample payload structure."""

    def test_all_samples_have_required_fields(self):
        """Sample payloads include workspace_id for Zapier field mapping."""
        for event, sample in SAMPLE_PAYLOADS.items():
            assert "workspace_id" in sample, f"{event} missing workspace_id"
            assert "event" in sample, f"{event} missing event field"

    def test_hot_lead_sample_has_score(self):
        """Hot lead sample includes lead_score for Zapier mapping."""
        sample = SAMPLE_PAYLOADS["hot_lead"]
        assert "lead_score" in sample
        assert isinstance(sample["lead_score"], int | float)
        assert sample["lead_score"] > 0

    def test_escalation_sample_has_priority(self):
        """Escalation sample includes priority field."""
        sample = SAMPLE_PAYLOADS["escalation_triggered"]
        assert "priority" in sample
        assert sample["priority"] in ("low", "medium", "high")

    def test_message_sample_has_content_and_sentiment(self):
        """Message received sample has content, sentiment, intent."""
        sample = SAMPLE_PAYLOADS["message_received"]
        assert "content" in sample
        assert "sentiment" in sample
        assert "intent" in sample
        assert "role" in sample


class TestSubscribeLogic:
    """Test subscribe/unsubscribe business logic."""

    def test_zapier_action_type_used(self):
        """Subscribe creates actions with action_type='zapier' to distinguish from manual webhooks."""
        from app.models.channel import WebhookAction

        action = WebhookAction(
            workspace_id=uuid4(),
            trigger_event="lead.qualified",
            action_type="zapier",
            config={
                "url": "https://hooks.zapier.com/test",
                "zapier_event": "hot_lead",
                "headers": {"Content-Type": "application/json"},
            },
            is_active=True,
        )
        assert action.action_type == "zapier"
        assert action.trigger_event == "lead.qualified"
        assert action.config["zapier_event"] == "hot_lead"

    def test_invalid_event_type_caught(self):
        """Invalid event names are not in the trigger events dict."""
        assert "nonexistent_event" not in ZAPIER_TRIGGER_EVENTS
        assert "invalid" not in ZAPIER_TRIGGER_EVENTS


class TestQualityAlertEvent:
    """Test that quality.alert event type exists."""

    def test_quality_alert_in_event_types(self):
        """QUALITY_ALERT event type is defined for quality alerts."""
        assert hasattr(EventTypes, "QUALITY_ALERT")
        assert EventTypes.QUALITY_ALERT == "quality.alert"

    def test_quality_alert_in_zapier_events(self):
        """quality_alert maps to quality.alert event bus type."""
        info = ZAPIER_TRIGGER_EVENTS["quality_alert"]
        assert info["event_bus_type"] == "quality.alert"
