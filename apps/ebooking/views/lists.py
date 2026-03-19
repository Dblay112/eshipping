"""Booking list views."""
import logging
import calendar as cal_module
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect
from django_ratelimit.decorators import ratelimit

from apps.ebooking.permissions import can_manage_bookings
from ..models import BookingRecord
from apps.operations.models import SDRecord, ScheduleEntry

logger = logging.getLogger(__name__)


@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def booking_list(request):
    """
    Display all booking records with calendar-based filtering and search.

    Features:
    - Calendar navigation with date selection
    - Search by SD number, vessel, agent, or contract
    - Filter by creator (show mine)
    - Groups bookings by SD with contract-level details
    - Shows balance tracking per contract
    - Displays correction counts and unviewed corrections
    - Pagination at 10 SDs per page

    Permissions: All authenticated users can view
    Rate limit: 10 requests per minute
    """
    # DEBUG: Log user desk assignments
    from apps.core.permissions import _get_user_desks
    user_desks = _get_user_desks(request.user)
    logger.info(f"DEBUG booking_list - User: {request.user.staff_number}, Desks: {user_desks}, desk field: {getattr(request.user, 'desk', None)}, desks field: {getattr(request.user, 'desks', None)}")

    today = date.today()
    show_mine = request.GET.get('mine', '').lower() == 'true'
    q = request.GET.get('q', '').strip()

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

    # Get booking dates in current month for calendar dots
    booking_dates = set(
        BookingRecord.objects.filter(
            date__gte=month_start,
            date__lte=month_end
        ).values_list('date', flat=True)
    )

    prev_month = (date(cal_year, cal_month, 1) - timedelta(days=1)).replace(day=1)
    next_month = (date(cal_year, cal_month, 28) + timedelta(days=7)).replace(day=1)

    # Default behavior (no search): show records for today unless user selects a date.
    # Search mode intentionally shows history across all dates.
    if not q and not selected_date:
        selected_date = today
        date_str = today.isoformat()

    # If searching, ignore date filter entirely (history)
    if q:
        selected_date = None
        date_str = ''

    # Get all booking records
    qs = BookingRecord.objects.select_related('sd_record', 'created_by').prefetch_related(
        'lines__details'
    ).order_by('-created_at')

    # Filter by date if selected (date view). Search mode shows full history.
    if selected_date and not q:
        qs = qs.filter(date=selected_date)

    if show_mine:
        qs = qs.filter(created_by=request.user)

    # Search filter
    if q:
        qs = qs.filter(
            Q(sd_number__icontains=q) |
            Q(vessel__icontains=q) |
            Q(agent__icontains=q) |
            Q(lines__contract_number__icontains=q)
        ).distinct()

    # Group bookings by SD
    sd_groups = {}
    for booking_record in qs:
        sd_key = booking_record.sd_number
        if sd_key not in sd_groups:
            sd_record = booking_record.sd_record

            # Check if current user is assigned to this SD (via SDRecord OR ScheduleEntry)
            is_assigned_officer = False

            # Check direct assignment on SD record
            if sd_record and sd_record.officer_assigned == request.user:
                is_assigned_officer = True

            # Also check assignment via schedule entry
            if not is_assigned_officer:
                schedule_entry = ScheduleEntry.objects.filter(
                    sd_number__iexact=sd_key
                ).select_related('assigned_officer').first()
                if schedule_entry and schedule_entry.assigned_officer == request.user:
                    is_assigned_officer = True

            sd_groups[sd_key] = {
                'sd_number': sd_key,
                'vessel': booking_record.vessel or (sd_record.vessel_name if sd_record else ''),
                'agent': booking_record.agent or (sd_record.agent if sd_record else ''),
                'sd_record': sd_record,
                'sd_tonnage': float(sd_record.tonnage) if sd_record else None,
                'total_booked': 0,
                'allocation_groups': {},
                'is_assigned_officer': is_assigned_officer,
            }

        # Group by contract
        for line in booking_record.lines.all():
            contract_key = line.contract_number or 'no_contract'
            if contract_key not in sd_groups[sd_key]['allocation_groups']:
                # Find allocation for this contract
                allocation = None
                allocated_tonnage = None
                mk_number = None
                allocation_label = None
                if sd_record and line.contract_number:
                    from apps.operations.models import SDAllocation
                    allocation = SDAllocation.objects.filter(
                        sd_record=sd_record,
                        contract_number__iexact=line.contract_number
                    ).first()
                    if allocation:
                        allocated_tonnage = float(allocation.allocated_tonnage)
                        mk_number = allocation.mk_number
                        allocation_label = allocation.allocation_label

                sd_groups[sd_key]['allocation_groups'][contract_key] = {
                    'contract_number': line.contract_number or '—',
                    'mk_number': mk_number,
                    'allocation_label': allocation_label,
                    'allocated_tonnage': allocated_tonnage,
                    'total_booked': 0,
                    'bookings': [],
                }

            # Add booking details
            for detail in line.details.all():
                # Count corrections for this booking detail
                correction_count = detail.corrections.count()
                has_unviewed_corrections = detail.corrections.filter(viewed_at__isnull=True).exists()

                sd_groups[sd_key]['allocation_groups'][contract_key]['bookings'].append({
                    'pk': booking_record.pk,
                    'detail_id': detail.pk,
                    'booking_number': detail.booking_number,
                    'bill_number': detail.bill_number,
                    'tonnage_booked': float(detail.tonnage_booked),
                    'bill_pdf': detail.file,
                    'created_at': booking_record.created_at,
                    'created_by': booking_record.created_by,
                    'updated_at': booking_record.updated_at,
                    'updated_by': booking_record.updated_by,
                    'correction_count': correction_count,
                    'has_unviewed_corrections': has_unviewed_corrections,
                })
                sd_groups[sd_key]['allocation_groups'][contract_key]['total_booked'] += float(detail.tonnage_booked)
                sd_groups[sd_key]['total_booked'] += float(detail.tonnage_booked)

    # Compute balances
    for sd in sd_groups.values():
        if sd['sd_tonnage'] is not None:
            sd['balance'] = sd['sd_tonnage'] - sd['total_booked']
        else:
            sd['balance'] = None
        for ag in sd['allocation_groups'].values():
            if ag['allocated_tonnage'] is not None:
                ag['balance'] = ag['allocated_tonnage'] - ag['total_booked']
            else:
                ag['balance'] = None
        # Sort allocation groups alphabetically by allocation_label (A, B, C, D, E, F)
        sd['allocation_groups'] = sorted(
            sd['allocation_groups'].values(),
            key=lambda x: x['allocation_label'] or 'ZZZ'  # Put None/empty at end
        )

    # Paginate SD groups
    sd_groups_list = list(sd_groups.values())
    paginator = Paginator(sd_groups_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'ebooking/booking_list.html', {
        'sd_groups': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'show_mine': show_mine,
        'selected_date': selected_date,
        'today': today,
        'cal_year': cal_year,
        'cal_month': cal_month,
        'cal_month_name': date(cal_year, cal_month, 1).strftime('%B %Y'),
        'cal_weeks': cal_module.monthcalendar(cal_year, cal_month),
        'booking_dates': [d.isoformat() for d in booking_dates],
        'prev_month': prev_month,
        'next_month': next_month,
        'can_manage': can_manage_bookings(request.user),
        'is_ebooking': can_manage_bookings(request.user),
    })


