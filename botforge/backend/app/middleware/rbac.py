"""
Role-Based Access Control (RBAC) middleware.
Enforces role-based permissions on routes.
Spec: docs/plans/phase-0-scaffold.md § 0b.2a
"""

from fastapi import Depends, HTTPException

# Role hierarchy: owner > admin > agent > viewer
ROLE_HIERARCHY = {
    "owner": 4,
    "admin": 3,
    "agent": 2,
    "viewer": 1,
}

# Permission matrix: which roles can access which endpoints
ROLE_PERMISSIONS = {
    "owner": {"settings", "billing", "members", "conversations", "analytics", "chat"},
    "admin": {"settings", "members", "conversations", "analytics", "chat"},
    "agent": {"conversations", "chat"},
    "viewer": {"analytics"},
}


def require_role(required_role: str):
    """
    Dependency factory that creates a role checker dependency.

    Returns the User object after validating the role. This allows endpoints to use:
        current_user: User = Depends(require_role("agent"))
    to both enforce RBAC and get the authenticated user.

    Can also be used as a pure validator:
        _: None = Depends(require_role("admin"))
    or as a route-level dependency:
        @router.get("/", dependencies=[Depends(require_role("agent"))])

    Args:
        required_role: Minimum role required (owner, admin, agent, viewer)

    Returns:
        Dependency function that validates user's role and returns the User object

    Raises:
        HTTPException 403: If user doesn't have required role
    """
    from app.api.auth import get_current_user

    async def role_dependency(current_user: tuple = Depends(get_current_user)):
        """Validate user has required role and return User object."""
        user, workspace_id, user_role = current_user

        # Check if user's role meets minimum requirement
        user_level = ROLE_HIERARCHY.get(user_role, 0)
        required_level = ROLE_HIERARCHY.get(required_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"Insufficient permissions. Required role: {required_role}",
                },
            )

        # Attach workspace context to user for convenience
        user.workspace_id = workspace_id
        user.role = user_role

        return user

    return role_dependency


def has_permission(user_role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        user_role: User's role (owner, admin, agent, viewer)
        permission: Permission to check (settings, billing, etc.)

    Returns:
        True if role has permission, False otherwise
    """
    permissions = ROLE_PERMISSIONS.get(user_role, set())
    return permission in permissions


class RBACError(HTTPException):
    """Custom exception for RBAC violations."""

    def __init__(self, required_role: str, user_role: str):
        super().__init__(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": f"Insufficient permissions. Required role: {required_role}, your role: {user_role}",
            },
        )
