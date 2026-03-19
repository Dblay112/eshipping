# Generated manually to fix table rename idempotency issue

from django.db import migrations


def fix_table_rename(apps, schema_editor):
    """
    Ensure ebooking_bookingrecord is renamed to ebooking_booking.
    This is idempotent - safe to run multiple times.
    Works with both SQLite and PostgreSQL.
    """
    # Check if old table exists and new table doesn't
    with schema_editor.connection.cursor() as cursor:
        # Get database engine
        db_engine = schema_editor.connection.settings_dict['ENGINE']

        # Get list of tables based on database type
        if 'postgresql' in db_engine:
            cursor.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public' AND tablename IN ('ebooking_bookingrecord', 'ebooking_booking')
            """)
        else:  # SQLite
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('ebooking_bookingrecord', 'ebooking_booking')
            """)

        tables = [row[0] for row in cursor.fetchall()]

        has_old_table = 'ebooking_bookingrecord' in tables
        has_new_table = 'ebooking_booking' in tables

        if has_old_table and not has_new_table:
            # Need to rename
            cursor.execute('ALTER TABLE ebooking_bookingrecord RENAME TO ebooking_booking')
        elif has_new_table and not has_old_table:
            # Already renamed, nothing to do
            pass
        elif has_old_table and has_new_table:
            # Both exist - this shouldn't happen, but drop the old one
            cursor.execute('DROP TABLE ebooking_bookingrecord')
        # else: neither exists, which means fresh database - migrations will create it


def reverse_fix(apps, schema_editor):
    """Reverse the rename if needed"""
    with schema_editor.connection.cursor() as cursor:
        # Get database engine
        db_engine = schema_editor.connection.settings_dict['ENGINE']

        # Get list of tables based on database type
        if 'postgresql' in db_engine:
            cursor.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public' AND tablename IN ('ebooking_bookingrecord', 'ebooking_booking')
            """)
        else:  # SQLite
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('ebooking_bookingrecord', 'ebooking_booking')
            """)

        tables = [row[0] for row in cursor.fetchall()]

        if 'ebooking_booking' in tables and 'ebooking_bookingrecord' not in tables:
            cursor.execute('ALTER TABLE ebooking_booking RENAME TO ebooking_bookingrecord')


class Migration(migrations.Migration):

    dependencies = [
        ('ebooking', '0007_alter_bookingdetail_file'),
    ]

    operations = [
        migrations.RunPython(fix_table_rename, reverse_fix),
    ]
