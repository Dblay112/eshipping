# Generated manually for booking restructure

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('operations', '0001_initial'),
        ('ebooking', '0001_initial'),
    ]

    operations = [
        # Create BookingRecord model (uses default table: ebooking_bookingrecord)
        migrations.CreateModel(
            name='BookingRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sd_number', models.CharField(max_length=100, verbose_name='SD Number')),
                ('vessel', models.CharField(blank=True, max_length=200, verbose_name='Vessel')),
                ('agent', models.CharField(blank=True, max_length=200, verbose_name='Agent')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='booking_records_created', to=settings.AUTH_USER_MODEL)),
                ('sd_record', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='booking_records', to='operations.sdrecord')),
            ],
            options={
                'verbose_name': 'Booking Record',
                'verbose_name_plural': 'Booking Records',
                'ordering': ['-created_at'],
            },
        ),
        # Create BookingLine model
        migrations.CreateModel(
            name='BookingLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contract_number', models.CharField(max_length=100, verbose_name='Contract Number')),
                ('booking_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='ebooking.bookingrecord')),
            ],
            options={
                'verbose_name': 'Booking Line',
                'verbose_name_plural': 'Booking Lines',
                'ordering': ['contract_number'],
            },
        ),
        # Create BookingDetail model
        migrations.CreateModel(
            name='BookingDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('booking_number', models.CharField(max_length=100, verbose_name='Booking Number')),
                ('bill_number', models.CharField(blank=True, max_length=100, verbose_name='Bill of Lading No.')),
                ('tonnage_booked', models.DecimalField(decimal_places=4, max_digits=10, verbose_name='Tonnage Booked (MT)')),
                ('file', models.FileField(blank=True, null=True, upload_to='booking_files/', verbose_name='Document')),
                ('booking_line', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='details', to='ebooking.bookingline')),
            ],
            options={
                'verbose_name': 'Booking Detail',
                'verbose_name_plural': 'Booking Details',
                'ordering': ['booking_number'],
            },
        ),
    ]
