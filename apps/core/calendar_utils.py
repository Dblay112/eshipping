import calendar
from datetime import date, timedelta


def get_calendar_state(request, *, today=None):
    """
    Parse calendar navigation parameters consistently across all views.

    Provides standardized calendar state for views that use calendar-based
    date selection (schedules, evacuations, daily port reports, etc.).

    Features:
    - Parses date, cal_year, cal_month from query parameters
    - Handles month rollover (< 1 or > 12)
    - Calculates month boundaries and navigation links
    - Generates calendar weeks for template rendering
    - Defaults to today if no date selected

    Args:
        request: Django HttpRequest object with GET parameters
        today: Optional date override for testing (defaults to date.today())

    Returns:
        dict: Calendar state with keys:
            - today: Current date (or override)
            - selected_date: User-selected date or today
            - cal_year: Calendar year being displayed
            - cal_month: Calendar month being displayed (1-12)
            - cal_month_name: Formatted month name (e.g., "March 2026")
            - cal_weeks: List of week lists for calendar grid
            - month_start: First day of displayed month
            - month_end: Last day of displayed month
            - prev_month: First day of previous month
            - next_month: First day of next month

    Query Parameters:
        - date: ISO date string (YYYY-MM-DD) for selected date
        - cal_year: Integer year for calendar display
        - cal_month: Integer month (1-12) for calendar display

    Example:
        >>> state = get_calendar_state(request)
        >>> state['cal_month_name']
        'March 2026'
        >>> state['cal_weeks']
        [[0, 0, 0, 0, 0, 1, 2], [3, 4, 5, 6, 7, 8, 9], ...]

    Usage:
        In views:
        ```python
        from apps.core.calendar_utils import get_calendar_state

        def my_view(request):
            cal_state = get_calendar_state(request)
            # ... filter records by cal_state['selected_date']
            return render(request, 'template.html', cal_state)
        ```
    """
    if today is None:
        today = date.today()

    date_str = request.GET.get('date', '')
    try:
        selected_date = date.fromisoformat(date_str) if date_str else today
    except ValueError:
        selected_date = today

    cal_year = int(request.GET.get('cal_year', selected_date.year))
    cal_month = int(request.GET.get('cal_month', selected_date.month))
    if cal_month < 1:
        cal_month, cal_year = 12, cal_year - 1
    elif cal_month > 12:
        cal_month, cal_year = 1, cal_year + 1

    month_start = date(cal_year, cal_month, 1)
    month_end = date(cal_year, cal_month, calendar.monthrange(cal_year, cal_month)[1])

    prev_month = (date(cal_year, cal_month, 1) - timedelta(days=1)).replace(day=1)
    next_month = (date(cal_year, cal_month, 28) + timedelta(days=7)).replace(day=1)

    return {
        'today': today,
        'selected_date': selected_date,
        'cal_year': cal_year,
        'cal_month': cal_month,
        'cal_month_name': date(cal_year, cal_month, 1).strftime('%B %Y'),
        'cal_weeks': calendar.monthcalendar(cal_year, cal_month),
        'month_start': month_start,
        'month_end': month_end,
        'prev_month': prev_month,
        'next_month': next_month,
    }
