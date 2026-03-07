"""Tests for knowledge gap detection."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from app.models.knowledge_base import KnowledgeGap
from app.modules.rag.knowledge_gaps import (
    KnowledgeGapDetector,
    should_trigger_gap_detection,
)


@pytest.fixture
def gap_detector():
    """Create KnowledgeGapDetector instance."""
    with patch("sentence_transformers.SentenceTransformer"):
        detector = KnowledgeGapDetector(similarity_threshold=0.85)
        # Mock the embedding model
        detector.embed_model = MagicMock()
        detector.embed_model.encode = MagicMock(return_value=np.array([0.1, 0.2, 0.3, 0.4]))
        return detector


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    return session


class TestKnowledgeGapDetector:
    """Test KnowledgeGapDetector class."""

    async def test_log_gap_creates_new_gap(self, gap_detector, mock_session):
        """Test logging a new knowledge gap when no similar gaps exist."""
        # Mock database query returning no existing gaps
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        gap = await gap_detector.log_gap(
            query="What is your return policy?",
            workspace_id="ws-123",
            conversation_id="conv-456",
            session=mock_session,
        )

        assert gap is not None
        assert gap.query_text == "What is your return policy?"
        assert gap.workspace_id == "ws-123"
        assert gap.occurrence_count == 1
        assert gap.status == "open"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called()

    async def test_log_gap_deduplicates_similar_query(self, gap_detector, mock_session):
        """Test that similar queries increment existing gap occurrence count."""
        # Create existing gap with similar embedding
        existing_gap = KnowledgeGap(
            id=uuid4(),
            workspace_id="ws-123",
            query_text="What's your refund policy?",
            query_embedding=[0.11, 0.21, 0.31, 0.41],  # Very similar to new query
            occurrence_count=1,
            status="open",
            created_at=datetime.now(UTC),
            last_asked_at=datetime.now(UTC),
        )

        # Mock database query returning existing gap
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_gap]
        mock_session.execute.return_value = mock_result

        # Mock high similarity
        with patch.object(gap_detector, "_cosine_similarity", return_value=0.95):
            gap = await gap_detector.log_gap(
                query="What is your return policy?",
                workspace_id="ws-123",
                conversation_id="conv-456",
                session=mock_session,
            )

            assert gap.id == existing_gap.id
            assert gap.occurrence_count == 2  # Incremented
            mock_session.add.assert_not_called()  # No new gap created
            mock_session.commit.assert_called()

    async def test_log_gap_creates_new_when_below_threshold(self, gap_detector, mock_session):
        """Test that dissimilar queries create new gaps."""
        existing_gap = KnowledgeGap(
            id=uuid4(),
            workspace_id="ws-123",
            query_text="What's your refund policy?",
            query_embedding=[0.11, 0.21, 0.31, 0.41],
            occurrence_count=1,
            status="open",
            created_at=datetime.now(UTC),
            last_asked_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_gap]
        mock_session.execute.return_value = mock_result

        # Mock low similarity
        with patch.object(gap_detector, "_cosine_similarity", return_value=0.50):
            gap = await gap_detector.log_gap(
                query="How do I track my shipment?",
                workspace_id="ws-123",
                conversation_id="conv-456",
                session=mock_session,
            )

            assert gap.query_text == "How do I track my shipment?"
            mock_session.add.assert_called_once()  # New gap created

    async def test_log_gap_skips_gaps_with_no_embedding(self, gap_detector, mock_session):
        """Test that gaps without embeddings are skipped during similarity check."""
        gap_without_embedding = KnowledgeGap(
            id=uuid4(),
            workspace_id="ws-123",
            query_text="Some query",
            query_embedding=None,  # No embedding
            occurrence_count=1,
            status="open",
            created_at=datetime.now(UTC),
            last_asked_at=datetime.now(UTC),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [gap_without_embedding]
        mock_session.execute.return_value = mock_result

        gap = await gap_detector.log_gap(
            query="What is your return policy?",
            workspace_id="ws-123",
            conversation_id=None,
            session=mock_session,
        )

        # Should create new gap since existing has no embedding
        assert gap.query_text == "What is your return policy?"
        mock_session.add.assert_called_once()

    async def test_log_gap_handles_errors_gracefully(self, gap_detector, mock_session):
        """Test that log_gap returns None on error without crashing."""
        mock_session.execute.side_effect = Exception("Database error")

        gap = await gap_detector.log_gap(
            query="What is your return policy?",
            workspace_id="ws-123",
            conversation_id="conv-456",
            session=mock_session,
        )

        assert gap is None  # Should return None on error

    async def test_mark_as_addressed_success(self, gap_detector, mock_session):
        """Test marking a knowledge gap as addressed."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        success = await gap_detector.mark_as_addressed(
            gap_id="gap-123",
            workspace_id="ws-456",
            user_id="user-789",
            session=mock_session,
        )

        assert success is True
        mock_session.commit.assert_called_once()

    async def test_mark_as_addressed_not_found(self, gap_detector, mock_session):
        """Test marking non-existent gap returns False."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        success = await gap_detector.mark_as_addressed(
            gap_id="nonexistent",
            workspace_id="ws-456",
            user_id="user-789",
            session=mock_session,
        )

        assert success is False

    async def test_mark_as_addressed_handles_errors(self, gap_detector, mock_session):
        """Test that mark_as_addressed returns False on error."""
        mock_session.execute.side_effect = Exception("Database error")

        success = await gap_detector.mark_as_addressed(
            gap_id="gap-123",
            workspace_id="ws-456",
            user_id="user-789",
            session=mock_session,
        )

        assert success is False

    async def test_get_top_gaps(self, gap_detector, mock_session):
        """Test getting top knowledge gaps ordered by occurrence."""
        gaps = [
            KnowledgeGap(
                id=uuid4(),
                workspace_id="ws-123",
                query_text="Query 1",
                occurrence_count=10,
                status="open",
                created_at=datetime.now(UTC),
                last_asked_at=datetime.now(UTC),
            ),
            KnowledgeGap(
                id=uuid4(),
                workspace_id="ws-123",
                query_text="Query 2",
                occurrence_count=5,
                status="open",
                created_at=datetime.now(UTC),
                last_asked_at=datetime.now(UTC),
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = gaps
        mock_session.execute.return_value = mock_result

        result = await gap_detector.get_top_gaps(
            workspace_id="ws-123",
            session=mock_session,
            limit=20,
        )

        assert len(result) == 2
        assert result == gaps

    def test_cosine_similarity_identical_vectors(self, gap_detector):
        """Test cosine similarity returns 1.0 for identical vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        similarity = gap_detector._cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal_vectors(self, gap_detector):
        """Test cosine similarity returns 0.0 for orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        similarity = gap_detector._cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(0.0)

    def test_cosine_similarity_opposite_vectors(self, gap_detector):
        """Test cosine similarity returns -1.0 for opposite vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]

        similarity = gap_detector._cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(-1.0)

    def test_cosine_similarity_zero_vector(self, gap_detector):
        """Test cosine similarity returns 0.0 for zero vectors."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        similarity = gap_detector._cosine_similarity(vec1, vec2)

        assert similarity == 0.0


class TestGapDetectionTriggers:
    """Test should_trigger_gap_detection function."""

    def test_trigger_on_empty_chunks(self):
        """Test gap detection triggers when no chunks retrieved."""
        assert should_trigger_gap_detection([], "Some response") is True

    def test_trigger_on_dont_know_phrase(self):
        """Test gap detection triggers on 'I don't know' phrases."""
        response = "I don't know the answer to that question."
        assert should_trigger_gap_detection([{"text": "chunk"}], response) is True

    def test_trigger_on_not_sure_phrase(self):
        """Test gap detection triggers on 'I'm not sure' phrases."""
        response = "I'm not sure about that."
        assert should_trigger_gap_detection([{"text": "chunk"}], response) is True

    def test_trigger_on_no_information_phrase(self):
        """Test gap detection triggers on 'no information available'."""
        response = "No information available on that topic."
        assert should_trigger_gap_detection([{"text": "chunk"}], response) is True

    def test_trigger_on_cannot_answer_phrase(self):
        """Test gap detection triggers on 'I cannot answer'."""
        response = "I cannot answer that question."
        assert should_trigger_gap_detection([{"text": "chunk"}], response) is True

    def test_trigger_on_unable_to_find_phrase(self):
        """Test gap detection triggers on 'unable to find'."""
        response = "Unable to find information about that."
        assert should_trigger_gap_detection([{"text": "chunk"}], response) is True

    def test_no_trigger_on_valid_response(self):
        """Test gap detection does NOT trigger on valid response."""
        chunks = [{"text": "relevant chunk"}]
        response = "Here is the answer to your question."
        assert should_trigger_gap_detection(chunks, response) is False

    def test_trigger_case_insensitive(self):
        """Test gap detection is case-insensitive."""
        response = "I DON'T KNOW the answer."
        assert should_trigger_gap_detection([{"text": "chunk"}], response) is True
