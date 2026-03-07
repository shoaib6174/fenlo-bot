"""Knowledge Base schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    """Schema for creating a knowledge base"""

    name: str = Field(..., min_length=1, max_length=255, description="Knowledge base name")
    description: str | None = Field(None, description="Optional description")


class KnowledgeBaseUpdate(BaseModel):
    """Schema for updating a knowledge base"""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    """Schema for knowledge base response"""

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    doc_count: int
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeGapResponse(BaseModel):
    """Schema for knowledge gap response — maps backend 'open' to frontend 'active'"""

    id: UUID
    query_text: str
    occurrence_count: int
    first_asked_at: datetime
    last_asked_at: datetime
    status: str  # 'active', 'addressed', 'dismissed'
    kb_id: UUID | None = None
    workspace_id: UUID
