"""Tests for ARQ worker job queue service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.job_queue import JobQueue, close_job_queue, get_job_queue


@pytest.fixture
def mock_arq_pool():
    """Mock ARQ Redis pool."""
    pool = AsyncMock()
    pool.enqueue_job = AsyncMock()
    pool.job_result = AsyncMock()
    pool.close = AsyncMock()
    return pool


@pytest.fixture
async def job_queue(mock_arq_pool):
    """Create JobQueue instance with mocked pool."""
    queue = JobQueue()
    queue._pool = mock_arq_pool
    return queue


class TestJobQueue:
    """Test JobQueue service."""

    async def test_context_manager_initialization(self):
        """Test JobQueue context manager creates and closes pool."""
        with patch("app.services.job_queue.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            async with JobQueue() as queue:
                assert queue._pool is not None
                mock_create_pool.assert_called_once()

            mock_pool.close.assert_called_once()

    async def test_pool_property_raises_when_not_initialized(self):
        """Test pool property raises RuntimeError when not initialized."""
        queue = JobQueue()
        with pytest.raises(RuntimeError, match="JobQueue not initialized"):
            _ = queue.pool

    async def test_enqueue_document_processing(self, job_queue, mock_arq_pool):
        """Test enqueueing document processing job."""
        mock_job = MagicMock()
        mock_job.job_id = "test-job-123"
        mock_arq_pool.enqueue_job.return_value = mock_job

        result = await job_queue.enqueue_document_processing(
            document_id="doc-123",
            workspace_id="ws-456",
            kb_id="kb-789",
        )

        assert result == mock_job
        mock_arq_pool.enqueue_job.assert_called_once_with(
            "process_document",
            "doc-123",
            "ws-456",
            "kb-789",
        )

    async def test_enqueue_embedding_generation(self, job_queue, mock_arq_pool):
        """Test enqueueing embedding generation job."""
        mock_job = MagicMock()
        mock_job.job_id = "embed-job-456"
        mock_arq_pool.enqueue_job.return_value = mock_job

        chunks = ["chunk1", "chunk2", "chunk3"]
        result = await job_queue.enqueue_embedding_generation(
            text_chunks=chunks,
            document_id="doc-123",
        )

        assert result == mock_job
        mock_arq_pool.enqueue_job.assert_called_once_with(
            "generate_embeddings",
            chunks,
            "doc-123",
        )

    async def test_enqueue_webhook_delivery(self, job_queue, mock_arq_pool):
        """Test enqueueing webhook delivery job."""
        mock_job = MagicMock()
        mock_job.job_id = "webhook-job-789"
        mock_arq_pool.enqueue_job.return_value = mock_job

        result = await job_queue.enqueue_webhook_delivery(outbox_id="outbox-123")

        assert result == mock_job
        mock_arq_pool.enqueue_job.assert_called_once_with(
            "send_webhook",
            "outbox-123",
        )

    async def test_enqueue_insight_generation(self, job_queue, mock_arq_pool):
        """Test enqueueing insight generation job."""
        mock_job = MagicMock()
        mock_job.job_id = "insight-job-101"
        mock_arq_pool.enqueue_job.return_value = mock_job

        result = await job_queue.enqueue_insight_generation(message_id="msg-123")

        assert result == mock_job
        mock_arq_pool.enqueue_job.assert_called_once_with(
            "generate_insights",
            "msg-123",
        )

    async def test_enqueue_data_archival(self, job_queue, mock_arq_pool):
        """Test enqueueing data archival job."""
        mock_job = MagicMock()
        mock_job.job_id = "archive-job-202"
        mock_arq_pool.enqueue_job.return_value = mock_job

        result = await job_queue.enqueue_data_archival(days=90)

        assert result == mock_job
        mock_arq_pool.enqueue_job.assert_called_once_with(
            "archive_old_data",
            90,
        )

    async def test_get_job_result_success(self, job_queue, mock_arq_pool):
        """Test getting job result successfully."""
        expected_result = {"status": "success", "data": "processed"}
        mock_arq_pool.job_result.return_value = expected_result

        result = await job_queue.get_job_result("job-123")

        assert result == expected_result
        mock_arq_pool.job_result.assert_called_once_with("job-123")

    async def test_get_job_result_error(self, job_queue, mock_arq_pool):
        """Test getting job result returns None on error."""
        mock_arq_pool.job_result.side_effect = Exception("Job not found")

        result = await job_queue.get_job_result("nonexistent-job")

        assert result is None

    async def test_job_logging_on_enqueue(self, job_queue, mock_arq_pool):
        """Test that jobs are logged when enqueued."""
        mock_job = MagicMock()
        mock_job.job_id = "test-job-123"
        mock_arq_pool.enqueue_job.return_value = mock_job

        with patch("app.services.job_queue.logger") as mock_logger:
            await job_queue.enqueue_document_processing(
                document_id="doc-123",
                workspace_id="ws-456",
                kb_id="kb-789",
            )

            # Logger should have been called with info
            assert mock_logger.info.called


class TestJobQueueSingleton:
    """Test JobQueue singleton dependency injection."""

    async def test_get_job_queue_singleton(self):
        """Test get_job_queue returns singleton instance."""
        import app.services.job_queue as jq_module

        # Reset global state before test
        jq_module._job_queue = None

        with patch("app.services.job_queue.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            queue1 = await get_job_queue()
            queue2 = await get_job_queue()

            assert queue1 is queue2
            mock_create_pool.assert_called_once()  # Only called once

        # Cleanup
        jq_module._job_queue = None

    async def test_close_job_queue(self):
        """Test closing the global job queue."""
        import app.services.job_queue as jq_module

        # Reset global state before test
        jq_module._job_queue = None

        with patch("app.services.job_queue.create_pool") as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool

            await get_job_queue()
            await close_job_queue()

            mock_pool.close.assert_called_once()

        # Cleanup
        jq_module._job_queue = None
