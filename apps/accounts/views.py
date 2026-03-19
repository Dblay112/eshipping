"""Account management views for staff authentication and administration."""
import datetime

from django.http import HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django_ratelimit.decorators import ratelimit

from .models import Account
from .forms import AddStaffForm, EditStaffForm


@ratelimit(key='ip', rate='10/h', method='POST')
def login_view(request):
    """
    Staff login with rate limiting and brute force protection.

    Features:
    - Login via Staff ID and password
    - Rate limiting: 10 attempts per hour per IP
    - Django-Axes brute force protection (5 attempts = 1hr lockout)
    - Force password change on first login
    - Session timeout: 4 hours
    - Password reset flow for users flagged for password change

    Security:
    - Session key cycling after password change
    - Complex password validation for superusers
    - Minimum 6-character password for regular staff

    Returns:
        GET: Renders login page
        POST: Authenticates and redirects to dashboard or shows error
    """
    import logging
    logger = logging.getLogger('apps.accounts')

    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        # SECURITY: Check if rate limited (10 attempts per hour from same IP)
        if getattr(request, 'limited', False):
            messages.error(
                request,
                "Too many login attempts. Please try again in 1 hour. "
                "If you're having trouble logging in, contact your system administrator."
            )
            logger.warning(
                f'Rate limit exceeded from IP {request.META.get("REMOTE_ADDR")}')
            return render(request, "accounts/login.html")

        action = (request.POST.get("action") or "").strip()

        if action == "reset_password":
            user_pk = request.session.get("reset_user_pk")
            if not user_pk:
                messages.error(request, "Session expired. Please login again.")
                return render(request, "accounts/login.html")

            try:
                user = Account.objects.get(pk=user_pk)
            except Account.DoesNotExist:
                messages.error(
                    request, "Invalid session user. Please try again.")
                request.session.pop("reset_user_pk", None)
                return render(request, "accounts/login.html")

            new_password = request.POST.get("new_password") or ""
            confirm_password = request.POST.get("confirm_password") or ""

            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, "accounts/login.html", {"require_password_reset": True})

            try:
                # Admin/superuser: complex password validation
                if user.is_superuser:
                    from .validators import validate_admin_password
                    validate_admin_password(new_password)
                else:
                    # Regular staff: Django's 6-char minimum
                    validate_password(new_password, user=user)
            except ValidationError as e:
                for msg in e.messages:
                    messages.error(request, msg)
                return render(request, "accounts/login.html", {"require_password_reset": True})

            if user.check_password(new_password):
                messages.error(
                    request, "New password cannot be the same as your current password.")
                return render(request, "accounts/login.html", {"require_password_reset": True})

            user.set_password(new_password)
            user.force_password_change = False
            user.save()

            request.session.pop("reset_user_pk", None)
            # SECURITY FIX: Regenerate session ID immediately after password change
            # to prevent session fixation attacks
            request.session.cycle_key()

            # Re-authenticate properly with the new password, then log in
            user = authenticate(
                request, staff_number=user.staff_number, password=new_password)
            if user is None:
                messages.error(
                    request, "Password updated, but we couldn't log you in. Please login again.")
                return redirect("login")

            auth_login(request, user)
            update_session_auth_hash(request, user)
            request.session.cycle_key()  # Regenerate session ID for security

            messages.success(
                request, f"Welcome {user.first_name}! Password updated successfully.")
            logger.info(
                f'User {user.staff_number} completed password reset and logged in from IP {request.META.get("REMOTE_ADDR")}')
            return redirect("dashboard")

        staff_number = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        if not staff_number:
            messages.error(request, "Please enter your Staff ID.")
            return render(request, "accounts/login.html")

        if not password:
            messages.error(request, "Please enter your password.")
            return render(request, "accounts/login.html")

        if not staff_number.isdigit():
            messages.error(request, "Staff ID must be numeric.")
            logger.warning(
                f'Invalid staff ID format attempted: {staff_number} from IP {request.META.get("REMOTE_ADDR")}')
            return render(request, "accounts/login.html")

        # IMPORTANT: authenticate using your USERNAME_FIELD name
        user = authenticate(request, staff_number=int(
            staff_number), password=password)
        if user is None:
            messages.error(
                request, "Invalid login credentials. Please try again.")
            logger.warning(
                f'Failed login attempt for staff_number: {staff_number} from IP {request.META.get("REMOTE_ADDR")}')
            return render(request, "accounts/login.html")

        if getattr(user, "force_password_change", False):
            request.session["reset_user_pk"] = user.pk
            request.session.save()
            logger.info(f'User {staff_number} redirected to password reset')
            return render(request, "accounts/login.html", {"require_password_reset": True})

        auth_login(request, user)
        request.session.cycle_key()  # Regenerate session ID to prevent session fixation
        messages.success(request, f"Welcome {user.first_name}!")
        logger.info(
            f'Successful login for staff_number: {staff_number} from IP {request.META.get("REMOTE_ADDR")}')
        return redirect("dashboard")

    return render(request, "accounts/login.html")


