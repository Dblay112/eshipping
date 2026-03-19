from apps.operations.models import SDRecord


def sd_numbers(request):
    """
    Context processor to make all SD numbers available globally in templates.

    Provides autocomplete functionality for SD number input fields across
    all forms (tallies, bookings, declarations, evacuations).

    Features:
    - Loads all SD numbers from database
    - Orders alphabetically for consistent display
    - Available in all templates via context

    Returns:
        dict: {'all_sd_numbers': QuerySet of SD numbers}

    Usage:
        In templates:
        ```html
        <datalist id="sd-numbers">
            {% for sd in all_sd_numbers %}
                <option value="{{ sd }}">
            {% endfor %}
        </datalist>
        ```

    Performance Note:
        This runs on every request. Consider caching if SD count grows large.
    """
    return {
        'all_sd_numbers': SDRecord.objects.values_list('sd_number', flat=True).order_by('sd_number')
    }


def pending_recall_requests_count(request):
    """
    Context processor to show pending recall request count in navbar badge.

    Displays notification badge for operations staff when tallies need recall approval.
    Only visible to operations desk staff who can approve recall requests.

    Recall Request Workflow:
    1. Assigned officer requests recall of approved tally
    2. Operations desk sees notification badge with count
    3. Operations desk approves/rejects recall request
    4. If approved, tally status changes to DRAFT for editing

    Features:
    - Shows count only to operations desk staff
    - Returns 0 for unauthenticated users
    - Returns 0 for non-operations staff
    - Counts only PENDING recall requests

    Args:
        request: Django HttpRequest object

    Returns:
        dict: {'pending_recall_requests_count': int}

    Usage:
        In navbar template:
        ```html
        {% if pending_recall_requests_count > 0 %}
            <span class="badge">{{ pending_recall_requests_count }}</span>
        {% endif %}
        ```

    Performance Note:
        Runs on every request for operations staff. Consider caching if needed.
    """
    if not request.user.is_authenticated:
        return {'pending_recall_requests_count': 0}

    # Only show count to operations staff
    from apps.operations.permissions import can_manage_sd_records
    if not can_manage_sd_records(request.user):
        return {'pending_recall_requests_count': 0}

    from apps.tally.models import RecallRequest
    count = RecallRequest.objects.filter(status='PENDING').count()

    return {'pending_recall_requests_count': count}
