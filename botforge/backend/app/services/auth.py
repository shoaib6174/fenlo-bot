"""
Authentication service for BotForge.
Handles password hashing, JWT generation, and user authentication.
Spec: docs/plans/phase-0-scaffold.md § 0b.2
"""

import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Bcrypt has a 72-byte limit, but Pydantic validation ensures max 72 chars
    return pwd_context.hash(password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User's UUID
        workspace_id: Workspace UUID
        role: User's role in the workspace
        expires_delta: Token expiration time (default: 24 hours)

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(hours=24)

    to_encode = {
        "sub": str(user_id),
        "workspace_id": str(workspace_id),
        "role": role,
        "exp": expire,
    }

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.

    Returns:
        Token payload if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


async def create_user_with_workspace(
    db: AsyncSession,
    email: str,
    password: str,
    name: str,
) -> tuple[User, Workspace]:
    """
    Create a new user with a default workspace.
    User is automatically added as owner of the workspace.

    Args:
        db: Database session
        email: User's email
        password: Plain text password (will be hashed)
        name: User's name

    Returns:
        Tuple of (User, Workspace)
    """
    # Check if user already exists
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise ValueError("User with this email already exists")

    # Hash password
    password_hash = hash_password(password)

    # Create user
    user = User(
        email=email,
        password_hash=password_hash,
        name=name,
    )
    db.add(user)
    await db.flush()  # Get user.id

    # Create default workspace
    workspace = Workspace(
        owner_id=user.id,
        name=f"{name}'s Workspace",
    )
    db.add(workspace)
    await db.flush()  # Get workspace.id

    # Add user as owner in workspace_members
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role="owner",
    )
    db.add(member)

    await db.commit()
    await db.refresh(user)
    await db.refresh(workspace)

    return user, workspace


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> tuple[User, Workspace, str] | None:
    """
    Authenticate a user by email and password.

    Args:
        db: Database session
        email: User's email
        password: Plain text password

    Returns:
        Tuple of (User, Workspace, role) if authentication successful, None otherwise
    """
    # Get user
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None

    # Verify password
    if not verify_password(password, user.password_hash):
        return None

    # Get user's primary workspace (first one they're a member of)
    stmt = (
        select(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(WorkspaceMember.invited_at)
        .limit(1)
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        return None

    # Get workspace
    stmt = select(Workspace).where(Workspace.id == member.workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        return None

    return user, workspace, member.role
