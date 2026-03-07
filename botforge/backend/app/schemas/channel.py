"""Channel-related Pydantic schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChannelConfigWhatsApp(BaseModel):
    """JSONB schema for WhatsApp channel configuration (Twilio)"""

    phone_number: str
    template_messages: list[str] = []
    business_hours: dict | None = None

    class Config:
        extra = "allow"


class ChannelConfigWhatsAppMeta(BaseModel):
    """JSONB schema for WhatsApp channel configuration (Meta Cloud API)"""

    access_token: str
    phone_number_id: str
    app_secret: str
    verify_token: str = ""
    phone_number: str = ""  # Display phone number
    business_hours: dict | None = None

    class Config:
        extra = "allow"


class ContactInfo(BaseModel):
    """JSONB schema for conversation.contact_info column"""

    phone: str | None = None
    email: str | None = None
    name: str | None = None
    source: str | None = None

    class Config:
        extra = "allow"


# ========================
# Widget Channel Schemas (S50)
# ========================


class ChannelConfigWidget(BaseModel):
    """JSONB schema for Widget channel configuration (stored in ChannelConfig.config)."""

    colors: dict[str, str] = Field(
        default_factory=lambda: {"primary": "#007bff", "background": "#ffffff"},
        description="Widget color scheme",
    )
    position: str = Field(
        default="bottom-right",
        description="Widget position on page (bottom-right, bottom-left, top-right, top-left)",
        pattern="^(bottom-right|bottom-left|top-right|top-left)$",
    )
    greeting: str = Field(
        default="Hi! How can I help you today?", description="Initial greeting message"
    )
    allowed_domains: list[str] = Field(
        ...,
        description="List of allowed domains for CORS (e.g., ['example.com', '*.example.com'])",
        min_length=1,  # Must have at least one domain (Spec Panel Review R-01)
    )
    widget_id_hmac_salt: str = Field(
        ...,
        description="HMAC salt for widget WebSocket auth (server-side only, never returned to client)",
    )

    @field_validator("allowed_domains")
    @classmethod
    def validate_allowed_domains(cls, v: list[str]) -> list[str]:
        """Validate that allowed_domains is not empty."""
        if not v:
            raise ValueError("allowed_domains must contain at least one domain")
        return v

    class Config:
        extra = "forbid"  # Strict validation


# ========================
# General Channel Config Schemas (S50)
# ========================


class ChannelConfigCreate(BaseModel):
    """Request schema for creating a channel config."""

    channel: str = Field(
        ...,
        description="Channel type (widget, whatsapp, telegram, voice)",
        pattern="^(widget|whatsapp|telegram|voice)$",
    )
    config: dict = Field(
        ...,
        description="Channel-specific configuration (ChannelConfigWidget, ChannelConfigWhatsApp, etc.)",
    )
    is_active: bool = Field(default=True, description="Whether this channel is active")
    provider: str | None = Field(
        default=None, description="Provider for this channel (e.g. 'twilio', 'meta' for whatsapp)"
    )


class ChannelConfigUpdate(BaseModel):
    """Request schema for updating a channel config."""

    config: dict | None = Field(None, description="Channel-specific configuration")
    is_active: bool | None = Field(None, description="Whether this channel is active")
    provider: str | None = Field(
        default=None, description="Provider for this channel (e.g. 'twilio', 'meta' for whatsapp)"
    )


class ChannelConfigResponse(BaseModel):
    """Response schema for channel configs."""

    id: UUID
    workspace_id: UUID
    channel: str
    provider: str | None = None
    config: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


# ========================
# Widget Public Config Schemas (S50)
# ========================


class WidgetPublicConfigResponse(BaseModel):
    """Public config response for widget (no sensitive data)."""

    widget_id: UUID = Field(..., description="Widget ID (public identifier)")
    colors: dict[str, str] = Field(..., description="Widget color scheme")
    position: str = Field(..., description="Widget position on page")
    greeting: str = Field(..., description="Initial greeting message")
    widget_api_version: int = Field(default=1, description="API version for forward compatibility")
    hmac: str = Field(..., description="HMAC token for WebSocket auth (time-limited)")
    hmac_timestamp: int = Field(..., description="HMAC generation timestamp (Unix seconds)")


class WidgetErrorReport(BaseModel):
    """Schema for widget error reporting."""

    widget_id: UUID = Field(..., description="Widget ID")
    error_type: str = Field(
        ...,
        description="Error type",
        pattern="^(websocket_disconnect|render_error|api_error)$",
    )
    message: str = Field(..., description="Error message", max_length=1000)
    stack_trace: str | None = Field(None, description="Stack trace (optional)", max_length=5000)
    browser: str | None = Field(None, description="Browser info", max_length=200)
    url: str | None = Field(None, description="Page URL where error occurred", max_length=2000)
    timestamp: datetime = Field(..., description="Error timestamp (ISO 8601)")

    @field_validator("message", "stack_trace", "browser", "url")
    @classmethod
    def validate_max_payload_size(cls, v: str | None) -> str | None:
        """Validate that total payload doesn't exceed 10KB."""
        # Individual field validation (max_length) handles most of this
        # Total payload size is checked at endpoint level
        return v


# ========================
# Embed Code Schemas (S78)
# ========================


class EmbedCodeResponse(BaseModel):
    """Response schema for widget embed code generation."""

    html: str = Field(..., description="HTML snippet to embed on website")
    widget_id: str = Field(..., description="Widget ID")
    widget_url: str = Field(..., description="Widget script URL")
