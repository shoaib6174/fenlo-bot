"""
Handoff API — Endpoints for external systems to interact with escalated conversations.

External endpoints (HMAC-authenticated):
  POST /api/v1/handoff/reply    — Agent replies to escalated conversation
  POST /api/v1/handoff/resolve  — Agent resolves escalated conversation

Internal endpoints (JWT-authenticated):
  GET  /api/v1/handoff/status/{conversation_id}    — Get handoff state
  POST /api/v1/handoff/escalate/{conversation_id}  — Manual escalation
"""

import hashlib
import hmac as hmac_mod
import json
import time
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.conversation import Conversation
from app.models.handoff import HandoffEvent
from app.services.handoff_service import HandoffService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/handoff", tags=["handoff"])

# HMAC timestamp tolerance: 5 minutes
_HMAC_TOLERANCE_SECONDS = 300


# ── Request / Response Schemas ──────────────────────────────────────


class HandoffReplyRequest(BaseModel):
    conversation_id: UUID
    message: str = Field(..., min_length=1, max_length=5000)
    agent_name: str | None = None


class HandoffResolveRequest(BaseModel):
    conversation_id: UUID
    resolution_note: str | None = None


class HandoffStatusResponse(BaseModel):
    conversation_id: UUID
    status: str
    escalated_at: str | None = None
    resolved_at: str | None = None
    external_ticket_id: str | None = None
    handoff_provider: str | None = None
    events: list[dict] = []


# ── HMAC Validation ─────────────────────────────────────────────────


