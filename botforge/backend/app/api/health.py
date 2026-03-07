"""
Health check endpoints for liveness, readiness, and full status.
Spec: docs/plans/phase-0-scaffold.md (Section 0a.4)
"""

import json
import time
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.middleware.rate_limiter import ip_rate_limit

router = APIRouter(prefix="/api/health", tags=["health"])

# Track app start time for uptime calculation
_START_TIME = time.time()

# Worker health Redis keys (must match worker.py)
WORKER_HEARTBEAT_KEY = "arq:worker:heartbeat"
WORKER_FAILURES_KEY = "arq:worker:failure_count"
WORKER_DEAD_LETTERS_KEY = "arq:worker:dead_letters"


def get_uptime() -> int:
    """Get application uptime in seconds."""
    return int(time.time() - _START_TIME)


async def check_db(db: AsyncSession) -> bool:
    """Check database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis() -> bool:
    """Check Redis connectivity."""
    # Import here to avoid circular dependency
    from app.core.redis import get_redis_client

    try:
        redis = get_redis_client()
        if redis is None:
            return False
        await redis.ping()
        return True
    except Exception:
        return False


async def check_pinecone() -> Literal["ok", "skipped", "error"]:
    """Check Pinecone connectivity (Phase 2+)."""
    # Placeholder for Phase 2
    return "skipped"


async def check_llm_providers() -> dict:
    """
    Check LLM provider circuit breaker states.
    Returns dict with state and failure count for each provider.
    """
    try:
        from app.core.llm_router import LLMRouter

        router = LLMRouter()
        return {
            "groq": {
                "state": router.groq_circuit.state.value.lower(),
                "failures": len(router.groq_circuit.failures),
            },
            "openai": {
                "state": router.openai_circuit.state.value.lower(),
                "failures": len(router.openai_circuit.failures),
            },
        }
    except Exception:
        return {
            "groq": {"state": "unknown", "failures": 0},
            "openai": {"state": "unknown", "failures": 0},
        }


async def get_active_websocket_count() -> int:
    """Get count of active WebSocket connections."""
    try:
        from app.main import active_websockets

        return len(active_websockets)
    except Exception:
        return 0


async def get_queue_depth() -> int | Literal["skipped"]:
    """Get ARQ queue depth from Redis."""
    from app.core.redis import get_redis_client

    try:
        redis = get_redis_client()
        if redis is None:
            return "skipped"
        # ARQ stores pending jobs in a sorted set
        depth = await redis.zcard("arq:queue")
        return depth or 0
    except Exception:
        return "skipped"


async def check_voice() -> Literal["ok", "skipped", "error"]:
    """Check Vapi API connectivity (Phase 3+)."""
    from app.config import settings

    if not settings.vapi_private_key:
        return "skipped"

    try:
        from app.modules.voice.vapi_provider import VapiProvider

        provider = VapiProvider(private_key=settings.vapi_private_key)
        valid = await provider.validate_keys()
        return "ok" if valid else "error"
    except Exception:
        return "error"


async def get_webhook_metrics() -> dict:
    """
    Get webhook delivery metrics from WebhookOutbox (Phase 4+).
    Returns pending count, failed count, dead letter count, success rate.
    """
    from app.core.redis import get_redis_client

    metrics = {
        "pending": 0,
        "failed": 0,
        "dead": 0,
        "success_rate_1h": None,
        "oldest_pending_age_sec": None,
    }

    try:
        redis = get_redis_client()
        if redis is None:
            return metrics

        # Count pending webhooks
        pending_count = await redis.zcard("webhook_outbox:pending")
        metrics["pending"] = pending_count or 0

        # Count failed webhooks (retry queue)
        failed_count = await redis.zcard("webhook_outbox:retry")
        metrics["failed"] = failed_count or 0

        # Count dead letters
        dead_count = await redis.llen("webhook_outbox:dead_letters")
        metrics["dead"] = dead_count or 0

        # Get oldest pending age
        if pending_count and pending_count > 0:
            oldest = await redis.zrange("webhook_outbox:pending", 0, 0, withscores=True)
            if oldest:
                oldest_score = oldest[0][1]  # (member, score) tuple
                current_time = time.time()
                metrics["oldest_pending_age_sec"] = int(current_time - oldest_score)

        # Success rate: count successes in last hour from stats hash
        success_1h = await redis.get("webhook_stats:success:1h")
        failed_1h = await redis.get("webhook_stats:failed:1h")
        if success_1h or failed_1h:
            success = int(success_1h or 0)
            failed = int(failed_1h or 0)
            total = success + failed
            if total > 0:
                metrics["success_rate_1h"] = round(success / total, 2)

    except Exception:
        pass

    return metrics


async def get_channel_metrics(db: AsyncSession) -> dict:
    """
    Get channel-specific metrics (Phase 4+).
    Returns active channel counts, WebSocket connections, circuit breaker status.
    """
    from sqlalchemy import select

    from app.config import settings
    from app.models.channel import ChannelConfig

    metrics = {
        "active_widgets": 0,
        "active_whatsapp": 0,
        "widget_connections": 0,
        "twilio_circuit_breaker": "unknown",
    }

    try:
        # Count active channel configs
        result = await db.execute(
            select(ChannelConfig.channel, text("COUNT(*)"))
            .where(ChannelConfig.is_active)
            .group_by(ChannelConfig.channel)
        )
        channel_counts = dict(result.all())

        metrics["active_widgets"] = channel_counts.get("widget", 0)
        metrics["active_whatsapp"] = channel_counts.get("whatsapp", 0)

        # Get active WebSocket connections count from Redis
        from app.core.redis import get_redis_client

        redis = get_redis_client()
        if redis:
            widget_ws_count = await redis.get("widget:active_connections")
            metrics["widget_connections"] = int(widget_ws_count or 0)

            # Get Twilio circuit breaker status
            cb_status = await redis.get("twilio:circuit_breaker:status")
            if cb_status:
                metrics["twilio_circuit_breaker"] = cb_status.decode()
            else:
                metrics["twilio_circuit_breaker"] = (
                    "closed" if settings.whatsapp_enabled else "disabled"
                )

    except Exception:
        pass

    return metrics


async def check_worker() -> dict:
    """
    Check ARQ worker health via heartbeat key in Redis.
    Returns dict with status (healthy/degraded/down), last_heartbeat, failure_count.
    """
    from app.core.redis import get_redis_client

    result = {"status": "down", "last_heartbeat": None, "failure_count": 0}

    try:
        redis = get_redis_client()
        if redis is None:
            result["status"] = "unknown"
            return result

        # Check heartbeat
        heartbeat_raw = await redis.get(WORKER_HEARTBEAT_KEY)
        if heartbeat_raw:
            heartbeat = json.loads(heartbeat_raw)
            result["last_heartbeat"] = heartbeat.get("ts")
            age = time.time() - heartbeat.get("ts", 0)
            result["status"] = "healthy" if age < 120 else "degraded"
        else:
            result["status"] = "down"

        # Get failure count
        failure_count = await redis.get(WORKER_FAILURES_KEY)
        result["failure_count"] = int(failure_count) if failure_count else 0

    except Exception:
        result["status"] = "unknown"

    return result


@router.get("/live", dependencies=[Depends(ip_rate_limit)])
async def liveness():
    """
    Liveness probe — container restart check.
    Returns 200 if process is running. < 10ms target.
    """
    return {"status": "ok", "uptime_s": get_uptime()}


@router.get("/ready", dependencies=[Depends(ip_rate_limit)])
async def readiness(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe — load balancer routing.
    Checks critical dependencies: DB, Redis, and worker. < 100ms target.
    """
    db_ok = await check_db(db)
    redis_ok = await check_redis()
    worker = await check_worker()
    worker_status = worker["status"]

    # DB and Redis are critical; worker degradation doesn't block readiness
    critical_ok = db_ok and redis_ok
    status = "ok" if critical_ok else "degraded"

    return {
        "status": status,
        "db": db_ok,
        "redis": redis_ok,
        "worker": worker_status,
    }


