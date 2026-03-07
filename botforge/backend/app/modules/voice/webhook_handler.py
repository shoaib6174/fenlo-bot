"""Vapi webhook handler — signature validation, workspace resolution, event dispatch.

Flow:
1. Validate signature (HMAC-SHA256)
2. Check idempotency (Redis SET NX)
3. Resolve workspace from assistantId → channel_configs → workspace_id
4. Dispatch to handler based on event type:
   - status-update: create/update CallLog via state machine
   - end-of-call-report: store transcript, summary, recording URL, run escalation
"""

import asyncio
import hashlib
import hmac
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.event_bus import EventTypes, create_event_bus
from app.models.channel import ChannelConfig
from app.models.conversation import Conversation
from app.models.voice import CallLog
from app.modules.voice.call_state import CallStateMachine, InvalidTransitionError
from app.schemas.voice import WebhookPayload
from app.services.escalation_engine import EscalationEngine

logger = structlog.get_logger()

_state_machine = CallStateMachine()
_escalation_engine = EscalationEngine()


# --- Signature Validation ---


async def validate_vapi_webhook(request: Request, secret: str) -> bool:
    """Validate Vapi webhook HMAC-SHA256 signature.

    Vapi signs webhooks using the webhook secret configured on the assistant.
    The signature is sent in the ``x-vapi-signature`` header.

    Args:
        request: FastAPI/Starlette Request.
        secret: Webhook signing secret.

    Returns:
        True if signature is valid, False otherwise.
    """
    signature = request.headers.get("x-vapi-signature")
    if not signature:
        logger.warning("webhook.missing_signature")
        return False

    body = await request.body()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


# --- Workspace Resolution ---


async def resolve_workspace_from_webhook(
    payload: WebhookPayload, session: AsyncSession
) -> UUID | None:
    """Resolve workspace_id from Vapi webhook payload.

    Every Vapi assistant is created per-workspace during voice setup.
    The assistant_id is stored in channel_configs.config['assistant_id'].

    Flow: assistantId (from webhook) → channel_configs lookup → workspace_id
    """
    assistant_id = payload.assistant_id
    if not assistant_id:
        logger.warning(
            "webhook.no_assistant_id",
            event_type=payload.event_type,
        )
        return None

    result = await session.execute(
        select(ChannelConfig.workspace_id)
        .where(ChannelConfig.channel == "voice")
        .where(ChannelConfig.config["assistant_id"].astext == assistant_id)
    )
    workspace_id = result.scalar_one_or_none()

    if workspace_id is None:
        logger.warning(
            "webhook.unknown_assistant",
            assistant_id=assistant_id,
        )
    return workspace_id


# --- Event Handlers ---


async def handle_status_update(
    payload: WebhookPayload,
    workspace_id: UUID,
    session: AsyncSession,
) -> dict:
    """Handle Vapi status-update event.

    Creates or updates CallLog based on call state transitions.
    Creates a linked Conversation on first call event.
    """
    call_id = payload.call_id
    if not call_id:
        logger.warning("webhook.status_update_no_call_id")
        return {"status": "error", "detail": "no call_id"}

    status = payload.status
    if not status:
        logger.warning("webhook.status_update_no_status", call_id=call_id)
        return {"status": "error", "detail": "no status"}

    # Look up existing CallLog by vapi_call_id
    result = await session.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
    call_log = result.scalar_one_or_none()

    if call_log is None:
        # First event for this call — create Conversation + CallLog
        now = datetime.now(UTC)
        phone_info = payload.phone_number
        direction = payload.direction

        conversation = Conversation(
            id=uuid4(),
            workspace_id=workspace_id,
            channel="voice",
            external_id=call_id,
            contact_name=None,
            contact_info={"phone": phone_info.get("from"), "source": "vapi"},
            status="active",
            metadata_={"vapi_call_id": call_id, "direction": direction},
            started_at=now,
        )
        session.add(conversation)
        await session.flush()  # Get conversation.id

        # Determine initial state from event
        try:
            initial_state = _state_machine._map_event_to_state(status)
        except Exception:
            initial_state = "initiated"

        call_log = CallLog(
            id=uuid4(),
            conversation_id=conversation.id,
            vapi_call_id=call_id,
            direction=direction,
            phone_from=phone_info.get("from") or "",
            phone_to=phone_info.get("to") or "",
            status=initial_state,
            created_at=now,
        )
        session.add(call_log)
        logger.info(
            "webhook.call_created",
            call_id=call_id,
            state=initial_state,
            direction=direction,
            workspace_id=str(workspace_id),
        )
        return {"status": "created", "state": initial_state}

    # Existing call — transition state
    try:
        new_state = _state_machine.transition(call_log.status, status)
    except InvalidTransitionError as e:
        logger.warning(
            "webhook.invalid_transition",
            call_id=call_id,
            error=str(e),
        )
        return {"status": "ignored", "detail": str(e)}

    if new_state != call_log.status:
        call_log.status = new_state
        logger.info(
            "webhook.state_updated",
            call_id=call_id,
            new_state=new_state,
        )

    return {"status": "updated", "state": new_state}


