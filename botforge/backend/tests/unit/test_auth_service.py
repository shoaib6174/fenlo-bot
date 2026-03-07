"""Unit tests for authentication service."""

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.config import Settings
from app.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

settings = Settings()


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_returns_bcrypt(self):
        """Test that password hashing returns a bcrypt hash."""
        password = "test-password-123"
        hashed = hash_password(password)

        # Bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # Standard bcrypt hash length

    def test_verify_correct_password(self):
        """Test that correct password verification works."""
        password = "test-password-123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Test that wrong password verification fails."""
        password = "test-password-123"
        wrong = "wrong-password"
        hashed = hash_password(password)

        assert verify_password(wrong, hashed) is False

    def test_hash_is_not_plaintext(self):
        """Test that hash is not the plaintext password."""
        password = "test-password-123"
        hashed = hash_password(password)

        assert hashed != password


class TestJWT:
    """Test JWT token creation and validation."""

    def test_token_contains_user_id(self):
        """Test that JWT contains user_id in payload."""
        user_id = "user-123"
        workspace_id = "ws-456"
        role = "owner"

        token = create_access_token(user_id=user_id, workspace_id=workspace_id, role=role)

        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        assert payload["sub"] == user_id

    def test_token_contains_workspace_id(self):
        """Test that JWT contains workspace_id in payload."""
        user_id = "user-123"
        workspace_id = "ws-456"
        role = "owner"

        token = create_access_token(user_id=user_id, workspace_id=workspace_id, role=role)

        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        assert payload["workspace_id"] == workspace_id

    def test_token_has_expiry(self):
        """Test that JWT has expiry timestamp."""
        user_id = "user-123"
        workspace_id = "ws-456"
        role = "owner"

        token = create_access_token(user_id=user_id, workspace_id=workspace_id, role=role)

        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        assert "exp" in payload

        # Expiry should be in the future
        exp_datetime = datetime.fromtimestamp(payload["exp"], tz=UTC)
        assert exp_datetime > datetime.now(UTC)

    def test_decode_valid_token(self):
        """Test decoding a valid JWT token."""
        user_id = "user-123"
        workspace_id = "ws-456"
        role = "owner"

        token = create_access_token(user_id=user_id, workspace_id=workspace_id, role=role)

        payload = decode_access_token(token)

        assert payload["sub"] == user_id
        assert payload["workspace_id"] == workspace_id
        assert payload["role"] == role

    def test_decode_expired_returns_none(self):
        """Test that decoding expired token returns None."""
        user_id = "user-123"
        workspace_id = "ws-456"
        role = "owner"

        # Create token that expired 1 hour ago
        token = create_access_token(
            user_id=user_id, workspace_id=workspace_id, role=role, expires_delta=timedelta(hours=-1)
        )

        # decode_access_token returns None for expired tokens
        result = decode_access_token(token)
        assert result is None

    def test_decode_tampered_returns_none(self):
        """Test that decoding tampered token returns None."""
        user_id = "user-123"
        workspace_id = "ws-456"
        role = "owner"

        token = create_access_token(user_id=user_id, workspace_id=workspace_id, role=role)

        # Tamper with the token
        tampered = token[:-10] + "tampered00"

        # decode_access_token returns None for tampered tokens
        result = decode_access_token(tampered)
        assert result is None
