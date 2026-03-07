"""
Voice API — Vapi integration, call management, escalation rules.

Endpoints for voice setup, configuration, webhook handling,
call management, and escalation rule CRUD.

RBAC:
- owner/admin: setup, config changes, escalation rule CRUD
- agent+: read config, list calls, view call details
- webhook: no auth (validated via HMAC signature)
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.channel import ChannelConfig
from app.models.conversation import Conversation
from app.models.user import User
from app.models.voice import CallLog, EscalationRule
from app.modules.voice.vapi_provider import VapiProvider
from app.modules.voice.webhook_handler import (
    dispatch_webhook,
    resolve_workspace_from_webhook,
    validate_vapi_webhook,
)
from app.schemas.voice import (
    CallListResponse,
    CallLogResponse,
    CallStatsResponse,
    EscalationRuleCreate,
    EscalationRuleResponse,
    EscalationRuleUpdate,
    VoiceConfigResponse,
    VoiceConfigUpdate,
    VoiceSetupRequest,
    WebhookPayload,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


def _get_webhook_url() -> str:
    """Build the voice webhook URL from backend config."""
    # settings.backend_url may already include /api (e.g. https://host/api)
    base = settings.backend_url.rstrip("/")
    if base.endswith("/api"):
        return f"{base}/v1/voice/webhook"
    return f"{base}/api/v1/voice/webhook"


async def _create_default_escalation_rules(workspace_id: UUID, session: AsyncSession) -> int:
    """
    Create default escalation rules for a workspace if none exist.

    Called automatically after voice setup to provide sensible defaults.
    Returns the number of rules created.
    """
    # Check if rules already exist
    existing = await session.execute(
        select(func.count(EscalationRule.id)).where(EscalationRule.workspace_id == workspace_id)
    )
    if existing.scalar() > 0:
        return 0

    now = datetime.now(UTC)
    defaults = [
        EscalationRule(
            id=uuid4(),
            workspace_id=workspace_id,
            rule_type="keyword",
            condition={
                "keywords": ["speak to human", "talk to agent", "real person"],
                "match_mode": "any",
            },
            action="escalate",
            is_active=True,
            priority=10,
            created_at=now,
        ),
        EscalationRule(
            id=uuid4(),
            workspace_id=workspace_id,
            rule_type="sentiment",
            condition={"threshold": "very_negative"},
            action="escalate",
            is_active=True,
            priority=5,
            created_at=now,
        ),
        EscalationRule(
            id=uuid4(),
            workspace_id=workspace_id,
            rule_type="confidence",
            condition={"min_confidence": 0.3},
            action="notify",
            is_active=True,
            priority=1,
            created_at=now,
        ),
    ]

    for rule in defaults:
        session.add(rule)

    logger.info(
        "default_escalation_rules_created", workspace_id=str(workspace_id), count=len(defaults)
    )
    return len(defaults)


# --- Voice Configuration ---


@router.post("/setup", response_model=VoiceConfigResponse)
async def setup_voice(
    data: VoiceSetupRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Set up voice for a workspace — validates Vapi keys and creates assistant."""
    workspace_id = current_user.workspace_id

    # Check if voice is already configured
    existing = await session.execute(
        select(ChannelConfig).where(
            ChannelConfig.workspace_id == workspace_id,
            ChannelConfig.channel == "voice",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Voice is already configured. Use PATCH /config to update or DELETE /config to reset.",
        )

    # Validate Vapi keys
    provider = VapiProvider(private_key=data.vapi_private_key)
    keys_valid = await provider.validate_keys()
    if not keys_valid:
        raise HTTPException(
            status_code=400,
            detail="Invalid Vapi API keys. Please check your private key.",
        )

    # Create Vapi assistant
    webhook_url = _get_webhook_url()
    system_prompt = data.system_prompt or (
        f"You are a helpful AI assistant for {current_user.name}'s workspace. "
        "Answer questions clearly and concisely. If you can't help, offer to connect "
        "the caller with a human agent."
    )

    try:
        assistant = await provider.create_assistant(
            name=f"BotForge - {current_user.name}",
            first_message=data.first_message,
            system_prompt=system_prompt,
            webhook_url=webhook_url,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to create Vapi assistant: {e}",
        ) from e

    # Store config in channel_configs
    now = datetime.now(UTC)
    channel_config = ChannelConfig(
        id=uuid4(),
        workspace_id=workspace_id,
        channel="voice",
        config={
            "assistant_id": assistant["id"],
            "public_key": data.vapi_public_key,
            "first_message": data.first_message,
            "voice_enabled": True,
        },
        is_active=True,
        created_at=now,
    )
    session.add(channel_config)

    # Auto-create default escalation rules
    await _create_default_escalation_rules(workspace_id, session)

    await session.commit()

    return VoiceConfigResponse(
        voice_enabled=True,
        assistant_id=assistant["id"],
        public_key=data.vapi_public_key,
        first_message=data.first_message,
        created_at=now,
    )


@router.get("/config", response_model=VoiceConfigResponse)
async def get_voice_config(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Get voice configuration status for the current workspace."""
    workspace_id = current_user.workspace_id

    result = await session.execute(
        select(ChannelConfig).where(
            ChannelConfig.workspace_id == workspace_id,
            ChannelConfig.channel == "voice",
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        return VoiceConfigResponse(voice_enabled=False)

    cfg = config.config or {}
    return VoiceConfigResponse(
        voice_enabled=cfg.get("voice_enabled", False),
        assistant_id=cfg.get("assistant_id"),
        public_key=cfg.get("public_key"),
        first_message=cfg.get("first_message"),
        created_at=config.created_at,
    )


@router.patch("/config", response_model=VoiceConfigResponse)
async def update_voice_config(
    data: VoiceConfigUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Update voice configuration for the current workspace."""
    workspace_id = current_user.workspace_id

    result = await session.execute(
        select(ChannelConfig).where(
            ChannelConfig.workspace_id == workspace_id,
            ChannelConfig.channel == "voice",
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Voice not configured. Use POST /setup first.")

    cfg = dict(config.config or {})

    if data.first_message is not None:
        cfg["first_message"] = data.first_message
    if data.voice_enabled is not None:
        cfg["voice_enabled"] = data.voice_enabled

    config.config = cfg
    await session.commit()
    await session.refresh(config)

    return VoiceConfigResponse(
        voice_enabled=cfg.get("voice_enabled", False),
        assistant_id=cfg.get("assistant_id"),
        public_key=cfg.get("public_key"),
        first_message=cfg.get("first_message"),
        created_at=config.created_at,
    )


@router.delete("/config")
async def delete_voice_config(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Disable voice and clean up Vapi assistant."""
    workspace_id = current_user.workspace_id

    result = await session.execute(
        select(ChannelConfig).where(
            ChannelConfig.workspace_id == workspace_id,
            ChannelConfig.channel == "voice",
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Voice not configured.")

    # Try to delete the Vapi assistant
    cfg = config.config or {}
    assistant_id = cfg.get("assistant_id")
    if assistant_id and settings.vapi_private_key:
        provider = VapiProvider(private_key=settings.vapi_private_key)
        await provider.delete_assistant(assistant_id)

    await session.delete(config)
    await session.commit()

    return {"status": "voice_disabled", "message": "Voice configuration removed."}


# --- Webhook ---


@router.post("/webhook")
async def voice_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    """Handle Vapi webhook events (no auth — validated via HMAC signature).

    Flow: validate signature → check idempotency → resolve workspace → dispatch.
    Always returns 200 to prevent Vapi retries on processing errors.
    """
    # 1. Validate signature
    webhook_secret = settings.vapi_webhook_secret
    if webhook_secret:
        is_valid = await validate_vapi_webhook(request, webhook_secret)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    # 2. Parse payload
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from e

    payload = WebhookPayload(message=body.get("message", body))

    # 3. Check idempotency
    from app.modules.voice.idempotency import check_idempotency

    event_id = payload.call_id or ""
    timestamp = payload.timestamp or ""
    is_duplicate = await check_idempotency(payload.event_type, event_id, timestamp)
    if is_duplicate:
        return {"status": "already_processed"}

    # 4. Resolve workspace
    workspace_id = await resolve_workspace_from_webhook(payload, session)
    if workspace_id is None:
        # Unknown assistant — return 200 to stop retries
        logger.warning("webhook.workspace_not_found", event_type=payload.event_type)
        return {"status": "ignored", "detail": "unknown assistant"}

    # 5. Dispatch to handler
    result = await dispatch_webhook(payload, workspace_id, session)
    return result


# --- Call Management ---


@router.get("/calls/stats", response_model=CallStatsResponse)
async def get_call_stats(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Get aggregated call statistics for the current workspace."""
    workspace_id = current_user.workspace_id

    # Get all call logs for this workspace via conversation join
    result = await session.execute(
        select(CallLog)
        .join(Conversation, CallLog.conversation_id == Conversation.id)
        .where(Conversation.workspace_id == workspace_id)
    )
    calls = result.scalars().all()

    total = len(calls)
    if total == 0:
        return CallStatsResponse()

    # Average duration (exclude nulls)
    durations = [c.duration_sec for c in calls if c.duration_sec is not None]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    # Escalation rate: calls with escalation actions
    escalated = sum(
        1
        for c in calls
        if c.actions_taken and any(a.get("action") == "escalate" for a in c.actions_taken)
    )
    escalation_rate = escalated / total if total > 0 else 0.0

    # Sentiment distribution
    sentiment_dist = {"positive": 0, "neutral": 0, "negative": 0}
    for c in calls:
        if c.sentiment in sentiment_dist:
            sentiment_dist[c.sentiment] += 1

    return CallStatsResponse(
        total_calls=total,
        avg_duration_sec=round(avg_duration, 1),
        escalation_rate=round(escalation_rate, 3),
        sentiment_distribution=sentiment_dist,
    )


@router.get("/calls/{call_id}", response_model=CallLogResponse)
async def get_call_detail(
    call_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Get full call detail including transcript and actions. Workspace-scoped."""
    workspace_id = current_user.workspace_id

    result = await session.execute(
        select(CallLog)
        .join(Conversation, CallLog.conversation_id == Conversation.id)
        .where(CallLog.id == call_id, Conversation.workspace_id == workspace_id)
    )
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found.")

    return CallLogResponse.model_validate(call)


@router.get("/calls/{call_id}/transcript")
async def get_call_transcript(
    call_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Get live transcript for a call. Workspace-scoped.

    Returns the current transcript text from CallLog. During active calls,
    this is updated in real-time by conversation-update webhooks.
    After call ends, contains the final transcript from end-of-call-report.
    """
    workspace_id = current_user.workspace_id

    result = await session.execute(
        select(CallLog.transcript, CallLog.status)
        .join(Conversation, CallLog.conversation_id == Conversation.id)
        .where(CallLog.id == call_id, Conversation.workspace_id == workspace_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Call not found.")

    return {
        "transcript": row.transcript or "",
        "status": row.status,
        "is_active": row.status not in ("ended", "failed", "cancelled"),
    }


@router.get("/calls", response_model=CallListResponse)
async def list_calls(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    direction: str | None = Query(None, description="Filter by direction: inbound, outbound, web"),
):
    """List calls for the current workspace (paginated, filterable)."""
    workspace_id = current_user.workspace_id

    # Base query with workspace scoping via conversation join
    base_q = (
        select(CallLog)
        .join(Conversation, CallLog.conversation_id == Conversation.id)
        .where(Conversation.workspace_id == workspace_id)
    )

    if direction:
        base_q = base_q.where(CallLog.direction == direction)

    # Count total
    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    result = await session.execute(
        base_q.order_by(CallLog.created_at.desc()).limit(page_size).offset(offset)
    )
    calls = result.scalars().all()

    return CallListResponse(
        calls=[CallLogResponse.model_validate(c) for c in calls],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/web-token")
async def get_web_token(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """Return Vapi public key for web call SDK initialization."""
    workspace_id = current_user.workspace_id

    result = await session.execute(
        select(ChannelConfig).where(
            ChannelConfig.workspace_id == workspace_id,
            ChannelConfig.channel == "voice",
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Voice not configured.")

    cfg = config.config or {}
    public_key = cfg.get("public_key")
    assistant_id = cfg.get("assistant_id")

    if not public_key:
        raise HTTPException(status_code=404, detail="No public key configured.")

    return {
        "public_key": public_key,
        "assistant_id": assistant_id,
    }


# --- Escalation Rules CRUD ---


@router.get("/escalation-rules", response_model=list[EscalationRuleResponse])
async def list_escalation_rules(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("agent")),
):
    """List escalation rules for the current workspace, sorted by priority DESC."""
    workspace_id = current_user.workspace_id

    result = await session.execute(
        select(EscalationRule)
        .where(EscalationRule.workspace_id == workspace_id)
        .order_by(EscalationRule.priority.desc())
    )
    rules = result.scalars().all()
    return [EscalationRuleResponse.model_validate(r) for r in rules]


@router.post(
    "/escalation-rules",
    response_model=EscalationRuleResponse,
    status_code=201,
)
async def create_escalation_rule(
    data: EscalationRuleCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Create a new escalation rule (admin only).

    Validates rule_type + condition schema via Pydantic model_validator.
    """
    workspace_id = current_user.workspace_id

    rule = EscalationRule(
        id=uuid4(),
        workspace_id=workspace_id,
        rule_type=data.rule_type,
        condition=data.condition,
        action=data.action,
        is_active=data.is_active,
        priority=data.priority,
        created_at=datetime.now(UTC),
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)

    return EscalationRuleResponse.model_validate(rule)


@router.patch(
    "/escalation-rules/{rule_id}",
    response_model=EscalationRuleResponse,
)
async def update_escalation_rule(
    rule_id: str,
    data: EscalationRuleUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Update an escalation rule (admin only). Workspace-scoped."""
    workspace_id = current_user.workspace_id

    result = await session.execute(
        select(EscalationRule).where(
            EscalationRule.id == rule_id,
            EscalationRule.workspace_id == workspace_id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Escalation rule not found.")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await session.commit()
    await session.refresh(rule)

    return EscalationRuleResponse.model_validate(rule)


@router.delete("/escalation-rules/{rule_id}")
async def delete_escalation_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Delete an escalation rule (admin only). Workspace-scoped."""
    workspace_id = current_user.workspace_id

    result = await session.execute(
        select(EscalationRule).where(
            EscalationRule.id == rule_id,
            EscalationRule.workspace_id == workspace_id,
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Escalation rule not found.")

    await session.delete(rule)
    await session.commit()

    return {"status": "deleted", "rule_id": rule_id}
