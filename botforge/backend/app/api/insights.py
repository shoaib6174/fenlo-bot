"""
Insights API — AI-generated weekly analytics summaries.

Endpoints:
  GET  /weekly    — get insight for a specific week (default: current)
  GET  /history   — list past insights
  POST /generate  — trigger manual generation (admin only)
"""

from datetime import date, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.insights import WeeklyInsight
from app.services.insights_generator import get_insights_generator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


def _week_bounds(ref: date | None = None) -> tuple[date, date]:
    """Return (Monday, Sunday) of the week containing *ref* (default: today)."""
    d = ref or date.today()
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


# ------------------------------------------------------------------
# GET /weekly — retrieve an existing insight (or 404)
# ------------------------------------------------------------------


@router.get("/weekly", dependencies=[Depends(require_role("viewer"))])
async def get_weekly_insight(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    week: date | None = Query(default=None, description="Any date in the target week (YYYY-MM-DD)"),
):
    """Return the AI-generated weekly insight for the given week."""
    _, workspace_id, _ = current_user
    week_start, week_end = _week_bounds(week)

    insight = (
        await db.execute(
            select(WeeklyInsight).where(
                WeeklyInsight.workspace_id == str(workspace_id),
                WeeklyInsight.week_start == week_start,
            )
        )
    ).scalar_one_or_none()

    if not insight:
        raise HTTPException(status_code=404, detail="No insight generated for this week yet")

    return {
        "id": str(insight.id),
        "period": insight.period,
        "summary": insight.summary,
        "metrics": insight.metrics,
        "recommendations": insight.recommendations,
        "created_at": insight.created_at.isoformat() if insight.created_at else None,
    }


# ------------------------------------------------------------------
# GET /history — paginated list of past insights
# ------------------------------------------------------------------


@router.get("/history", dependencies=[Depends(require_role("viewer"))])
async def get_insights_history(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=52),
):
    """Return the most recent weekly insights (newest first)."""
    _, workspace_id, _ = current_user

    rows = (
        (
            await db.execute(
                select(WeeklyInsight)
                .where(WeeklyInsight.workspace_id == str(workspace_id))
                .order_by(WeeklyInsight.week_start.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )

    return [
        {
            "id": str(r.id),
            "period": r.period,
            "summary": r.summary,
            "week_start": r.week_start.isoformat() if r.week_start else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ------------------------------------------------------------------
# POST /generate — manual trigger (admin)
# ------------------------------------------------------------------


@router.post("/generate", dependencies=[Depends(require_role("admin"))])
async def generate_insight(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    week: date | None = Query(default=None, description="Any date in the target week (YYYY-MM-DD)"),
):
    """Trigger manual insight generation for a given week (admin only)."""
    _, workspace_id, _ = current_user
    week_start, week_end = _week_bounds(week)

    # Check if insight already exists
    existing = (
        await db.execute(
            select(WeeklyInsight.id).where(
                WeeklyInsight.workspace_id == str(workspace_id),
                WeeklyInsight.week_start == week_start,
            )
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Insight already exists for week of {week_start}",
        )

    generator = get_insights_generator()
    insight = await generator.generate_weekly_insights(str(workspace_id), week_start, week_end, db)

    return {
        "id": str(insight.id),
        "period": insight.period,
        "status": insight.status,
    }
