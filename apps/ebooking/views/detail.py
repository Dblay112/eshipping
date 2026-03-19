"""Booking detail editing and deletion views."""
import logging
import json
from datetime import date
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from apps.ebooking.permissions import can_manage_bookings
from ..models import BookingRecord, BookingLine, BookingDetail, BookingCorrection

logger = logging.getLogger(__name__)


@login_required(login_url='login')
def booking_edit(request, pk):
    """
    Edit existing booking record with file and correction preservation.

    Features:
    - Preserves existing files if no new file uploaded
    - Maintains correction history across edits
    - Re-associates corrections by booking number
    - Validates tonnage > 0
    - Security: Only ebooking desk or creator can edit

    Args:
        pk: Primary key of BookingRecord to edit

    Returns:
        GET: Renders booking form with existing data
        POST: Updates booking and redirects to list
    """
    if not can_manage_bookings(request.user):
        messages.error(request, "Only the E-Booking desk can edit bookings.")
        return redirect('booking_list')

    booking = get_object_or_404(BookingRecord, pk=pk)

    # SECURITY: Verify ownership - only creator or any ebooking desk member can edit
    if booking.created_by != request.user and not can_manage_bookings(request.user):
        logger.warning(
            f'User {request.user.pk} attempted to edit booking {pk} '
            f'created by {booking.created_by.pk if booking.created_by else "None"}'
        )
        messages.error(request, "You can only edit your own bookings.")
        return redirect('booking_list')

    if request.method == 'POST':
        booking_date = request.POST.get('booking_date')
        sd_number = request.POST.get('sd_number_0', '').strip()

        if not sd_number:
            messages.error(request, "SD number is required.")
            return redirect('booking_edit', pk=pk)

        # Store existing files AND corrections before deleting
        existing_files = {}
        existing_corrections = {}
        for line in booking.lines.all():
            for detail in line.details.all():
                if detail.file:
                    existing_files[detail.pk] = detail.file
                # Store corrections by booking_number for later reassociation
                corrections_list = list(detail.corrections.all().values(
                    'correction_text', 'created_by_id', 'round_number', 'created_at'
                ))
                if corrections_list:
                    existing_corrections[detail.booking_number] = corrections_list

        # Update booking record
        booking.updated_by = request.user
        booking.save()

        # Parse contract indices
        contract_indices = set()
        for key in request.POST.keys():
            if key.startswith('contract_number_0_'):
                contract_idx = key.split('_')[3]
                contract_indices.add(contract_idx)

        # Delete existing lines and details (this will cascade delete corrections)
        booking.lines.all().delete()

        total_updated = 0
        for contract_idx in contract_indices:
            contract_number = request.POST.get(f'contract_number_0_{contract_idx}', '').strip()
            if not contract_number:
                continue

            # Create booking line
            booking_line = BookingLine.objects.create(
                booking_record=booking,
                contract_number=contract_number
            )

            # Parse booking rows for this contract
            row_indices = set()
            for key in request.POST.keys():
                if key.startswith(f'booking_number_0_{contract_idx}_'):
                    row_idx = key.split('_')[4]
                    row_indices.add(row_idx)

            for row_idx in row_indices:
                booking_number = request.POST.get(f'booking_number_0_{contract_idx}_{row_idx}', '').strip()
                bill_number = request.POST.get(f'bill_number_0_{contract_idx}_{row_idx}', '').strip()
                tonnage = request.POST.get(f'tonnage_0_{contract_idx}_{row_idx}', '').strip()
                old_detail_id = request.POST.get(f'detail_id_0_{contract_idx}_{row_idx}', '').strip()

                if booking_number and tonnage:
                    tonnage_decimal = float(tonnage)

                    # VALIDATION: Tonnage must be greater than 0
                    if tonnage_decimal <= 0:
                        continue

                    # Check if new file uploaded
                    file_field = request.FILES.get(f'file_0_{contract_idx}_{row_idx}')

                    # If no new file, try to preserve old file
                    if not file_field and old_detail_id:
                        try:
                            old_id = int(old_detail_id)
                            file_field = existing_files.get(old_id)
                        except (ValueError, TypeError):
                            pass

                    new_detail = BookingDetail.objects.create(
                        booking_line=booking_line,
                        booking_number=booking_number,
                        bill_number=bill_number,
                        tonnage_booked=tonnage_decimal,
                        file=file_field
                    )
                    total_updated += 1

                    # Restore corrections for this booking number
                    if booking_number in existing_corrections:
                        for corr_data in existing_corrections[booking_number]:
                            BookingCorrection.objects.create(
                                booking_detail=new_detail,
                                correction_text=corr_data['correction_text'],
                                created_by_id=corr_data['created_by_id'],
                                round_number=corr_data['round_number'],
                                created_at=corr_data['created_at']
                            )

        messages.success(request, f"✓ Booking updated successfully - {total_updated} booking(s) updated")
        return redirect('booking_list')

    # Prepare booking data for edit mode
    booking_data = {
        'sd_number': booking.sd_number,
        'agent': booking.agent,
        'vessel': booking.vessel,
        'contracts': []
    }

    for line in booking.lines.all():
        contract_data = {
            'contract_number': line.contract_number,
            'bookings': []
        }

        for detail in line.details.all():
            file_name = None
            if detail.file:
                # Extract just the filename from the full path
                import os
                file_name = os.path.basename(detail.file.name)

            contract_data['bookings'].append({
                'detail_id': detail.pk,  # Add detail ID for tracking
                'booking_number': detail.booking_number,
                'bill_number': detail.bill_number,
                'agent': booking.agent,
                'vessel': booking.vessel,
                'tonnage': str(detail.tonnage_booked),
                'has_file': bool(detail.file),
                'file_name': file_name
            })

        booking_data['contracts'].append(contract_data)

    return render(request, 'ebooking/booking_form.html', {
        'booking': booking,
        'booking_data_json': json.dumps(booking_data),
        'can_manage': can_manage_bookings(request.user),
        'today': booking.created_at.date().isoformat() if booking.created_at else date.today().isoformat(),
    })


