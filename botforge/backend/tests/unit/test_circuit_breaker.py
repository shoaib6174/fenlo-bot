"""Unit tests for circuit breaker functionality in LLM Router.

Spec: docs/plans/phase-1-engine.md (Section 1.2)
"""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.llm_router import CircuitBreaker, CircuitOpenError, LLMRouter, ProviderError


class TestCircuitBreaker:
    """Test circuit breaker state machine."""

    def test_initial_state_is_closed(self):
        """Test that circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=10)
        assert cb.state == "CLOSED"

    async def test_opens_after_threshold_failures(self):
        """Test that circuit opens after N failures."""
        cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=10)

        async def failing_func():
            raise ProviderError("Service unavailable")

        # First 2 failures - circuit stays closed
        for _ in range(2):
            with pytest.raises(ProviderError):
                await cb.call(failing_func)
            assert cb.state == "CLOSED"

        # 3rd failure - circuit opens
        with pytest.raises(ProviderError):
            await cb.call(failing_func)
        assert cb.state == "OPEN"

    async def test_open_circuit_raises_immediately(self):
        """Test that OPEN circuit raises without calling function."""
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=10)

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ProviderError("Service unavailable")

        # Trigger 2 failures to open circuit
        for _ in range(2):
            with pytest.raises(ProviderError):
                await cb.call(failing_func)

        assert cb.state == "OPEN"
        assert call_count == 2

        # Next call should raise CircuitOpenError without calling function
        with pytest.raises(CircuitOpenError):
            await cb.call(failing_func)

        # Verify function was NOT called
        assert call_count == 2

    async def test_transitions_to_half_open_after_timeout(self):
        """Test transition from OPEN to HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=1)

        async def failing_func():
            raise ProviderError("Service unavailable")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ProviderError):
                await cb.call(failing_func)

        assert cb.state == "OPEN"

        # Wait for recovery timeout
        time.sleep(1.1)

        # Next call should transition to HALF_OPEN
        async def success_func():
            return "success"

        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state == "CLOSED"  # Successful test closes circuit

    async def test_half_open_success_closes_circuit(self):
        """Test that successful call in HALF_OPEN state closes circuit."""
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=1)

        async def failing_func():
            raise ProviderError("Service unavailable")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ProviderError):
                await cb.call(failing_func)

        time.sleep(1.1)

        # Successful call should close circuit
        async def success_func():
            return "OK"

        result = await cb.call(success_func)
        assert result == "OK"
        assert cb.state == "CLOSED"

    async def test_half_open_failure_reopens_circuit(self):
        """Test that failure in HALF_OPEN state reopens circuit."""
        cb = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=1)

        async def failing_func():
            raise ProviderError("Service unavailable")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ProviderError):
                await cb.call(failing_func)

        time.sleep(1.1)

        # Failed test call should reopen circuit
        with pytest.raises(ProviderError):
            await cb.call(failing_func)

        assert cb.state == "OPEN"

    async def test_monitoring_window(self):
        """Test that old failures outside monitoring window are ignored."""
        cb = CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=10,
            monitoring_window=2,  # 2 second window
        )

        async def failing_func():
            raise ProviderError("Service unavailable")

        # First failure
        with pytest.raises(ProviderError):
            await cb.call(failing_func)

        # Wait for monitoring window to expire
        time.sleep(2.1)

        # Second failure (first is now outside window)
        with pytest.raises(ProviderError):
            await cb.call(failing_func)

        # Circuit should still be CLOSED (only 1 failure in window)
        assert cb.state == "CLOSED"


class TestLLMRouterCircuitBreaker:
    """Test circuit breaker integration in LLM Router."""

    async def test_groq_circuit_breaker_fallback(self):
        """Test that Groq failures trigger fallback to OpenAI."""
        # Reset singleton
        LLMRouter._instance = None

        with (
            patch("app.core.llm_router.AsyncGroq") as mock_groq_class,
            patch("app.core.llm_router.AsyncOpenAI") as mock_openai_class,
            patch("app.core.llm_router.httpx.AsyncClient"),
        ):
            # Mock Groq client to fail
            mock_groq = AsyncMock()
            mock_groq.chat.completions.create = AsyncMock(side_effect=Exception("Groq unavailable"))
            mock_groq_class.return_value = mock_groq

            # Mock OpenAI client to succeed
            mock_completion = Mock()
            mock_completion.choices = [Mock(message=Mock(content="Response from OpenAI"))]
            mock_openai = AsyncMock()
            mock_openai.chat.completions.create = AsyncMock(return_value=mock_completion)
            mock_openai_class.return_value = mock_openai

            router = LLMRouter()

            # First call should try Groq, fail, then use OpenAI
            result = await router.complete(messages=[{"role": "user", "content": "Hi"}])

            assert result is not None

        # Cleanup singleton
        LLMRouter._instance = None

    async def test_all_providers_down_graceful_degradation(self):
        """Test graceful degradation when all providers are down."""
        # Reset singleton
        LLMRouter._instance = None

        with (
            patch("app.core.llm_router.AsyncGroq") as mock_groq_class,
            patch("app.core.llm_router.AsyncOpenAI") as mock_openai_class,
            patch("app.core.llm_router.httpx.AsyncClient"),
        ):
            # Mock both providers to fail
            mock_groq = AsyncMock()
            mock_groq.chat.completions.create = AsyncMock(side_effect=Exception("Groq unavailable"))
            mock_groq_class.return_value = mock_groq

            mock_openai = AsyncMock()
            mock_openai.chat.completions.create = AsyncMock(
                side_effect=Exception("OpenAI unavailable")
            )
            mock_openai_class.return_value = mock_openai

            router = LLMRouter()

            # Should not crash, should handle gracefully
            try:
                result = await router.complete(messages=[{"role": "user", "content": "Hi"}])
                # Should return some form of graceful response
                assert result is not None
            except Exception as e:
                # Or raise a specific, handled exception
                assert "all providers" in str(e).lower() or "unavailable" in str(e).lower()

        # Cleanup singleton
        LLMRouter._instance = None
