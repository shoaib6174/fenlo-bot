"""Workspace-related Pydantic schemas"""

from pydantic import BaseModel


class WorkspaceSettings(BaseModel):
    """JSONB schema for workspace.settings column"""

    system_prompt: str = ""
    bot_name: str = "Assistant"
    personality: str = "professional"
    rag_enabled: bool = True
    knowledge_base_id: str | None = None
    greeting: str = "Hello! How can I help you?"
    fallback_response: str = "I don't have that information."
    forbidden_topics: list[str] = []

    class Config:
        extra = "allow"  # Allow additional fields for future extension
