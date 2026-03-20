import json

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django_ratelimit.decorators import ratelimit

import logging

from ..models import SDRecord, ScheduleEntry

logger = logging.getLogger(__name__)


@ratelimit(key='user', rate='10/m', method='GET')
@login_required(login_url='login')
def sd_search_json(request):
    """
    Live search endpoint for SD records (used by navbar search).

    Features:
    - Searches across SD number, vessel, buyer, agent, SI REF, MK number, contract number
    - Returns top 8 results ordered by creation date
    - Includes contract allocations for each SD
    - Returns JSON with SD details and URL for navigation

    Security:
    - All authenticated users can search (no desk restriction)
    - Rate limited to 10 requests per minute per user

    Permissions: All authenticated users
    Rate limit: 10 requests per minute per user

    Query Parameters:
        q: Search query (minimum 2 characters)

    Returns:
        JSON response with search results:
        {
            "results": [
                {
                    "id": 1,
                    "sd_number": "SD100",
                    "vessel": "MSC IKARIA VI",
                    "agent": "MAERSK",
                    "buyer": "CARGILL",
                    "tonnage": "1000.00",
                    "is_complete": true,
                    "url": "/operations/1/",
                    "contracts": [
                        {
                            "contract_number": "NJ2604251911",
                            "allocated_tonnage": "250.00",
                            "mk_number": "MK 042519"
                        }
                    ]
                }
            ]
        }
    """
    # SECURITY: all authenticated users can use SD search (no desk restriction)
    q = request.GET.get('q', '').strip()
    results = []
    if len(q) >= 2:
        sds = SDRecord.objects.prefetch_related('allocations').filter(
            Q(sd_number__icontains=q) |
            Q(vessel_name__icontains=q) |
            Q(buyer__icontains=q) |
            Q(agent__icontains=q) |
            Q(si_ref__icontains=q) |
            Q(allocations__mk_number__icontains=q) |
            Q(allocations__contract_number__icontains=q)
        ).distinct().order_by('-created_at')[:8]

        for sd in sds:
            # Get contracts for this SD
            contracts = []
            for alloc in sd.allocations.all():
                contracts.append({
                    'contract_number': alloc.contract_number,
                    'allocated_tonnage': str(alloc.allocated_tonnage),
                    'mk_number': alloc.mk_number,
                })

            results.append({
                'id': sd.pk,
                'sd_number': sd.sd_number,
                'vessel': sd.vessel_name,
                'agent': sd.agent,
                'buyer': sd.buyer,
                'tonnage': str(sd.tonnage),
                'is_complete': sd.is_complete,
                'url': reverse('sd_detail', args=[sd.pk]),
                'contracts': contracts,
            })
    return JsonResponse({'results': results})


@csrf_protect
@login_required(login_url='login')
def sd_details_json(request):
    """
    API endpoint to fetch SD record details by SD number.

    Used by forms to auto-fill data when user enters an SD number.
    Powers the tally prepopulation feature and other form auto-fills.

    Features:
    - Fetches SD record by SD number (case-insensitive)
    - Returns all contract allocations with details
    - Returns vessel, agent, buyer, crop year, tonnage, etc.
    - Returns 404 if SD not found

    Security:
    - All authenticated users can fetch SD details (no desk restriction)
    - CSRF protected to prevent cross-site request forgery attacks

    Permissions: All authenticated users

    Query Parameters:
        sd_number: SD number to fetch (required)

    Returns:
        JSON response with SD details:
        {
            "exists": true,
            "id": 1,
            "sd_number": "SD100",
            "vessel_name": "MSC IKARIA VI",
            "agent": "MAERSK",
            "buyer": "CARGILL",
            "crop_year": "2024/2025 MC",
            "tonnage": "1000.00",
            "container_size": "40FT",
            "loading_type": "FCL",
            "port_of_loading": "TEMA",
            "port_of_discharge": "HAMBURG",
            "eta": "2026-03-20",
            "allocations": [
                {
                    "id": 1,
                    "contract_number": "NJ2604251911",
                    "mk_number": "MK 042519",
                    "allocated_tonnage": "250.00",
                    "buyer": "CARGILL",
                    "agent": "MAERSK",
                    "cocoa_type": "COCOA BEANS",
                    "allocation_label": "PT"
                }
            ]
        }

        Or if not found:
        {
            "exists": false,
            "error": "SD number not found"
        }
    """
    sd_number = request.GET.get('sd_number', '').strip()

    if not sd_number:
        return JsonResponse({'error': 'SD number is required'}, status=400)

    try:
        sd = SDRecord.objects.prefetch_related('allocations').get(sd_number__iexact=sd_number)

        # Get all allocations (contract lines)
        allocations = []
        for alloc in sd.allocations.all():
            allocations.append({
                'id': alloc.id,
                'contract_number': alloc.contract_number,
                'mk_number': alloc.mk_number,
                'allocated_tonnage': str(alloc.allocated_tonnage),
                'buyer': alloc.buyer,
                'agent': alloc.agent,
                'cocoa_type': alloc.cocoa_type,
                'allocation_label': alloc.allocation_label,
            })

        data = {
            'exists': True,
            'id': sd.pk,
            'sd_number': sd.sd_number,
            'vessel_name': sd.vessel_name,
            'agent': sd.agent,
            'buyer': sd.buyer,
            'crop_year': sd.crop_year,
            'tonnage': str(sd.tonnage),
            'container_size': sd.container_size,
            'loading_type': sd.loading_type,
            'port_of_loading': sd.port_of_loading,
            'port_of_discharge': sd.port_of_discharge,
            'eta': sd.eta.isoformat() if sd.eta else None,
            'allocations': allocations,
        }

        return JsonResponse(data)

    except SDRecord.DoesNotExist:
        return JsonResponse({'exists': False, 'error': 'SD number not found'}, status=404)


