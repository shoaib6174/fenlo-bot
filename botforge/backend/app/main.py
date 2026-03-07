"""BotForge FastAPI application entry point."""

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.middleware.cors import RouteCORSMiddleware

# --- Structlog Configuration ---
_log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        (
            structlog.dev.ConsoleRenderer()
            if settings.log_format == "console"
            else structlog.processors.JSONRenderer()
        ),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(_log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# --- Active WebSocket Connections (for graceful shutdown) ---
# Track active WebSocket connections to notify on shutdown
active_websockets: set = set()


# --- Lifespan Context Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # --- STARTUP ---
    logger.info("app.starting", app=settings.app_name, version="0.1.0")

    # Initialize LLM Router singleton (AX.11)
    from app.core.llm_router import LLMRouter

    app.state.llm_router = LLMRouter()
    logger.info("llm_router.attached_to_app_state")

    # Pre-allocated thread pool for embedding calls (bounds CPU on m7i-flex.large)
    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="embed")
    loop = asyncio.get_running_loop()
    loop.set_default_executor(_executor)
    logger.info("threadpool.initialized", max_workers=2)

    # Initialize Event Bus and Action Dispatcher (Phase 4 S49)
    from app.core.event_bus import create_event_bus
    from app.dependencies import AsyncSessionLocal
    from app.modules.channels.action_dispatcher import ActionDispatcher
    from app.services.job_queue import get_job_queue

    app.state.event_bus = create_event_bus(settings)
    logger.info("event_bus.initialized", backend="in_process")

    # Initialize ARQ pool for action dispatcher
    job_queue = await get_job_queue()
    arq_pool = job_queue.pool

    # Create and start action dispatcher
    app.state.action_dispatcher = ActionDispatcher(
        event_bus=app.state.event_bus,
        db_session_factory=AsyncSessionLocal,
        arq_pool=arq_pool,
    )
    await app.state.action_dispatcher.start()
    logger.info("action_dispatcher.started")

    # Initialize Dashboard Broadcaster — subscribes to event bus for live updates (Phase 5 S58)
    from app.api.dashboard_ws import get_broadcaster
    from app.core.event_bus import EventTypes

    broadcaster = get_broadcaster()
    for et in [
        EventTypes.MESSAGE_CREATED,
        EventTypes.CONVERSATION_STARTED,
        EventTypes.CONVERSATION_ESCALATED,
    ]:
        await app.state.event_bus.subscribe(et, broadcaster.handle_event)
    logger.info("dashboard_broadcaster.started")

    # Initialize Slack Notifier — subscribes to event bus for Slack notifications (Phase 8 S84)
    from app.services.notifications import EmailNotifier, SlackNotifier

    app.state.slack_notifier = SlackNotifier(
        event_bus=app.state.event_bus,
        db_session_factory=AsyncSessionLocal,
    )
    await app.state.slack_notifier.start()
    logger.info("slack_notifier.started")

    # Initialize Email Notifier — subscribes to event bus for email alerts (Phase 8 S85)
    app.state.email_notifier = EmailNotifier(
        event_bus=app.state.event_bus,
        db_session_factory=AsyncSessionLocal,
    )
    await app.state.email_notifier.start()
    logger.info("email_notifier.started")

    # --- Sentry Integration (0.S2) ---
    # Deferred to startup so it doesn't block port binding.
    # Uses default_integrations=False to prevent auto-discovery of langchain
    # integration which triggers a slow transformers import (~8s).
    if settings.sentry_enabled and settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.asyncio import AsyncioIntegration
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.logging import LoggingIntegration
            from sentry_sdk.integrations.starlette import StarletteIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.sentry_environment,
                traces_sample_rate=settings.sentry_traces_sample_rate,
                default_integrations=False,
                integrations=[
                    StarletteIntegration(transaction_style="endpoint"),
                    FastApiIntegration(transaction_style="endpoint"),
                    AsyncioIntegration(),
                    LoggingIntegration(),
                ],
                enable_tracing=True,
                send_default_pii=False,
                release=None,
            )
            logger.info("sentry.initialized", environment=settings.sentry_environment)
        except Exception as e:
            logger.warning("sentry.init_failed", error=str(e))

    yield

    # --- SHUTDOWN ---
    logger.info("shutdown.initiated", active_ws_count=len(active_websockets))

    # Send "reconnecting" message to all active WebSocket clients
    # This allows clients to show a "Server restarting..." UI and auto-reconnect
    reconnect_tasks = []
    for ws in list(active_websockets):
        try:
            task = asyncio.create_task(
                ws.send_json({"type": "reconnect", "message": "Server restarting, please wait..."})
            )
            reconnect_tasks.append(task)
        except Exception as e:
            logger.warning("shutdown.ws_notify_failed", error=str(e))

    if reconnect_tasks:
        await asyncio.gather(*reconnect_tasks, return_exceptions=True)
        logger.info("shutdown.ws_notified", count=len(reconnect_tasks))

    # Grace period for in-flight LLM calls / WebSocket messages to complete
    try:
        await asyncio.sleep(5)
        logger.info("shutdown.grace_period_complete")
    except Exception as e:
        logger.warning("shutdown.grace_period_failed", error=str(e))

    # Close resources
    try:
        from app.core.redis import close_redis
        from app.dependencies import engine

        _executor.shutdown(wait=False)
        logger.info("shutdown.threadpool_closed")

        await close_redis()
        logger.info("shutdown.redis_closed")

        await engine.dispose()
        logger.info("shutdown.db_closed")
    except Exception as e:
        logger.error("shutdown.cleanup_failed", error=str(e))

    logger.info("shutdown.complete")


