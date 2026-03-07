"""LangChain-based RAG pipeline implementation."""

import asyncio
import io
import os
from typing import BinaryIO

import pdfplumber
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

from app.modules.rag.pipeline import Chunk


class LangChainRAGPipeline:
    """LangChain + Pinecone + sentence-transformers RAG implementation"""

    def __init__(
        self,
        pinecone_api_key: str,
        pinecone_environment: str = "us-east-1",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        index_name: str = "botforge-vectors",
    ):
        """Initialize RAG pipeline.

        Args:
            pinecone_api_key: Pinecone API key
            pinecone_environment: Pinecone environment/region
            embedding_model: HuggingFace model for embeddings
            index_name: Pinecone index name
        """
        self.pc = Pinecone(api_key=pinecone_api_key)
        self.index_name = index_name
        self.embedding_model_name = embedding_model

        # Initialize embedding model (runs on CPU)
        self.embed_model = SentenceTransformer(embedding_model)

        # Create index if it doesn't exist
        if index_name not in self.pc.list_indexes().names():
            self.pc.create_index(
                name=index_name,
                dimension=384,  # all-MiniLM-L6-v2 dimension
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=pinecone_environment),
            )

        self.index = self.pc.Index(index_name)

        # Text splitter configuration
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
        )

    async def ingest(
        self,
        content: bytes | BinaryIO,
        filename: str,
        kb_id: str,
        doc_id: str,
        metadata: dict | None = None,
    ) -> int:
        """Parse, chunk, embed, and store document."""
        # Parse document based on file type
        text = await self._parse_document(content, filename)

        # Split into chunks
        chunks = self.text_splitter.split_text(text)

        # Generate embeddings (run in thread pool to avoid blocking)
        embeddings = await asyncio.to_thread(
            self.embed_model.encode, chunks, show_progress_bar=False
        )

        # Prepare vectors for Pinecone
        vectors = []
        base_metadata = metadata or {}
        base_metadata.update(
            {
                "doc_id": doc_id,
                "kb_id": kb_id,
                "filename": filename,
            }
        )

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
            vector_id = f"{doc_id}_{i}"
            chunk_metadata = base_metadata.copy()
            chunk_metadata.update(
                {
                    "chunk_index": i,
                    "text": chunk,
                }
            )
            vectors.append(
                {
                    "id": vector_id,
                    "values": embedding.tolist(),
                    "metadata": chunk_metadata,
                }
            )

        # Upsert to Pinecone (namespace = kb_id for workspace isolation)
        self.index.upsert(vectors=vectors, namespace=kb_id)

        return len(chunks)

    async def retrieve(
        self,
        query: str,
        kb_id: str,
        top_k: int = 5,
        score_threshold: float = 0.1,
    ) -> list[Chunk]:
        """Semantic search for relevant chunks."""
        # Embed query (run in thread pool)
        query_embedding = await asyncio.to_thread(
            self.embed_model.encode, query, show_progress_bar=False
        )

        # Search Pinecone
        results = self.index.query(
            vector=query_embedding.tolist(),
            top_k=top_k,
            include_metadata=True,
            namespace=kb_id,
        )

        # Convert to Chunk objects, filter by score threshold
        chunks = []
        for match in results.matches:
            if match.score >= score_threshold:
                metadata = match.metadata
                chunks.append(
                    Chunk(
                        doc_id=metadata.get("doc_id", ""),
                        doc_name=metadata.get("filename", ""),
                        chunk_text=metadata.get("text", ""),
                        page_number=metadata.get("page_number"),
                        relevance_score=match.score,
                        metadata=metadata,
                    )
                )

        return chunks

    async def delete(self, doc_id: str, kb_id: str) -> None:
        """Remove document vectors from store."""
        # Query all vector IDs for this document
        # Pinecone delete by prefix is not supported, so we need to list and delete
        # For now, we'll use a workaround: delete by filter
        self.index.delete(
            filter={"doc_id": {"$eq": doc_id}},
            namespace=kb_id,
        )

    async def _parse_document(self, content: bytes | BinaryIO, filename: str) -> str:
        """Parse document to text based on file type.

        Args:
            content: Document bytes or file-like object
            filename: Original filename for extension detection

        Returns:
            Extracted text
        """
        # Convert BinaryIO to bytes if needed
        if isinstance(content, io.IOBase):
            content = content.read()

        # Detect file type by extension
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            return await self._parse_pdf(content)
        elif ext in [".docx", ".doc"]:
            return await self._parse_docx(content)
        elif ext in [".txt", ".md", ".csv"]:
            return content.decode("utf-8", errors="ignore")
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    async def _parse_pdf(self, content: bytes) -> str:
        """Parse PDF using pdfplumber (runs in thread pool)."""

        def _extract():
            text_parts = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return "\n\n".join(text_parts)

        return await asyncio.to_thread(_extract)

    async def _parse_docx(self, content: bytes) -> str:
        """Parse DOCX using python-docx (runs in thread pool)."""

        def _extract():
            doc = DocxDocument(io.BytesIO(content))
            return "\n\n".join([para.text for para in doc.paragraphs if para.text])

        return await asyncio.to_thread(_extract)

    async def cleanup_partial_vectors(self, doc_id: str, kb_id: str) -> None:
        """Clean up partial vectors on ingestion failure.

        This is called during error recovery to ensure clean state for retry.
        """
        await self.delete(doc_id, kb_id)
