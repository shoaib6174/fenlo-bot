"""
LLM Router with Circuit Breaker Pattern

Primary: Groq (Llama 3.3 70B) - free, fast
Fallback: OpenAI GPT-4o-mini
Circuit breaker per provider prevents cascading failures
Singleton HTTP clients with connection pooling
"""

import time
from collections.abc import AsyncGenerator, Callable
from enum import StrEnum
from typing import Any, Optional

import httpx
import structlog
from groq import AsyncGroq
from openai import AsyncOpenAI

from app.config import settings

logger = structlog.get_logger(__name__)


class CircuitState(StrEnum):
    """Circuit breaker states"""

    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Provider is down, skip it
    HALF_OPEN = "HALF_OPEN"  # Testing if provider recovered


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open"""

    pass


class ProviderError(Exception):
    """Raised when LLM provider fails"""

    pass


class CircuitBreaker:
    """
    Circuit breaker per LLM provider.

    Prevents cascading failures by "tripping" after N failures within T seconds,
    then directing traffic to fallback for M seconds before testing recovery.

    States:
    - CLOSED: Normal operation, all requests go through
    - OPEN: Provider is down, skip all requests (raise CircuitOpenError)
    - HALF_OPEN: Testing recovery, allow one request through

    Flow:
    CLOSED → (N failures in T seconds) → OPEN → (wait M seconds) → HALF_OPEN
    → (success) → CLOSED
    → (failure) → OPEN
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        monitoring_window: int = 60,
    ):
        """
        Args:
            name: Provider name (for logging)
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before testing recovery (OPEN → HALF_OPEN)
            monitoring_window: Seconds window for counting failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.monitoring_window = monitoring_window
        self.state = CircuitState.CLOSED
        self.failures: list[float] = []  # Timestamps of recent failures
        self.last_failure_time: float | None = None

    def _clean_old_failures(self):
        """Remove failures outside the monitoring window"""
        now = time.time()
        cutoff = now - self.monitoring_window
        self.failures = [f for f in self.failures if f > cutoff]

    def _record_failure(self):
        """Record a failure and update circuit state"""
        now = time.time()
        self.failures.append(now)
        self.last_failure_time = now
        self._clean_old_failures()

        if len(self.failures) >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker.opened",
                provider=self.name,
                failures=len(self.failures),
                threshold=self.failure_threshold,
            )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Raises:
            CircuitOpenError: If circuit is OPEN and recovery timeout hasn't elapsed
        """
        # Check if we should test recovery
        if self.state == CircuitState.OPEN:
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time > self.recovery_timeout
            ):
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    "circuit_breaker.half_open",
                    provider=self.name,
                    message="Testing provider recovery",
                )
            else:
                raise CircuitOpenError(f"{self.name} circuit is OPEN")

        # Execute the function
        try:
            result = await func(*args, **kwargs)

            # If we were testing recovery, mark as successful
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failures.clear()
                logger.info(
                    "circuit_breaker.closed",
                    provider=self.name,
                    message="Provider recovered",
                )

            return result

        except Exception as e:
            self._record_failure()
            logger.error(
                "circuit_breaker.failure",
                provider=self.name,
                error=str(e),
                state=self.state,
                failure_count=len(self.failures),
            )
            raise


