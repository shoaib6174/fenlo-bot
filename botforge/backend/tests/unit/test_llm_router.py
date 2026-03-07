"""
Unit tests for LLM Router and Circuit Breaker
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.llm_router import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    LLMRouter,
    ProviderError,
)


class TestCircuitBreaker:
    """Test circuit breaker state machine"""

    def test_starts_closed(self):
        """Circuit breaker starts in CLOSED state"""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.failures == []

    @pytest.mark.asyncio
    async def test_executes_function_when_closed(self):
        """Circuit breaker executes function normally when CLOSED"""
        cb = CircuitBreaker("test")
        mock_func = AsyncMock(return_value="success")

        result = await cb.call(mock_func, "arg1", kwarg="value")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg="value")

    @pytest.mark.asyncio
    async def test_records_failure(self):
        """Circuit breaker records failures"""
        cb = CircuitBreaker("test", failure_threshold=2)
        mock_func = AsyncMock(side_effect=ProviderError("Provider error"))

        with pytest.raises(ProviderError):
            await cb.call(mock_func)

        assert len(cb.failures) == 1
        assert cb.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        """Circuit opens after N failures within window"""
        cb = CircuitBreaker("test", failure_threshold=3, monitoring_window=60)
        mock_func = AsyncMock(side_effect=ProviderError("Provider error"))

        # First 2 failures - circuit stays CLOSED
        for _ in range(2):
            with pytest.raises(ProviderError):
                await cb.call(mock_func)
            assert cb.state == CircuitState.CLOSED

        # 3rd failure - circuit OPENS
        with pytest.raises(ProviderError):
            await cb.call(mock_func)
        assert cb.state == CircuitState.OPEN
        assert len(cb.failures) == 3

    @pytest.mark.asyncio
    async def test_raises_when_open(self):
        """Circuit breaker raises CircuitOpenError when OPEN"""
        cb = CircuitBreaker("test", failure_threshold=1)
        mock_func = AsyncMock(side_effect=ProviderError("Provider error"))

        # Trigger circuit to open
        with pytest.raises(ProviderError):
            await cb.call(mock_func)
        assert cb.state == CircuitState.OPEN

        # Next call should raise CircuitOpenError without calling function
        with pytest.raises(CircuitOpenError, match="test circuit is OPEN"):
            await cb.call(mock_func)

        # Function should not be called when circuit is OPEN
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self):
        """Circuit transitions to HALF_OPEN after recovery timeout"""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=1, monitoring_window=60)
        mock_func = AsyncMock(side_effect=ProviderError("Provider error"))

        # Open the circuit
        with pytest.raises(ProviderError):
            await cb.call(mock_func)
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # Next call should move to HALF_OPEN and attempt the function
        mock_func.side_effect = None
        mock_func.return_value = "recovered"

        result = await cb.call(mock_func)

        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED  # Success closes circuit

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """Successful call in HALF_OPEN state closes circuit"""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=1, monitoring_window=60)

        # Manually set to HALF_OPEN
        cb.state = CircuitState.HALF_OPEN
        mock_func = AsyncMock(return_value="success")

        result = await cb.call(mock_func)

        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert len(cb.failures) == 0

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """Failed call in HALF_OPEN state reopens circuit"""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=1, monitoring_window=60)

        # Manually set to HALF_OPEN
        cb.state = CircuitState.HALF_OPEN
        mock_func = AsyncMock(side_effect=ProviderError("Still failing"))

        with pytest.raises(ProviderError):
            await cb.call(mock_func)

        assert cb.state == CircuitState.OPEN
        assert len(cb.failures) == 1

    @pytest.mark.asyncio
    async def test_cleans_old_failures(self):
        """Circuit breaker removes failures outside monitoring window"""
        cb = CircuitBreaker("test", monitoring_window=1)

        # Add old failure
        cb.failures.append(time.time() - 2)
        assert len(cb.failures) == 1

        # Clean old failures
        cb._clean_old_failures()

        assert len(cb.failures) == 0


class TestLLMRouter:
    """Test LLM routing with circuit breaker protection"""

    @pytest.fixture
    def router(self):
        """Create LLMRouter instance"""
        # Reset singleton
        LLMRouter._instance = None
        LLMRouter._groq_client = None
        LLMRouter._openai_client = None

        with patch("app.core.llm_router.settings") as mock_settings:
            mock_settings.groq_api_key = "test-groq-key"
            mock_settings.openai_api_key = "test-openai-key"

            router = LLMRouter()
            yield router

    @pytest.mark.asyncio
    async def test_routes_to_groq_by_default(self, router):
        """Router tries Groq first (primary provider)"""
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(router, "_call_groq", new_callable=AsyncMock) as mock_groq:
            # Make _call_groq return an async generator
            async def mock_generator():
                yield {"type": "token", "content": "Hi"}
                yield {"type": "done", "tokens_in": 10, "tokens_out": 5}

            mock_groq.return_value = mock_generator()

            response = await router.complete(messages, stream=True)

            # Consume generator
            tokens = [chunk async for chunk in response]

            mock_groq.assert_called_once()
            assert len(tokens) == 2
            assert tokens[0]["content"] == "Hi"

    @pytest.mark.asyncio
    async def test_falls_back_to_openai_on_groq_error(self, router):
        """Router falls back to OpenAI when Groq fails"""
        messages = [{"role": "user", "content": "Hello"}]

        with (
            patch.object(router, "_call_groq", new_callable=AsyncMock) as mock_groq,
            patch.object(router, "_call_openai", new_callable=AsyncMock) as mock_openai,
        ):
            # Groq fails
            mock_groq.side_effect = ProviderError("Groq error")

            # OpenAI succeeds
            async def mock_generator():
                yield {"type": "token", "content": "Hi from OpenAI"}
                yield {"type": "done", "tokens_in": 10, "tokens_out": 5}

            mock_openai.return_value = mock_generator()

            response = await router.complete(messages, stream=True)
            tokens = [chunk async for chunk in response]

            mock_groq.assert_called_once()
            mock_openai.assert_called_once()
            assert tokens[0]["content"] == "Hi from OpenAI"

    @pytest.mark.asyncio
    async def test_graceful_degradation_when_all_fail(self, router):
        """Router returns friendly message when all providers fail"""
        messages = [{"role": "user", "content": "Hello"}]

        with (
            patch.object(router, "_call_groq", new_callable=AsyncMock) as mock_groq,
            patch.object(router, "_call_openai", new_callable=AsyncMock) as mock_openai,
        ):
            # Both fail
            mock_groq.side_effect = ProviderError("Groq error")
            mock_openai.side_effect = ProviderError("OpenAI error")

            response = await router.complete(messages, stream=True)
            tokens = [chunk async for chunk in response]

            # Should get fallback message
            assert any("high demand" in t.get("content", "").lower() for t in tokens)
            assert tokens[-1]["type"] == "done"
            assert tokens[-1]["provider"] == "fallback"

    @pytest.mark.asyncio
    async def test_non_streaming_mode(self, router):
        """Router supports non-streaming mode"""
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(router, "_call_groq", new_callable=AsyncMock) as mock_groq:
            mock_groq.return_value = {
                "content": "Hi there",
                "tokens_in": 10,
                "tokens_out": 5,
                "provider": "groq",
            }

            response = await router.complete(messages, stream=False)

            assert response["content"] == "Hi there"
            assert response["provider"] == "groq"
            mock_groq.assert_called_once_with(messages, stream=False)

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_calls_when_open(self, router):
        """Circuit breaker prevents calls to failing provider"""
        messages = [{"role": "user", "content": "Hello"}]

        # Force Groq circuit to OPEN
        router.groq_circuit.state = CircuitState.OPEN
        router.groq_circuit.last_failure_time = time.time()

        with (
            patch.object(router, "_call_groq", new_callable=AsyncMock) as mock_groq,
            patch.object(router, "_call_openai", new_callable=AsyncMock) as mock_openai,
        ):

            async def mock_generator():
                yield {"type": "token", "content": "From OpenAI"}
                yield {"type": "done", "tokens_in": 10, "tokens_out": 5}

            mock_openai.return_value = mock_generator()

            response = await router.complete(messages, stream=True)
            tokens = [chunk async for chunk in response]

            # Groq should NOT be called (circuit is OPEN)
            mock_groq.assert_not_called()
            # OpenAI should be called
            mock_openai.assert_called_once()
            assert tokens[0]["content"] == "From OpenAI"

    @pytest.mark.asyncio
    async def test_passes_kwargs_to_provider(self, router):
        """Router passes additional kwargs to provider"""
        messages = [{"role": "user", "content": "Hello"}]

        with patch.object(router, "_call_groq", new_callable=AsyncMock) as mock_groq:

            async def mock_generator():
                yield {"type": "done", "tokens_in": 10, "tokens_out": 5}

            mock_groq.return_value = mock_generator()

            await router.complete(messages, stream=True, temperature=0.7, max_tokens=100)

            mock_groq.assert_called_once_with(
                messages, stream=True, temperature=0.7, max_tokens=100
            )

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """LLMRouter is a singleton for connection pooling"""
        with patch("app.core.llm_router.settings") as mock_settings:
            mock_settings.groq_api_key = "test-key"
            mock_settings.openai_api_key = "test-key"

            router1 = LLMRouter()
            router2 = LLMRouter()

            assert router1 is router2

    @pytest.mark.asyncio
    async def test_streams_groq_tokens(self, router):
        """Router streams tokens from Groq response"""
        with patch.object(router._groq_client.chat.completions, "create") as mock_create:
            # Mock streaming response
            async def mock_stream():
                # Simulate chunk with content
                chunk1 = MagicMock()
                chunk1.choices = [MagicMock()]
                chunk1.choices[0].delta.content = "Hello"
                yield chunk1

                # Simulate chunk with more content
                chunk2 = MagicMock()
                chunk2.choices = [MagicMock()]
                chunk2.choices[0].delta.content = " world"
                yield chunk2

            mock_create.return_value = mock_stream()

            messages = [{"role": "user", "content": "Hi"}]
            result = await router._call_groq(messages, stream=True)

            tokens = []
            async for chunk in result:
                tokens.append(chunk)

            # Should have 2 content tokens + 1 done
            assert len(tokens) == 3
            assert tokens[0]["content"] == "Hello"
            assert tokens[1]["content"] == " world"
            assert tokens[2]["type"] == "done"

    @pytest.mark.asyncio
    async def test_handles_empty_chunks(self, router):
        """Router handles chunks with no choices"""
        with patch.object(router._groq_client.chat.completions, "create") as mock_create:

            async def mock_stream():
                # Empty chunk (no choices)
                chunk1 = MagicMock()
                chunk1.choices = []
                yield chunk1

                # Valid chunk
                chunk2 = MagicMock()
                chunk2.choices = [MagicMock()]
                chunk2.choices[0].delta.content = "Hello"
                yield chunk2

            mock_create.return_value = mock_stream()

            messages = [{"role": "user", "content": "Hi"}]
            result = await router._call_groq(messages, stream=True)

            tokens = [chunk async for chunk in result]

            # Should only have valid chunk + done
            assert len(tokens) == 2
            assert tokens[0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_close_clients(self, router):
        """Router closes HTTP clients on shutdown"""
        with (
            patch.object(router._groq_client, "close", new_callable=AsyncMock) as mock_groq_close,
            patch.object(
                router._openai_client, "close", new_callable=AsyncMock
            ) as mock_openai_close,
        ):
            await router.close()

            mock_groq_close.assert_called_once()
            mock_openai_close.assert_called_once()
