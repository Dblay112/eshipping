"""
Management command to diagnose and fix booking table issues.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Diagnose and fix booking table name issues'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check what tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name LIKE '%booking%'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]

            self.stdout.write(self.style.SUCCESS('Current booking-related tables:'))
            for table in tables:
                self.stdout.write(f'  - {table}')

            # Check if we need to fix anything
            has_old = 'ebooking_bookingrecord' in tables
            has_new = 'ebooking_booking' in tables

            self.stdout.write('')
            self.stdout.write(f'Has ebooking_bookingrecord: {has_old}')
            self.stdout.write(f'Has ebooking_booking: {has_new}')

            if has_old and not has_new:
                self.stdout.write(self.style.WARNING('Need to rename table...'))
                cursor.execute('ALTER TABLE ebooking_bookingrecord RENAME TO ebooking_booking')
                self.stdout.write(self.style.SUCCESS('[OK] Renamed ebooking_bookingrecord to ebooking_booking'))
            elif has_new and not has_old:
                self.stdout.write(self.style.SUCCESS('[OK] Table is correctly named'))
            elif has_old and has_new:
                self.stdout.write(self.style.ERROR('Both tables exist! Dropping old one...'))
                cursor.execute('DROP TABLE ebooking_bookingrecord')
                self.stdout.write(self.style.SUCCESS('[OK] Dropped ebooking_bookingrecord'))
            else:
                self.stdout.write(self.style.WARNING('Neither table exists - migrations will create it'))

            # Verify model configuration
            from apps.ebooking.models import BookingRecord
            self.stdout.write('')
            self.stdout.write(f'Model db_table setting: {BookingRecord._meta.db_table}')

            if BookingRecord._meta.db_table == 'ebooking_booking':
                self.stdout.write(self.style.SUCCESS('[OK] Model is correctly configured'))
            else:
                self.stdout.write(self.style.ERROR(f'[ERROR] Model should use ebooking_booking, not {BookingRecord._meta.db_table}'))