@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def assigned_sds_list(request):
    """
    View bookings for SDs assigned to the logged-in user.
    Officers can quickly find their assigned SDs without scrolling through all records.
    """
    today = date.today()
    q = request.GET.get('q', '').strip()
    show_all = request.GET.get('show_all', '').lower() == 'true'

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

    # Get SD records assigned to current user (from SD records OR schedule entries)
    assigned_sd_records = SDRecord.objects.filter(
        officer_assigned=request.user
    ).values_list('sd_number', flat=True)

    # Also get SDs from schedule entries where user is assigned officer
    schedule_sd_numbers = ScheduleEntry.objects.filter(
        assigned_officer=request.user
    ).values_list('sd_number', flat=True)

    # Combine both lists
    all_assigned_sd_numbers = set(assigned_sd_records) | set(schedule_sd_numbers)

    if not all_assigned_sd_numbers:
        # User has no assigned SDs
        return render(request, 'ebooking/assigned_sds_list.html', {
            'sd_groups': [],
            'page_obj': None,
            'q': q,
            'selected_date': selected_date,
            'today': today,
            'cal_year': cal_year,
            'cal_month': cal_month,
            'cal_month_name': date(cal_year, cal_month, 1).strftime('%B %Y'),
            'cal_weeks': cal_module.monthcalendar(cal_year, cal_month),
            'booking_dates': [],
            'prev_month': (date(cal_year, cal_month, 1) - timedelta(days=1)).replace(day=1),
            'next_month': (date(cal_year, cal_month, 28) + timedelta(days=7)).replace(day=1),
            'can_manage': can_manage_bookings(request.user),
            'is_ebooking': can_manage_bookings(request.user),
        })

    # Get booking dates in current month for calendar dots
    booking_dates = set(
        BookingRecord.objects.filter(
            sd_number__in=all_assigned_sd_numbers,
            date__gte=month_start,
            date__lte=month_end
        ).values_list('date', flat=True)
    )

    prev_month = (date(cal_year, cal_month, 1) - timedelta(days=1)).replace(day=1)
    next_month = (date(cal_year, cal_month, 28) + timedelta(days=7)).replace(day=1)

    # Show all mode: display all assigned SDs regardless of booking date
    if show_all:
        # Get all SD records for assigned SDs
        sd_records = SDRecord.objects.filter(
            sd_number__in=all_assigned_sd_numbers
        ).prefetch_related('allocations').order_by('-created_at')

        # Search filter
        if q:
            sd_records = sd_records.filter(
                Q(sd_number__icontains=q) |
                Q(vessel_name__icontains=q) |
                Q(agent__icontains=q)
            )

        # Build SD groups from SD records
        sd_groups = {}
        for sd_record in sd_records:
            sd_key = sd_record.sd_number

            # Get all bookings for this SD (regardless of date)
            bookings = BookingRecord.objects.filter(
                sd_number__iexact=sd_key
            ).prefetch_related('lines__details')

            sd_groups[sd_key] = {
                'sd_number': sd_key,
                'vessel': sd_record.vessel_name,
                'agent': sd_record.agent,
                'sd_record': sd_record,
                'sd_tonnage': float(sd_record.tonnage) if sd_record.tonnage else None,
                'total_booked': 0,
                'allocation_groups': {},
                'is_assigned_officer': True,
            }

            # Process bookings if they exist
            for booking_record in bookings:
                for line in booking_record.lines.all():
                    contract_key = line.contract_number or 'no_contract'
                    if contract_key not in sd_groups[sd_key]['allocation_groups']:
                        allocation = None
                        allocated_tonnage = None
                        mk_number = None
                        allocation_label = None
                        if line.contract_number:
                            from apps.operations.models import SDAllocation
                            allocation = SDAllocation.objects.filter(
                                sd_record=sd_record,
                                contract_number__iexact=line.contract_number
                            ).first()
                            if allocation:
                                allocated_tonnage = float(allocation.allocated_tonnage)
                                mk_number = allocation.mk_number
                                allocation_label = allocation.allocation_label

                        sd_groups[sd_key]['allocation_groups'][contract_key] = {
                            'contract_number': line.contract_number or '—',
                            'mk_number': mk_number,
                            'allocation_label': allocation_label,
                            'allocated_tonnage': allocated_tonnage,
                            'total_booked': 0,
                            'bookings': [],
                        }

                    for detail in line.details.all():
                        correction_count = detail.corrections.count()
                        has_unviewed_corrections = detail.corrections.filter(viewed_at__isnull=True).exists()
                        sd_groups[sd_key]['allocation_groups'][contract_key]['bookings'].append({
                            'pk': booking_record.pk,
                            'detail_id': detail.pk,
                            'booking_number': detail.booking_number,
                            'bill_number': detail.bill_number,
                            'tonnage_booked': float(detail.tonnage_booked),
                            'bill_pdf': detail.file,
                            'created_at': booking_record.created_at,
                            'created_by': booking_record.created_by,
                            'updated_at': booking_record.updated_at,
                            'updated_by': booking_record.updated_by,
                            'correction_count': correction_count,
                            'has_unviewed_corrections': has_unviewed_corrections,
                        })
                        sd_groups[sd_key]['allocation_groups'][contract_key]['total_booked'] += float(detail.tonnage_booked)
                        sd_groups[sd_key]['total_booked'] += float(detail.tonnage_booked)

        # Calculate balances and sort allocations
        for sd_data in sd_groups.values():
            if sd_data['sd_tonnage']:
                sd_data['balance'] = sd_data['sd_tonnage'] - sd_data['total_booked']
            else:
                sd_data['balance'] = None
            for ag in sd_data['allocation_groups'].values():
                if ag['allocated_tonnage'] is not None:
                    ag['balance'] = ag['allocated_tonnage'] - ag['total_booked']
                else:
                    ag['balance'] = None
            # Sort allocation groups alphabetically
            sd_data['allocation_groups'] = sorted(
                sd_data['allocation_groups'].values(),
                key=lambda x: x['allocation_label'] or 'ZZZ'
            )

        # Paginate at 12 SDs per page
        sd_groups_list = list(sd_groups.values())
        paginator = Paginator(sd_groups_list, 12)
        page_obj = paginator.get_page(request.GET.get('page'))

        return render(request, 'ebooking/booking_list.html', {
            'sd_groups': page_obj.object_list,
            'page_obj': page_obj,
            'selected_date': None,
            'today': today,
            'q': q,
            'cal_year': cal_year,
            'cal_month': cal_month,
            'cal_month_name': date(cal_year, cal_month, 1).strftime('%B %Y'),
            'cal_weeks': cal_module.monthcalendar(cal_year, cal_month),
            'booking_dates': [d.isoformat() for d in booking_dates],
            'show_mine': False,
            'can_manage': can_manage_bookings(request.user),
            'is_ebooking': can_manage_bookings(request.user),
            'prev_month': prev_month,
            'next_month': next_month,
            'show_all': True,
        })

    # Default behavior (no search): show records for today unless user selects a date.
    # Search mode intentionally shows history across all dates.
    if not q and not selected_date:
        selected_date = today
        date_str = today.isoformat()

    # If searching, ignore date filter entirely (history)
    if q:
        selected_date = None
        date_str = ''

    # Get booking records for assigned SDs only
    qs = BookingRecord.objects.filter(
        sd_number__in=all_assigned_sd_numbers
    ).select_related('sd_record', 'created_by').prefetch_related(
        'lines__details'
    ).order_by('-created_at')

    # Filter by date if selected (date view). Search mode shows full history.
    if selected_date and not q:
        qs = qs.filter(date=selected_date)

    # Search filter
    if q:
        qs = qs.filter(
            Q(sd_number__icontains=q) |
            Q(vessel__icontains=q) |
            Q(agent__icontains=q) |
            Q(lines__contract_number__icontains=q)
        ).distinct()

    # Group bookings by SD
    sd_groups = {}
    for booking_record in qs:
        sd_key = booking_record.sd_number
        if sd_key not in sd_groups:
            sd_record = booking_record.sd_record

            sd_groups[sd_key] = {
                'sd_number': sd_key,
                'vessel': booking_record.vessel or (sd_record.vessel_name if sd_record else ''),
                'agent': booking_record.agent or (sd_record.agent if sd_record else ''),
                'sd_record': sd_record,
                'sd_tonnage': float(sd_record.tonnage) if sd_record else None,
                'total_booked': 0,
                'allocation_groups': {},
                'is_assigned_officer': True,  # Always true in this view
            }

        # Group by contract
        for line in booking_record.lines.all():
            contract_key = line.contract_number or 'no_contract'
            if contract_key not in sd_groups[sd_key]['allocation_groups']:
                # Find allocation for this contract
                allocation = None
                allocated_tonnage = None
                mk_number = None
                allocation_label = None
                if sd_record and line.contract_number:
                    from apps.operations.models import SDAllocation
                    allocation = SDAllocation.objects.filter(
                        sd_record=sd_record,
                        contract_number__iexact=line.contract_number
                    ).first()
                    if allocation:
                        allocated_tonnage = float(allocation.allocated_tonnage)
                        mk_number = allocation.mk_number
                        allocation_label = allocation.allocation_label

                sd_groups[sd_key]['allocation_groups'][contract_key] = {
                    'contract_number': line.contract_number or '—',
                    'mk_number': mk_number,
                    'allocation_label': allocation_label,
                    'allocated_tonnage': allocated_tonnage,
                    'total_booked': 0,
                    'bookings': [],
                }

            # Add booking details
            for detail in line.details.all():
                # Count corrections for this booking detail
                correction_count = detail.corrections.count()
                has_unviewed_corrections = detail.corrections.filter(viewed_at__isnull=True).exists()

                sd_groups[sd_key]['allocation_groups'][contract_key]['bookings'].append({
                    'pk': booking_record.pk,
                    'detail_id': detail.pk,
                    'booking_number': detail.booking_number,
                    'bill_number': detail.bill_number,
                    'tonnage_booked': float(detail.tonnage_booked),
                    'bill_pdf': detail.file,
                    'created_at': booking_record.created_at,
                    'created_by': booking_record.created_by,
                    'updated_at': booking_record.updated_at,
                    'updated_by': booking_record.updated_by,
                    'correction_count': correction_count,
                    'has_unviewed_corrections': has_unviewed_corrections,
                })
                sd_groups[sd_key]['allocation_groups'][contract_key]['total_booked'] += float(detail.tonnage_booked)
                sd_groups[sd_key]['total_booked'] += float(detail.tonnage_booked)

    # Compute balances
    for sd in sd_groups.values():
        if sd['sd_tonnage'] is not None:
            sd['balance'] = sd['sd_tonnage'] - sd['total_booked']
        else:
            sd['balance'] = None
        for ag in sd['allocation_groups'].values():
            if ag['allocated_tonnage'] is not None:
                ag['balance'] = ag['allocated_tonnage'] - ag['total_booked']
            else:
                ag['balance'] = None
        # Sort allocation groups alphabetically by allocation_label (A, B, C, D, E, F)
        sd['allocation_groups'] = sorted(
            sd['allocation_groups'].values(),
            key=lambda x: x['allocation_label'] or 'ZZZ'  # Put None/empty at end
        )

    # Paginate SD groups
    sd_groups_list = list(sd_groups.values())
    paginator = Paginator(sd_groups_list, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'ebooking/assigned_sds_list.html', {
        'sd_groups': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'selected_date': selected_date,
        'today': today,
        'cal_year': cal_year,
        'cal_month': cal_month,
        'cal_month_name': date(cal_year, cal_month, 1).strftime('%B %Y'),
        'cal_weeks': cal_module.monthcalendar(cal_year, cal_month),
        'booking_dates': [d.isoformat() for d in booking_dates],
        'prev_month': prev_month,
        'next_month': next_month,
        'can_manage': can_manage_bookings(request.user),
        'is_ebooking': can_manage_bookings(request.user),
    })
