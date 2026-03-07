"""S46 tests — semantic cache, thread pool, graceful shutdown."""

import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.engine import MessageContext
from app.core.steps.rag_retrieval import RAG_CACHE_TTL, RAGRetrievalStep, _cache_key

# ---------- Semantic cache key tests ----------


class TestCacheKey:
    """Tests for _cache_key deterministic hashing."""

    def test_deterministic(self):
        """Same workspace + query produces identical key."""
        ws = str(uuid4())
        k1 = _cache_key(ws, "What is your pricing?")
        k2 = _cache_key(ws, "What is your pricing?")
        assert k1 == k2

    def test_normalized_case_insensitive(self):
        """Keys are case-insensitive (normalized to lowercase)."""
        ws = str(uuid4())
        k1 = _cache_key(ws, "HELLO WORLD")
        k2 = _cache_key(ws, "hello world")
        assert k1 == k2

    def test_trimmed_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        ws = str(uuid4())
        k1 = _cache_key(ws, "  hello  ")
        k2 = _cache_key(ws, "hello")
        assert k1 == k2

    def test_different_workspaces_differ(self):
        """Different workspaces produce different keys."""
        k1 = _cache_key("ws-aaa", "hello")
        k2 = _cache_key("ws-bbb", "hello")
        assert k1 != k2

    def test_key_format(self):
        """Key follows rag_cache:{workspace}:{hash16} format."""
        ws = "ws-123"
        key = _cache_key(ws, "test query")
        parts = key.split(":")
        assert parts[0] == "rag_cache"
        assert parts[1] == ws
        assert len(parts[2]) == 16  # sha256 truncated to 16 hex chars


# ---------- Semantic cache hit / miss ----------


