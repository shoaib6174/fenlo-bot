"""Integration tests for health check endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.middleware.rate_limiter import ip_rate_limit


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Disable rate limiting for health tests to avoid 429 from test ordering."""
    app.dependency_overrides[ip_rate_limit] = lambda: None
    yield
    app.dependency_overrides.pop(ip_rate_limit, None)


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check endpoints."""

    async def test_liveness_returns_ok(self):
        """Test that liveness endpoint returns 200 OK."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health/live")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "uptime_s" in response.json()

    async def test_readiness_reports_db_status(self):
        """Test that readiness endpoint reports database status."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health/ready")

        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "db" in data

    async def test_readiness_reports_redis_status(self):
        """Test that readiness endpoint reports Redis status."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health/ready")

        data = response.json()
        assert "redis" in data
        # Redis should report status (True/False)
        assert isinstance(data["redis"], bool)

    async def test_full_status_comprehensive(self):
        """Test that status endpoint provides comprehensive health info."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health/status")

        assert response.status_code == 200
        data = response.json()

        # Should include all critical dependencies
        assert "status" in data
        assert "db" in data
        assert "redis" in data
        assert "uptime_s" in data

    async def test_liveness_fast_response(self):
        """Test that liveness responds quickly (<100ms)."""
        import time

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            start = time.time()
            response = await client.get("/api/health/live")
            duration_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        # Should be very fast (< 500ms in test environment, <10ms in prod)
        assert duration_ms < 500

    async def test_full_status_includes_extended_fields(self):
        """Test that /status includes LLM circuit breaker, WebSocket, worker, and queue data (S80)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/health/status")

        assert response.status_code == 200
        data = response.json()

        # LLM providers should include circuit breaker state and failure count
        assert "llm_providers" in data
        assert "groq" in data["llm_providers"]
        assert "openai" in data["llm_providers"]
        groq = data["llm_providers"]["groq"]
        assert "state" in groq
        assert groq["state"] in ("closed", "open", "half_open", "unknown")
        assert "failures" in groq

        # Worker status should include detailed info
        assert "worker" in data
        assert "status" in data["worker"]
        assert data["worker"]["status"] in ("healthy", "degraded", "down", "unknown")

        # Active WebSocket count
        assert "active_websockets" in data
        assert isinstance(data["active_websockets"], int)

        # Queue depth
        assert "arq_queue_depth" in data
