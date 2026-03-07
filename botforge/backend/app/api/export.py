"""Conversation export API — CSV bulk export and single transcript download."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.services.export_service import ConversationExportService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.get("/conversations/csv")
async def export_conversations_csv(
    channel: str | None = Query(None, description="Filter by channel"),
    status: str | None = Query(None, description="Filter by status"),
    user_tuple=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all conversations as CSV download."""
    _user, workspace_id, _role = user_tuple

    service = ConversationExportService(db)
    csv_bytes = await service.export_csv(str(workspace_id), channel=channel, status=status)

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=conversations_{workspace_id}.csv",
        },
    )


@router.get("/conversations/{conversation_id}/transcript")
async def export_conversation_transcript(
    conversation_id: str,
    user_tuple=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export a single conversation as a text transcript."""
    _user, workspace_id, _role = user_tuple

    service = ConversationExportService(db)
    transcript_bytes = await service.export_transcript(conversation_id, str(workspace_id))

    if not transcript_bytes:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return Response(
        content=transcript_bytes,
        media_type="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=transcript_{conversation_id}.txt",
        },
    )
