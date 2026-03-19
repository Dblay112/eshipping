"""API endpoints for ebooking app."""
import logging
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import PermissionDenied

from ..models import BookingRecord

logger = logging.getLogger(__name__)


@login_required(login_url='login')
def debug_model_config(request):
    """
    Debug endpoint showing booking model configuration and database tables.

    Security:
    - SUPERUSER ONLY
    - DEBUG mode only (disabled in production)
    - Returns plain text output

    Returns:
        HttpResponse with model metadata and table names
        Http404 if not in DEBUG mode
        PermissionDenied if not superuser
    """
    # SECURITY FIX: Only allow in DEBUG mode to prevent information disclosure in production
    from django.conf import settings
    from django.http import Http404

    if not settings.DEBUG:
        raise Http404("Debug endpoints are disabled in production.")

    if not request.user.is_superuser:
        logger.warning(f'Unauthorized debug access attempt by user {request.user.pk}')
        raise PermissionDenied("Only superusers can access debug information.")

    from django.db import connection

    output = []
    output.append("=== BOOKING MODEL DEBUG INFO ===\n")
    output.append(f"Model db_table: {BookingRecord._meta.db_table}\n")
    output.append(f"Model file: {BookingRecord.__module__}\n\n")

    output.append("=== DATABASE TABLES ===\n")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name LIKE '%booking%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            output.append(f"  - {table}\n")

    output.append("\n=== MODEL META ===\n")
    output.append(f"db_table: {BookingRecord._meta.db_table}\n")
    output.append(f"app_label: {BookingRecord._meta.app_label}\n")
    output.append(f"model_name: {BookingRecord._meta.model_name}\n")

    return HttpResponse(''.join(output), content_type='text/plain')


@login_required(login_url='login')
def booking_data_json(request):
    """
    API endpoint to fetch existing booking data for an SD number.

    Used for form prepopulation when creating bookings. Returns complete
    booking structure with all contracts and booking details.

    Query params:
        sd_number: SD number to look up (case-insensitive)

    Returns:
        JsonResponse with structure:
        {
            'exists': bool,
            'booking_id': int,
            'sd_number': str,
            'agent': str,
            'vessel': str,
            'contracts': [
                {
                    'contract_number': str,
                    'bookings': [
                        {
                            'booking_number': str,
                            'bill_number': str,
                            'agent': str,
                            'vessel': str,
                            'tonnage': str,
                            'has_file': bool
                        }
                    ]
                }
            ]
        }
    """
    sd_number = request.GET.get('sd_number', '').strip()

    if not sd_number:
        return JsonResponse({'exists': False})

    try:
        booking = BookingRecord.objects.filter(sd_number__iexact=sd_number).first()

        if not booking:
            return JsonResponse({'exists': False})

        # Build booking data structure
        booking_data = {
            'exists': True,
            'booking_id': booking.pk,
            'sd_number': booking.sd_number,
            'agent': booking.agent,
            'vessel': booking.vessel,
            'contracts': []
        }

        # Get all booking lines (contracts)
        for line in booking.lines.all():
            contract_data = {
                'contract_number': line.contract_number,
                'bookings': []
            }

            # Get all booking details for this contract
            for detail in line.details.all():
                contract_data['bookings'].append({
                    'booking_number': detail.booking_number,
                    'bill_number': detail.bill_number,
                    'agent': booking.agent,  # Get from booking record, not detail
                    'vessel': booking.vessel,  # Get from booking record, not detail
                    'tonnage': str(detail.tonnage_booked),  # Correct field name
                    'has_file': bool(detail.file)
                })

            booking_data['contracts'].append(contract_data)

        return JsonResponse(booking_data)

    except Exception as e:
        logger.error(f'Error fetching booking data for SD {sd_number}: {str(e)}')
        return JsonResponse({'exists': False, 'error': 'Server error'})
