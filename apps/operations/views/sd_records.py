"""SD record management views for operations desk."""
import io
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django_ratelimit.decorators import ratelimit

from apps.core.validators import validate_file_size

from ..forms import (
    SDAllocationFormSet,
    SDClerkFormSet,
    SDRecordForm,
    get_container_formset,
)
from ..models import SDContainer, SDRecord, ScheduleEntry
from ..permissions import can_manage_schedules, can_manage_sd_records
from .sync import sync_existing_tallies


# ══════════════════════════════════════════════════════
#  OPERATIONS — SD RECORD VIEWS
# ══════════════════════════════════════════════════════

@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def operations_list(request):
    """
    Display all SD records with search and filtering.

    Features:
    - Search by SD number, vessel, buyer, agent, SI REF, MK number, or contract
    - Filter by creator (show mine)
    - Shows related counts (tallies, bookings, declarations, evacuations)
    - Shows assigned officer from schedule
    - Bulk-loads related data to avoid N+1 queries
    - Pagination at 10 SDs per page

    Permissions: All authenticated users can view
    Rate limit: 10 requests per minute per user

    Returns:
        Renders operations_list.html with filtered SD records
    """
    from apps.tally.models import TallyInfo

    q = request.GET.get('q', '').strip()
    show_mine = request.GET.get('mine', '').lower() == 'true'

    sds = SDRecord.objects.prefetch_related('allocations', 'containers', 'clerks')

    if show_mine:
        sds = sds.filter(created_by=request.user)

    if q:
        sds = sds.filter(
            Q(sd_number__icontains=q) |
            Q(vessel_name__icontains=q) |
            Q(buyer__icontains=q) |
            Q(agent__icontains=q) |
            Q(si_ref__icontains=q) |
            Q(allocations__mk_number__icontains=q) |
            Q(allocations__contract_number__icontains=q)
        ).distinct()

    sds = sds.order_by('-created_at')

    # Annotate with related counts and assigned officer
    sds_list = list(sds)

    # Bulk-load approved tally counts in one query (avoid N+1)
    sd_numbers = [sd.sd_number for sd in sds_list]
    tallies_counts_qs = (
        TallyInfo.objects
        .filter(sd_number__in=sd_numbers, status='APPROVED')
        .values('sd_number')
        .annotate(c=Count('id'))
    )
    tallies_count_map = {row['sd_number']: row['c'] for row in tallies_counts_qs}

    # Bulk-load assigned officers in one query (avoid per-SD lookups)
    schedule_entries = (
        ScheduleEntry.objects
        .filter(sd_number__in=sd_numbers)
        .select_related('assigned_officer')
        .order_by('id')
    )
    assigned_officer_map = {}
    for se in schedule_entries:
        # Keep first entry per SD number (matches previous .first() behavior)
        if se.sd_number not in assigned_officer_map:
            assigned_officer_map[se.sd_number] = se.assigned_officer

    for sd in sds_list:
        # Count approved tallies only
        sd.tallies_count = tallies_count_map.get(sd.sd_number, 0)

        # Get assigned officer from schedule
        sd.assigned_officer = assigned_officer_map.get(sd.sd_number)

        # Note: has_bookings, has_declarations, has_evacuations are now properties on the model
        # They are automatically calculated when accessed in templates

    paginator = Paginator(sds_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'operations/operations_list.html', {
        'sds': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'show_mine': show_mine,
        'can_manage': can_manage_sd_records(request.user),
        'is_operations': can_manage_sd_records(request.user),
        'is_superior': can_manage_schedules(request.user) or request.user.is_superuser,
    })


