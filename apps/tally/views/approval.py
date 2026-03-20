"""Tally approval workflow views.

Mechanically extracted from views_old.py to keep behavior unchanged.
"""

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..models import TallyInfo, Terminal

from ._old_shared import _auto_update_sd_from_tally

import logging

logger = logging.getLogger(__name__)

@login_required(login_url='login')
def submit_tally(request, pk):
    """
    Clerk submits a DRAFT or REJECTED tally for supervisor approval.

    Workflow:
    - DRAFT → PENDING_APPROVAL (first submission)
    - REJECTED → PENDING_APPROVAL (resubmission after corrections)

    Permissions: Only the tally creator can submit

    Args:
        pk: Primary key of TallyInfo to submit

    Returns:
        Redirects to my_tallies page with success message
    """
    tally = get_object_or_404(TallyInfo, pk=pk, created_by=request.user)

    # Allow submission of DRAFT or REJECTED tallies
    if tally.status not in ['DRAFT', 'REJECTED']:
        messages.error(request, "Only DRAFT or REJECTED tallies can be submitted.")
        return redirect("tally_view", pk=pk)

    # Change status to PENDING_APPROVAL (resubmit to supervisor)
    tally.status = 'PENDING_APPROVAL'
    tally.save(update_fields=['status'])

    # AUDIT: Tally submitted
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
    if ',' in ip:
        ip = ip.split(',')[0].strip()
    staff_number = getattr(request.user, 'staff_number', request.user.id)
    logger.info(
        f'AUDIT: Tally submitted - Tally#: {tally.tally_number}, SD: {tally.sd_number}, Terminal: {tally.terminal.name if tally.terminal else "N/A"}, By: {staff_number} (User ID: {request.user.pk}), IP: {ip}')

    messages.success(
        request,
        f"✓ Tally #{tally.tally_number} submitted for approval"
    )
    return redirect("my_tallies")

@login_required(login_url='login')
def approve_tally(request, pk):
    """
    Terminal supervisor approves a pending tally.

    Security:
    - Only terminal supervisors can approve
    - Non-manager supervisors can only approve tallies from their assigned terminals
    - Managers can approve tallies from any terminal
    - Full audit logging for accountability

    Side effects:
    - Updates tally status to APPROVED
    - Records approver and timestamp
    - Auto-updates linked SD record with tally data (containers, clerks, tonnage)

    Args:
        pk: Primary key of TallyInfo to approve

    Returns:
        Redirects to pending_tallies page with success message
    """
    from apps.operations.permissions import is_terminal_supervisor
    from apps.core.permissions import _get_user_desks
    import logging
    logger = logging.getLogger('security.permissions')

    if not is_terminal_supervisor(request.user):
        messages.error(request, "Access denied.")
        return redirect("my_tallies")

    tally = get_object_or_404(TallyInfo, pk=pk)
    if tally.status != 'PENDING_APPROVAL':
        messages.error(request, "This tally is not pending approval.")
        return redirect("tally_view", pk=pk)

    # SECURITY FIX: Non-manager supervisors can only approve tallies from their own terminals
    # Use new multi-desk system instead of legacy desk field
    user_desks = _get_user_desks(request.user)
    is_manager = 'MANAGER' in user_desks or request.user.is_superuser

    if not is_manager:
        if not tally.terminal:
            messages.error(request, "This tally has no terminal assigned.")
            return redirect("pending_tallies")

        if not tally.terminal.supervisors.filter(pk=request.user.pk).exists():
            logger.warning(
                f'Unauthorized tally approval attempt: User {request.user.pk} '
                f'tried to approve tally {pk} for terminal {tally.terminal.name} '
                f'(not their assigned terminal)'
            )
            messages.error(request, f"You can only approve tallies for your assigned terminals ({', '.join([t.name for t in Terminal.objects.filter(supervisors=request.user)])}).")
            return redirect("pending_tallies")

    tally.status = 'APPROVED'
    tally.approved_by = request.user
    tally.approved_at = timezone.now()
    tally.rejection_reason = ''
    tally.save(update_fields=['status', 'approved_by', 'approved_at', 'rejection_reason'])

    # SECURITY: Audit log for tally approval
    audit_logger = logging.getLogger('security.audit')
    audit_logger.info(
        f'AUDIT: Tally approved - '
        f'Tally Number: {tally.tally_number}, '
        f'SD Number: {tally.sd_number}, '
        f'Terminal: {tally.terminal.name if tally.terminal else "N/A"}, '
        f'Approved by: {request.user.staff_number} (User ID: {request.user.pk}), '
        f'Created by: {tally.created_by.staff_number if tally.created_by else "N/A"}, '
        f'IP: {request.META.get("REMOTE_ADDR", "unknown")}'
    )

    # Auto-update SD record with tally data
    _auto_update_sd_from_tally(tally)

    messages.success(
        request,
        f"✓ Tally {tally.tally_number} approved by {request.user.first_name} {request.user.last_name}"
    )
    return redirect("pending_tallies")

