from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.core.calendar_utils import get_calendar_state
from apps.core.validators import validate_file_size

from ..forms import DailyPortForm
from ..models import DailyPort, SDRecord
from ..permissions import can_manage_sd_records


# ══════════════════════════════════════════════════════
#  DAILY PORT VIEWS
# ══════════════════════════════════════════════════════

@login_required(login_url='login')
def daily_port_view(request):
    """
    Display daily port reports with calendar navigation.

    Features:
    - Calendar-based date selection with month navigation
    - Shows daily port report for selected date (one per day)
    - Filter by creator (show mine)
    - Highlights dates with reports in calendar
    - Displays SD number, PDF, and Excel files

    Permissions: All authenticated users can view

    Returns:
        Renders daily_port.html with daily port report and calendar
    """
    cal = get_calendar_state(request, today=date.today())
    show_mine = request.GET.get('mine', '').lower() == 'true'

    daily_port = DailyPort.objects.filter(date=cal['selected_date'])
    if show_mine:
        daily_port = daily_port.filter(created_by=request.user)
    daily_port = daily_port.first()

    port_dates = set(
        DailyPort.objects
        .filter(date__gte=cal['month_start'], date__lte=cal['month_end'])
        .values_list('date', flat=True)
    )

    can_manage = can_manage_sd_records(request.user)

    return render(request, 'daily_port/daily_port.html', {
        'daily_port': daily_port,
        'port_dates': [d.isoformat() for d in port_dates],
        'show_mine': show_mine,
        'can_manage': can_manage,
        **{k: cal[k] for k in ['selected_date', 'today', 'cal_year', 'cal_month', 'cal_month_name', 'cal_weeks', 'prev_month', 'next_month']},
    })


@login_required(login_url='login')
def daily_port_create(request):
    """
    Create a new daily port report (operations desk only).

    Features:
    - Enter SD number and upload PDF/Excel files
    - One report per date (auto-redirects to edit if exists)
    - File size validation before processing
    - Auto-links to SD record when available
    - Audit trail with created_by tracking

    Security:
    - Only operations desk can create daily port reports
    - File size validation (PDF 10MB, Excel 25MB)
    - Duplicate date prevention

    Permissions: OPERATIONS desk or superuser only

    Returns:
        GET: Renders daily port form
        POST: Creates daily port and redirects to view
    """
    if not can_manage_sd_records(request.user):
        messages.error(request, "You don't have permission to add daily port entries.")
        return redirect('daily_port_view')

    all_sd_numbers = SDRecord.objects.values_list('sd_number', flat=True).distinct()

    if request.method == 'POST':
        form = DailyPortForm(request.POST, request.FILES)
        if form.is_valid():
            # SECURITY: Validate file sizes before processing
            from django.core.exceptions import ValidationError
            try:
                if 'pdf_file' in request.FILES:
                    validate_file_size(request.FILES['pdf_file'], 'pdf')
                if 'excel_file' in request.FILES:
                    validate_file_size(request.FILES['excel_file'], 'excel')
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'daily_port/daily_port_form.html', {
                    'form': form,
                    'editing': False,
                    'all_sd_numbers': all_sd_numbers,
                })

            existing = DailyPort.objects.filter(date=form.cleaned_data['date']).first()
            if existing:
                messages.warning(request, 'A daily port entry for that date already exists. Editing instead.')
                return redirect('daily_port_edit', pk=existing.pk)
            dp = form.save(commit=False)
            dp.created_by = request.user
            dp.save()
            messages.success(
                request,
                f"✓ Daily port for {dp.date.strftime('%d %b %Y')} created by {request.user.first_name} {request.user.last_name}"
            )
            return redirect(f"{reverse('daily_port_view')}?date={dp.date.isoformat()}")
    else:
        initial_date = request.GET.get('date', '')
        form = DailyPortForm(initial={'date': initial_date} if initial_date else None)

    return render(request, 'daily_port/daily_port_form.html', {
        'form': form,
        'editing': False,
        'all_sd_numbers': all_sd_numbers,
    })


