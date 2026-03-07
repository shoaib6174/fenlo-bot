"""
BotForge ARQ Worker — Background job processor for CPU-intensive tasks.

This worker runs as a separate process/container from the FastAPI API server
to prevent document parsing, embedding generation, and other heavy tasks from
degrading chat latency.

Architecture:
[FastAPI API Server] → Redis Queue → [ARQ Worker Process]
    (handles chat,        (jobs)       (PDF parse, embed,
     WS, REST API)                     sentiment analysis,
                                       webhook delivery)

Jobs:
- process_document: Parse PDF/DOCX/TXT, chunk, embed, store in Pinecone
- generate_embeddings: Create embeddings for chunks
- send_webhook: Deliver webhook with retry logic
- generate_insights: Run sentiment/intent/quality analysis
- archive_old_data: Cleanup job for old conversations
- generate_weekly_insights_cron: Weekly AI insights per workspace (Monday 8am)

Usage:
    # Development (separate terminal):
    python -m arq worker.WorkerSettings

    # Production (systemd service on EC2):
    Start command: python -m arq worker.WorkerSettings
"""

import asyncio
import json
import time
from typing import Any

import structlog
from arq.connections import RedisSettings
from arq.cron import cron

from app.config import settings
from app.modules.rag.langchain_pipeline import LangChainRAGPipeline

logger = structlog.get_logger(__name__)

# Redis keys for worker health tracking
WORKER_HEARTBEAT_KEY = "arq:worker:heartbeat"
WORKER_HEARTBEAT_TTL = 120  # seconds — if no heartbeat for 2min, worker is considered down
WORKER_FAILURES_KEY = "arq:worker:failure_count"
WORKER_DEAD_LETTERS_KEY = "arq:worker:dead_letters"
WORKER_DEAD_LETTERS_MAX = 100  # Keep last 100 dead letters


async def _update_heartbeat(ctx: dict[str, Any]) -> None:
    """Update worker heartbeat in Redis."""
    try:
        redis = ctx.get("redis")
        if redis:
            await redis.set(
                WORKER_HEARTBEAT_KEY,
                json.dumps({"ts": time.time(), "status": "alive"}),
                ex=WORKER_HEARTBEAT_TTL,
            )
    except Exception:
        pass  # Best-effort — don't crash the worker over heartbeat


