"""
Unit tests for Booking / Calendar Integration (S88).

Tests cover:
- BookingEnrichmentStep skips non-booking intents
- BookingEnrichmentStep adds booking_config when configured
- BookingEnrichmentStep skips when no URL configured
- BookingSettings schema validation
- Default booking values
"""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.api.booking import VALID_PROVIDERS, BookingSettings
from app.core.steps.booking import DEFAULT_BOOKING_PROMPT, BookingEnrichmentStep

# --- Schema Tests ---


class TestBookingSchema:
    """Test Pydantic schema for booking settings."""

    def test_schema_defaults(self):
        """BookingSettings uses defaults when no values provided."""
        s = BookingSettings()
        assert s.booking_provider == "custom_url"
        assert s.booking_url == ""
        assert s.booking_prompt == ""
        assert s.booking_enabled is False

    def test_schema_custom_values(self):
        """BookingSettings accepts custom values."""
        s = BookingSettings(
            booking_provider="calendly",
            booking_url="https://calendly.com/test/30min",
            booking_prompt="Book a call with us!",
            booking_enabled=True,
        )
        assert s.booking_provider == "calendly"
        assert s.booking_url == "https://calendly.com/test/30min"
        assert s.booking_prompt == "Book a call with us!"
        assert s.booking_enabled is True

    def test_valid_providers(self):
        """Valid providers set is complete."""
        assert "calendly" in VALID_PROVIDERS
        assert "cal_com" in VALID_PROVIDERS
        assert "google" in VALID_PROVIDERS
        assert "custom_url" in VALID_PROVIDERS


# --- Enrichment Step Tests ---


@dataclass
class FakeContext:
    workspace_id: Any = None
    intent: str | None = None
    metadata: dict = field(default_factory=dict)


class TestBookingEnrichmentStep:
    """Test the pipeline enrichment step."""

    @pytest.mark.asyncio
    async def test_skips_non_booking_intent(self):
        """Step does nothing when intent is not 'booking'."""
        mock_db = AsyncMock()
        step = BookingEnrichmentStep(mock_db)

        ctx = FakeContext(intent="faq")
        result = await step.execute(ctx)

        assert "booking_config" not in result.metadata
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_no_url_configured(self):
        """Step skips when workspace has no booking URL."""
        workspace = MagicMock()
        workspace.settings = {"booking": {"booking_provider": "calendly", "booking_url": ""}}

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = workspace

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        step = BookingEnrichmentStep(mock_db)
        ctx = FakeContext(workspace_id=uuid4(), intent="booking")
        result = await step.execute(ctx)

        assert "booking_config" not in result.metadata

    @pytest.mark.asyncio
    async def test_adds_booking_config_when_configured(self):
        """Step adds booking_config metadata when URL is set."""
        workspace = MagicMock()
        workspace.settings = {
            "booking": {
                "booking_provider": "calendly",
                "booking_url": "https://calendly.com/test/30min",
                "booking_prompt": "Schedule a call!",
            }
        }

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = workspace

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        step = BookingEnrichmentStep(mock_db)
        ctx = FakeContext(workspace_id=uuid4(), intent="booking")
        result = await step.execute(ctx)

        assert "booking_config" in result.metadata
        config = result.metadata["booking_config"]
        assert config["provider"] == "calendly"
        assert config["url"] == "https://calendly.com/test/30min"
        assert config["prompt"] == "Schedule a call!"

    @pytest.mark.asyncio
    async def test_uses_default_prompt_when_not_set(self):
        """Step uses default prompt when custom prompt is empty."""
        workspace = MagicMock()
        workspace.settings = {
            "booking": {
                "booking_provider": "custom_url",
                "booking_url": "https://booking.example.com",
            }
        }

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = workspace

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        step = BookingEnrichmentStep(mock_db)
        ctx = FakeContext(workspace_id=uuid4(), intent="booking")
        result = await step.execute(ctx)

        assert result.metadata["booking_config"]["prompt"] == DEFAULT_BOOKING_PROMPT

    @pytest.mark.asyncio
    async def test_handles_missing_workspace(self):
        """Step handles workspace not found gracefully."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result

        step = BookingEnrichmentStep(mock_db)
        ctx = FakeContext(workspace_id=uuid4(), intent="booking")
        result = await step.execute(ctx)

        assert "booking_config" not in result.metadata
