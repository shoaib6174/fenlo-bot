"""Unit tests for RBAC (Role-Based Access Control)."""

from app.middleware.rbac import (
    ROLE_HIERARCHY,
    ROLE_PERMISSIONS,
    has_permission,
)


class TestRBAC:
    """Test role-based access control."""

    def test_owner_has_all_permissions(self):
        """Test that owner role has all permissions."""
        assert has_permission("owner", "settings") is True
        assert has_permission("owner", "billing") is True
        assert has_permission("owner", "members") is True
        assert has_permission("owner", "conversations") is True
        assert has_permission("owner", "analytics") is True
        assert has_permission("owner", "chat") is True

    def test_admin_cannot_delete_workspace(self):
        """Test that admin role cannot access billing/workspace deletion."""
        assert has_permission("admin", "billing") is False
        assert has_permission("admin", "settings") is True
        assert has_permission("admin", "members") is True

    def test_agent_can_access_conversations(self):
        """Test that agent role can access conversations."""
        assert has_permission("agent", "conversations") is True
        assert has_permission("agent", "chat") is True

    def test_agent_cannot_access_settings(self):
        """Test that agent role cannot access settings."""
        assert has_permission("agent", "settings") is False
        assert has_permission("agent", "members") is False
        assert has_permission("agent", "billing") is False

    def test_viewer_read_only(self):
        """Test that viewer role has read-only access."""
        assert has_permission("viewer", "analytics") is True
        assert has_permission("viewer", "chat") is False
        assert has_permission("viewer", "settings") is False
        assert has_permission("viewer", "conversations") is False

    def test_unknown_role_denied(self):
        """Test that unknown role is denied all permissions."""
        assert has_permission("unknown", "settings") is False
        assert has_permission("unknown", "chat") is False
        assert has_permission("invalid_role", "analytics") is False

    def test_role_hierarchy_correct(self):
        """Test that role hierarchy is properly defined."""
        assert ROLE_HIERARCHY["owner"] > ROLE_HIERARCHY["admin"]
        assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["agent"]
        assert ROLE_HIERARCHY["agent"] > ROLE_HIERARCHY["viewer"]

    def test_permission_matrix_exists(self):
        """Test that permission matrix is properly defined."""
        assert "owner" in ROLE_PERMISSIONS
        assert "admin" in ROLE_PERMISSIONS
        assert "agent" in ROLE_PERMISSIONS
        assert "viewer" in ROLE_PERMISSIONS

        # Check that each role has a set of permissions
        for role in ["owner", "admin", "agent", "viewer"]:
            assert isinstance(ROLE_PERMISSIONS[role], set)
