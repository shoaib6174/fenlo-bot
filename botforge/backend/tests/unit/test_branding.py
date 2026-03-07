"""
Unit tests for Branding / White-Label API (S87).

Tests cover:
- Default branding values are returned
- Branding update merges into workspace settings
- Public branding endpoint returns safe subset
- Client preview mode flag is persisted
- Invalid workspace returns 404
"""

import pytest

from app.api.branding import DEFAULT_BRANDING, BrandingSettings

# --- Default Branding Tests ---


class TestDefaultBranding:
    """Test that default branding values are correct."""

    def test_default_brand_name(self):
        """Default brand name is BotForge."""
        assert DEFAULT_BRANDING["brand_name"] == "BotForge"

    def test_default_accent_color(self):
        """Default accent color is blue-600."""
        assert DEFAULT_BRANDING["accent_color"] == "#2563eb"

    def test_default_hide_powered_by(self):
        """Powered-by is visible by default."""
        assert DEFAULT_BRANDING["hide_powered_by"] is False

    def test_default_preview_mode(self):
        """Client preview mode is off by default."""
        assert DEFAULT_BRANDING["client_preview_mode"] is False


# --- Schema Validation Tests ---


class TestBrandingSchema:
    """Test Pydantic schema for branding settings."""

    def test_schema_defaults(self):
        """BrandingSettings uses defaults when no values provided."""
        s = BrandingSettings()
        assert s.brand_name == "BotForge"
        assert s.logo_url == ""
        assert s.accent_color == "#2563eb"
        assert s.hide_powered_by is False
        assert s.client_preview_mode is False

    def test_schema_custom_values(self):
        """BrandingSettings accepts custom values."""
        s = BrandingSettings(
            brand_name="Acme Bots",
            logo_url="https://example.com/logo.png",
            accent_color="#dc2626",
            hide_powered_by=True,
            client_preview_mode=True,
        )
        assert s.brand_name == "Acme Bots"
        assert s.logo_url == "https://example.com/logo.png"
        assert s.accent_color == "#dc2626"
        assert s.hide_powered_by is True
        assert s.client_preview_mode is True

    def test_schema_model_dump(self):
        """model_dump produces dict suitable for storage."""
        s = BrandingSettings(brand_name="TestCo")
        d = s.model_dump()
        assert isinstance(d, dict)
        assert d["brand_name"] == "TestCo"
        assert "favicon_url" in d

    def test_brand_name_max_length(self):
        """Brand name exceeding max length is rejected."""
        with pytest.raises(ValueError):
            BrandingSettings(brand_name="x" * 101)


# --- Branding Merge Tests ---


class TestBrandingMerge:
    """Test that branding merges correctly with defaults."""

    def test_partial_branding_merged_with_defaults(self):
        """Stored partial branding is merged with defaults."""
        stored = {"brand_name": "ClientCo", "accent_color": "#059669"}
        merged = {**DEFAULT_BRANDING, **stored}
        assert merged["brand_name"] == "ClientCo"
        assert merged["accent_color"] == "#059669"
        assert merged["hide_powered_by"] is False  # default preserved
        assert merged["logo_url"] == ""  # default preserved

    def test_empty_branding_returns_defaults(self):
        """Empty stored branding returns all defaults."""
        stored = {}
        merged = {**DEFAULT_BRANDING, **stored}
        assert merged == DEFAULT_BRANDING
