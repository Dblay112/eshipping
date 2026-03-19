from django.contrib import admin
from .models import BookingRecord, BookingLine, BookingDetail


@admin.register(BookingRecord)
class BookingRecordAdmin(admin.ModelAdmin):
    list_display = ['sd_number', 'vessel', 'agent', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['sd_number', 'vessel', 'agent']
    raw_id_fields = ['created_by', 'updated_by']
    ordering = ['-created_at']


@admin.register(BookingLine)
class BookingLineAdmin(admin.ModelAdmin):
    list_display = ['booking_record', 'contract_number']
    search_fields = ['contract_number']
    raw_id_fields = ['booking_record']


@admin.register(BookingDetail)
class BookingDetailAdmin(admin.ModelAdmin):
    list_display = ['booking_line', 'contract_number', 'booking_number', 'bill_number', 'tonnage_booked']
    search_fields = ['contract_number', 'booking_number', 'bill_number']
    raw_id_fields = ['booking_line']