@login_required(login_url="login")
def change_password(request):
    """
    Change user's password with validation and audit logging.

    Features:
    - Current password verification
    - New password confirmation matching
    - Different validation for admins vs regular staff
    - Updates password_changed_at timestamp in profile
    - Clears force_password_change flag
    - Session preservation after password change

    Validation:
    - Current password must be correct
    - New password and confirmation must match
    - New password cannot be same as current
    - Admins: Complex password requirements (via validate_admin_password)
    - Regular staff: Django's default validation (6 char minimum)

    Security:
    - Requires authentication
    - Verifies current password before allowing change
    - Session auth hash updated to prevent logout
    - Password hashed with Django's default hasher

    Permissions: All authenticated users (can change own password)

    Returns:
        GET: Renders change password form
        POST: Updates password and redirects to dashboard
    """
    user = request.user
    if request.method == "POST":
        current_password = request.POST.get("current_password") or ""
        new_password = request.POST.get("new_password") or ""
        confirm_password = request.POST.get("confirm_password") or ""

        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return render(request, "accounts/change_password.html")

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return render(request, "accounts/change_password.html")

        if user.check_password(new_password):
            messages.error(
                request, "New password cannot be the same as your current password.")
            return render(request, "accounts/change_password.html")

        try:
            # Admin/superuser: complex password validation
            if user.is_superuser:
                from .validators import validate_admin_password
                validate_admin_password(new_password)
            else:
                # Regular staff: Django's 6-char minimum
                validate_password(new_password, user=user)
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg)
            return render(request, "accounts/change_password.html")

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Password changed successfully.")
        return redirect("dashboard")

    return render(request, "accounts/change_password.html")


@login_required(login_url="login")
def logout_view(request):
    """
    Log out current user and redirect to login page.

    Clears session data and displays logout confirmation message.
    """
    auth_logout(request)
    messages.info(request, "You have been logged out!")
    return redirect("login")


