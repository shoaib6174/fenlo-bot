"""
Channel Configuration CRUD API — Admin-only, workspace-scoped.

Manages channel configs for Widget, WhatsApp, Telegram, Voice.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import settings
from app.dependencies import get_db
from app.middleware.rbac import require_role
from app.models.channel import ChannelConfig
from app.models.user import User
from app.modules.channels.telegram_provider import TelegramProvider
from app.modules.channels.widget_provider import WidgetProvider
from app.schemas.channel import (
    ChannelConfigCreate,
    ChannelConfigResponse,
    ChannelConfigUpdate,
    EmbedCodeResponse,
)

router = APIRouter(prefix="/api/v1/channels", tags=["channels"])


@router.post(
    "",
    response_model=ChannelConfigResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
async def create_channel_config(
    data: ChannelConfigCreate,
    user_workspace_role: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChannelConfigResponse:
    """
    Create a new channel configuration.

    Requires admin role. Channel type determines which config schema to validate.
    """
    _, workspace_id, _ = user_workspace_role

    # Validate channel-specific config based on channel type
    if data.channel == "widget":
        widget_provider = WidgetProvider()
        if not await widget_provider.validate_config(data.config):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid widget configuration",
            )
    elif data.channel == "telegram":
        telegram_provider = TelegramProvider()
        if not await telegram_provider.validate_config(data.config):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Telegram configuration: bot token validation failed",
            )

    # Create channel config
    channel_config = ChannelConfig(
        workspace_id=workspace_id,
        channel=data.channel,
        provider=data.provider,
        config=data.config,
        is_active=data.is_active,
    )

    db.add(channel_config)
    await db.commit()
    await db.refresh(channel_config)

    return ChannelConfigResponse.model_validate(channel_config)


@router.get("", response_model=list[ChannelConfigResponse])
async def list_channel_configs(
    user_workspace_role: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChannelConfigResponse]:
    """
    List all channel configurations for the current workspace.

    Accessible by both admin and member roles.
    """
    _, workspace_id, _ = user_workspace_role

    stmt = (
        select(ChannelConfig)
        .where(ChannelConfig.workspace_id == workspace_id)
        .order_by(ChannelConfig.created_at.desc())
    )

    result = await db.execute(stmt)
    configs = result.scalars().all()

    return [ChannelConfigResponse.model_validate(c) for c in configs]


@router.get("/{config_id}", response_model=ChannelConfigResponse)
async def get_channel_config(
    config_id: UUID,
    user_workspace_role: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChannelConfigResponse:
    """
    Get a specific channel configuration by ID.

    Workspace-scoped — can only access configs in current workspace.
    """
    _, workspace_id, _ = user_workspace_role

    stmt = select(ChannelConfig).where(
        ChannelConfig.id == config_id, ChannelConfig.workspace_id == workspace_id
    )

    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )

    return ChannelConfigResponse.model_validate(config)


@router.put(
    "/{config_id}",
    response_model=ChannelConfigResponse,
    dependencies=[Depends(require_role("admin"))],
)
async def update_channel_config(
    config_id: UUID,
    data: ChannelConfigUpdate,
    user_workspace_role: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChannelConfigResponse:
    """
    Update a channel configuration.

    Requires admin role. Partial updates supported (only provided fields are updated).
    """
    _, workspace_id, _ = user_workspace_role

    # Fetch existing config
    stmt = select(ChannelConfig).where(
        ChannelConfig.id == config_id, ChannelConfig.workspace_id == workspace_id
    )

    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )

    # Update fields
    if data.config is not None:
        # Validate new config if it's a widget or telegram
        if config.channel == "widget":
            widget_provider = WidgetProvider()
            if not await widget_provider.validate_config(data.config):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid widget configuration",
                )
        elif config.channel == "telegram":
            telegram_provider = TelegramProvider()
            if not await telegram_provider.validate_config(data.config):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Telegram configuration: bot token validation failed",
                )
        config.config = data.config

    if data.is_active is not None:
        config.is_active = data.is_active

    if data.provider is not None:
        config.provider = data.provider

    await db.commit()
    await db.refresh(config)

    return ChannelConfigResponse.model_validate(config)


@router.delete(
    "/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("admin"))],
)
async def delete_channel_config(
    config_id: UUID,
    user_workspace_role: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete (deactivate) a channel configuration.

    Requires admin role. Soft delete: sets is_active=False instead of deleting the row.
    """
    _, workspace_id, _ = user_workspace_role

    # Fetch existing config
    stmt = select(ChannelConfig).where(
        ChannelConfig.id == config_id, ChannelConfig.workspace_id == workspace_id
    )

    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )

    # Soft delete — deactivate instead of removing
    config.is_active = False
    await db.commit()


@router.get("/{config_id}/embed-code", response_model=EmbedCodeResponse)
async def get_embed_code(
    config_id: UUID,
    user_workspace_role: tuple[User, UUID, str] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EmbedCodeResponse:
    """
    Generate embeddable widget code for a channel configuration.

    Returns HTML snippet with HMAC-signed widget_id for secure widget loading.
    Only supports widget channel type.
    """
    _, workspace_id, _ = user_workspace_role

    # Fetch channel config
    stmt = select(ChannelConfig).where(
        ChannelConfig.id == config_id, ChannelConfig.workspace_id == workspace_id
    )

    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel configuration not found",
        )

    # Only widget channels support embed code
    if config.channel != "widget":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Embed code not supported for channel type: {config.channel}",
        )

    # Generate HMAC for widget_id
    widget_provider = WidgetProvider()
    hmac_salt = config.config.get("widget_id_hmac_salt", "")
    hmac_value, hmac_timestamp = widget_provider.generate_hmac(str(config.id), hmac_salt)

    # Build widget script URL (use configured frontend URL)
    widget_url = f"{settings.frontend_url}/widget.js"

    # Generate HTML snippet
    html_snippet = f"""<script
  src="{widget_url}"
  data-widget-id="{config.id}"
  data-hmac="{hmac_value}"
  data-timestamp="{hmac_timestamp}"
  data-theme="light"
  data-position="bottom-right"
></script>"""

    return EmbedCodeResponse(
        html=html_snippet,
        widget_id=str(config.id),
        widget_url=widget_url,
    )
