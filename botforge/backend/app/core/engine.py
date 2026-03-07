"""
Core conversation engine with composable pipeline architecture.

This module implements the MessagePipeline pattern where each processing step
is independently testable, swappable, and can be enabled/disabled per workspace.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID


@dataclass
class MessageContext:
    """
    Context object passed through the pipeline.
    Each step can read from and write to this context.
    """

    # Input fields
    workspace_id: UUID
    user_id: UUID | None
    conversation_id: UUID | None
    message: str

    # Processing state
    system_prompt: str | None = None
    conversation_history: list[dict[str, Any]] = field(default_factory=list)
    rag_chunks: list[dict[str, Any]] = field(default_factory=list)

    # Response fields
    response: str | None = None
    response_tokens: list[str] = field(default_factory=list)

    # Metadata
    sentiment: str | None = None
    intent: str | None = None
    quality_score: float | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    lead_score: int | None = None
    tokens_used: int | None = None
    provider_used: str | None = None

    # Control flow
    should_halt: bool = False
    halt_reason: str | None = None

    # Additional data for steps
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageResult:
    """Final result returned from the pipeline."""

    conversation_id: UUID | None
    response: str
    sentiment: str | None = None
    intent: str | None = None
    quality_score: float | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    lead_score: int | None = None
    tokens_used: int | None = None
    provider_used: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PipelineStep(Protocol):
    """
    Protocol for pipeline steps.
    Each step receives context, processes it, and returns updated context.
    """

    async def execute(self, context: MessageContext) -> MessageContext:
        """
        Execute this pipeline step.

        Args:
            context: Current message context

        Returns:
            Updated message context (can be the same object, mutated)
        """
        ...


class MessagePipeline:
    """
    Composable message processing pipeline.

    Steps can be added, removed, or reordered without touching the engine.
    Each step is independently testable and swappable.

    Example:
        pipeline = MessagePipeline([
            LoadContextStep(),
            PromptGuardStep(),
            SemanticCacheStep(),
            RAGRetrievalStep(),
            BuildPromptStep(),
            BudgetCheckStep(),
            LLMStreamStep(),
            QualityScoringStep(),
            SentimentAnalysisStep(),
            IntentClassificationStep(),
            PersistenceStep(),
            UsageTrackingStep(),
            EscalationStep(),
            LeadScoringStep(),
            EventPublishStep(),
        ])

        result = await pipeline.process(context)
    """

    def __init__(self, steps: list[PipelineStep]):
        """
        Initialize pipeline with a list of steps.

        Args:
            steps: Ordered list of pipeline steps to execute
        """
        self.steps = steps

    async def process(self, context: MessageContext) -> MessageResult:
        """
        Process a message through all pipeline steps.

        Steps are executed sequentially. If any step sets should_halt=True,
        processing stops and returns the current state.

        Args:
            context: Initial message context

        Returns:
            Final message result
        """
        for step in self.steps:
            context = await step.execute(context)

            if context.should_halt:
                break

        # Convert context to result
        return MessageResult(
            conversation_id=context.conversation_id,
            response=context.response or "",
            sentiment=context.sentiment,
            intent=context.intent,
            quality_score=context.quality_score,
            citations=context.citations,
            lead_score=context.lead_score,
            tokens_used=context.tokens_used,
            provider_used=context.provider_used,
            metadata=context.metadata,
        )


class ConversationEngine:
    """
    Main conversation engine.

    Delegates message processing to the MessagePipeline.
    Pipeline can be configured per workspace based on enabled features.
    """

    def __init__(self, pipeline: MessagePipeline):
        """
        Initialize engine with a pipeline.

        Args:
            pipeline: Configured message pipeline
        """
        self.pipeline = pipeline

    async def process_message(
        self,
        workspace_id: UUID,
        message: str,
        user_id: UUID | None = None,
        conversation_id: UUID | None = None,
    ) -> MessageResult:
        """
        Process a user message and return a response.

        Args:
            workspace_id: Workspace identifier
            message: User's message text
            user_id: Optional user identifier
            conversation_id: Optional existing conversation ID

        Returns:
            Message processing result
        """
        context = MessageContext(
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
        )

        return await self.pipeline.process(context)