@login_required(login_url='login')
def reject_tally(request, pk):
    """
    Terminal supervisor rejects a pending tally with reason.

    Features:
    - Requires rejection reason (mandatory field)
    - Tally returns to REJECTED status
    - Clerk can edit and resubmit
    - Full audit logging

    Permissions: Same as approve_tally (terminal supervisors only)

    Args:
        pk: Primary key of TallyInfo to reject

    Returns:
        GET: Renders rejection form
        POST: Rejects tally and redirects to pending_tallies
    """
    from apps.operations.permissions import is_terminal_supervisor
    from apps.core.permissions import _get_user_desks
    import logging
    logger = logging.getLogger('security.permissions')

    if not is_terminal_supervisor(request.user):
        messages.error(request, "Access denied.")
        return redirect("my_tallies")

    tally = get_object_or_404(TallyInfo, pk=pk)
    if tally.status != 'PENDING_APPROVAL':
        messages.error(request, "This tally is not pending approval.")
        return redirect("tally_view", pk=pk)

    # SECURITY FIX: Non-manager supervisors can only reject tallies from their own terminals
    user_desks = _get_user_desks(request.user)
    is_manager = 'MANAGER' in user_desks or request.user.is_superuser

    if not is_manager:
        if not tally.terminal:
            messages.error(request, "This tally has no terminal assigned.")
            return redirect("pending_tallies")

        if not tally.terminal.supervisors.filter(pk=request.user.pk).exists():
            logger.warning(
                f'Unauthorized tally rejection attempt: User {request.user.pk} '
                f'tried to reject tally {pk} for terminal {tally.terminal.name} '
                f'(not their assigned terminal)'
            )
            messages.error(request, f"You can only reject tallies for your assigned terminals.")
            return redirect("pending_tallies")

    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a rejection reason.")
            return redirect("pending_tallies")
        tally.status = 'REJECTED'
        tally.rejection_reason = reason
        tally.approved_by = request.user
        tally.approved_at = timezone.now()
        tally.save(update_fields=['status', 'rejection_reason', 'approved_by', 'approved_at'])

        # SECURITY: Audit log for tally rejection
        audit_logger = logging.getLogger('security.audit')
        audit_logger.info(
            f'AUDIT: Tally rejected - '
            f'Tally Number: {tally.tally_number}, '
            f'SD Number: {tally.sd_number}, '
            f'Terminal: {tally.terminal.name if tally.terminal else "N/A"}, '
            f'Rejected by: {request.user.staff_number} (User ID: {request.user.pk}), '
            f'Created by: {tally.created_by.staff_number if tally.created_by else "N/A"}, '
            f'Reason: {reason[:100]}, '
            f'IP: {request.META.get("REMOTE_ADDR", "unknown")}'
        )

        messages.success(
            request,
            f"✓ Tally {tally.tally_number} rejected by {request.user.first_name} {request.user.last_name}"
        )
        return redirect("pending_tallies")

    return redirect("pending_tallies")

@login_required(login_url='login')
def recall_tally(request, pk):
    """DEPRECATED: Old recall function. Use request_recall and approve_recall_request instead."""
    messages.error(request, "This recall method is deprecated. Please use the new recall request workflow.")
    return redirect("my_tallies")

@login_required(login_url='login')
def request_recall(request, pk):
    """Supervisor requests recall of an approved tally."""
    from apps.operations.permissions import is_terminal_supervisor
    from apps.tally.models import RecallRequest
    import logging

    if not is_terminal_supervisor(request.user):
        messages.error(request, "Access denied. Only supervisors can request recalls.")
        return redirect("my_tallies")

    tally = get_object_or_404(TallyInfo, pk=pk)

    # Check if tally is approved
    if tally.status != 'APPROVED':
        messages.error(request, "Only approved tallies can be recalled.")
        return redirect("pending_tallies")

    # Check if within 48 hours
    if not tally.can_be_recalled:
        messages.error(request, "This tally can no longer be recalled (48-hour window expired).")
        return redirect("pending_tallies")

    # Check if there's already a pending recall request
    existing_request = RecallRequest.objects.filter(
        tally=tally,
        status='PENDING'
    ).first()

    if existing_request:
        messages.warning(request, f"A recall request for this tally is already pending approval from operations desk.")
        return redirect("pending_tallies")

    if request.method == 'POST':
        reason = request.POST.get('recall_reason', '').strip()
        if not reason:
            messages.error(request, "Please provide a reason for requesting recall.")
            return redirect("pending_tallies")

        # Create recall request
        recall_request = RecallRequest.objects.create(
            tally=tally,
            requested_by=request.user,
            reason=reason,
            status='PENDING'
        )

        # Audit log
        audit_logger = logging.getLogger('security.audit')
        audit_logger.info(
            f'AUDIT: Recall requested - '
            f'Tally Number: {tally.tally_number}, '
            f'SD Number: {tally.sd_number}, '
            f'Terminal: {tally.terminal.name if tally.terminal else "N/A"}, '
            f'Requested by: {request.user.staff_number} (User ID: {request.user.pk}), '
            f'Reason: {reason[:100]}, '
            f'IP: {request.META.get("REMOTE_ADDR", "unknown")}'
        )

        messages.success(
            request,
            f"✓ Recall request submitted for Tally {tally.tally_number}. Operations desk will review your request."
        )
        return redirect("pending_tallies")

    return redirect("pending_tallies")