@ratelimit(key='user', rate='20/h', method='POST')
@login_required(login_url='login')
def sd_create(request):
    """
    Create new SD record with contract allocations (operations desk only).

    Features:
    - One form creates SD with multiple contract allocations
    - Optional containers and clerks (auto-populated from tallies)
    - Draft save option (saves shipment info + allocations only)
    - File uploads (SD document PDF, container list Excel)
    - Auto-links orphaned records (tallies, bookings, declarations, evacuations)
    - Syncs assigned officer from schedule entries
    - Prevents duplicate SD numbers

    Security:
    - Only operations desk can create
    - Rate limiting: 20 creations per hour per user
    - File size validation (PDF 10MB, Excel 25MB)
    - Duplicate SD number check

    Permissions: OPERATIONS desk or superuser only

    Returns:
        GET: Renders SD form with empty formsets
        POST: Creates SD and redirects to operations_list
    """
    # SECURITY: Rate limiting prevents spam and DoS attacks
    if getattr(request, 'limited', False):
        messages.error(request, 'Too many SD creation attempts. Please wait before trying again.')
        return redirect('operations_list')

    if not (can_manage_sd_records(request.user) or request.user.is_superuser):
        messages.error(request, 'Only the Operations desk can add SD records.')
        return redirect('operations_list')

    ContainerFormSet = get_container_formset()

    if request.method == 'POST':
        form = SDRecordForm(request.POST, request.FILES)
        alloc_formset = SDAllocationFormSet(request.POST, prefix='allocs')
        container_formset = ContainerFormSet(request.POST, prefix='containers')
        clerk_formset = SDClerkFormSet(request.POST, prefix='clerks')

        # Check if this is a draft save (only Shipment Info + Contract Allocations)
        form_action = request.POST.get('form_action', 'create')
        is_draft = form_action == 'save_draft'

        # For draft saves, only validate main form and allocations
        # Containers and clerks are auto-populated from tallies
        if is_draft:
            forms_valid = form.is_valid() and alloc_formset.is_valid()
        else:
            forms_valid = form.is_valid() and alloc_formset.is_valid()

        if forms_valid:
            # SECURITY: Validate file sizes before processing
            from django.core.exceptions import ValidationError
            try:
                if 'sd_document' in request.FILES:
                    validate_file_size(request.FILES['sd_document'], 'pdf')
                if 'container_list' in request.FILES:
                    validate_file_size(request.FILES['container_list'], 'excel')
            except ValidationError as e:
                messages.error(request, str(e))
                return render(request, 'sd/sd_form.html', {
                    'form': form,
                    'alloc_formset': alloc_formset,
                    'container_formset': container_formset,
                    'clerk_formset': clerk_formset,
                    'action': 'Create',
                    'can_manage': can_manage_sd_records(request.user),
                    'is_operations': can_manage_sd_records(request.user),
                    'is_superior': can_manage_schedules(request.user) or request.user.is_superuser,
                })

            # Check if SD number already exists
            sd_number = form.cleaned_data.get('sd_number')
            existing_sd = SDRecord.objects.filter(sd_number__iexact=sd_number).first()
            if existing_sd:
                messages.warning(request, f'SD {sd_number} already exists. Redirecting to edit page.')
                return redirect('sd_edit', pk=existing_sd.pk)

            sd = form.save(commit=False)
            sd.created_by = request.user
            sd.date_of_entry = sd.created_at.date() if sd.created_at else None
            if not sd.date_of_entry:
                from datetime import date as _date
                sd.date_of_entry = _date.today()
            sd.save()

            alloc_formset.instance = sd
            alloc_formset.save()

            # Save containers and clerks if valid (they're auto-populated from tallies)
            if not is_draft:
                if container_formset.is_valid():
                    container_formset.instance = sd
                    container_formset.save()

                if clerk_formset.is_valid():
                    clerk_formset.instance = sd
                    clerk_formset.save()

                # Pull any existing tally containers that match this sd_number
                sync_existing_tallies(sd)

            messages.success(
                request,
                f"✓ SD Record {sd.sd_number} {'saved as draft' if is_draft else 'created'} by {request.user.first_name} {request.user.last_name}"
            )
            return redirect('operations_list')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = SDRecordForm()
        alloc_formset = SDAllocationFormSet(prefix='allocs')
        container_formset = ContainerFormSet(prefix='containers')
        clerk_formset = SDClerkFormSet(prefix='clerks')

    return render(request, 'sd/sd_form.html', {
        'form': form,
        'alloc_formset': alloc_formset,
        'container_formset': container_formset,
        'clerk_formset': clerk_formset,
        'action': 'Create',
        'can_manage': can_manage_sd_records(request.user),
        'is_operations': can_manage_sd_records(request.user),
        'is_superior': can_manage_schedules(request.user) or request.user.is_superuser,
    })


