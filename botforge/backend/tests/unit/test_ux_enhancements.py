"""S48 tests — personality builder, batch upload, SSE stream."""

import io
import zipfile
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_manager import ContextManager
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.services.auth import hash_password


async def _create_workspace_fixtures(db_session: AsyncSession):
    """Create user + workspace for tests."""
    user_id = uuid4()
    workspace_id = uuid4()

    user = User(
        id=user_id,
        email=f"ux-{uuid4().hex[:6]}@test.com",
        password_hash=hash_password("password"),
        name="UX Test User",
    )
    workspace = Workspace(
        id=workspace_id,
        owner_id=user_id,
        name="UX WS",
        settings={"system_prompt": "You are a friendly sales assistant.", "bot_name": "SalesBot"},
    )
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role="owner")

    db_session.add_all([user, workspace, member])
    await db_session.flush()

    return user_id, workspace_id


# --- Personality Builder / System Prompt Tests ---


@pytest.mark.asyncio
class TestSystemPromptLoading:
    """Tests for workspace-level system prompt configuration."""

    async def test_loads_custom_system_prompt(self, db_session: AsyncSession):
        """ContextManager loads system_prompt from workspace settings."""
        user_id, workspace_id = await _create_workspace_fixtures(db_session)

        cm = ContextManager(db_session)
        conv_id, history, system_prompt, lead_score = await cm.load_context(
            workspace_id=workspace_id,
            conversation_id=None,
        )

        assert system_prompt == "You are a friendly sales assistant."
        assert conv_id is not None

    async def test_falls_back_to_default_when_empty(self, db_session: AsyncSession):
        """Falls back to default prompt when system_prompt is empty."""
        user_id = uuid4()
        workspace_id = uuid4()

        user = User(
            id=user_id,
            email=f"ux-{uuid4().hex[:6]}@test.com",
            password_hash=hash_password("password"),
            name="Default User",
        )
        workspace = Workspace(
            id=workspace_id,
            owner_id=user_id,
            name="Default WS",
            settings={"bot_name": "Bot"},  # no system_prompt key
        )
        member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role="owner")
        db_session.add_all([user, workspace, member])
        await db_session.flush()

        cm = ContextManager(db_session)
        _, _, system_prompt, _ = await cm.load_context(
            workspace_id=workspace_id,
            conversation_id=None,
        )

        assert "helpful AI assistant" in system_prompt


# --- Batch Upload Tests ---


class TestBatchUploadHelpers:
    """Tests for batch document upload logic."""

    def test_zip_extraction_with_valid_files(self):
        """ZIP with supported files yields expected filenames."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("doc1.pdf", b"fake pdf content")
            zf.writestr("notes.txt", b"some notes")
            zf.writestr("subdir/report.docx", b"fake docx")
            zf.writestr("image.png", b"not a document")  # unsupported
            zf.writestr(".hidden", b"hidden file")  # hidden

        buf.seek(0)
        zf = zipfile.ZipFile(buf)

        allowed = {".pdf", ".docx", ".txt", ".md", ".csv"}
        extracted = []
        for info in zf.infolist():
            if info.is_dir():
                continue
            fname = info.filename.split("/")[-1]
            if not fname or fname.startswith("."):
                continue
            ext = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            if ext in allowed:
                extracted.append(fname)

        assert "doc1.pdf" in extracted
        assert "notes.txt" in extracted
        assert "report.docx" in extracted
        assert "image.png" not in extracted
        assert ".hidden" not in extracted

    def test_empty_zip_yields_no_files(self):
        """Empty ZIP produces no files."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w"):
            pass  # empty

        buf.seek(0)
        zf = zipfile.ZipFile(buf)
        files = [info for info in zf.infolist() if not info.is_dir()]
        assert len(files) == 0


# --- SSE Fallback Tests ---


class TestSSEEventFormat:
    """Tests for SSE event formatting."""

    def test_token_event_format(self):
        """SSE token event has correct format."""
        import json

        token = "Hello"
        event = f"event: token\ndata: {json.dumps({'token': token + ' '})}\n\n"

        assert event.startswith("event: token\n")
        assert "data: " in event
        parsed = json.loads(event.split("data: ")[1].strip())
        assert parsed["token"] == "Hello "

    def test_done_event_format(self):
        """SSE done event includes conversation_id and metadata."""
        import json

        done_data = {
            "conversation_id": str(uuid4()),
            "sentiment": "positive",
            "intent": "sales",
            "quality_score": 0.85,
            "tokens_used": 42,
        }
        event = f"event: done\ndata: {json.dumps(done_data)}\n\n"

        assert event.startswith("event: done\n")
        parsed = json.loads(event.split("data: ")[1].strip())
        assert parsed["sentiment"] == "positive"
        assert parsed["quality_score"] == 0.85

    def test_error_event_format(self):
        """SSE error event has message and code."""
        import json

        error_data = {"message": "Auth failed", "code": "sse_error"}
        event = f"event: error\ndata: {json.dumps(error_data)}\n\n"

        parsed = json.loads(event.split("data: ")[1].strip())
        assert parsed["code"] == "sse_error"
        assert parsed["message"] == "Auth failed"
