"""
Custom password validators for admin/superuser accounts.
Regular staff have simple 6-character minimum requirement.
Admins have complex password requirements.
"""
from django.core.exceptions import ValidationError
import re


def validate_admin_password(password):
    """
    Validate admin/superuser password with complex security requirements.

    Enforces strong password policy for administrative accounts to prevent
    unauthorized access. Regular staff have simpler 6-character minimum.

    Security Requirements:
    - Minimum 8 characters (prevents brute force attacks)
    - At least 1 uppercase letter (increases complexity)
    - At least 1 lowercase letter (increases complexity)
    - At least 1 number (prevents dictionary attacks)
    - At least 1 special character (maximum complexity)

    Special Characters Allowed:
        !@#$%^&*(),.?":{}|<>_-+=[]\/;~`

    Args:
        password: Password string to validate

    Raises:
        ValidationError: If password doesn't meet requirements
                        Contains list of all failed requirements

    Example:
        >>> validate_admin_password("Admin123!")
        # Passes validation
        >>> validate_admin_password("weak")
        ValidationError: ['Password must be at least 8 characters long.', ...]

    Usage:
        In forms:
        ```python
        def clean_password(self):
            password = self.cleaned_data.get('password')
            if user.is_admin or user.is_superuser:
                validate_admin_password(password)
            return password
        ```
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")

    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter.")

    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter.")

    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number.")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\/;~`]', password):
        errors.append(r"Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>_-+=[]\/;~`).")

    if errors:
        raise ValidationError(errors)
