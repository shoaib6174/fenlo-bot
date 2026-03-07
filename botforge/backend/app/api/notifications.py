"""
Notifications API — manage Slack and email notification settings.

Endpoints:
- POST /api/v1/notifications/test-slack — send a test Slack notification
- GET  /api/v1/notifications/settings — get all notification settings
- PUT  /api/v1/notifications/settings — update all notification settings
- GET  /api/v1/notifications/email-preview — preview recent email alerts
- POST /api/v1/notifications/test-email — generate a test email alert preview
"""

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.event_bus import EventTypes
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.user import User
from app.models.workspace import Workspace
from app.services.notifications import (
    DEFAULT_EMAIL_SETTINGS,
    get_email_log,
    render_email_html,
    send_test_slack_notification,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


# ========================
# Schemas
# ========================


class SlackTestRequest(BaseModel):
    """Request to test a Slack webhook URL."""

    webhook_url: HttpUrl = Field(..., description="Slack Incoming Webhook URL to test")


class SlackTestResponse(BaseModel):
    """Response from Slack test notification."""

    success: bool
    error: str | None = None


class NotificationSettings(BaseModel):
    """Full notification settings for a workspace (Slack + Email)."""

    slack_webhook_url: str = ""
    slack_notifications: dict = Field(
        default_factory=lambda: {
            "enabled": False,
            "escalation": True,
            "hot_lead": True,
            "quality": True,
            "documents": False,
        }
    )
    email_alerts: dict = Field(default_factory=lambda: {**DEFAULT_EMAIL_SETTINGS})


class NotificationSettingsResponse(BaseModel):
    """Response containing all notification settings."""

    slack_webhook_url: str = ""
    slack_notifications: dict = Field(default_factory=dict)
    email_alerts: dict = Field(default_factory=dict)


class EmailPreviewItem(BaseModel):
    """A single email alert preview."""

    subject: str
    html: str
    event_type: str
    alert_type: str
    recipient: str
    created_at: str


# ========================
# Slack Endpoints
# ========================


@router.post(
    "/test-slack",
    response_model=SlackTestResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def test_slack_notification(
    data: SlackTestRequest,
    user: tuple[User, UUID, str] = Depends(get_current_user),
) -> dict:
    """
    Send a test notification to verify a Slack webhook URL.

    **Required role**: admin
    """
    result = await send_test_slack_notification(str(data.webhook_url))

    logger.info(
        "notification.test_slack",
        workspace_id=str(user[1]),
        success=result["success"],
    )

    return result


# ========================
# Unified Settings Endpoints
# ========================


@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def get_notification_settings(
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get all notification settings (Slack + Email) for the workspace.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    settings = workspace.settings or {}

    return {
        "slack_webhook_url": settings.get("slack_webhook_url", ""),
        "slack_notifications": settings.get(
            "slack_notifications",
            {
                "enabled": False,
                "escalation": True,
                "hot_lead": True,
                "quality": True,
                "documents": False,
            },
        ),
        "email_alerts": settings.get("email_alerts", {**DEFAULT_EMAIL_SETTINGS}),
    }


@router.put(
    "/settings",
    response_model=NotificationSettingsResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def update_notification_settings(
    data: NotificationSettings,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update all notification settings (Slack + Email) for the workspace.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Merge notification settings into workspace settings
    current_settings = workspace.settings or {}
    current_settings["slack_webhook_url"] = (
        str(data.slack_webhook_url) if data.slack_webhook_url else ""
    )
    current_settings["slack_notifications"] = data.slack_notifications
    current_settings["email_alerts"] = data.email_alerts

    workspace.settings = current_settings
    await db.commit()

    logger.info(
        "notification.settings_updated",
        workspace_id=str(workspace_id),
        slack_enabled=data.slack_notifications.get("enabled", False),
        email_enabled=data.email_alerts.get("enabled", False),
    )

    return {
        "slack_webhook_url": current_settings.get("slack_webhook_url", ""),
        "slack_notifications": current_settings.get("slack_notifications", {}),
        "email_alerts": current_settings.get("email_alerts", {}),
    }


# ========================
# Email Endpoints
# ========================


@router.get(
    "/email-preview",
    response_model=list[EmailPreviewItem],
    dependencies=[Depends(require_role("admin"))],
)
async def get_email_preview(
    user: tuple[User, UUID, str] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """
    Get recent email alert previews for the workspace.

    Since SMTP is not configured ($0 budget), email alerts are logged
    in-memory and viewable here. Shows last 50 emails.

    **Required role**: admin
    """
    _, workspace_id, _ = user
    return get_email_log(str(workspace_id))


@router.post(
    "/test-email",
    response_model=EmailPreviewItem,
    dependencies=[Depends(require_role("admin"))],
)
async def test_email_alert(
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate a test email alert preview.

    Renders a sample quality alert email to verify template rendering.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    # Get workspace name
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()
    workspace_name = workspace.name if workspace else "BotForge"

    # Get recipient email from settings
    settings = (workspace.settings or {}) if workspace else {}
    email_config = settings.get("email_alerts", {})
    recipient = email_config.get("recipient_email", "")

    # Render a sample quality alert
    sample_data = {
        "workspace_id": str(workspace_id),
        "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "quality_score": 0.35,
        "threshold": 0.6,
        "reason": "Test alert — quality score dropped below threshold",
    }

    email = render_email_html(EventTypes.QUALITY_ALERT, sample_data, workspace_name)

    from datetime import UTC, datetime

    return {
        "subject": email["subject"],
        "html": email["html"],
        "event_type": EventTypes.QUALITY_ALERT,
        "alert_type": "quality_drop",
        "recipient": recipient,
        "created_at": datetime.now(UTC).isoformat(),
    }
