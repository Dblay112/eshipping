# Generated manually for multi-file attachment feature

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ebooking', '0010_bookingcorrection_attachment_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CorrectionAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(help_text='Image or PDF file', upload_to='correction_attachments/', verbose_name='File')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('correction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='ebooking.bookingcorrection', verbose_name='Correction')),
            ],
            options={
                'verbose_name': 'Correction Attachment',
                'verbose_name_plural': 'Correction Attachments',
                'ordering': ['uploaded_at'],
            },
        ),
    ]
