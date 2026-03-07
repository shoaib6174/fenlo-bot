"""ARQ cron job for auto-archiving old conversations based on retention policy."""

from datetime import UTC, datetime, timedelta

import structlog

logger = structlog.get_logger(__name__)


async def auto_archive_conversations(ctx: dict) -> None:
    """Archive conversations older than retention_days for all workspaces.

    Runs as an ARQ cron job (e.g. daily at 03:00 UTC).
    """
    from app.config import settings

    if not settings.auto_archive_enabled:
        logger.info("retention_cron.disabled")
        return

    from sqlalchemy import select

    from app.dependencies import AsyncSessionLocal
    from app.models.workspace import Workspace
    from app.services.data_lifecycle import DataLifecycleService

    cutoff = datetime.now(UTC) - timedelta(days=settings.retention_days)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Workspace.id))
        workspace_ids = [str(row[0]) for row in result.all()]

        total_archived = 0
        for ws_id in workspace_ids:
            try:
                service = DataLifecycleService(db)
                archived = await service.archive_old_conversations(ws_id, cutoff)
                if archived > 0:
                    total_archived += archived
                    logger.info(
                        "retention_cron.archived",
                        workspace_id=ws_id,
                        count=archived,
                    )
            except Exception as e:
                logger.error(
                    "retention_cron.error",
                    workspace_id=ws_id,
                    error=str(e),
                )

        await db.commit()

    logger.info(
        "retention_cron.complete",
        total_archived=total_archived,
        workspaces_processed=len(workspace_ids),
        retention_days=settings.retention_days,
    )
