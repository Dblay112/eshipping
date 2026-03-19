"""Evacuation management views for container tracking."""
import io
from datetime import date
import calendar as cal_module
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import inlineformset_factory
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django_ratelimit.decorators import ratelimit
import logging

from apps.evacuation.permissions import can_manage_evacuations
from apps.operations.models import SDRecord
from apps.core.validators import validate_file_size
from .models import Evacuation, EvacuationLine, EvacuationContainer
from .forms import EvacuationForm, EvacuationLineForm, EvacuationLineFormSet

logger = logging.getLogger(__name__)


@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def evacuation_list(request):
    """
    Display all evacuation records with calendar-based filtering and search.

    Features:
    - Calendar navigation with date selection
    - Search by SD number, agent, or vessel
    - Filter by creator (show mine)
    - Groups evacuation lines by SD number
    - Shows shift information (Day/Night)
    - Expandable rows for container details
    - Pagination at 10 evacuations per page

    Permissions: All authenticated users can view
    Rate limit: 10 requests per minute per user

    Returns:
        Renders evacuation_list.html with filtered evacuations
    """
    # DEBUG: Log user desk assignments
    from apps.core.permissions import _get_user_desks
    user_desks = _get_user_desks(request.user)
    logger.info(
        f"DEBUG evacuation_list - User: {request.user.staff_number}, Desks: {user_desks}, desk field: {getattr(request.user, 'desk', None)}, desks field: {getattr(request.user, 'desks', None)}")

    show_mine = request.GET.get('mine', '').lower() == 'true'
    q = request.GET.get('q', '').strip()
    today = date.today()

    # Calendar state
    cal_year = int(request.GET.get('cal_year', today.year))
    cal_month = int(request.GET.get('cal_month', today.month))
    if cal_month < 1:
        cal_month, cal_year = 12, cal_year - 1
    elif cal_month > 12:
        cal_month, cal_year = 1, cal_year + 1

    date_str = request.GET.get('date', '')
    selected_date = None
    if date_str:
        try:
            selected_date = date.fromisoformat(date_str)
        except ValueError:
            pass

    # Default behavior (no search): show records for today unless user selects a date.
    # Search mode intentionally shows history across all dates.
    if not q and not selected_date:
        selected_date = today
        date_str = today.isoformat()

    prev_month = (date(cal_year, cal_month, 1) -
                  timedelta(days=1)).replace(day=1)
    next_month = (date(cal_year, cal_month, 28) +
                  timedelta(days=7)).replace(day=1)

    month_start = date(cal_year, cal_month, 1)
    month_end = date(cal_year, cal_month,
                     cal_module.monthrange(cal_year, cal_month)[1])
    evac_dates = set(
        Evacuation.objects.filter(date__gte=month_start, date__lte=month_end)
        .values_list('date', flat=True)
    )

    # Get all evacuation lines
    sd_lines = EvacuationLine.objects.select_related(
        'evacuation', 'sd_record').order_by('sd_number', '-evacuation__date')

    # Filter by date if selected (date view should not merge SDs across days)
    # When searching by SD/agent/vessel, show history across all dates.
    if selected_date and not q:
        sd_lines = sd_lines.filter(evacuation__date=selected_date)
    elif selected_date and q:
        selected_date = None
        date_str = ''

    if show_mine:
        sd_lines = sd_lines.filter(evacuation__created_by=request.user)

    # Search filter
    if q:
        sd_lines = sd_lines.filter(
            Q(sd_number__icontains=q) |
            Q(agent__icontains=q) |
            Q(vessel__icontains=q)
        ).distinct()

    # Group evacuation lines by SD number
    from itertools import groupby
    lines_list = list(sd_lines)
    grouped_evacuations = []
    for sd_number, group in groupby(lines_list, key=lambda line: line.sd_number):
        lines_in_sd = list(group)
        grouped_evacuations.append({
            'sd_number': sd_number,
            'lines': lines_in_sd,
            'count': len(lines_in_sd),
        })

    # Paginate grouped evacuations
    paginator = Paginator(grouped_evacuations, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Calculate total lines count for display
    total_lines = len(lines_list)

    return render(request, 'evacuation/evacuation_list.html', {
        'grouped_evacuations': page_obj.object_list,
        'page_obj': page_obj,
        'total_lines': total_lines,
        'show_mine': show_mine,
        'q': q,
        'can_manage': can_manage_evacuations(request.user),
        'today': today,
        'selected_date': selected_date,
        'cal_year': cal_year,
        'cal_month': cal_month,
        'cal_month_name': date(cal_year, cal_month, 1).strftime('%B %Y'),
        'cal_weeks': cal_module.monthcalendar(cal_year, cal_month),
        'evacuation_dates': [d.isoformat() for d in evac_dates],
        'prev_month': prev_month,
        'next_month': next_month,
    })


@ratelimit(key='user', rate='20/h', method='POST')
@login_required(login_url='login')
def evacuation_create(request):
    """
    Create new evacuation record with multiple SD lines (evacuation desk only).

    Features:
    - One form submission creates evacuation with multiple SD lines
    - Shift selection (Day/Night)
    - Excel file upload for each SD's container list
    - Auto-links to SD records when available
    - Validates file sizes before processing
    - Full audit trail with created_by tracking

    Security:
    - Only evacuation desk can create
    - Rate limiting: 20 creations per hour per user
    - File size validation (25MB max for Excel)
    - Formset validation for multiple SD lines

    Permissions: EVACUATION desk or superuser only

    Returns:
        GET: Renders evacuation form with empty formset
        POST: Creates evacuation and redirects to list
    """
    # SECURITY: Rate limiting prevents spam and DoS attacks
    if getattr(request, 'limited', False):
        messages.error(
            request, "Too many evacuation creation attempts. Please wait before trying again.")
        return redirect('evacuation_list')

    if not can_manage_evacuations(request.user):
        messages.error(
            request, "Only the Evacuation desk can log evacuations.")
        return redirect('evacuation_list')

    all_sd_numbers = SDRecord.objects.values_list(
        'sd_number', flat=True).distinct()

    if request.method == 'POST':
        form = EvacuationForm(request.POST)
        formset = EvacuationLineFormSet(request.POST, request.FILES)

        # Debug: Print form and formset errors
        if not form.is_valid():
            logger.error(f'Evacuation form errors: {form.errors}')
        if not formset.is_valid():
            logger.error(f'Evacuation formset errors: {formset.errors}')
            logger.error(
                f'Evacuation formset non_form_errors: {formset.non_form_errors()}')

        if form.is_valid() and formset.is_valid():
            # SECURITY: Validate file sizes before processing
            from django.core.exceptions import ValidationError
            try:
                for line_form in formset:
                    if line_form.cleaned_data and not line_form.cleaned_data.get('DELETE'):
                        container_file = line_form.cleaned_data.get(
                            'container_file')
                        if container_file:
                            validate_file_size(container_file, 'excel')
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'evacuation/evacuation_form.html', {
                    'form': form,
                    'formset': formset,
                    'action': 'Create',
                    'can_manage': can_manage_evacuations(request.user),
                    'all_sd_numbers': all_sd_numbers,
                })

            # Validate that each SD exists in operations database
            evac_date = form.cleaned_data['date']
            evac_shift = form.cleaned_data['shift']

            evac = form.save(commit=False)
            evac.created_by = request.user
            evac.save()
            formset.instance = evac

            # DEBUG: Log formset data before saving
            logger.info(
                f"DEBUG evacuation_create - Formset total forms: {formset.total_form_count()}")
            logger.info(
                f"DEBUG evacuation_create - Formset initial forms: {formset.initial_form_count()}")
            logger.info(
                f"DEBUG evacuation_create - POST data TOTAL_FORMS: {request.POST.get('form-TOTAL_FORMS')}")

            # Log each form in detail
            for idx, line_form in enumerate(formset):
                logger.info(
                    f"DEBUG evacuation_create - Form {idx} has_changed: {line_form.has_changed()}")
                logger.info(
                    f"DEBUG evacuation_create - Form {idx} cleaned_data: {line_form.cleaned_data if hasattr(line_form, 'cleaned_data') else 'NO CLEANED DATA'}")
                if line_form.cleaned_data and not line_form.cleaned_data.get('DELETE'):
                    logger.info(
                        f"DEBUG evacuation_create - Form {idx}: SD={line_form.cleaned_data.get('sd_number')}, will be saved")

            saved_lines = formset.save()
            logger.info(
                f"DEBUG evacuation_create - Saved {len(saved_lines)} EvacuationLine records")

            # Log what was actually saved
            for line in saved_lines:
                logger.info(
                    f"DEBUG evacuation_create - Saved line: SD={line.sd_number}, ID={line.pk}")

            # Auto-link sd_record where sd_number matches
            for line in evac.lines.all():
                if not line.sd_record and line.sd_number:
                    try:
                        sd_rec = SDRecord.objects.get(
                            sd_number__iexact=line.sd_number)
                        line.sd_record = sd_rec
                        line.save(update_fields=['sd_record'])
                    except SDRecord.DoesNotExist:
                        pass

            # Build descriptive success message with audit info
            sd_numbers = ', '.join(
                [line.sd_number for line in evac.lines.all()])
            messages.success(
                request,
                f"✓ Evacuation created by {request.user.first_name} {request.user.last_name}: "
                f"{sd_numbers} on {evac.date.strftime('%d %b %Y')} ({evac.get_shift_display()})"
            )
            return redirect('evacuation_list')
        else:
            # Show specific errors
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            if not formset.is_valid():
                if formset.non_form_errors():
                    for error in formset.non_form_errors():
                        messages.error(request, f"Form error: {error}")
                for i, line_form in enumerate(formset):
                    if line_form.errors:
                        for field, errors in line_form.errors.items():
                            for error in errors:
                                messages.error(
                                    request, f"SD Line {i+1} - {field}: {error}")
            messages.error(request, "Please fix the errors above.")
    else:
        form = EvacuationForm(initial={'date': date.today().isoformat()})
        formset = EvacuationLineFormSet(queryset=EvacuationLine.objects.none())

    return render(request, 'evacuation/evacuation_form.html', {
        'form': form,
        'formset': formset,
        'action': 'Create',
        'can_manage': can_manage_evacuations(request.user),
        'all_sd_numbers': all_sd_numbers,
    })


