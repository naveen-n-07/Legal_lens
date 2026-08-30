"""
auth.py - Import bridge for app.auth.rbac
"""

from app.auth.rbac import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    RequireRole,
    require_admin,
    require_inspector,
    require_reviewing_officer,
    require_inspector_or_officer,
    log_audit_action,
    VALID_ROLES
)

def require_role(roles: list):
    """
    Function-style guard helper for role checking.
    """
    return RequireRole(roles)
