# Generated manually to remove unique_together constraint
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('evacuation', '0008_evacuation_updated_at_evacuation_updated_by_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='evacuation',
            unique_together=set(),
        ),
    ]
