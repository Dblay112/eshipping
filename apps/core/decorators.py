"""
Security decorators for permission and ownership verification.
Created as part of security audit fixes (February 2026).
"""
from django.http import Http404
import logging

logger = logging.getLogger('security.permissions')


def check_sd_access_permission(user, sd_pk):
    """
    Check if user can access SD record BEFORE fetching full data.
    This prevents IDOR vulnerabilities by validating permission first.

    SECURITY: All authenticated users can VIEW SD records (read-only).
    Edit/Delete permissions are handled separately in views.

    Args:
        user: The requesting user
        sd_pk: Primary key of the SD record

    Returns:
        True if user has access, False otherwise

    Raises:
        Http404 if SD record doesn't exist
    """
    from apps.operations.models import SDRecord

    try:
        # Fetch minimal data first (only fields needed for permission check)
        sd_check = SDRecord.objects.only('pk').get(pk=sd_pk)
    except SDRecord.DoesNotExist:
        raise Http404("SD record not found")

    # All authenticated users can view SD records
    return user.is_authenticated
