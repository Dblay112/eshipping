"""
Management command to force create all Django tables.
This bypasses the migration system and directly creates tables from models.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


class Command(BaseCommand):
    help = 'Force create all tables from models (bypasses migrations)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm you want to force create tables',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.ERROR(
                "This command will force create all tables.\n"
                "Run with --confirm to proceed."
            ))
            return

        self.stdout.write("Force creating tables from models...")

        # Get all models
        all_models = apps.get_models()

        with connection.schema_editor() as schema_editor:
            for model in all_models:
                table_name = model._meta.db_table

                # Check if table exists
                table_exists = self._table_exists(table_name)

                if table_exists:
                    self.stdout.write(f"  ✓ {table_name} already exists")
                else:
                    try:
                        self.stdout.write(f"  Creating {table_name}...")
                        schema_editor.create_model(model)
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Created {table_name}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  ✗ Failed to create {table_name}: {e}"))

        self.stdout.write(self.style.SUCCESS("\nDone! All tables created."))

    def _table_exists(self, table_name):
        """Check if a table exists in the database"""
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM pg_tables
                        WHERE schemaname = 'public'
                        AND tablename = %s
                    );
                """, [table_name])
            else:  # SQLite
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name=?;
                """, [table_name])

            if connection.vendor == 'postgresql':
                return cursor.fetchone()[0]
            else:
                return cursor.fetchone() is not None