async def _validate_hmac(
    conversation_id: UUID,
    raw_body: bytes,
    signature: str | None,
    timestamp: str | None,
    session: AsyncSession,
) -> None:
    """
    Validate HMAC-SHA256 signature on incoming webhook request.

    Signature format matches GenericWebhookProvider._sign():
      HMAC-SHA256(webhook_secret, "{timestamp}.{body}")

    Raises HTTPException(401) on failure.
    """
    if not signature or not timestamp:
        raise HTTPException(status_code=401, detail="Missing signature or timestamp")

    # Replay protection: reject requests older than tolerance
    try:
        ts = int(timestamp)
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid timestamp format") from e

    if abs(time.time() - ts) > _HMAC_TOLERANCE_SECONDS:
        raise HTTPException(status_code=401, detail="Request timestamp too old")

    # Look up workspace secret via conversation
    conv = await session.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    from app.models.workspace import Workspace

    workspace = await session.get(Workspace, conv.workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    ws_settings = workspace.settings or {}
    webhook_secret = ws_settings.get("handoff", {}).get("webhook_secret", "")
    if not webhook_secret:
        raise HTTPException(status_code=401, detail="Webhook secret not configured")

    # Compute expected signature
    message = f"{timestamp}.{raw_body.decode()}"
    expected = hmac_mod.new(webhook_secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    if not hmac_mod.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")


# ── External Endpoints (HMAC-authenticated) ─────────────────────────


@router.post("/reply")
async def handoff_reply(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive an agent reply from an external system (e.g. Freshdesk, webhook).

    HMAC-authenticated via X-Webhook-Signature / X-Webhook-Timestamp headers.
    The agent's message is relayed to the user on their original channel.
    """
    raw_body = await request.body()

    # Parse body first to get conversation_id for HMAC lookup
    try:
        body_dict = json.loads(raw_body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from e

    try:
        payload = HandoffReplyRequest(**body_dict)
    except Exception as e:
        raise HTTPException(status_code=422, detail="Invalid request payload") from e

    signature = request.headers.get("x-webhook-signature")
    timestamp = request.headers.get("x-webhook-timestamp")

    await _validate_hmac(payload.conversation_id, raw_body, signature, timestamp, db)

    service = HandoffService()
    result = await service.handle_agent_reply(
        conversation_id=payload.conversation_id,
        message=payload.message,
        agent_name=payload.agent_name,
        session=db,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {"status": "ok", "message": "Reply delivered"}


@router.post("/resolve")
async def handoff_resolve_external(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve an escalated conversation from an external system.

    HMAC-authenticated via X-Webhook-Signature / X-Webhook-Timestamp headers.
    Sets conversation back to active and notifies the user.
    """
    raw_body = await request.body()

    try:
        body_dict = json.loads(raw_body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from e

    try:
        payload = HandoffResolveRequest(**body_dict)
    except Exception as e:
        raise HTTPException(status_code=422, detail="Invalid request payload") from e

    signature = request.headers.get("x-webhook-signature")
    timestamp = request.headers.get("x-webhook-timestamp")

    await _validate_hmac(payload.conversation_id, raw_body, signature, timestamp, db)

    service = HandoffService()
    result = await service.resolve(
        conversation_id=payload.conversation_id,
        session=db,
        resolution_note=payload.resolution_note,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {"status": "ok", "message": "Conversation resolved"}


# ── Internal Endpoints (JWT-authenticated) ──────────────────────────


@router.get(
    "/status/{conversation_id}",
    dependencies=[Depends(require_role("agent"))],
    response_model=HandoffStatusResponse,
)
async def handoff_status(
    conversation_id: UUID,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get handoff status for a conversation.

    Returns the conversation's escalation state, timestamps, and recent events.
    """
    user, workspace_id, role = current_user

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    metadata = conv.metadata_ or {}

    # Fetch recent handoff events
    events_result = await db.execute(
        select(HandoffEvent)
        .where(HandoffEvent.conversation_id == conversation_id)
        .order_by(desc(HandoffEvent.created_at))
        .limit(20)
    )
    events = events_result.scalars().all()

    return HandoffStatusResponse(
        conversation_id=conversation_id,
        status=conv.status or "active",
        escalated_at=metadata.get("escalated_at"),
        resolved_at=metadata.get("resolved_at"),
        external_ticket_id=metadata.get("external_ticket_id"),
        handoff_provider=metadata.get("handoff_provider"),
        events=[
            {
                "event_type": e.event_type,
                "actor": e.actor,
                "payload": e.payload,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    )


@router.post(
    "/escalate/{conversation_id}",
    dependencies=[Depends(require_role("agent"))],
)
async def handoff_escalate_manual(
    conversation_id: UUID,
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually escalate a conversation to a human agent.

    Used from the inbox UI by an internal agent/admin.
    """
    user, workspace_id, role = current_user

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conv.status == "escalated":
        raise HTTPException(status_code=409, detail="Conversation already escalated")

    service = HandoffService()
    result = await service.escalate(
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        reason={"rule_type": "manual", "triggered_by": user.email},
        session=db,
    )

    if not result.success:
        status_code = 429 if "rate limit" in (result.error or "").lower() else 400
        raise HTTPException(status_code=status_code, detail=result.error)

    return {
        "status": "ok",
        "message": "Conversation escalated",
        "external_ticket_id": result.external_ticket_id,
    }


# ── Freshdesk Webhook (7.26) ───────────────────────────────────────


@router.post("/freshdesk-webhook")
async def freshdesk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Freshdesk webhook payloads (agent reply or ticket resolved).

    Freshdesk sends webhooks on ticket updates. We look for the
    conversation_id in custom fields and map the action to reply/resolve.

    No HMAC — Freshdesk uses a simple shared token in the URL or headers.
    Validated via x-freshdesk-token header against workspace settings.
    """
    raw_body = await request.body()

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    # Extract conversation_id from freshdesk custom fields
    custom_fields = body.get("ticket", {}).get("custom_fields", {})
    conv_id_str = custom_fields.get("cf_conversation_id")
    if not conv_id_str:
        # Fallback: top-level field
        conv_id_str = body.get("conversation_id")

    if not conv_id_str:
        return {"status": "ignored", "detail": "No conversation_id found"}

    from uuid import UUID as UUIDType

    try:
        conv_id = UUIDType(conv_id_str)
    except ValueError:
        return {"status": "ignored", "detail": "Invalid conversation_id format"}

    # Validate freshdesk token
    token = request.headers.get("x-freshdesk-token")
    conv = await db.get(Conversation, conv_id)
    if not conv:
        return {"status": "ignored", "detail": "Conversation not found"}

    from app.models.workspace import Workspace

    workspace = await db.get(Workspace, conv.workspace_id)
    expected_token = (
        (workspace.settings or {}).get("handoff", {}).get("freshdesk_webhook_token", "")
        if workspace
        else ""
    )
    if expected_token and token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid Freshdesk token")

    # Determine action from ticket status or note
    ticket = body.get("ticket", {})
    ticket_status = ticket.get("status")
    agent_name = body.get("agent", {}).get("name") or ticket.get("responder_name")

    service = HandoffService()

    # Status 4 or 5 = Resolved/Closed in Freshdesk
    if ticket_status in (4, 5):
        result = await service.resolve(
            conversation_id=conv_id,
            session=db,
            resolution_note=body.get("resolution_note"),
        )
        return {"status": "ok" if result.success else "error", "action": "resolved"}

    # If there's a latest note/reply, forward as agent reply
    note_body = body.get("note", {}).get("body") or body.get("reply", {}).get("body")
    if note_body:
        # Strip HTML tags for plain text relay
        import re

        plain_text = re.sub(r"<[^>]+>", "", note_body).strip()
        if plain_text:
            result = await service.handle_agent_reply(
                conversation_id=conv_id,
                message=plain_text,
                agent_name=agent_name,
                session=db,
            )
            return {"status": "ok" if result.success else "error", "action": "replied"}

    return {"status": "ignored", "detail": "No actionable content"}
