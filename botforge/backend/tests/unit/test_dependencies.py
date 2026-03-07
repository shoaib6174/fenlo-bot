"""Unit tests for app/dependencies.py."""

from app.dependencies import get_db


class TestDependencies:
    """Test dependency injection helpers."""

    def test_get_current_user_importable_from_auth(self):
        """get_current_user should be importable from app.api.auth."""
        from app.api.auth import get_current_user

        assert callable(get_current_user)

    def test_get_db_is_async_generator_function(self):
        """get_db should be an async generator function."""
        import inspect

        assert inspect.isasyncgenfunction(get_db)
