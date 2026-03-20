from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django_ratelimit.decorators import ratelimit

from apps.core.calendar_utils import get_calendar_state

from ..forms import WorkProgramForm
from ..models import WorkProgram
from ..permissions import can_manage_sd_records


# ══════════════════════════════════════════════════════
#  WORK PROGRAM VIEWS
# ══════════════════════════════════════════════════════

@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def work_program_list(request):
    """
    Display all work programs with calendar navigation.

    Features:
    - Calendar-based date selection with month navigation
    - Shows work program for selected date (one per day)
    - Highlights dates with work programs in calendar
    - Displays PDF/Excel files for each work program
    - Shows creator and last updater information

    Permissions: All authenticated users can view
    Rate limit: 10 requests per minute per user

    Returns:
        Renders work_program_list.html with work program and calendar
    """
    cal = get_calendar_state(request, today=date.today())

    # Get work program dates in current month for calendar dots
    wp_dates = set(
        WorkProgram.objects.filter(
            date__gte=cal['month_start'],
            date__lte=cal['month_end'],
        ).values_list('date', flat=True)
    )

    # Get work program for selected date (only one per day)
    work_program = WorkProgram.objects.filter(date=cal['selected_date']).select_related('created_by', 'updated_by').first()

    return render(request, 'work_program/work_program_list.html', {
        'work_program': work_program,
        'wp_dates': [d.isoformat() for d in wp_dates],
        'can_manage': can_manage_sd_records(request.user),
        **{k: cal[k] for k in ['selected_date', 'today', 'cal_year', 'cal_month', 'cal_month_name', 'cal_weeks', 'prev_month', 'next_month']},
    })


@login_required(login_url='login')
def work_program_create(request):
    """
    Create a new work program document (operations desk only).

    Features:
    - Upload PDF or Excel file for daily work program
    - One work program per date
    - Auto-redirects to edit if date already exists
    - Audit trail with created_by and updated_by tracking

    Security:
    - Only operations desk can create work programs
    - File size validation (PDF 10MB, Excel 25MB)

    Permissions: OPERATIONS desk or superuser only

    Returns:
        GET: Renders work program form
        POST: Creates work program and redirects to list
    """
    if not can_manage_sd_records(request.user):
        messages.error(request, 'Only the Operations desk can create work programs.')
        return redirect('work_program_list')

    if request.method == 'POST':
        form = WorkProgramForm(request.POST, request.FILES)
        if form.is_valid():
            wp = form.save(commit=False)
            wp.created_by = request.user
            wp.updated_by = request.user
            wp.save()

            # AUDIT: Work Program created
            import logging
            logger = logging.getLogger(__name__)
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            staff_number = getattr(request.user, 'staff_number', request.user.id)
            logger.info(
                f'AUDIT: Work Program created - Date: {wp.date.strftime("%Y-%m-%d")}, By: {staff_number} (User ID: {request.user.pk}), IP: {ip}')

            messages.success(request, f"Work program for {wp.date.strftime('%d %b %Y')} created successfully.")
            return redirect('work_program_list')
    else:
        form = WorkProgramForm()

    return render(request, 'work_program/work_program_form.html', {
        'form': form,
        'action': 'Create',
        'can_manage': can_manage_sd_records(request.user),
    })


@login_required(login_url='login')
def work_program_edit(request, pk):
    """
    Edit existing work program document (operations desk only).

    Features:
    - Update date or replace PDF/Excel file
    - Preserves existing file if no new file uploaded
    - Audit trail with updated_by tracking

    Security:
    - Only operations desk can edit work programs
    - No ownership verification (any operations user can edit)

    Permissions: OPERATIONS desk or superuser only

    Args:
        pk: Primary key of WorkProgram to edit

    Returns:
        GET: Renders edit form with existing data
        POST: Updates work program and redirects to list
    """
    if not can_manage_sd_records(request.user):
        messages.error(request, 'Only the Operations desk can edit work programs.')
        return redirect('work_program_list')

    wp = get_object_or_404(WorkProgram, pk=pk)

    if request.method == 'POST':
        form = WorkProgramForm(request.POST, request.FILES, instance=wp)
        if form.is_valid():
            wp = form.save(commit=False)
            wp.updated_by = request.user
            wp.save()

            # AUDIT: Work Program updated
            import logging
            logger = logging.getLogger(__name__)
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            staff_number = getattr(request.user, 'staff_number', request.user.id)
            logger.info(
                f'AUDIT: Work Program updated - Date: {wp.date.strftime("%Y-%m-%d")}, By: {staff_number} (User ID: {request.user.pk}), IP: {ip}')

            messages.success(request, f"Work program for {wp.date.strftime('%d %b %Y')} updated successfully.")
            return redirect('work_program_list')
    else:
        form = WorkProgramForm(instance=wp)

    return render(request, 'work_program/work_program_form.html', {
        'form': form,
        'work_program': wp,
        'action': 'Edit',
        'can_manage': can_manage_sd_records(request.user),
    })


@login_required(login_url='login')
def work_program_delete(request, pk):
    """
    Delete a work program document (operations desk only).

    Features:
    - Confirmation page before deletion
    - Deletes uploaded PDF/Excel files
    - No cascade effects (standalone document)

    Security:
    - Only operations desk can delete work programs
    - No ownership verification (any operations user can delete)

    Permissions: OPERATIONS desk or superuser only

    Args:
        pk: Primary key of WorkProgram to delete

    Returns:
        GET: Renders confirmation page
        POST: Deletes work program and redirects to list
    """
    if not can_manage_sd_records(request.user):
        messages.error(request, 'Only the Operations desk can delete work programs.')
        return redirect('work_program_list')

    wp = get_object_or_404(WorkProgram, pk=pk)

    if request.method == 'POST':
        wp_date = wp.date
        wp.delete()

        # AUDIT: Work Program deleted
        import logging
        logger = logging.getLogger(__name__)
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        staff_number = getattr(request.user, 'staff_number', request.user.id)
        logger.info(
            f'AUDIT: Work Program deleted - Date: {wp_date.strftime("%Y-%m-%d")}, By: {staff_number} (User ID: {request.user.pk}), IP: {ip}')

        messages.success(request, f"Work program for {wp_date.strftime('%d %b %Y')} deleted successfully.")
        return redirect('work_program_list')

    return render(request, 'work_program/work_program_confirm_delete.html', {
        'work_program': wp,
        'can_manage': can_manage_sd_records(request.user),
    })