@login_required(login_url='login')
def sd_edit(request, pk):
    """
    Edit existing SD record with tonnage tracking (operations desk only).

    Features:
    - Update shipment information and contract allocations
    - Tonnage tracking per contract (loaded vs allocated)
    - Auto-calculates balances and completion status
    - Prevents over-loading (caps at allocated tonnage)
    - Updates containers and clerks from formsets
    - Full audit trail with updated_by tracking

    Security:
    - Only operations desk can edit
    - Tonnage validation (loaded ≤ allocated)
    - File size validation for uploads

    Permissions: OPERATIONS desk or superuser only

    Args:
        pk: Primary key of SDRecord to edit

    Returns:
        GET: Renders edit form with existing data
        POST: Updates SD and redirects to operations_list
    """
    if not (can_manage_sd_records(request.user) or request.user.is_superuser):
        messages.error(request, 'Only the Operations desk can edit SD records.')
        return redirect('operations_list')

    sd = get_object_or_404(SDRecord, pk=pk)
    ContainerFormSet = get_container_formset(sd_record=sd)

    if request.method == 'POST':
        form = SDRecordForm(request.POST, request.FILES, instance=sd)
        alloc_formset = SDAllocationFormSet(request.POST, instance=sd, prefix='allocs')
        container_formset = ContainerFormSet(request.POST, instance=sd, prefix='containers')
        clerk_formset = SDClerkFormSet(request.POST, instance=sd, prefix='clerks')

        # Containers and clerks are auto-populated from tallies, so we don't validate them strictly
        if form.is_valid() and alloc_formset.is_valid():
            sd = form.save(commit=False)
            sd.updated_by = request.user
            sd.save()
            alloc_formset.save()

            # Save tonnage tracking data (tt_loaded_0, tt_loaded_1, etc.)
            allocations = sd.allocations.all().order_by('allocation_label', 'contract_number')

            # Calculate totals while saving to ensure accuracy
            from decimal import Decimal
            import logging
            logger = logging.getLogger(__name__)

            total_allocated = Decimal('0')
            total_loaded = Decimal('0')

            for idx, allocation in enumerate(allocations):
                tt_loaded_key = f'tt_loaded_{idx}'
                if tt_loaded_key in request.POST:
                    loaded_value = request.POST.get(tt_loaded_key, '').strip()
                    if loaded_value:
                        try:
                            loaded_decimal = Decimal(loaded_value)
                            # Prevent over-loading: cap at allocated tonnage
                            if loaded_decimal > allocation.allocated_tonnage:
                                loaded_decimal = allocation.allocated_tonnage
                            allocation.tonnage_loaded = loaded_decimal
                        except (ValueError, TypeError, ArithmeticError):
                            allocation.tonnage_loaded = Decimal('0')
                    else:
                        allocation.tonnage_loaded = Decimal('0')
                    allocation.save()

                # Add to totals
                total_allocated += Decimal(str(allocation.allocated_tonnage))
                total_loaded += Decimal(str(allocation.tonnage_loaded or 0))

                allocation_balance = Decimal(str(allocation.allocated_tonnage)) - Decimal(str(allocation.tonnage_loaded or 0))
                logger.info(f'[SD EDIT] Allocation {idx}: allocated={allocation.allocated_tonnage}, loaded={allocation.tonnage_loaded}, balance={allocation_balance}')

            # Calculate grand total balance
            grand_balance = total_allocated - total_loaded

            # Keep SD-level summary in sync (detail page depends on this)
            sd.tonnage_loaded = total_loaded

            logger.info(f'[SD EDIT] SD {sd.sd_number}: total_allocated={total_allocated}, total_loaded={total_loaded}, grand_balance={grand_balance}')

            # Mark complete if grand total balance is exactly 0
            sd.is_complete = (grand_balance == 0)
            sd.save()

            logger.info(f'[SD EDIT] SD {sd.sd_number}: is_complete={sd.is_complete}')

            # Save containers and clerks if valid, but don't block on errors
            if container_formset.is_valid():
                container_formset.save()
            if clerk_formset.is_valid():
                clerk_formset.save()

            messages.success(
                request,
                f"✓ SD Record {sd.sd_number} updated by {request.user.first_name} {request.user.last_name}"
            )
            return redirect('sd_detail', pk=sd.pk)

        messages.error(request, 'Please fix the errors below.')
    else:
        form = SDRecordForm(instance=sd)
        alloc_formset = SDAllocationFormSet(instance=sd, prefix='allocs')
        container_formset = ContainerFormSet(instance=sd, prefix='containers')
        clerk_formset = SDClerkFormSet(instance=sd, prefix='clerks')

    return render(request, 'sd/sd_form.html', {
        'form': form,
        'alloc_formset': alloc_formset,
        'container_formset': container_formset,
        'clerk_formset': clerk_formset,
        'sd': sd,
        'action': 'Edit',
        'can_manage': can_manage_sd_records(request.user),
        'is_operations': can_manage_sd_records(request.user),
        'is_superior': can_manage_schedules(request.user) or request.user.is_superuser,
    })


