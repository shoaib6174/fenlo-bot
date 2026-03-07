"""Usage metering and cost estimation for workspaces.

Tracks:
- LLM tokens (input + output)
- Vector queries
- Documents stored
- Storage bytes
- API calls

Subscribes to events from the event bus to track usage atomically.
"""

from datetime import date
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.models.workspace import WorkspaceUsage

ProviderType = Literal["groq", "openai"]


class UsageTracker:
    """Tracks workspace usage and estimates costs.

    Design:
    - Atomic increments to workspace_usage table
    - Subscribes to message.created events
    - Calculates estimated costs based on provider pricing
    """

    # Provider pricing (per 1M tokens)
    PROVIDER_PRICING = {
        "groq": {
            "input": 0.05,  # $0.05 per 1M input tokens
            "output": 0.05,  # $0.05 per 1M output tokens
        },
        "openai": {
            "input": 0.15,  # $0.15 per 1M input tokens (GPT-4o-mini)
            "output": 0.60,  # $0.60 per 1M output tokens
        },
    }

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        # Subscribe to events
        self.event_bus.subscribe("message.created", self._on_message_created)

    async def track_llm_usage(
        self,
        db: AsyncSession,
        workspace_id: str,
        tokens_in: int,
        tokens_out: int,
        provider: ProviderType,
    ) -> None:
        """Track LLM token usage and estimate cost.

        Args:
            db: Database session
            workspace_id: Workspace ID
            tokens_in: Input tokens used
            tokens_out: Output tokens used
            provider: LLM provider used (groq/openai)
        """
        current_period = date.today().replace(day=1)  # First day of current month
        cost = self._estimate_cost(tokens_in, tokens_out, provider)

        # Atomic increment using INSERT ... ON CONFLICT
        await db.execute(
            """
            INSERT INTO workspace_usage (
                workspace_id, period, llm_tokens_in, llm_tokens_out,
                api_calls, estimated_cost
            )
            VALUES (:ws, :period, :ti, :to, 1, :cost)
            ON CONFLICT (workspace_id, period) DO UPDATE SET
                llm_tokens_in = workspace_usage.llm_tokens_in + :ti,
                llm_tokens_out = workspace_usage.llm_tokens_out + :to,
                api_calls = workspace_usage.api_calls + 1,
                estimated_cost = workspace_usage.estimated_cost + :cost
            """,
            {
                "ws": workspace_id,
                "period": current_period,
                "ti": tokens_in,
                "to": tokens_out,
                "cost": cost,
            },
        )
        await db.commit()

    async def track_vector_query(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> None:
        """Track a vector database query."""
        current_period = date.today().replace(day=1)

        await db.execute(
            """
            INSERT INTO workspace_usage (workspace_id, period, vector_queries)
            VALUES (:ws, :period, 1)
            ON CONFLICT (workspace_id, period) DO UPDATE SET
                vector_queries = workspace_usage.vector_queries + 1
            """,
            {"ws": workspace_id, "period": current_period},
        )
        await db.commit()

    async def track_document_storage(
        self,
        db: AsyncSession,
        workspace_id: str,
        bytes_added: int,
    ) -> None:
        """Track document storage (bytes)."""
        current_period = date.today().replace(day=1)

        await db.execute(
            """
            INSERT INTO workspace_usage (workspace_id, period, documents_stored, storage_bytes)
            VALUES (:ws, :period, 1, :bytes)
            ON CONFLICT (workspace_id, period) DO UPDATE SET
                documents_stored = workspace_usage.documents_stored + 1,
                storage_bytes = workspace_usage.storage_bytes + :bytes
            """,
            {"ws": workspace_id, "period": current_period, "bytes": bytes_added},
        )
        await db.commit()

    async def get_current_usage(
        self,
        db: AsyncSession,
        workspace_id: str,
    ) -> WorkspaceUsage:
        """Get current month's usage for a workspace."""
        current_period = date.today().replace(day=1)

        result = await db.execute(
            select(WorkspaceUsage).where(
                WorkspaceUsage.workspace_id == workspace_id,
                WorkspaceUsage.period == current_period,
            )
        )
        usage = result.scalar_one_or_none()

        # Return zero usage if no record exists
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

        return usage

    def _estimate_cost(
        self,
        tokens_in: int,
        tokens_out: int,
        provider: ProviderType,
    ) -> float:
        """Estimate cost for LLM usage.

        Returns cost in USD.
        """
        pricing = self.PROVIDER_PRICING.get(provider, self.PROVIDER_PRICING["openai"])

        cost_in = (tokens_in / 1_000_000) * pricing["input"]
        cost_out = (tokens_out / 1_000_000) * pricing["output"]

        return round(cost_in + cost_out, 6)  # 6 decimal places

    async def _on_message_created(self, event_data: dict) -> None:
        """Event handler for message.created events.

        Automatically tracks usage when messages are created.
        """
        # This will be called by the event bus when a message is created
        # The actual tracking happens in the LLM step via track_llm_usage
        pass
