"""
Branding & White-Label API — workspace customization for agency clients (S87).

Endpoints:
- GET  /api/v1/branding        — get branding settings
- PUT  /api/v1/branding        — update branding settings
- GET  /api/v1/branding/public — get public branding (no auth, for widget/preview)
"""

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.user import User
from app.models.workspace import Workspace

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/branding", tags=["branding"])

DEFAULT_BRANDING = {
    "brand_name": "BotForge",
    "logo_url": "",
    "favicon_url": "",
    "accent_color": "#2563eb",  # blue-600
    "hide_powered_by": False,
    "client_preview_mode": False,
}


# ========================
# Schemas
# ========================


class BrandingSettings(BaseModel):
    """Branding configuration for white-label mode."""

    brand_name: str = Field(default="BotForge", max_length=100)
    logo_url: str = Field(default="", max_length=500)
    favicon_url: str = Field(default="", max_length=500)
    accent_color: str = Field(default="#2563eb", max_length=20)
    hide_powered_by: bool = False
    client_preview_mode: bool = False


class BrandingResponse(BaseModel):
    """Response containing branding settings."""

    brand_name: str = "BotForge"
    logo_url: str = ""
    favicon_url: str = ""
    accent_color: str = "#2563eb"
    hide_powered_by: bool = False
    client_preview_mode: bool = False


class PublicBrandingResponse(BaseModel):
    """Public branding (safe to expose without auth)."""

    brand_name: str = "BotForge"
    logo_url: str = ""
    accent_color: str = "#2563eb"
    hide_powered_by: bool = False


# ========================
# Endpoints
# ========================


@router.get(
    "",
    response_model=BrandingResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def get_branding(
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get branding settings for the workspace.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    settings = workspace.settings or {}
    branding = settings.get("branding", {})

    return {**DEFAULT_BRANDING, **branding}


@router.put(
    "",
    response_model=BrandingResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def update_branding(
    data: BrandingSettings,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update branding settings for the workspace.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Merge branding into workspace settings
    current_settings = workspace.settings or {}
    current_settings["branding"] = data.model_dump()
    workspace.settings = current_settings
    await db.commit()

    logger.info(
        "branding.updated",
        workspace_id=str(workspace_id),
        brand_name=data.brand_name,
        preview_mode=data.client_preview_mode,
    )

    return data.model_dump()


@router.get(
    "/public",
    response_model=PublicBrandingResponse,
)
async def get_public_branding(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get public branding settings (no auth required).

    Used by widget and preview mode to apply branding without authentication.
    """
    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    settings = workspace.settings or {}
    branding = settings.get("branding", {})

    return {
        "brand_name": branding.get("brand_name", "BotForge"),
        "logo_url": branding.get("logo_url", ""),
        "accent_color": branding.get("accent_color", "#2563eb"),
        "hide_powered_by": branding.get("hide_powered_by", False),
    }