@login_required(login_url='login')
def sd_detail(request, pk):
    """
    Display comprehensive SD record details with all related records.

    Features:
    - Shows shipment information and contract allocations
    - Groups containers by allocation
    - Displays related records from all desks:
      * Bookings (with balance tracking)
      * Declarations (with balance tracking)
      * Tallies (approved only)
      * Evacuations (with container details)
      * Schedule assignments (assigned officers)
    - Loading summary with tonnage loaded and balance
    - Completion status indicator

    Security:
    - IDOR protection: checks permission before fetching data
    - Only authorized users can view (operations, managers, creator, assigned officer)

    Permissions: Operations desk, managers, creator, assigned officer, or superuser

    Args:
        pk: Primary key of SDRecord to view

    Returns:
        Renders sd_detail.html with comprehensive SD data
    """
    from decimal import Decimal

    from apps.core.decorators import check_sd_access_permission

    # SECURITY FIX: Check permission BEFORE fetching data (prevents IDOR)
    if not check_sd_access_permission(request.user, pk):
        messages.error(request, "You don't have permission to view this SD record.")
        return redirect('operations_list')

    # NOW fetch full data after permission is verified
    sd = get_object_or_404(
        SDRecord.objects.prefetch_related('allocations', 'containers__allocation', 'clerks__officer'),
        pk=pk,
    )

    # Group containers by allocation for the detail view
    allocations_with_containers = []
    for alloc in sd.allocations.all():
        allocations_with_containers.append({
            'allocation': alloc,
            'containers': sd.containers.filter(allocation=alloc),
        })
    # Containers with no allocation assigned
    unassigned_containers = sd.containers.filter(allocation__isnull=True)

    # ── AGGREGATED VIEW: Fetch related records from all desks ──
    # Bookings
    bookings = sd.booking_records.select_related('created_by').order_by('-created_at')
    has_bookings = bookings.exists()

    # Declarations
    declarations = sd.declarations.select_related('allocation', 'created_by').order_by('-created_at')
    has_declarations = declarations.exists()

    # Loading summary: compute from allocations (source of truth)
    allocations = list(sd.allocations.all())
    tonnage_loaded = sum((a.tonnage_loaded or Decimal('0')) for a in allocations)
    total_allocated = sum((a.allocated_tonnage or Decimal('0')) for a in allocations)
    grand_balance = max(total_allocated - tonnage_loaded, Decimal('0'))

    # Tallies (approved only)
    from apps.tally.models import TallyInfo
    tallies = TallyInfo.objects.filter(
        sd_number__iexact=sd.sd_number,
        status='APPROVED'
    ).select_related('created_by').order_by('-loading_date')
    has_tallies = tallies.exists()

    # Evacuations
    evacuations = sd.evacuation_lines.select_related('evacuation', 'evacuation__created_by').order_by('-evacuation__date')
    has_evacuations = evacuations.exists()

    # Schedule assignments (find schedule entries for this SD)
    schedule_entries = ScheduleEntry.objects.filter(
        sd_number__iexact=sd.sd_number
    ).select_related('schedule', 'assigned_officer').order_by('-schedule__date')
    has_schedule = schedule_entries.exists()

    return render(request, 'sd/sd_detail.html', {
        'sd': sd,
        'allocations_with_containers': allocations_with_containers,
        'unassigned_containers': unassigned_containers,
        'can_manage': can_manage_sd_records(request.user),
        'is_operations': can_manage_sd_records(request.user),
        'is_superior': can_manage_schedules(request.user) or request.user.is_superuser,
        # Aggregated data
        'bookings': bookings,
        'has_bookings': has_bookings,
        'declarations': declarations,
        'has_declarations': has_declarations,
        'tallies': tallies,
        'has_tallies': has_tallies,
        'evacuations': evacuations,
        'has_evacuations': has_evacuations,
        'schedule_entries': schedule_entries,
        'has_schedule': has_schedule,
        # Loading summary calculations
        'tonnage_loaded': tonnage_loaded,
        'grand_balance': grand_balance,
    })


