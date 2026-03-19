from django.apps import AppConfig


class EbookingConfig(AppConfig):
    """
    Django app configuration for ebooking module.

    Manages booking records for cocoa shipments with Bill of Lading tracking.
    Handles booking corrections requested by assigned officers.

    Features:
    - Booking creation per contract allocation
    - Balance tracking (allocated tonnage vs booked tonnage)
    - Multiple bookings per contract allowed
    - Bill of Lading document upload
    - Booking correction workflow with audit trail
    - Auto-linking to SD records when created
    """
    name = 'apps.ebooking'
