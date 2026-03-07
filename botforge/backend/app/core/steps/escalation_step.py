"""
Escalation Step — evaluates escalation rules after analytics.

Runs after Sentiment/Intent/Quality steps so it has access to those signals.
If rules match, triggers handoff via HandoffService.
"""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.engine import MessageContext
from app.services.escalation_engine import EscalationEngine

logger = structlog.get_logger(__name__)


class EscalationStep:
    """
    Evaluate escalation rules and trigger handoff if matched.

    Pipeline position: after analytics (Sentiment, Intent, Quality, LeadScoring),
    before Persistence.

    Uses the existing EscalationEngine which evaluates keyword, sentiment,
    confidence, intent, and business_hours rules.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = EscalationEngine()

    async def execute(self, context: MessageContext) -> MessageContext:
        # Skip if no response (pipeline already halted) or no workspace
        if not context.response or not context.workspace_id:
            return context

        # Skip if conversation is already escalated
        if context.halt_reason == "conversation_escalated":
            return context

        try:
            # Build transcript from current message + response
            transcript = f"User: {context.message}\nAssistant: {context.response}"

            # Evaluate escalation rules
            match = await self.engine.evaluate(
                workspace_id=context.workspace_id,
                transcript=transcript,
                session=self.db,
                call_sentiment=context.sentiment,
                analysis={
                    "intent": context.intent,
                    "quality_score": context.quality_score,
                },
            )

            if match is None:
                return context

            if match.get("action") != "escalate":
                # Other actions (notify, log) — just log and continue
                logger.info(
                    "escalation_step.rule_matched_non_escalate",
                    action=match.get("action"),
                    rule_type=match.get("rule_type"),
                )
                return context

            # Trigger handoff
            logger.info(
                "escalation_step.triggering_handoff",
                conversation_id=str(context.conversation_id),
                rule_type=match.get("rule_type"),
                matched=match.get("matched"),
            )

            from app.services.handoff_service import HandoffService

            llm_router = context.metadata.get("llm_router")
            service = HandoffService(llm_router=llm_router)

            result = await service.escalate(
                conversation_id=context.conversation_id,
                workspace_id=context.workspace_id,
                reason=match,
                session=self.db,
            )

            if result.success:
                # Append escalation notice to the response
                handoff_msg = context.metadata.get(
                    "escalation_message",
                    "\n\nI'm connecting you with a human agent who can better assist you.",
                )
                context.response += handoff_msg

        except Exception as e:
            # Never block the pipeline — escalation is best-effort
            logger.warning(
                "escalation_step.failed",
                conversation_id=str(context.conversation_id),
                error=str(e),
            )

        return context
