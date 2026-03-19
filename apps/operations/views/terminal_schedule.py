from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django_ratelimit.decorators import ratelimit

from ..forms import TerminalScheduleForm
from ..permissions import can_manage_schedules


# ══════════════════════════════════════════════════════
#  TERMINAL SCHEDULE VIEWS
# ══════════════════════════════════════════════════════

@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def terminal_schedule_list(request):
    """
    Display all terminals with their assigned supervisors.

    Features:
    - Lists all terminals (warehouses) in Tema
    - Shows supervisor assignments for each terminal
    - Supports multiple supervisors per terminal
    - Ordered alphabetically by terminal name

    Permissions: All authenticated users can view
    Rate limit: 10 requests per minute per user

    Returns:
        Renders terminal_schedule_list.html with terminals
    """
    from apps.tally.models import Terminal
    terminals = Terminal.objects.prefetch_related('supervisors').order_by('name')
    return render(request, 'schedule/terminal_schedule_list.html', {
        'terminals': terminals,
        'can_manage': can_manage_schedules(request.user),
    })


@login_required(login_url='login')
def terminal_schedule_create(request):
    """
    Create a new terminal with supervisor assignments (managers only).

    Features:
    - Create terminal (warehouse) with name
    - Assign one or multiple supervisors via checkboxes
    - Supervisors route tallies for approval
    - Audit trail with creator tracking

    Security:
    - Only managers can create terminals
    - Multi-select supervisor assignment

    Permissions: MANAGER desk or superuser only

    Returns:
        GET: Renders terminal form
        POST: Creates terminal and redirects to list
    """
    if not can_manage_schedules(request.user):
        messages.error(request, "You don't have permission to manage terminal schedules.")
        return redirect('terminal_schedule_list')

    if request.method == 'POST':
        form = TerminalScheduleForm(request.POST)
        if form.is_valid():
            terminal = form.save()
            messages.success(
                request,
                f"✓ Terminal '{terminal.name}' created by {request.user.first_name} {request.user.last_name}"
            )
            return redirect('terminal_schedule_list')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = TerminalScheduleForm()

    return render(request, 'schedule/terminal_schedule_form.html', {
        'form': form, 'action': 'Create',
        'can_manage': can_manage_schedules(request.user),
    })


@login_required(login_url='login')
def terminal_schedule_edit(request, pk):
    """
    Edit existing terminal and supervisor assignments (managers only).

    Features:
    - Update terminal name
    - Add/remove supervisor assignments
    - Preserves existing tally routing
    - Audit trail with updater tracking

    Security:
    - Only managers can edit terminals
    - No ownership verification (any manager can edit)

    Permissions: MANAGER desk or superuser only

    Args:
        pk: Primary key of Terminal to edit

    Returns:
        GET: Renders edit form with existing data
        POST: Updates terminal and redirects to list
    """
    from apps.tally.models import Terminal
    if not can_manage_schedules(request.user):
        messages.error(request, "You don't have permission to manage terminal schedules.")
        return redirect('terminal_schedule_list')

    terminal = get_object_or_404(Terminal, pk=pk)
    if request.method == 'POST':
        form = TerminalScheduleForm(request.POST, instance=terminal)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"✓ Terminal '{terminal.name}' updated by {request.user.first_name} {request.user.last_name}"
            )
            return redirect('terminal_schedule_list')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = TerminalScheduleForm(instance=terminal)

    return render(request, 'schedule/terminal_schedule_form.html', {
        'form': form, 'terminal': terminal, 'action': 'Edit',
        'can_manage': can_manage_schedules(request.user),
    })


@login_required(login_url='login')
def terminal_schedule_delete(request, pk):
    """
    Delete a terminal (managers only).

    Features:
    - Confirmation page before deletion
    - Cascades deletion to supervisor assignments
    - Orphans related tallies (sets terminal to NULL)

    Security:
    - Only managers can delete terminals
    - No ownership verification (any manager can delete)

    Permissions: MANAGER desk or superuser only

    Args:
        pk: Primary key of Terminal to delete

    Returns:
        GET: Renders confirmation page
        POST: Deletes terminal and redirects to list
    """
    from apps.tally.models import Terminal
    if not can_manage_schedules(request.user):
        messages.error(request, "You don't have permission to delete terminals.")
        return redirect('terminal_schedule_list')

    terminal = get_object_or_404(Terminal, pk=pk)

    if request.method == 'POST':
        terminal_name = terminal.name
        terminal.delete()
        messages.success(request, f"Terminal '{terminal_name}' has been deleted.")
        return redirect('terminal_schedule_list')

    return render(request, 'schedule/terminal_schedule_confirm_delete.html', {
        'terminal': terminal,
        'can_manage': can_manage_schedules(request.user),
    })
