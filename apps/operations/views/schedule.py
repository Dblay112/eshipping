from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django_ratelimit.decorators import ratelimit

from ..forms import ScheduleEntryFormSet, ScheduleForm
from apps.core.calendar_utils import get_calendar_state

from ..models import Schedule
from ..permissions import can_manage_schedules


# ══════════════════════════════════════════════════════
#  SCHEDULE VIEWS
# ══════════════════════════════════════════════════════

@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def schedule_view(request):
    """
    Display daily loading schedule with calendar navigation and pagination.

    Features:
    - Calendar-based date selection with month navigation
    - Shows schedule entries (SD, agent, tonnage, assigned officer)
    - Filter by creator (show mine)
    - Pagination at 12 entries per page
    - Highlights dates with schedules in calendar
    - Shows assigned officer for each SD

    Permissions: All authenticated users can view
    Rate limit: 10 requests per minute per user

    Returns:
        Renders schedule.html with schedule entries and calendar
    """
    cal = get_calendar_state(request, today=date.today())
    show_mine = request.GET.get('mine', '').lower() == 'true'

    schedule = (
        Schedule.objects
        .filter(date=cal['selected_date'])
        .prefetch_related('entries__assigned_officer')
    )
    if show_mine:
        schedule = schedule.filter(created_by=request.user)
    schedule = schedule.first()

    entries_page = None
    if schedule:
        entries_qs = schedule.entries.select_related('assigned_officer').all().order_by('id')
        paginator = Paginator(entries_qs, 12)
        entries_page = paginator.get_page(request.GET.get('page'))

    scheduled_dates = set(
        Schedule.objects
        .filter(date__gte=cal['month_start'], date__lte=cal['month_end'])
        .values_list('date', flat=True)
    )

    is_superior = can_manage_schedules(request.user) or request.user.is_superuser

    return render(request, 'schedule/schedule.html', {
        'schedule': schedule,
        'entries_page': entries_page,
        'scheduled_dates': [d.isoformat() for d in scheduled_dates],
        'show_mine': show_mine,
        'can_manage': is_superior,
        'is_superior': is_superior,
        **{k: cal[k] for k in ['selected_date', 'today', 'cal_year', 'cal_month', 'cal_month_name', 'cal_weeks', 'prev_month', 'next_month']},
    })


@login_required(login_url='login')
def schedule_create(request):
    """
    Create new daily loading schedule with officer assignments (managers only).

    Features:
    - One form submission creates schedule with multiple SD entries
    - Formset workflow for adding multiple SDs
    - Assign officer to each SD (typeable input with suggestions)
    - Validates duplicate SD assignments (each SD only once per schedule)
    - Prevents duplicate schedules for same date
    - Auto-links to SD records when available
    - Audit trail with created_by tracking

    Security:
    - Only managers can create schedules
    - Duplicate SD validation prevents conflicts
    - Existing schedule redirects to edit mode

    Permissions: MANAGER desk or superuser only

    Returns:
        GET: Renders schedule form with empty formset
        POST: Creates schedule and redirects to view
    """
    if not (can_manage_schedules(request.user) or request.user.is_superuser):
        messages.error(request, "You don't have permission to create schedules.")
        return redirect('schedule_view')

    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        formset = ScheduleEntryFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            existing = Schedule.objects.filter(date=form.cleaned_data['date']).first()
            if existing:
                messages.warning(request, "A schedule for that date already exists. Editing instead.")
                return redirect('schedule_edit', pk=existing.pk)

            # Validate: Check for duplicate SD assignments
            sd_numbers = []
            for entry_form in formset:
                if entry_form.cleaned_data and not entry_form.cleaned_data.get('DELETE', False):
                    sd_num = entry_form.cleaned_data.get('sd_number', '').strip()
                    if sd_num:
                        if sd_num in sd_numbers:
                            messages.error(request, f"SD {sd_num} is assigned to multiple officers. Each SD can only be assigned once per schedule.")
                            return render(request, 'schedule/schedule_form.html', {
                                'form': form, 'formset': formset, 'action': 'Create',
                                'can_manage': can_manage_schedules(request.user),
                            })
                        sd_numbers.append(sd_num)

            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()
            formset.instance = schedule
            formset.save()
            messages.success(
                request,
                f"✓ Schedule for {schedule.date.strftime('%d %b %Y')} created by {request.user.first_name} {request.user.last_name}"
            )
            return redirect('schedule_view')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = ScheduleForm(initial={'date': request.GET.get('date', date.today().isoformat())})
        formset = ScheduleEntryFormSet()

    return render(request, 'schedule/schedule_form.html', {
        'form': form, 'formset': formset, 'action': 'Create',
        'can_manage': can_manage_schedules(request.user),
    })