@login_required(login_url='login')
def sd_export_excel(request, pk):
    """
    Download the uploaded container list Excel file for an SD record.

    Features:
    - Serves the uploaded Excel file as a download
    - Returns 204 No Content if no file attached
    - Redirects to file URL for browser download

    Security:
    - IDOR protection: checks permission before fetching data
    - Only authorized users can download (operations, managers, creator, assigned officer)

    Permissions: Operations desk, managers, creator, assigned officer, or superuser

    Args:
        pk: Primary key of SDRecord to download file from

    Returns:
        Redirects to file URL or returns 204 if no file
    """
    from apps.core.decorators import check_sd_access_permission

    # SECURITY FIX: Check permission BEFORE fetching data (prevents IDOR)
    if not check_sd_access_permission(request.user, pk):
        messages.error(request, "You don't have permission to export this SD record.")
        return redirect('operations_list')

    sd = get_object_or_404(SDRecord, pk=pk)

    # If no file attached, do nothing (no download)
    if not sd.container_list:
        return HttpResponse(status=204)

    # Serve the uploaded file
    return redirect(sd.container_list.url)


@login_required(login_url='login')
def sd_record_delete(request, pk):
    """
    Delete an SD record (operations desk only, creator or superuser).

    Features:
    - Confirmation page before deletion
    - Cascades deletion to related allocations, containers, clerks
    - Orphans related tallies, bookings, declarations (sets sd_record to NULL)
    - Audit logging for unauthorized attempts

    Security:
    - Only operations desk can access
    - Only creator or superuser can delete (ownership verification)
    - Logs unauthorized deletion attempts

    Permissions: Operations desk AND (creator OR superuser)

    Args:
        pk: Primary key of SDRecord to delete

    Returns:
        GET: Renders confirmation page
        POST: Deletes SD and redirects to list
    """
    if not can_manage_sd_records(request.user):
        messages.error(request, "You don't have permission to delete SD records.")
        return redirect('operations_list')

    sd = get_object_or_404(SDRecord, pk=pk)

    # SECURITY FIX: Verify ownership - only creator or superuser can delete
    if sd.created_by != request.user and not request.user.is_superuser:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f'SECURITY: Unauthorized SD delete attempt by user {request.user.pk} '
            f'for SD {pk} created by {sd.created_by.pk if sd.created_by else "None"}'
        )
        messages.error(
            request,
            'You can only delete your own SD records. Contact a superuser if changes are needed.'
        )
        return redirect('operations_list')

    if request.method == 'POST':
        sd_number = sd.sd_number
        sd.delete()
        messages.success(request, f'SD {sd_number} deleted successfully.')
        return redirect('operations_list')

    return render(request, 'operations/sd_confirm_delete.html', {
        'sd': sd,
        'can_manage': can_manage_sd_records(request.user),
    })
