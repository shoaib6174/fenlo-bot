"""Unit tests for InsightsGenerator — LLM insights, fallback, sanitization, validation."""

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.prompt_sanitizer import sanitize_list, sanitize_number
from app.services.insights_generator import InsightsGenerator


def _make_row(**kwargs):
    """Create a mock SQLAlchemy row with attribute access."""
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


def _mock_db_for_metrics(
    conv_count=10,
    prev_conv=8,
    msg_count=50,
    avg_latency=400.0,
    avg_quality=0.75,
    positive=20,
    neutral=15,
    negative=5,
    avg_lead=6.0,
    gap_contents=None,
    peak_hour=14,
):
    """Build an AsyncMock db session that returns canned analytics data."""
    db = AsyncMock()

    # scalar calls: conv_count, prev_conv, avg_lead
    db.scalar = AsyncMock(side_effect=[conv_count, prev_conv, avg_lead])

    msg_row = _make_row(
        msg_count=msg_count,
        avg_latency=avg_latency,
        avg_quality=avg_quality,
        positive=positive,
        neutral=neutral,
        negative=negative,
    )

    gap_contents = gap_contents or ["pricing plans", "refund policy", "API limits"]
    gap_rows = [_make_row(content=c) for c in gap_contents]

    peak_row = _make_row(hr=peak_hour, cnt=30)

    # Insight model operations
    insight_mock = MagicMock()
    insight_mock.id = "test-insight-id"
    insight_mock.period = "Week of Feb 10-16, 2026"
    insight_mock.status = "completed"

    # execute calls order: msg_q, gap_q, peak_q
    msg_result = MagicMock()
    msg_result.one.return_value = msg_row

    gap_result = MagicMock()
    gap_result.all.return_value = gap_rows

    peak_result = MagicMock()
    peak_result.first.return_value = peak_row

    db.execute = AsyncMock(side_effect=[msg_result, gap_result, peak_result])

    # commit / refresh / add are no-ops
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    return db


