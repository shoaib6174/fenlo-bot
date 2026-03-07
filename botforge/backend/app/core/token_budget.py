"""Token budget enforcement for workspaces.

Prevents workspaces from exceeding their monthly token allocation.
- At 80%: emit warning event
- At 100%: complete current response, then block subsequent requests
- Never truncate mid-response
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.models.workspace import WorkspaceUsage


class TokenBudgetError(Exception):
    """Raised when workspace has exhausted token budget."""

    pass


class TokenBudgetGuard:
    """Enforces monthly token budget limits per workspace.

    Design:
    - Check before each LLM call
    - Emit warning at 80% usage
    - Block at 100% usage (after completing current response)
    - Default: 1M tokens/month
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._warning_emitted: set[str] = set()  # Track which workspaces already warned

    async def check_budget(
        self,
        db: AsyncSession,
        workspace_id: str,
        estimated_tokens: int = 1000,  # Estimate for upcoming request
    ) -> tuple[bool, str | None]:
        """Check if workspace is within budget.

        Args:
            db: Database session
            workspace_id: Workspace to check
            estimated_tokens: Estimated tokens for upcoming request

        Returns:
            (allowed: bool, message: Optional[str])
            - (True, None) if within budget
            - (False, "error message") if budget exhausted

        Side effects:
            - Emits token.budget_warning event at 80%
            - Emits token.budget_exhausted event at 100%
        """
        # Get workspace settings and current usage
        usage = await self._get_current_usage(db, workspace_id)
        budget = await self._get_budget_limit(db, workspace_id)

        current_usage = usage.llm_tokens_in + usage.llm_tokens_out
        projected_usage = current_usage + estimated_tokens
        usage_percentage = (projected_usage / budget) * 100 if budget > 0 else 0

        # At 80%: emit warning (once per period)
        if usage_percentage >= 80 and workspace_id not in self._warning_emitted:
            await self.event_bus.publish(
                "token.budget_warning",
                {
                    "workspace_id": workspace_id,
                    "current_usage": current_usage,
                    "budget": budget,
                    "percentage": usage_percentage,
                },
            )
            self._warning_emitted.add(workspace_id)

        # At 100%: block request
        if projected_usage >= budget:
            await self.event_bus.publish(
                "token.budget_exhausted",
                {
                    "workspace_id": workspace_id,
                    "current_usage": current_usage,
                    "budget": budget,
                },
            )
            return False, "Monthly token budget exhausted. Contact your workspace admin to upgrade."

        return True, None

    async def _get_current_usage(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> WorkspaceUsage:
        """Get current month's usage for workspace."""
        from datetime import date

        current_period = date.today().replace(day=1)  # First day of current month

        result = await db.execute(
            select(WorkspaceUsage).where(
                WorkspaceUsage.workspace_id == workspace_id,
                WorkspaceUsage.period == current_period,
            )
        )
        usage = result.scalar_one_or_none()

        # Create usage record if doesn't exist
        if usage is None:
            usage = WorkspaceUsage(
                workspace_id=workspace_id,
                period=current_period,
                llm_tokens_in=0,
                llm_tokens_out=0,
                vector_queries=0,
                documents_stored=0,
                storage_bytes=0,
                api_calls=0,
                estimated_cost=0.0,
            )
            db.add(usage)
            await db.flush()

        return usage

    async def _get_budget_limit(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> int:
        """Get token budget limit for workspace.

        Default: 1,000,000 tokens/month
        Can be overridden in workspace settings.
        """
        from app.models.workspace import Workspace

        result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
        workspace = result.scalar_one_or_none()

        if workspace and workspace.settings:
            return workspace.settings.get("token_budget_monthly", 1_000_000)

        return 1_000_000  # Default

    def reset_warnings(self):
        """Reset warning emission tracking (call at start of new month)."""
        self._warning_emitted.clear()
