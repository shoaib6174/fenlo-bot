"""
Knowledge Gap Detection

Tracks unanswered questions to surface content gaps in the knowledge base.

Key Features:
- Logs queries when RAG retrieval returns no relevant results
- Semantic deduplication (threshold: 0.85) to group similar questions
- Occurrence counting for prioritization
- One-click "Add to Knowledge Base" workflow
- Workspace-scoped for multi-tenant isolation

Product Differentiator (from PRD D-01):
This feature helps business owners understand what their customers are asking
that the bot can't answer, enabling data-driven KB improvements.
"""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from sentence_transformers import SentenceTransformer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeGap


class KnowledgeGapDetector:
    """
    Detects and logs knowledge gaps with semantic deduplication.

    A knowledge gap is triggered when:
    1. RAG retrieval returns no chunks above threshold (score < 0.7)
    2. Bot response contains "I don't know" phrases

    Duplicate detection uses semantic similarity (embeddings) rather than
    string matching to group related questions:
    - "What is your return policy?" ≈ "What's your refund policy?" (same gap)
    - "What is your return policy?" ≠ "How do I return a broken item?" (different)
    """

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        similarity_threshold: float = 0.85,
    ):
        """
        Initialize knowledge gap detector.

        Args:
            embedding_model: HuggingFace model for semantic similarity
            similarity_threshold: Cosine similarity threshold for deduplication (0.0-1.0)
        """
        self.embed_model = SentenceTransformer(embedding_model)
        self.similarity_threshold = similarity_threshold

    async def log_gap(
        self,
        query: str,
        workspace_id: str,
        conversation_id: str | None,
        session: AsyncSession,
    ) -> KnowledgeGap | None:
        """
        Log a knowledge gap, deduplicating if similar query exists.

        Steps:
        1. Embed the query
        2. Find existing gaps for this workspace
        3. Check semantic similarity against each existing gap
        4. If match found (similarity >= threshold), increment occurrence count
        5. Otherwise, create new gap entry

        Args:
            query: User query that couldn't be answered
            workspace_id: Workspace identifier (for isolation)
            conversation_id: Optional conversation ID where gap occurred
            session: Database session

        Returns:
            The KnowledgeGap record (new or updated), or None if error
        """
        try:
            # Embed query (run in thread pool to avoid blocking)
            query_embedding = await asyncio.to_thread(
                self.embed_model.encode, query, show_progress_bar=False
            )

            # Find existing gaps for this workspace (only open ones)
            result = await session.execute(
                select(KnowledgeGap).where(
                    KnowledgeGap.workspace_id == workspace_id,
                    KnowledgeGap.status == "open",
                )
            )
            existing_gaps = result.scalars().all()

            # Check for semantic duplicates
            for gap in existing_gaps:
                if gap.query_embedding is None:
                    continue

                # Compute cosine similarity
                similarity = self._cosine_similarity(query_embedding, gap.query_embedding)

                if similarity >= self.similarity_threshold:
                    # Duplicate found — increment occurrence count
                    gap.occurrence_count += 1
                    gap.last_asked_at = datetime.now(UTC)

                    await session.commit()
                    return gap

            # No duplicate found — create new gap
            new_gap = KnowledgeGap(
                id=uuid4(),
                workspace_id=workspace_id,
                query_text=query,
                query_embedding=query_embedding.tolist(),
                occurrence_count=1,
                status="open",
                created_at=datetime.now(UTC),
                last_asked_at=datetime.now(UTC),
            )

            session.add(new_gap)
            await session.commit()
            await session.refresh(new_gap)
            return new_gap

        except Exception as e:
            # Log error but don't fail the chat flow
            print(f"[KnowledgeGapDetector] Error logging gap: {e}")
            return None

    async def mark_as_addressed(
        self,
        gap_id: str,
        workspace_id: str,
        user_id: str,
        session: AsyncSession,
    ) -> bool:
        """
        Mark a knowledge gap as addressed.

        This is called when:
        - Admin uploads a document to cover this gap
        - Admin manually dismisses the gap

        Args:
            gap_id: Knowledge gap identifier
            workspace_id: Workspace identifier (for security check)
            user_id: User who addressed the gap
            session: Database session

        Returns:
            True if successful, False otherwise
        """
        try:
            result = await session.execute(
                update(KnowledgeGap)
                .where(
                    KnowledgeGap.id == gap_id,
                    KnowledgeGap.workspace_id == workspace_id,
                )
                .values(
                    status="addressed",
                )
            )
            await session.commit()
            return result.rowcount > 0

        except Exception as e:
            print(f"[KnowledgeGapDetector] Error marking gap as addressed: {e}")
            return False

    async def get_top_gaps(
        self,
        workspace_id: str,
        session: AsyncSession,
        limit: int = 20,
    ) -> list[KnowledgeGap]:
        """
        Get top knowledge gaps ordered by occurrence count.

        Args:
            workspace_id: Workspace identifier
            session: Database session
            limit: Maximum number of gaps to return

        Returns:
            List of knowledge gaps, highest occurrence first
        """
        result = await session.execute(
            select(KnowledgeGap)
            .where(
                KnowledgeGap.workspace_id == workspace_id,
                KnowledgeGap.status == "open",
            )
            .order_by(KnowledgeGap.occurrence_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0.0-1.0, where 1.0 is identical)
        """
        import numpy as np

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)

        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0

        return float(dot_product / (norm_v1 * norm_v2))


def should_trigger_gap_detection(chunks: list, response: str) -> bool:
    """
    Determine if a knowledge gap should be logged.

    Triggers when:
    1. No relevant chunks retrieved (empty list or all below threshold)
    2. Bot response contains "I don't know" phrases

    Args:
        chunks: List of retrieved RAG chunks
        response: Bot's generated response

    Returns:
        True if gap should be logged
    """
    # Trigger 1: No relevant chunks
    if not chunks:
        return True

    # Trigger 2: Bot admits lack of knowledge
    dont_know_phrases = [
        "i don't know",
        "i'm not sure",
        "i don't have information",
        "i cannot answer",
        "i can't answer",
        "no information available",
        "unable to find",
    ]

    response_lower = response.lower()
    for phrase in dont_know_phrases:
        if phrase in response_lower:
            return True

    return False
