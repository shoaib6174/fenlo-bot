"""
Workspace settings API routes (for testing RBAC).
Spec: docs/plans/phase-0-scaffold.md § 0b.2a
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.middleware.rbac import require_role

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("")
async def get_settings(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get workspace settings.
    Accessible by: owner, admin
    """
    user, workspace_id, role = current_user

    # Get workspace
    from sqlalchemy import select

    from app.models.workspace import Workspace

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Workspace not found")

    return {
        "workspace_id": str(workspace.id),
        "name": workspace.name,
        "settings": workspace.settings,
        "features": workspace.features,
        "token_budget_monthly": workspace.token_budget_monthly,
    }


@router.put("")
async def update_settings(
    settings_data: dict,
    current_user: tuple = Depends(get_current_user),
    _: None = Depends(require_role("admin")),  # admin or owner only
    db: AsyncSession = Depends(get_db),
):
    """
    Update workspace settings.
    Accessible by: owner, admin only (enforced by RBAC)
    """
    from fastapi import HTTPException

    user, workspace_id, role = current_user

    # Get workspace
    from sqlalchemy import select

    from app.models.workspace import Workspace

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Workspace not found")

    # Update settings (merge with existing)
    workspace.settings = {**workspace.settings, **settings_data}
    await db.commit()

    return {
        "message": "Settings updated successfully",
        "settings": workspace.settings,
    }


@router.delete("/billing")
async def delete_workspace(
    current_user: tuple = Depends(get_current_user),
    _: None = Depends(require_role("owner")),  # owner only
    db: AsyncSession = Depends(get_db),
):
    """
    Delete workspace (billing endpoint example).
    Accessible by: owner only (enforced by RBAC)
    """
    user, workspace_id, role = current_user

    return {
        "message": "This would delete the workspace (not implemented in Phase 0)",
        "workspace_id": str(workspace_id),
        "allowed_role": role,
    }
