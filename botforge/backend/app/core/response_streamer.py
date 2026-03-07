"""
Response Streamer - WebSocket streaming for real-time token delivery.

Handles:
- WebSocket connection management with JWT authentication
- Streaming tokens from LLM providers
- Event emission (token, typing, done, error, citation, quality_score)
- Integration with MessagePipeline
"""

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from app.core.engine import MessageContext, PipelineStep


class StreamEvent:
    """WebSocket stream event types"""

    TOKEN = "token"
    TYPING = "typing"
    DONE = "done"
    ERROR = "error"
    CITATION = "citation"
    QUALITY_SCORE = "quality_score"


class ResponseStreamer:
    """
    Manages WebSocket streaming for real-time response delivery.

    Supports:
    - Token-by-token streaming
    - Event-based updates (typing indicator, citations, quality scores)
    - Error handling with graceful degradation
    """

    def __init__(self, websocket: WebSocket):
        """
        Initialize streamer with WebSocket connection.

        Args:
            websocket: FastAPI WebSocket instance
        """
        self.websocket = websocket

    async def send_event(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """
        Send an event to the WebSocket client.

        Args:
            event_type: Event type (token, typing, done, error, citation, quality_score)
            data: Optional event data
        """
        message = {
            "type": event_type,
            "data": data or {},
        }
        try:
            await self.websocket.send_json(message)
        except WebSocketDisconnect:
            # Client disconnected, silently ignore
            pass
        except Exception:
            # Log error but don't crash
            pass

    async def stream_token(self, token: str) -> None:
        """
        Stream a single token to the client.

        Args:
            token: Token string to send
        """
        await self.send_event(StreamEvent.TOKEN, {"token": token})

    async def stream_tokens(self, tokens: AsyncIterator[str]) -> str:
        """
        Stream tokens from an async iterator.

        Args:
            tokens: Async iterator of token strings

        Returns:
            Complete response text (accumulated tokens)
        """
        response_text = ""
        async for token in tokens:
            response_text += token
            await self.stream_token(token)
        return response_text

    async def send_typing(self, is_typing: bool = True) -> None:
        """
        Send typing indicator.

        Args:
            is_typing: Whether bot is currently typing
        """
        await self.send_event(StreamEvent.TYPING, {"is_typing": is_typing})

    async def send_done(
        self,
        conversation_id: UUID | None = None,
        message_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Send completion event.

        Args:
            conversation_id: Conversation identifier
            message_id: Message identifier
            metadata: Optional metadata (sentiment, intent, tokens_used, etc.)
        """
        data = {
            "conversation_id": str(conversation_id) if conversation_id else None,
            "message_id": str(message_id) if message_id else None,
        }
        if metadata:
            data.update(metadata)
        await self.send_event(StreamEvent.DONE, data)

    async def send_error(self, error_message: str, error_code: str | None = None) -> None:
        """
        Send error event.

        Args:
            error_message: Human-readable error message
            error_code: Optional error code
        """
        await self.send_event(
            StreamEvent.ERROR,
            {
                "message": error_message,
                "code": error_code,
            },
        )

    async def send_citation(self, citation: dict[str, Any]) -> None:
        """
        Send citation event.

        Args:
            citation: Citation data (doc_name, page_number, chunk_text, relevance_score)
        """
        await self.send_event(StreamEvent.CITATION, citation)

    async def send_citations(self, citations: list[dict[str, Any]]) -> None:
        """
        Send multiple citations.

        Args:
            citations: List of citation dicts
        """
        for citation in citations:
            await self.send_citation(citation)

    async def send_quality_score(self, score: float) -> None:
        """
        Send quality score event.

        Args:
            score: Quality score (0.0-1.0)
        """
        await self.send_event(StreamEvent.QUALITY_SCORE, {"score": score})


class LLMStreamStep(PipelineStep):
    """
    Pipeline step that streams LLM response via WebSocket.

    This step:
    1. Sends typing indicator
    2. Calls LLM router with streaming enabled
    3. Streams tokens to WebSocket client
    4. Accumulates full response in context
    5. Sends done event

    Requires:
    - context.metadata["streamer"]: ResponseStreamer instance
    - context.metadata["llm_router"]: LLMRouter instance
    """

    async def execute(self, context: MessageContext) -> MessageContext:
        """
        Call LLM — streaming via WebSocket or synchronous for HTTP.

        Args:
            context: Current message context

        Returns:
            Updated context with response text
        """
        llm_router = context.metadata.get("llm_router")
        streamer = context.metadata.get("streamer")
        is_sync = context.metadata.get("synchronous", False)

        if not llm_router:
            context.should_halt = True
            context.halt_reason = "Missing LLM router"
            return context

        # Build prompt from context
        messages = []
        system_content = context.system_prompt or ""

        # Inject RAG context if available
        if context.rag_chunks:
            rag_context = "\n\n".join(
                f"[Source: {chunk.get('metadata', {}).get('filename', 'Unknown')}]\n{chunk['text']}"
                for chunk in context.rag_chunks
            )
            rag_instruction = (
                "\n\nUse the following knowledge base context to answer the user's question. "
                "If the context is relevant, base your answer on it and cite the source documents. "
                "If the context doesn't help answer the question, say so.\n\n"
                f"--- Knowledge Base Context ---\n{rag_context}\n--- End Context ---"
            )
            system_content += rag_instruction

        if system_content:
            messages.append({"role": "system", "content": system_content})
        for msg in context.conversation_history:
            messages.append(msg)
        messages.append({"role": "user", "content": context.message})

        if is_sync:
            # Synchronous (HTTP) path — no streaming
            try:
                result = await llm_router.complete(messages, stream=False)
                context.response = result.get("content", "")
                context.tokens_used = result.get("tokens_in", 0) + result.get("tokens_out", 0)
                context.provider_used = result.get("provider", "unknown")
            except Exception as e:
                context.should_halt = True
                context.halt_reason = f"LLM error: {e}"
        elif streamer:
            # WebSocket streaming path
            try:
                await streamer.send_typing(True)
                token_stream = llm_router.stream(messages)
                response_text = await streamer.stream_tokens(token_stream)
                context.response = response_text
                await streamer.send_typing(False)
            except Exception as e:
                await streamer.send_error(str(e), "llm_error")
                context.should_halt = True
                context.halt_reason = f"LLM streaming error: {e}"
        else:
            context.should_halt = True
            context.halt_reason = "No streamer for non-sync request"

        return context


class BuildPromptStep(PipelineStep):
    """
    Pipeline step that builds the prompt for LLM.

    This is a no-op in streaming mode (handled by LLMStreamStep).
    In non-streaming mode, this would prepare the full prompt.
    """

    async def execute(self, context: MessageContext) -> MessageContext:
        """
        Build prompt from context (no-op for streaming).

        Args:
            context: Current message context

        Returns:
            Unchanged context
        """
        # Prompt building happens in LLMStreamStep for streaming mode
        return context
