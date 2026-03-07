"""
Job Queue Service — Enqueue background jobs to ARQ worker.

This service provides a clean interface for the FastAPI application to
enqueue jobs without directly coupling to ARQ implementation details.
"""

from typing import Any

import structlog
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import settings

logger = structlog.get_logger(__name__)


class JobQueue:
    """
    Job queue service for enqueueing background tasks to ARQ worker.

    Usage:
        async with JobQueue() as queue:
            job = await queue.enqueue_document_processing(doc_id, workspace_id, kb_id)
            logger.info("job_enqueued", job_id=job.job_id)
    """

    def __init__(self) -> None:
        self._pool: ArqRedis | None = None

    async def __aenter__(self) -> "JobQueue":
        """Context manager entry — create Redis pool."""
        self._pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Context manager exit — close Redis pool."""
        if self._pool:
            await self._pool.close()

    @property
    def pool(self) -> ArqRedis:
        """Get Redis pool, raising if not initialized."""
        if not self._pool:
            raise RuntimeError(
                "JobQueue not initialized. Use 'async with JobQueue()' context manager."
            )
        return self._pool

    async def enqueue_document_processing(
        self,
        document_id: str,
        workspace_id: str,
        kb_id: str,
    ) -> Any:
        """
        Enqueue document processing job.

        Args:
            document_id: Document ID from documents table
            workspace_id: Workspace ID for scoping
            kb_id: Knowledge base ID for Pinecone namespace

        Returns:
            ARQ Job object with job_id
        """
        job = await self.pool.enqueue_job(
            "process_document",
            document_id,
            workspace_id,
            kb_id,
        )

        logger.info(
            "job_queue.enqueued",
            job_type="process_document",
            job_id=job.job_id if job else None,
            document_id=document_id,
            workspace_id=workspace_id,
            kb_id=kb_id,
        )

        return job

    async def enqueue_embedding_generation(
        self,
        text_chunks: list[str],
        document_id: str,
    ) -> Any:
        """
        Enqueue embedding generation job.

        Args:
            text_chunks: List of text chunks to embed
            document_id: Document ID for tracking

        Returns:
            ARQ Job object
        """
        job = await self.pool.enqueue_job(
            "generate_embeddings",
            text_chunks,
            document_id,
        )

        logger.info(
            "job_queue.enqueued",
            job_type="generate_embeddings",
            job_id=job.job_id if job else None,
            document_id=document_id,
            chunk_count=len(text_chunks),
        )

        return job

    async def enqueue_webhook_delivery(
        self,
        outbox_id: str,
    ) -> Any:
        """
        Enqueue webhook delivery job.

        Args:
            outbox_id: Webhook outbox entry ID

        Returns:
            ARQ Job object
        """
        job = await self.pool.enqueue_job(
            "send_webhook",
            outbox_id,
        )

        logger.info(
            "job_queue.enqueued",
            job_type="send_webhook",
            job_id=job.job_id if job else None,
            outbox_id=outbox_id,
        )

        return job

    async def enqueue_insight_generation(
        self,
        message_id: str,
    ) -> Any:
        """
        Enqueue insight generation job (sentiment, intent, quality).

        Args:
            message_id: Message ID to analyze

        Returns:
            ARQ Job object
        """
        job = await self.pool.enqueue_job(
            "generate_insights",
            message_id,
        )

        logger.info(
            "job_queue.enqueued",
            job_type="generate_insights",
            job_id=job.job_id if job else None,
            message_id=message_id,
        )

        return job

    async def enqueue_data_archival(
        self,
        days: int = 90,
    ) -> Any:
        """
        Enqueue data archival job.

        Args:
            days: Archive data older than this many days

        Returns:
            ARQ Job object
        """
        job = await self.pool.enqueue_job(
            "archive_old_data",
            days,
        )

        logger.info(
            "job_queue.enqueued",
            job_type="archive_old_data",
            job_id=job.job_id if job else None,
            days=days,
        )

        return job

    async def get_job_result(self, job_id: str) -> Any:
        """
        Get job result by job ID.

        Args:
            job_id: ARQ job ID

        Returns:
            Job result or None if not complete
        """
        try:
            result = await self.pool.job_result(job_id)
            return result
        except Exception as e:
            logger.error(
                "job_queue.get_result_error",
                job_id=job_id,
                error=str(e),
            )
            return None


# Singleton instance for dependency injection
_job_queue: JobQueue | None = None


async def get_job_queue() -> JobQueue:
    """
    Dependency injection for JobQueue service.

    Usage in FastAPI routes:
        @router.post("/upload")
        async def upload_document(
            queue: JobQueue = Depends(get_job_queue),
        ):
            job = await queue.enqueue_document_processing(...)
    """
    global _job_queue

    if _job_queue is None:
        _job_queue = JobQueue()
        await _job_queue.__aenter__()

    return _job_queue


async def close_job_queue() -> None:
    """Close the global job queue connection."""
    global _job_queue

    if _job_queue is not None:
        await _job_queue.__aexit__(None, None, None)
        _job_queue = None
