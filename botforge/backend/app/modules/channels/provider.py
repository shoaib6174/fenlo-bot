"""
Channel Provider Protocol — Abstract interface for multi-channel support.

All channel implementations (Widget, Twilio WhatsApp, future Telegram)
implement this Protocol. This ensures consistent behavior across channels
and allows the system to handle messages from any source uniformly.
"""

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.models.channel import ChannelConfig


@dataclass
class ChannelSendResult:
    """
    Typed result from channel message delivery (S49 Spec Panel Review A-01).

    Used by send_message() to communicate delivery status and guide retry logic.
    """

    success: bool
    provider_message_id: str | None = None  # Provider's message ID (for tracking)
    error: str | None = None  # Error message if delivery failed
    should_retry: bool = False  # True → queue in webhook outbox for retry


@dataclass
class InboundMessage:
    """
    Typed result from inbound message processing (S49 Spec Panel v2 Review A-01).

    Replaces untyped dict return from process_inbound(). Provides consistent
    structure for messages from any channel (widget, WhatsApp, Telegram, etc.).
    """

    content: str  # Message text content
    sender_id: str  # Channel-specific sender ID (phone number, session_id, etc.)
    provider_message_id: str  # Provider's message ID (Twilio MessageSid, widget msg UUID)
    metadata: dict = field(
        default_factory=dict
    )  # Channel-specific extras (e.g., media URLs, contact info)


class ChannelProvider(Protocol):
    """
    Abstract interface for channel implementations.

    All channel providers (Widget, TwilioWhatsApp, future Telegram) implement
    this Protocol. The Protocol pattern provides interface enforcement without
    requiring inheritance, allowing flexibility in implementation.

    **Design Notes**:
    - Widget provider: session_id as sender_id, localStorage-based continuity
    - Twilio provider: phone number as sender_id, MessageSid for idempotency
    - Future Telegram provider: chat_id as sender_id, message_id for idempotency
    """

    async def send_message(
        self, conversation_id: UUID, message: str, config: ChannelConfig
    ) -> ChannelSendResult:
        """
        Send a message through this channel.

        Args:
            conversation_id: BotForge conversation ID
            message: Message content to send
            config: Channel configuration (contains credentials, settings)

        Returns:
            ChannelSendResult with success status and optional provider message ID

        Raises:
            No exceptions — errors are returned in ChannelSendResult.error
        """
        ...

    async def validate_config(self, config: dict) -> bool:
        """
        Validate channel-specific configuration.

        Args:
            config: Channel config dict to validate

        Returns:
            True if config is valid, False otherwise

        Example for Widget:
            config = {
                "colors": {"primary": "#007bff"},
                "position": "bottom-right",
                "greeting": "Hi! How can I help?",
                "allowed_domains": ["example.com"]
            }
        """
        ...

    async def process_inbound(self, payload: dict, config: ChannelConfig) -> InboundMessage:
        """
        Process an inbound message from this channel.

        Args:
            payload: Raw payload from channel (Twilio webhook, widget WebSocket message)
            config: Channel configuration

        Returns:
            InboundMessage with extracted content and sender info

        Raises:
            ValueError: If payload is malformed or missing required fields
        """
        ...

    async def format_message(self, content: str, config: dict) -> str:
        """
        Format outbound message for this channel.

        Allows channel-specific formatting (e.g., WhatsApp template variables,
        widget markdown, Telegram HTML). Async to support future DB-backed
        template rendering.

        Args:
            content: Raw message content
            config: Channel config (may contain formatting preferences)

        Returns:
            Formatted message string

        Example:
            Widget: Markdown → HTML
            WhatsApp: Template variables → actual values
            Telegram: Markdown → Telegram HTML
        """
        ...
