"""Immutable audit logger for GDPR compliance operations.

Uses structured logging as the primary audit trail. In production, these logs
should be shipped to an append-only store (CloudWatch Logs, S3, etc.) via
the log infrastructure.
"""

from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger("compliance.audit")


class ImmutableAuditLogger:
    """Writes compliance audit events to structured logs.

    Each event is logged with a consistent schema that can be parsed and
    shipped to an immutable store by the log pipeline.
    """

    async def log_purge_attempt(
        self,
        workspace_id: str,
        requester_user_id: str,
        phase: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log a purge operation phase to the immutable audit trail."""
        event = {
            "audit_type": "gdpr_purge",
            "workspace_id": workspace_id,
            "requester_user_id": requester_user_id,
            "phase": phase,
            "status": status,
            "details": details or {},
            "timestamp_iso": datetime.now(UTC).isoformat(),
        }
        logger.info(
            "compliance.purge_audit",
            **event,
        )

    async def log_export_attempt(
        self,
        workspace_id: str,
        requester_user_id: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log a data export operation to the immutable audit trail."""
        event = {
            "audit_type": "gdpr_export",
            "workspace_id": workspace_id,
            "requester_user_id": requester_user_id,
            "status": status,
            "details": details or {},
            "timestamp_iso": datetime.now(UTC).isoformat(),
        }
        logger.info(
            "compliance.export_audit",
            **event,
        )

    async def log_archive_attempt(
        self,
        workspace_id: str,
        archived_count: int,
        before_date: str,
    ) -> None:
        """Log an archive operation to the immutable audit trail."""
        logger.info(
            "compliance.archive_audit",
            audit_type="data_archive",
            workspace_id=workspace_id,
            archived_count=archived_count,
            before_date=before_date,
            timestamp_iso=datetime.now(UTC).isoformat(),
        )
