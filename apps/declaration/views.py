import calendar
from datetime import date, timedelta
import json

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django_ratelimit.decorators import ratelimit
import logging

from apps.declaration.permissions import can_manage_declarations
from apps.core.validators import validate_file_size
from .models import Declaration
from .forms import DeclarationForm
from apps.operations.models import SDRecord

logger = logging.getLogger(__name__)


@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def declaration_list(request):
    """
    Display all declarations with calendar-based filtering and search.

    Features:
    - Calendar navigation with date selection
    - Search by SD number, agent, declaration number, or contract
    - Filter by creator (show mine)
    - Groups declarations by SD with contract-level details
    - Shows balance tracking per contract
    - Pagination at 10 declarations per page

    Permissions: All authenticated users can view
    Rate limit: 10 requests per minute per user

    Returns:
        Renders declaration_list.html with filtered declarations
    """
    # DEBUG: Log user desk assignments
    from apps.core.permissions import _get_user_desks
    user_desks = _get_user_desks(request.user)
    logger.info(f"DEBUG declaration_list - User: {request.user.staff_number}, Desks: {user_desks}, desk field: {getattr(request.user, 'desk', None)}, desks field: {getattr(request.user, 'desks', None)}")

    today = date.today()
    show_mine = request.GET.get('mine', '').lower() == 'true'
    q = request.GET.get('q', '').strip()

    # Date selection for calendar (optional)
    date_str = request.GET.get('date', '')
    selected_date = None
    if date_str:
        try:
            selected_date = date.fromisoformat(date_str)
        except ValueError:
            pass

    # Calendar navigation
    cal_year = int(request.GET.get('cal_year', today.year))
    cal_month = int(request.GET.get('cal_month', today.month))
    if cal_month < 1:
        cal_month, cal_year = 12, cal_year - 1
    elif cal_month > 12:
        cal_month, cal_year = 1, cal_year + 1

    month_start = date(cal_year, cal_month, 1)
    month_end = date(cal_year, cal_month, calendar.monthrange(cal_year, cal_month)[1])

    # Get all declaration dates in the current month for calendar dots
    declaration_dates = set(
        Declaration.objects
        .filter(date__gte=month_start, date__lte=month_end)
        .values_list('date', flat=True)
    )

    # Default behavior (no search): show records for today unless user selects a date.
    # Search mode intentionally shows history across all dates.
    if not q and not selected_date:
        selected_date = today
        date_str = today.isoformat()

    # If searching, ignore date filter entirely (history)
    if q:
        selected_date = None
        date_str = ''

    prev_month = (date(cal_year, cal_month, 1) - timedelta(days=1)).replace(day=1)
    next_month = (date(cal_year, cal_month, 28) + timedelta(days=7)).replace(day=1)

    # Get all declarations
    qs = Declaration.objects.select_related('sd_record', 'allocation', 'created_by').order_by('-created_at')

    # Filter by date if selected (date view). Search mode shows full history.
    if selected_date and not q:
        qs = qs.filter(date=selected_date)

    if show_mine:
        qs = qs.filter(created_by=request.user)

    # Search filter
    if q:
        qs = qs.filter(
            Q(sd_number__icontains=q) |
            Q(agent__icontains=q) |
            Q(declaration_number__icontains=q) |
            Q(contract_number__icontains=q)
        ).distinct()

    # Group declarations by SD
    sd_groups = {}
    for d in qs:
        sd_key = d.sd_number
        if sd_key not in sd_groups:
            sd_record = d.sd_record
            sd_groups[sd_key] = {
                'sd_number': sd_key,
                'agent': d.agent or (sd_record.agent if sd_record else ''),
                'sd_record': sd_record,
                'declarations': [],
                'file_count': 0,
            }

        sd_groups[sd_key]['declarations'].append(d)
        if d.declaration_pdf:
            sd_groups[sd_key]['file_count'] += 1

    # Sort declarations alphabetically by allocation label (A, B, C, D, E, F)
    for sd in sd_groups.values():
        sd['declarations'] = sorted(
            sd['declarations'],
            key=lambda x: x.allocation.allocation_label if x.allocation and x.allocation.allocation_label else 'ZZZ'
        )

    # Paginate SD groups
    sd_groups_list = list(sd_groups.values())
    paginator = Paginator(sd_groups_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'declaration/declaration_list.html', {
        'sd_groups': page_obj.object_list,
        'page_obj': page_obj,
        'selected_date': selected_date,
        'today': today,
        'q': q,
        'cal_year': cal_year,
        'cal_month': cal_month,
        'cal_month_name': date(cal_year, cal_month, 1).strftime('%B %Y'),
        'cal_weeks': calendar.monthcalendar(cal_year, cal_month),
        'declaration_dates': [d.isoformat() for d in declaration_dates],
        'show_mine': show_mine,
        'can_manage': can_manage_declarations(request.user),
        'prev_month': prev_month,
        'next_month': next_month,
    })


