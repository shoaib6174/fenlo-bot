"""GDPR-compliant data lifecycle service — export, purge, archive, storage."""

import io
import json
import time
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.purge_dead_letter_queue import PurgeDeadLetterQueue
from app.models.channel import ChannelConfig
from app.models.conversation import Conversation, Message
from app.models.knowledge_base import Document, KnowledgeBase
from app.models.purge_operation import PurgeOperation
from app.services.immutable_audit_logger import ImmutableAuditLogger

logger = structlog.get_logger(__name__)


class PurgeFailedError(Exception):
    """Raised when a purge operation fails."""


@dataclass
class PurgeReport:
    """Result of a purge operation."""

    deleted_records: dict[str, int] = field(default_factory=dict)
    duration_ms: float = 0.0
    success: bool = False


@dataclass
class StorageReport:
    """Workspace storage usage report."""

    conversations_count: int = 0
    messages_count: int = 0
    documents_count: int = 0
    channels_count: int = 0
    knowledge_bases_count: int = 0


class DataLifecycleService:
    """GDPR-compliant data lifecycle management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_logger = ImmutableAuditLogger()
        self.dlq = PurgeDeadLetterQueue()

    async def export_workspace_data(self, workspace_id: str, requester_user_id: str) -> bytes:
        """Export all workspace data as JSON ZIP (GDPR Art. 20).

        Returns ZIP file bytes containing structured JSON files.
        """
        await self.audit_logger.log_export_attempt(workspace_id, requester_user_id, "started")

        try:
            # Gather all workspace data
            conversations = await self._export_conversations(workspace_id)
            messages = await self._export_messages(workspace_id)
            documents = await self._export_documents(workspace_id)
            channels = await self._export_channels(workspace_id)
            knowledge_bases = await self._export_knowledge_bases(workspace_id)

            # Build ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                metadata = {
                    "schema_version": "1.0.0",
                    "workspace_id": workspace_id,
                    "exported_at": datetime.now(UTC).isoformat(),
                    "record_counts": {
                        "conversations": len(conversations),
                        "messages": len(messages),
                        "documents": len(documents),
                        "channels": len(channels),
                        "knowledge_bases": len(knowledge_bases),
                    },
                }
                zf.writestr("metadata.json", json.dumps(metadata, indent=2, default=str))
                zf.writestr("conversations.json", json.dumps(conversations, indent=2, default=str))
                zf.writestr("messages.json", json.dumps(messages, indent=2, default=str))
                zf.writestr("documents.json", json.dumps(documents, indent=2, default=str))
                zf.writestr("channels.json", json.dumps(channels, indent=2, default=str))
                zf.writestr(
                    "knowledge_bases.json", json.dumps(knowledge_bases, indent=2, default=str)
                )

            await self.audit_logger.log_export_attempt(
                workspace_id,
                requester_user_id,
                "success",
                {"record_counts": metadata["record_counts"]},
            )

            return zip_buffer.getvalue()

        except Exception as e:
            await self.audit_logger.log_export_attempt(
                workspace_id, requester_user_id, "failed", {"error": str(e)}
            )
            raise

    async def purge_workspace(self, workspace_id: str, requester_user_id: str) -> PurgeReport:
        """Delete all workspace data (GDPR Art. 17 — Right to erasure).

        Uses a saga pattern: each phase is tracked in purge_operations for
        crash recovery. Deletes in dependency order to respect FK constraints.
        """
        start_time = time.time()

        # Create saga record
        purge_op = PurgeOperation(
            workspace_id=workspace_id,
            requester_user_id=requester_user_id,
            phase="initiated",
        )
        self.db.add(purge_op)
        await self.db.flush()
        purge_op_id = purge_op.id

        await self.audit_logger.log_purge_attempt(
            workspace_id,
            requester_user_id,
            "INITIATED",
            "started",
            {"purge_op_id": str(purge_op_id)},
        )

        # Phase 1: Health check
        await self._update_phase(purge_op_id, "health_check")

        # Phase 2: Delete from external systems (Redis cache)
        await self._update_phase(purge_op_id, "external_delete")
        try:
            await self._purge_redis_cache(workspace_id)
        except Exception as e:
            logger.warning("purge.redis_cleanup_failed", error=str(e))
            # Non-fatal — Redis data is ephemeral

        # Phase 3: Delete from database (order matters for FK constraints)
        await self._update_phase(purge_op_id, "db_delete")
        deleted_counts: dict[str, int] = {}

        try:
            # Messages first (FK → conversations)
            result = await self.db.execute(
                delete(Message).where(
                    Message.conversation_id.in_(
                        select(Conversation.id).where(Conversation.workspace_id == workspace_id)
                    )
                )
            )
            deleted_counts["messages"] = result.rowcount

            # Conversations
            result = await self.db.execute(
                delete(Conversation).where(Conversation.workspace_id == workspace_id)
            )
            deleted_counts["conversations"] = result.rowcount

            # Documents (FK → knowledge_bases)
            result = await self.db.execute(
                delete(Document).where(
                    Document.kb_id.in_(
                        select(KnowledgeBase.id).where(KnowledgeBase.workspace_id == workspace_id)
                    )
                )
            )
            deleted_counts["documents"] = result.rowcount

            # Knowledge bases
            result = await self.db.execute(
                delete(KnowledgeBase).where(KnowledgeBase.workspace_id == workspace_id)
            )
            deleted_counts["knowledge_bases"] = result.rowcount

            # Channel configs
            result = await self.db.execute(
                delete(ChannelConfig).where(ChannelConfig.workspace_id == workspace_id)
            )
            deleted_counts["channels"] = result.rowcount

        except Exception as e:
            await self._update_phase(purge_op_id, "failed", {"error": str(e)})
            await self.audit_logger.log_purge_attempt(
                workspace_id,
                requester_user_id,
                "DB_DELETE",
                "failed",
                {"error": str(e)},
            )
            await self.dlq.add(
                workspace_id,
                {
                    "error": str(e),
                    "purge_op_id": str(purge_op_id),
                },
            )
            raise PurgeFailedError(f"Database purge failed: {e}") from e

        # Phase 4: Complete
        duration_ms = (time.time() - start_time) * 1000
        await self._update_phase(
            purge_op_id,
            "complete",
            {
                "deleted_counts": deleted_counts,
                "duration_ms": duration_ms,
            },
        )

        await self.audit_logger.log_purge_attempt(
            workspace_id,
            requester_user_id,
            "COMPLETE",
            "success",
            {"deleted_counts": deleted_counts, "duration_ms": duration_ms},
        )

        return PurgeReport(
            deleted_records=deleted_counts,
            duration_ms=duration_ms,
            success=True,
        )

    async def archive_old_conversations(self, workspace_id: str, before: datetime) -> int:
        """Archive conversations older than cutoff (soft close)."""
        result = await self.db.execute(
            update(Conversation)
            .where(
                Conversation.workspace_id == workspace_id,
                Conversation.started_at < before,
                Conversation.status == "active",
            )
            .values(status="closed", ended_at=func.now())
        )
        archived = result.rowcount

        await self.audit_logger.log_archive_attempt(workspace_id, archived, before.isoformat())

        return archived

    async def check_storage_usage(self, workspace_id: str) -> StorageReport:
        """Report storage usage for a workspace."""
        conversations_count = (
            await self.db.scalar(
                select(func.count(Conversation.id)).where(Conversation.workspace_id == workspace_id)
            )
        ) or 0

        messages_count = (
            await self.db.scalar(
                select(func.count(Message.id)).where(
                    Message.conversation_id.in_(
                        select(Conversation.id).where(Conversation.workspace_id == workspace_id)
                    )
                )
            )
        ) or 0

        documents_count = (
            await self.db.scalar(
                select(func.count(Document.id)).where(
                    Document.kb_id.in_(
                        select(KnowledgeBase.id).where(KnowledgeBase.workspace_id == workspace_id)
                    )
                )
            )
        ) or 0

        channels_count = (
            await self.db.scalar(
                select(func.count(ChannelConfig.id)).where(
                    ChannelConfig.workspace_id == workspace_id
                )
            )
        ) or 0

        kb_count = (
            await self.db.scalar(
                select(func.count(KnowledgeBase.id)).where(
                    KnowledgeBase.workspace_id == workspace_id
                )
            )
        ) or 0

        return StorageReport(
            conversations_count=conversations_count,
            messages_count=messages_count,
            documents_count=documents_count,
            channels_count=channels_count,
            knowledge_bases_count=kb_count,
        )

    # --- Private helpers ---

    async def _update_phase(self, purge_op_id, phase: str, details: dict | None = None) -> None:
        """Update purge operation saga state."""
        values: dict = {"phase": phase, "updated_at": func.now()}
        if details:
            values["details"] = details
        if phase in ("complete", "failed", "rolled_back"):
            values["completed_at"] = func.now()

        await self.db.execute(
            update(PurgeOperation).where(PurgeOperation.id == purge_op_id).values(**values)
        )

    async def _purge_redis_cache(self, workspace_id: str) -> None:
        """Delete workspace-scoped Redis keys using SCAN (non-blocking)."""
        from app.core.redis import get_redis_client

        redis = get_redis_client()
        if not redis:
            return

        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=f"*:{workspace_id}:*", count=100)
            if keys:
                await redis.delete(*keys)
            if cursor == 0:
                break

    async def _export_conversations(self, workspace_id: str) -> list[dict]:
        result = await self.db.execute(
            select(Conversation).where(Conversation.workspace_id == workspace_id)
        )
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "channel": r.channel,
                "contact_name": r.contact_name,
                "contact_info": r.contact_info,
                "status": r.status,
                "lead_score": r.lead_score,
                "started_at": str(r.started_at) if r.started_at else None,
                "ended_at": str(r.ended_at) if r.ended_at else None,
            }
            for r in rows
        ]

    async def _export_messages(self, workspace_id: str) -> list[dict]:
        result = await self.db.execute(
            select(Message).where(
                Message.conversation_id.in_(
                    select(Conversation.id).where(Conversation.workspace_id == workspace_id)
                )
            )
        )
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "conversation_id": str(r.conversation_id),
                "role": r.role,
                "content": r.content,
                "sentiment": r.sentiment,
                "intent": r.intent,
                "quality_score": r.quality_score,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in rows
        ]

    async def _export_documents(self, workspace_id: str) -> list[dict]:
        result = await self.db.execute(
            select(Document).where(
                Document.kb_id.in_(
                    select(KnowledgeBase.id).where(KnowledgeBase.workspace_id == workspace_id)
                )
            )
        )
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "kb_id": str(r.kb_id),
                "filename": r.filename,
                "file_type": r.file_type,
                "file_size": r.file_size,
                "status": r.status,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in rows
        ]

    async def _export_channels(self, workspace_id: str) -> list[dict]:
        result = await self.db.execute(
            select(ChannelConfig).where(ChannelConfig.workspace_id == workspace_id)
        )
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "channel": r.channel,
                "is_active": r.is_active,
                "created_at": str(r.created_at) if r.created_at else None,
                # Exclude config JSONB — may contain API keys/secrets
            }
            for r in rows
        ]

    async def _export_knowledge_bases(self, workspace_id: str) -> list[dict]:
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.workspace_id == workspace_id)
        )
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "doc_count": r.doc_count,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in rows
        ]
