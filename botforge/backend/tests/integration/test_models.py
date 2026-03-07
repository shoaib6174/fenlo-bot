"""Integration tests for database models."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember


@pytest.mark.asyncio
class TestModels:
    """Test database models and relationships."""

    async def test_user_create_and_query(self, db_session: AsyncSession):
        """Test creating and querying a user."""
        user = User(id=uuid4(), email="test@example.com", password_hash="hashed", name="Test User")
        db_session.add(user)
        await db_session.commit()

        result = await db_session.execute(select(User).where(User.email == "test@example.com"))
        queried_user = result.scalar_one_or_none()

        assert queried_user is not None
        assert queried_user.email == "test@example.com"
        assert queried_user.name == "Test User"

    async def test_workspace_create(self, db_session: AsyncSession):
        """Test creating a workspace."""
        user = User(id=uuid4(), email="owner@example.com", password_hash="hashed", name="Owner")
        db_session.add(user)
        await db_session.flush()

        workspace = Workspace(id=uuid4(), owner_id=user.id, name="Test Workspace")
        db_session.add(workspace)
        await db_session.commit()

        result = await db_session.execute(select(Workspace).where(Workspace.owner_id == user.id))
        queried_ws = result.scalar_one_or_none()

        assert queried_ws is not None
        assert queried_ws.name == "Test Workspace"

    async def test_workspace_member_relationship(self, db_session: AsyncSession):
        """Test workspace member relationship."""
        user = User(id=uuid4(), email="member@example.com", password_hash="hashed", name="Member")
        workspace = Workspace(id=uuid4(), owner_id=user.id, name="Member Workspace")
        db_session.add_all([user, workspace])
        await db_session.flush()

        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner")
        db_session.add(member)
        await db_session.commit()

        result = await db_session.execute(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)
        )
        queried_member = result.scalar_one_or_none()

        assert queried_member is not None
        assert queried_member.role == "owner"

    async def test_conversation_create(self, db_session: AsyncSession):
        """Test creating a conversation."""
        user = User(id=uuid4(), email="conv@example.com", password_hash="hashed", name="Conv User")
        workspace = Workspace(id=uuid4(), owner_id=user.id, name="Conv Workspace")
        db_session.add_all([user, workspace])
        await db_session.flush()

        conversation = Conversation(
            id=uuid4(), workspace_id=workspace.id, channel="web", status="active"
        )
        db_session.add(conversation)
        await db_session.commit()

        result = await db_session.execute(
            select(Conversation).where(Conversation.workspace_id == workspace.id)
        )
        queried_conv = result.scalar_one_or_none()

        assert queried_conv is not None
        assert queried_conv.channel == "web"

    async def test_message_create(self, db_session: AsyncSession):
        """Test creating a message."""
        user = User(id=uuid4(), email="msg@example.com", password_hash="hashed", name="Msg User")
        workspace = Workspace(id=uuid4(), owner_id=user.id, name="Msg Workspace")
        db_session.add_all([user, workspace])
        await db_session.flush()

        conversation = Conversation(
            id=uuid4(), workspace_id=workspace.id, channel="web", status="active"
        )
        db_session.add(conversation)
        await db_session.flush()

        message = Message(
            id=uuid4(), conversation_id=conversation.id, role="user", content="Hello, bot!"
        )
        db_session.add(message)
        await db_session.commit()

        result = await db_session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        queried_msg = result.scalar_one_or_none()

        assert queried_msg is not None
        assert queried_msg.content == "Hello, bot!"

    async def test_knowledge_base_create(self, db_session: AsyncSession):
        """Test creating a knowledge base."""
        user = User(id=uuid4(), email="kb@example.com", password_hash="hashed", name="KB User")
        workspace = Workspace(id=uuid4(), owner_id=user.id, name="KB Workspace")
        db_session.add_all([user, workspace])
        await db_session.flush()

        kb = KnowledgeBase(
            id=uuid4(), workspace_id=workspace.id, name="Test KB", description="Test knowledge base"
        )
        db_session.add(kb)
        await db_session.commit()

        result = await db_session.execute(
            select(KnowledgeBase).where(KnowledgeBase.workspace_id == workspace.id)
        )
        queried_kb = result.scalar_one_or_none()

        assert queried_kb is not None
        assert queried_kb.name == "Test KB"

    async def test_cascade_delete_workspace(self, db_session: AsyncSession):
        """Test cascade delete when workspace is deleted."""
        user = User(
            id=uuid4(), email="cascade@example.com", password_hash="hashed", name="Cascade User"
        )
        workspace = Workspace(id=uuid4(), owner_id=user.id, name="Cascade Workspace")
        db_session.add_all([user, workspace])
        await db_session.flush()

        member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="owner")
        db_session.add(member)
        await db_session.commit()

        # Delete workspace
        await db_session.delete(workspace)
        await db_session.commit()

        # Member should be cascade deleted
        result = await db_session.execute(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace.id)
        )
        queried_member = result.scalar_one_or_none()

        assert queried_member is None

    async def test_jsonb_fields(self, db_session: AsyncSession):
        """Test JSONB field storage and retrieval."""
        user = User(
            id=uuid4(), email="jsonb@example.com", password_hash="hashed", name="JSONB User"
        )
        workspace = Workspace(
            id=uuid4(),
            owner_id=user.id,
            name="JSONB Workspace",
            settings={"bot_name": "Test Bot", "personality": "friendly", "rag_enabled": True},
        )
        db_session.add_all([user, workspace])
        await db_session.commit()

        result = await db_session.execute(select(Workspace).where(Workspace.id == workspace.id))
        queried_ws = result.scalar_one_or_none()

        assert queried_ws is not None
        assert queried_ws.settings["bot_name"] == "Test Bot"
        assert queried_ws.settings["rag_enabled"] is True
