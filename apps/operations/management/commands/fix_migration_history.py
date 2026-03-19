"""
Management command to fix migration history after app rename.

This command updates the django_migrations table to rename all 'sd_tracker'
entries to 'operations' to match the current app label.

Usage: python manage.py fix_migration_history
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Fix migration history: rename sd_tracker to operations in django_migrations table'

    def handle(self, *args, **options):
        self.stdout.write('Checking django_migrations table...')

        with connection.cursor() as cursor:
            # Check how many sd_tracker migrations exist
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app = 'sd_tracker'"
            )
            count = cursor.fetchone()[0]

            if count == 0:
                self.stdout.write(self.style.SUCCESS('✓ No sd_tracker migrations found - already fixed!'))
                return

            self.stdout.write(f'Found {count} migrations with app=sd_tracker')
            self.stdout.write('Updating to app=operations...')

            # Update all sd_tracker migrations to operations
            cursor.execute(
                "UPDATE django_migrations SET app = 'operations' WHERE app = 'sd_tracker'"
            )

            self.stdout.write(self.style.SUCCESS(f'✓ Updated {count} migration records from sd_tracker to operations'))
            self.stdout.write(self.style.SUCCESS('✓ Migration history fixed successfully!'))
