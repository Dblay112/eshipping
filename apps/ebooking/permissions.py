# ═══════════════════════════════════════════════════════════════
#  EBOOKING — PERMISSIONS
# ═══════════════════════════════════════════════════════════════

from apps.core.permissions import _get_user_desks


def can_manage_bookings(user):
    """
    Check if user can create or edit booking records.

    Permission Logic:
    - EBOOKING desk: Full access to booking management
    - Superuser: Full access (admin override)
    - All other desks: No access (read-only via booking list)

    Historical Note:
    - PERMISSION FIX (2026-03-02): Removed MANAGER from this check
    - MANAGER desk can only manage schedules/staff/terminals
    - If manager needs ebooking access, assign them to EBOOKING desk

    Args:
        user: Account instance to check permissions for

    Returns:
        bool: True if user can manage bookings, False otherwise

    Example:
        >>> can_manage_bookings(ebooking_user)
        True
        >>> can_manage_bookings(operations_user)
        False

    Usage:
        In views:
        ```python
        if not can_manage_bookings(request.user):
            messages.error(request, "Only ebooking desk can create bookings.")
            return redirect('booking_list')
        ```
    """
    if not user.is_authenticated:
        return False

    user_desks = _get_user_desks(user)
    return bool('EBOOKING' in user_desks) or bool(user.is_superuser)
