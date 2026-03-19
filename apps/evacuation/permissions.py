# ═══════════════════════════════════════════════════════════════
#  EVACUATION — PERMISSIONS
# ═══════════════════════════════════════════════════════════════

from apps.core.permissions import _get_user_desks


def can_manage_evacuations(user):
    """
    Check if user can create, edit, or delete evacuation records.

    Permission Logic:
    - EVACUATION desk: Full access to all evacuation operations
    - Superuser: Full access (admin override)
    - All other desks: No access (read-only via evacuation_list)

    Historical Note:
    - PERMISSION FIX (2026-03-02): Removed MANAGER from this check
    - MANAGER desk can only manage schedules/staff/terminals
    - If manager needs evacuation access, assign them to EVACUATION desk

    Args:
        user: Account instance to check permissions for

    Returns:
        bool: True if user can manage evacuations, False otherwise

    Example:
        >>> can_manage_evacuations(evacuation_desk_user)
        True
        >>> can_manage_evacuations(operations_desk_user)
        False
    """
    if not user.is_authenticated:
        return False

    user_desks = _get_user_desks(user)
    return bool('EVACUATION' in user_desks) or bool(user.is_superuser)