@login_required(login_url='login')
def daily_port_edit(request, pk):
    """
    Edit existing daily port report (operations desk only).

    Features:
    - Update SD number, date, or replace files
    - Preserves existing files if no new file uploaded
    - Ownership verification (only creator or superuser)
    - Audit logging for unauthorized attempts

    Security:
    - Only operations desk can edit daily port reports
    - Ownership verification: only creator or superuser can edit
    - Logs unauthorized edit attempts

    Permissions: OPERATIONS desk AND (creator OR superuser)

    Args:
        pk: Primary key of DailyPort to edit

    Returns:
        GET: Renders edit form with existing data
        POST: Updates daily port and redirects to view
    """
    import logging

    if not can_manage_sd_records(request.user):
        messages.error(request, "You don't have permission to edit daily port entries.")
        return redirect('daily_port_view')

    all_sd_numbers = SDRecord.objects.values_list('sd_number', flat=True).distinct()
    dp = get_object_or_404(DailyPort, pk=pk)

    # SECURITY FIX: Verify ownership - only creator or superuser can edit
    if dp.created_by != request.user and not request.user.is_superuser:
        logger = logging.getLogger(__name__)
        logger.warning(
            f'SECURITY: Unauthorized daily port edit attempt by user {request.user.pk} '
            f'for daily port {pk} created by {dp.created_by.pk if dp.created_by else "None"}'
        )
        messages.error(
            request,
            'You can only edit your own daily port entries. Contact a superuser if changes are needed.'
        )
        return redirect('daily_port_view')

    if request.method == 'POST':
        form = DailyPortForm(request.POST, request.FILES, instance=dp)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"✓ Daily port for {dp.date.strftime('%d %b %Y')} updated by {request.user.first_name} {request.user.last_name}"
            )
            return redirect(f"{reverse('daily_port_view')}?date={dp.date.isoformat()}")
    else:
        form = DailyPortForm(instance=dp)

    return render(request, 'daily_port/daily_port_form.html', {
        'form': form,
        'editing': True,
        'daily_port': dp,
        'all_sd_numbers': all_sd_numbers,
    })


@login_required(login_url='login')
def daily_port_delete(request, pk):
    """
    Delete a daily port report (operations desk only, creator or superuser).

    Features:
    - Confirmation page before deletion
    - Deletes uploaded PDF/Excel files
    - Ownership verification (only creator or superuser)
    - Audit logging for unauthorized attempts

    Security:
    - Only operations desk can delete daily port reports
    - Ownership verification: only creator or superuser can delete
    - Logs unauthorized deletion attempts

    Permissions: OPERATIONS desk AND (creator OR superuser)

    Args:
        pk: Primary key of DailyPort to delete

    Returns:
        GET: Renders confirmation page
        POST: Deletes daily port and redirects to view
    """
    import logging

    if not can_manage_sd_records(request.user):
        messages.error(request, "You don't have permission to delete daily port entries.")
        return redirect('daily_port_view')

    dp = get_object_or_404(DailyPort, pk=pk)

    # SECURITY FIX: Verify ownership - only creator or superuser can delete
    if dp.created_by != request.user and not request.user.is_superuser:
        logger = logging.getLogger(__name__)
        logger.warning(
            f'SECURITY: Unauthorized daily port delete attempt by user {request.user.pk} '
            f'for daily port {pk} created by {dp.created_by.pk if dp.created_by else "None"}'
        )
        messages.error(
            request,
            'You can only delete your own daily port entries. Contact a superuser if changes are needed.'
        )
        return redirect('daily_port_view')

    if request.method == 'POST':
        dp_date = dp.date
        dp.delete()
        messages.success(request, f"Daily port for {dp_date.strftime('%d %b %Y')} deleted successfully.")
        return redirect('daily_port_view')

    return render(request, 'daily_port/daily_port_confirm_delete.html', {
        'daily_port': dp,
        'can_manage': can_manage_sd_records(request.user),
    })
