"""
Pydantic schemas for authentication.
Spec: docs/plans/phase-0-scaffold.md § 0b.2
"""

import uuid

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Schema for user registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)  # bcrypt max is 72 bytes
    name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    """Schema for user login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response (used for WebSocket short-lived tokens)."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Schema for user profile response."""

    id: uuid.UUID
    email: str
    name: str
    workspace_id: uuid.UUID
    workspace_name: str
    role: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Schema for authentication response (register/login)."""

    user: UserResponse
    message: str