# --- FastAPI App ---
app = FastAPI(
    title="BotForge API",
    description="""
## 🤖 BotForge - AI Chatbot Platform API

Build, deploy, and manage AI-powered chatbots across multiple channels.

### Features
- 🧠 **RAG-Powered Conversations** — Grounded responses with citations
- 🎙️ **Voice Integration** — Vapi-powered voice calls with escalation
- 📊 **Analytics & Insights** — Sentiment, intent, lead scoring
- 🔌 **Multi-Channel** — Web, WhatsApp, Telegram, Voice, Widget
- 🔐 **Enterprise-Ready** — Workspace isolation, RBAC, GDPR compliance

### Authentication
Most endpoints require a JWT bearer token. Obtain one via `POST /api/v1/auth/login`.

### Rate Limits
- Authenticated: 100 req/min per user
- Widget (anonymous): 20 req/hour per IP

**Documentation**: [Architecture](/architecture) | [GitHub](https://github.com/fenloai-service/botforge)
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
    contact={
        "name": "BotForge Support",
        "email": "support@botforge.com",
    },
    license_info={
        "name": "Proprietary",
    },
)

# --- CORS Middleware ---
# Widget routes (/api/v1/widget/*, /api/v1/chat/stream*, /api/v1/webhooks/*)
# get permissive CORS (any origin, no credentials).
# All other routes get strict CORS (configured origins only, with credentials).
app.add_middleware(RouteCORSMiddleware)


# --- Request Context Middleware ---
@app.middleware("http")
async def request_context_middleware(request: Request, call_next) -> Response:
    """Attach trace_id and timing to every request."""
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
    start_time = time.perf_counter()

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        trace_id=trace_id,
        endpoint=request.url.path,
        method=request.method,
    )

    response: Response = await call_next(request)

    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    logger.info(
        "request.completed",
        status_code=response.status_code,
        duration_ms=duration_ms,
    )

    response.headers["x-trace-id"] = trace_id
    return response


# --- Global Exception Handlers ---
def _get_trace_id() -> str | None:
    """Extract trace_id from structlog context vars."""
    ctx = structlog.contextvars.get_contextvars()
    return ctx.get("trace_id")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Standardize HTTPException responses."""
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE",
        429: "RATE_LIMITED",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code_map.get(exc.status_code, "HTTP_ERROR"),
                "message": str(exc.detail),
                "trace_id": _get_trace_id(),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Standardize Pydantic validation errors."""
    details = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field = (
            ".".join(str(part) for part in loc[1:])
            if len(loc) > 1
            else str(loc[0])
            if loc
            else None
        )
        details.append({"field": field, "message": err.get("msg", "")})

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": details,
                "trace_id": _get_trace_id(),
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions. Logs full traceback, returns safe response."""
    logger.error("unhandled_exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "trace_id": _get_trace_id(),
            }
        },
    )


# --- Route Inclusions ---
from app.api import (  # noqa: E402
    admin,
    analytics,
    api_keys,
    auth,
    booking,
    branding,
    channels,
    chat,
    dashboard,
    dashboard_ws,
    docs,
    export,
    handoff,
    health,
    inbox,
    insights,
    kb,
    notifications,
    onboarding,
    public,
    telegram,
    voice,
    webhook_actions,
    whatsapp,
    whatsapp_meta,
    widget,
    workspace_settings,
    zapier,
)

app.include_router(health.router)


# Root /health endpoint for Nginx health monitoring
@app.get("/health")
async def root_health():
    """Simple health check at /health for Nginx health monitoring."""
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(workspace_settings.router)
app.include_router(chat.router)
app.include_router(kb.router)
app.include_router(docs.router)
app.include_router(dashboard.router)
app.include_router(voice.router)
app.include_router(webhook_actions.router)
app.include_router(zapier.router)
app.include_router(channels.router)
app.include_router(whatsapp.router)
app.include_router(whatsapp_meta.router)
app.include_router(telegram.router)
app.include_router(widget.router)
app.include_router(inbox.router)
app.include_router(handoff.router)
app.include_router(analytics.router)
app.include_router(insights.router)
app.include_router(onboarding.router)
app.include_router(admin.router)
app.include_router(export.router)
app.include_router(notifications.router)
app.include_router(api_keys.router)
app.include_router(branding.router)
app.include_router(booking.router)
app.include_router(dashboard_ws.router)
app.include_router(public.router)
