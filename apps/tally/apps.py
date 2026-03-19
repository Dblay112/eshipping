from django.apps import AppConfig


class TallyConfig(AppConfig):
    """
    Django app configuration for tally module.

    Manages cocoa loading tally records with approval workflow.
    Handles bulk loading, straight loading (20ft/40ft), and Japan-specific tallies.

    Features:
    - Tally creation with container tracking
    - Approval workflow (DRAFT → PENDING → APPROVED/REJECTED)
    - Auto-linking to SD records when created
    - Signal handlers for database schema fixes

    Signal Registration:
    - Imports signals module in ready() to register post_migrate handler
    - Ensures sd_record_id column exists after migrations
    """
    name = 'apps.tally'

    def ready(self):
        """
        Initialize app when Django starts.

        Imports signal handlers to register them with Django's signal dispatcher.
        This ensures post_migrate signals run after database migrations.

        Signal Handlers:
        - ensure_sd_record_column_exists: Fixes missing sd_record_id column
        """
        # Import signals (for other signal handlers if any)
        try:
            from . import signals  # noqa
        except ImportError:
            pass
