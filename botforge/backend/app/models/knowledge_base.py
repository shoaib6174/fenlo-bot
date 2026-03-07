"""Knowledge base and document models"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback if pgvector extension not installed yet
    Vector = None


class KnowledgeBase(Base):
    """Knowledge base containing documents"""

    __tablename__ = "knowledge_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    doc_count = Column(Integer, nullable=False, default=0)
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


class Document(Base):
    """Document in a knowledge base"""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("status IN ('processing', 'ready', 'failed')", name="ck_document_status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kb_id = Column(
        UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False
    )
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # application/pdf, text/plain, etc.
    file_size = Column(BigInteger, nullable=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="processing")  # processing, ready, failed
    metadata_ = Column("metadata", JSONB)  # {pages, author, etc.}
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    processed_at = Column(TIMESTAMP(timezone=True))


# Create index after table definition
Index("idx_documents_kb", Document.kb_id, Document.status)


class KnowledgeGap(Base):
    """Knowledge gap detection - questions without good answers"""

    __tablename__ = "knowledge_gaps"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'addressed', 'dismissed')", name="ck_knowledge_gap_status"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    query_text = Column(Text, nullable=False)
    query_embedding = Column(Vector(384) if Vector else JSONB)  # For semantic deduplication
    occurrence_count = Column(Integer, nullable=False, default=1)
    last_asked_at = Column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    status = Column(String(20), nullable=False, default="open")  # open, addressed, dismissed
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(UTC))


# Create index after table definition
Index(
    "idx_knowledge_gaps_workspace",
    KnowledgeGap.workspace_id,
    KnowledgeGap.status,
    KnowledgeGap.occurrence_count.desc(),
)
