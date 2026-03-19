"""
Check what tables exist in the database
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Check what tables exist in the database'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # List all tables
            cursor.execute("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)

            tables = cursor.fetchall()

            self.stdout.write(f"\nTotal tables: {len(tables)}")
            self.stdout.write("\nTables in database:")
            for table in tables:
                self.stdout.write(f"  - {table[0]}")

            # Check specifically for accounts_account
            if any('accounts_account' in str(t) for t in tables):
                self.stdout.write(self.style.SUCCESS("\n✓ accounts_account table EXISTS"))
            else:
                self.stdout.write(self.style.ERROR("\n✗ accounts_account table MISSING"))
