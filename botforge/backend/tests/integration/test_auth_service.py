"""Integration tests for auth service layer (create_user_with_workspace, authenticate_user).

These test the database-interacting functions in services/auth.py
that aren't covered by the existing unit tests (which only test
password hashing and JWT encode/decode).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.services.auth import (
    authenticate_user,
    create_user_with_workspace,
    hash_password,
)


@pytest.mark.asyncio
class TestCreateUserWithWorkspace:
    """Test user + workspace creation service."""

    async def test_creates_user(self, db_session: AsyncSession):
        user, workspace = await create_user_with_workspace(
            db=db_session,
            email="new@example.com",
            password="SecurePass123!",
            name="New User",
        )
        assert user.email == "new@example.com"
        assert user.name == "New User"
        assert user.id is not None

    async def test_creates_workspace_for_user(self, db_session: AsyncSession):
        user, workspace = await create_user_with_workspace(
            db=db_session,
            email="ws@example.com",
            password="SecurePass123!",
            name="WS User",
        )
        assert workspace.id is not None
        assert workspace.owner_id == user.id
        assert "WS User" in workspace.name

    async def test_adds_user_as_owner_member(self, db_session: AsyncSession):
        user, workspace = await create_user_with_workspace(
            db=db_session,
            email="owner@example.com",
            password="SecurePass123!",
            name="Owner",
        )
        from sqlalchemy import select

        stmt = select(WorkspaceMember).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.workspace_id == workspace.id,
        )
        result = await db_session.execute(stmt)
        member = result.scalar_one_or_none()
        assert member is not None
        assert member.role == "owner"

    async def test_hashes_password(self, db_session: AsyncSession):
        user, _ = await create_user_with_workspace(
            db=db_session,
            email="hash@example.com",
            password="MyPassword123",
            name="Hash User",
        )
        assert user.password_hash != "MyPassword123"
        assert user.password_hash.startswith("$2b$")

    async def test_duplicate_email_raises_value_error(self, db_session: AsyncSession):
        await create_user_with_workspace(
            db=db_session,
            email="dup@example.com",
            password="Pass123!",
            name="First",
        )
        with pytest.raises(ValueError, match="already exists"):
            await create_user_with_workspace(
                db=db_session,
                email="dup@example.com",
                password="Pass456!",
                name="Second",
            )


@pytest.mark.asyncio
class TestAuthenticateUser:
    """Test user authentication service."""

    async def test_valid_credentials_returns_user_workspace_role(self, db_session: AsyncSession):
        await create_user_with_workspace(
            db=db_session,
            email="auth@example.com",
            password="CorrectPass123!",
            name="Auth User",
        )
        result = await authenticate_user(
            db=db_session,
            email="auth@example.com",
            password="CorrectPass123!",
        )
        assert result is not None
        user, workspace, role = result
        assert user.email == "auth@example.com"
        assert workspace is not None
        assert role == "owner"

    async def test_wrong_password_returns_none(self, db_session: AsyncSession):
        await create_user_with_workspace(
            db=db_session,
            email="wrong@example.com",
            password="RightPass123!",
            name="Wrong Pass",
        )
        result = await authenticate_user(
            db=db_session,
            email="wrong@example.com",
            password="WrongPass123!",
        )
        assert result is None

    async def test_nonexistent_email_returns_none(self, db_session: AsyncSession):
        result = await authenticate_user(
            db=db_session,
            email="ghost@example.com",
            password="AnyPass123!",
        )
        assert result is None

    async def test_user_without_workspace_member_returns_none(self, db_session: AsyncSession):
        """User exists but has no workspace membership."""
        from uuid import uuid4

        user = User(
            id=uuid4(),
            email="orphan@example.com",
            password_hash=hash_password("Pass123!"),
            name="Orphan",
        )
        db_session.add(user)
        await db_session.commit()

        result = await authenticate_user(
            db=db_session,
            email="orphan@example.com",
            password="Pass123!",
        )
        assert result is None
