from django.apps import AppConfig


class SdTrackerConfig(AppConfig):
    """
    Django app configuration for operations module (SD Tracker).

    Manages SD (Shipping Document) records, schedules, and container tracking.
    Core module that other desks link to via orphaned record auto-linking.

    Features:
    - SD record creation with contract allocations
    - Daily loading schedules with officer assignments
    - Container tracking from tally approvals
    - Orphaned record auto-linking (bookings, declarations, evacuations, tallies)
    - Schedule officer assignment to SD records
    - Work program and daily port report management

    Signal Registration:
    - Imports signals module in ready() to register post_save/pre_delete handlers
    - Tally container sync: TallyContainer → SDContainer
    - Backward linkage: SDRecord creation → link existing records
    - Cleanup: TallyContainer deletion → remove SDContainer
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.operations'
    verbose_name = 'SD Tracker'

    def ready(self):
        """
        Initialize app when Django starts.

        Imports signal handlers to register them with Django's signal dispatcher.
        This ensures post_save and pre_delete signals run for data synchronization.

        Signal Handlers:
        - sync_tally_container_to_sd: Syncs approved tally containers to SD
        - sync_all_tally_containers_on_tally_save: Re-syncs all containers on tally update
        - link_existing_records_to_sd: Auto-links orphaned records when SD created
        - cleanup_sd_container_on_tally_container_delete: Removes SDContainer on deletion
        - cleanup_sd_containers_on_tally_delete: Removes all SDContainers when tally deleted
        """
        import apps.operations.signals  # noqa — registers signal handlers