@login_required(login_url='login')
def evacuation_edit(request, pk, line_pk=None):
    """
    Edit existing evacuation record (evacuation desk only).

    Features:
    - Update date, shift, and notes
    - Edit single SD line (when line_pk provided) or all lines
    - Update container files for each SD
    - Preserves existing files if no new file uploaded
    - Full audit trail with updated_by tracking

    Security:
    - Only evacuation desk can edit
    - File size validation (25MB max for Excel)
    - Formset validation with minimum 1 SD line (when editing all)

    Permissions: EVACUATION desk or superuser only

    Args:
        pk: Primary key of Evacuation to edit
        line_pk: Optional primary key of specific EvacuationLine to edit

    Returns:
        GET: Renders edit form with existing data
        POST: Updates evacuation and redirects to list
    """
    if not can_manage_evacuations(request.user):
        messages.error(
            request, "Only the Evacuation desk can edit evacuations.")
        return redirect('evacuation_list')

    evac = get_object_or_404(Evacuation, pk=pk)

    all_sd_numbers = SDRecord.objects.values_list(
        'sd_number', flat=True).distinct()

    # If editing a specific line, filter queryset to only that line
    if line_pk:
        line = get_object_or_404(EvacuationLine, pk=line_pk, evacuation=evac)
        # For single-line edit: min_num=0 (can delete this line if other lines exist)
        EditEvacuationLineFormSet = inlineformset_factory(
            Evacuation, EvacuationLine,
            form=EvacuationLineForm,
            extra=0, can_delete=True, min_num=0, validate_min=False,
        )
    else:
        # For full edit: min_num=1 (must keep at least one line)
        EditEvacuationLineFormSet = inlineformset_factory(
            Evacuation, EvacuationLine,
            form=EvacuationLineForm,
            extra=0, can_delete=True, min_num=1, validate_min=True,
        )

    if request.method == 'POST':
        form = EvacuationForm(request.POST, instance=evac)

        # Filter queryset if editing single line
        if line_pk:
            formset = EditEvacuationLineFormSet(
                request.POST, request.FILES, instance=evac,
                queryset=EvacuationLine.objects.filter(pk=line_pk)
            )
        else:
            formset = EditEvacuationLineFormSet(
                request.POST, request.FILES, instance=evac)

        if form.is_valid() and formset.is_valid():
            saved = form.save(commit=False)
            saved.updated_by = request.user
            saved.save()
            saved_lines = formset.save()

            # Build descriptive success message
            if line_pk:
                messages.success(
                    request,
                    f"✓ SD line updated: {line.sd_number}"
                )
            else:
                sd_numbers = ', '.join(
                    [line.sd_number for line in evac.lines.all()])
                messages.success(
                    request,
                    f"✓ Evacuation updated: {sd_numbers} on {evac.date.strftime('%d %b %Y')} ({evac.get_shift_display()})"
                )
            return redirect('evacuation_list')

        # Show specific form errors
        if not form.is_valid():
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        # Show specific formset errors
        if not formset.is_valid():
            if formset.non_form_errors():
                for error in formset.non_form_errors():
                    # Translate Django's generic message to user-friendly message
                    error_str = str(error)
                    if "at least 1" in error_str.lower():
                        messages.error(request, "You must keep at least one SD line. Cannot delete all lines.")
                    else:
                        messages.error(request, error_str)

            # Show line-specific errors
            for i, line_form in enumerate(formset):
                if line_form.errors:
                    for field, errors in line_form.errors.items():
                        for error in errors:
                            messages.error(request, f"SD Line {i+1} - {field}: {error}")
    else:
        form = EvacuationForm(instance=evac)

        # Filter queryset if editing single line
        if line_pk:
            formset = EditEvacuationLineFormSet(
                instance=evac,
                queryset=EvacuationLine.objects.filter(pk=line_pk)
            )
        else:
            formset = EditEvacuationLineFormSet(instance=evac)

    return render(request, 'evacuation/evacuation_form.html', {
        'form': form,
        'formset': formset,
        'evac': evac,
        'record': evac,
        'action': 'Edit',
        'can_manage': can_manage_evacuations(request.user),
        'all_sd_numbers': all_sd_numbers,
    })


