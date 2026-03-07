"""Unit tests for conversation export service."""

import csv
import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.export_service import CSV_COLUMNS, ConversationExportService


@pytest.mark.asyncio
class TestCSVExport:
    """Test CSV export functionality."""

    async def test_csv_has_correct_headers(self):
        """CSV output should include all required column headers."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        service = ConversationExportService(db)
        csv_bytes = await service.export_csv("ws-1")

        reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
        assert reader.fieldnames == CSV_COLUMNS

    async def test_csv_includes_conversation_data(self):
        """CSV should include conversation data rows."""
        db = AsyncMock()

        # Mock a conversation row
        mock_row = MagicMock()
        mock_row.id = "conv-1"
        mock_row.channel = "web"
        mock_row.contact_name = "John"
        mock_row.status = "active"
        mock_row.lead_score = 42
        mock_row.message_count = 5
        mock_row.started_at = datetime(2026, 2, 15, tzinfo=UTC)
        mock_row.ended_at = None

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db.execute = AsyncMock(return_value=mock_result)

        service = ConversationExportService(db)
        csv_bytes = await service.export_csv("ws-1")

        reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["conversation_id"] == "conv-1"
        assert rows[0]["channel"] == "web"
        assert rows[0]["contact_name"] == "John"
        assert rows[0]["lead_score"] == "42"

    async def test_csv_handles_null_fields(self):
        """CSV should handle None values gracefully."""
        db = AsyncMock()

        mock_row = MagicMock()
        mock_row.id = "conv-2"
        mock_row.channel = None
        mock_row.contact_name = None
        mock_row.status = None
        mock_row.lead_score = None
        mock_row.message_count = None
        mock_row.started_at = None
        mock_row.ended_at = None

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db.execute = AsyncMock(return_value=mock_result)

        service = ConversationExportService(db)
        csv_bytes = await service.export_csv("ws-1")

        reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8")))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["channel"] == ""
        assert rows[0]["lead_score"] == "0"

    async def test_csv_empty_workspace_returns_headers_only(self):
        """Empty workspace should produce CSV with headers but no data rows."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        service = ConversationExportService(db)
        csv_bytes = await service.export_csv("ws-1")

        lines = csv_bytes.decode("utf-8").strip().split("\n")
        assert len(lines) == 1  # Header only


@pytest.mark.asyncio
class TestTranscriptExport:
    """Test text transcript export."""

    async def test_transcript_not_found_returns_empty(self):
        """Missing conversation should return empty bytes."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        service = ConversationExportService(db)
        result = await service.export_transcript("nonexistent", "ws-1")
        assert result == b""

    async def test_transcript_includes_header(self):
        """Transcript should include header with conversation metadata."""
        db = AsyncMock()

        # Mock conversation
        mock_conv = MagicMock()
        mock_conv.id = "conv-1"
        mock_conv.channel = "web"
        mock_conv.contact_name = "Alice"
        mock_conv.status = "active"
        mock_conv.started_at = datetime(2026, 2, 15, 10, 30, tzinfo=UTC)
        mock_conv.lead_score = 25

        conv_result = MagicMock()
        conv_result.scalar_one_or_none.return_value = mock_conv

        # Mock messages (empty)
        msg_result = MagicMock()
        msg_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[conv_result, msg_result])

        service = ConversationExportService(db)
        result = await service.export_transcript("conv-1", "ws-1")
        text = result.decode("utf-8")

        assert "BotForge Conversation Transcript" in text
        assert "conv-1" in text
        assert "web" in text
        assert "Alice" in text
        assert "Total messages: 0" in text

    async def test_csv_columns_constant(self):
        """CSV_COLUMNS should have expected columns."""
        assert "conversation_id" in CSV_COLUMNS
        assert "channel" in CSV_COLUMNS
        assert "message_count" in CSV_COLUMNS
        assert len(CSV_COLUMNS) == 8
