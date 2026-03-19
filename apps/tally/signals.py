"""
Signal handlers for tally app.

This includes a post_migrate signal that forcefully adds the sd_record_id column
if it's missing from the database. This is a workaround for migration 0013 being
marked as applied but the column never actually being created in production.
"""
from django.db import connection
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def ensure_sd_record_column_exists(sender, **kwargs):
    """
    Ensure sd_record_id column exists in tally_tallyinfo table after migrations.

    EMERGENCY FIX: This signal handler forcefully adds the sd_record_id column
    if it's missing from the database. This is a workaround for migration 0013
    being marked as applied but the column never actually being created in production.

    Historical Context:
    - Migration 0013 added sd_record ForeignKey to TallyInfo model
    - On some deployments, migration was marked applied but column wasn't created
    - This caused crashes when trying to access tally.sd_record
    - This signal handler runs after every migration to verify and fix the issue

    Features:
    - Runs only for tally app (checks sender.name)
    - Checks if column exists before attempting to add
    - Handles both PostgreSQL and SQLite databases
    - Adds foreign key constraint on PostgreSQL
    - Prints status messages for debugging
    - Doesn't raise exceptions (lets app continue on error)

    Database Support:
    - PostgreSQL: Adds column + foreign key constraint
    - SQLite: Adds column only (SQLite has limited ALTER TABLE support)

    Args:
        sender: AppConfig instance that triggered the signal
        **kwargs: Additional signal arguments

    Example Output:
        [TALLY] sd_record_id column exists
        OR
        [TALLY] sd_record_id column missing - adding now...
        [TALLY] sd_record_id column and constraint added successfully
    """
    # Only run for tally app
    if sender.name != 'apps.tally':
        return

    with connection.cursor() as cursor:
        try:
            # Check if column exists
            cursor.execute("SELECT * FROM tally_tallyinfo LIMIT 0")
            columns = [col[0] for col in cursor.description]

            if 'sd_record_id' in columns:
                print('[TALLY] sd_record_id column exists')
                return

            print('[TALLY] sd_record_id column missing - adding now...')

            db_vendor = connection.vendor

            if db_vendor == 'postgresql':
                # Add column
                cursor.execute("""
                    ALTER TABLE tally_tallyinfo
                    ADD COLUMN sd_record_id INTEGER NULL
                """)

                # Add foreign key constraint
                cursor.execute("""
                    ALTER TABLE tally_tallyinfo
                    ADD CONSTRAINT tally_tallyinfo_sd_record_id_fkey
                    FOREIGN KEY (sd_record_id)
                    REFERENCES operations_sdrecord(id)
                    ON DELETE SET NULL
                """)
                print('[TALLY] sd_record_id column and constraint added successfully')

            elif db_vendor == 'sqlite':
                cursor.execute("""
                    ALTER TABLE tally_tallyinfo
                    ADD COLUMN sd_record_id INTEGER NULL
                """)
                print('[TALLY] sd_record_id column added successfully')

        except Exception as e:
            print(f'[TALLY] Error ensuring sd_record_id column: {e}')
            # Don't raise - let the app continue
