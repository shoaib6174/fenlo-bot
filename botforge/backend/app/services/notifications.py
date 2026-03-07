"""
Notification Service — routes events to configured channels (Slack, email, webhook).

Provides a pluggable notification framework. Each notifier implements the same
interface and is activated per-workspace via settings.

Architecture:
  EventBus → SlackNotifier (subscribes to events)
           → reads workspace.settings for Slack URL + per-event toggles
           → formats Slack Block Kit message
           → POST to Slack Incoming Webhook URL

  EventBus → EmailNotifier (subscribes to events)
           → reads workspace.settings for email config + alert thresholds
           → renders HTML email template
           → logs/stores email (SMTP optional, not available on $0 budget)
"""

import html
from collections import deque
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select

from app.core.event_bus import EventBus, EventTypes
from app.models.workspace import Workspace

logger = structlog.get_logger(__name__)

# Map EventBus event types to Slack notification keys
EVENT_NOTIFICATION_MAP: dict[str, dict[str, str]] = {
    EventTypes.CONVERSATION_ESCALATED: {
        "key": "escalation",
        "label": "Escalation",
        "emoji": ":rotating_light:",
        "color": "#e74c3c",
    },
    EventTypes.LEAD_QUALIFIED: {
        "key": "hot_lead",
        "label": "Hot Lead",
        "emoji": ":fire:",
        "color": "#f39c12",
    },
    EventTypes.QUALITY_ALERT: {
        "key": "quality",
        "label": "Quality Alert",
        "emoji": ":warning:",
        "color": "#e67e22",
    },
    EventTypes.DOCUMENT_PROCESSED: {
        "key": "documents",
        "label": "Document Processed",
        "emoji": ":page_facing_up:",
        "color": "#2ecc71",
    },
}


