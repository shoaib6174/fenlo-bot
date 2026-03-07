"""Unit tests for GDPR data lifecycle service, audit logger, and DLQ."""

import json
import zipfile
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.purge_dead_letter_queue import PurgeDeadLetterQueue
from app.models.purge_operation import PURGE_PHASES, PurgeOperation
from app.services.data_lifecycle import (
    DataLifecycleService,
    PurgeReport,
    StorageReport,
)
from app.services.immutable_audit_logger import ImmutableAuditLogger

# ---------------------------------------------------------------------------
# Audit Logger Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestImmutableAuditLogger:
    """Test structured audit logging."""

    async def test_log_purge_attempt_logs_event(self):
        """Purge audit should log with correct schema."""
        logger = ImmutableAuditLogger()
        # Should not raise — logs to structured logger
        await logger.log_purge_attempt(
            workspace_id="ws-1",
            requester_user_id="user-1",
            phase="INITIATED",
            status="started",
            details={"test": True},
        )

    async def test_log_export_attempt_logs_event(self):
        """Export audit should log with correct schema."""
        logger = ImmutableAuditLogger()
        await logger.log_export_attempt(
            workspace_id="ws-1",
            requester_user_id="user-1",
            status="started",
        )

    async def test_log_archive_attempt_logs_event(self):
        """Archive audit should log with correct schema."""
        logger = ImmutableAuditLogger()
        await logger.log_archive_attempt(
            workspace_id="ws-1",
            archived_count=42,
            before_date="2026-01-01",
        )


# ---------------------------------------------------------------------------
# Dead Letter Queue Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPurgeDeadLetterQueue:
    """Test Redis-backed dead letter queue."""

    async def test_add_without_redis_logs_error(self):
        """Without Redis, add should log error but not crash."""
        dlq = PurgeDeadLetterQueue()
        dlq.redis = None
        # Should not raise
        await dlq.add("ws-1", {"error": "test"})

    async def test_get_all_without_redis_returns_empty(self):
        """Without Redis, get_all returns empty list."""
        dlq = PurgeDeadLetterQueue()
        dlq.redis = None
        result = await dlq.get_all()
        assert result == []

    async def test_add_with_redis_stores_entry(self):
        """With Redis, entry should be stored in list."""
        redis = AsyncMock()
        dlq = PurgeDeadLetterQueue()
        dlq.redis = redis

        await dlq.add("ws-1", {"error": "test failure"})

        redis.lpush.assert_awaited_once()
        call_args = redis.lpush.call_args
        stored = json.loads(call_args[0][1])
        assert stored["workspace_id"] == "ws-1"
        assert stored["requires_manual_intervention"] is True
        redis.expire.assert_awaited_once()

    async def test_get_all_with_redis_returns_entries(self):
        """get_all should parse stored JSON entries."""
        redis = AsyncMock()
        entry = json.dumps({"workspace_id": "ws-1", "error": "test"})
        redis.lrange = AsyncMock(return_value=[entry])

        dlq = PurgeDeadLetterQueue()
        dlq.redis = redis

        result = await dlq.get_all()
        assert len(result) == 1
        assert result[0]["workspace_id"] == "ws-1"


# ---------------------------------------------------------------------------
# PurgeOperation Model Tests
# ---------------------------------------------------------------------------


class TestPurgeOperationModel:
    """Test purge operation model constraints."""

    def test_purge_phases_defined(self):
        """Should have all lifecycle phases."""
        assert "initiated" in PURGE_PHASES
        assert "complete" in PURGE_PHASES
        assert "failed" in PURGE_PHASES
        assert "rolled_back" in PURGE_PHASES
        assert len(PURGE_PHASES) == 7

    def test_model_table_name(self):
        assert PurgeOperation.__tablename__ == "purge_operations"


# ---------------------------------------------------------------------------
# DataLifecycleService Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDataLifecycleService:
    """Test data lifecycle service logic (mocked DB)."""

    async def test_storage_report_dataclass(self):
        """StorageReport should have all expected fields."""
        report = StorageReport(
            conversations_count=10,
            messages_count=50,
            documents_count=5,
            channels_count=2,
            knowledge_bases_count=1,
        )
        assert report.conversations_count == 10
        assert report.messages_count == 50
        assert report.documents_count == 5

    async def test_purge_report_defaults(self):
        """PurgeReport defaults should be empty/false."""
        report = PurgeReport()
        assert report.deleted_records == {}
        assert report.duration_ms == 0.0
        assert report.success is False

    async def test_purge_report_with_data(self):
        """PurgeReport should store delete counts."""
        report = PurgeReport(
            deleted_records={"messages": 100, "conversations": 10},
            duration_ms=1234.5,
            success=True,
        )
        assert report.deleted_records["messages"] == 100
        assert report.success is True

    async def test_export_produces_valid_zip(self):
        """export_workspace_data should produce a valid ZIP with expected files."""
        db = AsyncMock()

        # Mock all query results to return empty
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        service = DataLifecycleService(db)

        zip_bytes = await service.export_workspace_data("ws-1", "user-1")

        # Verify it's a valid ZIP
        zf = zipfile.ZipFile(BytesIO(zip_bytes))
        names = zf.namelist()
        assert "metadata.json" in names
        assert "conversations.json" in names
        assert "messages.json" in names
        assert "documents.json" in names
        assert "channels.json" in names
        assert "knowledge_bases.json" in names

        # Verify metadata
        metadata = json.loads(zf.read("metadata.json"))
        assert metadata["schema_version"] == "1.0.0"
        assert metadata["workspace_id"] == "ws-1"