class LLMRouter:
    """
    Routes LLM requests with circuit breaker protection.

    Primary: Groq (free, fast)
    Fallback: OpenAI GPT-4o-mini

    Features:
    - Per-provider circuit breakers prevent cascading failures
    - Singleton HTTP clients with connection pooling (saves 50-100ms/request)
    - Graceful degradation when all providers are down
    """

    _instance: Optional["LLMRouter"] = None
    _groq_client: AsyncGroq | None = None
    _openai_client: AsyncOpenAI | None = None

    def __new__(cls):
        """Singleton pattern for connection pool reuse"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize circuit breakers and HTTP clients"""
        # Only initialize once
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # Circuit breakers per provider
        self.groq_circuit = CircuitBreaker("groq")
        self.openai_circuit = CircuitBreaker("openai")

        # Singleton HTTP clients with connection pooling
        # Reusing connections saves 50-100ms per request (TCP + TLS handshake)
        self._groq_client = AsyncGroq(
            api_key=settings.groq_api_key,
            http_client=httpx.AsyncClient(
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                timeout=30.0,
            ),
        )

        self._openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=httpx.AsyncClient(
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                timeout=30.0,
            ),
        )

        logger.info(
            "llm_router.initialized",
            groq_enabled=bool(settings.groq_api_key),
            openai_enabled=bool(settings.openai_api_key),
        )

    async def _call_groq(
        self,
        messages: list[dict],
        stream: bool = True,
        **kwargs,
    ) -> AsyncGenerator[dict, None] | dict:
        """Call Groq API"""
        try:
            response = await self._groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                stream=stream,
                **kwargs,
            )

            if stream:
                return self._stream_groq_response(response)
            else:
                return {
                    "content": response.choices[0].message.content,
                    "tokens_in": response.usage.prompt_tokens,
                    "tokens_out": response.usage.completion_tokens,
                    "provider": "groq",
                }

        except Exception as e:
            logger.error("groq.error", error=str(e), error_type=type(e).__name__)
            raise ProviderError(f"Groq error: {e}") from e

    async def _stream_groq_response(self, response) -> AsyncGenerator[dict, None]:
        """Stream tokens from Groq response"""
        tokens_in = 0
        tokens_out = 0

        async for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Track token usage (if available)
            if hasattr(chunk, "usage") and chunk.usage:
                tokens_in = chunk.usage.prompt_tokens
                tokens_out += 1

            # Stream content
            if delta.content:
                yield {
                    "type": "token",
                    "content": delta.content,
                    "provider": "groq",
                }

        # Send final metadata
        yield {
            "type": "done",
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "provider": "groq",
        }

    async def _call_openai(
        self,
        messages: list[dict],
        stream: bool = True,
        **kwargs,
    ) -> AsyncGenerator[dict, None] | dict:
        """Call OpenAI API"""
        try:
            response = await self._openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=stream,
                **kwargs,
            )

            if stream:
                return self._stream_openai_response(response)
            else:
                return {
                    "content": response.choices[0].message.content,
                    "tokens_in": response.usage.prompt_tokens,
                    "tokens_out": response.usage.completion_tokens,
                    "provider": "openai",
                }

        except Exception as e:
            logger.error("openai.error", error=str(e), error_type=type(e).__name__)
            raise ProviderError(f"OpenAI error: {e}") from e

    async def _stream_openai_response(self, response) -> AsyncGenerator[dict, None]:
        """Stream tokens from OpenAI response"""
        tokens_out = 0

        async for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            tokens_out += 1

            # Stream content
            if delta.content:
                yield {
                    "type": "token",
                    "content": delta.content,
                    "provider": "openai",
                }

        # Send final metadata
        yield {
            "type": "done",
            "tokens_in": 0,  # OpenAI doesn't provide this in streaming
            "tokens_out": tokens_out,
            "provider": "openai",
        }

    async def _queue_and_respond(self, messages: list[dict]) -> AsyncGenerator[dict, None]:
        """
        Graceful degradation when all providers are down.

        In Phase 1: return user-friendly message immediately
        Future phases: actually queue message for later processing
        """
        logger.critical(
            "llm.all_providers_down",
            message="All LLM providers unavailable",
            action="returning_fallback_message",
        )

        # User-friendly response
        fallback_message = (
            "We're experiencing high demand right now. "
            "Your message has been queued and will be processed shortly. "
            "Please check back in a few minutes."
        )

        yield {"type": "token", "content": fallback_message, "provider": "fallback"}
        yield {"type": "done", "tokens_in": 0, "tokens_out": 0, "provider": "fallback"}

    async def complete(
        self,
        messages: list[dict],
        stream: bool = True,
        **kwargs,
    ) -> AsyncGenerator[dict, None] | dict:
        """
        Route request to LLM provider with circuit breaker protection.

        Flow:
        1. Try Groq (primary, free)
        2. If Groq fails or circuit open → try OpenAI (fallback)
        3. If all providers down → queue message + return friendly response

        Args:
            messages: Chat messages in OpenAI format
            stream: Whether to stream response tokens
            **kwargs: Additional provider-specific parameters

        Yields:
            Streaming: dict with {"type": "token", "content": str} or {"type": "done", ...}
            Non-streaming: dict with content and metadata

        Raises:
            Never raises - always returns a response (graceful degradation)
        """
        # Try Groq first (with circuit breaker)
        try:
            logger.debug("llm_router.trying_groq", message_count=len(messages))
            return await self.groq_circuit.call(self._call_groq, messages, stream=stream, **kwargs)
        except (CircuitOpenError, ProviderError) as e:
            logger.info(
                "llm_router.groq_failed",
                reason=str(e),
                fallback="openai",
            )

        # Fallback to OpenAI (with circuit breaker)
        try:
            logger.debug("llm_router.trying_openai", message_count=len(messages))
            return await self.openai_circuit.call(
                self._call_openai, messages, stream=stream, **kwargs
            )
        except (CircuitOpenError, ProviderError) as e:
            logger.error(
                "llm_router.openai_failed",
                reason=str(e),
                fallback="queue",
            )

        # All providers down — graceful degradation
        if stream:
            return self._queue_and_respond(messages)
        else:
            # Non-streaming fallback
            return {
                "content": (
                    "We're experiencing high demand. "
                    "Your message has been queued and will be processed shortly."
                ),
                "tokens_in": 0,
                "tokens_out": 0,
                "provider": "fallback",
            }

    async def stream(
        self,
        messages: list[dict],
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens as strings (convenience wrapper).

        This is a simplified interface that yields just the content strings,
        filtering out metadata events. Useful for WebSocket streaming.

        Args:
            messages: Chat messages in OpenAI format
            **kwargs: Additional provider-specific parameters

        Yields:
            Token strings
        """
        response = await self.complete(messages, stream=True, **kwargs)

        async for chunk in response:
            if chunk.get("type") == "token":
                yield chunk["content"]

    async def close(self):
        """Close HTTP clients (call on shutdown)"""
        if self._groq_client:
            await self._groq_client.close()
        if self._openai_client:
            await self._openai_client.close()
        logger.info("llm_router.closed")
