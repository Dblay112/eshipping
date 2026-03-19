"""Shared helpers used by tally views.

Mechanically extracted from views_old.py to keep behavior unchanged.
"""

import re
import logging

from django.urls import NoReverseMatch, reverse

from ..models import Terminal

logger = logging.getLogger(__name__)

def _safe_reverse(name, **kwargs):
    try:
        return reverse(name, kwargs=kwargs or None)
    except NoReverseMatch:
        return "#"

def _can_view_tally(user, tally):
    """Return True if user is allowed to view this tally."""
    from apps.operations.permissions import can_manage_sd_records, is_terminal_supervisor

    # Creator can always view their own tally
    if tally.created_by == user:
        return True

    # Superuser, manager, and operations desk can view all tallies
    if user.is_superuser or user.is_manager or can_manage_sd_records(user):
        return True

    # Terminal supervisor can view tallies from their terminal
    if is_terminal_supervisor(user):
        if tally.terminal and tally.terminal.supervisors.filter(pk=user.pk).exists():
            return True
        # Also allow if terminal_name matches any terminal they supervise
        supervised = Terminal.objects.filter(supervisors=user).values_list('name', flat=True)
        if tally.terminal_name in supervised:
            return True

    return False

def _parse_container_indices(request):
    container_pattern = re.compile(r"^containers\[(\d+)\]\[")
    indices = set()

    for key in request.POST.keys():
        m = container_pattern.match(key)
        if m:
            indices.add(int(m.group(1)))

    for key in request.FILES.keys():
        m = container_pattern.match(key)
        if m:
            indices.add(int(m.group(1)))

    return sorted(indices)

def _auto_update_sd_from_tally(tally):
    """
    When a tally is approved, automatically sync its data to the SD record:
    - Add clerk names to SDClerk table
    - Sync container numbers/seals to SDContainer table
    """
    from apps.operations.models import SDRecord, SDContainer, SDClerk

    try:
        sd = SDRecord.objects.get(sd_number__iexact=tally.sd_number)
    except SDRecord.DoesNotExist:
        # SD not created yet - this is okay, sync will happen when SD is created
        return

    # Add clerk names if not already present
    if isinstance(tally.clerk_name, list):
        clerk_names = [name.strip() for name in tally.clerk_name if name and str(name).strip()]
    else:
        clerk_names = []

    for clerk_name in clerk_names:
        if clerk_name:
            SDClerk.objects.get_or_create(
                sd_record=sd,
                officer_name=clerk_name,
                tally_reference=str(tally.tally_number),
                defaults={
                    'date_worked': tally.loading_date,
                }
            )

    # Sync containers from tally to SD
    for tc in tally.containers.all():
        SDContainer.objects.update_or_create(
            sd_record=sd,
            tally_container_id=tc.pk,
            defaults={
                'container_number': tc.container_number or '',
                'seal_number': tc.seal_number or '',
                'bag_count': tc.bags or 0,
                'loading_date': tally.loading_date,
                'from_tally': True,
            }
        )