@login_required(login_url='login')
def schedule_edit(request, pk):
    """
    Edit existing schedule and officer assignments (managers only).

    Features:
    - Update date, notes, and schedule entries
    - Add/remove/edit SD assignments
    - Reassign officers to different SDs
    - Validates duplicate SD assignments
    - Preserves existing entries when adding new ones
    - Audit trail with updated_by tracking

    Security:
    - Only managers can edit schedules
    - Ownership verification: only creator or any manager can edit
    - Logs unauthorized edit attempts

    Permissions: MANAGER desk or superuser only

    Args:
        pk: Primary key of Schedule to edit

    Returns:
        GET: Renders edit form with existing data
        POST: Updates schedule and redirects to view
    """
    if not (can_manage_schedules(request.user) or request.user.is_superuser):
        messages.error(request, "You don't have permission to edit schedules.")
        return redirect('schedule_view')

    schedule = get_object_or_404(Schedule, pk=pk)

    # SECURITY FIX: Verify ownership - only creator or any manager can edit
    if schedule.created_by != request.user and not can_manage_schedules(request.user):
        import logging
        logger = logging.getLogger('security.permissions')
        logger.warning(
            f'User {request.user.pk} attempted to edit schedule {pk} '
            f'created by {schedule.created_by.pk if schedule.created_by else "None"}'
        )
        messages.error(
            request,
            'You can only edit your own schedules. Contact a superuser if changes are needed.'
        )
        return redirect('schedule_view')

    if request.method == 'POST':
        form = ScheduleForm(request.POST, instance=schedule)
        formset = ScheduleEntryFormSet(request.POST, instance=schedule)
        if form.is_valid() and formset.is_valid():
            # Validate: Check for duplicate SD assignments
            sd_numbers = []
            for entry_form in formset:
                if entry_form.cleaned_data and not entry_form.cleaned_data.get('DELETE', False):
                    sd_num = entry_form.cleaned_data.get('sd_number', '').strip()
                    if sd_num:
                        if sd_num in sd_numbers:
                            messages.error(request, f"SD {sd_num} is assigned to multiple officers. Each SD can only be assigned once per schedule.")
                            return render(request, 'schedule/schedule_form.html', {
                                'form': form, 'formset': formset, 'schedule': schedule,
                                'action': 'Edit', 'can_manage': can_manage_schedules(request.user),
                            })
                        sd_numbers.append(sd_num)

            form.save()
            formset.save()
            messages.success(
                request,
                f"✓ Schedule for {schedule.date.strftime('%d %b %Y')} updated by {request.user.first_name} {request.user.last_name}"
            )
            return redirect('schedule_view')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = ScheduleForm(instance=schedule)
        formset = ScheduleEntryFormSet(instance=schedule)

    return render(request, 'schedule/schedule_form.html', {
        'form': form, 'formset': formset, 'schedule': schedule,
        'action': 'Edit', 'can_manage': can_manage_schedules(request.user),
    })


@login_required(login_url='login')
def schedule_delete(request, pk):
    """
    Delete a schedule (managers only, creator or any manager).

    Features:
    - Confirmation page before deletion
    - Cascades deletion to all schedule entries
    - Orphans SD records (sets officer_assigned to NULL)
    - Audit logging for unauthorized attempts

    Security:
    - Only managers can delete schedules
    - Ownership verification: only creator or any manager can delete
    - Logs unauthorized deletion attempts

    Permissions: MANAGER desk or superuser only

    Args:
        pk: Primary key of Schedule to delete

    Returns:
        GET: Renders confirmation page
        POST: Deletes schedule and redirects to view
    """
    if not (can_manage_schedules(request.user) or request.user.is_superuser):
        messages.error(request, "You don't have permission to delete schedules.")
        return redirect('schedule_view')

    schedule = get_object_or_404(Schedule, pk=pk)

    # SECURITY FIX: Verify ownership - only creator or any manager can delete
    if schedule.created_by != request.user and not can_manage_schedules(request.user):
        import logging
        logger = logging.getLogger('security.permissions')
        logger.warning(
            f'User {request.user.pk} attempted to delete schedule {pk} '
            f'created by {schedule.created_by.pk if schedule.created_by else "None"}'
        )
        messages.error(
            request,
            'You can only delete your own schedules. Contact a superuser if changes are needed.'
        )
        return redirect('schedule_view')

    if request.method == 'POST':
        schedule_date = schedule.date
        schedule.delete()
        messages.success(request, f"Schedule for {schedule_date.strftime('%d %b %Y')} deleted successfully.")
        return redirect('schedule_view')

    return render(request, 'schedule/schedule_confirm_delete.html', {
        'schedule': schedule,
        'can_manage': can_manage_schedules(request.user),
    })
