"""
Tool Authorization Decorator - Role-Based Access Control
========================================================
Simple decorator to restrict tool access by role using existing auth infrastructure.

Usage:
    @mcp.tool(name="export_database_table", description="...")
    @require_roles(['admin', 'dba'])
    def export_database_table(...):
        ...

Roles: admin (full access), dba (database exports), user (standard smoke tests)
"""

from functools import wraps
from typing import List
import logging

logger = logging.getLogger(__name__)


def get_current_user_role() -> str:
    """
    Get current user's role from context.

    Returns:
        Role string (admin, dba, user, or anonymous)
    """
    try:
        from tools.feedback_context import get_tracking_info

        tracking = get_tracking_info()
        role = tracking.get("client_role", "anonymous")

        logger.debug(f"Current user role: {role}")
        return role.lower()

    except Exception as e:
        logger.error(f"Error getting user role: {e}")
        return "anonymous"


def get_user_info() -> dict:
    """
    Get complete user information from context.

    Returns:
        Dict with client_id, session_id, and role
    """
    try:
        from tools.feedback_context import get_tracking_info

        tracking = get_tracking_info()
        client_id = tracking.get("client_id", "anonymous")
        session_id = tracking.get("session_id", "unknown")
        role = tracking.get("client_role", "anonymous")

        return {
            "client_id": client_id,
            "session_id": session_id,
            "role": role.lower()
        }

    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return {
            "client_id": "anonymous",
            "session_id": "unknown",
            "role": "anonymous"
        }


def require_roles(allowed_roles: List[str]):
    """
    Decorator to restrict tool access by role.

    Args:
        allowed_roles: List of roles that can access this tool
                      Example: ['admin', 'dba']

    Usage:
        @mcp.tool(name="export_database_table", description="Export database table. **Requires admin or dba role.**")
        @require_roles(['admin', 'dba'])
        def export_database_table(session_id: str, db_type: str, table_name: str):
            ...

    Access Rules:
        - Admin role always has access to everything
        - Tool executes if user's role is in allowed_roles
        - Access denied returns error dict (doesn't raise exception)

    Returns:
        Decorator function that wraps the tool
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_info = get_user_info()
            user_role = user_info.get("role", "anonymous")
            client_id = user_info.get("client_id", "anonymous")

            # Get function name safely
            func_name = getattr(func, '__name__', 'unknown_tool')

            # Admin always has access
            if user_role == "admin":
                logger.info(f"🔓 Admin access: {client_id} → {func_name}")
                return func(*args, **kwargs)

            # Normalize allowed roles for case-insensitive comparison
            allowed_roles_lower = [role.lower() for role in allowed_roles]

            # Check if user's role is in allowed roles
            if user_role not in allowed_roles_lower:
                logger.warning(
                    f"🚫 Access denied: {client_id} (role: {user_role}) "
                    f"tried to access {func_name} (requires: {allowed_roles})"
                )
                return {
                    "error": "insufficient_permissions",
                    "message": f"This tool requires one of these roles: {', '.join(allowed_roles)}",
                    "your_role": user_role,
                    "required_roles": allowed_roles,
                    "tool_name": func_name,
                    "hint": "Contact your administrator for role assignment"
                }

            # Access granted
            logger.info(f"✅ Access granted: {client_id} (role: {user_role}) → {func_name}")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def check_role_access(required_roles: List[str]) -> tuple[bool, str]:
    """
    Check if current user has access to a specific role requirement.

    Useful for manual role checking without decorator.

    Args:
        required_roles: List of roles that grant access

    Returns:
        Tuple of (has_access: bool, message: str)

    Example:
        has_access, msg = check_role_access(['admin', 'dba'])
        if not has_access:
            return {"error": msg}
    """
    user_role = get_current_user_role()

    # Admin always has access
    if user_role == "admin":
        return True, "Admin access granted"

    # Check if role is in required roles
    required_roles_lower = [role.lower() for role in required_roles]
    if user_role in required_roles_lower:
        return True, f"Role '{user_role}' has access"

    return False, f"Access denied. Requires one of: {', '.join(required_roles)}"
