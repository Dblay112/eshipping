# ═══════════════════════════════════════════════════════════════
#  OPERATIONS — PERMISSIONS
# ═══════════════════════════════════════════════════════════════

from apps.core.permissions import _get_user_desks


def can_manage_schedules(user):
    """
    Check if user can create or edit daily loading schedules.

    Permission Logic:
    - MANAGER desk: Full access to schedule management
    - Superuser: Full access (admin override)
    - All other desks: No access (read-only via schedule view)

    Args:
        user: Account instance to check permissions for

    Returns:
        bool: True if user can manage schedules, False otherwise

    Example:
        >>> can_manage_schedules(manager_user)
        True
        >>> can_manage_schedules(operations_user)
        False

    Usage:
        In views:
        ```python
        if not can_manage_schedules(request.user):
            messages.error(request, "Only managers can create schedules.")
            return redirect('schedule_view')
        ```
    """
    if not user.is_authenticated:
        return False

    user_desks = _get_user_desks(user)
    return (
        'MANAGER' in user_desks
        or bool(user.is_superuser)
    )


def can_manage_sd_records(user):
    """
    Check if user can create or edit SD records.

    Permission Logic:
    - OPERATIONS desk: Full access to SD record management
    - Superuser: Full access (admin override)
    - All other desks: No access (read-only via SD list)

    Historical Note:
    - PERMISSION FIX (2026-03-02): Removed MANAGER from this check
    - MANAGER desk can only manage schedules/staff/terminals
    - If manager needs operations access, assign them to OPERATIONS desk

    Args:
        user: Account instance to check permissions for

    Returns:
        bool: True if user can manage SD records, False otherwise

    Example:
        >>> can_manage_sd_records(operations_user)
        True
        >>> can_manage_sd_records(manager_user)
        False

    Usage:
        In views:
        ```python
        if not can_manage_sd_records(request.user):
            messages.error(request, "Only operations desk can create SD records.")
            return redirect('operations_list')
        ```
    """
    if not user.is_authenticated:
        return False

    user_desks = _get_user_desks(user)
    return bool('OPERATIONS' in user_desks) or bool(user.is_superuser)


def is_terminal_supervisor(user):
    """
    Check if user is assigned as supervisor on any terminal.

    Terminal supervisors can approve/reject tallies for their assigned terminals.
    Multiple supervisors can be assigned to the same terminal.

    Permission Logic:
    - Explicitly assigned as terminal supervisor: Can approve tallies
    - Superuser: Can approve all tallies (admin override)
    - All other users: Cannot approve tallies

    Historical Note:
    - PERMISSION FIX (2026-03-02): Removed automatic MANAGER supervisor access
    - MANAGER desk can only manage schedules/staff/terminals
    - To approve tallies, manager must be explicitly assigned as terminal supervisor

    Args:
        user: Account instance to check permissions for

    Returns:
        bool: True if user is terminal supervisor or superuser, False otherwise

    Example:
        >>> is_terminal_supervisor(supervisor_user)
        True
        >>> is_terminal_supervisor(manager_user)
        False  # Unless explicitly assigned as supervisor

    Usage:
        In views:
        ```python
        if not is_terminal_supervisor(request.user):
            messages.error(request, "Only terminal supervisors can approve tallies.")
            return redirect('my_tallies')
        ```
    """
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    from apps.tally.models import Terminal
    return Terminal.objects.filter(supervisors=user).exists()
