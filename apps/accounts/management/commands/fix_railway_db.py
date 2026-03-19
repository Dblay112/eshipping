"""
Management command to fix Railway database migration issues.
This command checks if tables exist and forces their creation if needed.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Fix Railway database by checking and creating missing tables'

    def handle(self, *args, **options):
        self.stdout.write("Checking database connection...")

        # Check database type
        db_vendor = connection.vendor
        self.stdout.write(f"Database vendor: {db_vendor}")

        if db_vendor == 'sqlite':
            self.stdout.write(self.style.WARNING("WARNING: Using SQLite database"))
        elif db_vendor == 'postgresql':
            self.stdout.write(self.style.SUCCESS("Using PostgreSQL database"))

        # Check if accounts_account table exists
        with connection.cursor() as cursor:
            if db_vendor == 'postgresql':
                cursor.execute("""
                    SELECT tablename
                    FROM pg_tables
                    WHERE schemaname='public'
                    ORDER BY tablename;
                """)
            else:
                cursor.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                    ORDER BY name;
                """)

            tables = [row[0] for row in cursor.fetchall()]

        self.stdout.write(f"\nFound {len(tables)} tables in database:")
        for table in tables[:10]:  # Show first 10
            self.stdout.write(f"  - {table}")

        if len(tables) > 10:
            self.stdout.write(f"  ... and {len(tables) - 10} more")

        # Check for accounts_account specifically
        if 'accounts_account' in tables:
            self.stdout.write(self.style.SUCCESS("\n✓ accounts_account table EXISTS"))
        else:
            self.stdout.write(self.style.ERROR("\n✗ accounts_account table MISSING"))
            self.stdout.write("\nTo fix this, run:")
            self.stdout.write("  python manage.py migrate --run-syncdb")

        # Check django_migrations table
        if 'django_migrations' in tables:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                count = cursor.fetchone()[0]
                self.stdout.write(f"\n✓ django_migrations table has {count} entries")