@login_required(login_url='login')
def booking_detail_delete(request, detail_pk):
    """
    Delete a single booking detail (one booking line), not the entire BookingRecord.

    Features:
    - Cascades deletion: detail → line (if empty) → record (if empty)
    - Security: Only ebooking desk or creator can delete
    - Confirmation page before deletion

    Args:
        detail_pk: Primary key of BookingDetail to delete

    Returns:
        GET: Renders confirmation page
        POST: Deletes detail and redirects to list
    """
    if not can_manage_bookings(request.user):
        messages.error(request, "Only the E-Booking desk can delete bookings.")
        return redirect('booking_list')

    detail = get_object_or_404(BookingDetail, pk=detail_pk)
    booking_record = detail.booking_line.booking_record

    # SECURITY: Verify ownership - only creator or any ebooking desk member can delete
    if booking_record.created_by != request.user and not can_manage_bookings(request.user):
        logger.warning(
            f'User {request.user.pk} attempted to delete booking detail {detail_pk} '
            f'created by {booking_record.created_by.pk if booking_record.created_by else "None"}'
        )
        messages.error(
            request,
            "You can only delete your own bookings. Contact a manager if changes are needed."
        )
        return redirect('booking_list')

    if request.method == 'POST':
        sd_number = booking_record.sd_number
        contract_number = detail.contract_number
        booking_number = detail.booking_number

        # Delete the booking detail
        detail.delete()

        # Check if the booking line is now empty (no more details)
        booking_line = detail.booking_line
        if booking_line and booking_line.details.count() == 0:
            booking_line.delete()

        # Check if the booking record is now empty (no more lines)
        if booking_record.lines.count() == 0:
            booking_record.delete()
            messages.success(request, f"Last booking for SD {sd_number} deleted successfully.")
        else:
            messages.success(request, f"Booking {booking_number} for contract {contract_number} deleted successfully.")

        return redirect('booking_list')

    return render(request, 'ebooking/booking_detail_confirm_delete.html', {
        'detail': detail,
        'booking_record': booking_record,
        'can_manage': can_manage_bookings(request.user),
    })
