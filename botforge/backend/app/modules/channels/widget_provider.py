"""
Widget Channel Provider — Domain allowlist auth, HMAC verification, session continuity.

Widget conversations are anonymous (user_id=None) and scoped to workspace via widget_id.
Session continuity via localStorage session_id.
"""

import hashlib
import hmac
import time
from uuid import UUID

from app.models.channel import ChannelConfig
from app.modules.channels.provider import ChannelProvider, ChannelSendResult, InboundMessage


class WidgetProvider(ChannelProvider):
    """Widget channel provider with domain allowlist and HMAC auth."""

    async def send_message(
        self, conversation_id: UUID, message: str, config: ChannelConfig
    ) -> ChannelSendResult:
        """
        Widget messages are delivered via WebSocket push (not HTTP POST).
        This method is a no-op for widgets — responses are sent via the existing
        WebSocket connection in the widget WebSocket handler.

        Returns success=True with no provider_message_id since there's no external API call.
        """
        # Widget responses are pushed via WebSocket, not sent via external API
        # This method exists to satisfy the ChannelProvider protocol
        return ChannelSendResult(
            success=True, provider_message_id=None, error=None, should_retry=False
        )

    async def validate_config(self, config: dict) -> bool:
        """
        Validate widget configuration.

        Required fields:
        - allowed_domains: list[str] with at least one domain (enforced by ChannelConfigWidget schema)
        - widget_id_hmac_salt: str (non-empty)
        """
        if not isinstance(config, dict):
            return False

        # Check required fields
        allowed_domains = config.get("allowed_domains")
        if not isinstance(allowed_domains, list) or len(allowed_domains) == 0:
            return False

        widget_id_hmac_salt = config.get("widget_id_hmac_salt")
        if not isinstance(widget_id_hmac_salt, str) or not widget_id_hmac_salt.strip():
            return False

        return True

    async def process_inbound(self, payload: dict, config: ChannelConfig) -> InboundMessage:
        """
        Process inbound widget message from WebSocket.

        Payload structure:
        {
            "type": "message",
            "content": "Hello",
            "session_id": "uuid-or-null",
            "message_id": "uuid"  # Client-generated for idempotency
        }

        Returns InboundMessage with:
        - content: message text
        - sender_id: session_id (or generated if null)
        - provider_message_id: message_id from client (for idempotency)
        - metadata: empty dict (widget has no additional metadata like media)
        """
        if not isinstance(payload, dict):
            raise ValueError("Invalid payload: must be a dict")

        # Extract required fields
        content = payload.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Invalid payload: 'content' must be a non-empty string")

        # Session ID for sender identification
        session_id = payload.get("session_id")
        if session_id is None:
            # New session — generate a UUID
            from uuid import uuid4

            session_id = str(uuid4())

        # Message ID for idempotency
        message_id = payload.get("message_id")
        if not message_id:
            raise ValueError("Invalid payload: 'message_id' is required")

        return InboundMessage(
            content=content.strip(),
            sender_id=str(session_id),
            provider_message_id=str(message_id),
            metadata={},
        )

    async def format_message(self, content: str, config: dict) -> str:
        """
        Format message for widget delivery.

        Widget supports plain text and Markdown. No special formatting needed
        (frontend widget.js handles Markdown rendering).
        """
        return content

    # --- Widget-Specific Methods (not in ChannelProvider Protocol) ---

    def validate_domain(self, origin: str, allowed_domains: list[str]) -> bool:
        """
        Validate Origin header against allowed_domains list.

        Domain Matching Rules (Spec Panel Review M-04):
        - Bare domain "example.com" matches ONLY https://example.com (not subdomains)
        - Wildcard "*.example.com" matches any subdomain (e.g., https://app.example.com)
          but NOT bare https://example.com
        - To allow both, list both: ["example.com", "*.example.com"]
        - localhost and 127.0.0.1 are NOT implicitly allowed — must be explicitly listed
        - Matching is case-insensitive
        - Port is included in the match when present in the Origin

        Args:
            origin: Origin header value (e.g., "https://example.com", "https://app.example.com:8080")
            allowed_domains: List of allowed domains (bare or wildcard)

        Returns:
            True if origin is allowed, False otherwise
        """
        if not origin or not allowed_domains:
            return False

        # Parse origin to extract hostname:port
        # Origin format: <scheme>://<host>[:<port>]
        try:
            # Remove scheme
            if "://" in origin:
                origin = origin.split("://", 1)[1]
            else:
                # Invalid origin (no scheme)
                return False

            # Extract hostname (may include port)
            origin_host = origin.split("/")[0].lower()  # Case-insensitive

            # Check against each allowed domain
            for allowed in allowed_domains:
                allowed = allowed.lower()  # Case-insensitive

                if allowed.startswith("*."):
                    # Wildcard subdomain match
                    # "*.example.com" matches "app.example.com" but NOT "example.com"
                    base_domain = allowed[2:]  # Remove "*."

                    # Extract hostname without port for subdomain matching
                    origin_hostname = origin_host.split(":")[0]

                    # Check if origin is a subdomain of the base domain
                    if origin_hostname.endswith("." + base_domain):
                        return True
                    # Explicitly reject bare domain for wildcard match
                    # (origin_hostname == base_domain is NOT allowed for "*.example.com")
                else:
                    # Bare domain match (exact match with optional port)
                    # "example.com" matches "example.com" or "example.com:8080"
                    if origin_host == allowed or origin_host.startswith(allowed + ":"):
                        return True

            return False

        except Exception:
            # Malformed origin
            return False

    def generate_hmac(self, widget_id: str, hmac_salt: str) -> tuple[str, int]:
        """
        Generate time-limited HMAC for widget WebSocket auth.

        HMAC = HMAC-SHA256(widget_id_hmac_salt, widget_id + ":" + timestamp)
        TTL: 5 minutes (prevents replay attacks beyond this window)

        Args:
            widget_id: Widget UUID as string
            hmac_salt: Secret salt from ChannelConfig.config.widget_id_hmac_salt

        Returns:
            Tuple of (hmac_hex, timestamp_unix_seconds)
        """
        timestamp = int(time.time())
        message = f"{widget_id}:{timestamp}"

        hmac_obj = hmac.new(
            key=hmac_salt.encode("utf-8"),
            msg=message.encode("utf-8"),
            digestmod=hashlib.sha256,
        )

        return hmac_obj.hexdigest(), timestamp

    def validate_hmac(
        self, widget_id: str, hmac_value: str, hmac_timestamp: int, hmac_salt: str
    ) -> bool:
        """
        Validate HMAC for widget WebSocket auth.

        Checks:
        1. HMAC matches the expected value for widget_id + timestamp
        2. Timestamp is within 5 minutes of server time (TTL)

        Args:
            widget_id: Widget UUID as string
            hmac_value: HMAC hex string from client
            hmac_timestamp: Timestamp (Unix seconds) from client
            hmac_salt: Secret salt from ChannelConfig.config.widget_id_hmac_salt

        Returns:
            True if HMAC is valid and not expired, False otherwise
        """
        # Check HMAC expiry (5 minutes = 300 seconds)
        current_time = int(time.time())
        if abs(current_time - hmac_timestamp) > 300:
            return False

        # Recompute expected HMAC
        message = f"{widget_id}:{hmac_timestamp}"
        expected_hmac = hmac.new(
            key=hmac_salt.encode("utf-8"),
            msg=message.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_hmac, hmac_value)