async def startup(ctx: dict[str, Any]) -> None:
    """Initialize worker context on startup."""
    logger.info("arq_worker.startup", redis_url=settings.redis_url)

    # Initialize RAG pipeline (shared across all jobs)
    if settings.pinecone_api_key:
        ctx["rag_pipeline"] = LangChainRAGPipeline(
            pinecone_api_key=settings.pinecone_api_key,
            pinecone_environment=settings.pinecone_environment,
            index_name=settings.pinecone_index_name,
        )
        logger.info("arq_worker.startup.rag_pipeline_initialized")
    else:
        logger.warning(
            "arq_worker.startup.no_pinecone_key",
            msg="PINECONE_API_KEY not set - document processing will fail",
        )

    # Store database URL for job access
    ctx["database_url"] = settings.database_url

    # Set initial heartbeat
    await _update_heartbeat(ctx)
    logger.info("arq_worker.startup.heartbeat_set")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Clean up resources on shutdown."""
    logger.info("arq_worker.shutdown")
    # Clear heartbeat so health check immediately reports worker as down
    try:
        redis = ctx.get("redis")
        if redis:
            await redis.delete(WORKER_HEARTBEAT_KEY)
    except Exception:
        pass


async def on_job_complete(ctx: dict[str, Any]) -> None:
    """Called after every job completes (success or failure). Updates heartbeat."""
    await _update_heartbeat(ctx)


async def on_job_failure(ctx: dict[str, Any], error: BaseException) -> None:
    """
    Called when a job fails after all retries are exhausted.
    Logs failure details, increments failure counter, and records dead letter.
    """
    job = ctx.get("job_id", "unknown")
    func_name = ctx.get("job_name", "unknown")

    logger.error(
        "arq_worker.job_failure",
        job_id=job,
        function=func_name,
        error=str(error),
        error_type=type(error).__name__,
    )

    try:
        redis = ctx.get("redis")
        if redis:
            # Increment failure counter
            await redis.incr(WORKER_FAILURES_KEY)

            # Add to dead letter list
            dead_letter = json.dumps(
                {
                    "job_id": job,
                    "function": func_name,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "ts": time.time(),
                }
            )
            await redis.lpush(WORKER_DEAD_LETTERS_KEY, dead_letter)
            # Trim to keep only the most recent entries
            await redis.ltrim(WORKER_DEAD_LETTERS_KEY, 0, WORKER_DEAD_LETTERS_MAX - 1)
    except Exception as e:
        logger.warning("arq_worker.dead_letter_write_failed", error=str(e))


async def process_document(
    ctx: dict[str, Any],
    doc_id: str,
    kb_id: str,
    filename: str,
    content: bytes,
    metadata: dict,
) -> dict[str, Any]:
    """
    CPU-intensive: Parse document, chunk, embed, store in Pinecone.

    Args:
        ctx: ARQ context with Redis connection
        doc_id: Document ID from documents table
        kb_id: Knowledge base ID for Pinecone namespace
        filename: Original filename
        content: File content bytes
        metadata: Document metadata

    Returns:
        dict with status, chunk_count, error (if any)
    """
    # Import here to avoid circular imports
    from app.modules.rag.ingestion import process_document_job

    start_time = time.time()

    logger.info(
        "arq_worker.process_document.start",
        doc_id=doc_id,
        kb_id=kb_id,
        filename=filename,
    )

    try:
        result = await process_document_job(
            ctx=ctx,
            doc_id=doc_id,
            kb_id=kb_id,
            filename=filename,
            content=content,
            metadata=metadata,
        )

        duration_s = round(time.time() - start_time, 3)
        logger.info(
            "arq_worker.process_document.complete",
            doc_id=doc_id,
            status=result.get("status"),
            chunk_count=result.get("chunk_count", 0),
            duration_s=duration_s,
        )

        return result

    except Exception as e:
        duration_s = round(time.time() - start_time, 3)
        logger.error(
            "arq_worker.process_document.error",
            doc_id=doc_id,
            error=str(e),
            duration_s=duration_s,
            exc_info=True,
        )

        return {
            "status": "failed",
            "doc_id": doc_id,
            "error": str(e),
        }


async def generate_embeddings(
    ctx: dict[str, Any],
    text_chunks: list[str],
    document_id: str,
) -> dict[str, Any]:
    """
    Generate embeddings for text chunks.

    Args:
        ctx: ARQ context
        text_chunks: List of text chunks to embed
        document_id: Document ID for tracking

    Returns:
        dict with status, embedding_count
    """
    logger.info(
        "arq_worker.generate_embeddings.start",
        document_id=document_id,
        chunk_count=len(text_chunks),
    )

    try:
        # TODO Phase 2: Generate embeddings using sentence-transformers
        # Run in thread pool to avoid blocking
        # embeddings = await asyncio.to_thread(embed_model.encode, text_chunks)

        await asyncio.sleep(0.05)  # Placeholder

        logger.info(
            "arq_worker.generate_embeddings.complete",
            document_id=document_id,
            embedding_count=len(text_chunks),
        )

        return {
            "status": "success",
            "document_id": document_id,
            "embedding_count": len(text_chunks),
        }

    except Exception as e:
        logger.error(
            "arq_worker.generate_embeddings.error",
            document_id=document_id,
            error=str(e),
            exc_info=True,
        )

        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(e),
        }


async def send_webhook(
    ctx: dict[str, Any],
    outbox_id: str,
) -> dict[str, Any]:
    """
    I/O-intensive: Deliver webhook with retry logic.

    Idempotent: If the outbox entry is already sent, this no-ops.
    This is critical because both the fast-path ARQ enqueue AND
    the sweep cron may attempt to deliver the same entry.

    Retry logic:
    - Exponential backoff: 60s, 300s (5min), 900s (15min)
    - After 3 failures → status=dead (dead letter)
    - Updates outbox entry with error message and next_retry_at

    Args:
        ctx: ARQ context with DB URL
        outbox_id: Webhook outbox entry ID

    Returns:
        dict with status, attempts, error
    """
    from datetime import UTC, datetime, timedelta
    from uuid import UUID

    import httpx
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.channel import WebhookOutbox

    logger.info(
        "arq_worker.send_webhook.start",
        outbox_id=outbox_id,
    )

    # Create DB session
    database_url = ctx.get("database_url")
    if not database_url:
        logger.error("arq_worker.send_webhook.no_db_url")
        return {"status": "failed", "error": "No database URL in context"}

    engine = create_async_engine(database_url, echo=False)

    try:
        async with AsyncSession(engine) as session:
            # Load outbox entry
            stmt = select(WebhookOutbox).where(WebhookOutbox.id == UUID(outbox_id))
            result = await session.execute(stmt)
            outbox = result.scalar_one_or_none()

            if not outbox:
                logger.warning("arq_worker.send_webhook.not_found", outbox_id=outbox_id)
                return {"status": "not_found", "outbox_id": outbox_id}

            # Idempotency check — if already sent, no-op
            if outbox.status == "sent":
                logger.debug(
                    "arq_worker.send_webhook.already_sent",
                    outbox_id=outbox_id,
                    msg="Idempotent — entry already delivered",
                )
                return {"status": "already_sent", "outbox_id": outbox_id}

            # If status is dead, don't retry
            if outbox.status == "dead":
                logger.debug(
                    "arq_worker.send_webhook.dead_letter",
                    outbox_id=outbox_id,
                    msg="Entry is dead lettered — not retrying",
                )
                return {"status": "dead", "outbox_id": outbox_id}

            # Perform HTTP POST
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        connect=settings.webhook_connect_timeout,
                        read=settings.webhook_read_timeout,
                    )
                ) as client:
                    # Extract headers from first matching WebhookAction (if any)
                    # For now, outbox doesn't store headers — send without custom headers
                    # TODO: Store headers in outbox entry for full control
                    headers = {"Content-Type": "application/json"}

                    response = await client.post(
                        outbox.target_url,
                        json=outbox.payload,
                        headers=headers,
                    )

                    # Success: 2xx status
                    if 200 <= response.status_code < 300:
                        await session.execute(
                            update(WebhookOutbox)
                            .where(WebhookOutbox.id == UUID(outbox_id))
                            .values(
                                status="sent",
                                sent_at=datetime.now(UTC),
                            )
                        )
                        await session.commit()

                        logger.info(
                            "arq_worker.send_webhook.success",
                            outbox_id=outbox_id,
                            status_code=response.status_code,
                            retry_count=outbox.retry_count,
                        )

                        # Publish WEBHOOK_DELIVERED event
                        try:
                            redis = ctx.get("redis")
                            if redis:
                                from app.core.event_bus import EventTypes

                                await redis.publish(
                                    EventTypes.WEBHOOK_DELIVERED,
                                    json.dumps(
                                        {
                                            "workspace_id": str(outbox.workspace_id),
                                            "event_type": outbox.event_type,
                                            "outbox_id": str(outbox.id),
                                        }
                                    ),
                                )
                        except Exception:
                            pass  # Best-effort event publishing

                        return {
                            "status": "success",
                            "outbox_id": outbox_id,
                            "attempts": outbox.retry_count + 1,
                        }

                    # Failure: non-2xx status → retry
                    else:
                        error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                        raise httpx.HTTPStatusError(
                            error_msg,
                            request=response.request,
                            response=response,
                        )

            except (httpx.HTTPError, Exception) as e:
                # Delivery failed — increment retry count
                new_retry_count = outbox.retry_count + 1
                error_msg = str(e)[:500]  # Truncate long errors

                # Calculate next retry time with exponential backoff
                if new_retry_count >= outbox.max_retries:
                    # Max retries exhausted → dead letter
                    await session.execute(
                        update(WebhookOutbox)
                        .where(WebhookOutbox.id == UUID(outbox_id))
                        .values(
                            status="dead",
                            retry_count=new_retry_count,
                            error_message=error_msg,
                        )
                    )
                    await session.commit()

                    logger.error(
                        "arq_worker.send_webhook.dead_letter",
                        outbox_id=outbox_id,
                        error=error_msg,
                        retries=new_retry_count,
                        msg="Max retries exhausted — moving to dead letter",
                    )

                    # Publish WEBHOOK_FAILED event
                    try:
                        redis = ctx.get("redis")
                        if redis:
                            from app.core.event_bus import EventTypes

                            await redis.publish(
                                EventTypes.WEBHOOK_FAILED,
                                json.dumps(
                                    {
                                        "workspace_id": str(outbox.workspace_id),
                                        "event_type": outbox.event_type,
                                        "outbox_id": str(outbox.id),
                                        "error": error_msg,
                                    }
                                ),
                            )
                    except Exception:
                        pass

                    return {
                        "status": "dead",
                        "outbox_id": outbox_id,
                        "error": error_msg,
                        "attempts": new_retry_count,
                    }

                else:
                    # Schedule retry with exponential backoff
                    # Retry delays: 60s, 300s (5min), 900s (15min)
                    backoff_seconds = settings.webhook_retry_backoff * (5**new_retry_count)
                    next_retry = datetime.now(UTC) + timedelta(seconds=backoff_seconds)

                    await session.execute(
                        update(WebhookOutbox)
                        .where(WebhookOutbox.id == UUID(outbox_id))
                        .values(
                            status="failed",
                            retry_count=new_retry_count,
                            next_retry_at=next_retry,
                            error_message=error_msg,
                        )
                    )
                    await session.commit()

                    logger.warning(
                        "arq_worker.send_webhook.retry_scheduled",
                        outbox_id=outbox_id,
                        error=error_msg,
                        retry_count=new_retry_count,
                        next_retry_at=next_retry.isoformat(),
                        backoff_seconds=backoff_seconds,
                    )

                    return {
                        "status": "retry_scheduled",
                        "outbox_id": outbox_id,
                        "error": error_msg,
                        "attempts": new_retry_count,
                        "next_retry_at": next_retry.isoformat(),
                    }

    except Exception as e:
        logger.error(
            "arq_worker.send_webhook.error",
            outbox_id=outbox_id,
            error=str(e),
            exc_info=True,
        )

        return {
            "status": "failed",
            "outbox_id": outbox_id,
            "error": str(e),
        }

    finally:
        await engine.dispose()


async def generate_insights(
    ctx: dict[str, Any],
    message_id: str,
) -> dict[str, Any]:
    """
    Generate sentiment, intent, quality score for a message.

    Args:
        ctx: ARQ context
        message_id: Message ID to analyze

    Returns:
        dict with status, insights
    """
    logger.info(
        "arq_worker.generate_insights.start",
        message_id=message_id,
    )

    try:
        # TODO Phase 1 stretch/Phase 5: Implement insight generation
        # - Sentiment analysis
        # - Intent classification
        # - Quality scoring

        await asyncio.sleep(0.05)  # Placeholder

        logger.info(
            "arq_worker.generate_insights.complete",
            message_id=message_id,
        )

        return {
            "status": "success",
            "message_id": message_id,
            "sentiment": "neutral",
            "intent": "faq",
            "quality_score": 0.8,
        }

    except Exception as e:
        logger.error(
            "arq_worker.generate_insights.error",
            message_id=message_id,
            error=str(e),
            exc_info=True,
        )

        return {
            "status": "failed",
            "message_id": message_id,
            "error": str(e),
        }


async def archive_old_data(
    ctx: dict[str, Any],
    days: int = 90,
) -> dict[str, Any]:
    """
    Archive conversations and messages older than N days.

    Args:
        ctx: ARQ context
        days: Age threshold in days

    Returns:
        dict with status, archived_count
    """
    logger.info(
        "arq_worker.archive_old_data.start",
        days=days,
    )

    try:
        from app.core.retention_cron import auto_archive_conversations

        await auto_archive_conversations(ctx)

        logger.info(
            "arq_worker.archive_old_data.complete",
            days=days,
        )

        return {
            "status": "success",
        }

    except Exception as e:
        logger.error(
            "arq_worker.archive_old_data.error",
            days=days,
            error=str(e),
            exc_info=True,
        )

        return {
            "status": "failed",
            "error": str(e),
        }


async def sweep_pending_webhooks(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Periodic sweep cron job to catch missed webhook deliveries.

    Runs every 60 seconds. Queries for pending/failed outbox entries
    whose next_retry_at has passed, and enqueues send_webhook jobs for them.

    This provides a safety net if the fast-path ARQ enqueue fails
    (e.g., Redis momentarily unavailable when the outbox entry was created).

    Batching (S49 Spec Panel v2 Review N-02):
    - Uses `while has_more` loop with LIMIT 50
    - Continues until fewer than 50 results (no more pending entries)
    - Safety cap: 500 entries per sweep cycle to prevent runaway loops

    Observability (S49 Spec Panel v2 Review N-02):
    - Logs at INFO level after each run with batch stats
    - Writes Redis heartbeat sweep:last_run_at with 120s TTL
    - Health endpoint includes last_sweep_at timestamp

    Args:
        ctx: ARQ context with DB URL and Redis

    Returns:
        dict with status, entries_found, entries_enqueued
    """
    from datetime import UTC, datetime

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.channel import WebhookOutbox

    logger.info("arq_worker.sweep_pending_webhooks.start")

    # Create DB session
    database_url = ctx.get("database_url")
    if not database_url:
        logger.error("arq_worker.sweep_pending_webhooks.no_db_url")
        return {"status": "failed", "error": "No database URL in context"}

    engine = create_async_engine(database_url, echo=False)

    try:
        entries_found = 0
        entries_enqueued = 0
        batches = 0
        safety_cap = 500  # Max entries per sweep cycle

        async with AsyncSession(engine) as session:
            while entries_found < safety_cap:
                # Query for pending/failed entries ready for delivery
                stmt = (
                    select(WebhookOutbox.id)
                    .where(
                        WebhookOutbox.status.in_(["pending", "failed"]),
                        (
                            (WebhookOutbox.next_retry_at.is_(None))
                            | (WebhookOutbox.next_retry_at <= datetime.now(UTC))
                        ),
                    )
                    .order_by(WebhookOutbox.created_at)
                    .limit(50)
                )

                result = await session.execute(stmt)
                outbox_ids = [str(row[0]) for row in result.all()]

                if not outbox_ids:
                    # No more pending entries
                    break

                entries_found += len(outbox_ids)
                batches += 1

                # Enqueue ARQ jobs for each entry
                redis = ctx.get("redis")
                if redis:
                    for outbox_id in outbox_ids:
                        try:
                            # Use arq_pool from context if available
                            # Otherwise, fall back to enqueueing via redis.lpush (less reliable)
                            job_data = {
                                "function": "send_webhook",
                                "args": (outbox_id,),
                                "kwargs": {},
                                "job_id": f"sweep_{outbox_id}_{int(time.time())}",
                                "enqueue_time": time.time(),
                                "queue_name": "arq:queue",
                            }

                            # Directly push to ARQ queue (best-effort)
                            import msgpack

                            await redis.lpush("arq:queue", msgpack.packb(job_data))
                            entries_enqueued += 1

                        except Exception as e:
                            logger.warning(
                                "arq_worker.sweep_pending_webhooks.enqueue_failed",
                                outbox_id=outbox_id,
                                error=str(e),
                            )

                # If we got fewer than 50 results, we're done
                if len(outbox_ids) < 50:
                    break

        # Write sweep heartbeat to Redis (TTL 120s)
        redis = ctx.get("redis")
        if redis:
            await redis.set(
                "sweep:last_run_at",
                json.dumps({"ts": time.time(), "entries_found": entries_found}),
                ex=120,
            )

        logger.info(
            "arq_worker.sweep_pending_webhooks.complete",
            entries_found=entries_found,
            entries_enqueued=entries_enqueued,
            batches=batches,
        )

        return {
            "status": "success",
            "entries_found": entries_found,
            "entries_enqueued": entries_enqueued,
            "batches": batches,
        }

    except Exception as e:
        logger.error(
            "arq_worker.sweep_pending_webhooks.error",
            error=str(e),
            exc_info=True,
        )

        return {
            "status": "failed",
            "error": str(e),
        }

    finally:
        await engine.dispose()


