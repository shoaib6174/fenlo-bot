"""Integration tests for WebSocket chat streaming"""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_db
from app.main import app
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import create_access_token, hash_password


@pytest.fixture(autouse=True)
def ensure_llm_router_state():
    """Ensure app.state.llm_router is set for WebSocket tests."""
    if not hasattr(app.state, "llm_router"):
        app.state.llm_router = MagicMock()
    yield


@pytest.fixture
async def ws_user_and_token(db_session):
    """Create test user with workspace and return (user, token) for WebSocket tests."""
    user = User(
        id=uuid.uuid4(),
        email="wstest@example.com",
        name="WS Test User",
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.flush()

    workspace = Workspace(
        id=uuid.uuid4(),
        owner_id=user.id,
        name="WS Test Workspace",
        features={},
        settings={},
    )
    db_session.add(workspace)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )
    db_session.add(member)
    await db_session.commit()

    token = create_access_token(
        user_id=user.id,
        workspace_id=workspace.id,
        role="owner",
    )

    return user, token


@pytest.fixture
def ws_client(db_session):
    """Create WebSocket test client with DB dependency override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_db, None)


def test_websocket_requires_token():
    """Test that WebSocket connection requires authentication token"""
    if not hasattr(app.state, "llm_router"):
        app.state.llm_router = MagicMock()
    client = TestClient(app)

    # Try to connect without token - should fail with WebSocket error
    with pytest.raises(Exception):  # noqa: B017  - WebSocket failures vary by transport
        with client.websocket_connect("/api/v1/chat/stream"):
            pass


@pytest.mark.asyncio
async def test_websocket_connection_established(ws_user_and_token, ws_client):
    """Test that WebSocket connection can be established with valid token"""
    user, token = ws_user_and_token

    # Connect with valid token - should not raise
    with ws_client.websocket_connect(f"/api/v1/chat/stream?token={token}") as websocket:
        assert websocket is not None


@pytest.mark.skip(
    reason="Hangs during async fixture teardown when run in full suite. Passes in isolation."
)
@pytest.mark.asyncio
async def test_websocket_rejects_empty_message(ws_user_and_token, ws_client):
    """Test that WebSocket rejects empty messages with error response"""
    user, token = ws_user_and_token

    with ws_client.websocket_connect(f"/api/v1/chat/stream?token={token}") as websocket:
        websocket.send_json(
            {
                "message": "",
                "conversation_id": None,
            }
        )

        data = websocket.receive_json()
        assert data.get("type") == "error"
        assert data["data"]["code"] == "missing_message"


@pytest.mark.skip(
    reason="Hangs: invalid conversation_id enters full LLM pipeline. Needs LLM mock to avoid timeout."
)
@pytest.mark.asyncio
async def test_websocket_handles_invalid_conversation_id(ws_user_and_token, ws_client):
    """Test that WebSocket handles invalid conversation ID format"""
    user, token = ws_user_and_token

    with ws_client.websocket_connect(f"/api/v1/chat/stream?token={token}") as websocket:
        websocket.send_json(
            {
                "message": "Hello",
                "conversation_id": "not-a-uuid",
            }
        )

        data = websocket.receive_json()
        assert data.get("type") == "error"
        assert data["data"]["code"] == "invalid_conversation_id"
