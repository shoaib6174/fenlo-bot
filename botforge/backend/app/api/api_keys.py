"""
API Key Management — create, list, revoke, and update API keys (S86).

Endpoints:
- POST   /api/v1/api-keys       — create a new API key (returns raw key ONCE)
- GET    /api/v1/api-keys       — list all keys (prefix only, never full key)
- DELETE /api/v1/api-keys/{id}  — revoke a key
- PATCH  /api/v1/api-keys/{id}  — update name or scopes
"""

import hashlib
import secrets
from datetime import UTC, datetime
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
from app.models.api_key import APIKey
from app.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])

API_KEY_PREFIX = "bf_live_"  # pragma: allowlist secret
API_KEY_RANDOM_LENGTH = 24
VALID_SCOPES = {"read", "chat", "admin"}


# ========================
# Schemas
# ========================


class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""

    name: str = Field(..., min_length=1, max_length=255, description="Friendly name for the key")
    scopes: list[str] = Field(
        default=["read", "chat"],
        description="Access scopes: read, chat, admin",
    )
    rate_limit: int = Field(default=100, ge=1, le=1000, description="Requests per minute")


class CreateAPIKeyResponse(BaseModel):
    """Response after creating a key — includes the raw key (shown ONCE)."""

    id: str
    name: str
    key: str  # Full key — only returned on creation
    prefix: str
    scopes: list[str]
    rate_limit: int
    created_at: str


class APIKeyListItem(BaseModel):
    """API key summary for list view — never includes the full key."""

    id: str
    name: str
    prefix: str
    scopes: list[str]
    rate_limit: int
    is_revoked: bool
    last_used_at: str | None
    request_count: int
    created_at: str


class UpdateAPIKeyRequest(BaseModel):
    """Request to update an API key's name or scopes."""

    name: str | None = Field(None, min_length=1, max_length=255)
    scopes: list[str] | None = None


# ========================
# Endpoints
# ========================


@router.post(
    "",
    response_model=CreateAPIKeyResponse,
    status_code=201,
    dependencies=[Depends(require_role("admin"))],
)
async def create_api_key(
    data: CreateAPIKeyRequest,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a new API key for the workspace.

    The raw key is returned **only once** — copy it immediately.
    Subsequent requests will only show the prefix.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    # Validate scopes
    invalid_scopes = set(data.scopes) - VALID_SCOPES
    if invalid_scopes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scopes: {', '.join(invalid_scopes)}. Valid: {', '.join(VALID_SCOPES)}",
        )

    # Generate raw key: bf_live_ + 24 random hex chars
    raw_key = API_KEY_PREFIX + secrets.token_hex(API_KEY_RANDOM_LENGTH // 2)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    prefix = raw_key[:12] + "..."  # e.g. "bf_live_abc1..."

    api_key = APIKey(
        workspace_id=workspace_id,
        name=data.name,
        key_hash=key_hash,
        prefix=prefix,
        scopes=data.scopes,
        rate_limit=data.rate_limit,
    )
    db.add(api_key)
    await db.flush()

    logger.info(
        "api_key.created",
        workspace_id=str(workspace_id),
        key_id=str(api_key.id),
        name=data.name,
        scopes=data.scopes,
    )

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "key": raw_key,
        "prefix": prefix,
        "scopes": api_key.scopes,
        "rate_limit": api_key.rate_limit,
        "created_at": api_key.created_at.isoformat(),
    }


@router.get(
    "",
    response_model=list[APIKeyListItem],
    dependencies=[Depends(require_role("admin"))],
)
async def list_api_keys(
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    List all API keys for the workspace (prefix only, never the full key).

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = (
        select(APIKey).where(APIKey.workspace_id == workspace_id).order_by(APIKey.created_at.desc())
    )
    result = await db.execute(stmt)
    keys = result.scalars().all()

    return [
        {
            "id": str(k.id),
            "name": k.name,
            "prefix": k.prefix,
            "scopes": k.scopes,
            "rate_limit": k.rate_limit,
            "is_revoked": k.is_revoked,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "request_count": k.request_count,
            "created_at": k.created_at.isoformat(),
        }
        for k in keys
    ]


@router.delete(
    "/{key_id}",
    dependencies=[Depends(require_role("admin"))],
)
async def revoke_api_key(
    key_id: UUID,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Revoke an API key. The key will immediately stop working.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = select(APIKey).where(APIKey.id == key_id, APIKey.workspace_id == workspace_id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if api_key.is_revoked:
        raise HTTPException(status_code=400, detail="API key is already revoked")

    api_key.is_revoked = True
    api_key.revoked_at = datetime.now(UTC)

    logger.info(
        "api_key.revoked",
        workspace_id=str(workspace_id),
        key_id=str(key_id),
    )

    return {"message": "API key revoked"}


@router.patch(
    "/{key_id}",
    response_model=APIKeyListItem,
    dependencies=[Depends(require_role("admin"))],
)
async def update_api_key(
    key_id: UUID,
    data: UpdateAPIKeyRequest,
    user: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update an API key's name or scopes.

    **Required role**: admin
    """
    _, workspace_id, _ = user

    stmt = select(APIKey).where(APIKey.id == key_id, APIKey.workspace_id == workspace_id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if api_key.is_revoked:
        raise HTTPException(status_code=400, detail="Cannot update a revoked key")

    if data.name is not None:
        api_key.name = data.name
    if data.scopes is not None:
        invalid_scopes = set(data.scopes) - VALID_SCOPES
        if invalid_scopes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scopes: {', '.join(invalid_scopes)}",
            )
        api_key.scopes = data.scopes

    logger.info(
        "api_key.updated",
        workspace_id=str(workspace_id),
        key_id=str(key_id),
    )

    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "prefix": api_key.prefix,
        "scopes": api_key.scopes,
        "rate_limit": api_key.rate_limit,
        "is_revoked": api_key.is_revoked,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "request_count": api_key.request_count,
        "created_at": api_key.created_at.isoformat(),
    }
