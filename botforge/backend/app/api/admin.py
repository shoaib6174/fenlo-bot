"""Admin API endpoints — GDPR export, purge, archive, storage usage."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.services.data_lifecycle import DataLifecycleService, PurgeFailedError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/export/{workspace_id}", dependencies=[Depends(require_role("admin"))])
async def export_workspace_data(
    workspace_id: str,
    user_tuple=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all workspace data as a ZIP file (GDPR Art. 20)."""
    user, ws_id, _role = user_tuple

    if str(ws_id) != workspace_id:
        raise HTTPException(status_code=403, detail="Cannot export another workspace's data")

    service = DataLifecycleService(db)
    try:
        zip_bytes = await service.export_workspace_data(workspace_id, str(user.id))
    except Exception as e:
        logger.error("admin.export_failed", workspace_id=workspace_id, error=str(e))
        raise HTTPException(status_code=500, detail="Export failed") from e

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=export_{workspace_id}.zip",
        },
    )


@router.delete("/workspace/{workspace_id}/data", dependencies=[Depends(require_role("admin"))])
async def purge_workspace_data(
    workspace_id: str,
    user_tuple=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Purge all workspace data (GDPR Art. 17 — Right to erasure).

    WARNING: This permanently deletes all conversations, messages, documents,
    channels, and knowledge bases for the workspace. This cannot be undone.
    """
    user, ws_id, _role = user_tuple

    if str(ws_id) != workspace_id:
        raise HTTPException(status_code=403, detail="Cannot purge another workspace's data")

    service = DataLifecycleService(db)
    try:
        report = await service.purge_workspace(workspace_id, str(user.id))
    except PurgeFailedError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "success": report.success,
        "deleted_records": report.deleted_records,
        "duration_ms": round(report.duration_ms, 2),
    }


@router.post("/archive", dependencies=[Depends(require_role("admin"))])
async def archive_conversations(
    before: str = Query(..., description="ISO date — archive conversations before this date"),
    user_tuple=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive (close) old conversations before a cutoff date."""
    _user, workspace_id, _role = user_tuple

    from datetime import datetime

    try:
        cutoff = datetime.fromisoformat(before)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO-8601.") from e

    service = DataLifecycleService(db)
    archived = await service.archive_old_conversations(str(workspace_id), cutoff)

    return {"success": True, "archived_count": archived}


@router.get("/storage/{workspace_id}", dependencies=[Depends(require_role("admin"))])
async def get_storage_usage(
    workspace_id: str,
    user_tuple=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get storage usage report for a workspace."""
    _user, ws_id, _role = user_tuple

    if str(ws_id) != workspace_id:
        raise HTTPException(status_code=403, detail="Cannot view another workspace's storage")

    service = DataLifecycleService(db)
    report = await service.check_storage_usage(workspace_id)

    return {
        "workspace_id": workspace_id,
        "conversations_count": report.conversations_count,
        "messages_count": report.messages_count,
        "documents_count": report.documents_count,
        "channels_count": report.channels_count,
        "knowledge_bases_count": report.knowledge_bases_count,
    }
