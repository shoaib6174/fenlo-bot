"""Unit tests for analytics pipeline steps (sentiment, intent, quality)."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.engine import MessageContext
from app.core.steps.analytics import (
    IntentClassifierStep,
    QualityScorerStep,
    SentimentAnalysisStep,
)


def _make_context(**overrides) -> MessageContext:
    """Create a test MessageContext with sensible defaults."""
    defaults = {
        "workspace_id": uuid4(),
        "user_id": uuid4(),
        "conversation_id": uuid4(),
        "message": "What are your business hours?",
        "response": "We are open Monday through Friday, 9 AM to 6 PM EST.",
    }
    defaults.update(overrides)
    ctx = MessageContext(
        workspace_id=defaults["workspace_id"],
        user_id=defaults.get("user_id"),
        conversation_id=defaults.get("conversation_id"),
        message=defaults["message"],
    )
    ctx.response = defaults.get("response")
    ctx.rag_chunks = defaults.get("rag_chunks", [])
    ctx.citations = defaults.get("citations", [])
    ctx.metadata = defaults.get("metadata", {})
    return ctx


def _mock_llm_router(content: str) -> AsyncMock:
    """Create a mock LLM router that returns the given content."""
    router = AsyncMock()
    router.complete = AsyncMock(return_value={"content": content})
    return router


# --- Sentiment Analysis Tests ---


@pytest.mark.asyncio
class TestSentimentAnalysisStep:
    async def test_positive_sentiment(self):
        router = _mock_llm_router("positive")
        ctx = _make_context(metadata={"llm_router": router})

        result = await SentimentAnalysisStep().execute(ctx)

        assert result.sentiment == "positive"
        router.complete.assert_called_once()

    async def test_negative_sentiment(self):
        router = _mock_llm_router("negative")
        ctx = _make_context(metadata={"llm_router": router})

        result = await SentimentAnalysisStep().execute(ctx)

        assert result.sentiment == "negative"

    async def test_neutral_fallback_on_invalid(self):
        router = _mock_llm_router("happy")  # invalid sentiment
        ctx = _make_context(metadata={"llm_router": router})

        result = await SentimentAnalysisStep().execute(ctx)

        assert result.sentiment == "neutral"

    async def test_neutral_fallback_on_error(self):
        router = AsyncMock()
        router.complete = AsyncMock(side_effect=Exception("LLM down"))
        ctx = _make_context(metadata={"llm_router": router})

        result = await SentimentAnalysisStep().execute(ctx)

        assert result.sentiment == "neutral"

    async def test_skip_when_no_response(self):
        ctx = _make_context(response=None)

        result = await SentimentAnalysisStep().execute(ctx)

        assert result.sentiment is None

    async def test_skip_when_no_router(self):
        ctx = _make_context()  # no llm_router in metadata

        result = await SentimentAnalysisStep().execute(ctx)

        assert result.sentiment is None


# --- Intent Classification Tests ---


@pytest.mark.asyncio
class TestIntentClassifierStep:
    async def test_faq_intent(self):
        router = _mock_llm_router("faq")
        ctx = _make_context(metadata={"llm_router": router})

        result = await IntentClassifierStep().execute(ctx)

        assert result.intent == "faq"

    async def test_sales_intent(self):
        router = _mock_llm_router("sales")
        ctx = _make_context(
            message="How much does the enterprise plan cost?",
            metadata={"llm_router": router},
        )

        result = await IntentClassifierStep().execute(ctx)

        assert result.intent == "sales"

    async def test_escalation_intent(self):
        router = _mock_llm_router("escalation")
        ctx = _make_context(
            message="I want to speak to a human",
            metadata={"llm_router": router},
        )

        result = await IntentClassifierStep().execute(ctx)

        assert result.intent == "escalation"

    async def test_other_fallback_on_invalid(self):
        router = _mock_llm_router("unknown_intent")
        ctx = _make_context(metadata={"llm_router": router})

        result = await IntentClassifierStep().execute(ctx)

        assert result.intent == "other"

    async def test_other_fallback_on_error(self):
        router = AsyncMock()
        router.complete = AsyncMock(side_effect=Exception("timeout"))
        ctx = _make_context(metadata={"llm_router": router})

        result = await IntentClassifierStep().execute(ctx)

        assert result.intent == "other"

    async def test_uses_original_message(self):
        """Intent should classify the original user message, not the prompt-guarded version."""
        router = _mock_llm_router("support")
        ctx = _make_context(
            message="[SAFE] Help me reset my password [/SAFE]",
            metadata={
                "llm_router": router,
                "original_message": "Help me reset my password",
            },
        )

        result = await IntentClassifierStep().execute(ctx)

        assert result.intent == "support"
        call_content = router.complete.call_args[1]["messages"][0]["content"]
        assert "Help me reset my password" in call_content
        assert "[SAFE]" not in call_content


# --- Quality Scorer Tests ---


@pytest.mark.asyncio
class TestQualityScorerStep:
    async def test_high_quality_with_citations(self):
        """Well-structured response with citations scores high."""
        ctx = _make_context(
            response=(
                "Based on our documentation, here are the business hours:\n\n"
                "- **Monday-Friday**: 9 AM to 6 PM EST\n"
                "- **Saturday**: 10 AM to 2 PM EST\n"
                "- **Sunday**: Closed\n\n"
                "You can also reach us via email at support@example.com."
            ),
            citations=[{"doc_name": "FAQ.pdf", "page_number": 1}],
            rag_chunks=[{"text": "hours info", "score": 0.9}],
        )

        result = await QualityScorerStep().execute(ctx)

        assert result.quality_score is not None
        assert result.quality_score >= 0.6

    async def test_low_quality_short_response(self):
        """Very short response scores lower."""
        ctx = _make_context(response="Yes.")

        result = await QualityScorerStep().execute(ctx)

        assert result.quality_score is not None
        assert result.quality_score < 0.5

    async def test_medium_quality_no_citations(self):
        """Decent response without citations scores medium."""
        ctx = _make_context(
            response="Our business hours are Monday through Friday, 9 AM to 6 PM Eastern Standard Time.",
        )

        result = await QualityScorerStep().execute(ctx)

        assert result.quality_score is not None
        assert 0.2 <= result.quality_score <= 0.8

    async def test_skip_when_no_response(self):
        ctx = _make_context(response=None)

        result = await QualityScorerStep().execute(ctx)

        assert result.quality_score is None

    async def test_score_between_0_and_1(self):
        """Score is always in valid range."""
        ctx = _make_context(
            response="A" * 5000,  # very long response
            citations=[{"doc_name": "test.pdf"}],
        )

        result = await QualityScorerStep().execute(ctx)

        assert result.quality_score is not None
        assert 0.0 <= result.quality_score <= 1.0

    async def test_relevance_scoring(self):
        """Response containing query terms scores higher on relevance."""
        ctx = _make_context(
            message="What are the business hours for your office?",
            response="Our business hours are 9 AM to 5 PM. The office is open Monday through Friday.",
            metadata={"original_message": "What are the business hours for your office?"},
        )

        result = await QualityScorerStep().execute(ctx)

        assert result.quality_score is not None
        assert result.quality_score >= 0.3  # relevance boost from matching terms
