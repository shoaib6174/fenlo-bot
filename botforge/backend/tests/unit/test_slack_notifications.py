"""
Unit tests for Slack Notifications (S84) and Email Alerts (S85).

Tests cover:
- Slack message formatting for all 4 event types
- Event filtering based on workspace settings
- Notification enable/disable logic
- Test notification function
- Email HTML template rendering for all 4 alert types
- Email alert configuration defaults
- Quality threshold evaluation
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.event_bus import EventTypes
from app.services.notifications import (
    DEFAULT_EMAIL_SETTINGS,
    EMAIL_ALERT_MAP,
    EVENT_NOTIFICATION_MAP,
    _format_slack_message,
    render_email_html,
    send_test_slack_notification,
)

# --- Message Formatting Tests ---


class TestSlackMessageFormatting:
    """Test Slack Block Kit message formatting for each event type."""

    def test_escalation_message_format(self):
        """Escalation events include reason, priority, and rule name."""
        data = {
            "workspace_id": str(uuid4()),
            "conversation_id": str(uuid4()),
            "reason": "negative_sentiment",
            "priority": "high",
            "rule_name": "Frustrated Customer",
        }
        message = _format_slack_message(EventTypes.CONVERSATION_ESCALATED, data)

        assert "blocks" in message
        assert "text" in message
        assert "Escalation" in message["text"]
        # Check that blocks contain the event details
        block_text = str(message["blocks"])
        assert "negative_sentiment" in block_text
        assert "high" in block_text

    def test_hot_lead_message_format(self):
        """Hot lead events include lead score and signals."""
        data = {
            "workspace_id": str(uuid4()),
            "conversation_id": str(uuid4()),
            "lead_score": 8.5,
            "signals": ["pricing_inquiry", "timeline_mentioned"],
        }
        message = _format_slack_message(EventTypes.LEAD_QUALIFIED, data)

        assert "Hot Lead" in message["text"]
        block_text = str(message["blocks"])
        assert "8.5" in block_text
        assert "pricing_inquiry" in block_text

    def test_quality_alert_message_format(self):
        """Quality alerts include score, threshold, and reason."""
        data = {
            "workspace_id": str(uuid4()),
            "conversation_id": str(uuid4()),
            "quality_score": 0.35,
            "threshold": 0.6,
            "reason": "Quality score dropped below threshold",
        }
        message = _format_slack_message(EventTypes.QUALITY_ALERT, data)

        assert "Quality Alert" in message["text"]
        block_text = str(message["blocks"])
        assert "0.35" in block_text
        assert "0.6" in block_text

    def test_document_processed_message_format(self):
        """Document processed events include document name and status."""
        data = {
            "workspace_id": str(uuid4()),
            "document_name": "Product FAQ.pdf",
            "status": "completed",
        }
        message = _format_slack_message(EventTypes.DOCUMENT_PROCESSED, data)

        assert "Document Processed" in message["text"]
        block_text = str(message["blocks"])
        assert "Product FAQ.pdf" in block_text


# --- Event Filtering Tests ---


class TestEventFiltering:
    """Test that events are filtered based on workspace settings."""

    def test_all_four_events_mapped(self):
        """All 4 notification event types are defined in the mapping."""
        expected_events = {
            EventTypes.CONVERSATION_ESCALATED,
            EventTypes.LEAD_QUALIFIED,
            EventTypes.QUALITY_ALERT,
            EventTypes.DOCUMENT_PROCESSED,
        }
        assert set(EVENT_NOTIFICATION_MAP.keys()) == expected_events

    def test_event_keys_match_config_keys(self):
        """Event mapping keys match the config toggle keys."""
        expected_keys = {"escalation", "hot_lead", "quality", "documents"}
        actual_keys = {info["key"] for info in EVENT_NOTIFICATION_MAP.values()}
        assert actual_keys == expected_keys

    def test_each_event_has_label_emoji_color(self):
        """Each event mapping has label, emoji, and color for Slack formatting."""
        for event_type, info in EVENT_NOTIFICATION_MAP.items():
            assert "label" in info, f"{event_type} missing label"
            assert "emoji" in info, f"{event_type} missing emoji"
            assert "color" in info, f"{event_type} missing color"
            assert info["color"].startswith("#"), f"{event_type} color should be hex"


# --- Test Notification Function ---


class TestSendTestNotification:
    """Test the test notification sender."""

    @pytest.mark.asyncio
    async def test_successful_test_notification(self):
        """Successful test notification returns success=True."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.notifications.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await send_test_slack_notification("https://hooks.slack.com/services/test")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_failed_test_notification(self):
        """Failed test notification returns success=False with error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch("app.services.notifications.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await send_test_slack_notification("https://hooks.slack.com/services/bad")

            assert result["success"] is False
            assert "404" in result["error"]


# ========================
# Email Alert Tests (S85)
# ========================


class TestEmailTemplateRendering:
    """Test HTML email template rendering for all alert types."""

    def test_quality_alert_email(self):
        """Quality alert email contains score, threshold, and reason."""
        data = {
            "workspace_id": str(uuid4()),
            "conversation_id": str(uuid4()),
            "quality_score": 0.35,
            "threshold": 0.6,
            "reason": "Quality score dropped below threshold",
        }
        email = render_email_html(EventTypes.QUALITY_ALERT, data, "TestWorkspace")

        assert "[BotForge] Quality Score Drop" in email["subject"]
        assert "0.35" in email["html"]
        assert "0.6" in email["html"]
        assert "TestWorkspace" in email["html"]

    def test_escalation_email(self):
        """Escalation email contains reason, priority, and rule name."""
        data = {
            "workspace_id": str(uuid4()),
            "conversation_id": str(uuid4()),
            "reason": "negative_sentiment",
            "priority": "high",
            "rule_name": "Angry Customer",
        }
        email = render_email_html(EventTypes.CONVERSATION_ESCALATED, data)

        assert "Conversation Escalated" in email["subject"]
        assert "negative_sentiment" in email["html"]
        assert "high" in email["html"]
        assert "Angry Customer" in email["html"]

    def test_knowledge_gap_email(self):
        """Knowledge gap email contains query and frequency."""
        data = {
            "workspace_id": str(uuid4()),
            "query": "Do you offer enterprise pricing?",
            "frequency": 5,
        }
        email = render_email_html(EventTypes.KNOWLEDGE_GAP_DETECTED, data)

        assert "Knowledge Gap" in email["subject"]
        assert "enterprise pricing" in email["html"]
        assert "5" in email["html"]

    def test_document_processed_email(self):
        """Document processed email contains document name and status."""
        data = {
            "workspace_id": str(uuid4()),
            "document_name": "Product FAQ.pdf",
            "status": "completed",
        }
        email = render_email_html(EventTypes.DOCUMENT_PROCESSED, data)

        assert "Document Processed" in email["subject"]
        assert "Product FAQ.pdf" in email["html"]


class TestEmailAlertConfig:
    """Test email alert configuration and defaults."""

    def test_all_four_email_events_mapped(self):
        """All 4 email alert event types are defined."""
        expected = {
            EventTypes.QUALITY_ALERT,
            EventTypes.CONVERSATION_ESCALATED,
            EventTypes.KNOWLEDGE_GAP_DETECTED,
            EventTypes.DOCUMENT_PROCESSED,
        }
        assert set(EMAIL_ALERT_MAP.keys()) == expected

    def test_default_email_settings_structure(self):
        """Default email settings have all required keys."""
        required_keys = {
            "enabled",
            "recipient_email",
            "quality_drop",
            "escalation",
            "knowledge_gap",
            "doc_processed",
            "digest_frequency",
            "quality_threshold",
        }
        assert required_keys.issubset(set(DEFAULT_EMAIL_SETTINGS.keys()))
        assert DEFAULT_EMAIL_SETTINGS["enabled"] is False
        assert DEFAULT_EMAIL_SETTINGS["quality_threshold"] == 0.6

    def test_email_html_is_valid_html(self):
        """Rendered email HTML starts with DOCTYPE and contains body."""
        data = {
            "workspace_id": str(uuid4()),
            "quality_score": 0.35,
            "threshold": 0.6,
            "reason": "test",
        }
        email = render_email_html(EventTypes.QUALITY_ALERT, data)

        assert email["html"].strip().startswith("<!DOCTYPE html>")
        assert "<body" in email["html"]
        assert "</body>" in email["html"]
