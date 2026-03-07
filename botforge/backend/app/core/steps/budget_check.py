"""Pipeline step for token budget enforcement."""

from app.core.engine import MessageContext, PipelineStep
from app.core.token_budget import TokenBudgetGuard


class BudgetCheckStep(PipelineStep):
    """Check workspace token budget before LLM call.

    - Emits warning at 80%
    - Blocks at 100% (after completing current response)
    - Sets context.should_halt if budget exhausted
    """

    def __init__(self, budget_guard: TokenBudgetGuard):
        self.budget_guard = budget_guard

    async def execute(self, context: MessageContext) -> MessageContext:
        """Check budget before proceeding to LLM call."""
        allowed, message = await self.budget_guard.check_budget(
            db=context.db,
            workspace_id=context.workspace_id,
            estimated_tokens=1000,  # Rough estimate for typical request
        )

        if not allowed:
            # Budget exhausted - halt pipeline and return error message
            context.should_halt = True
            context.result = {
                "role": "assistant",
                "content": message,
                "metadata": {
                    "budget_exhausted": True,
                },
            }

        return context
