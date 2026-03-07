"""Tests for LangChain RAG pipeline."""

import io
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.modules.rag.langchain_pipeline import LangChainRAGPipeline


@pytest.fixture
def mock_pinecone():
    """Mock Pinecone client."""
    with patch("app.modules.rag.langchain_pipeline.Pinecone") as mock_pc:
        pc_instance = MagicMock()
        mock_index = MagicMock()

        # Mock list_indexes
        mock_list = MagicMock()
        mock_list.names.return_value = ["existing-index"]
        pc_instance.list_indexes.return_value = mock_list

        # Mock index operations
        pc_instance.Index.return_value = mock_index
        mock_pc.return_value = pc_instance

        yield pc_instance, mock_index


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer."""
    with patch("app.modules.rag.langchain_pipeline.SentenceTransformer") as mock_st:
        model = MagicMock()
        model.encode.return_value = np.array([[0.1, 0.2, 0.3]])  # Mock embedding
        mock_st.return_value = model
        yield model


@pytest.fixture
def rag_pipeline(mock_pinecone, mock_sentence_transformer):
    """Create LangChainRAGPipeline instance with mocked dependencies."""
    pc_instance, mock_index = mock_pinecone

    pipeline = LangChainRAGPipeline(
        pinecone_api_key="test-key",
        pinecone_environment="us-east-1",
        index_name="existing-index",
    )

    return pipeline


class TestLangChainRAGPipeline:
    """Test LangChainRAGPipeline class."""

    def test_initialization_uses_existing_index(self, mock_pinecone, mock_sentence_transformer):
        """Test pipeline uses existing Pinecone index if available."""
        pc_instance, mock_index = mock_pinecone

        LangChainRAGPipeline(
            pinecone_api_key="test-key",
            index_name="existing-index",
        )

        pc_instance.create_index.assert_not_called()
        pc_instance.Index.assert_called_once_with("existing-index")

    def test_initialization_creates_new_index(self, mock_sentence_transformer):
        """Test pipeline creates new Pinecone index if doesn't exist."""
        with patch("app.modules.rag.langchain_pipeline.Pinecone") as mock_pc:
            pc_instance = MagicMock()
            mock_list = MagicMock()
            mock_list.names.return_value = []  # No existing indexes
            pc_instance.list_indexes.return_value = mock_list
            mock_pc.return_value = pc_instance

            LangChainRAGPipeline(
                pinecone_api_key="test-key",
                index_name="new-index",
            )

            pc_instance.create_index.assert_called_once()
            call_kwargs = pc_instance.create_index.call_args[1]
            assert call_kwargs["name"] == "new-index"
            assert call_kwargs["dimension"] == 384
            assert call_kwargs["metric"] == "cosine"

    async def test_ingest_pdf_document(self, rag_pipeline):
        """Test ingesting a PDF document."""
        pdf_content = b"%PDF-1.4 fake pdf content"

        with patch.object(rag_pipeline, "_parse_document", return_value="Extracted text"):
            with patch.object(rag_pipeline.text_splitter, "split_text") as mock_split:
                mock_split.return_value = ["chunk1", "chunk2"]

                # Mock embeddings (numpy arrays, matching sentence-transformers output)
                rag_pipeline.embed_model.encode.return_value = np.array(
                    [
                        [0.1, 0.2, 0.3],
                        [0.4, 0.5, 0.6],
                    ]
                )

                chunk_count = await rag_pipeline.ingest(
                    content=pdf_content,
                    filename="test.pdf",
                    kb_id="kb-123",
                    doc_id="doc-456",
                    metadata={"source": "upload"},
                )

                assert chunk_count == 2
                rag_pipeline.index.upsert.assert_called_once()

                # Verify vector structure
                call_args = rag_pipeline.index.upsert.call_args
                vectors = call_args[1]["vectors"]
                assert len(vectors) == 2
                assert vectors[0]["id"] == "doc-456_0"
                assert vectors[1]["id"] == "doc-456_1"
                assert vectors[0]["metadata"]["doc_id"] == "doc-456"
                assert vectors[0]["metadata"]["kb_id"] == "kb-123"
                assert vectors[0]["metadata"]["text"] == "chunk1"

    async def test_ingest_with_metadata(self, rag_pipeline):
        """Test ingesting document with custom metadata."""
        with patch.object(rag_pipeline, "_parse_document", return_value="Text"):
            with patch.object(rag_pipeline.text_splitter, "split_text") as mock_split:
                mock_split.return_value = ["chunk1"]
                rag_pipeline.embed_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])

                await rag_pipeline.ingest(
                    content=b"content",
                    filename="test.txt",
                    kb_id="kb-123",
                    doc_id="doc-456",
                    metadata={"author": "John Doe", "version": "1.0"},
                )

                call_args = rag_pipeline.index.upsert.call_args
                vectors = call_args[1]["vectors"]
                assert vectors[0]["metadata"]["author"] == "John Doe"
                assert vectors[0]["metadata"]["version"] == "1.0"

    async def test_retrieve_returns_relevant_chunks(self, rag_pipeline):
        """Test retrieve returns chunks above score threshold."""
        # Mock Pinecone query response
        mock_match1 = MagicMock()
        mock_match1.score = 0.85
        mock_match1.metadata = {
            "doc_id": "doc-123",
            "filename": "test.pdf",
            "text": "Relevant chunk 1",
            "page_number": 1,
        }

        mock_match2 = MagicMock()
        mock_match2.score = 0.75
        mock_match2.metadata = {
            "doc_id": "doc-123",
            "filename": "test.pdf",
            "text": "Relevant chunk 2",
        }

        mock_match3 = MagicMock()
        mock_match3.score = 0.65  # Below threshold
        mock_match3.metadata = {
            "doc_id": "doc-456",
            "filename": "other.pdf",
            "text": "Irrelevant chunk",
        }

        mock_results = MagicMock()
        mock_results.matches = [mock_match1, mock_match2, mock_match3]
        rag_pipeline.index.query.return_value = mock_results

        rag_pipeline.embed_model.encode.return_value = np.array([0.1, 0.2, 0.3])

        chunks = await rag_pipeline.retrieve(
            query="What is the return policy?",
            kb_id="kb-123",
            top_k=5,
            score_threshold=0.7,
        )

        assert len(chunks) == 2  # Only 2 above threshold
        assert chunks[0].doc_id == "doc-123"
        assert chunks[0].relevance_score == 0.85
        assert chunks[0].chunk_text == "Relevant chunk 1"
        assert chunks[0].page_number == 1
        assert chunks[1].relevance_score == 0.75

    async def test_retrieve_with_empty_results(self, rag_pipeline):
        """Test retrieve returns empty list when no matches found."""
        mock_results = MagicMock()
        mock_results.matches = []
        rag_pipeline.index.query.return_value = mock_results

        rag_pipeline.embed_model.encode.return_value = np.array([0.1, 0.2, 0.3])

        chunks = await rag_pipeline.retrieve(
            query="Nonexistent query",
            kb_id="kb-123",
        )

        assert len(chunks) == 0

    async def test_delete_removes_document_vectors(self, rag_pipeline):
        """Test delete removes all vectors for a document."""
        await rag_pipeline.delete(doc_id="doc-123", kb_id="kb-456")

        rag_pipeline.index.delete.assert_called_once_with(
            filter={"doc_id": {"$eq": "doc-123"}},
            namespace="kb-456",
        )

    async def test_cleanup_partial_vectors(self, rag_pipeline):
        """Test cleanup_partial_vectors calls delete."""
        with patch.object(rag_pipeline, "delete") as mock_delete:
            await rag_pipeline.cleanup_partial_vectors(
                doc_id="doc-123",
                kb_id="kb-456",
            )

            mock_delete.assert_called_once_with("doc-123", "kb-456")

    async def test_parse_pdf_extracts_text(self, rag_pipeline):
        """Test PDF parsing extracts text from all pages."""
        pdf_content = b"fake pdf bytes"

        with patch("app.modules.rag.langchain_pipeline.pdfplumber") as mock_pdf:
            mock_page1 = MagicMock()
            mock_page1.extract_text.return_value = "Page 1 text"
            mock_page2 = MagicMock()
            mock_page2.extract_text.return_value = "Page 2 text"

            mock_pdf_obj = MagicMock()
            mock_pdf_obj.pages = [mock_page1, mock_page2]
            mock_pdf_obj.__enter__ = MagicMock(return_value=mock_pdf_obj)
            mock_pdf_obj.__exit__ = MagicMock(return_value=None)
            mock_pdf.open.return_value = mock_pdf_obj

            text = await rag_pipeline._parse_pdf(pdf_content)

            assert "Page 1 text" in text
            assert "Page 2 text" in text

    async def test_parse_docx_extracts_paragraphs(self, rag_pipeline):
        """Test DOCX parsing extracts paragraph text."""
        docx_content = b"fake docx bytes"

        with patch("app.modules.rag.langchain_pipeline.DocxDocument") as mock_docx:
            mock_para1 = MagicMock()
            mock_para1.text = "Paragraph 1"
            mock_para2 = MagicMock()
            mock_para2.text = "Paragraph 2"
            mock_para3 = MagicMock()
            mock_para3.text = ""  # Empty paragraph should be skipped

            mock_doc = MagicMock()
            mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]
            mock_docx.return_value = mock_doc

            text = await rag_pipeline._parse_docx(docx_content)

            assert "Paragraph 1" in text
            assert "Paragraph 2" in text

    async def test_parse_document_detects_file_type(self, rag_pipeline):
        """Test _parse_document detects file type by extension."""
        with patch.object(rag_pipeline, "_parse_pdf") as mock_pdf:
            mock_pdf.return_value = "PDF text"
            result = await rag_pipeline._parse_document(b"content", "file.pdf")
            assert result == "PDF text"

        with patch.object(rag_pipeline, "_parse_docx") as mock_docx:
            mock_docx.return_value = "DOCX text"
            result = await rag_pipeline._parse_document(b"content", "file.docx")
            assert result == "DOCX text"

        # Plain text
        result = await rag_pipeline._parse_document(b"Plain text", "file.txt")
        assert result == "Plain text"

        result = await rag_pipeline._parse_document(b"Markdown", "file.md")
        assert result == "Markdown"

    async def test_parse_document_raises_on_unsupported_type(self, rag_pipeline):
        """Test _parse_document raises ValueError for unsupported file types."""
        with pytest.raises(ValueError, match="Unsupported file type"):
            await rag_pipeline._parse_document(b"content", "file.xyz")

    async def test_parse_document_handles_binary_io(self, rag_pipeline):
        """Test _parse_document converts BinaryIO to bytes."""
        file_like = io.BytesIO(b"Text content")

        result = await rag_pipeline._parse_document(file_like, "test.txt")

        assert result == "Text content"
