"""Extended tests for RouteCORSMiddleware — integration-level CORS header tests."""

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.middleware.cors import RouteCORSMiddleware


async def _dummy(request: Request):
    return JSONResponse({"ok": True})


def _make_app():
    """Build a minimal Starlette app with RouteCORSMiddleware for testing."""
    app = Starlette(
        routes=[
            Route("/api/v1/widget/chat", _dummy),
            Route("/api/v1/chat/stream", _dummy),
            Route("/api/v1/settings", _dummy),
            Route("/api/v1/auth/login", _dummy, methods=["POST"]),
        ],
    )
    app.add_middleware(RouteCORSMiddleware)
    return app


@pytest.fixture
def app():
    return _make_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestWidgetCORS:
    """Widget routes should return Access-Control-Allow-Origin: *."""

    @pytest.mark.asyncio
    async def test_widget_allows_any_origin(self, client):
        r = await client.get(
            "/api/v1/widget/chat",
            headers={"origin": "https://evil.com"},
        )
        assert r.headers["access-control-allow-origin"] == "*"

    @pytest.mark.asyncio
    async def test_widget_preflight(self, client):
        r = await client.options(
            "/api/v1/widget/chat",
            headers={
                "origin": "https://evil.com",
                "access-control-request-method": "POST",
            },
        )
        assert r.status_code == 204
        assert r.headers["access-control-allow-origin"] == "*"
        assert "access-control-allow-methods" in r.headers

    @pytest.mark.asyncio
    async def test_stream_allows_any_origin(self, client):
        r = await client.get(
            "/api/v1/chat/stream",
            headers={"origin": "https://external-page.com"},
        )
        assert r.headers["access-control-allow-origin"] == "*"


class TestAdminCORS:
    """Admin routes should only allow configured origins."""

    @pytest.mark.asyncio
    async def test_admin_allows_configured_origin(self, client):
        r = await client.get(
            "/api/v1/settings",
            headers={"origin": "http://localhost:3000"},
        )
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert r.headers.get("access-control-allow-credentials") == "true"

    @pytest.mark.asyncio
    async def test_admin_blocks_unknown_origin(self, client):
        r = await client.get(
            "/api/v1/settings",
            headers={"origin": "https://evil.com"},
        )
        assert "access-control-allow-origin" not in r.headers

    @pytest.mark.asyncio
    async def test_admin_preflight_allowed_origin(self, client):
        r = await client.options(
            "/api/v1/settings",
            headers={
                "origin": "http://localhost:3000",
                "access-control-request-method": "GET",
            },
        )
        assert r.status_code == 204
        assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert r.headers.get("access-control-allow-credentials") == "true"

    @pytest.mark.asyncio
    async def test_admin_preflight_blocked_origin(self, client):
        r = await client.options(
            "/api/v1/settings",
            headers={
                "origin": "https://evil.com",
                "access-control-request-method": "GET",
            },
        )
        assert "access-control-allow-origin" not in r.headers
