"""
Diagnostic command to check Railway database connection and migration status.
Run this on Railway to see what's happening with the database.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Diagnose Railway database connection and migration status'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("RAILWAY DATABASE DIAGNOSTIC")
        self.stdout.write("=" * 60)

        # 1. Check DATABASE_URL environment variable
        database_url = os.environ.get('DATABASE_URL', 'NOT SET')
        if database_url != 'NOT SET':
            # Mask password for security
            if '@' in database_url:
                parts = database_url.split('@')
                user_part = parts[0].split('://')[1].split(':')[0]
                masked = database_url.replace(parts[0].split(':')[-1], '****')
                self.stdout.write(f"\n1. DATABASE_URL: {masked}")
            else:
                self.stdout.write(f"\n1. DATABASE_URL: {database_url}")
        else:
            self.stdout.write("\n1. DATABASE_URL: NOT SET (will use SQLite)")

        # 2. Check Django database configuration
        db_config = settings.DATABASES['default']
        self.stdout.write(f"\n2. Django Database Config:")
        self.stdout.write(f"   Engine: {db_config['ENGINE']}")
        self.stdout.write(f"   Name: {db_config.get('NAME', 'N/A')}")
        self.stdout.write(f"   Host: {db_config.get('HOST', 'N/A')}")
        self.stdout.write(f"   Port: {db_config.get('PORT', 'N/A')}")

        # 3. Check actual database connection
        self.stdout.write(f"\n3. Actual Database Connection:")
        db_vendor = connection.vendor
        self.stdout.write(f"   Vendor: {db_vendor}")

        if db_vendor == 'sqlite':
            self.stdout.write(self.style.WARNING("   ⚠️  Using SQLite (not PostgreSQL!)"))
        elif db_vendor == 'postgresql':
            self.stdout.write(self.style.SUCCESS("   ✓ Using PostgreSQL"))

        # 4. List all tables in database
        self.stdout.write(f"\n4. Tables in Database:")
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

        if tables:
            self.stdout.write(f"   Found {len(tables)} tables:")
            for table in tables[:20]:  # Show first 20
                if 'accounts_account' in table:
                    self.stdout.write(self.style.SUCCESS(f"   ✓ {table}"))
                else:
                    self.stdout.write(f"   - {table}")
            if len(tables) > 20:
                self.stdout.write(f"   ... and {len(tables) - 20} more")
        else:
            self.stdout.write(self.style.ERROR("   ✗ NO TABLES FOUND!"))

        # 5. Check for accounts_account table specifically
        self.stdout.write(f"\n5. Critical Table Check:")
        if 'accounts_account' in tables:
            self.stdout.write(self.style.SUCCESS("   ✓ accounts_account EXISTS"))
        else:
            self.stdout.write(self.style.ERROR("   ✗ accounts_account MISSING"))

        # 6. Check django_migrations table
        if 'django_migrations' in tables:
            with connection.cursor() as cursor:
                cursor.execute("SELECT app, name FROM django_migrations ORDER BY id")
                migrations = cursor.fetchall()

            self.stdout.write(f"\n6. Applied Migrations: {len(migrations)} total")

            # Count by app
            from collections import Counter
            app_counts = Counter([m[0] for m in migrations])
            for app, count in sorted(app_counts.items()):
                self.stdout.write(f"   {app}: {count} migrations")
        else:
            self.stdout.write(self.style.ERROR("\n6. django_migrations table MISSING!"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("DIAGNOSIS COMPLETE")
        self.stdout.write("=" * 60)