@login_required(login_url='login')
def approve_recall_request(request, request_id):
    """Operations desk approves a recall request."""
    from apps.operations.permissions import can_manage_sd_records
    from apps.tally.models import RecallRequest
    import logging

    if not can_manage_sd_records(request.user):
        messages.error(request, "Access denied. Only operations desk can approve recall requests.")
        return redirect("my_tallies")

    recall_request = get_object_or_404(RecallRequest, pk=request_id)

    if recall_request.status != 'PENDING':
        messages.error(request, "This recall request has already been processed.")
        return redirect("all_approved_tallies")

    if request.method == 'POST':
        operations_notes = request.POST.get('operations_notes', '').strip()

        # Update recall request
        recall_request.status = 'APPROVED'
        recall_request.approved_by = request.user
        recall_request.processed_at = timezone.now()
        recall_request.operations_notes = operations_notes
        recall_request.save()

        # Recall the tally
        tally = recall_request.tally
        tally.status = 'REJECTED'
        tally.rejection_reason = f"[RECALLED] {recall_request.reason}"
        tally.save(update_fields=['status', 'rejection_reason'])

        # Audit log
        audit_logger = logging.getLogger('security.audit')
        audit_logger.info(
            f'AUDIT: Recall request approved - '
            f'Tally Number: {tally.tally_number}, '
            f'SD Number: {tally.sd_number}, '
            f'Requested by: {recall_request.requested_by.staff_number}, '
            f'Approved by: {request.user.staff_number} (User ID: {request.user.pk}), '
            f'Reason: {recall_request.reason[:100]}, '
            f'IP: {request.META.get("REMOTE_ADDR", "unknown")}'
        )

        messages.success(
            request,
            f"✓ Recall request approved. Tally {tally.tally_number} has been recalled. Clerk can now edit and resubmit."
        )
        return redirect("all_approved_tallies")

    return redirect("all_approved_tallies")

@login_required(login_url='login')
def reject_recall_request(request, request_id):
    """Operations desk rejects a recall request."""
    from apps.operations.permissions import can_manage_sd_records
    from apps.tally.models import RecallRequest
    import logging

    if not can_manage_sd_records(request.user):
        messages.error(request, "Access denied. Only operations desk can reject recall requests.")
        return redirect("my_tallies")

    recall_request = get_object_or_404(RecallRequest, pk=request_id)

    if recall_request.status != 'PENDING':
        messages.error(request, "This recall request has already been processed.")
        return redirect("all_approved_tallies")

    if request.method == 'POST':
        operations_notes = request.POST.get('operations_notes', '').strip()
        if not operations_notes:
            messages.error(request, "Please provide a reason for rejecting this recall request.")
            return redirect("all_approved_tallies")

        # Update recall request
        recall_request.status = 'REJECTED'
        recall_request.approved_by = request.user
        recall_request.processed_at = timezone.now()
        recall_request.operations_notes = operations_notes
        recall_request.save()

        # Audit log
        audit_logger = logging.getLogger('security.audit')
        audit_logger.info(
            f'AUDIT: Recall request rejected - '
            f'Tally Number: {recall_request.tally.tally_number}, '
            f'Requested by: {recall_request.requested_by.staff_number}, '
            f'Rejected by: {request.user.staff_number} (User ID: {request.user.pk}), '
            f'Reason: {operations_notes[:100]}, '
            f'IP: {request.META.get("REMOTE_ADDR", "unknown")}'
        )

        messages.success(
            request,
            f"✓ Recall request rejected. Supervisor {recall_request.requested_by.first_name} {recall_request.requested_by.last_name} will be notified."
        )
        return redirect("all_approved_tallies")

    return redirect("all_approved_tallies")

    return redirect("all_approved_tallies")

