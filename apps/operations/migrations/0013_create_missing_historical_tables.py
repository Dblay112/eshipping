# Generated manually on 2026-03-13
# Patch migration to create missing django-simple-history tables in production.
#
# Production issue: simple_history signals attempt to INSERT into operations_historical* tables
# (e.g., operations_historicalsdrecord) but those tables are missing.
#
# This migration is safe to run even if some tables already exist.

from django.db import migrations


def _create_table_if_missing(apps, schema_editor, model_name: str) -> None:
    Model = apps.get_model('operations', model_name)
    table_name = Model._meta.db_table

    existing = schema_editor.connection.introspection.table_names()
    if table_name in existing:
        return

    schema_editor.create_model(Model)


def create_missing_history_tables(apps, schema_editor):
    # Keep this list explicit (and stable) to avoid surprises.
    history_models = [
        'HistoricalSchedule',
        'HistoricalScheduleEntry',
        'HistoricalSDRecord',
        'HistoricalSDAllocation',
        'HistoricalSDContainer',
        'HistoricalSDClerk',
        'HistoricalContainerListUpload',
        'HistoricalDailyPort',
        'HistoricalWorkProgram',
    ]

    for model_name in history_models:
        _create_table_if_missing(apps, schema_editor, model_name)


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0012_historicalsdallocation_tonnage_loaded_and_more'),
    ]

    operations = [
        migrations.RunPython(create_missing_history_tables, migrations.RunPython.noop),
    ]
