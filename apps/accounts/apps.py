from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """
    Django app configuration for accounts module.

    Manages staff authentication, user profiles, and multi-desk assignments.
    Uses custom user model (Account) with staff_number as primary identifier.

    Features:
    - Custom authentication using staff_number instead of username
    - Multi-desk assignment system for cross-department staff
    - Staff profile management with employment tracking
    - Password change enforcement for new staff
    - Rank-based hierarchy for staff directory
    """
    name = 'apps.accounts'