@login_required(login_url='login')
def all_approved_tallies(request):
    """All staff can see APPROVED tallies (supervisors see only their approvals, others see all)."""
    from apps.operations.permissions import can_manage_sd_records, is_terminal_supervisor
    from django.db.models import Count
    import calendar as cal_module
    from datetime import date, timedelta

    is_ops = can_manage_sd_records(request.user)
    is_sup = is_terminal_supervisor(request.user)

    today = date.today()
    q = (request.GET.get('q') or '').strip()

    # Calendar state
    date_str = request.GET.get('date', '')
    selected_date = None
    if date_str:
        try:
            selected_date = date.fromisoformat(date_str)
        except ValueError:
            pass

    cal_year = int(request.GET.get('cal_year', today.year))
    cal_month = int(request.GET.get('cal_month', today.month))
    if cal_month < 1:
        cal_month, cal_year = 12, cal_year - 1
    elif cal_month > 12:
        cal_month, cal_year = 1, cal_year + 1

    month_start = date(cal_year, cal_month, 1)
    month_end = date(cal_year, cal_month, cal_module.monthrange(cal_year, cal_month)[1])

    # Get tally dates in current month for calendar dots
    tally_dates_qs = TallyInfo.objects.filter(
        status='APPROVED',
        loading_date__gte=month_start,
        loading_date__lte=month_end
    )
    if is_sup and not is_ops:
        tally_dates_qs = tally_dates_qs.filter(approved_by=request.user)

    tally_dates = set(tally_dates_qs.values_list('loading_date', flat=True))

    prev_month = (date(cal_year, cal_month, 1) - timedelta(days=1)).replace(day=1)
    next_month = (date(cal_year, cal_month, 28) + timedelta(days=7)).replace(day=1)

    from apps.tally.models import RecallRequest

    qs = TallyInfo.objects.filter(status='APPROVED').annotate(
        recall_request_count=Count('recall_requests')
    ).prefetch_related('recall_requests__requested_by', 'recall_requests__approved_by')

    # Supervisors (who are not ops/manager/superuser) only see their own approvals
    if is_sup and not is_ops:
        qs = qs.filter(approved_by=request.user)

    # Filter by date if selected
    if selected_date:
        qs = qs.filter(loading_date=selected_date)

    if q:
        qs = qs.filter(
            Q(sd_number__icontains=q) |
            Q(vessel__icontains=q) |
            Q(terminal_name__icontains=q) |
            Q(mk_number__icontains=q)
        )
    qs = qs.order_by('sd_number', '-approved_at')

    # Group tallies by SD number
    from itertools import groupby
    tallies_list = list(qs)
    grouped_tallies = []
    for sd_number, group in groupby(tallies_list, key=lambda t: t.sd_number):
        tallies_in_sd = list(group)
        grouped_tallies.append({
            'sd_number': sd_number,
            'tallies': tallies_in_sd,
            'count': len(tallies_in_sd),
            'total_bags': sum(t.total_bags or 0 for t in tallies_in_sd),
            'total_tonnage': sum(float(t.total_tonnage or 0) for t in tallies_in_sd),
        })

    paginator = Paginator(grouped_tallies, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Calculate total tallies count for display
    total_tallies = len(tallies_list)

    # Attach pending recall requests to each tally for modal display
    for group in grouped_tallies:
        for tally in group['tallies']:
            tally.pending_recall_requests = [
                req for req in tally.recall_requests.all() if req.status == 'PENDING'
            ]

    # Get pending recall requests for operations desk (no longer displayed at top)
    from apps.tally.models import RecallRequest
    pending_recall_requests = []
    if is_ops:
        pending_recall_requests = RecallRequest.objects.filter(
            status='PENDING'
        ).select_related('tally', 'requested_by').order_by('-created_at')

    return render(request, "tally_details/all_approved_tallies.html", {
        'grouped_tallies': page_obj.object_list,
        'page_obj': page_obj,
        'total_tallies': total_tallies,
        'pending_recall_requests': pending_recall_requests,
        'q': q,
        'is_supervisor_view': is_sup and not is_ops,
        'selected_date': selected_date,
        'today': today,
        'cal_year': cal_year,
        'cal_month': cal_month,
        'cal_month_name': date(cal_year, cal_month, 1).strftime('%B %Y'),
        'cal_weeks': cal_module.monthcalendar(cal_year, cal_month),
        'tally_dates': [d.isoformat() for d in tally_dates],
        'prev_month': prev_month,
        'next_month': next_month,
    })


# ── Helper: Auto-update SD from approved tally ────────────────────────

