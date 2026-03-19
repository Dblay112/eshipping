import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from django_ratelimit.decorators import ratelimit

from apps.core.calendar_utils import get_calendar_state

from ..models import TallyInfo


@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def my_tallies(request):
    """
    Display all tallies created by the current user with filtering and grouping.

    Features:
    - Calendar-based date selection with month navigation
    - Search by tally number, SD number, MK number, vessel, destination
    - Filter by period (today, week, month, all)
    - Sort by newest, oldest, or SD number
    - Groups tallies by SD number for better organization
    - Shows recall request counts and status
    - Separate pagination for PC (10 SD groups) and mobile (5 SD groups)
    - Statistics: total tallies, this week count, today count

    Permissions: All authenticated users (shows only their own tallies)
    Rate limit: 10 requests per minute per user

    Query Parameters:
        q: Search query (tally number, SD, MK, vessel, destination, date)
        period: Filter by time period (today, week, month, all)
        sort: Sort order (newest, oldest, sd)
        date: Specific date to filter by (YYYY-MM-DD)
        page: Page number for pagination

    Returns:
        Renders my_tallies.html with grouped tallies and calendar
    """
    q = (request.GET.get('q') or '').strip()
    period = (request.GET.get('period') or 'all').strip().lower()
    sort = (request.GET.get('sort') or 'newest').strip().lower()

    qs = TallyInfo.objects.filter(created_by=request.user).annotate(
        recall_request_count=Count('recall_requests')
    ).prefetch_related('recall_requests__requested_by', 'recall_requests__approved_by')

    cal = get_calendar_state(request, today=timezone.localdate())

    # Get all tally dates in the current month for calendar dots
    tally_dates = set(
        TallyInfo.objects
        .filter(created_by=request.user, loading_date__gte=cal['month_start'], loading_date__lte=cal['month_end'])
        .values_list('loading_date', flat=True)
    )

    date_str = request.GET.get('date', '')
    selected_date = cal['selected_date']
    today = cal['today']
    cal_year = cal['cal_year']
    cal_month = cal['cal_month']
    prev_month = cal['prev_month']
    next_month = cal['next_month']
    cal_month_name = cal['cal_month_name']
    cal_weeks = cal['cal_weeks']

    if q:
        q_filters = (
            Q(tally_number__icontains=q)
            | Q(tally_type__icontains=q)
            | Q(sd_number__icontains=q)
            | Q(mk_number__icontains=q)
            | Q(vessel__icontains=q)
            | Q(destination__icontains=q)
        )
        try:
            parsed_date = datetime.date.fromisoformat(q)
            q_filters = q_filters | Q(loading_date=parsed_date)
        except ValueError:
            pass

        qs = qs.filter(q_filters)

    # Filter by selected date if provided
    if date_str:
        qs = qs.filter(loading_date=selected_date)
    elif period == 'today':
        qs = qs.filter(loading_date=today)
    elif period == 'week':
        start = today - datetime.timedelta(days=6)
        qs = qs.filter(loading_date__range=(start, today))
    elif period == 'month':
        start = today.replace(day=1)
        qs = qs.filter(loading_date__gte=start)

    if sort == 'oldest':
        qs = qs.order_by('date_created')
    elif sort == 'sd':
        qs = qs.order_by('sd_number', 'mk_number', '-date_created')
    else:
        qs = qs.order_by('-date_created')

    total_tallies = TallyInfo.objects.filter(created_by=request.user).count()

    week_start = today - datetime.timedelta(days=6)
    this_week_count = TallyInfo.objects.filter(
        created_by=request.user,
        loading_date__range=(week_start, today)
    ).count()
    today_count = TallyInfo.objects.filter(
        created_by=request.user,
        loading_date=today
    ).count()

    # Group ALL tallies by SD number first
    from itertools import groupby
    all_tallies = list(qs)  # Get all tallies matching filters
    tallies_by_sd_all = {}
    for sd_num, group in groupby(
        sorted(all_tallies, key=lambda t: t.sd_number or ''),
        key=lambda t: t.sd_number or 'NO SD',
    ):
        tallies_by_sd_all[sd_num] = list(group)

    # Paginate SD groups - 10 per page for PC, 5 per page for mobile
    sd_groups = list(tallies_by_sd_all.items())
    page_number = request.GET.get('page') or 1

    # PC pagination (10 SD groups per page)
    paginator_pc = Paginator(sd_groups, 10)
    page_obj_pc = paginator_pc.get_page(page_number)

    # Mobile pagination (5 SD groups per page)
    paginator_mobile = Paginator(sd_groups, 5)
    page_obj_mobile = paginator_mobile.get_page(page_number)

    # Get SD groups for current page (PC)
    current_sd_groups_pc = dict(page_obj_pc.object_list)

    # Get SD groups for current page (Mobile)
    current_sd_groups_mobile = dict(page_obj_mobile.object_list)

    # Flatten SD groups back to individual tallies for PC table
    tallies = []
    for sd_num, sd_tallies in current_sd_groups_pc.items():
        tallies.extend(sd_tallies)

    context = {
        'tallies': tallies,  # Flattened list for PC table
        'tallies_by_sd': current_sd_groups_pc,  # Grouped dict for PC table
        'tallies_by_sd_mobile': current_sd_groups_mobile,  # Grouped dict for mobile cards
        'page_obj': page_obj_pc,  # PC pagination
        'page_obj_mobile': page_obj_mobile,  # Mobile pagination
        'showing': len(tallies),
        'total_tallies': total_tallies,
        'this_week_count': this_week_count,
        'today_count': today_count,
        'q': q,
        'period': period,
        'sort': sort,
        'selected_date': selected_date,
        'today': today,
        'cal_year': cal_year,
        'cal_month': cal_month,
        'cal_month_name': cal_month_name,
        'cal_weeks': cal_weeks,
        'tally_dates': [d.isoformat() for d in tally_dates],
        'prev_month': prev_month,
        'next_month': next_month,
    }

    return render(request, 'tally_details/my_tallies.html', context)
