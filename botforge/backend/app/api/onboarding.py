"""Onboarding wizard API — progress tracking and step completion."""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.models.onboarding import ONBOARDING_STEPS, OnboardingProgress

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


async def _get_or_create_progress(workspace_id: str, db: AsyncSession) -> OnboardingProgress:
    """Get existing progress or create a new row for the workspace."""
    result = await db.execute(
        select(OnboardingProgress).where(OnboardingProgress.workspace_id == workspace_id)
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        progress = OnboardingProgress(
            workspace_id=workspace_id,
            current_step=ONBOARDING_STEPS[0],
        )
        db.add(progress)
        await db.flush()
    return progress


def _compute_completion_pct(step_completed: dict) -> int:
    """Return completion percentage (0–100)."""
    total = len(ONBOARDING_STEPS)
    if not step_completed or total == 0:
        return 0
    done = sum(1 for s in ONBOARDING_STEPS if step_completed.get(s, False))
    return int(done / total * 100)


def _next_incomplete_step(step_completed: dict) -> str | None:
    """Return the first incomplete step, or None if all done."""
    for step in ONBOARDING_STEPS:
        if not step_completed.get(step, False):
            return step
    return None


@router.get("/progress")
async def get_progress(
    user_tuple=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current onboarding progress for the workspace."""
    user, workspace_id, _role = user_tuple
    progress = await _get_or_create_progress(str(workspace_id), db)

    return {
        "workspace_id": str(progress.workspace_id),
        "step_completed": progress.step_completed,
        "current_step": progress.current_step,
        "completion_pct": _compute_completion_pct(progress.step_completed),
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
    }


@router.put("/step/{step_name}")
async def complete_step(
    step_name: str,
    user_tuple=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark an onboarding step as completed (idempotent)."""
    if step_name not in ONBOARDING_STEPS:
        raise HTTPException(status_code=400, detail=f"Unknown step: {step_name}")

    user, workspace_id, _role = user_tuple
    progress = await _get_or_create_progress(str(workspace_id), db)

    # Update step_completed JSONB — copy to trigger change detection
    updated = dict(progress.step_completed or {})
    updated[step_name] = True
    progress.step_completed = updated

    # Advance current_step to next incomplete
    next_step = _next_incomplete_step(updated)
    progress.current_step = next_step

    # Check if all steps are done
    from sqlalchemy.sql import func

    if next_step is None and progress.completed_at is None:
        progress.completed_at = func.now()

    await db.flush()

    logger.info(
        "onboarding.step_completed",
        workspace_id=str(workspace_id),
        step=step_name,
    )

    return {
        "success": True,
        "step": step_name,
        "next_step": next_step,
        "completion_pct": _compute_completion_pct(updated),
    }


@router.post("/skip")
async def skip_onboarding(
    user_tuple=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Skip onboarding — marks all steps as complete."""
    user, workspace_id, _role = user_tuple
    progress = await _get_or_create_progress(str(workspace_id), db)

    from sqlalchemy.sql import func

    updated = dict.fromkeys(ONBOARDING_STEPS, True)
    progress.step_completed = updated
    progress.current_step = None
    if progress.completed_at is None:
        progress.completed_at = func.now()

    await db.flush()

    logger.info("onboarding.skipped", workspace_id=str(workspace_id))

    return {"success": True, "completion_pct": 100}


@router.post("/complete")
async def complete_onboarding(
    user_tuple=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly mark onboarding as complete."""
    user, workspace_id, _role = user_tuple
    progress = await _get_or_create_progress(str(workspace_id), db)

    from sqlalchemy.sql import func

    # Mark final "complete" step
    updated = dict(progress.step_completed or {})
    updated["complete"] = True
    progress.step_completed = updated
    progress.current_step = None
    if progress.completed_at is None:
        progress.completed_at = func.now()

    await db.flush()

    logger.info("onboarding.completed", workspace_id=str(workspace_id))

    return {
        "success": True,
        "completed_at": progress.completed_at.isoformat()
        if hasattr(progress.completed_at, "isoformat")
        else str(progress.completed_at),
        "completion_pct": _compute_completion_pct(updated),
    }
