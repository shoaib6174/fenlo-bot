"""
Webhook Actions API — CRUD for webhook action configuration.

Admins create webhook actions that trigger on specific events (e.g., "lead.qualified").
When the event occurs, the action dispatcher creates outbox entries for delivery.
"""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.channel import WebhookAction, WebhookOutbox
from app.models.user import User
from app.schemas.webhook import (
    WebhookActionCreate,
    WebhookActionResponse,
    WebhookActionUpdate,
    WebhookHistoryResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/webhook-actions", tags=["webhooks"])


@router.post(
    "",
    response_model=WebhookActionResponse,
    status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
async def create_webhook_action(
    data: WebhookActionCreate,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebhookAction:
    """
    Create a new webhook action.

    Webhook actions trigger on specific events (e.g., "message.created", "lead.qualified").
    When the event occurs, the action dispatcher creates an outbox entry for delivery.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    # Validate URL exists in config
    if "url" not in data.config or not data.config["url"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_CONFIG",
                    "message": "Webhook config must include a 'url' field",
                }
            },
        )

    action = WebhookAction(
        workspace_id=workspace_id,
        trigger_event=data.trigger_event,
        action_type=data.action_type,
        config=data.config,
        is_active=data.is_active,
    )

    db.add(action)
    await db.commit()
    await db.refresh(action)

    logger.info(
        "webhook_action.created",
        action_id=str(action.id),
        workspace_id=str(workspace_id),
        trigger_event=data.trigger_event,
    )

    return action


@router.get(
    "", response_model=list[WebhookActionResponse], dependencies=[Depends(require_role("admin"))]
)
async def list_webhook_actions(
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WebhookAction]:
    """
    List all webhook actions for the workspace.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = (
        select(WebhookAction)
        .where(WebhookAction.workspace_id == workspace_id)
        .order_by(WebhookAction.created_at.desc())
    )

    result = await db.execute(stmt)
    actions = list(result.scalars().all())

    return actions


@router.get(
    "/history", response_model=WebhookHistoryResponse, dependencies=[Depends(require_role("admin"))]
)
async def get_webhook_history(
    page: int = 1,
    per_page: int = 50,
    status: str | None = None,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get webhook delivery history (outbox entries) with pagination.

    Supports filtering by status: pending, sent, failed, dead.

    **Query params**:
    - `page`: Page number (default: 1)
    - `per_page`: Items per page (default: 50, max: 100)
    - `status`: Filter by status (optional)

    **Required role**: admin
    """
    _, workspace_id, _ = user

    # Validate pagination params
    if per_page > 100:
        per_page = 100
    if page < 1:
        page = 1

    # Build query
    stmt = select(WebhookOutbox).where(WebhookOutbox.workspace_id == workspace_id)

    # Apply status filter if provided
    if status:
        valid_statuses = ["pending", "sent", "failed", "dead"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            )
        stmt = stmt.where(WebhookOutbox.status == status)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.alias())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Apply pagination
    stmt = (
        stmt.order_by(WebhookOutbox.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    )

    result = await db.execute(stmt)
    items = list(result.scalars().all())

    # Calculate total pages
    pages = (total + per_page - 1) // per_page if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get(
    "/{action_id}",
    response_model=WebhookActionResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def get_webhook_action(
    action_id: UUID,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebhookAction:
    """
    Get a specific webhook action by ID.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = select(WebhookAction).where(
        WebhookAction.id == action_id,
        WebhookAction.workspace_id == workspace_id,
    )

    result = await db.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Webhook action not found")

    return action


@router.put(
    "/{action_id}",
    response_model=WebhookActionResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def update_webhook_action(
    action_id: UUID,
    data: WebhookActionUpdate,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebhookAction:
    """
    Update a webhook action.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    # Fetch existing action
    stmt = select(WebhookAction).where(
        WebhookAction.id == action_id,
        WebhookAction.workspace_id == workspace_id,
    )

    result = await db.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Webhook action not found")

    # Update fields
    if data.trigger_event is not None:
        action.trigger_event = data.trigger_event
    if data.action_type is not None:
        action.action_type = data.action_type
    if data.config is not None:
        # Validate URL exists if updating config
        if "url" not in data.config or not data.config["url"]:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_CONFIG",
                        "message": "Webhook config must include a 'url' field",
                    }
                },
            )
        action.config = data.config
    if data.is_active is not None:
        action.is_active = data.is_active

    await db.commit()
    await db.refresh(action)

    logger.info(
        "webhook_action.updated",
        action_id=str(action.id),
        workspace_id=str(workspace_id),
    )

    return action


@router.delete("/{action_id}", status_code=204, dependencies=[Depends(require_role("admin"))])
async def delete_webhook_action(
    action_id: UUID,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a webhook action.

    This does NOT delete existing outbox entries — they will continue to be delivered.
    It only prevents new outbox entries from being created for this action.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    # Fetch existing action
    stmt = select(WebhookAction).where(
        WebhookAction.id == action_id,
        WebhookAction.workspace_id == workspace_id,
    )

    result = await db.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Webhook action not found")

    await db.delete(action)
    await db.commit()

    logger.info(
        "webhook_action.deleted",
        action_id=str(action.id),
        workspace_id=str(workspace_id),
    )
