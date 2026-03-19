# Generated manually on 2026-03-01
# Data migration to convert single desk to multi-desk format

from django.db import migrations


def migrate_desk_to_desks(apps, schema_editor):
    """Migrate existing desk values to the new desks list field"""
    Account = apps.get_model('accounts', 'Account')

    for account in Account.objects.all():
        # If desks is already populated, skip
        if account.desks:
            continue

        # If desk field has a value and it's not 'OTHER', add it to desks list
        if account.desk and account.desk != 'OTHER':
            account.desks = [account.desk]
            account.save(update_fields=['desks'])


def reverse_migration(apps, schema_editor):
    """Reverse migration - copy first desk from desks list back to desk field"""
    Account = apps.get_model('accounts', 'Account')

    for account in Account.objects.all():
        if account.desks and len(account.desks) > 0:
            account.desk = account.desks[0]
            account.save(update_fields=['desk'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_account_desks_alter_account_desk'),
    ]

    operations = [
        migrations.RunPython(migrate_desk_to_desks, reverse_migration),
    ]
