"""
Management command to fix missing sd_record_id column in tally_tallyinfo table.

This command checks if the column exists and creates it if missing.
Safe to run multiple times (idempotent).
Works with both PostgreSQL and SQLite.

Usage: python manage.py fix_sd_record_column
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Fix missing sd_record_id column in tally_tallyinfo table'

    def handle(self, *args, **options):
        self.stdout.write('Checking tally_tallyinfo table...')

        # Use Django's introspection to check if column exists (works with all databases)
        with connection.cursor() as cursor:
            # Get table description
            cursor.execute("SELECT * FROM tally_tallyinfo LIMIT 0")
            columns = [col[0] for col in cursor.description]

            if 'sd_record_id' in columns:
                self.stdout.write(self.style.SUCCESS('✓ Column sd_record_id already exists'))
                return

            self.stdout.write('Adding sd_record_id column...')

            # Detect database backend
            db_vendor = connection.vendor

            if db_vendor == 'postgresql':
                # PostgreSQL syntax
                cursor.execute("""
                    ALTER TABLE tally_tallyinfo
                    ADD COLUMN sd_record_id INTEGER NULL
                """)

                cursor.execute("""
                    ALTER TABLE tally_tallyinfo
                    ADD CONSTRAINT tally_tallyinfo_sd_record_id_fkey
                    FOREIGN KEY (sd_record_id)
                    REFERENCES operations_sdrecord(id)
                    ON DELETE SET NULL
                """)
            elif db_vendor == 'sqlite':
                # SQLite syntax (no foreign key constraint in ALTER TABLE)
                cursor.execute("""
                    ALTER TABLE tally_tallyinfo
                    ADD COLUMN sd_record_id INTEGER NULL
                    REFERENCES sd_tracker_sdrecord(id)
                    ON DELETE SET NULL
                """)
            else:
                self.stdout.write(self.style.ERROR(f'Unsupported database: {db_vendor}'))
                return

            self.stdout.write(self.style.SUCCESS('✓ Column sd_record_id created successfully'))