@pytest.mark.asyncio
class TestInsightsGenerator:
    """Test AI weekly insights generation."""

    async def test_generates_weekly_summary_with_llm(self):
        """LLM should be called and its response parsed into summary + recommendations."""
        gen = InsightsGenerator()
        db = _mock_db_for_metrics()

        llm_response = json.dumps(
            {
                "summary": "Great week with 10 conversations.",
                "recommendations": ["Add FAQ about pricing", "Enable escalation rules"],
            }
        )

        with patch("app.services.insights_generator.LLMRouter") as MockRouter:
            router_inst = MagicMock()
            router_inst.complete = AsyncMock(return_value={"content": llm_response})
            MockRouter.return_value = router_inst

            with patch("app.services.insights_generator.settings") as mock_settings:
                mock_settings.insights_validate_recommendations = False

                insight = await gen.generate_weekly_insights(
                    "ws-123", date(2026, 2, 10), date(2026, 2, 16), db
                )

        assert insight.summary == "Great week with 10 conversations."
        assert len(insight.recommendations) == 2
        assert "pricing" in insight.recommendations[0].lower()
        router_inst.complete.assert_awaited_once()

    async def test_template_fallback_on_llm_failure(self):
        """When LLM fails, should return a template-based summary."""
        gen = InsightsGenerator()
        db = _mock_db_for_metrics()

        with patch("app.services.insights_generator.LLMRouter") as MockRouter:
            router_inst = MagicMock()
            router_inst.complete = AsyncMock(side_effect=Exception("LLM timeout"))
            MockRouter.return_value = router_inst

            with patch("app.services.insights_generator.settings") as mock_settings:
                mock_settings.insights_validate_recommendations = False

                insight = await gen.generate_weekly_insights(
                    "ws-123", date(2026, 2, 10), date(2026, 2, 16), db
                )

        # Template fallback should still produce a summary
        assert "10 conversations" in insight.summary
        assert "50 messages" in insight.summary
        assert insight.status == "completed"

    async def test_handles_empty_data_gracefully(self):
        """No conversations/messages should produce a valid (empty) insight."""
        gen = InsightsGenerator()
        db = _mock_db_for_metrics(
            conv_count=0,
            prev_conv=0,
            msg_count=0,
            avg_latency=0,
            avg_quality=0,
            positive=0,
            neutral=0,
            negative=0,
            avg_lead=0,
            gap_contents=[],
        )

        # Override peak_q to return None (no data)
        msg_result = MagicMock()
        msg_result.one.return_value = _make_row(
            msg_count=0, avg_latency=0, avg_quality=0, positive=0, neutral=0, negative=0
        )
        gap_result = MagicMock()
        gap_result.all.return_value = []
        peak_result = MagicMock()
        peak_result.first.return_value = None
        db.execute = AsyncMock(side_effect=[msg_result, gap_result, peak_result])

        with patch("app.services.insights_generator.LLMRouter") as MockRouter:
            router_inst = MagicMock()
            router_inst.complete = AsyncMock(side_effect=Exception("no data"))
            MockRouter.return_value = router_inst

            with patch("app.services.insights_generator.settings") as mock_settings:
                mock_settings.insights_validate_recommendations = False

                insight = await gen.generate_weekly_insights(
                    "ws-123", date(2026, 2, 10), date(2026, 2, 16), db
                )

        assert insight.summary is not None
        assert "0 conversations" in insight.summary

    async def test_llm_response_with_markdown_code_block(self):
        """LLM sometimes wraps JSON in ```json ... ```, parser should handle it."""
        gen = InsightsGenerator()

        response = '```json\n{"summary": "Wrapped response", "recommendations": ["Do X"]}\n```'

        with patch("app.services.insights_generator.LLMRouter") as MockRouter:
            router_inst = MagicMock()
            router_inst.complete = AsyncMock(return_value={"content": response})
            MockRouter.return_value = router_inst

            summary, recs = await gen._generate_summary(
                {
                    "total_conversations": 5,
                    "change_pct": 10.0,
                    "total_messages": 20,
                    "avg_latency_ms": 300,
                    "positive_pct": 70,
                    "negative_pct": 10,
                    "top_gaps": ["pricing"],
                    "peak_hour": "14:00",
                    "avg_lead_score": 5.0,
                }
            )

        assert summary == "Wrapped response"
        assert recs == ["Do X"]

    async def test_recommendation_validation_filters_vague(self):
        """Validation should filter out vague recommendations."""
        gen = InsightsGenerator()

        recs = [
            "Improve your chatbot",  # vague — should be filtered
            "Add FAQ about pricing plans",  # good
            "Make things better",  # vague
        ]

        metrics = {
            "top_gaps": ["pricing", "refunds"],
            "positive_pct": 70,
            "negative_pct": 10,
            "avg_lead_score": 6.5,
        }

        # LLM returns "2" meaning only recommendation #2 passes
        with patch("app.services.insights_generator.LLMRouter") as MockRouter:
            router_inst = MagicMock()
            router_inst.complete = AsyncMock(return_value={"content": "2"})
            MockRouter.return_value = router_inst

            filtered = await gen._validate_recommendations(recs, metrics)

        assert len(filtered) == 1
        assert "pricing" in filtered[0].lower()

    async def test_validation_returns_all_on_failure(self):
        """If validation LLM call fails, return all recommendations."""
        gen = InsightsGenerator()

        recs = ["Add FAQ", "Enable feature"]
        metrics = {"top_gaps": [], "positive_pct": 0, "negative_pct": 0, "avg_lead_score": 0}

        with patch("app.services.insights_generator.LLMRouter") as MockRouter:
            router_inst = MagicMock()
            router_inst.complete = AsyncMock(side_effect=Exception("timeout"))
            MockRouter.return_value = router_inst

            filtered = await gen._validate_recommendations(recs, metrics)

        assert len(filtered) == 2
        assert filtered == recs


@pytest.mark.asyncio
class TestPromptSanitizer:
    """Test prompt sanitization helpers."""

    async def test_sanitize_list_truncates_and_escapes(self):
        """Should truncate items, replace quotes, limit count."""
        items = ['He said "hello"', "A" * 200, "normal", "extra1", "extra2", "extra3"]
        result = sanitize_list(items, max_items=3, max_length=50)

        assert '"He said' in result
        # Double quotes inside should be replaced with single
        assert '""' not in result
        # Only 3 items
        assert result.count('"') == 6  # 3 pairs of quotes

    async def test_sanitize_list_handles_empty(self):
        """Empty list should produce empty string."""
        assert sanitize_list([]) == ""
        assert sanitize_list(["", ""]) == ""

    async def test_sanitize_number_clamps(self):
        """Should return abs and clamp to max."""
        assert sanitize_number(-5) == 5
        assert sanitize_number(1e10) == 1e6
        assert sanitize_number(42, max_value=100) == 42
        assert sanitize_number(150, max_value=100) == 100
