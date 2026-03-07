"""Conversation export service — CSV and text transcript formats."""

import csv
import io
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message

logger = structlog.get_logger(__name__)

CSV_COLUMNS = [
    "conversation_id",
    "channel",
    "contact_name",
    "status",
    "lead_score",
    "message_count",
    "started_at",
    "ended_at",
]


class ConversationExportService:
    """Export conversations to CSV or text transcript."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_csv(
        self,
        workspace_id: str,
        channel: str | None = None,
        status: str | None = None,
    ) -> bytes:
        """Export conversations as CSV bytes.

        Columns: conversation_id, channel, contact_name, status,
                 lead_score, message_count, started_at, ended_at
        """
        # Build query
        msg_count_subq = (
            select(func.count(Message.id))
            .where(Message.conversation_id == Conversation.id)
            .correlate(Conversation)
            .scalar_subquery()
        )

        query = select(
            Conversation.id,
            Conversation.channel,
            Conversation.contact_name,
            Conversation.status,
            Conversation.lead_score,
            msg_count_subq.label("message_count"),
            Conversation.started_at,
            Conversation.ended_at,
        ).where(Conversation.workspace_id == workspace_id)

        if channel:
            query = query.where(Conversation.channel == channel)
        if status:
            query = query.where(Conversation.status == status)

        query = query.order_by(Conversation.started_at.desc())

        result = await self.db.execute(query)
        rows = result.all()

        # Write CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    "conversation_id": str(row.id),
                    "channel": row.channel or "",
                    "contact_name": row.contact_name or "",
                    "status": row.status or "",
                    "lead_score": row.lead_score or 0,
                    "message_count": row.message_count or 0,
                    "started_at": row.started_at.isoformat() if row.started_at else "",
                    "ended_at": row.ended_at.isoformat() if row.ended_at else "",
                }
            )

        return output.getvalue().encode("utf-8")

    async def export_transcript(
        self,
        conversation_id: str,
        workspace_id: str,
    ) -> bytes:
        """Export a single conversation as a text transcript.

        Includes conversation metadata and full message thread with analytics.
        """
        # Fetch conversation
        conv_result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == workspace_id,
            )
        )
        conversation = conv_result.scalar_one_or_none()
        if not conversation:
            return b""

        # Fetch messages
        msg_result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        messages = msg_result.scalars().all()

        # Build transcript
        lines = [
            "=" * 60,
            "BotForge Conversation Transcript",
            "=" * 60,
            f"Conversation ID: {conversation.id}",
            f"Channel: {conversation.channel or 'N/A'}",
            f"Contact: {conversation.contact_name or 'Anonymous'}",
            f"Status: {conversation.status or 'N/A'}",
            f"Started: {conversation.started_at.isoformat() if conversation.started_at else 'N/A'}",
            f"Lead Score: {conversation.lead_score or 0}",
            "-" * 60,
            "",
        ]

        for msg in messages:
            role = (
                "User" if msg.role == "user" else ("Bot" if msg.role == "assistant" else "System")
            )
            timestamp = msg.created_at.strftime("%H:%M") if msg.created_at else "??:??"
            lines.append(f"[{timestamp}] {role}: {msg.content}")

            # Analytics metadata
            meta_parts = []
            if msg.sentiment:
                meta_parts.append(f"Sentiment: {msg.sentiment}")
            if msg.intent:
                meta_parts.append(f"Intent: {msg.intent}")
            if msg.quality_score is not None:
                meta_parts.append(f"Quality: {msg.quality_score:.2f}")
            if meta_parts:
                lines.append(f"           {' | '.join(meta_parts)}")
            lines.append("")

        lines.extend(
            [
                "-" * 60,
                f"Exported: {datetime.now(UTC).isoformat()}",
                f"Total messages: {len(messages)}",
            ]
        )

        return "\n".join(lines).encode("utf-8")
