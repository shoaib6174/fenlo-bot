"""Pipeline step for usage tracking."""

from app.core.engine import MessageContext, PipelineStep
from app.services.usage_tracker import UsageTracker


class UsageTrackingStep(PipelineStep):
    """Track token usage after LLM call.

    Increments workspace_usage atomically with:
    - LLM tokens (in + out)
    - API call count
    - Estimated cost
    """

    def __init__(self, usage_tracker: UsageTracker):
        self.usage_tracker = usage_tracker

    async def execute(self, context: MessageContext) -> MessageContext:
        """Track usage from LLM response."""
        # Only track if we actually made an LLM call
        if not context.should_halt and context.metadata.get("tokens_used"):
            tokens_used = context.metadata["tokens_used"]
            provider = context.metadata.get("provider", "groq")

            await self.usage_tracker.track_llm_usage(
                db=context.db,
                workspace_id=context.workspace_id,
                tokens_in=tokens_used.get("input", 0),
                tokens_out=tokens_used.get("output", 0),
                provider=provider,
            )

        return context
