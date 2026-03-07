"""
Booking Enrichment Step — injects booking context when intent is "booking" (S88).

Runs after IntentClassificationStep. When intent == "booking":
1. Reads workspace settings for booking configuration
2. If configured: adds booking metadata (provider, URL, prompt) to context
3. If not configured: no-op (response already handles generically)

The frontend uses `metadata.booking_config` to render an inline booking card.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.engine import MessageContext
from app.models.workspace import Workspace

logger = structlog.get_logger(__name__)

DEFAULT_BOOKING_PROMPT = (
    "I'd be happy to help you schedule a meeting! "
    "Click the button below to pick a time that works for you."
)


class BookingEnrichmentStep:
    """
    Enrich message context with booking info when booking intent is detected.

    Adds `booking_config` to context.metadata with:
    - provider: calendly | cal_com | google | custom_url
    - url: the scheduling page URL
    - prompt: custom message to show with the booking card
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, context: MessageContext) -> MessageContext:
        if context.intent != "booking":
            return context

        try:
            stmt = select(Workspace).where(Workspace.id == context.workspace_id)
            result = await self.db.execute(stmt)
            workspace = result.scalar_one_or_none()

            if not workspace:
                return context

            settings = workspace.settings or {}
            booking = settings.get("booking", {})
            booking_url = booking.get("booking_url", "")

            if not booking_url:
                logger.debug("booking_intent_no_config", workspace_id=str(context.workspace_id))
                return context

            context.metadata["booking_config"] = {
                "provider": booking.get("booking_provider", "custom_url"),
                "url": booking_url,
                "prompt": booking.get("booking_prompt", DEFAULT_BOOKING_PROMPT),
            }

            logger.info(
                "booking_enrichment_applied",
                workspace_id=str(context.workspace_id),
                provider=booking.get("booking_provider", "custom_url"),
            )

        except Exception as e:
            logger.warning("booking_enrichment_failed", error=str(e))

        return context
