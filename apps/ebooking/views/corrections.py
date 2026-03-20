"""Booking correction tracking views."""
import logging
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from apps.ebooking.permissions import can_manage_bookings
from ..models import BookingDetail, BookingCorrection, CorrectionAttachment
from apps.operations.models import ScheduleEntry

logger = logging.getLogger(__name__)


@login_required(login_url='login')
def booking_add_correction(request, detail_pk):
    """
    Assigned officer adds correction request for a Bill of Lading.

    Creates accountability trail - no more paper waste! Officers can request
    corrections with multiple file attachments. System tracks round numbers
    and timestamps for full audit trail.

    Features:
    - Multi-file attachment support (images and PDFs)
    - File validation (10MB max per file)
    - Auto-incremented round numbers
    - Viewed/unviewed tracking for ebooking desk

    Permissions:
    - Ebooking desk (can add corrections)
    - Assigned officer (via SDRecord or ScheduleEntry)
    - Manager (can add corrections)

    Args:
        detail_pk: Primary key of BookingDetail to add correction for

    Returns:
        GET: Renders correction form
        POST: Creates correction and redirects to booking list
    """
    detail = get_object_or_404(BookingDetail, pk=detail_pk)
    booking_record = detail.booking_line.booking_record
    sd_record = booking_record.sd_record

    # SECURITY FIX: Check if user is ebooking desk OR assigned to SD OR manager
    is_ebooking = can_manage_bookings(request.user)

    # Check if user is assigned to this SD (via SDRecord OR ScheduleEntry)
    is_assigned = False

    # Check direct assignment on SD record
    if sd_record and sd_record.officer_assigned == request.user:
        is_assigned = True

    # Also check assignment via schedule entry
    if not is_assigned and booking_record.sd_number:
        schedule_entry = ScheduleEntry.objects.filter(
            sd_number__iexact=booking_record.sd_number
        ).select_related('assigned_officer').first()
        if schedule_entry and schedule_entry.assigned_officer == request.user:
            is_assigned = True

    is_manager = request.user.is_manager

    if not (is_ebooking or is_assigned or is_manager):
        logger.warning(
            f'Unauthorized correction attempt by user {request.user.pk} '
            f'for booking detail {detail_pk}'
        )
        messages.error(request, "You don't have permission to add corrections for this booking.")
        return redirect('booking_list')

    if request.method == 'POST':
        correction_text = request.POST.get('correction_text', '').strip()
        if not correction_text:
            messages.error(request, "Please enter the correction needed.")
            return redirect('booking_list')

        # Handle multiple file attachments
        attachments = request.FILES.getlist('attachments')

        # Validate each file
        for attachment in attachments:
            # Validate file size (10MB max per file)
            if attachment.size > 10 * 1024 * 1024:
                messages.error(request, f"File '{attachment.name}' exceeds 10MB limit.")
                return render(request, 'ebooking/booking_add_correction.html', {
                    'detail': detail,
                    'booking_record': booking_record,
                })

            # Validate file type (images and PDFs only)
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'application/pdf']
            if attachment.content_type not in allowed_types:
                messages.error(request, f"File '{attachment.name}' is not an allowed type. Only images (JPEG, PNG, GIF) and PDF files are allowed.")
                return render(request, 'ebooking/booking_add_correction.html', {
                    'detail': detail,
                    'booking_record': booking_record,
                })

        # Create correction (without attachment field - using new multi-file system)
        correction = BookingCorrection.objects.create(
            booking_detail=detail,
            correction_text=correction_text,
            created_by=request.user
        )

        # AUDIT: Booking correction requested
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        staff_number = getattr(request.user, 'staff_number', request.user.id)
        logger.info(
            f'AUDIT: Booking correction requested - Booking: {detail.booking_number}, Round: {correction.round_number}, By: {staff_number} (User ID: {request.user.pk}), IP: {ip}')

        # Create separate attachment records for each file
        for attachment in attachments:
            CorrectionAttachment.objects.create(
                correction=correction,
                file=attachment
            )

        attachment_count = len(attachments)
        attachment_msg = f" with {attachment_count} attachment{'s' if attachment_count != 1 else ''}" if attachment_count > 0 else ""
        messages.success(
            request,
            f"Correction #{correction.round_number} submitted for {detail.booking_number}{attachment_msg}. "
            "E-Booking desk will review and update the document."
        )
        return redirect('booking_list')

    # GET request - show form
    return render(request, 'ebooking/booking_add_correction.html', {
        'detail': detail,
        'booking_record': booking_record,
    })


@login_required(login_url='login')
def booking_correction_history(request, detail_pk):
    """
    View all correction rounds for a specific Bill of Lading.

    Full accountability trail with timestamps, round numbers, and officer names.
    Ebooking desk can mark corrections as viewed. Pagination at 5 corrections
    per page.

    Features:
    - Shows all correction rounds in reverse chronological order
    - Marks corrections as viewed when ebooking desk views them
    - Displays attachments for each correction
    - Pagination for long correction histories

    Permissions:
    - Ebooking desk (can view and mark as viewed)
    - Assigned officer (via SDRecord or ScheduleEntry)

    Args:
        detail_pk: Primary key of BookingDetail to view corrections for

    Returns:
        Renders correction history page with paginated corrections
    """
    detail = get_object_or_404(
        BookingDetail.objects.prefetch_related('corrections__created_by'),
        pk=detail_pk
    )
    booking_record = detail.booking_line.booking_record

    # Only ebooking desk or assigned officer can view corrections
    is_ebooking = can_manage_bookings(request.user)

    # Check if user is assigned to this SD (via SDRecord OR ScheduleEntry)
    is_assigned = False

    # Check direct assignment on SD record
    if booking_record.sd_record and booking_record.sd_record.officer_assigned == request.user:
        is_assigned = True

    # Also check assignment via schedule entry
    if not is_assigned and booking_record.sd_number:
        schedule_entry = ScheduleEntry.objects.filter(
            sd_number__iexact=booking_record.sd_number
        ).select_related('assigned_officer').first()
        if schedule_entry and schedule_entry.assigned_officer == request.user:
            is_assigned = True

    if not (is_ebooking or is_assigned):
        messages.error(request, "You don't have permission to view these corrections.")
        return redirect('booking_list')

    # Mark all corrections as viewed if ebooking desk is viewing
    if is_ebooking:
        detail.corrections.filter(viewed_at__isnull=True).update(viewed_at=timezone.now())

    corrections_list = detail.corrections.all().order_by('-round_number')  # Most recent first

    # Pagination: 5 corrections per page
    paginator = Paginator(corrections_list, 5)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'ebooking/booking_correction_history.html', {
        'detail': detail,
        'booking_record': booking_record,
        'corrections': page_obj,  # Template expects 'corrections'
        'total_corrections': detail.corrections.count(),  # For the count display
        'is_ebooking': is_ebooking,
    })
