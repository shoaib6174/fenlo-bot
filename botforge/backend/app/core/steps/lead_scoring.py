"""
Lead Scoring Pipeline Step

Scores conversations for sales potential based on message signals.
Runs after analytics steps (sentiment, intent) so those fields are available.

Signal weights:
- Pricing/cost keywords in user message: +10
- Timeline/urgency keywords: +10
- Contact info shared (email, phone): +20
- 5+ messages in conversation: +5
- Negative sentiment on assistant response: -10
- Sales or booking intent detected: +15

Score is cumulative across the conversation (stored on Conversation.lead_score).
"""

import re

import structlog

from app.core.engine import MessageContext

logger = structlog.get_logger(__name__)

# Signal patterns
_PRICING_KEYWORDS = re.compile(
    r"\b(price|pricing|cost|how much|quote|budget|discount|plan|subscription|tier|payment)\b",
    re.IGNORECASE,
)

_TIMELINE_KEYWORDS = re.compile(
    r"\b(when|deadline|asap|urgent|timeline|schedule|start|launch|by next|this week|this month|immediately)\b",
    re.IGNORECASE,
)

_CONTACT_PATTERNS = re.compile(
    r"(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b)"  # email
    r"|(\b\+?1?\d{9,15}\b)"  # phone number
    r"|(\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b)",  # US phone
    re.IGNORECASE,
)


def calculate_lead_delta(
    user_message: str,
    sentiment: str | None = None,
    intent: str | None = None,
    message_count: int = 0,
) -> int:
    """
    Calculate the lead score delta for a single message exchange.

    Args:
        user_message: The user's message text
        sentiment: Assistant response sentiment (positive/neutral/negative)
        intent: Classified user intent
        message_count: Total messages in conversation so far

    Returns:
        Score delta (can be negative)
    """
    delta = 0

    # Pricing keywords: +10
    if _PRICING_KEYWORDS.search(user_message):
        delta += 10

    # Timeline/urgency keywords: +10
    if _TIMELINE_KEYWORDS.search(user_message):
        delta += 10

    # Contact info shared: +20
    if _CONTACT_PATTERNS.search(user_message):
        delta += 20

    # Engagement depth: +5 for 5+ messages
    if message_count >= 5:
        delta += 5

    # Sales or booking intent: +15
    if intent in ("sales", "booking"):
        delta += 15

    # Negative sentiment penalty: -10
    if sentiment == "negative":
        delta -= 10

    return delta


class LeadScoringStep:
    """
    Score conversations for sales potential.

    Calculates a delta from the current message exchange and adds it
    to the existing conversation lead_score. The cumulative score is
    set on context.lead_score for persistence.
    """

    async def execute(self, context: MessageContext) -> MessageContext:
        if not context.message:
            return context

        try:
            user_msg = context.metadata.get("original_message", context.message)
            message_count = len(context.conversation_history) if context.conversation_history else 0

            # Get existing score from conversation (stored in metadata by LoadContextStep)
            existing_score = context.metadata.get("existing_lead_score", 0) or 0

            delta = calculate_lead_delta(
                user_message=user_msg,
                sentiment=context.sentiment,
                intent=context.intent,
                message_count=message_count,
            )

            # Cumulative score, floor at 0
            context.lead_score = max(0, existing_score + delta)

            logger.debug(
                "lead_score_calculated",
                delta=delta,
                total=context.lead_score,
                existing=existing_score,
            )

        except Exception as e:
            logger.warning("lead_scoring_failed", error=str(e))
            context.lead_score = context.metadata.get("existing_lead_score", 0)

        return context
