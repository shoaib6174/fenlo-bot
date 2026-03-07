"""
Zapier REST Hooks API — subscribe/unsubscribe/sample endpoints.

Zapier's REST hooks protocol:
1. Zapier calls POST /subscribe with {hookUrl, event} to register
2. BotForge stores this as a WebhookAction and delivers events via outbox
3. Zapier calls DELETE /subscribe/{id} to unsubscribe when a Zap is turned off
4. Zapier calls GET /sample/{event} to get sample payloads for field mapping
"""

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.channel import WebhookAction
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["zapier"])

# ========================
# Zapier Trigger Events
# ========================

ZAPIER_TRIGGER_EVENTS = {
    "new_conversation": {
        "event_bus_type": "conversation.started",
        "label": "New Conversation",
        "description": "Triggers when a new conversation starts",
    },
    "message_received": {
        "event_bus_type": "message.created",
        "label": "Message Received",
        "description": "Triggers when a user sends a message",
    },
    "escalation_triggered": {
        "event_bus_type": "conversation.escalated",
        "label": "Escalation Triggered",
        "description": "Triggers when escalation rules fire",
    },
    "hot_lead": {
        "event_bus_type": "lead.qualified",
        "label": "Hot Lead Detected",
        "description": "Triggers when lead score exceeds threshold",
    },
    "knowledge_gap": {
        "event_bus_type": "knowledge_gap.detected",
        "label": "Knowledge Gap Detected",
        "description": "Triggers when a new knowledge gap is found",
    },
    "quality_alert": {
        "event_bus_type": "quality.alert",
        "label": "Quality Alert",
        "description": "Triggers when quality score drops below threshold",
    },
}

# Sample payloads for Zapier field mapping
SAMPLE_PAYLOADS = {
    "new_conversation": {
        "event": "new_conversation",
        "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
        "channel": "web",
        "started_at": "2026-02-16T12:00:00Z",
        "user_message": "Hi, I need help with my order",
    },
    "message_received": {
        "event": "message_received",
        "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "message_id": "m1a2b3c4-d5e6-7890-abcd-ef1234567890",
        "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
        "role": "user",
        "content": "What are your business hours?",
        "sentiment": "neutral",
        "intent": "faq",
        "timestamp": "2026-02-16T12:01:00Z",
    },
    "escalation_triggered": {
        "event": "escalation_triggered",
        "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
        "reason": "negative_sentiment",
        "rule_name": "Frustrated Customer",
        "priority": "high",
        "timestamp": "2026-02-16T12:02:00Z",
    },
    "hot_lead": {
        "event": "hot_lead",
        "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
        "lead_score": 8.5,
        "signals": ["pricing_inquiry", "timeline_mentioned", "contact_shared"],
        "timestamp": "2026-02-16T12:03:00Z",
    },
    "knowledge_gap": {
        "event": "knowledge_gap",
        "gap_id": "g1a2b3c4-d5e6-7890-abcd-ef1234567890",
        "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
        "query": "Do you offer enterprise pricing?",
        "frequency": 5,
        "detected_at": "2026-02-16T12:04:00Z",
    },
    "quality_alert": {
        "event": "quality_alert",
        "workspace_id": "w1a2b3c4-d5e6-7890-abcd-ef1234567890",
        "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "quality_score": 0.35,
        "threshold": 0.6,
        "reason": "Quality score dropped below threshold",
        "timestamp": "2026-02-16T12:05:00Z",
    },
}


# ========================
# Request/Response Schemas
# ========================


class ZapierSubscribeRequest(BaseModel):
    """Zapier REST hooks subscribe request."""

    hook_url: HttpUrl = Field(
        ..., alias="hookUrl", description="The URL Zapier wants us to POST events to"
    )
    event: str = Field(..., description="The trigger event to subscribe to")

    model_config = {"populate_by_name": True}


class ZapierSubscribeResponse(BaseModel):
    """Zapier REST hooks subscribe response."""

    id: UUID
    event: str
    hook_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ZapierTriggerInfo(BaseModel):
    """Info about an available trigger event."""

    event: str
    label: str
    description: str


# ========================
# Endpoints
# ========================