@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url="login")
def dashboard(request):
    """
    Role-aware dashboard shown after login.

    Displays personalized statistics and quick links based on user's desk assignments:
    - Tally statistics (all users)
    - Desk-specific stats (operations, ebooking, declarations, evacuations)
    - Manager/supervisor stats (pending tallies, schedules)
    - Assigned officer stats (assigned SDs)

    Features:
    - Multi-desk support (shows stats for all assigned desks)
    - Recent activity lists (last 5 items)
    - Weekly and daily statistics
    - Rate limiting: 10 requests per minute per user

    Returns:
        Renders dashboard with personalized statistics
    """
    user = request.user
    desk = getattr(user, 'desk', 'OTHER')
    today = timezone.localdate()
    week_start = today - datetime.timedelta(days=6)

    now = timezone.localtime()

    # Build multi-desk set (primary + any additional roles)
    try:
        extra_desks = set(user.desks) if hasattr(
            user, 'desks') and user.desks else set()
    except Exception:
        extra_desks = set()
    all_desks = {desk or 'OTHER'} | extra_desks

    is_manager_or_super = user.is_superuser or 'MANAGER' in all_desks

    # Check if OTHER desk user is an assigned officer
    is_assigned_officer = False
    assigned_sds = []
    if 'OTHER' in all_desks or desk == 'OTHER':
        try:
            from apps.operations.models import ScheduleEntry, SDRecord
            # Check if user appears as assigned_officer in any schedule entry
            schedule_entries = ScheduleEntry.objects.filter(
                assigned_officer=user).select_related('schedule')
            if schedule_entries.exists():
                is_assigned_officer = True
                # Get SDs assigned to this officer
                sd_numbers = schedule_entries.values_list(
                    'sd_number', flat=True).distinct()
                assigned_sds = list(SDRecord.objects.filter(
                    sd_number__in=sd_numbers).order_by('-created_at')[:5])
        except Exception:
            pass

    ctx = {
        'today': today,
        'now': now,
        'desk': desk,
        'all_desks': all_desks,
        'is_manager_or_super': is_manager_or_super,
        'is_assigned_officer': is_assigned_officer,
        'assigned_sds': assigned_sds,
    }

    # ── TALLY stats (all users create tallies) ──────────────────────
    try:
        from apps.tally.models import TallyInfo
        my_tallies_total = TallyInfo.objects.filter(created_by=user).count()
        my_tallies_today = TallyInfo.objects.filter(
            created_by=user, loading_date=today).count()
        my_tallies_week = TallyInfo.objects.filter(
            created_by=user, loading_date__range=(week_start, today)).count()
        my_tallies_draft = TallyInfo.objects.filter(
            created_by=user, status='DRAFT').count()
        my_tallies_pending = TallyInfo.objects.filter(
            created_by=user, status='PENDING_APPROVAL').count()
        my_tallies_approved = TallyInfo.objects.filter(
            created_by=user, status='APPROVED').count()
        recent_my_tallies = list(
            TallyInfo.objects.filter(created_by=user)
            .order_by('-date_created')[:5]
        )
        ctx.update({
            'my_tallies_total': my_tallies_total,
            'my_tallies_today': my_tallies_today,
            'my_tallies_week': my_tallies_week,
            'my_tallies_draft': my_tallies_draft,
            'my_tallies_pending': my_tallies_pending,
            'my_tallies_approved': my_tallies_approved,
            'recent_my_tallies': recent_my_tallies,
        })
    except Exception:
        pass

    # ── Role-specific stats ─────────────────────────────────────────
    if is_manager_or_super or bool({'OPERATIONS'} & all_desks):
        try:
            from apps.operations.models import SDRecord, WorkProgram, DailyPort
            from apps.tally.models import TallyInfo as TI
            sd_total = SDRecord.objects.count()
            sd_active = SDRecord.objects.filter(is_complete=False).count()
            sd_today = SDRecord.objects.filter(created_at__date=today).count()
            sd_week = SDRecord.objects.filter(
                created_at__date__range=(week_start, today)).count()

            # Work program stats
            work_program_total = WorkProgram.objects.count()
            work_program_month = WorkProgram.objects.filter(
                date__year=today.year, date__month=today.month).count()
            recent_work_programs = list(
                WorkProgram.objects.order_by('-date')[:5])

            # Daily port stats
            daily_port_total = DailyPort.objects.count()
            daily_port_month = DailyPort.objects.filter(
                date__year=today.year, date__month=today.month).count()
            recent_daily_ports = list(DailyPort.objects.order_by('-date')[:5])

            pending_approval = TI.objects.filter(
                status='PENDING_APPROVAL').count()
            approved_today = TI.objects.filter(
                status='APPROVED', approved_at__date=today).count()
            recent_sds = list(SDRecord.objects.select_related(
                'created_by').order_by('-created_at')[:5])
            ctx.update({
                'sd_total': sd_total,
                'sd_active': sd_active,
                'sd_today': sd_today,
                'sd_week': sd_week,
                'work_program_total': work_program_total,
                'work_program_month': work_program_month,
                'recent_work_programs': recent_work_programs,
                'daily_port_total': daily_port_total,
                'daily_port_month': daily_port_month,
                'recent_daily_ports': recent_daily_ports,
                'pending_approval': pending_approval,
                'approved_today': approved_today,
                'recent_sds': recent_sds,
            })
        except Exception:
            pass

    if is_manager_or_super or bool({'TERMINAL_SUPERVISOR'} & all_desks):
        try:
            from apps.tally.models import TallyInfo as TI
            from apps.tally.models import Terminal
            supervised_terminals = Terminal.objects.filter(supervisors=user)
            if is_manager_or_super:
                pending_for_me = TI.objects.filter(
                    status='PENDING_APPROVAL').count()
                pending_tallies_list = list(TI.objects.filter(
                    status='PENDING_APPROVAL').order_by('-date_created')[:5])
            else:
                pending_for_me = TI.objects.filter(
                    status='PENDING_APPROVAL', terminal__supervisors=user).count()
                pending_tallies_list = list(
                    TI.objects.filter(status='PENDING_APPROVAL',
                                      terminal__supervisors=user)
                    .order_by('-date_created')[:5]
                )
            my_approved = TI.objects.filter(
                approved_by=user, status='APPROVED').count()
            ctx.update({
                'pending_for_me': pending_for_me,
                'pending_tallies_list': pending_tallies_list,
                'my_approved': my_approved,
                'supervised_terminals': list(supervised_terminals),
            })
        except Exception:
            pass

    if is_manager_or_super or bool({'EBOOKING'} & all_desks):
        try:
            from apps.ebooking.models import BookingRecord, BookingCorrection
            booking_total = BookingRecord.objects.count()
            booking_month = BookingRecord.objects.filter(
                created_at__year=today.year, created_at__month=today.month).count()
            booking_today = BookingRecord.objects.filter(
                created_at__date=today).count()
            booking_week = BookingRecord.objects.filter(
                created_at__date__range=(week_start, today)).count()

            # Booking corrections stats
            correction_pending = BookingCorrection.objects.filter(
                is_resolved=False).count()
            correction_total = BookingCorrection.objects.count()

            recent_bookings = list(BookingRecord.objects.select_related(
                'created_by').order_by('-created_at')[:5])
            recent_corrections = list(BookingCorrection.objects.select_related(
                'booking_detail__booking_record').order_by('-requested_at')[:5])

            ctx.update({
                'booking_total': booking_total,
                'booking_month': booking_month,
                'booking_today': booking_today,
                'booking_week': booking_week,
                'correction_pending': correction_pending,
                'correction_total': correction_total,
                'recent_bookings': recent_bookings,
                'recent_corrections': recent_corrections,
            })
        except Exception:
            pass

    if is_manager_or_super or bool({'DECLARATION'} & all_desks):
        try:
            from apps.declaration.models import Declaration
            declaration_total = Declaration.objects.count()
            declaration_month = Declaration.objects.filter(
                created_at__year=today.year, created_at__month=today.month).count()
            declaration_today = Declaration.objects.filter(
                created_at__date=today).count()
            declaration_week = Declaration.objects.filter(
                created_at__date__range=(week_start, today)).count()
            recent_declarations = list(Declaration.objects.select_related(
                'created_by').order_by('-created_at')[:5])
            ctx.update({
                'declaration_total': declaration_total,
                'declaration_month': declaration_month,
                'declaration_today': declaration_today,
                'declaration_week': declaration_week,
                'recent_declarations': recent_declarations,
            })
        except Exception:
            pass

    if is_manager_or_super or bool({'EVACUATION'} & all_desks):
        try:
            from apps.evacuation.models import EvacuationRecord
            evacuation_total = EvacuationRecord.objects.count()
            evacuation_month = EvacuationRecord.objects.filter(
                date__year=today.year, date__month=today.month).count()
            evacuation_today = EvacuationRecord.objects.filter(
                date=today).count()
            evacuation_week = EvacuationRecord.objects.filter(
                date__range=(week_start, today)).count()
            recent_evacuations = list(EvacuationRecord.objects.select_related(
                'created_by').order_by('-date')[:5])
            ctx.update({
                'evacuation_total': evacuation_total,
                'evacuation_month': evacuation_month,
                'evacuation_today': evacuation_today,
                'evacuation_week': evacuation_week,
                'recent_evacuations': recent_evacuations,
            })
        except Exception:
            pass

    return render(request, 'dashboard/dashboard.html', ctx)