@ratelimit(key='user', rate='20/h', method='POST')
@login_required(login_url='login')
def declaration_create(request):
    """
    Create declarations for all contracts in an SD (declarations desk only).

    Features:
    - One form submission creates multiple declarations (one per contract)
    - Auto-loads all contract allocations from SD record
    - Validates tonnage against allocated amounts
    - File upload for each contract's declaration PDF
    - Prevents duplicate declarations for same SD
    - Redirects to edit if declaration already exists

    Security:
    - Only declarations desk can create
    - Rate limiting: 20 creations per hour per user
    - File size validation (10MB max)
    - Tonnage validation (must be ≤ allocated)

    Permissions: DECLARATIONS desk or superuser only

    Returns:
        GET: Renders declaration form with SD allocations
        POST: Creates declarations and redirects to list
    """
    # SECURITY: Rate limiting prevents spam and DoS attacks
    if getattr(request, 'limited', False):
        messages.error(request, "Too many declaration creation attempts. Please wait before trying again.")
        return redirect('declaration_list')

    if not can_manage_declarations(request.user):
        messages.error(request, "Only the Declaration desk can add declarations.")
        return redirect('declaration_list')

    if request.method == 'POST':
        from .forms import DeclarationHeaderForm, DeclarationLineForm
        header_form = DeclarationHeaderForm(request.POST)

        if header_form.is_valid():
            sd_number = header_form.cleaned_data['sd_number']
            declaration_date = header_form.cleaned_data.get('date') or date.today()

            # Get the SD record
            try:
                sd_record = SDRecord.objects.get(sd_number__iexact=sd_number)
            except SDRecord.DoesNotExist:
                messages.error(request, f"SD {sd_number} not found in operations records.")
                return render(request, 'declaration/declaration_form.html', {
                    'header_form': header_form,
                    'can_manage': can_manage_declarations(request.user),
                })

            # Check if declaration already exists for this SD
            existing_declaration = Declaration.objects.filter(sd_record=sd_record).first()
            if existing_declaration:
                messages.info(request, f"Declaration for SD {sd_record.sd_number} already exists. Redirecting to edit page.")
                return redirect('declaration_edit', pk=existing_declaration.pk)

            # Process each allocation's declaration
            allocations = sd_record.allocations.all()
            declarations_created = 0

            for idx, allocation in enumerate(allocations):
                decl_number = request.POST.get(f'declaration_number_{idx}', '').strip()
                tonnage = request.POST.get(f'tonnage_{idx}', '').strip()
                agent = request.POST.get(f'agent_{idx}', '').strip()
                pdf_file = request.FILES.get(f'declaration_pdf_{idx}')

                # Only create declaration if declaration number is provided
                if decl_number:
                    try:
                        # SECURITY: Validate file size before processing
                        if pdf_file:
                            validate_file_size(pdf_file, 'pdf')

                        tonnage_decimal = float(tonnage) if tonnage else 0

                        # VALIDATION: Declared tonnage must be within [0, allocated]
                        if tonnage_decimal < 0:
                            messages.error(
                                request,
                                f"Declaration for {allocation.allocation_label or allocation.contract_number} has negative tonnage. "
                                f"Allocated: {allocation.allocated_tonnage} MT, Attempted: {tonnage_decimal:.2f} MT"
                            )
                            continue

                        if tonnage_decimal > float(allocation.allocated_tonnage):
                            messages.error(
                                request,
                                f"Declaration for {allocation.allocation_label or allocation.contract_number} exceeds allocated tonnage. "
                                f"Allocated: {allocation.allocated_tonnage} MT, Attempted: {tonnage_decimal:.2f} MT"
                            )
                            continue

                        decl = Declaration.objects.create(
                            sd_record=sd_record,
                            sd_number=sd_record.sd_number,
                            allocation=allocation,
                            contract_number=allocation.contract_number,
                            agent=agent or allocation.agent or sd_record.agent,
                            vessel=sd_record.vessel_name,
                            declaration_number=decl_number,
                            tonnage=tonnage_decimal,
                            declaration_pdf=pdf_file,
                            date=declaration_date,
                            created_by=request.user,
                        )
                        declarations_created += 1
                    except ValidationError as e:
                        messages.error(request, str(e))
                    except Exception as e:
                        # SECURITY: Log detailed error but show generic message to user
                        logger.error(
                            f"Error creating declaration for {allocation.allocation_label}: {str(e)}",
                            exc_info=True,
                            extra={
                                'user': request.user.pk,
                                'sd_number': sd_number,
                                'allocation_label': allocation.allocation_label
                            }
                        )
                        messages.error(request, f"An error occurred while creating declaration for {allocation.allocation_label}. Please try again or contact support.")

            if declarations_created > 0:
                messages.success(
                    request,
                    f"✓ {declarations_created} declaration(s) created by {request.user.first_name} {request.user.last_name} for SD {sd_record.sd_number}"
                )
                # Redirect to list page with the declaration date so user can see their changes
                return redirect(f'/declarations/?date={declaration_date.isoformat()}')
            else:
                messages.warning(request, "No declarations were created. Please fill in at least one declaration number.")
        else:
            messages.error(request, "Please select an SD record.")
    else:
        from .forms import DeclarationHeaderForm
        sd_param = request.GET.get('sd')
        initial = {}
        if sd_param:
            try:
                sd_rec = SDRecord.objects.get(pk=sd_param)
                initial = {'sd_record': sd_rec}
            except SDRecord.DoesNotExist:
                pass
        # Default date to today (matches booking create UX)
        initial.setdefault('date', date.today())
        header_form = DeclarationHeaderForm(initial=initial)

    return render(request, 'declaration/declaration_form.html', {
        'header_form': header_form,
        'action': 'Create',
        'can_manage': can_manage_declarations(request.user),
    })


