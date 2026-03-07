"""
Booking / Calendar Integration API — workspace scheduling settings (S88).

Endpoints:
- GET  /api/v1/booking        — get booking settings
- PUT  /api/v1/booking        — update booking settings
"""

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.user import User
from app.models.workspace import Workspace

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/booking", tags=["booking"])

VALID_PROVIDERS = {"calendly", "cal_com", "google", "custom_url"}

DEFAULT_BOOKING = {
    "booking_provider": "custom_url",
    "booking_url": "",
    "booking_prompt": "",
    "booking_enabled": False,
}


# ========================
# Schemas
# ========================


class BookingSettings(BaseModel):
    """Booking configuration for calendar integration."""

    booking_provider: str = Field(default="custom_url", max_length=50)
    booking_url: str = Field(default="", max_length=500)
    booking_prompt: str = Field(default="", max_length=500)
    booking_enabled: bool = False


class BookingResponse(BaseModel):
    """Response containing booking settings."""

    booking_provider: str = "custom_url"
    booking_url: str = ""
    booking_prompt: str = ""
    booking_enabled: bool = False


# ========================
# Endpoints
# ========================


@router.get(
    "",
    response_model=BookingResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def get_booking(
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get booking/calendar settings for the workspace.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    settings = workspace.settings or {}
    booking = settings.get("booking", {})

    return {**DEFAULT_BOOKING, **booking}


@router.put(
    "",
    response_model=BookingResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def update_booking(
    data: BookingSettings,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update booking/calendar settings for the workspace.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Validate provider
    if data.booking_provider not in VALID_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid provider. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}",
        )

    # Merge booking into workspace settings
    current_settings = workspace.settings or {}
    current_settings["booking"] = data.model_dump()
    workspace.settings = current_settings
    await db.commit()

    logger.info(
        "booking.updated",
        workspace_id=str(workspace_id),
        provider=data.booking_provider,
        enabled=data.booking_enabled,
    )

    return data.model_dump()
