"""Document schemas"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Schema for document response"""

    id: UUID
    kb_id: UUID
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str  # processing, ready, failed
    metadata_: dict | None
    created_at: datetime
    processed_at: datetime | None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Schema for document list response"""

    documents: list[DocumentResponse]
    total: int