async def handle_end_of_call_report(
    payload: WebhookPayload,
    workspace_id: UUID,
    session: AsyncSession,
) -> dict:
    """Handle Vapi end-of-call-report event.

    Stores transcript, summary, recording URL, duration, and sentiment.
    Transitions call to 'ended' state.
    """
    call_id = payload.call_id
    if not call_id:
        logger.warning("webhook.eocr_no_call_id")
        return {"status": "error", "detail": "no call_id"}

    result = await session.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
    call_log = result.scalar_one_or_none()

    if call_log is None:
        # end-of-call-report arrived before status-update (race condition)
        # Create the call record directly
        now = datetime.now(UTC)
        phone_info = payload.phone_number
        direction = payload.direction

        conversation = Conversation(
            id=uuid4(),
            workspace_id=workspace_id,
            channel="voice",
            external_id=call_id,
            status="active",
            contact_info={"phone": phone_info.get("from"), "source": "vapi"},
            metadata_={"vapi_call_id": call_id, "direction": direction},
            started_at=now,
        )
        session.add(conversation)
        await session.flush()

        call_log = CallLog(
            id=uuid4(),
            conversation_id=conversation.id,
            vapi_call_id=call_id,
            direction=direction,
            phone_from=phone_info.get("from") or "",
            phone_to=phone_info.get("to") or "",
            status="ended",
            created_at=now,
        )
        session.add(call_log)

    # Transition to ended (if not already terminal)
    ended_reason = payload.ended_reason
    if ended_reason:
        try:
            new_state = _state_machine.transition(call_log.status, ended_reason)
            call_log.status = new_state
        except InvalidTransitionError:
            # Already terminal or invalid — use end-of-call-report default
            if call_log.status not in CallStateMachine.TERMINAL_STATES:
                call_log.status = "ended"
    elif call_log.status not in CallStateMachine.TERMINAL_STATES:
        call_log.status = "ended"

    # Store call details
    call_log.transcript = payload.transcript
    call_log.summary = payload.summary
    call_log.recording_url = payload.recording_url
    call_log.duration_sec = payload.duration_sec

    # Extract sentiment from Vapi analysis
    analysis = payload.analysis
    if analysis:
        success_eval = analysis.get("successEvaluation", "")
        if success_eval:
            sentiment_map = {
                "true": "positive",
                "false": "negative",
                "unknown": "neutral",
            }
            call_log.sentiment = sentiment_map.get(str(success_eval).lower(), "neutral")

    # --- Run Escalation Engine ---
    escalation_result = await _escalation_engine.evaluate(
        workspace_id,
        call_log.transcript,
        session,
        call_sentiment=call_log.sentiment,
        analysis=analysis,
    )

    if escalation_result:
        # Update CallLog.actions_taken
        actions = list(call_log.actions_taken or [])
        actions.append(escalation_result)
        call_log.actions_taken = actions

        # Set Conversation.status to "escalated" if action is "escalate"
        if escalation_result.get("action") == "escalate":
            conv_result = await session.execute(
                select(Conversation).where(Conversation.id == call_log.conversation_id)
            )
            conversation = conv_result.scalar_one_or_none()
            if conversation:
                conversation.status = "escalated"

            # Emit call.escalated event via EventBus
            event_bus = create_event_bus(settings)
            asyncio.create_task(
                event_bus.publish(
                    EventTypes.CONVERSATION_ESCALATED,
                    {
                        "workspace_id": str(workspace_id),
                        "conversation_id": str(call_log.conversation_id),
                        "call_log_id": str(call_log.id),
                        "rule_type": escalation_result["rule_type"],
                        "action": escalation_result["action"],
                        "matched": escalation_result["matched"],
                    },
                )
            )

        logger.info(
            "webhook.escalation_triggered",
            call_id=call_id,
            rule_type=escalation_result["rule_type"],
            action=escalation_result["action"],
            matched=escalation_result["matched"],
        )

    logger.info(
        "webhook.eocr_processed",
        call_id=call_id,
        duration=call_log.duration_sec,
        has_transcript=bool(call_log.transcript),
        sentiment=call_log.sentiment,
        escalated=bool(escalation_result),
    )

    return {
        "status": "processed",
        "state": call_log.status,
        "call_log_id": str(call_log.id),
        "escalation": escalation_result,
    }


async def handle_conversation_update(
    payload: WebhookPayload,
    workspace_id: UUID,
    session: AsyncSession,
) -> dict:
    """Handle Vapi conversation-update event — real-time transcript streaming.

    Extracts partial transcript from the webhook and stores it on the
    CallLog for polling.  Does NOT replace the final transcript stored
    by end-of-call-report.
    """
    call_id = payload.call_id
    if not call_id:
        logger.warning("webhook.conversation_update_no_call_id")
        return {"status": "error", "detail": "no call_id"}

    messages = payload.conversation_messages
    if not messages:
        return {"status": "ignored", "detail": "no messages"}

    # Find existing call log
    result = await session.execute(select(CallLog).where(CallLog.vapi_call_id == call_id))
    call_log = result.scalar_one_or_none()

    if call_log is None:
        logger.debug("webhook.conversation_update_no_call", call_id=call_id)
        return {"status": "ignored", "detail": "call not found"}

    # Build partial transcript text from messages
    transcript_lines = [f"{m['role']}: {m['content']}" for m in messages]
    call_log.transcript = "\n".join(transcript_lines)

    logger.debug(
        "webhook.conversation_update",
        call_id=call_id,
        message_count=len(messages),
    )

    return {"status": "updated", "message_count": len(messages)}


# --- Dispatch ---


async def dispatch_webhook(
    payload: WebhookPayload,
    workspace_id: UUID,
    session: AsyncSession,
) -> dict:
    """Dispatch a validated webhook event to the appropriate handler."""
    event_type = payload.event_type

    if event_type == "status-update":
        return await handle_status_update(payload, workspace_id, session)
    elif event_type == "end-of-call-report":
        return await handle_end_of_call_report(payload, workspace_id, session)
    elif event_type == "conversation-update":
        return await handle_conversation_update(payload, workspace_id, session)
    else:
        logger.info("webhook.unhandled_event", event_type=event_type)
        return {"status": "ignored", "event_type": event_type}
