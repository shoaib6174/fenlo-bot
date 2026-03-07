"""
Route-level CORS middleware.
Spec: docs/plans/phase-0-scaffold.md (Section 0a.7)

Widget routes must be embeddable on ANY domain (permissive CORS).
Admin routes must be restricted to configured origins (strict CORS).

This replaces FastAPI's global CORSMiddleware with a custom one that
applies different CORS policies based on the request path.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.config import settings

# Routes that allow any origin (widget, chat streaming, webhooks)
WIDGET_ROUTES = [
    "/api/v1/widget",
    "/api/v1/chat/stream",
    "/api/v1/webhooks",
    "/api/v1/voice/webhook",
    "/api/v1/public",
]

ALLOW_METHODS = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
ALLOW_HEADERS = "accept, accept-language, content-type, authorization, x-trace-id, x-csrf-token"


def is_widget_route(path: str) -> bool:
    """Check if the path is a widget route that allows any origin."""
    return any(path.startswith(route) for route in WIDGET_ROUTES)


class RouteCORSMiddleware(BaseHTTPMiddleware):
    """CORS middleware with per-route origin policies.

    Widget routes: Access-Control-Allow-Origin: * (no credentials)
    Admin routes: Access-Control-Allow-Origin: <configured> (with credentials)
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.allowed_origins = set(settings.cors_origins_list)

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")
        path = request.url.path
        widget = is_widget_route(path)

        # Handle preflight OPTIONS
        if request.method == "OPTIONS":
            response = Response(status_code=204)
            self._set_cors_headers(response, origin, path, widget, preflight=True)
            return response

        response = await call_next(request)
        self._set_cors_headers(response, origin, path, widget, preflight=False)
        return response

    def _set_cors_headers(
        self,
        response: Response,
        origin: str | None,
        path: str,
        widget: bool,
        preflight: bool,
    ) -> None:
        if widget:
            # Permissive: any origin, no credentials
            response.headers["access-control-allow-origin"] = "*"
        elif origin and origin in self.allowed_origins:
            # Strict: echo allowed origin, with credentials
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
            response.headers["vary"] = "Origin"
        else:
            # No matching origin — still set Vary so caches don't mix
            response.headers["vary"] = "Origin"
            return  # No CORS headers = browser blocks the request

        response.headers["access-control-allow-methods"] = ALLOW_METHODS

        if preflight:
            response.headers["access-control-allow-headers"] = ALLOW_HEADERS
            response.headers["access-control-max-age"] = "600"