def _format_slack_message(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Format event data into a Slack Block Kit message.

    Returns a Slack message payload with structured blocks for rich display.
    """
    event_info = EVENT_NOTIFICATION_MAP.get(event_type, {})
    emoji = event_info.get("emoji", ":bell:")
    label = event_info.get("label", event_type)

    conversation_id = data.get("conversation_id", "")

    # Build context fields based on event type
    fields = []

    if event_type == EventTypes.CONVERSATION_ESCALATED:
        fields = [
            f"*Reason:* {data.get('reason', 'N/A')}",
            f"*Priority:* {data.get('priority', 'N/A')}",
            f"*Rule:* {data.get('rule_name', 'N/A')}",
        ]
    elif event_type == EventTypes.LEAD_QUALIFIED:
        lead_score = data.get("lead_score", 0)
        fields = [
            f"*Lead Score:* {lead_score}",
            f"*Signals:* {', '.join(data.get('signals', []))}",
        ]
    elif event_type == EventTypes.QUALITY_ALERT:
        fields = [
            f"*Quality Score:* {data.get('quality_score', 'N/A')}",
            f"*Threshold:* {data.get('threshold', 'N/A')}",
            f"*Reason:* {data.get('reason', 'N/A')}",
        ]
    elif event_type == EventTypes.DOCUMENT_PROCESSED:
        fields = [
            f"*Document:* {data.get('document_name', 'N/A')}",
            f"*Status:* {data.get('status', 'completed')}",
        ]

    # Build Slack Block Kit payload
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} BotForge: {label}",
                "emoji": True,
            },
        },
    ]

    if fields:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(fields),
                },
            }
        )

    if conversation_id:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Conversation: `{conversation_id}`",
                    }
                ],
            }
        )

    return {
        "text": f"{label} — {fields[0] if fields else event_type}",
        "blocks": blocks,
    }


class SlackNotifier:
    """
    Sends notifications to Slack via Incoming Webhooks.

    Subscribes to EventBus events and checks workspace settings to determine
    if Slack notifications are enabled and which events should be forwarded.

    Workspace settings format (stored in workspace.settings JSONB):
        {
            "slack_webhook_url": "https://hooks.slack.com/services/...",
            "slack_notifications": {
                "enabled": true,
                "escalation": true,
                "hot_lead": true,
                "quality": true,
                "documents": false
            }
        }
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_session_factory: Any,
    ):
        self.event_bus = event_bus
        self.db_session_factory = db_session_factory

    async def start(self) -> None:
        """Subscribe to relevant EventBus events."""
        for event_type in EVENT_NOTIFICATION_MAP:
            await self.event_bus.subscribe(event_type, self._handle_event)

        logger.info(
            "slack_notifier.started",
            subscribed_events=len(EVENT_NOTIFICATION_MAP),
        )

    async def _handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Handle an incoming event — check settings and send to Slack if enabled."""
        workspace_id_str = data.get("workspace_id")
        if not workspace_id_str:
            return

        try:
            workspace_id = UUID(workspace_id_str)
        except (ValueError, TypeError):
            return

        async with self.db_session_factory() as session:
            try:
                # Load workspace settings
                stmt = select(Workspace).where(Workspace.id == workspace_id)
                result = await session.execute(stmt)
                workspace = result.scalar_one_or_none()

                if not workspace:
                    return

                settings = workspace.settings or {}
                slack_url = settings.get("slack_webhook_url", "")
                slack_config = settings.get("slack_notifications", {})

                # Check if Slack is enabled globally
                if not slack_url or not slack_config.get("enabled", False):
                    return

                # Check if this specific event type is enabled
                event_info = EVENT_NOTIFICATION_MAP.get(event_type)
                if not event_info:
                    return

                event_key = event_info["key"]
                if not slack_config.get(event_key, False):
                    logger.debug(
                        "slack_notifier.event_disabled",
                        event_type=event_type,
                        event_key=event_key,
                        workspace_id=str(workspace_id),
                    )
                    return

                # Format and send
                message = _format_slack_message(event_type, data)
                await self._send_to_slack(slack_url, message, workspace_id, event_type)

            except Exception as e:
                logger.error(
                    "slack_notifier.error",
                    event_type=event_type,
                    workspace_id=str(workspace_id),
                    error=str(e),
                    exc_info=True,
                )

    async def _send_to_slack(
        self,
        webhook_url: str,
        message: dict[str, Any],
        workspace_id: UUID,
        event_type: str,
    ) -> None:
        """POST message to Slack Incoming Webhook URL."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook_url, json=message)

                if response.status_code == 200:
                    logger.info(
                        "slack_notifier.sent",
                        workspace_id=str(workspace_id),
                        event_type=event_type,
                    )
                else:
                    logger.warning(
                        "slack_notifier.delivery_failed",
                        workspace_id=str(workspace_id),
                        event_type=event_type,
                        status_code=response.status_code,
                        body=response.text[:200],
                    )
        except httpx.TimeoutException:
            logger.warning(
                "slack_notifier.timeout",
                workspace_id=str(workspace_id),
                event_type=event_type,
            )
        except Exception as e:
            logger.error(
                "slack_notifier.send_error",
                workspace_id=str(workspace_id),
                event_type=event_type,
                error=str(e),
            )


async def send_test_slack_notification(webhook_url: str) -> dict[str, Any]:
    """
    Send a test notification to verify Slack webhook URL.

    Returns dict with success status and optional error message.
    """
    message = {
        "text": "BotForge test notification — your Slack integration is working!",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":white_check_mark: BotForge: Test Notification",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Your Slack webhook is configured correctly. You'll receive notifications for enabled events.",
                },
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=message)

            if response.status_code == 200:
                return {"success": True}
            else:
                return {
                    "success": False,
                    "error": f"Slack returned status {response.status_code}: {response.text[:200]}",
                }
    except httpx.TimeoutException:
        return {"success": False, "error": "Request timed out (10s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========================
# Email Alert Definitions
# ========================

# Map EventBus event types to email alert keys
EMAIL_ALERT_MAP: dict[str, dict[str, str]] = {
    EventTypes.QUALITY_ALERT: {
        "key": "quality_drop",
        "label": "Quality Score Drop",
        "description": "Quality score dropped below threshold",
        "icon_color": "#e74c3c",
    },
    EventTypes.CONVERSATION_ESCALATED: {
        "key": "escalation",
        "label": "Conversation Escalated",
        "description": "A conversation was escalated to a human agent",
        "icon_color": "#f39c12",
    },
    EventTypes.KNOWLEDGE_GAP_DETECTED: {
        "key": "knowledge_gap",
        "label": "Knowledge Gap Detected",
        "description": "A new knowledge gap was found",
        "icon_color": "#9b59b6",
    },
    EventTypes.DOCUMENT_PROCESSED: {
        "key": "doc_processed",
        "label": "Document Processed",
        "description": "Document processing completed",
        "icon_color": "#2ecc71",
    },
}

# Default email alert settings
DEFAULT_EMAIL_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "recipient_email": "",
    "quality_drop": True,
    "escalation": True,
    "knowledge_gap": True,
    "doc_processed": False,
    "digest_frequency": "immediate",  # immediate | hourly | daily
    "quality_threshold": 0.6,
}


