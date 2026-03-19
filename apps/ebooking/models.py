from django.db import models
from django.conf import settings
from django.db.models import Sum
from simple_history.models import HistoricalRecords
from apps.core.validators import validate_pdf_file, validate_file_size_10mb


class BookingRecord(models.Model):
    """
    A booking record created by the E-Booking desk for a particular SD.
    One record per SD booking session. Multiple contract lines via BookingLine.
    """
    sd_record = models.ForeignKey(
        'operations.SDRecord',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='booking_records',
    )
    sd_number = models.CharField(max_length=100, verbose_name="SD Number")
    vessel = models.CharField(max_length=200, blank=True, verbose_name="Vessel Name")
    agent = models.CharField(max_length=200, blank=True, verbose_name="Shipping Line / Agent")
    notes = models.TextField(blank=True)

    # User-selected booking date (used for calendar grouping)
    date = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='booking_records_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='booking_records_updated',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        db_table = 'ebooking_booking'
        ordering = ['-created_at']
        verbose_name = "Booking Record"
        verbose_name_plural = "Booking Records"

    def __str__(self):
        return f"Booking — SD {self.sd_number} ({self.created_at.date() if self.created_at else ''})"

    def save(self, *args, **kwargs):
        if self.sd_record and not self.agent:
            self.agent = self.sd_record.agent
        if self.sd_record and not self.sd_number:
            self.sd_number = self.sd_record.sd_number
        super().save(*args, **kwargs)


class BookingLine(models.Model):
    """
    One contract line within a booking record.
    Each line represents one contract and can have multiple booking/bill details.
    """
    booking_record = models.ForeignKey(
        BookingRecord,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    contract_number = models.CharField(max_length=100, blank=True, verbose_name="Contract Number")

    history = HistoricalRecords()

    class Meta:
        ordering = ['contract_number']
        verbose_name = "Booking Line"
        verbose_name_plural = "Booking Lines"

    def __str__(self):
        return f"{self.contract_number} — {self.booking_record}"

    @property
    def total_tonnage_booked(self):
        """Sum of all booking details for this contract."""
        return self.details.aggregate(total=Sum('tonnage_booked'))['total'] or 0

    @property
    def contract_balance(self):
        """Balance remaining for this contract on the SD."""
        if not self.booking_record.sd_record or not self.contract_number:
            return None
        from apps.operations.models import SDAllocation
        alloc = SDAllocation.objects.filter(
            sd_record=self.booking_record.sd_record,
            contract_number__iexact=self.contract_number
        ).first()
        if not alloc:
            return None
        total_booked = BookingDetail.objects.filter(
            booking_line__booking_record__sd_record=self.booking_record.sd_record,
            booking_line__contract_number__iexact=self.contract_number
        ).aggregate(total=Sum('tonnage_booked'))['total'] or 0
        return alloc.allocated_tonnage - total_booked


class BookingDetail(models.Model):
    """
    Individual booking/bill of lading detail.
    Multiple details can exist per contract line.
    """
    booking_line = models.ForeignKey(
        BookingLine,
        on_delete=models.CASCADE,
        related_name='details',
    )
    contract_number = models.CharField(
        max_length=100, blank=True, verbose_name="Contract Number",
        help_text="Denormalized from BookingLine for easier querying"
    )
    booking_number = models.CharField(max_length=100, verbose_name="Booking Number")
    bill_number = models.CharField(max_length=100, blank=True, verbose_name="Bill of Lading No.")
    tonnage_booked = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="Tonnage Booked (MT)"
    )
    file = models.FileField(
        upload_to='booking_files/',
        null=True, blank=True,
        verbose_name="Document",
        validators=[validate_pdf_file, validate_file_size_10mb]
    )

    class Meta:
        ordering = ['booking_number']
        verbose_name = "Booking Detail"
        verbose_name_plural = "Booking Details"

    def __str__(self):
        return f"{self.booking_number} — {self.bill_number}"

    def save(self, *args, **kwargs):
        # Auto-populate contract_number from booking_line if not set
        if self.booking_line and not self.contract_number:
            self.contract_number = self.booking_line.contract_number
        super().save(*args, **kwargs)


class BookingCorrection(models.Model):
    """
    Tracks correction requests from assigned officers to ebooking desk.
    Each correction round is saved with timestamp for full accountability.
    Eliminates paper waste from the correction cycle.
    """
    booking_detail = models.ForeignKey(
        BookingDetail,
        on_delete=models.CASCADE,
        related_name='corrections',
        verbose_name="Booking Detail"
    )
    correction_text = models.TextField(
        verbose_name="Correction Needed",
        help_text="Describe what needs to be corrected in the Bill of Lading"
    )
    attachment = models.FileField(
        upload_to='correction_attachments/',
        null=True,
        blank=True,
        verbose_name="Attachment",
        help_text="Optional: Attach scanned document or image showing the correction needed"
    )
    round_number = models.PositiveIntegerField(
        default=1,
        verbose_name="Correction Round",
        help_text="1st correction, 2nd correction, etc."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='booking_corrections_created',
        verbose_name="Officer"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    viewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Viewed At",
        help_text="When the ebooking desk viewed this correction"
    )

    class Meta:
        ordering = ['booking_detail', 'round_number']
        verbose_name = "Booking Correction"
        verbose_name_plural = "Booking Corrections"

    def __str__(self):
        return f"Correction #{self.round_number} for {self.booking_detail.booking_number}"


class CorrectionAttachment(models.Model):
    """
    Multiple file attachments for a single correction request.
    Supports multi-page Bill of Lading documents.
    """
    correction = models.ForeignKey(
        BookingCorrection,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name="Correction"
    )
    file = models.FileField(
        upload_to='correction_attachments/',
        verbose_name="File",
        help_text="Image or PDF file"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = "Correction Attachment"
        verbose_name_plural = "Correction Attachments"

    def __str__(self):
        return f"Attachment for {self.correction}"

    def save(self, *args, **kwargs):
        # NOTE: round_number is tracked on BookingCorrection, not on attachments.
        super().save(*args, **kwargs)