@login_required(login_url='login')
def declaration_edit(request, pk):
    """
    Edit existing declarations for an SD (declarations desk only).

    Features:
    - Update existing declarations (number, tonnage, PDF)
    - Create new declarations for contracts that don't have one yet
    - Validates tonnage against allocated amounts
    - Preserves existing PDFs if no new file uploaded
    - Full audit trail with updated_by tracking

    Security:
    - Only declarations desk can edit
    - File size validation (10MB max)
    - Tonnage validation (must be ≤ allocated)

    Permissions: DECLARATIONS desk or superuser only

    Args:
        pk: Primary key of any Declaration for the SD (all declarations for that SD will be editable)

    Returns:
        GET: Renders edit form with all SD allocations and existing declarations
        POST: Updates/creates declarations and redirects to list
    """
    if not can_manage_declarations(request.user):
        messages.error(request, "Only the Declaration desk can edit declarations.")
        return redirect('declaration_list')

    decl = get_object_or_404(Declaration, pk=pk)

    # Get the SD record and all declarations for this SD
    sd_record = decl.sd_record
    if not sd_record:
        messages.error(request, "SD record not found for this declaration.")
        return redirect('declaration_list')

    if request.method == 'POST':
        # Process the edit form submission - update existing declarations AND create new ones
        allocations = sd_record.allocations.all()
        declarations_updated = 0
        declarations_created = 0

        # Get the declaration date from the form
        declaration_date = request.POST.get('date')
        if declaration_date:
            try:
                from datetime import datetime
                declaration_date = datetime.strptime(declaration_date, '%Y-%m-%d').date()
            except ValueError:
                declaration_date = date.today()
        else:
            declaration_date = date.today()

        for idx, allocation in enumerate(allocations):
            decl_number = request.POST.get(f'declaration_number_{idx}', '').strip()
            tonnage = request.POST.get(f'tonnage_{idx}', '').strip()
            agent = request.POST.get(f'agent_{idx}', '').strip()
            pdf_file = request.FILES.get(f'declaration_pdf_{idx}')
            declaration_id = request.POST.get(f'declaration_id_{idx}')

            # Skip if no declaration number provided
            if not decl_number:
                continue

            try:
                # SECURITY: Validate file size before processing
                if pdf_file:
                    validate_file_size(pdf_file, 'pdf')

                tonnage_decimal = float(tonnage) if tonnage else 0

                # VALIDATION: Check if declared tonnage exceeds allocated tonnage
                if tonnage_decimal < 0:
                    messages.error(
                        request,
                        f"Declaration for {allocation.allocation_label or allocation.contract_number} has negative tonnage. "
                        f"Allocated: {allocation.allocated_tonnage} MT, Attempted: {tonnage_decimal:.2f} MT"
                    )
                    continue

                if tonnage_decimal > float(allocation.allocated_tonnage):
                    messages.error(
                        request,
                        f"Declaration for {allocation.allocation_label or allocation.contract_number} exceeds allocated tonnage. "
                        f"Allocated: {allocation.allocated_tonnage} MT, Attempted: {tonnage_decimal:.2f} MT"
                    )
                    continue

                if declaration_id:
                    # Update existing declaration
                    existing_decl = Declaration.objects.get(pk=declaration_id)
                    existing_decl.declaration_number = decl_number
                    existing_decl.tonnage = tonnage_decimal
                    existing_decl.agent = agent or allocation.agent or sd_record.agent
                    if pdf_file:
                        existing_decl.declaration_pdf = pdf_file
                    existing_decl.updated_by = request.user
                    existing_decl.save()
                    declarations_updated += 1
                else:
                    # Create new declaration for this allocation
                    Declaration.objects.create(
                        sd_record=sd_record,
                        sd_number=sd_record.sd_number,
                        allocation=allocation,
                        contract_number=allocation.contract_number,
                        agent=agent or allocation.agent or sd_record.agent,
                        vessel=sd_record.vessel_name,
                        declaration_number=decl_number,
                        tonnage=tonnage_decimal,
                        declaration_pdf=pdf_file,
                        date=declaration_date,
                        created_by=request.user,
                    )
                    declarations_created += 1
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                # SECURITY: Log detailed error but show generic message to user
                logger.error(
                    f"Error processing declaration for {allocation.allocation_label}: {str(e)}",
                    exc_info=True,
                    extra={
                        'user': request.user.pk,
                        'sd_number': sd_record.sd_number,
                        'allocation_label': allocation.allocation_label
                    }
                )
                messages.error(request, f"An error occurred while processing declaration for {allocation.allocation_label}. Please try again or contact support.")

        if declarations_updated > 0 or declarations_created > 0:
            success_parts = []
            if declarations_updated > 0:
                success_parts.append(f"{declarations_updated} updated")
            if declarations_created > 0:
                success_parts.append(f"{declarations_created} created")
            messages.success(
                request,
                f"✓ Declaration(s) {', '.join(success_parts)} by {request.user.first_name} {request.user.last_name} for SD {sd_record.sd_number}"
            )
            # Redirect to list page with the declaration date so user can see their changes
            return redirect(f'/declarations/?date={declaration_date.isoformat()}')
        else:
            messages.warning(request, "No declarations were updated or created.")

    # GET request - display form with prepopulated data
    from .forms import DeclarationHeaderForm

    # Create header form with SD record pre-selected
    # Default date to the existing declaration date if available (matches booking edit UX)
    first_decl_date = (
        Declaration.objects.filter(sd_record=sd_record)
        .exclude(created_at__isnull=True)
        .order_by('created_at')
        .values_list('created_at', flat=True)
        .first()
    )

    header_form = DeclarationHeaderForm(initial={
        'sd_number': sd_record.sd_number,
        'date': first_decl_date.date() if first_decl_date else date.today(),
    })

    all_declarations = Declaration.objects.filter(sd_record=sd_record).select_related('allocation')

    # Prepare declaration data for prepopulation
    declaration_data = {
        'sd_number': sd_record.sd_number,
        'sd_id': sd_record.pk,
        'declarations': []
    }

    # Map declarations by allocation ID
    decl_map = {}
    for d in all_declarations:
        if d.allocation_id:
            decl_map[d.allocation_id] = {
                'declaration_number': d.declaration_number,
                'tonnage': str(d.tonnage),
                'agent': d.agent,
                'has_file': bool(d.declaration_pdf),
                'declaration_id': d.pk
            }

    # Get all allocations for this SD
    allocations = sd_record.allocations.all()
    for alloc in allocations:
        if alloc.pk in decl_map:
            declaration_data['declarations'].append(decl_map[alloc.pk])
        else:
            # No declaration for this allocation yet
            declaration_data['declarations'].append({
                'declaration_number': '',
                'tonnage': '',
                'agent': alloc.agent or sd_record.agent,
                'has_file': False,
                'declaration_id': None
            })

    return render(request, 'declaration/declaration_form.html', {
        'header_form': header_form,
        'declaration_data_json': json.dumps(declaration_data),
        'is_edit_mode': True,
        'action': 'Edit',
        'can_manage': can_manage_declarations(request.user),
    })


@login_required(login_url='login')
def declaration_delete(request, pk):
    """
    Delete a declaration record (declarations desk only).

    Features:
    - Confirmation page before deletion
    - Deletes uploaded PDF file
    - No cascade effects (standalone record)

    Security:
    - Only declarations desk can delete
    - No ownership verification (any declarations user can delete)

    Permissions: DECLARATIONS desk or superuser only

    Args:
        pk: Primary key of Declaration to delete

    Returns:
        GET: Renders confirmation page
        POST: Deletes declaration and redirects to list
    """
    if not can_manage_declarations(request.user):
        messages.error(request, "Only the Declaration desk can delete declarations.")
        return redirect('declaration_list')

    decl = get_object_or_404(Declaration, pk=pk)

    if request.method == 'POST':
        sd_number = decl.sd_number
        decl.delete()
        messages.success(request, f"Declaration for SD {sd_number} deleted successfully.")
        return redirect('declaration_list')

    return render(request, 'declaration/declaration_confirm_delete.html', {
        'declaration': decl,
        'can_manage': can_manage_declarations(request.user),
    })