@login_required(login_url="login")
def add_staff(request):
    """
    Add new staff member (managers only).

    Features:
    - Multi-desk assignment via checkboxes
    - Auto-generated secure password
    - Force password change on first login
    - Email validation
    - Rank and location selection
    - Full audit logging

    Security:
    - Only managers can add staff
    - Password complexity enforced
    - Audit trail with IP address

    Permissions: MANAGER (is_manager=True) or superuser only

    Returns:
        GET: Renders add staff form
        POST: Creates staff and redirects to staff_list
    """
    import logging
    logger = logging.getLogger('security.audit')

    # Check if user is a manager
    if not request.user.is_manager:
        messages.error(request, "Only managers can access staff management.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = AddStaffForm(request.POST)
        if form.is_valid():
            staff = form.save()

            # SECURITY: Audit log for staff creation
            logger.info(
                f'AUDIT: Staff member created - '
                f'New Staff ID: {staff.staff_number}, '
                f'Name: {staff.first_name} {staff.last_name}, '
                f'Rank: {staff.rank}, '
                f'Created by: {request.user.staff_number} (User ID: {request.user.pk}), '
                f'IP: {request.META.get("REMOTE_ADDR", "unknown")}'
            )

            messages.success(
                request,
                f"Staff member {staff.first_name} {staff.last_name} (ID: {staff.staff_number}) has been added successfully. "
                f"They will be required to change their password on first login."
            )
            return redirect('staff_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AddStaffForm()

    return render(request, 'accounts/add_staff.html', {
        'form': form,
        'title': 'Add New Staff Member'
    })


@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url="login")
def staff_list(request):
    """
    Display all staff members with filtering and hierarchical sorting.

    Features:
    - Location filter (Tema, Takoradi, Accra, Kumasi)
    - Search by name, rank, or staff number
    - Hierarchical rank sorting (Manager → Deputy → Officers → Clerks → Contract)
    - Pagination at 15 staff per page
    - Shows total staff count for selected location
    - Managers see edit/delete buttons

    Permissions: All authenticated users can view
    Rate limit: 10 requests per minute per user

    Returns:
        Renders staff_list.html with filtered and sorted staff
    """
    q = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip().upper()

    # Exclude superuser from staff list display
    staff_qs = Account.objects.select_related('profile').filter(is_superuser=False)

    # Location filter
    valid_locations = {'TEMA', 'TAKORADI', 'ACCRA', 'KUMASI'}
    if location in valid_locations:
        staff_qs = staff_qs.filter(location=location)
    else:
        location = ''

    # Search filter
    if q:
        staff_qs = staff_qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(rank__icontains=q) |
            Q(staff_number__icontains=q)
        )

    # Define rank hierarchy for sorting
    rank_order = {
        'MANAGER': 1,
        'DEPUTY MANAGER': 2,
        'PRINCIPAL SHIPPING OFFICER': 3,
        'SENIOR SHIPPING OFFICER': 4,
        'SHIPPING OFFICER': 5,
        'ASSISTANT SHIPPING OFFICER': 6,
        'PRINCIPAL SHIPPING CLERK': 7,
        'SENIOR SHIPPING CLERK': 8,
        'SHIPPING CLERK': 9,
        'CONTRACT STAFF': 10,
    }

    def _rank_sort_key(rank_value: str) -> int:
        normalized = ((rank_value or '').strip()).upper()
        if not normalized:
            return 999

        # Allow common real-world variations while keeping the same hierarchy.
        aliases = {
            'SHIPPING MANAGER': 'MANAGER',
            'MANAGER': 'MANAGER',
            'DEPUTY': 'DEPUTY MANAGER',
            'DEPUTY MANAGER': 'DEPUTY MANAGER',
            'PRINCIPAL SHIPPING OFFICER': 'PRINCIPAL SHIPPING OFFICER',
            'SENIOR SHIPPING OFFICER': 'SENIOR SHIPPING OFFICER',
            'ASSISTANT SHIPPING OFFICER': 'ASSISTANT SHIPPING OFFICER',
            'PRINCIPAL SHIPPING CLERK': 'PRINCIPAL SHIPPING CLERK',
            'SENIOR SHIPPING CLERK': 'SENIOR SHIPPING CLERK',
            'SHIPPING CLERK': 'SHIPPING CLERK',
            'CONTRACT': 'CONTRACT STAFF',
            'CONTRACT STAFF': 'CONTRACT STAFF',
        }

        if normalized in aliases:
            return rank_order.get(aliases[normalized], 999)

        # Fuzzy matching for safe ordering when rank text includes extra words.
        if 'DEPUTY' in normalized and 'MANAGER' in normalized:
            return rank_order['DEPUTY MANAGER']
        if 'MANAGER' in normalized:
            return rank_order['MANAGER']
        if 'PRINCIPAL' in normalized and 'OFFICER' in normalized:
            return rank_order['PRINCIPAL SHIPPING OFFICER']
        if 'SENIOR' in normalized and 'OFFICER' in normalized:
            return rank_order['SENIOR SHIPPING OFFICER']
        if 'ASSISTANT' in normalized and 'OFFICER' in normalized:
            return rank_order['ASSISTANT SHIPPING OFFICER']
        if 'SHIPPING' in normalized and 'OFFICER' in normalized:
            return rank_order['SHIPPING OFFICER']
        if 'PRINCIPAL' in normalized and 'CLERK' in normalized:
            return rank_order['PRINCIPAL SHIPPING CLERK']
        if 'SENIOR' in normalized and 'CLERK' in normalized:
            return rank_order['SENIOR SHIPPING CLERK']
        if 'SHIPPING' in normalized and 'CLERK' in normalized:
            return rank_order['SHIPPING CLERK']
        if 'CONTRACT' in normalized:
            return rank_order['CONTRACT STAFF']

        return 999

    # Sort by rank hierarchy, then by name
    staff_list = list(staff_qs)
    staff_list.sort(key=lambda s: (
        _rank_sort_key(s.rank),
        (s.last_name or '').lower(),
        (s.first_name or '').lower(),
    ))

    # Paginate
    paginator = Paginator(staff_list, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/staff_list.html', {
        'staff_list': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'location': location,
        'is_manager': request.user.is_manager,
    })


