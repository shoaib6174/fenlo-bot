"""
AI-powered weekly insights generator.

Queries analytics data for a workspace, formats an LLM prompt,
and generates a human-readable summary with actionable recommendations.
Falls back to a template-based summary when the LLM is unavailable.
"""

from datetime import date, timedelta

import structlog
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.llm_router import LLMRouter
from app.core.prompt_sanitizer import sanitize_list, sanitize_number
from app.models.conversation import Conversation, Message
from app.models.insights import WeeklyInsight

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

INSIGHTS_PROMPT = """\
You are an analytics assistant. Summarize this week's chatbot performance data concisely.

Data:
- Conversations: {total_conversations} ({change_pct:+.1f}% vs last week)
- Messages: {total_messages}
- Avg response time: {avg_latency_ms}ms
- Sentiment: {positive_pct:.0f}% positive, {negative_pct:.0f}% negative
- Top unanswered questions: {top_gaps}
- Busiest hour: {peak_hour}
- Lead score avg: {avg_lead_score:.1f}/10

Generate a 2-3 sentence summary and 2 actionable recommendations.

Respond in exactly this JSON format:
{{"summary": "...", "recommendations": ["...", "..."]}}
"""

VALIDATION_PROMPT = """\
You are a quality control assistant. Review these recommendations for a chatbot analytics dashboard:

Recommendations:
{numbered_recs}

Context:
- Top unanswered questions: {top_gaps}
- Sentiment: {positive_pct:.1f}% positive, {negative_pct:.1f}% negative
- Average lead score: {avg_lead_score:.1f}/10

For each recommendation, check:
1. Is it actionable (can be completed in <15 minutes)?
2. Does it address a real problem in the data?
3. Is it specific (references concrete features/documents)?

Return ONLY the recommendation numbers that pass ALL three criteria, comma-separated.
Example: "1,3"
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class InsightsGenerator:
    """Generate AI-powered weekly insights from analytics data."""

    async def generate_weekly_insights(
        self,
        workspace_id: str,
        week_start: date,
        week_end: date,
        db: AsyncSession,
    ) -> WeeklyInsight:
        """Query analytics, generate LLM summary, persist and return insight."""
        logger.info(
            "insights.generating",
            workspace_id=workspace_id,
            week_start=str(week_start),
            week_end=str(week_end),
        )

        # 1. Gather metrics ---------------------------------------------------
        metrics = await self._gather_metrics(workspace_id, week_start, week_end, db)

        # 2. Generate summary via LLM (or template fallback) -------------------
        summary, recommendations = await self._generate_summary(metrics)

        # 3. Optional recommendation validation --------------------------------
        if settings.insights_validate_recommendations and recommendations:
            recommendations = await self._validate_recommendations(recommendations, metrics)

        # 4. Persist -----------------------------------------------------------
        period_label = f"Week of {week_start:%b %d}-{week_end:%d, %Y}"
        insight = WeeklyInsight(
            workspace_id=workspace_id,
            week_start=week_start,
            week_end=week_end,
            period=period_label,
            summary=summary,
            metrics=metrics,
            recommendations=recommendations,
            status="completed",
        )
        db.add(insight)
        await db.commit()
        await db.refresh(insight)

        logger.info("insights.completed", insight_id=str(insight.id))
        return insight

    # ------------------------------------------------------------------
    # Data gathering
    # ------------------------------------------------------------------

    async def _gather_metrics(
        self,
        workspace_id: str,
        week_start: date,
        week_end: date,
        db: AsyncSession,
    ) -> dict:
        """Collect all analytics data needed for the insight prompt."""
        ws_end = week_end + timedelta(days=1)
        prev_start = week_start - timedelta(days=7)

        # Current week conversations
        conv_count = (
            await db.scalar(
                select(func.count(Conversation.id)).where(
                    Conversation.workspace_id == workspace_id,
                    Conversation.started_at >= week_start,
                    Conversation.started_at < ws_end,
                )
            )
        ) or 0

        # Previous week conversations (for week-over-week change)
        prev_conv = (
            await db.scalar(
                select(func.count(Conversation.id)).where(
                    Conversation.workspace_id == workspace_id,
                    Conversation.started_at >= prev_start,
                    Conversation.started_at < week_start,
                )
            )
        ) or 0

        change_pct = ((conv_count - prev_conv) / prev_conv * 100) if prev_conv else 0.0

        # Message-level aggregation
        msg_q = (
            select(
                func.count(Message.id).label("msg_count"),
                func.avg(Message.latency_ms).label("avg_latency"),
                func.avg(Message.quality_score).label("avg_quality"),
                func.count(case((Message.sentiment == "positive", 1))).label("positive"),
                func.count(case((Message.sentiment == "neutral", 1))).label("neutral"),
                func.count(case((Message.sentiment == "negative", 1))).label("negative"),
            )
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.workspace_id == workspace_id,
                Message.created_at >= week_start,
                Message.created_at < ws_end,
            )
        )
        row = (await db.execute(msg_q)).one()
        total_msgs = row.msg_count or 0

        total_sentiment = (row.positive or 0) + (row.neutral or 0) + (row.negative or 0)
        positive_pct = ((row.positive or 0) / total_sentiment * 100) if total_sentiment else 0.0
        negative_pct = ((row.negative or 0) / total_sentiment * 100) if total_sentiment else 0.0

        # Lead score average
        avg_lead = (
            await db.scalar(
                select(func.avg(Conversation.lead_score)).where(
                    Conversation.workspace_id == workspace_id,
                    Conversation.started_at >= week_start,
                    Conversation.started_at < ws_end,
                    Conversation.lead_score.isnot(None),
                )
            )
        ) or 0.0

        # Top unanswered: most common user messages without good quality response
        gap_q = (
            select(Message.content)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.workspace_id == workspace_id,
                Message.role == "user",
                Message.created_at >= week_start,
                Message.created_at < ws_end,
            )
            .group_by(Message.content)
            .order_by(func.count().desc())
            .limit(5)
        )
        gap_rows = (await db.execute(gap_q)).all()
        top_gaps = [r.content[:100] for r in gap_rows if r.content]

        # Peak hour (busiest by message count)
        peak_q = (
            select(
                func.extract("hour", Message.created_at).label("hr"),
                func.count(Message.id).label("cnt"),
            )
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.workspace_id == workspace_id,
                Message.created_at >= week_start,
                Message.created_at < ws_end,
            )
            .group_by("hr")
            .order_by(func.count(Message.id).desc())
            .limit(1)
        )
        peak_row = (await db.execute(peak_q)).first()
        peak_hour = f"{int(peak_row.hr)}:00" if peak_row else "N/A"

        return {
            "total_conversations": conv_count,
            "change_pct": change_pct,
            "total_messages": total_msgs,
            "avg_latency_ms": round(float(row.avg_latency or 0), 1),
            "avg_quality": round(float(row.avg_quality or 0), 3),
            "positive_pct": positive_pct,
            "negative_pct": negative_pct,
            "avg_lead_score": float(avg_lead),
            "top_gaps": top_gaps,
            "peak_hour": peak_hour,
        }

    # ------------------------------------------------------------------
    # LLM summary generation
    # ------------------------------------------------------------------

    async def _generate_summary(self, metrics: dict) -> tuple[str, list[str]]:
        """Call LLM to generate summary + recommendations. Falls back to template."""
        prompt = INSIGHTS_PROMPT.format(
            total_conversations=sanitize_number(metrics["total_conversations"]),
            change_pct=sanitize_number(metrics["change_pct"], max_value=1000),
            total_messages=sanitize_number(metrics["total_messages"]),
            avg_latency_ms=sanitize_number(metrics["avg_latency_ms"], max_value=60000),
            positive_pct=sanitize_number(metrics["positive_pct"], max_value=100),
            negative_pct=sanitize_number(metrics["negative_pct"], max_value=100),
            top_gaps=sanitize_list(metrics["top_gaps"], max_items=3, max_length=100),
            peak_hour=metrics["peak_hour"][:20],
            avg_lead_score=min(metrics["avg_lead_score"], 10.0),
        )

        try:
            router = LLMRouter()
            result = await router.complete(
                [{"role": "user", "content": prompt}],
                stream=False,
            )
            content = result.get("content", "") if isinstance(result, dict) else ""
            return self._parse_llm_response(content, metrics)
        except Exception as e:
            logger.warning("insights.llm_failed", error=str(e))
            return self._template_fallback(metrics)

    def _parse_llm_response(self, content: str, metrics: dict) -> tuple[str, list[str]]:
        """Extract summary and recommendations from LLM JSON response."""
        import json

        try:
            # Try to extract JSON from the response
            # Handle cases where LLM wraps JSON in markdown code blocks
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0].strip()
            if text.startswith("json"):
                text = text[4:].strip()

            data = json.loads(text)
            summary = data.get("summary", "")
            recommendations = data.get("recommendations", [])
            if isinstance(recommendations, list):
                recommendations = [str(r) for r in recommendations[:5]]
            else:
                recommendations = []
            if summary:
                return summary, recommendations
        except (json.JSONDecodeError, ValueError):
            logger.warning("insights.json_parse_failed", content=content[:200])

        # If parsing fails, use the raw content as summary
        if content.strip():
            return content.strip()[:500], []
        return self._template_fallback(metrics)

    def _template_fallback(self, metrics: dict) -> tuple[str, list[str]]:
        """Template-based insight when LLM is unavailable."""
        conv = int(metrics["total_conversations"])
        msgs = int(metrics["total_messages"])
        change = metrics["change_pct"]
        pos = metrics["positive_pct"]
        peak = metrics["peak_hour"]

        direction = "up" if change > 0 else "down" if change < 0 else "flat"
        summary = (
            f"{conv} conversations ({msgs} messages) this week, "
            f"{direction} {abs(change):.0f}% vs last week. "
            f"Sentiment is {pos:.0f}% positive. Busiest hour: {peak}."
        )

        recommendations = []
        if metrics["top_gaps"]:
            recommendations.append(f"Add FAQ content for: {metrics['top_gaps'][0]}")
        if metrics["negative_pct"] > 20:
            recommendations.append("Review negative sentiment conversations for common pain points")

        return summary, recommendations

    # ------------------------------------------------------------------
    # Recommendation validation
    # ------------------------------------------------------------------

    async def _validate_recommendations(
        self, recommendations: list[str], metrics: dict
    ) -> list[str]:
        """LLM self-critique: filter out vague/irrelevant recommendations."""
        numbered = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(recommendations))
        prompt = VALIDATION_PROMPT.format(
            numbered_recs=numbered,
            top_gaps=sanitize_list(metrics.get("top_gaps", []), max_items=3),
            positive_pct=sanitize_number(metrics.get("positive_pct", 0), max_value=100),
            negative_pct=sanitize_number(metrics.get("negative_pct", 0), max_value=100),
            avg_lead_score=min(metrics.get("avg_lead_score", 0), 10.0),
        )

        try:
            router = LLMRouter()
            result = await router.complete(
                [{"role": "user", "content": prompt}],
                stream=False,
            )
            content = result.get("content", "") if isinstance(result, dict) else ""
            valid_indices = [
                int(i.strip()) - 1 for i in content.strip().split(",") if i.strip().isdigit()
            ]
            filtered = [recommendations[i] for i in valid_indices if 0 <= i < len(recommendations)]

            logger.info(
                "insights.validation",
                original=len(recommendations),
                filtered=len(filtered),
            )
            return filtered if filtered else recommendations
        except Exception as e:
            logger.warning("insights.validation_failed", error=str(e))
            return recommendations


# ---------------------------------------------------------------------------
# Convenience singleton
# ---------------------------------------------------------------------------

_instance: InsightsGenerator | None = None


def get_insights_generator() -> InsightsGenerator:
    """Return a module-level InsightsGenerator singleton."""
    global _instance  # noqa: PLW0603
    if _instance is None:
        _instance = InsightsGenerator()
    return _instance
