"""
Analytics API — Workspace-scoped analytics with Redis caching.

Endpoints:
  GET /overview    — high-level metrics
  GET /volume      — message/conversation volume time series
  GET /top-questions — most frequent user messages
  GET /sentiment   — sentiment distribution over time
  GET /channels    — per-channel breakdown
  GET /lead-scores — lead score bucket distribution
"""

from datetime import date, timedelta

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.analytics_cache import get_analytics_cache
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.services.analytics_service import AnalyticsService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def _default_start() -> date:
    return date.today() - timedelta(days=30)


def _default_end() -> date:
    return date.today()


def _get_service() -> AnalyticsService:
    return AnalyticsService(cache=get_analytics_cache())


@router.get("/overview", dependencies=[Depends(require_role("viewer"))])
async def analytics_overview(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    """High-level workspace metrics for a date range (default: last 30 days)."""
    _, workspace_id, _ = current_user
    start = start_date or _default_start()
    end = end_date or _default_end()
    svc = _get_service()
    return await svc.get_overview(str(workspace_id), start, end, db)


@router.get("/volume", dependencies=[Depends(require_role("viewer"))])
async def analytics_volume(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    period: str = Query("day", pattern="^(day|week|month)$"),
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    """Message and conversation volume time series."""
    _, workspace_id, _ = current_user
    start = start_date or _default_start()
    end = end_date or _default_end()
    svc = _get_service()
    return await svc.get_volume(str(workspace_id), start, end, period, db)


@router.get("/top-questions", dependencies=[Depends(require_role("viewer"))])
async def analytics_top_questions(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    """Most frequent user messages."""
    _, workspace_id, _ = current_user
    svc = _get_service()
    return await svc.get_top_questions(str(workspace_id), limit, db)


@router.get("/sentiment", dependencies=[Depends(require_role("viewer"))])
async def analytics_sentiment(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    period: str = Query("day", pattern="^(day|week|month)$"),
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
):
    """Sentiment distribution over time."""
    _, workspace_id, _ = current_user
    start = start_date or _default_start()
    end = end_date or _default_end()
    svc = _get_service()
    return await svc.get_sentiment(str(workspace_id), start, end, period, db)


@router.get("/channels", dependencies=[Depends(require_role("viewer"))])
async def analytics_channels(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-channel conversation count and quality."""
    _, workspace_id, _ = current_user
    svc = _get_service()
    return await svc.get_channels(str(workspace_id), db)


@router.get("/lead-scores", dependencies=[Depends(require_role("viewer"))])
async def analytics_lead_scores(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lead score bucket distribution."""
    _, workspace_id, _ = current_user
    svc = _get_service()
    return await svc.get_lead_scores(str(workspace_id), db)