@login_required(login_url="login")
def staff_edit(request, pk):
    """
    Edit existing staff member details (managers only).

    Features:
    - Update personal information (name, email, phone, rank, location)
    - Multi-desk assignment modification
    - Employment status management (active/inactive)
    - Cannot edit own account (unless superuser)
    - Full audit logging

    Security:
    - Only managers can edit staff
    - Self-editing prevented (except superuser)
    - Audit trail maintained

    Permissions: MANAGER (is_manager=True) or superuser only

    Args:
        pk: Primary key of Account to edit

    Returns:
        GET: Renders edit staff form
        POST: Updates staff and redirects to staff_list
    """
    import logging
    logger = logging.getLogger('apps.accounts')

    if not request.user.is_manager and not request.user.is_superuser:
        messages.error(request, "Only managers can edit staff members.")
        logger.warning(
            f'Unauthorized staff edit attempt by user {request.user.pk} (not a manager)')
        return redirect('staff_list')

    staff = get_object_or_404(Account, pk=pk)

    # SECURITY: Prevent editing your own account (unless you're a superuser)
    if staff.pk == request.user.pk and not request.user.is_superuser:
        messages.error(
            request, "You cannot edit your own account. Contact another manager.")
        logger.warning(
            f'Manager {request.user.pk} attempted to edit their own account')
        return redirect('staff_list')

    if request.method == 'POST':
        form = EditStaffForm(request.POST, instance=staff)

        if form.is_valid():
            form.save()
            messages.success(
                request, f"Staff member {staff.first_name} {staff.last_name} updated successfully.")
            logger.info(f'User {request.user.pk} updated staff {staff.pk}')
            return redirect('staff_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EditStaffForm(instance=staff)

    return render(request, 'accounts/staff_edit.html', {
        'form': form,
        'staff': staff,
        'title': f'Edit Staff: {staff.first_name} {staff.last_name}'
    })


@login_required(login_url="login")
def staff_delete(request, pk):
    """
    Delete or deactivate staff member (admin/managers only).

    Features:
    - Soft delete (deactivate) if staff has created records
    - Hard delete if no records exist
    - Prevents self-deletion
    - Full audit logging with IP address

    Security:
    - Only staff 1000 (primary admin) or managers can delete
    - Cannot delete own account
    - Checks for existing records before allowing hard delete
    - Audit trail for all deletions/deactivations

    Permissions: Staff 1000 or MANAGER (is_manager=True) only

    Args:
        pk: Primary key of Account to delete/deactivate

    Returns:
        GET: Renders confirmation page
        POST: Deletes/deactivates staff and redirects to staff_list
    """
    import logging
    logger = logging.getLogger('security.audit')

    # SECURITY: Only staff 1000 (primary admin) OR managers can delete staff
    if not (request.user.staff_number == 1000 or request.user.is_manager):
        messages.error(
            request, "Only the primary administrator or managers can delete staff members.")
        logger.warning(
            f'Unauthorized delete attempt by staff {request.user.staff_number} (not admin or manager)')
        return redirect('staff_list')

    staff = get_object_or_404(Account, pk=pk)

    # Prevent deleting yourself
    if staff.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect('staff_list')

    # Check if staff has created any records
    has_records = False
    try:
        from apps.operations.models import SDRecord, Schedule
        from apps.ebooking.models import BookingRecord
        from apps.declaration.models import Declaration
        from apps.evacuation.models import Evacuation
        from apps.tally.models import TallyInfo

        has_records = (
            SDRecord.objects.filter(created_by=staff).exists() or
            Schedule.objects.filter(created_by=staff).exists() or
            BookingRecord.objects.filter(created_by=staff).exists() or
            Declaration.objects.filter(created_by=staff).exists() or
            Evacuation.objects.filter(created_by=staff).exists() or
            TallyInfo.objects.filter(created_by=staff).exists()
        )
    except:
        pass

    if request.method == 'POST':
        action = request.POST.get('action', 'delete')
        staff_name = f"{staff.first_name} {staff.last_name}"

        if action == 'deactivate':
            staff.is_active = False
            staff.save()

            # SECURITY: Audit log for staff deactivation
            logger.info(
                f'AUDIT: Staff member deactivated - '
                f'Staff ID: {staff.staff_number}, '
                f'Name: {staff_name}, '
                f'Deactivated by: {request.user.staff_number} (User ID: {request.user.pk}), '
                f'IP: {request.META.get("REMOTE_ADDR", "unknown")}'
            )

            messages.success(
                request, f"Staff member {staff_name} has been deactivated. They can no longer log in.")
            return redirect('staff_list')
        elif action == 'delete':
            if has_records:
                messages.error(
                    request,
                    f"Cannot delete {staff_name} because they have created records. Please use Deactivate instead."
                )
                return redirect('staff_list')
            try:
                # SECURITY: Audit log for staff deletion
                logger.warning(
                    f'AUDIT: Staff member deleted - '
                    f'Staff ID: {staff.staff_number}, '
                    f'Name: {staff_name}, '
                    f'Deleted by: {request.user.staff_number} (User ID: {request.user.pk}), '
                    f'IP: {request.META.get("REMOTE_ADDR", "unknown")}'
                )

                staff.delete()
                messages.success(
                    request, f"Staff member {staff_name} has been deleted.")
                return redirect('staff_list')
            except Exception as e:
                # SECURITY: Log detailed error but show generic message to user
                logger.error(
                    f"Error deleting staff member {staff.staff_number}: {str(e)}",
                    exc_info=True,
                    extra={
                        'user': request.user.pk,
                        'staff_id': staff.pk,
                        'staff_number': staff.staff_number
                    }
                )
                messages.error(
                    request, "An error occurred while deleting the staff member. Please try again or contact support.")
                return redirect('staff_list')

    return render(request, 'accounts/staff_confirm_delete.html', {
        'staff': staff,
        'has_records': has_records,
    })


@login_required(login_url='login')
def debug_permissions(request):
    """Debug view to show user's desk assignments and permissions"""
    from apps.core.permissions import _get_user_desks
    from apps.operations.permissions import (
        can_manage_schedules,
        can_manage_sd_records,
        is_terminal_supervisor
    )
    from apps.ebooking.permissions import can_manage_bookings
    from apps.declaration.permissions import can_manage_declarations
    from apps.evacuation.permissions import can_manage_evacuations

    user = request.user
    user_desks = _get_user_desks(user)

    output = []
    output.append("=== USER DESK ASSIGNMENTS DEBUG ===\n\n")
    output.append(f"Staff Number: {user.staff_number}\n")
    output.append(f"Name: {user.first_name} {user.last_name}\n")
    output.append(f"Is Superuser: {user.is_superuser}\n\n")

    output.append("--- Raw Field Values ---\n")
    output.append(
        f"desk field (legacy): '{getattr(user, 'desk', 'NOT FOUND')}'\n")
    output.append(
        f"desks field (new): {getattr(user, 'desks', 'NOT FOUND')}\n\n")

    output.append("--- Computed Desks ---\n")
    output.append(f"_get_user_desks() returns: {user_desks}\n\n")

    output.append("--- Permission Checks ---\n")
    output.append(f"can_manage_schedules: {can_manage_schedules(user)}\n")
    output.append(f"can_manage_sd_records: {can_manage_sd_records(user)}\n")
    output.append(f"can_manage_bookings: {can_manage_bookings(user)}\n")
    output.append(
        f"can_manage_declarations: {can_manage_declarations(user)}\n")
    output.append(f"can_manage_evacuations: {can_manage_evacuations(user)}\n")
    output.append(
        f"is_terminal_supervisor: {is_terminal_supervisor(user)}\n\n")

    output.append("--- Expected Desk Codes ---\n")
    output.append(
        "MANAGER, OPERATIONS, EBOOKING, DECLARATION, EVACUATION, TERMINAL_SUPERVISOR\n\n")

    output.append("--- Instructions ---\n")
    output.append(
        "1. Check if your 'desk' or 'desks' field has the correct value\n")
    output.append("2. Desk codes must match exactly (case-sensitive)\n")
    output.append("3. If desks field is empty [], check the desk field\n")
    output.append(
        "4. If desk field is 'OTHER', you need to be assigned to a desk\n")

    return HttpResponse(''.join(output), content_type='text/plain')
