# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evacuation', '0003_evacuationline_container_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='evacuationline',
            name='vessel',
            field=models.CharField(blank=True, max_length=200, verbose_name='Vessel Name'),
        ),
    ]