def render_email_html(
    event_type: str,
    data: dict[str, Any],
    workspace_name: str = "BotForge",
) -> dict[str, str]:
    """
    Render an HTML email for an alert event.

    Returns dict with 'subject' and 'html' keys.
    """
    alert_info = EMAIL_ALERT_MAP.get(event_type, {})
    label = alert_info.get("label", event_type)
    icon_color = alert_info.get("icon_color", "#3498db")
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # Build detail rows based on event type
    detail_rows = ""
    if event_type == EventTypes.QUALITY_ALERT:
        detail_rows = f"""
        <tr><td style="padding:8px 0;color:#666;width:140px">Quality Score</td>
            <td style="padding:8px 0;font-weight:600">{html.escape(str(data.get('quality_score', 'N/A')))}</td></tr>
        <tr><td style="padding:8px 0;color:#666">Threshold</td>
            <td style="padding:8px 0">{html.escape(str(data.get('threshold', '0.6')))}</td></tr>
        <tr><td style="padding:8px 0;color:#666">Reason</td>
            <td style="padding:8px 0">{html.escape(str(data.get('reason', 'N/A')))}</td></tr>
        """
    elif event_type == EventTypes.CONVERSATION_ESCALATED:
        detail_rows = f"""
        <tr><td style="padding:8px 0;color:#666;width:140px">Reason</td>
            <td style="padding:8px 0;font-weight:600">{html.escape(str(data.get('reason', 'N/A')))}</td></tr>
        <tr><td style="padding:8px 0;color:#666">Priority</td>
            <td style="padding:8px 0">{html.escape(str(data.get('priority', 'N/A')))}</td></tr>
        <tr><td style="padding:8px 0;color:#666">Rule</td>
            <td style="padding:8px 0">{html.escape(str(data.get('rule_name', 'N/A')))}</td></tr>
        """
    elif event_type == EventTypes.KNOWLEDGE_GAP_DETECTED:
        detail_rows = f"""
        <tr><td style="padding:8px 0;color:#666;width:140px">Query</td>
            <td style="padding:8px 0;font-weight:600">{html.escape(str(data.get('query', 'N/A')))}</td></tr>
        <tr><td style="padding:8px 0;color:#666">Frequency</td>
            <td style="padding:8px 0">{html.escape(str(data.get('frequency', '1')))} times</td></tr>
        """
    elif event_type == EventTypes.DOCUMENT_PROCESSED:
        detail_rows = f"""
        <tr><td style="padding:8px 0;color:#666;width:140px">Document</td>
            <td style="padding:8px 0;font-weight:600">{html.escape(str(data.get('document_name', 'N/A')))}</td></tr>
        <tr><td style="padding:8px 0;color:#666">Status</td>
            <td style="padding:8px 0">{html.escape(str(data.get('status', 'completed')))}</td></tr>
        """

    conversation_id = data.get("conversation_id", "")
    conv_section = ""
    if conversation_id:
        conv_section = f"""
        <tr><td style="padding:8px 0;color:#666">Conversation</td>
            <td style="padding:8px 0;font-family:monospace;font-size:12px">{html.escape(str(conversation_id))}</td></tr>
        """

    email_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<div style="max-width:560px;margin:40px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1)">
  <div style="background:{icon_color};padding:24px 32px;color:#fff">
    <h1 style="margin:0;font-size:20px;font-weight:600">{html.escape(label)}</h1>
    <p style="margin:4px 0 0;opacity:0.85;font-size:14px">{html.escape(workspace_name)} &middot; {timestamp}</p>
  </div>
  <div style="padding:24px 32px">
    <table style="width:100%;border-collapse:collapse;font-size:14px;color:#333">
      {detail_rows}
      {conv_section}
    </table>
  </div>
  <div style="padding:16px 32px;border-top:1px solid #eee;text-align:center">
    <p style="margin:0;font-size:12px;color:#999">
      This alert was sent by BotForge. Manage alert settings in Settings &gt; Notifications.
    </p>
  </div>
