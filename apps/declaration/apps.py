from django.apps import AppConfig


class DeclarationConfig(AppConfig):
    """
    Django app configuration for declaration module.

    Manages customs declaration records for cocoa shipments.
    Tracks declarations per contract with balance monitoring.

    Features:
    - Declaration creation per contract allocation
    - Balance tracking (allocated tonnage vs declared tonnage)
    - Multiple declarations per contract allowed
    - Auto-linking to SD records when created
    - PDF document upload for each declaration
    """
    name = 'apps.declaration'
