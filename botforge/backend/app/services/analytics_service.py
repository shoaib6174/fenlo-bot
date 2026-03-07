"""
Analytics aggregation service with Redis caching.

Provides workspace-scoped analytics: overview metrics, volume trends,
sentiment distribution, channel breakdown, lead score buckets, and
top questions.  All queries join messages→conversations for workspace
isolation (messages table has no workspace_id column).
"""

from datetime import date, timedelta

import structlog
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.analytics_cache import DEFAULT_TTL_SEC, AnalyticsCacheManager
from app.models.conversation import Conversation, Message

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """Workspace-scoped analytics with Redis-cached aggregations."""

    def __init__(self, cache: AnalyticsCacheManager):
        self.cache = cache

    # ------------------------------------------------------------------
    # 1. Overview
    # ------------------------------------------------------------------

    async def get_overview(
        self,
        workspace_id: str,
        start_date: date,
        end_date: date,
        db: AsyncSession,
    ) -> dict:
        """
        High-level metrics for a workspace over a date range.
        Returns total conversations, messages, avg response time,
        sentiment distribution, and avg quality score.
        """
        cache_key = f"analytics:{workspace_id}:overview:{start_date}:{end_date}"

        async def compute():
            # Conversations in range
            conv_count = (
                await db.scalar(
                    select(func.count(Conversation.id)).where(
                        Conversation.workspace_id == workspace_id,
                        Conversation.started_at >= start_date,
                        Conversation.started_at < end_date + timedelta(days=1),
                    )
                )
                or 0
            )

            # Messages in range (join through conversations)
            base = (
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
                    Message.created_at >= start_date,
                    Message.created_at < end_date + timedelta(days=1),
                )
            )
            row = (await db.execute(base)).one()

            # Format response time: show null for 0ms (no data), otherwise round to 1 decimal
            avg_latency = round(float(row.avg_latency or 0), 1)
            response_time_display = avg_latency if avg_latency > 0 else None

            return {
                "total_conversations": conv_count,
                "total_messages": row.msg_count or 0,
                "avg_response_time_ms": response_time_display,
                "avg_quality_score": round(float(row.avg_quality or 0), 3),
                "sentiment_distribution": {
                    "positive": row.positive or 0,
                    "neutral": row.neutral or 0,
                    "negative": row.negative or 0,
                },
            }

        return await self.cache.get_or_compute(cache_key, compute, ttl=DEFAULT_TTL_SEC)

    # ------------------------------------------------------------------
    # 2. Volume (time series)
    # ------------------------------------------------------------------

    async def get_volume(
        self,
        workspace_id: str,
        start_date: date,
        end_date: date,
        period: str,  # "day" | "week" | "month"
        db: AsyncSession,
    ) -> list[dict]:
        """
        Message and conversation volume over time, grouped by period.
        """
        cache_key = f"analytics:{workspace_id}:volume:{period}:{start_date}:{end_date}"

        async def compute():
            # Truncate to period
            trunc_map = {"day": "day", "week": "week", "month": "month"}
            trunc = trunc_map.get(period, "day")

            # Message volume
            msg_q = (
                select(
                    func.date_trunc(trunc, Message.created_at).label("period"),
                    func.count(Message.id).label("message_count"),
                    func.count(func.distinct(Message.conversation_id)).label("conversation_count"),
                )
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(
                    Conversation.workspace_id == workspace_id,
                    Message.created_at >= start_date,
                    Message.created_at < end_date + timedelta(days=1),
                )
                .group_by("period")
                .order_by("period")
            )

            rows = (await db.execute(msg_q)).all()
            return [
                {
                    "date": row.period.isoformat() if row.period else None,
                    "message_count": row.message_count,
                    "conversation_count": row.conversation_count,
                }
                for row in rows
            ]

        return await self.cache.get_or_compute(cache_key, compute, ttl=DEFAULT_TTL_SEC)

    # ------------------------------------------------------------------
    # 3. Top questions
    # ------------------------------------------------------------------

    async def get_top_questions(
        self,
        workspace_id: str,
        limit: int,
        db: AsyncSession,
    ) -> list[dict]:
        """
        Most frequent user messages (approximated by first message in
        each conversation, grouped by similarity — here simplified to
        exact match for MVP).
        """
        cache_key = f"analytics:{workspace_id}:top_questions:{limit}"

        async def compute():
            # Get first user message of each conversation
            first_msg = (
                select(
                    Message.content,
                    func.count().label("count"),
                )
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(
                    Conversation.workspace_id == workspace_id,
                    Message.role == "user",
                )
                .group_by(Message.content)
                .order_by(func.count().desc())
                .limit(limit)
            )

            rows = (await db.execute(first_msg)).all()
            return [
                {
                    "question": row.content[:200] if row.content else "",
                    "count": row.count,
                }
                for row in rows
            ]

        return await self.cache.get_or_compute(cache_key, compute, ttl=DEFAULT_TTL_SEC)

    # ------------------------------------------------------------------
    # 4. Sentiment breakdown
    # ------------------------------------------------------------------

    async def get_sentiment(
        self,
        workspace_id: str,
        start_date: date,
        end_date: date,
        period: str,
        db: AsyncSession,
    ) -> list[dict]:
        """Sentiment counts over time, grouped by period."""
        cache_key = f"analytics:{workspace_id}:sentiment:{period}:{start_date}:{end_date}"

        async def compute():
            trunc_map = {"day": "day", "week": "week", "month": "month"}
            trunc = trunc_map.get(period, "day")

            q = (
                select(
                    func.date_trunc(trunc, Message.created_at).label("period"),
                    func.count(case((Message.sentiment == "positive", 1))).label("positive"),
                    func.count(case((Message.sentiment == "neutral", 1))).label("neutral"),
                    func.count(case((Message.sentiment == "negative", 1))).label("negative"),
                )
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(
                    Conversation.workspace_id == workspace_id,
                    Message.created_at >= start_date,
                    Message.created_at < end_date + timedelta(days=1),
                )
                .group_by("period")
                .order_by("period")
            )

            rows = (await db.execute(q)).all()
            return [
                {
                    "date": row.period.isoformat() if row.period else None,
                    "positive": row.positive or 0,
                    "neutral": row.neutral or 0,
                    "negative": row.negative or 0,
                }
                for row in rows
            ]

        return await self.cache.get_or_compute(cache_key, compute, ttl=DEFAULT_TTL_SEC)

    # ------------------------------------------------------------------
    # 5. Channel breakdown
    # ------------------------------------------------------------------

    async def get_channels(
        self,
        workspace_id: str,
        db: AsyncSession,
    ) -> dict:
        """Per-channel conversation count and average quality score."""
        cache_key = f"analytics:{workspace_id}:channels"

        async def compute():
            # Channel counts from conversations
            q = (
                select(
                    Conversation.channel,
                    func.count(Conversation.id).label("count"),
                )
                .where(Conversation.workspace_id == workspace_id)
                .group_by(Conversation.channel)
            )
            rows = (await db.execute(q)).all()

            # Avg quality per channel (join messages)
            quality_q = (
                select(
                    Conversation.channel,
                    func.avg(Message.quality_score).label("avg_quality"),
                )
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(
                    Conversation.workspace_id == workspace_id,
                    Message.quality_score.isnot(None),
                )
                .group_by(Conversation.channel)
            )
            quality_rows = (await db.execute(quality_q)).all()
            quality_map = {r.channel: float(r.avg_quality or 0) for r in quality_rows}

            result = {}
            for row in rows:
                channel = row.channel or "unknown"
                # Return null for channels with no quality data (e.g., voice uses Vapi metrics)
                avg_quality = quality_map.get(channel)
                if avg_quality is not None:
                    avg_quality = round(avg_quality, 3)

                result[channel] = {
                    "count": row.count,
                    "avg_quality": avg_quality,
                }
            return result

        return await self.cache.get_or_compute(cache_key, compute, ttl=DEFAULT_TTL_SEC)

    # ------------------------------------------------------------------
    # 6. Lead score distribution
    # ------------------------------------------------------------------

    async def get_lead_scores(
        self,
        workspace_id: str,
        db: AsyncSession,
    ) -> dict:
        """Lead score distribution in buckets: 0-3, 4-6, 7-10."""
        cache_key = f"analytics:{workspace_id}:lead_scores"

        async def compute():
            q = select(
                func.count(case((Conversation.lead_score.between(0, 3), 1))).label("low"),
                func.count(case((Conversation.lead_score.between(4, 6), 1))).label("medium"),
                func.count(case((Conversation.lead_score >= 7, 1))).label("high"),
            ).where(Conversation.workspace_id == workspace_id)
            row = (await db.execute(q)).one()
            return {
                "buckets": {
                    "0-3": row.low or 0,
                    "4-6": row.medium or 0,
                    "7-10": row.high or 0,
                }
            }

        return await self.cache.get_or_compute(cache_key, compute, ttl=DEFAULT_TTL_SEC)
