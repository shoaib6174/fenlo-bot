"""Unit tests for configuration management."""

import pytest

from app.config import Settings


class TestConfig:
    """Test configuration loading and validation."""

    def test_loads_from_env(self, monkeypatch):
        """Test that configuration loads from environment variables."""
        monkeypatch.setenv("database_url", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("jwt_secret", "test-secret-key-12345")

        settings = Settings()

        # Auto-fixed to asyncpg format, no ssl for localhost
        assert settings.database_url == "postgresql+asyncpg://test:test@localhost/test"
        assert settings.jwt_secret == "test-secret-key-12345"

    def test_defaults_work(self):
        """Test that default values are applied when env vars are missing."""
        settings = Settings()

        assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]
        assert settings.cors_origins_list is not None
        assert isinstance(settings.cors_origins_list, list)

    def test_validates_database_url(self, monkeypatch):
        """Test that non-postgresql URLs pass through unchanged."""
        monkeypatch.setenv("database_url", "invalid-url")

        settings = Settings()
        assert settings.database_url == "invalid-url"

    def test_validates_jwt_secret(self):
        """Test JWT secret validation."""
        settings = Settings()

        assert hasattr(settings, "jwt_secret")
        assert len(settings.jwt_secret) > 0


class TestDatabaseUrlNormalization:
    """Test DATABASE_URL auto-fix logic."""

    def test_adds_asyncpg_driver(self, monkeypatch):
        """postgresql:// with remote host gets asyncpg driver + ssl=require."""
        monkeypatch.setenv("database_url", "postgresql://user:pass@host/db")
        s = Settings()
        assert s.database_url == "postgresql+asyncpg://user:pass@host/db?ssl=require"

    def test_adds_asyncpg_to_postgres_shorthand(self, monkeypatch):
        """postgres:// (shorthand) is converted to postgresql+asyncpg:// with ssl."""
        monkeypatch.setenv("database_url", "postgres://user:pass@host/db")
        s = Settings()
        assert s.database_url == "postgresql+asyncpg://user:pass@host/db?ssl=require"

    def test_preserves_correct_format(self, monkeypatch):
        """postgresql+asyncpg:// with remote host gets ssl=require added."""
        monkeypatch.setenv("database_url", "postgresql+asyncpg://user:pass@host/db")
        s = Settings()
        assert s.database_url == "postgresql+asyncpg://user:pass@host/db?ssl=require"

    def test_no_ssl_for_localhost(self, monkeypatch):
        """localhost connections do NOT get ssl=require."""
        monkeypatch.setenv("database_url", "postgresql://user:pass@localhost/db")
        s = Settings()
        assert s.database_url == "postgresql+asyncpg://user:pass@localhost/db"
        assert "ssl" not in s.database_url

    def test_no_ssl_for_127(self, monkeypatch):
        """127.0.0.1 connections do NOT get ssl=require."""
        monkeypatch.setenv("database_url", "postgresql://user:pass@127.0.0.1/db")
        s = Settings()
        assert s.database_url == "postgresql+asyncpg://user:pass@127.0.0.1/db"
        assert "ssl" not in s.database_url

    def test_strips_sslmode_adds_ssl(self, monkeypatch):
        """?sslmode=require is stripped and replaced with ?ssl=require for remote hosts."""
        monkeypatch.setenv("database_url", "postgresql://user:pass@host/db?sslmode=require")
        s = Settings()
        assert s.database_url == "postgresql+asyncpg://user:pass@host/db?ssl=require"
        assert "sslmode" not in s.database_url

    def test_strips_channel_binding(self, monkeypatch):
        """channel_binding param is stripped, ssl=require added for remote host."""
        monkeypatch.setenv(
            "database_url",
            "postgresql://user:pass@host/db?sslmode=require&channel_binding=require",
        )
        s = Settings()
        assert s.database_url == "postgresql+asyncpg://user:pass@host/db?ssl=require"

    def test_preserves_supported_params(self, monkeypatch):
        """Non-problematic query params are preserved alongside ssl."""
        monkeypatch.setenv(
            "database_url",
            "postgresql://user:pass@host/db?application_name=botforge&sslmode=require",
        )
        s = Settings()
        assert "application_name=botforge" in s.database_url
        assert "ssl=require" in s.database_url
        assert "sslmode" not in s.database_url

    def test_does_not_duplicate_ssl(self, monkeypatch):
        """If ssl=require already present, don't add it again."""
        monkeypatch.setenv(
            "database_url",
            "postgresql+asyncpg://user:pass@host/db?ssl=require",
        )
        s = Settings()
        assert s.database_url.count("ssl=require") == 1

    def test_sync_url_conversion_remote(self, monkeypatch):
        """database_url_sync swaps ssl→sslmode for remote hosts."""
        monkeypatch.setenv(
            "database_url", "postgresql://user:pass@mydb.us-east-1.rds.amazonaws.com/db"
        )
        s = Settings()
        sync = s.database_url_sync
        assert "psycopg2" in sync
        assert "sslmode=require" in sync
        assert "ssl=require" not in sync  # asyncpg param must be removed

    def test_sync_url_conversion_localhost(self, monkeypatch):
        """database_url_sync does NOT add sslmode for localhost."""
        monkeypatch.setenv("database_url", "postgresql://user:pass@localhost/db")
        s = Settings()
        assert s.database_url_sync == "postgresql+psycopg2://user:pass@localhost/db"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("", ""),
            (
                "postgresql+asyncpg://u:p@localhost/d",
                "postgresql+asyncpg://u:p@localhost/d",
            ),
            (
                "postgresql+asyncpg://u:p@h/d",
                "postgresql+asyncpg://u:p@h/d?ssl=require",
            ),
            (
                "postgresql://u:p@h/d?sslmode=require",
                "postgresql+asyncpg://u:p@h/d?ssl=require",
            ),
            (
                "postgres://u:p@h/d?channel_binding=require",
                "postgresql+asyncpg://u:p@h/d?ssl=require",
            ),
        ],
    )
    def test_normalize_static_method(self, raw, expected):
        """Test _normalize_async_url directly."""
        assert Settings._normalize_async_url(raw) == expected