@router.get("/worker", dependencies=[Depends(ip_rate_limit)])
async def worker_health():
    """
    Worker health endpoint — detailed ARQ worker status.
    Checks heartbeat, failure count, and recent dead letters.
    """
    from app.core.redis import get_redis_client

    worker = await check_worker()

    # Fetch recent dead letters
    dead_letters = []
    try:
        redis = get_redis_client()
        if redis:
            raw_letters = await redis.lrange(WORKER_DEAD_LETTERS_KEY, 0, 9)
            dead_letters = [json.loads(dl) for dl in raw_letters]
    except Exception:
        pass

    return {
        **worker,
        "dead_letters": dead_letters,
    }


@router.get("/status", dependencies=[Depends(ip_rate_limit)])
async def full_status(db: AsyncSession = Depends(get_db)):
    """
    Full dependency status — all services.
    Incrementally enhanced per phase (see spec). < 2s target.

    Phase 0: DB, Redis
    Phase 1: + LLM providers (Groq, OpenAI)
    Phase 2: + Pinecone, ARQ queue depth
    Phase 3: + Voice (Vapi)
    Phase 4: + Webhooks, Channels (Widget, WhatsApp)
    """
    db_ok = await check_db(db)
    redis_ok = await check_redis()

    # Determine overall status
    critical_ok = db_ok and redis_ok
    status = "ok" if critical_ok else "degraded"

    llm_providers = await check_llm_providers()
    worker = await check_worker()
    websocket_count = await get_active_websocket_count()

    # Refine overall status based on LLM and worker health
    if not critical_ok:
        status = "down"
    elif worker["status"] in ("degraded", "down") or llm_providers["groq"]["state"] == "open":
        status = "degraded"

    return {
        "status": status,
        "db": db_ok,
        "redis": redis_ok,
        "pinecone": await check_pinecone(),
        "llm_providers": llm_providers,
        "arq_queue_depth": await get_queue_depth(),
        "voice": await check_voice(),
        "webhooks": await get_webhook_metrics(),
        "channels": await get_channel_metrics(db),
        "worker": worker,
        "active_websockets": websocket_count,
        "uptime_s": get_uptime(),
    }
