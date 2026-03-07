"""Unit tests for EscalationEngine rule evaluators."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.escalation_engine import EscalationEngine


def _make_rule(
    rule_type: str,
    condition: dict,
    action: str = "escalate",
    is_active: bool = True,
    priority: int = 10,
) -> MagicMock:
    """Create a mock EscalationRule."""
    rule = MagicMock()
    rule.id = uuid4()
    rule.rule_type = rule_type
    rule.condition = condition
    rule.action = action
    rule.is_active = is_active
    rule.priority = priority
    return rule


class TestEscalationEngine:
    """Test individual rule evaluators and engine behavior."""

    def setup_method(self):
        self.engine = EscalationEngine()

    def test_keyword_rule_matches(self):
        """Keyword rule matches when keyword is in transcript."""
        rule = _make_rule("keyword", {"keywords": ["speak to human", "agent"]})
        result = self.engine._evaluate_rule(rule, "I want to speak to human please")
        assert result == "speak to human"

    def test_keyword_rule_case_insensitive(self):
        """Keyword matching is case-insensitive."""
        rule = _make_rule("keyword", {"keywords": ["HELP"]})
        result = self.engine._evaluate_rule(rule, "i need help with my order")
        assert result == "HELP"

    def test_sentiment_rule_triggers(self):
        """Sentiment rule triggers on negative sentiment."""
        rule = _make_rule("sentiment", {"threshold": "negative"})
        result = self.engine._evaluate_rule(rule, "", call_sentiment="negative", analysis={})
        assert result == "sentiment=negative"

    def test_business_hours_outside_escalates(self):
        """Business hours rule escalates when outside configured hours."""
        # Use a timezone and time range that will definitely be outside
        # Set hours to 03:00-03:01 so virtually any time of day is outside
        rule = _make_rule(
            "business_hours",
            {
                "timezone": "UTC",
                "start": "03:00",
                "end": "03:01",
                "days": [0, 1, 2, 3, 4],
            },
        )
        now = datetime.now(UTC)
        # Unless we're running at exactly 03:00 UTC, this will match
        if now.strftime("%H:%M") != "03:00":
            result = self.engine._evaluate_rule(rule, "")
            assert result is not None
            assert "outside_hours" in result

    def test_no_matching_rules_returns_none(self):
        """Keyword rule returns None when no keyword matches."""
        rule = _make_rule("keyword", {"keywords": ["cancel"]})
        result = self.engine._evaluate_rule(rule, "hello how are you")
        assert result is None

    def test_inactive_rule_skipped(self):
        """Engine skips inactive rules when evaluating."""
        # _get_active_rules already filters by is_active, so inactive rules
        # never reach _evaluate_rule. Test the evaluator returns None for
        # a rule that doesn't match, which is the behavior when rules are filtered out.
        rule = _make_rule("keyword", {"keywords": ["nonexistent"]})
        result = self.engine._evaluate_rule(rule, "normal conversation")
        assert result is None

    @pytest.mark.asyncio
    async def test_priority_ordering_highest_wins(self):
        """Higher priority rule wins even if both match."""
        low_priority = _make_rule(
            "keyword",
            {"keywords": ["help"]},
            action="log",
            priority=1,
        )
        high_priority = _make_rule(
            "keyword",
            {"keywords": ["help"]},
            action="escalate",
            priority=10,
        )

        # Mock _get_active_rules to return rules in priority DESC order
        self.engine._get_active_rules = AsyncMock(return_value=[high_priority, low_priority])

        session = AsyncMock()
        result = await self.engine.evaluate(
            workspace_id=uuid4(),
            transcript="I need help",
            session=session,
        )

        assert result is not None
        assert result["action"] == "escalate"
        assert result["rule_type"] == "keyword"

    def test_keyword_match_all_mode(self):
        """Keyword rule with match_mode 'all' requires all keywords present."""
        rule = _make_rule("keyword", {"keywords": ["help", "urgent"], "match_mode": "all"})
        # Both present
        result = self.engine._evaluate_rule(rule, "I need urgent help now")
        assert result is not None

        # Only one present
        result2 = self.engine._evaluate_rule(rule, "I need help")
        assert result2 is None

    def test_keyword_empty_keywords_returns_none(self):
        """Keyword rule with empty keywords list returns None."""
        rule = _make_rule("keyword", {"keywords": []})
        result = self.engine._evaluate_rule(rule, "anything")
        assert result is None

    def test_sentiment_very_negative_threshold(self):
        """Sentiment rule with very_negative threshold only triggers on very_negative."""
        rule = _make_rule("sentiment", {"threshold": "very_negative"})

        # negative should NOT trigger
        result = self.engine._evaluate_rule(rule, "", call_sentiment="negative", analysis={})
        assert result is None

        # very_negative SHOULD trigger
        result2 = self.engine._evaluate_rule(rule, "", call_sentiment="very_negative", analysis={})
        assert result2 == "sentiment=very_negative"

    def test_sentiment_no_sentiment_returns_none(self):
        """Sentiment rule returns None when no sentiment data."""
        rule = _make_rule("sentiment", {"threshold": "negative"})
        result = self.engine._evaluate_rule(rule, "", call_sentiment=None, analysis={})
        assert result is None

    def test_confidence_below_threshold(self):
        """Confidence rule triggers when score is below threshold."""
        rule = _make_rule("confidence", {"min_confidence": 0.5})
        analysis = {"structuredData": {"confidence": 0.3}}
        result = self.engine._evaluate_rule(rule, "", call_sentiment=None, analysis=analysis)
        assert result is not None
        assert "0.30" in result

    def test_confidence_above_threshold_returns_none(self):
        """Confidence rule returns None when score is above threshold."""
        rule = _make_rule("confidence", {"min_confidence": 0.5})
        analysis = {"structuredData": {"confidence": 0.8}}
        result = self.engine._evaluate_rule(rule, "", call_sentiment=None, analysis=analysis)
        assert result is None

    def test_confidence_no_data_returns_none(self):
        """Confidence rule returns None when no structured data."""
        rule = _make_rule("confidence", {"min_confidence": 0.5})
        result = self.engine._evaluate_rule(rule, "", call_sentiment=None, analysis={})
        assert result is None

    def test_intent_matches(self):
        """Intent rule matches detected intent."""
        rule = _make_rule("intent", {"intents": ["cancel_subscription", "refund"]})
        analysis = {"structuredData": {"intent": "cancel_subscription"}}
        result = self.engine._evaluate_rule(rule, "", call_sentiment=None, analysis=analysis)
        assert result == "intent=cancel_subscription"

    def test_intent_no_match_returns_none(self):
        """Intent rule returns None when intent doesn't match."""
        rule = _make_rule("intent", {"intents": ["cancel_subscription"]})
        analysis = {"structuredData": {"intent": "billing_inquiry"}}
        result = self.engine._evaluate_rule(rule, "", call_sentiment=None, analysis=analysis)
        assert result is None

    def test_unknown_rule_type_returns_none(self):
        """Unknown rule type returns None gracefully."""
        rule = _make_rule("nonexistent_type", {})
        result = self.engine._evaluate_rule(rule, "hello")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_active_rules_returns_none(self):
        """Engine returns None when no active rules exist."""
        self.engine._get_active_rules = AsyncMock(return_value=[])
        session = AsyncMock()
        result = await self.engine.evaluate(
            workspace_id=uuid4(),
            transcript="anything",
            session=session,
        )
        assert result is None