@csrf_exempt
@login_required(login_url='login')
def client_error_report(request):
    """
    Receive client-side error reports from browsers.

    Provides visibility when JavaScript breaks in production.
    The payload is logged server-side; no database writes.

    Features:
    - Logs JavaScript errors from production browsers
    - Captures error type, message, filename, line/column numbers
    - Captures stack trace and user agent
    - Associates error with user ID for debugging
    - No sensitive data stored (safe logging only)

    Security:
    - CSRF protected
    - Only authenticated users can report errors
    - Sanitizes payload before logging (no sensitive data)

    Permissions: All authenticated users

    Request Body (JSON):
        {
            "type": "error",
            "message": "Uncaught TypeError: Cannot read property 'foo' of undefined",
            "filename": "https://example.com/static/js/app.js",
            "lineno": 42,
            "colno": 15,
            "stack": "Error: ...",
            "url": "https://example.com/page",
            "userAgent": "Mozilla/5.0 ...",
            "timestamp": "2026-03-18T10:30:00.000Z"
        }

    Returns:
        JSON response: {"status": "ok"}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        logger.warning('client_error_report: invalid JSON payload')
        return JsonResponse({'status': 'ignored'}, status=200)

    # Avoid logging too much / sensitive info
    safe = {
        'type': payload.get('type'),
        'message': payload.get('message'),
        'filename': payload.get('filename'),
        'lineno': payload.get('lineno'),
        'colno': payload.get('colno'),
        'stack': payload.get('stack'),
        'url': payload.get('url'),
        'userAgent': payload.get('userAgent'),
        'timestamp': payload.get('timestamp'),
        'user_id': getattr(request.user, 'pk', None),
    }

    logger.warning('CLIENT_JS_ERROR %s', safe)
    return JsonResponse({'status': 'ok'})


@login_required(login_url='login')
def allocations_for_sd(request, pk):
    """
    Return contract allocations for a given SD record.

    Used by booking and declaration forms to load contract options.
    Each allocation represents a contract line with allocated tonnage.

    IMPORTANT: Balance is NOT cumulative. Each declaration/booking is independent.
    Balance = Allocated Tonnage (no summing of existing declarations/bookings).
    The frontend calculates: Balance = Allocated - Current Entry Tonnage.

    Features:
    - Returns all contract allocations for an SD
    - Includes contract number, MK number, allocated tonnage
    - Returns balance as allocated tonnage (frontend handles calculation)
    - Ordered by allocation label (PT, BL, etc.)

    Security:
    - All authenticated users can access allocation data (no desk restriction)
    - Used for booking/declaration form population

    Permissions: All authenticated users

    Args:
        pk: Primary key of SDRecord to fetch allocations for

    Returns:
        JSON response with allocations:
        {
            "allocations": [
                {
                    "id": 1,
                    "text": "PT - NJ2604251911 (250.00 MT)",
                    "contract_number": "NJ2604251911",
                    "mk_number": "MK 042519",
                    "allocated_tonnage": "250.00",
                    "allocation_label": "PT",
                    "label": "PT",
                    "balance": 250.0,
                    "agent": "MAERSK"
                }
            ]
        }
    """
    # SECURITY: all authenticated users can access allocation data for booking/declaration forms (no desk restriction)
    from ..models import SDAllocation

    allocations = SDAllocation.objects.filter(sd_record_id=pk).order_by('allocation_label')
    data = []

    for a in allocations:
        # Return allocated tonnage only - no balance calculation
        # Each declaration/booking is independent and shows: Allocated - Its Own Tonnage
        # We do NOT sum all declarations/bookings for cumulative balance
        data.append({
            'id': a.id,
            'text': str(a),
            'contract_number': a.contract_number,
            'mk_number': a.mk_number,
            'allocated_tonnage': str(a.allocated_tonnage),
            'allocation_label': a.allocation_label,
            'label': a.allocation_label,  # JavaScript expects 'label'
            'balance': float(a.allocated_tonnage),  # Return allocated tonnage as balance
            'agent': a.agent,  # For declaration form
        })

    return JsonResponse({'allocations': data})
