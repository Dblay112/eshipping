# ═══════════════════════════════════════════════════════════════
#  CORE — SHARED PERMISSIONS UTILITIES
# ═══════════════════════════════════════════════════════════════


def _get_user_desks(user):
    """
    Get all desks assigned to user (supports both legacy and multi-desk formats).

    Handles backward compatibility with legacy single-desk field while supporting
    the new multi-desk JSONField for staff assigned to multiple departments.

    Multi-Desk System:
    - New format: user.desks = ['OPERATIONS', 'EBOOKING'] (JSONField)
    - Legacy format: user.desk = 'OPERATIONS' (CharField)
    - Both formats supported simultaneously during migration period

    Permission Logic:
    - Checks new 'desks' JSONField first (multi-desk assignments)
    - Falls back to legacy 'desk' CharField (single desk)
    - Excludes 'OTHER' desk (legacy placeholder for non-desk staff)
    - Returns empty set for unauthenticated users

    Historical Note:
    - SECURITY FIX (2026-03-02): Added multi-desk support
    - Previously only checked single 'desk' field
    - Now combines both fields for complete desk list

    Args:
        user: Account instance to check desk assignments for

    Returns:
        set: Set of desk codes (e.g., {'OPERATIONS', 'EBOOKING'})
             Empty set if user has no desk assignments

    Example:
        >>> _get_user_desks(operations_user)
        {'OPERATIONS'}
        >>> _get_user_desks(multi_desk_user)
        {'OPERATIONS', 'EBOOKING', 'DECLARATION'}
        >>> _get_user_desks(unauthenticated_user)
        set()

    Usage:
        In permission functions:
        ```python
        def can_manage_bookings(user):
            user_desks = _get_user_desks(user)
            return 'EBOOKING' in user_desks or user.is_superuser
        ```
    """
    if not user.is_authenticated:
        return set()

    desks = set()

    # Check new multi-desk field (JSONField)
    if hasattr(user, 'desks') and user.desks:
        desks.update(user.desks)

    # Check legacy single desk field (for backward compatibility)
    if hasattr(user, 'desk') and user.desk and user.desk != 'OTHER':
        desks.add(user.desk)

    return desks