@router.post(
    "/subscribe",
    response_model=ZapierSubscribeResponse,
    status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
async def subscribe(
    data: ZapierSubscribeRequest,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Subscribe to a BotForge trigger event (Zapier REST hooks protocol).

    Zapier calls this endpoint when a user creates a Zap with a BotForge trigger.
    Creates a WebhookAction that delivers matching events to the provided hookUrl.
    """
    _, workspace_id, _ = user

    # Validate event type
    if data.event not in ZAPIER_TRIGGER_EVENTS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_EVENT",
                    "message": f"Unknown event '{data.event}'. Valid events: {', '.join(ZAPIER_TRIGGER_EVENTS.keys())}",
                }
            },
        )

    trigger_info = ZAPIER_TRIGGER_EVENTS[data.event]
    hook_url = str(data.hook_url)

    # Create a WebhookAction for the ActionDispatcher
    action = WebhookAction(
        workspace_id=workspace_id,
        trigger_event=trigger_info["event_bus_type"],
        action_type="zapier",
        config={
            "url": hook_url,
            "zapier_event": data.event,
            "headers": {"Content-Type": "application/json"},
        },
        is_active=True,
    )

    db.add(action)
    await db.commit()
    await db.refresh(action)

    logger.info(
        "zapier.subscribed",
        action_id=str(action.id),
        workspace_id=str(workspace_id),
        event=data.event,
        hook_url=hook_url,
    )

    return {
        "id": action.id,
        "event": data.event,
        "hook_url": hook_url,
        "created_at": action.created_at,
    }


@router.delete(
    "/subscribe/{subscription_id}",
    status_code=204,
    dependencies=[Depends(require_role("admin"))],
)
async def unsubscribe(
    subscription_id: UUID,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Unsubscribe from a BotForge trigger event (Zapier REST hooks protocol).

    Zapier calls this when a user turns off or deletes a Zap.
    """
    _, workspace_id, _ = user

    stmt = select(WebhookAction).where(
        WebhookAction.id == subscription_id,
        WebhookAction.workspace_id == workspace_id,
    )

    result = await db.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Subscription not found")

    await db.delete(action)
    await db.commit()

    logger.info(
        "zapier.unsubscribed",
        action_id=str(subscription_id),
        workspace_id=str(workspace_id),
    )


@router.get(
    "/sample/{event}",
    dependencies=[Depends(require_role("admin"))],
)
async def get_sample(
    event: str,
    user: tuple[User, UUID, str] = Depends(get_current_user),
) -> list[dict]:
    """
    Return sample payload for a trigger event (Zapier field mapping).

    Zapier calls this to discover the fields available in a trigger's payload,
    allowing users to map fields in their Zap actions.
    Returns a list with one sample object (Zapier expects an array).
    """
    if event not in SAMPLE_PAYLOADS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_EVENT",
                    "message": f"Unknown event '{event}'. Valid events: {', '.join(SAMPLE_PAYLOADS.keys())}",
                }
            },
        )

    return [SAMPLE_PAYLOADS[event]]


@router.get(
    "/triggers",
    response_model=list[ZapierTriggerInfo],
    dependencies=[Depends(require_role("admin"))],
)
async def list_triggers(
    user: tuple[User, UUID, str] = Depends(get_current_user),
) -> list[dict]:
    """
    List all available trigger events.

    Returns metadata about each trigger that can be used with the subscribe endpoint.
    """
    return [
        {
            "event": event_key,
            "label": info["label"],
            "description": info["description"],
        }
        for event_key, info in ZAPIER_TRIGGER_EVENTS.items()
    ]


@router.get(
    "/subscriptions",
    response_model=list[ZapierSubscribeResponse],
    dependencies=[Depends(require_role("admin"))],
)
async def list_subscriptions(
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    List all active Zapier webhook subscriptions for the workspace.
    """
    _, workspace_id, _ = user

    stmt = (
        select(WebhookAction)
        .where(
            WebhookAction.workspace_id == workspace_id,
            WebhookAction.action_type == "zapier",
        )
        .order_by(WebhookAction.created_at.desc())
    )

    result = await db.execute(stmt)
    actions = list(result.scalars().all())

    return [
        {
            "id": a.id,
            "event": a.config.get("zapier_event", a.trigger_event),
            "hook_url": a.config.get("url", ""),
            "created_at": a.created_at,
        }
        for a in actions
    ]
