"""Pydantic schemas for API and JSONB validation"""

from app.schemas.channel import ChannelConfigWhatsApp, ContactInfo
from app.schemas.workspace import WorkspaceSettings

__all__ = [
    "WorkspaceSettings",
    "ChannelConfigWhatsApp",
    "ContactInfo",
]
