"""Unit tests for lead scoring pipeline step and auto-escalation rules."""

from uuid import uuid4

import pytest

from app.core.engine import MessageContext
from app.core.steps.lead_scoring import LeadScoringStep, calculate_lead_delta


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
    ctx.sentiment = defaults.get("sentiment")
    ctx.intent = defaults.get("intent")
    ctx.conversation_history = defaults.get("conversation_history", [])
    ctx.metadata = defaults.get("metadata", {})
    return ctx


# --- calculate_lead_delta unit tests ---


class TestCalculateLeadDelta:
    def test_pricing_keywords_add_10(self):
        assert calculate_lead_delta("How much does the enterprise plan cost?") >= 10

    def test_timeline_keywords_add_10(self):
        assert calculate_lead_delta("We need this by next week, very urgent") >= 10

    def test_contact_info_adds_20(self):
        assert calculate_lead_delta("My email is john@example.com") >= 20

    def test_phone_number_adds_20(self):
        assert calculate_lead_delta("Call me at 555-123-4567") >= 20

    def test_sales_intent_adds_15(self):
        delta = calculate_lead_delta("Tell me about pricing", intent="sales")
        # pricing (+10) + sales intent (+15) = 25
        assert delta >= 25

    def test_booking_intent_adds_15(self):
        delta = calculate_lead_delta("I want to book a demo", intent="booking")
        assert delta >= 15

    def test_negative_sentiment_subtracts_10(self):
        delta = calculate_lead_delta("hello", sentiment="negative")
        assert delta == -10

    def test_engagement_depth_adds_5(self):
        delta = calculate_lead_delta("hello", message_count=6)
        assert delta == 5

    def test_no_signals_returns_0(self):
        delta = calculate_lead_delta("hello")
        assert delta == 0

    def test_combined_signals(self):
        """Multiple signals should stack."""
        delta = calculate_lead_delta(
            "How much does this cost? We need it by next week. Reach me at john@example.com",
            intent="sales",
            message_count=6,
        )
        # pricing (+10) + timeline (+10) + contact (+20) + sales (+15) + depth (+5) = 60
        assert delta == 60


# --- LeadScoringStep pipeline tests ---


@pytest.mark.asyncio
class TestLeadScoringStep:
    async def test_scores_pricing_message(self):
        ctx = _make_context(
            message="How much does the enterprise plan cost?",
            metadata={"existing_lead_score": 0},
        )

        result = await LeadScoringStep().execute(ctx)

        assert result.lead_score is not None
        assert result.lead_score >= 10

    async def test_cumulative_scoring(self):
        """Score should add to existing lead_score."""
        ctx = _make_context(
            message="What is the pricing?",
            metadata={"existing_lead_score": 25},
        )

        result = await LeadScoringStep().execute(ctx)

        assert result.lead_score >= 35  # 25 existing + 10 pricing

    async def test_floor_at_zero(self):
        """Score should never go below 0."""
        ctx = _make_context(
            message="hello",
            sentiment="negative",
            metadata={"existing_lead_score": 5},
        )

        result = await LeadScoringStep().execute(ctx)

        assert result.lead_score >= 0

    async def test_no_message_skips(self):
        ctx = _make_context(message="")

        result = await LeadScoringStep().execute(ctx)

        assert result.lead_score is None

    async def test_uses_original_message(self):
        """Should use original_message from metadata if available."""
        ctx = _make_context(
            message="[SAFE] How much does it cost? [/SAFE]",
            metadata={
                "existing_lead_score": 0,
                "original_message": "How much does it cost?",
            },
        )

        result = await LeadScoringStep().execute(ctx)

        assert result.lead_score >= 10
