"""Unit tests for MessagePipeline and ConversationEngine."""

from uuid import uuid4

import pytest

from app.core.engine import (
    ConversationEngine,
    MessageContext,
    MessagePipeline,
)


class MockStep:
    """Mock pipeline step for testing."""

    def __init__(self, name: str, should_halt: bool = False):
        self.name = name
        self.executed = False
        self.should_halt = should_halt

    async def execute(self, context: MessageContext) -> MessageContext:
        self.executed = True
        context.metadata[f"{self.name}_executed"] = True

        if self.should_halt:
            context.should_halt = True
            context.halt_reason = f"halted_by_{self.name}"
            context.response = f"Halted by {self.name}"

        return context


@pytest.mark.asyncio
class TestMessagePipeline:
    """Test MessagePipeline behavior."""

    async def test_pipeline_executes_steps_sequentially(self):
        """Test that pipeline executes all steps in order."""
        step1 = MockStep("step1")
        step2 = MockStep("step2")
        step3 = MockStep("step3")

        pipeline = MessagePipeline([step1, step2, step3])

        context = MessageContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            conversation_id=None,
            message="test message",
        )

        await pipeline.process(context)

        assert step1.executed
        assert step2.executed
        assert step3.executed
        assert context.metadata["step1_executed"]
        assert context.metadata["step2_executed"]
        assert context.metadata["step3_executed"]

    async def test_pipeline_halts_on_should_halt(self):
        """Test that pipeline stops when a step sets should_halt."""
        step1 = MockStep("step1")
        step2 = MockStep("step2", should_halt=True)
        step3 = MockStep("step3")

        pipeline = MessagePipeline([step1, step2, step3])

        context = MessageContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            conversation_id=None,
            message="test message",
        )

        result = await pipeline.process(context)

        assert step1.executed
        assert step2.executed
        assert not step3.executed  # Should not execute after halt
        assert result.response == "Halted by step2"

    async def test_pipeline_returns_message_result(self):
        """Test that pipeline converts context to MessageResult."""
        step = MockStep("step")

        pipeline = MessagePipeline([step])

        workspace_id = uuid4()
        conversation_id = uuid4()

        context = MessageContext(
            workspace_id=workspace_id,
            user_id=uuid4(),
            conversation_id=conversation_id,
            message="test message",
        )

        # Simulate a step that sets response data
        context.response = "Test response"
        context.sentiment = "positive"
        context.quality_score = 0.85

        result = await pipeline.process(context)

        assert result.conversation_id == conversation_id
        assert result.response == "Test response"
        assert result.sentiment == "positive"
        assert result.quality_score == 0.85

    async def test_empty_pipeline_returns_empty_response(self):
        """Test that empty pipeline returns empty result."""
        pipeline = MessagePipeline([])

        context = MessageContext(
            workspace_id=uuid4(),
            user_id=uuid4(),
            conversation_id=None,
            message="test message",
        )

        result = await pipeline.process(context)

        assert result.response == ""
        assert result.conversation_id is None


@pytest.mark.asyncio
class TestConversationEngine:
    """Test ConversationEngine behavior."""

    async def test_engine_delegates_to_pipeline(self):
        """Test that engine delegates processing to pipeline."""
        step = MockStep("step")
        pipeline = MessagePipeline([step])
        engine = ConversationEngine(pipeline)

        workspace_id = uuid4()
        user_id = uuid4()

        result = await engine.process_message(
            workspace_id=workspace_id,
            message="Hello",
            user_id=user_id,
        )

        assert step.executed
        assert result.response == ""  # Empty since mock step doesn't set response

    async def test_engine_creates_context_correctly(self):
        """Test that engine creates proper MessageContext."""

        class ContextCheckStep:
            def __init__(self):
                self.context = None

            async def execute(self, context: MessageContext) -> MessageContext:
                self.context = context
                return context

        check_step = ContextCheckStep()
        pipeline = MessagePipeline([check_step])
        engine = ConversationEngine(pipeline)

        workspace_id = uuid4()
        user_id = uuid4()
        conversation_id = uuid4()

        await engine.process_message(
            workspace_id=workspace_id,
            message="Test message",
            user_id=user_id,
            conversation_id=conversation_id,
        )

        assert check_step.context is not None
        assert check_step.context.workspace_id == workspace_id
        assert check_step.context.user_id == user_id
        assert check_step.context.conversation_id == conversation_id
        assert check_step.context.message == "Test message"