async def generate_weekly_insights_cron(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Weekly cron job: generate AI insights for every active workspace.

    Runs every Monday at 08:00 UTC. Creates a WeeklyInsight record per
    workspace for the previous week (Mon–Sun).
    """
    from datetime import date, timedelta

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.insights import WeeklyInsight
    from app.models.workspace import Workspace
    from app.services.insights_generator import get_insights_generator

    logger.info("arq_worker.weekly_insights.start")

    database_url = ctx.get("database_url")
    if not database_url:
        logger.error("arq_worker.weekly_insights.no_db_url")
        return {"status": "failed", "error": "No database URL in context"}

    engine = create_async_engine(database_url, echo=False)

    try:
        # Previous week bounds (Mon–Sun)
        today = date.today()
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)

        generated = 0
        skipped = 0

        async with AsyncSession(engine) as session:
            # Get all workspace IDs
            ws_rows = (await session.execute(select(Workspace.id))).scalars().all()

            for ws_id in ws_rows:
                # Skip if insight already exists for this week
                existing = (
                    await session.execute(
                        select(WeeklyInsight.id).where(
                            WeeklyInsight.workspace_id == str(ws_id),
                            WeeklyInsight.week_start == last_monday,
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    skipped += 1
                    continue

                try:
                    generator = get_insights_generator()
                    await generator.generate_weekly_insights(
                        str(ws_id), last_monday, last_sunday, session
                    )
                    generated += 1
                except Exception as e:
                    logger.warning(
                        "arq_worker.weekly_insights.workspace_failed",
                        workspace_id=str(ws_id),
                        error=str(e),
                    )

        logger.info(
            "arq_worker.weekly_insights.complete",
            generated=generated,
            skipped=skipped,
        )

        return {"status": "success", "generated": generated, "skipped": skipped}

    except Exception as e:
        logger.error(
            "arq_worker.weekly_insights.error",
            error=str(e),
            exc_info=True,
        )
        return {"status": "failed", "error": str(e)}

    finally:
        await engine.dispose()


# ── Handoff Auto-Resolve (S73) ────────────────────────────────────


async def check_handoff_timeouts(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Periodic cron job: auto-resolve escalated conversations past their timeout.

    Queries conversations with status='escalated' where auto_resolve_at has passed.
    Calls HandoffService.resolve() with auto=True for each.

    Runs every 5 minutes.
    """
    from datetime import UTC, datetime

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.conversation import Conversation

    logger.info("arq_worker.check_handoff_timeouts.start")

    database_url = ctx.get("database_url")
    if not database_url:
        logger.error("arq_worker.check_handoff_timeouts.no_db_url")
        return {"status": "failed", "error": "No database URL in context"}

    engine = create_async_engine(database_url, echo=False)

    try:
        resolved_count = 0
        error_count = 0

        async with AsyncSession(engine) as session:
            # Find escalated conversations past auto_resolve_at
            now = datetime.now(UTC).isoformat()
            stmt = select(Conversation).where(Conversation.status == "escalated").limit(50)
            result = await session.execute(stmt)
            conversations = result.scalars().all()

            for conv in conversations:
                metadata = conv.metadata_ or {}
                auto_resolve_at = metadata.get("auto_resolve_at")
                if not auto_resolve_at:
                    continue

                if auto_resolve_at > now:
                    continue  # Not yet expired

                try:
                    from app.services.handoff_service import HandoffService

                    service = HandoffService()
                    svc_result = await service.resolve(
                        conversation_id=conv.id,
                        session=session,
                        auto=True,
                    )
                    if svc_result.success:
                        resolved_count += 1
                        logger.info(
                            "arq_worker.check_handoff_timeouts.resolved",
                            conversation_id=str(conv.id),
                        )
                    else:
                        error_count += 1
                        logger.warning(
                            "arq_worker.check_handoff_timeouts.resolve_failed",
                            conversation_id=str(conv.id),
                            error=svc_result.error,
                        )
                except Exception as e:
                    error_count += 1
                    logger.error(
                        "arq_worker.check_handoff_timeouts.error",
                        conversation_id=str(conv.id),
                        error=str(e),
                    )

        logger.info(
            "arq_worker.check_handoff_timeouts.complete",
            resolved=resolved_count,
            errors=error_count,
        )
        return {"status": "success", "resolved": resolved_count, "errors": error_count}

    except Exception as e:
        logger.error(
            "arq_worker.check_handoff_timeouts.error",
            error=str(e),
            exc_info=True,
        )
        return {"status": "failed", "error": str(e)}

    finally:
        await engine.dispose()


# ARQ Worker Configuration
class WorkerSettings:
    """ARQ worker configuration."""

    # Job functions
    functions = [
        process_document,
        generate_embeddings,
        send_webhook,
        generate_insights,
        archive_old_data,
        sweep_pending_webhooks,
        generate_weekly_insights_cron,
        check_handoff_timeouts,
    ]

    # Cron jobs (periodic tasks) — must be CronJob instances via arq.cron.cron()
    cron_jobs = [
        # Sweep for missed webhook deliveries every minute
        cron(sweep_pending_webhooks, second=0, unique=True),
        # Weekly AI insights — every Monday 08:00 UTC
        cron(
            generate_weekly_insights_cron, weekday={0}, hour={8}, minute={0}, second=0, unique=True
        ),
        # Daily auto-archive — every day at 03:00 UTC
        cron(archive_old_data, hour={3}, minute={0}, second=0, unique=True),
        # Handoff auto-resolve — every 5 minutes
        cron(
            check_handoff_timeouts,
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
            second=30,
            unique=True,
        ),
    ]

    # Redis connection
    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    # Worker settings
    max_jobs = 10  # Max concurrent jobs
    job_timeout = 300  # 5 minutes max per job
    max_tries = 3  # Retry failed jobs up to 3 times

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    after_job_end = on_job_complete

    # Health check (ARQ built-in)
    health_check_key = "arq:health"
    health_check_interval = 60  # seconds
