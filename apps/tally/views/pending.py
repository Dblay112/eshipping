import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone
from django_ratelimit.decorators import ratelimit

from apps.core.calendar_utils import get_calendar_state
from apps.operations.permissions import is_terminal_supervisor

from ..models import TallyInfo


@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def pending_tallies(request):
    """Terminal supervisor sees tallies pending their approval."""
    # Allow terminal supervisors and superusers
    if not (is_terminal_supervisor(request.user) or request.user.is_superuser):
        messages.error(request, 'Access denied.')
        return redirect('my_tallies')

    cal = get_calendar_state(request, today=timezone.localdate())
    date_str = request.GET.get('date', '')
    selected_date = cal['selected_date']
    today = cal['today']

    month_start = cal['month_start']
    month_end = cal['month_end']

    # Supervisor sees tallies for their terminals; manager/superuser sees all pending
    if request.user.is_superuser or getattr(request.user, 'desk', '') == 'MANAGER':
        qs = TallyInfo.objects.filter(status__in=['PENDING_APPROVAL', 'APPROVED', 'REJECTED']).annotate(
            recall_request_count=Count('recall_requests')
        ).prefetch_related('recall_requests__requested_by', 'recall_requests__approved_by')

        # Get all pending tally dates in the current month for calendar dots
        pending_dates = set(
            TallyInfo.objects
            .filter(status__in=['PENDING_APPROVAL', 'APPROVED', 'REJECTED'], loading_date__gte=month_start, loading_date__lte=month_end)
            .values_list('loading_date', flat=True)
        )
    else:
        qs = TallyInfo.objects.filter(
            status__in=['PENDING_APPROVAL', 'APPROVED', 'REJECTED'],
            terminal__supervisors=request.user,
        ).annotate(
            recall_request_count=Count('recall_requests')
        ).prefetch_related('recall_requests__requested_by', 'recall_requests__approved_by')

        # Get pending tally dates for this supervisor's terminals
        pending_dates = set(
            TallyInfo.objects
            .filter(
                status__in=['PENDING_APPROVAL', 'APPROVED', 'REJECTED'],
                terminal__supervisors=request.user,
                loading_date__gte=month_start,
                loading_date__lte=month_end,
            )
            .values_list('loading_date', flat=True)
        )

    # Filter by selected date if provided
    if date_str:
        qs = qs.filter(loading_date=selected_date)

    qs = qs.order_by('-date_created')

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
        })

    paginator = Paginator(grouped_tallies, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Count only PENDING_APPROVAL tallies for the badge
    pending_count = qs.filter(status='PENDING_APPROVAL').count()

    context = {
        'grouped_tallies': page_obj.object_list,
        'page_obj': page_obj,
        'tallies': tallies_list,
        'pending_count': pending_count,
        'pending_dates': [d.isoformat() for d in pending_dates],
        **{k: cal[k] for k in ['selected_date', 'today', 'cal_year', 'cal_month', 'cal_month_name', 'cal_weeks', 'prev_month', 'next_month']},
    }

    return render(request, 'tally_details/pending_tallies.html', context)
