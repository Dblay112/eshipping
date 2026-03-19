# ═══════════════════════════════════════════════════════════════
#  DECLARATION — PERMISSIONS
# ═══════════════════════════════════════════════════════════════

from apps.core.permissions import _get_user_desks


def can_manage_declarations(user):
    """
    Check if user can create or edit declaration records.

    Permission Logic:
    - DECLARATION desk: Full access to declaration management
    - Superuser: Full access (admin override)
    - All other desks: No access (read-only via declaration list)

    Historical Note:
    - PERMISSION FIX (2026-03-02): Removed MANAGER from this check
    - MANAGER desk can only manage schedules/staff/terminals
    - If manager needs declaration access, assign them to DECLARATION desk

    Args:
        user: Account instance to check permissions for

    Returns:
        bool: True if user can manage declarations, False otherwise

    Example:
        >>> can_manage_declarations(declaration_user)
        True
        >>> can_manage_declarations(operations_user)
        False

    Usage:
        In views:
        ```python
        if not can_manage_declarations(request.user):
            messages.error(request, "Only declaration desk can create declarations.")
            return redirect('declaration_list')
        ```
    """
    if not user.is_authenticated:
        return False

    user_desks = _get_user_desks(user)
    return bool('DECLARATION' in user_desks) or bool(user.is_superuser)