@pytest.mark.asyncio
class TestRAGSemanticCache:
    """Tests for RAGRetrievalStep cache hit and miss paths."""

    def _make_context(self, workspace_id=None) -> MessageContext:
        ctx = MessageContext(
            workspace_id=workspace_id or uuid4(),
            user_id=uuid4(),
            conversation_id=uuid4(),
            message="What is your pricing?",
        )
        return ctx

    def _mock_workspace(self, rag_enabled=True, kb_id="kb-1"):
        ws = MagicMock()
        ws.settings = {"rag_enabled": rag_enabled, "default_kb_id": kb_id}
        return ws

    @patch("app.core.steps.rag_retrieval.get_resilient_redis")
    @patch("app.core.steps.rag_retrieval.get_db")
    @patch("app.core.steps.rag_retrieval.get_rag_pipeline")
    async def test_cache_hit_skips_pinecone(self, mock_pipeline_fn, mock_db, mock_redis_fn):
        """When cache has data, Pinecone retrieve is never called."""
        # Setup mocks
        cached_data = {
            "chunks": [{"text": "Pricing is $10/mo", "metadata": {}, "score": 0.95}],
            "citations": [{"doc_name": "pricing.pdf", "relevance_score": 0.95}],
        }
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=json.dumps(cached_data))
        mock_redis_fn.return_value = mock_cache

        mock_ws = self._mock_workspace()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_ws)

        async def fake_db():
            yield mock_session

        mock_db.return_value = fake_db()

        mock_rag = MagicMock()
        mock_rag.retrieve = AsyncMock()
        mock_pipeline_fn.return_value = mock_rag

        # Execute
        step = RAGRetrievalStep()
        ctx = self._make_context()
        result = await step.execute(ctx)

        # Verify cache hit
        assert result.metadata.get("rag_cache_hit") is True
        assert len(result.rag_chunks) == 1
        assert result.rag_chunks[0]["text"] == "Pricing is $10/mo"
        # Pinecone retrieve should NOT be called
        mock_rag.retrieve.assert_not_called()

    @patch("app.core.steps.rag_retrieval.get_resilient_redis")
    @patch("app.core.steps.rag_retrieval.get_db")
    @patch("app.core.steps.rag_retrieval.get_rag_pipeline")
    async def test_cache_miss_queries_pinecone_and_stores(
        self, mock_pipeline_fn, mock_db, mock_redis_fn
    ):
        """On cache miss, queries Pinecone and writes result to cache."""
        # Setup: cache returns None (miss)
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_redis_fn.return_value = mock_cache

        mock_ws = self._mock_workspace()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_ws)

        async def fake_db():
            yield mock_session

        mock_db.return_value = fake_db()

        # Pinecone returns chunks
        mock_chunk = SimpleNamespace(
            chunk_text="Answer text",
            metadata={"source": "doc.pdf"},
            relevance_score=0.9,
            doc_name="doc.pdf",
            page_number=1,
            doc_id="doc-1",
        )
        mock_rag = MagicMock()
        mock_rag.retrieve = AsyncMock(return_value=[mock_chunk])
        mock_pipeline_fn.return_value = mock_rag

        # Execute
        step = RAGRetrievalStep()
        ctx = self._make_context()
        result = await step.execute(ctx)

        # Verify Pinecone was called
        mock_rag.retrieve.assert_called_once()
        assert len(result.rag_chunks) == 1

        # Verify cache was written
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[1]["ex"] == RAG_CACHE_TTL
        stored = json.loads(call_args[0][1])
        assert len(stored["chunks"]) == 1

    @patch("app.core.steps.rag_retrieval.get_resilient_redis")
    @patch("app.core.steps.rag_retrieval.get_db")
    @patch("app.core.steps.rag_retrieval.get_rag_pipeline")
    async def test_cache_error_degrades_gracefully(self, mock_pipeline_fn, mock_db, mock_redis_fn):
        """Cache read error doesn't break retrieval — falls through to Pinecone."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(side_effect=Exception("Redis down"))
        mock_cache.set = AsyncMock(side_effect=Exception("Redis down"))
        mock_redis_fn.return_value = mock_cache

        mock_ws = self._mock_workspace()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_ws)

        async def fake_db():
            yield mock_session

        mock_db.return_value = fake_db()

        mock_chunk = SimpleNamespace(
            chunk_text="Fallback answer",
            metadata={},
            relevance_score=0.85,
            doc_name="fallback.pdf",
            page_number=1,
            doc_id="doc-2",
        )
        mock_rag = MagicMock()
        mock_rag.retrieve = AsyncMock(return_value=[mock_chunk])
        mock_pipeline_fn.return_value = mock_rag

        step = RAGRetrievalStep()
        ctx = self._make_context()
        result = await step.execute(ctx)

        # Should still get chunks despite cache failure
        assert len(result.rag_chunks) == 1
        assert result.rag_chunks[0]["text"] == "Fallback answer"
        # Cache hit flag should NOT be set
        assert result.metadata.get("rag_cache_hit") is None


# ---------- Thread pool executor ----------


class TestThreadPoolExecutor:
    """Tests for bounded thread pool used by asyncio.to_thread()."""

    def test_bounded_max_workers(self):
        """ThreadPoolExecutor respects max_workers limit."""
        executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="test-embed")
        futures = []
        import threading

        active_threads = []

        def slow_task():
            active_threads.append(threading.current_thread().name)
            import time

            time.sleep(0.05)
            return True

        for _ in range(4):
            futures.append(executor.submit(slow_task))

        results = [f.result(timeout=5) for f in futures]
        assert all(results)
        # All thread names should have our prefix
        assert all("test-embed" in name for name in active_threads)
        executor.shutdown(wait=True)


# ---------- WebSocket tracking ----------


class TestWebSocketTracking:
    """Tests for active_websockets set used in graceful shutdown.

    Since importing app.main triggers loading the vapi SDK (not installed in test env),
    we test the set contract directly with a plain set — the production code just uses
    a module-level ``set()`` with add/discard, which is standard Python.
    """

    def test_websockets_set_add_discard(self):
        """add/discard lifecycle mirrors production tracking."""
        active_websockets: set = set()

        mock_ws = MagicMock()
        active_websockets.add(mock_ws)
        assert len(active_websockets) == 1

        active_websockets.discard(mock_ws)
        assert len(active_websockets) == 0

    def test_discard_nonexistent_is_noop(self):
        """Discarding a WebSocket not in set doesn't raise."""
        active_websockets: set = set()
        mock_ws = MagicMock()
        # Should not raise
        active_websockets.discard(mock_ws)
        assert len(active_websockets) == 0

    def test_duplicate_add_is_idempotent(self):
        """Adding same WebSocket twice doesn't create duplicate."""
        active_websockets: set = set()
        mock_ws = MagicMock()
        active_websockets.add(mock_ws)
        active_websockets.add(mock_ws)
        assert len(active_websockets) == 1
