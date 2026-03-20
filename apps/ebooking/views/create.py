"""Booking creation views."""
import logging
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django_ratelimit.decorators import ratelimit

from apps.core.validators import validate_file_size
from apps.ebooking.permissions import can_manage_bookings
from ..models import BookingRecord, BookingLine, BookingDetail
from apps.operations.models import SDRecord

logger = logging.getLogger(__name__)


@ratelimit(key='user', rate='20/h', method='POST')
@login_required(login_url='login')
def booking_create(request):
    """Create new booking records for SD contracts."""
    # SECURITY: Rate limiting prevents spam and DoS attacks
    if getattr(request, 'limited', False):
        messages.error(request, "Too many booking creation attempts. Please wait before trying again.")
        return redirect('booking_list')

    if not can_manage_bookings(request.user):
        messages.error(request, "Only the E-Booking desk can add bookings.")
        return redirect('booking_list')

    if request.method == 'POST':
        booking_date_str = request.POST.get('booking_date', '').strip()
        booking_date = None
        if booking_date_str:
            try:
                booking_date = date.fromisoformat(booking_date_str)
            except ValueError:
                booking_date = date.today()
        else:
            booking_date = date.today()

        total_bookings_created = 0

        # Parse all SD blocks
        sd_indices = set()
        for key in request.POST.keys():
            if key.startswith('sd_number_'):
                sd_index = key.split('_')[2]
                sd_indices.add(sd_index)

        for sd_index in sd_indices:
            sd_number = request.POST.get(f'sd_number_{sd_index}', '').strip()
            if not sd_number:
                continue

            # Try to find SD record
            try:
                sd_record = SDRecord.objects.get(sd_number__iexact=sd_number)
            except SDRecord.DoesNotExist:
                messages.warning(request, f"SD {sd_number} not found in records. Skipping.")
                continue

            # Check if booking already exists for this SD
            existing_booking = BookingRecord.objects.filter(sd_record=sd_record).first()
            if existing_booking:
                messages.info(request, f"Booking for SD {sd_number} already exists. Redirecting to edit page.")
                return redirect('booking_edit', pk=existing_booking.pk)

            # Parse all contracts for this SD
            contract_indices = set()
            for key in request.POST.keys():
                if key.startswith(f'contract_number_{sd_index}_'):
                    parts = key.split('_')
                    if len(parts) >= 4:
                        contract_idx = parts[3]
                        contract_indices.add(contract_idx)

            # Create booking record for this SD
            booking_record = None
            bookings_for_sd = 0

            for contract_idx in contract_indices:
                contract_number = request.POST.get(f'contract_number_{sd_index}_{contract_idx}', '').strip()
                if not contract_number:
                    continue

                # Parse all booking rows for this contract
                row_indices = set()
                for key in request.POST.keys():
                    if key.startswith(f'booking_number_{sd_index}_{contract_idx}_'):
                        parts = key.split('_')
                        if len(parts) >= 5:
                            row_idx = parts[4]
                            row_indices.add(row_idx)

                for row_idx in row_indices:
                    booking_number = request.POST.get(f'booking_number_{sd_index}_{contract_idx}_{row_idx}', '').strip()
                    bill_number = request.POST.get(f'bill_number_{sd_index}_{contract_idx}_{row_idx}', '').strip()
                    agent = request.POST.get(f'agent_{sd_index}_{contract_idx}_{row_idx}', '').strip()
                    vessel = request.POST.get(f'vessel_{sd_index}_{contract_idx}_{row_idx}', '').strip()
                    tonnage = request.POST.get(f'tonnage_{sd_index}_{contract_idx}_{row_idx}', '').strip()
                    file = request.FILES.get(f'file_{sd_index}_{contract_idx}_{row_idx}')

                    # Only create if booking number and tonnage are provided
                    if booking_number and tonnage:
                        try:
                            # SECURITY: Validate file size before processing
                            if file:
                                validate_file_size(file, 'pdf')

                            tonnage_decimal = float(tonnage)

                            # VALIDATION: Tonnage must be greater than 0
                            if tonnage_decimal <= 0:
                                messages.warning(request, f"Skipped booking {booking_number}: Tonnage must be greater than 0")
                                continue

                            # Create booking record if not exists
                            if not booking_record:
                                booking_record = BookingRecord.objects.create(
                                    sd_record=sd_record,
                                    sd_number=sd_record.sd_number,
                                    agent=agent or sd_record.agent,
                                    vessel=vessel or sd_record.vessel_name,
                                    date=booking_date,
                                    created_by=request.user,
                                    updated_by=request.user,
                                )

                                # AUDIT: Booking created
                                ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
                                if ',' in ip:
                                    ip = ip.split(',')[0].strip()
                                staff_number = getattr(request.user, 'staff_number', request.user.id)
                                logger.info(
                                    f'AUDIT: Booking created - SD: {sd_record.sd_number}, Agent: {agent or sd_record.agent}, By: {staff_number} (User ID: {request.user.pk}), IP: {ip}')

                            # Get or create booking line for this contract
                            booking_line, created = BookingLine.objects.get_or_create(
                                booking_record=booking_record,
                                contract_number=contract_number,
                            )

                            # Create booking detail
                            BookingDetail.objects.create(
                                booking_line=booking_line,
                                contract_number=contract_number,
                                booking_number=booking_number,
                                bill_number=bill_number,
                                tonnage_booked=tonnage_decimal,
                                file=file,
                            )

                            bookings_for_sd += 1
                            total_bookings_created += 1

                        except ValidationError as e:
                            messages.error(request, str(e))
                        except Exception as e:
                            # SECURITY: Log detailed error but show generic message to user
                            logger.error(
                                f"Error creating booking {booking_number}: {str(e)}",
                                exc_info=True,
                                extra={
                                    'user': request.user.pk,
                                    'sd_number': sd_number,
                                    'booking_number': booking_number
                                }
                            )
                            messages.error(request, "An error occurred while creating the booking. Please try again or contact support.")

            if bookings_for_sd > 0:
                messages.success(
                    request,
                    f"✓ {bookings_for_sd} booking(s) created by {request.user.first_name} {request.user.last_name} for SD {sd_number}"
                )

        if total_bookings_created > 0:
            return redirect('booking_list')
        else:
            messages.warning(request, "No bookings were created. Please fill in at least one booking number and tonnage.")

    return render(request, 'ebooking/booking_form.html', {
        'action': 'Create',
        'can_manage': can_manage_bookings(request.user),
        'today': date.today().isoformat(),
    })
