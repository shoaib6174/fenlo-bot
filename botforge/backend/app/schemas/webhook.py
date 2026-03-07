"""Pydantic schemas for webhook actions and outbox."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ========================
# Webhook Action Schemas
# ========================


class WebhookActionCreate(BaseModel):
    """Request schema for creating a webhook action."""

    trigger_event: str = Field(
        ...,
        description="Event type that triggers this action (e.g., 'message.created', 'lead.qualified')",
        examples=["message.created", "conversation.escalated", "lead.qualified"],
    )
    action_type: str = Field(
        default="webhook",
        description="Type of action (currently only 'webhook' supported)",
        pattern="^(webhook|email|slack)$",
    )
    config: dict = Field(
        ...,
        description="Action configuration (URL, headers, payload template)",
        examples=[
            {
                "url": "https://example.com/webhook",
                "headers": {"Authorization": "Bearer secret"},
                "payload_template": '{"event": "{event_type}", "workspace": "{workspace_id}"}',
            }
        ],
    )
    is_active: bool = Field(default=True, description="Whether this action is active")

    model_config = {
        "json_schema_extra": {
            "example": {
                "trigger_event": "lead.qualified",
                "action_type": "webhook",
                "config": {
                    "url": "https://api.example.com/leads",
                    "headers": {"Authorization": "Bearer YOUR_TOKEN"},
                    "payload_template": '{"lead_score": "{lead_score}", "conversation_id": "{conversation_id}"}',
                },
                "is_active": True,
            }
        }
    }


class WebhookActionUpdate(BaseModel):
    """Request schema for updating a webhook action."""

    trigger_event: str | None = Field(None, description="Event type that triggers this action")
    action_type: str | None = Field(None, description="Type of action")
    config: dict | None = Field(None, description="Action configuration")
    is_active: bool | None = Field(None, description="Whether this action is active")


class WebhookActionResponse(BaseModel):
    """Response schema for webhook actions."""

    id: UUID
    workspace_id: UUID
    trigger_event: str
    action_type: str
    config: dict
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ========================
# Webhook Outbox Schemas
# ========================


class WebhookOutboxResponse(BaseModel):
    """Response schema for webhook outbox entries (delivery history)."""

    id: UUID
    workspace_id: UUID
    event_type: str
    payload: dict
    target_url: str
    status: str  # pending, sent, failed, dead
    retry_count: int
    max_retries: int
    next_retry_at: datetime | None
    error_message: str | None
    sequence: int
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}


# ========================
# Paginated Response
# ========================


class WebhookHistoryResponse(BaseModel):
    """Paginated response for webhook delivery history."""

    items: list[WebhookOutboxResponse]
    total: int
    page: int
    per_page: int
    pages: int