</div>
</body>
</html>"""

    subject = f"[BotForge] {label}"
    if conversation_id:
        subject += f" — {conversation_id[:8]}"

    return {"subject": subject, "html": email_html}


# In-memory email log for demo preview (last 50 emails per workspace)
_email_log: dict[str, deque] = {}
MAX_EMAIL_LOG = 50


def get_email_log(workspace_id: str) -> list[dict[str, Any]]:
    """Get recent email alerts for a workspace (demo preview)."""
    return list(_email_log.get(workspace_id, []))


class EmailNotifier:
    """
    Email notification handler.

    Subscribes to EventBus events and checks workspace settings to determine
    if email alerts are enabled. Renders HTML emails and logs them.

    In production with SMTP configured, would send via aiosmtplib.
    For the demo ($0 budget), emails are logged and viewable via API.

    Workspace settings format (stored in workspace.settings JSONB):
        {
            "email_alerts": {
                "enabled": true,
                "recipient_email": "admin@example.com",
                "quality_drop": true,
                "escalation": true,
                "knowledge_gap": true,
                "doc_processed": false,
                "digest_frequency": "immediate",
                "quality_threshold": 0.6
            }
        }
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_session_factory: Any,
    ):
        self.event_bus = event_bus
        self.db_session_factory = db_session_factory

    async def start(self) -> None:
        """Subscribe to relevant EventBus events."""
        for event_type in EMAIL_ALERT_MAP:
            await self.event_bus.subscribe(event_type, self._handle_event)

        logger.info(
            "email_notifier.started",
            subscribed_events=len(EMAIL_ALERT_MAP),
        )

    async def _handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Handle an incoming event — check settings and log/send email if enabled."""
        workspace_id_str = data.get("workspace_id")
        if not workspace_id_str:
            return

        try:
            workspace_id = UUID(workspace_id_str)
        except (ValueError, TypeError):
            return

        async with self.db_session_factory() as session:
            try:
                stmt = select(Workspace).where(Workspace.id == workspace_id)
                result = await session.execute(stmt)
                workspace = result.scalar_one_or_none()

                if not workspace:
                    return

                settings = workspace.settings or {}
                email_config = settings.get("email_alerts", {})

                # Check if email alerts are enabled
                if not email_config.get("enabled", False):
                    return

                # Check if this specific event type is enabled
                alert_info = EMAIL_ALERT_MAP.get(event_type)
                if not alert_info:
                    return

                alert_key = alert_info["key"]
                if not email_config.get(alert_key, False):
                    return

                # Check threshold for quality alerts
                if event_type == EventTypes.QUALITY_ALERT:
                    threshold = email_config.get("quality_threshold", 0.6)
                    score = data.get("quality_score", 1.0)
                    if score >= threshold:
                        return

                # Render email
                workspace_name = workspace.name or "BotForge"
                email = render_email_html(event_type, data, workspace_name)

                # Log to in-memory store (demo preview)
                if workspace_id_str not in _email_log:
                    _email_log[workspace_id_str] = deque(maxlen=MAX_EMAIL_LOG)

                _email_log[workspace_id_str].appendleft(
                    {
                        "subject": email["subject"],
                        "html": email["html"],
                        "event_type": event_type,
                        "alert_type": alert_key,
                        "recipient": email_config.get("recipient_email", ""),
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                )

                logger.info(
                    "email_notifier.logged",
                    workspace_id=workspace_id_str,
                    event_type=event_type,
                    recipient=email_config.get("recipient_email", ""),
                    subject=email["subject"],
                )

            except Exception as e:
                logger.error(
                    "email_notifier.error",
                    event_type=event_type,
                    workspace_id=workspace_id_str,
                    error=str(e),
                    exc_info=True,
                )
