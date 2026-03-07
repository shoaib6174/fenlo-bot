"""RAG pipeline protocol and implementations.

Abstraction layer for RAG operations (ingest, retrieve, delete).
Isolates LangChain dependency behind a swappable interface.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import BinaryIO, Protocol


@dataclass
class Chunk:
    """Retrieved chunk with metadata"""

    doc_id: str
    doc_name: str
    chunk_text: str
    page_number: int | None
    relevance_score: float
    metadata: dict


class RAGPipeline(Protocol):
    """Protocol for RAG operations - vendor-agnostic interface"""

    async def ingest(
        self,
        content: bytes | BinaryIO,
        filename: str,
        kb_id: str,
        doc_id: str,
        metadata: dict | None = None,
    ) -> int:
        """Parse, chunk, embed, and store document.

        Args:
            content: Document bytes or file-like object (storage-agnostic)
            filename: Original filename for extension detection
            kb_id: Knowledge base ID (namespace)
            doc_id: Document ID for vector metadata
            metadata: Optional metadata to attach to chunks

        Returns:
            Number of chunks created
        """
        ...

    async def retrieve(
        self,
        query: str,
        kb_id: str,
        top_k: int = 5,
        score_threshold: float = 0.1,
    ) -> list[Chunk]:
        """Semantic search for relevant chunks.

        Args:
            query: User query text
            kb_id: Knowledge base ID (namespace)
            top_k: Maximum number of chunks to return
            score_threshold: Minimum relevance score (0.0-1.0)

        Returns:
            List of chunks ranked by relevance
        """
        ...

    async def delete(self, doc_id: str, kb_id: str) -> None:
        """Remove document vectors from store.

        Args:
            doc_id: Document ID
            kb_id: Knowledge base ID (namespace)
        """
        ...

    async def cleanup_partial_vectors(self, doc_id: str, kb_id: str) -> None:
        """Clean up partial vectors from failed ingestion.

        This is called before retry to ensure clean state.
        Default implementation delegates to delete().

        Args:
            doc_id: Document ID
            kb_id: Knowledge base ID (namespace)
        """
        ...


@lru_cache(maxsize=1)
def get_rag_pipeline() -> RAGPipeline | None:
    """
    Factory function to get RAG pipeline instance.

    Returns singleton instance to avoid reinitializing embedding models.
    Returns None if PINECONE_API_KEY is not configured.
    """
    from app.config import settings

    pinecone_key = settings.pinecone_api_key
    if not pinecone_key:
        return None

    from app.modules.rag.langchain_pipeline import LangChainRAGPipeline

    return LangChainRAGPipeline(
        pinecone_api_key=pinecone_key,
        pinecone_environment=settings.pinecone_environment or "us-east-1",
        index_name=settings.pinecone_index_name or "botforge-vectors",
    )
