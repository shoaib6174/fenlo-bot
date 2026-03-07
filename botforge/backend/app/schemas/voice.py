"""Voice module Pydantic schemas — Vapi integration, calls, escalation rules."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# --- Condition Schemas for Escalation Rules ---

CONDITION_SCHEMAS: dict[str, dict] = {
    "keyword": {
        "required": ["keywords"],
        "properties": {
            "keywords": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "match_mode": {"type": "string", "enum": ["any", "all"], "default": "any"},
        },
        "example": {"keywords": ["speak to human", "agent", "help"], "match_mode": "any"},
    },
    "sentiment": {
        "required": ["threshold"],
        "properties": {
            "threshold": {"type": "string", "enum": ["negative", "very_negative"]},
        },
        "example": {"threshold": "negative"},
    },
    "confidence": {
        "required": ["min_confidence"],
        "properties": {
            "min_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        },
        "example": {"min_confidence": 0.3},
    },
    "intent": {
        "required": ["intents"],
        "properties": {
            "intents": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
        "example": {"intents": ["cancel_subscription", "refund_request"]},
    },
    "business_hours": {
        "required": ["timezone", "start", "end"],
        "properties": {
            "timezone": {"type": "string"},
            "start": {"type": "string", "pattern": r"^[0-2][0-9]:[0-5][0-9]$"},
            "end": {"type": "string", "pattern": r"^[0-2][0-9]:[0-5][0-9]$"},
            "days": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0, "maximum": 6},
                "default": [0, 1, 2, 3, 4],
            },
        },
        "example": {
            "timezone": "America/New_York",
            "start": "09:00",
            "end": "17:00",
            "days": [0, 1, 2, 3, 4],
        },
    },
}

VALID_RULE_TYPES = set(CONDITION_SCHEMAS.keys())
VALID_ACTIONS = {"escalate", "notify", "log"}


def validate_condition(rule_type: str, condition: dict) -> None:
    """Validate condition dict against the schema for the given rule type.

    Raises ValueError with a descriptive message on validation failure.
    """
    schema = CONDITION_SCHEMAS.get(rule_type)
    if not schema:
        raise ValueError(
            f"Unknown rule_type '{rule_type}'. Valid types: {sorted(VALID_RULE_TYPES)}"
        )

    for req_field in schema.get("required", []):
        if req_field not in condition:
            raise ValueError(
                f"Condition for '{rule_type}' requires field '{req_field}'. "
                f"Example: {schema.get('example')}"
            )

    # Type-specific validation
    if rule_type == "keyword":
        kws = condition.get("keywords")
        if not isinstance(kws, list) or len(kws) == 0:
            raise ValueError("'keywords' must be a non-empty list of strings")
        if not all(isinstance(k, str) for k in kws):
            raise ValueError("All keywords must be strings")

    elif rule_type == "sentiment":
        threshold = condition.get("threshold")
        if threshold not in ("negative", "very_negative"):
            raise ValueError("'threshold' must be 'negative' or 'very_negative'")

    elif rule_type == "confidence":
        mc = condition.get("min_confidence")
        if not isinstance(mc, int | float) or not (0.0 <= mc <= 1.0):
            raise ValueError("'min_confidence' must be a number between 0.0 and 1.0")

    elif rule_type == "intent":
        intents = condition.get("intents")
        if not isinstance(intents, list) or len(intents) == 0:
            raise ValueError("'intents' must be a non-empty list of strings")

    elif rule_type == "business_hours":
        import re

        time_re = re.compile(r"^[0-2][0-9]:[0-5][0-9]$")
        for field in ("start", "end"):
            val = condition.get(field, "")
            if not time_re.match(val):
                raise ValueError(f"'{field}' must be in HH:MM format (e.g. '09:00')")
        tz = condition.get("timezone", "")
        if not isinstance(tz, str) or not tz:
            raise ValueError("'timezone' must be a non-empty string (e.g. 'America/New_York')")


# --- Voice Setup ---


class VoiceSetupRequest(BaseModel):
    """Request to set up voice (Vapi) for a workspace."""

    vapi_private_key: str = Field(..., min_length=1, description="Vapi private API key")
    vapi_public_key: str = Field(..., min_length=1, description="Vapi public key for web SDK")
    first_message: str = Field(
        "Hello! How can I help you today?",
        description="Assistant's first spoken message",
    )
    system_prompt: str | None = Field(
        None,
        description="Custom system prompt for the voice assistant",
    )


class VoiceConfigResponse(BaseModel):
    """Response for voice configuration status."""

    voice_enabled: bool
    assistant_id: str | None = None
    public_key: str | None = None
    first_message: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class VoiceConfigUpdate(BaseModel):
    """Request to update voice configuration."""

    first_message: str | None = None
    system_prompt: str | None = None
    voice_enabled: bool | None = None


# --- Call Logs ---


class CallLogResponse(BaseModel):
    """Response for a single call log entry."""

    id: UUID
    conversation_id: UUID
    direction: str
    phone_from: str
    phone_to: str
    duration_sec: int | None = None
    recording_url: str | None = None
    transcript: str | None = None
    summary: str | None = None
    sentiment: str | None = None
    actions_taken: list[dict[str, Any]] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CallListResponse(BaseModel):
    """Paginated list of call logs."""

    calls: list[CallLogResponse]
    total: int
    page: int
    page_size: int


class CallStatsResponse(BaseModel):
    """Aggregated call statistics."""

    total_calls: int = 0
    avg_duration_sec: float = 0.0
    escalation_rate: float = 0.0
    sentiment_distribution: dict[str, int] = Field(
        default_factory=lambda: {"positive": 0, "neutral": 0, "negative": 0}
    )


# --- Escalation Rules ---


class EscalationRuleCreate(BaseModel):
    """Request to create an escalation rule."""

    rule_type: str = Field(
        ..., description="Rule type: keyword, sentiment, confidence, intent, business_hours"
    )
    condition: dict[str, Any] = Field(
        ..., description="Condition config (schema depends on rule_type)"
    )
    action: str = Field("escalate", description="Action: escalate, notify, log")
    priority: int = Field(0, ge=0, le=100, description="Priority (0-100, higher wins)")
    is_active: bool = True

    @model_validator(mode="after")
    def validate_rule(self) -> "EscalationRuleCreate":
        if self.rule_type not in VALID_RULE_TYPES:
            raise ValueError(f"Invalid rule_type. Must be one of: {sorted(VALID_RULE_TYPES)}")
        if self.action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action. Must be one of: {sorted(VALID_ACTIONS)}")
        validate_condition(self.rule_type, self.condition)
        return self


class EscalationRuleUpdate(BaseModel):
    """Request to update an escalation rule."""

    rule_type: str | None = None
    condition: dict[str, Any] | None = None
    action: str | None = None
    priority: int | None = Field(None, ge=0, le=100)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_rule(self) -> "EscalationRuleUpdate":
        # Only validate if both rule_type and condition are provided (or one is being updated)
        if self.action is not None and self.action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action. Must be one of: {sorted(VALID_ACTIONS)}")
        if self.rule_type is not None and self.rule_type not in VALID_RULE_TYPES:
            raise ValueError(f"Invalid rule_type. Must be one of: {sorted(VALID_RULE_TYPES)}")
        if self.rule_type is not None and self.condition is not None:
            validate_condition(self.rule_type, self.condition)
        return self


class EscalationRuleResponse(BaseModel):
    """Response for an escalation rule."""

    id: UUID
    workspace_id: UUID
    rule_type: str
    condition: dict[str, Any]
    action: str
    is_active: bool
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Webhook Payloads ---


class WebhookPayload(BaseModel):
    """Parsed Vapi webhook payload."""

    message: dict[str, Any] = Field(..., description="Webhook message object from Vapi")

    @property
    def event_type(self) -> str:
        """Extract event type from message."""
        return self.message.get("type", "unknown")

    @property
    def call_id(self) -> str | None:
        """Extract call ID from message."""
        call = self.message.get("call", {})
        return call.get("id") or self.message.get("callId")

    @property
    def assistant_id(self) -> str | None:
        """Extract assistant ID for workspace resolution."""
        assistant = self.message.get("assistant", {})
        return assistant.get("id") or self.message.get("assistantId")

    @property
    def status(self) -> str | None:
        """Extract status from status-update events."""
        return self.message.get("status")

    @property
    def ended_reason(self) -> str | None:
        """Extract ended reason from end-of-call-report."""
        return self.message.get("endedReason")

    @property
    def transcript(self) -> str | None:
        """Extract transcript from end-of-call-report."""
        return self.message.get("transcript")

    @property
    def summary(self) -> str | None:
        """Extract summary from end-of-call-report."""
        return self.message.get("summary")

    @property
    def recording_url(self) -> str | None:
        """Extract recording URL from end-of-call-report."""
        return self.message.get("recordingUrl")

    @property
    def duration_sec(self) -> int | None:
        """Extract call duration in seconds."""
        start = self.message.get("startedAt")
        end = self.message.get("endedAt")
        if start and end:
            from datetime import datetime as dt

            try:
                s = dt.fromisoformat(start.replace("Z", "+00:00"))
                e = dt.fromisoformat(end.replace("Z", "+00:00"))
                return int((e - s).total_seconds())
            except (ValueError, TypeError):
                return None
        return None

    @property
    def analysis(self) -> dict[str, Any] | None:
        """Extract analysis data from end-of-call-report."""
        return self.message.get("analysis")

    @property
    def phone_number(self) -> dict[str, str | None]:
        """Extract phone numbers from call."""
        call = self.message.get("call", {})
        customer = call.get("customer", {})
        phone_number = call.get("phoneNumber", {})
        return {
            "from": customer.get("number", "web"),
            "to": phone_number.get("number", "assistant"),
        }

    @property
    def direction(self) -> str:
        """Determine call direction."""
        call = self.message.get("call", {})
        call_type = call.get("type", "")
        if call_type == "webCall":
            return "web"
        elif call_type == "inboundPhoneCall":
            return "inbound"
        elif call_type == "outboundPhoneCall":
            return "outbound"
        return "web"

    @property
    def timestamp(self) -> str | None:
        """Extract event timestamp."""
        return self.message.get("timestamp")

    @property
    def conversation_messages(self) -> list[dict[str, str]]:
        """Extract conversation messages from conversation-update events.

        Returns list of {role, content} dicts.
        """
        messages = self.message.get("messages") or self.message.get("artifact", {}).get(
            "messages", []
        )
        result = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content") or msg.get("message") or ""
            if content:
                result.append({"role": role, "content": content})
        return result
