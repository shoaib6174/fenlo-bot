"""Unit tests for JSONB schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.channel import ChannelConfigWhatsApp, ContactInfo
from app.schemas.workspace import WorkspaceSettings


class TestJSONBValidation:
    """Test JSONB field validation with Pydantic schemas."""

    def test_workspace_settings_validates(self):
        """Test that valid workspace settings pass validation."""
        settings = WorkspaceSettings(
            system_prompt="You are a helpful assistant",
            bot_name="BotForge Assistant",
            personality="professional",
            rag_enabled=True,
            knowledge_base_id="kb-123",
            greeting="Hello! How can I help you?",
            fallback_response="I don't have that information.",
            forbidden_topics=["politics", "religion"],
        )

        assert settings.system_prompt == "You are a helpful assistant"
        assert settings.bot_name == "BotForge Assistant"
        assert settings.rag_enabled is True
        assert len(settings.forbidden_topics) == 2

    def test_workspace_settings_rejects_invalid(self):
        """Test that invalid workspace settings fail validation."""
        with pytest.raises(ValidationError):
            WorkspaceSettings(
                rag_enabled="not-a-boolean",  # Should be bool
                forbidden_topics="not-a-list",  # Should be list
            )

    def test_workspace_settings_defaults(self):
        """Test that workspace settings have proper defaults."""
        settings = WorkspaceSettings()

        assert settings.bot_name == "Assistant"
        assert settings.personality == "professional"
        assert settings.rag_enabled is True
        assert settings.greeting == "Hello! How can I help you?"
        assert isinstance(settings.forbidden_topics, list)

    def test_channel_config_validates(self):
        """Test that valid channel config passes validation."""
        config = ChannelConfigWhatsApp(
            phone_number="+1234567890",
            template_messages=["Welcome!", "Thank you!"],
            business_hours={
                "monday": {"open": "09:00", "close": "17:00"},
                "tuesday": {"open": "09:00", "close": "17:00"},
            },
        )

        assert config.phone_number == "+1234567890"
        assert len(config.template_messages) == 2
        assert "monday" in config.business_hours

    def test_channel_config_defaults(self):
        """Test that channel config has proper defaults."""
        config = ChannelConfigWhatsApp(phone_number="+1234567890")

        assert config.template_messages == []
        assert config.business_hours is None

    def test_contact_info_validates(self):
        """Test that valid contact info passes validation."""
        contact = ContactInfo(
            phone="+1234567890", email="user@example.com", name="John Doe", source="web"
        )

        assert contact.phone == "+1234567890"
        assert contact.email == "user@example.com"
        assert contact.name == "John Doe"

    def test_contact_info_optional_fields(self):
        """Test that contact info fields are optional."""
        contact = ContactInfo()

        assert contact.phone is None
        assert contact.email is None
        assert contact.name is None
        assert contact.source is None

    def test_contact_info_partial(self):
        """Test that contact info accepts partial data."""
        contact = ContactInfo(email="user@example.com")

        assert contact.email == "user@example.com"
        assert contact.phone is None
        assert contact.name is None