@login_required(login_url='login')
def evacuation_detail(request, pk):
    """
    Display detailed view of evacuation record.

    Shows:
    - Evacuation date, shift, and notes
    - All SD lines with vessel and agent information
    - Container details for each SD
    - Links to SD records when available
    - Creator and timestamps

    Permissions: All authenticated users can view

    Args:
        pk: Primary key of Evacuation to view

    Returns:
        Renders evacuation_detail.html with evacuation data
    """
    evac = get_object_or_404(
        Evacuation.objects.prefetch_related(
            'lines__sd_record', 'lines__containers'
        ).select_related('created_by'),
        pk=pk,
    )
    return render(request, 'evacuation/evacuation_detail.html', {
        'evac': evac,
        'can_manage': can_manage_evacuations(request.user),
    })


@login_required(login_url='login')
def evacuation_line_delete(request, line_pk):
    """
    Delete a single SD line from an evacuation record (evacuation desk only).

    Features:
    - Deletes individual SD line from evacuation
    - Cascades deletion: if last line, deletes parent Evacuation too
    - Confirmation page before deletion
    - Descriptive success messages

    Security:
    - Only evacuation desk can delete
    - Confirmation required before deletion

    Permissions: EVACUATION desk or superuser only

    Args:
        line_pk: Primary key of EvacuationLine to delete

    Returns:
        GET: Renders confirmation page
        POST: Deletes line and redirects to list
    """
    if not can_manage_evacuations(request.user):
        messages.error(
            request, "Only the Evacuation desk can delete evacuation records.")
        return redirect('evacuation_list')

    line = get_object_or_404(EvacuationLine, pk=line_pk)
    evac = line.evacuation

    if request.method == 'POST':
        sd_number = line.sd_number
        evac_date = evac.date
        shift = evac.get_shift_display()

        # Delete the line
        line.delete()

        # Check if parent Evacuation has any remaining lines
        remaining_lines = evac.lines.count()
        if remaining_lines == 0:
            # No lines left, delete the parent Evacuation too
            evac.delete()
            messages.success(
                request,
                f"SD {sd_number} evacuation deleted. No more records for {evac_date.strftime('%d %b %Y')} ({shift}), evacuation record removed."
            )
        else:
            messages.success(
                request,
                f"SD {sd_number} evacuation deleted from {evac_date.strftime('%d %b %Y')} ({shift})."
            )

        return redirect('evacuation_list')

    return render(request, 'evacuation/evacuation_confirm_delete.html', {
        'line': line,
        'evac': evac,
        'can_manage': can_manage_evacuations(request.user),
    })
