"""Unit tests for main.py — app creation, middleware, request context.

Tests the FastAPI app setup, request context middleware (trace_id injection),
route registration, and structlog configuration.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.middleware.rate_limiter import ip_rate_limit


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Disable rate limiting for main tests to avoid 429 from test ordering."""
    app.dependency_overrides[ip_rate_limit] = lambda: None
    yield
    app.dependency_overrides.pop(ip_rate_limit, None)


@pytest.mark.asyncio
class TestAppCreation:
    """Test FastAPI app is properly configured."""

    async def test_app_title(self):
        assert app.title == "BotForge"

    async def test_app_version(self):
        assert app.version == "0.1.0"

    async def test_docs_url_available(self):
        assert app.docs_url == "/docs"

    async def test_redoc_url_available(self):
        assert app.redoc_url == "/redoc"


@pytest.mark.asyncio
class TestRequestContextMiddleware:
    """Test that request context middleware injects trace_id and timing."""

    async def test_response_has_trace_id_header(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health/live")
            assert "x-trace-id" in response.headers
            # Should be a UUID-like string
            trace_id = response.headers["x-trace-id"]
            assert len(trace_id) > 10

    async def test_custom_trace_id_propagated(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/health/live", headers={"x-trace-id": "custom-trace-123"}
            )
            assert response.headers["x-trace-id"] == "custom-trace-123"

    async def test_auto_generated_trace_id_when_no_header(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health/live")
            trace_id = response.headers.get("x-trace-id")
            assert trace_id is not None
            assert trace_id != ""


@pytest.mark.asyncio
class TestRouteRegistration:
    """Test that all Phase 0 routes are registered."""

    async def test_health_routes_registered(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/health/live")
            assert response.status_code == 200

    async def test_auth_routes_registered(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # POST without body should get 422, not 404
            response = await client.post("/api/v1/auth/register")
            assert response.status_code == 422  # validation error, not 404

    async def test_settings_routes_registered(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Without auth should get 401, not 404
            response = await client.get("/api/v1/settings")
            assert response.status_code == 401

    async def test_unknown_route_returns_404(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/nonexistent")
            assert response.status_code in [404, 405]


@pytest.mark.asyncio
class TestCORSMiddleware:
    """Test CORS middleware is configured."""

    async def test_cors_headers_on_options_request(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.options(
                "/api/health/live",
                headers={
                    "origin": "http://localhost:3000",
                    "access-control-request-method": "GET",
                },
            )
            # Should have CORS headers
            assert "access-control-allow-origin" in response.headers


@pytest.mark.asyncio
class TestActiveWebsockets:
    """Test active websocket tracking structure."""

    async def test_active_websockets_is_set(self):
        from app.main import active_websockets

        assert isinstance(active_websockets, set)


@pytest.mark.asyncio
class TestStandardErrorResponses:
    """Test that all error responses use the standard error format."""

    async def test_404_returns_standard_error(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/nonexistent")
            assert response.status_code == 404
            body = response.json()
            assert "error" in body
            assert body["error"]["code"] == "NOT_FOUND"
            assert "trace_id" in body["error"]

    async def test_422_returns_validation_details(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # POST to auth/login with invalid body triggers RequestValidationError
            response = await client.post(
                "/api/v1/auth/login",
                json={},  # missing required fields
            )
            assert response.status_code == 422
            body = response.json()
            assert "error" in body
            assert body["error"]["code"] == "VALIDATION_ERROR"
            assert body["error"]["details"] is not None
            assert len(body["error"]["details"]) > 0

    async def test_401_returns_standard_error(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Access protected endpoint without auth
            response = await client.get("/api/v1/chat/conversations")
            assert response.status_code == 401
            body = response.json()
            assert "error" in body
            assert body["error"]["code"] == "UNAUTHORIZED"
