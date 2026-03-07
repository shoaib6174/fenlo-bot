"""Unit tests for route-level CORS middleware."""

from app.middleware.cors import WIDGET_ROUTES, is_widget_route


class TestWidgetRouteDetection:
    """Test widget route detection logic."""

    def test_widget_route_detected(self):
        assert is_widget_route("/api/v1/widget/chat") is True
        assert is_widget_route("/api/v1/widget/config") is True

    def test_chat_stream_detected(self):
        assert is_widget_route("/api/v1/chat/stream") is True
        assert is_widget_route("/api/v1/chat/stream/ws") is True

    def test_webhooks_detected(self):
        assert is_widget_route("/api/v1/webhooks/incoming") is True

    def test_admin_routes_not_widget(self):
        assert is_widget_route("/api/v1/settings") is False
        assert is_widget_route("/api/v1/auth/login") is False
        assert is_widget_route("/api/v1/chat/send") is False

    def test_widget_route_list_complete(self):
        assert "/api/v1/widget" in WIDGET_ROUTES
        assert "/api/v1/chat/stream" in WIDGET_ROUTES
        assert "/api/v1/webhooks" in WIDGET_ROUTES
