"""
Authentication API routes.
Endpoints: POST /register, POST /login, GET /me, GET /ws-token
Spec: docs/plans/phase-0-scaffold.md § 0b.2
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.middleware.rate_limiter import ip_rate_limit
from app.models.api_key import APIKey
from app.schemas.auth import (
    AuthResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services import auth as auth_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register", response_model=AuthResponse, status_code=201, dependencies=[Depends(ip_rate_limit)]
)
async def register(
    user_data: UserRegister,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    Creates user + workspace + workspace_member (owner).
    Sets httpOnly cookie with JWT.
    """
    try:
        user, workspace = await auth_service.create_user_with_workspace(
            db=db,
            email=user_data.email,
            password=user_data.password,
            name=user_data.name,
        )
    except ValueError as e:
        # User already exists with this email
        if "already exists" in str(e):
            raise HTTPException(status_code=409, detail=str(e)) from None
        # Other validation errors
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Create JWT token
    token = auth_service.create_access_token(
        user_id=user.id,
        workspace_id=workspace.id,
        role="owner",
    )

    # Set httpOnly cookie
    cookie_kwargs: dict = {
        "key": "access_token",
        "value": token,
        "httponly": True,
        "secure": settings.effective_cookie_secure,
        "samesite": settings.effective_cookie_samesite,
        "max_age": 86400,  # 24 hours
        "path": "/",
    }
    if settings.jwt_cookie_domain:
        cookie_kwargs["domain"] = settings.jwt_cookie_domain
    response.set_cookie(**cookie_kwargs)

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            role="owner",
        ),
        message="Registration successful",
    )


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(ip_rate_limit)])
async def login(
    credentials: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Login user.
    Verifies password and sets httpOnly cookie with JWT.
    """
    result = await auth_service.authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password,
    )

    if not result:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
        )

    user, workspace, role = result

    # Create JWT token
    token = auth_service.create_access_token(
        user_id=user.id,
        workspace_id=workspace.id,
        role=role,
    )

    # Set httpOnly cookie
    cookie_kwargs: dict = {
        "key": "access_token",
        "value": token,
        "httponly": True,
        "secure": settings.effective_cookie_secure,
        "samesite": settings.effective_cookie_samesite,
        "max_age": 86400,  # 24 hours
        "path": "/",
    }
    if settings.jwt_cookie_domain:
        cookie_kwargs["domain"] = settings.jwt_cookie_domain
    response.set_cookie(**cookie_kwargs)

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            workspace_id=workspace.id,
            workspace_name=workspace.name,
            role=role,
        ),
        message="Login successful",
    )


async def get_current_user_from_token(
    token: str,
    db: AsyncSession,
):
    """
    Get user from JWT token string (for WebSocket authentication).
    Returns a User object with workspace_id attribute attached.
    """
    # Decode token
    payload = auth_service.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    workspace_id = payload.get("workspace_id")
    role = payload.get("role")

    if not user_id or not workspace_id or not role:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
        )

    # Get user from database
    from sqlalchemy import select

    from app.models.user import User

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    # Attach workspace_id as attribute
    user.workspace_id = workspace_id
    return user


async def _authenticate_api_key(
    raw_key: str,
    db: AsyncSession,
) -> tuple | None:
    """Authenticate via API key. Returns (user, workspace_id, role) or None."""
    from app.models.user import User
    from app.models.workspace import Workspace

    # Hash the key for lookup
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    stmt = select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_revoked == False)  # noqa: E712
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        return None

    # Update usage tracking (fire-and-forget, don't block auth)
    await db.execute(
        update(APIKey)
        .where(APIKey.id == api_key.id)
        .values(last_used_at=datetime.now(UTC), request_count=APIKey.request_count + 1)
    )

    # Get workspace owner as the acting user
    ws_stmt = select(Workspace).where(Workspace.id == api_key.workspace_id)
    ws_result = await db.execute(ws_stmt)
    workspace = ws_result.scalar_one_or_none()
    if not workspace:
        return None

    user_stmt = select(User).where(User.id == workspace.owner_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        return None

    # Determine role from scopes
    scopes = api_key.scopes or ["read"]
    if "admin" in scopes:
        role = "admin"
    elif "chat" in scopes:
        role = "agent"
    else:
        role = "viewer"

    # Attach api_key metadata for downstream use
    user._api_key_id = str(api_key.id)
    user._api_key_scopes = scopes

    logger.info(
        "auth.api_key",
        api_key_prefix=api_key.prefix,
        workspace_id=str(api_key.workspace_id),
        scopes=scopes,
    )

    return user, api_key.workspace_id, role


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
):
    """
    Dependency to get the current authenticated user.
    Checks API key first (Authorization: Bearer bf_live_xxx or X-API-Key header),
    then falls through to JWT cookie auth.
    Returns tuple of (user, workspace_id, role).
    """
    # 1. Try API key auth from headers
    raw_key = None
    if x_api_key and x_api_key.startswith("bf_live_"):
        raw_key = x_api_key
    elif authorization and authorization.startswith("Bearer bf_live_"):
        raw_key = authorization.removeprefix("Bearer ").strip()

    if raw_key:
        result = await _authenticate_api_key(raw_key, db)
        if result:
            return result
        raise HTTPException(status_code=401, detail="Invalid API key")

    # 2. Fall through to JWT cookie auth
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    # Decode token
    payload = auth_service.decode_access_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    workspace_id = payload.get("workspace_id")
    role = payload.get("role")

    if not user_id or not workspace_id or not role:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
        )

    # Get user from database
    from app.models.user import User

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    return user, workspace_id, role


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user profile.
    Reads JWT from httpOnly cookie and returns user info.
    """
    user, workspace_id, role = current_user

    from sqlalchemy import select

    from app.models.workspace import Workspace

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        workspace_id=workspace.id,
        workspace_name=workspace.name,
        role=role,
    )


@router.get("/ws-token", response_model=TokenResponse)
async def get_websocket_token(
    current_user: tuple = Depends(get_current_user),
):
    """
    Get a short-lived token for WebSocket authentication.
    WebSocket connections use query parameter tokens since httpOnly cookies
    aren't reliably sent on WS upgrade in all browsers.
    Token expires in 5 minutes.
    """
    user, workspace_id, role = current_user

    # Create short-lived token (5 minutes)
    token = auth_service.create_access_token(
        user_id=user.id,
        workspace_id=workspace_id,
        role=role,
        expires_delta=timedelta(minutes=5),
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
    )


@router.post("/logout")
async def logout(response: Response):
    """
    Logout user by deleting the httpOnly cookie.
    """
    delete_kwargs: dict = {"key": "access_token", "path": "/"}
    if settings.jwt_cookie_domain:
        delete_kwargs["domain"] = settings.jwt_cookie_domain
    response.delete_cookie(**delete_kwargs)

    return {"message": "Logout successful"}
