from django.db import models
from django.db.models import Sum
from django.conf import settings
from datetime import datetime
from simple_history.models import HistoricalRecords
from apps.core.validators import (
    validate_pdf_file, validate_excel_file,
    validate_file_size_10mb, validate_file_size_25mb
)


def get_current_crop_year_choices():
    """
    Returns crop year choices for dropdown.

    Logic:
    - Crop year starts every September
    - Always show current crop year + previous crop year (4 options total)
    - Format: YYYY/YYYY TYPE (e.g., 2025/2026 MC)

    Example (February 2026):
    - Current crop year: 2025/2026 (started Sept 2025)
    - Previous crop year: 2024/2025
    - Returns: 2024/2025 MC, 2024/2025 LC, 2025/2026 MC, 2025/2026 LC

    Example (September 2026):
    - Current crop year: 2026/2027 (just started)
    - Previous crop year: 2025/2026
    - Returns: 2025/2026 MC, 2025/2026 LC, 2026/2027 MC, 2026/2027 LC
    """
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    # Determine the current crop year based on September cutoff
    if current_month >= 9:  # September or later
        # We're in the new crop year that started this September
        current_crop_start = current_year
        current_crop_end = current_year + 1
    else:  # January to August
        # We're still in the crop year that started last September
        current_crop_start = current_year - 1
        current_crop_end = current_year

    # Previous crop year (one year before current)
    previous_crop_start = current_crop_start - 1
    previous_crop_end = current_crop_end - 1

    # Build choices: previous year first, then current year
    choices = [
        (f'{previous_crop_start}/{previous_crop_end} MC', f'{previous_crop_start}/{previous_crop_end} MC'),
        (f'{previous_crop_start}/{previous_crop_end} LC', f'{previous_crop_start}/{previous_crop_end} LC'),
        (f'{current_crop_start}/{current_crop_end} MC', f'{current_crop_start}/{current_crop_end} MC'),
        (f'{current_crop_start}/{current_crop_end} LC', f'{current_crop_start}/{current_crop_end} LC'),
    ]

    return choices


class Schedule(models.Model):
    """A daily loading schedule created by a manager."""
    date = models.DateField(unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='schedules_created'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Schedule — {self.date.strftime('%d %b %Y')}"


class ScheduleEntry(models.Model):
    """One SD line inside a daily schedule."""
    schedule = models.ForeignKey(
        Schedule, on_delete=models.CASCADE, related_name='entries')
    sd_number = models.CharField(max_length=100, verbose_name="SD Number")
    agent = models.CharField(max_length=200, verbose_name="Agent")
    tonnage = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="Tonnage (MT)")
    assigned_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='schedule_entries'
    )
    notes = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['sd_number']

    def __str__(self):
        return f"{self.sd_number} — {self.agent} ({self.tonnage} MT)"


class SDRecord(models.Model):
    """
    Full SD record created by the Operations desk.
    One SD can have multiple contract allocations (SDAllocation).
    """

    # Core identifiers
    sd_number = models.CharField(
        max_length=100, unique=True, verbose_name="SD Number")
    date_of_entry = models.DateField(
        null=True, blank=True, verbose_name="Date of Entry")
    si_ref = models.CharField(
        max_length=100, blank=True, verbose_name="SI Ref No.")
    vessel_name = models.CharField(max_length=200, verbose_name="Vessel Name")
    eta = models.DateField(null=True, blank=True, verbose_name="ETA")

    # Totals (sum of all allocations)
    tonnage = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="Total Tonnage (MT)")
    buyer = models.CharField(max_length=200, blank=True, verbose_name="Buyer")
    agent = models.CharField(max_length=200, verbose_name="Agent")

    # Shipping details - crop_year uses dynamic choices
    crop_year = models.CharField(
        max_length=50, blank=True, verbose_name="Crop Year")
    shipment_period = models.CharField(
        max_length=100, blank=True, verbose_name="Shipment Period")
    PORT_CHOICES = [
        ('TAKORADI', 'Takoradi'),
        ('TEMA', 'Tema'),
        ('KUMASI', 'Kumasi'),
    ]
    port_of_loading = models.CharField(
        max_length=100, default="TEMA", choices=PORT_CHOICES)
    port_of_discharge = models.CharField(max_length=200, blank=True)
    container_size = models.CharField(
        max_length=50, blank=True, verbose_name="Container Size")
    bags_per_container = models.PositiveIntegerField(null=True, blank=True)

    LOADING_TYPE_CHOICES = [
        ('STRAIGHT', 'Straight'),
        ('BULK', 'Bulk'),
    ]
    loading_type = models.CharField(
        max_length=20, choices=LOADING_TYPE_CHOICES, blank=True, verbose_name="Loading Type")

    # Balance tracking
    opening_balance = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Opening Balance (MT)")
    closing_balance = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Closing Balance (MT)")
    tonnage_loaded = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Tonnage Loaded (MT)")

    # Stock allocation summary (free text kept for notes)
    stock_allocation_notes = models.TextField(
        blank=True, verbose_name="Additional Allocation Notes")

    # Documents
    sd_document = models.FileField(
        upload_to='sd_documents/',
        null=True, blank=True,
        verbose_name="SD Document (PDF)",
        validators=[validate_pdf_file, validate_file_size_10mb]
    )
    container_list = models.FileField(
        upload_to='container_lists/',
        null=True, blank=True,
        verbose_name="Container List (Excel)",
        validators=[validate_excel_file, validate_file_size_25mb]
    )

    # Status
    is_complete = models.BooleanField(
        default=False, verbose_name="Fully Loaded / Complete")

    # Metadata
    officer_assigned = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sd_records_assigned',
        verbose_name="Officer Assigned"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='sd_records_created'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sd_records_updated'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        verbose_name = "SD Record"
        verbose_name_plural = "SD Records"

    def __str__(self):
        return f"SD {self.sd_number} — {self.vessel_name}"

    @property
    def balance_remaining(self):
        if self.tonnage_loaded is not None:
            return max(self.tonnage - self.tonnage_loaded, 0)
        return self.tonnage

    @property
    def total_bags(self):
        return self.containers.aggregate(
            total=models.Sum('bag_count')
        )['total'] or 0

    @property
    def container_count(self):
        return self.containers.count()

    @property
    def total_allocated_tonnage(self):
        return self.allocations.aggregate(
            total=models.Sum('allocated_tonnage')
        )['total'] or 0

    @property
    def schedule_assigned_officer(self):
        """Get the officer assigned to this SD from the schedule."""
        from apps.operations.models import ScheduleEntry
        entry = ScheduleEntry.objects.filter(
            sd_number__iexact=self.sd_number
        ).select_related('assigned_officer').first()
        return entry.assigned_officer if entry else None

    @property
    def has_bookings(self):
        """Check if any booking records exist for this SD."""
        from apps.ebooking.models import BookingRecord
        return BookingRecord.objects.filter(sd_number__iexact=self.sd_number).exists()

    @property
    def has_declarations(self):
        """Check if any declaration records exist for this SD."""
        from apps.declaration.models import Declaration
        return Declaration.objects.filter(sd_number__iexact=self.sd_number).exists()

    @property
    def has_evacuations(self):
        """Check if any evacuation records exist for this SD."""
        from apps.evacuation.models import EvacuationLine
        return EvacuationLine.objects.filter(sd_number__iexact=self.sd_number).exists()

    @property
    def has_tallies(self):
        """Check if any approved tallies exist for this SD."""
        from apps.tally.models import TallyInfo
        return TallyInfo.objects.filter(
            sd_number__iexact=self.sd_number,
            status='APPROVED'
        ).exists()

    @property
    def approved_tallies(self):
        """Get all approved tallies for this SD."""
        from apps.tally.models import TallyInfo
        return TallyInfo.objects.filter(
            sd_number__iexact=self.sd_number,
            status='APPROVED'
        ).order_by('-approved_at')

    @property
    def all_bookings(self):
        """Get all booking records for this SD."""
        from apps.ebooking.models import BookingRecord
        return BookingRecord.objects.filter(sd_number__iexact=self.sd_number).order_by('-created_at')

    @property
    def all_declarations(self):
        """Get all declaration records for this SD."""
        from apps.declaration.models import Declaration
        return Declaration.objects.filter(sd_number__iexact=self.sd_number).order_by('-created_at')

    @property
    def all_evacuations(self):
        """Get all evacuation records for this SD."""
        from apps.evacuation.models import EvacuationLine
        return EvacuationLine.objects.filter(sd_number__iexact=self.sd_number).select_related('evacuation').order_by('-evacuation__date')


class SDAllocation(models.Model):
    """
    One contract/allocation line under an SD.
    A single SD can have A, B, C, D... allocations each with
    their own contract number, MK number, and tonnage.
    """
    sd_record = models.ForeignKey(
        SDRecord, on_delete=models.CASCADE, related_name='allocations')
    allocation_label = models.CharField(
        max_length=10, blank=True, verbose_name="Label (A, B, C…)")
    contract_number = models.CharField(
        max_length=100, verbose_name="Contract Number")
    mk_number = models.CharField(max_length=100, verbose_name="MK No.")
    allocated_tonnage = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="Allocated Tonnage (MT)")
    tonnage_loaded = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True,
        verbose_name="Tonnage Loaded (MT)", default=0)
    buyer = models.CharField(max_length=200, blank=True, verbose_name="Buyer")
    si_ref = models.CharField(max_length=100, blank=True, verbose_name="SI Ref")
    agent = models.CharField(max_length=200, blank=True,
                             verbose_name="Agent / Stock")
    cocoa_type = models.CharField(
        max_length=100, blank=True, verbose_name="Cocoa Type")
    notes = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['allocation_label', 'contract_number']

    def __str__(self):
        label = f"{self.allocation_label} – " if self.allocation_label else ""
        return f"{label}{self.contract_number} / MK {self.mk_number} ({self.allocated_tonnage} MT)"


class SDContainer(models.Model):
    """
    Individual container loaded under an SD.
    Can be linked to a specific allocation (contract) and
    also linked back to the originating TallyContainer via tally_container_id.
    Container number + seal number are auto-populated when a
    tally whose sd_number matches this SD is saved.
    """
    sd_record = models.ForeignKey(
        SDRecord, on_delete=models.CASCADE, related_name='containers')
    allocation = models.ForeignKey(
        SDAllocation, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='containers',
        verbose_name="Contract / Allocation"
    )

    container_number = models.CharField(
        max_length=100, verbose_name="Container No. (C/NO)")
    seal_number = models.CharField(
        max_length=100, blank=True, verbose_name="Seal No.")
    bag_count = models.PositiveIntegerField(
        default=400, verbose_name="No. of Bags")
    gross_weight = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Gross Weight (kg)")
    net_weight = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Net Weight (kg)")
    loading_date = models.DateField(
        null=True, blank=True, verbose_name="Date Loaded")
    balance_after = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Balance After Loading (MT)")

    # Link back to the tally that created this row (set automatically)
    tally_container_id = models.PositiveIntegerField(null=True, blank=True, db_index=True,
                                                     verbose_name="Source TallyContainer ID")
    from_tally = models.BooleanField(
        default=False, verbose_name="Auto-added from Tally")

    history = HistoricalRecords()

    class Meta:
        ordering = ['loading_date', 'container_number']
        # Prevent the same tally container being added twice
        unique_together = [['sd_record', 'tally_container_id']]

    def __str__(self):
        return f"{self.container_number} — Seal: {self.seal_number or '—'}"


class ContainerListUpload(models.Model):
    """
    An Excel container list file attached to an SD, per contract/allocation.
    Operations desk uploads these; visible to all staff.
    """
    sd_record = models.ForeignKey(
        SDRecord, on_delete=models.CASCADE, related_name='container_list_uploads')
    allocation = models.ForeignKey(
        SDAllocation, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='container_list_uploads',
        verbose_name="Contract / Allocation"
    )
    contract_number = models.CharField(
        max_length=100, blank=True, verbose_name="Contract Number")
    tonnage = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="Tonnage (MT)")
    excel_file = models.FileField(
        upload_to='container_lists/',
        verbose_name="Container List (Excel)",
        validators=[validate_excel_file, validate_file_size_25mb]
    )
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='container_lists_uploaded')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Container List Upload"
        verbose_name_plural = "Container List Uploads"

    def __str__(self):
        return f"Container List — {self.sd_record.sd_number} / {self.contract_number or 'General'}"

    def filename(self):
        import os
        return os.path.basename(self.excel_file.name) if self.excel_file else ''


class SDClerk(models.Model):
    """A clerk/tally officer who worked on a particular SD."""
    sd_record = models.ForeignKey(
        SDRecord, on_delete=models.CASCADE, related_name='clerks')
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sd_clerk_entries'
    )
    officer_name = models.CharField(
        max_length=200, blank=True, verbose_name="Clerk Name")
    tally_reference = models.CharField(
        max_length=100, blank=True, verbose_name="Tally Reference")
    date_worked = models.DateField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['date_worked', 'officer_name']

    def __str__(self):
        name = self.officer_name or (
            str(self.officer) if self.officer else "Unknown")
        return f"{name} on SD {self.sd_record.sd_number}"

    def save(self, *args, **kwargs):
        if self.officer and not self.officer_name:
            self.officer_name = f"{self.officer.first_name} {self.officer.last_name}".strip(
            )
        super().save(*args, **kwargs)


class DailyPort(models.Model):
    """Daily port report — one per date, with PDF/Excel uploads."""
    date = models.DateField(unique=True)
    pdf_file = models.FileField(
        upload_to='daily_port/',
        verbose_name="PDF Document",
        validators=[validate_pdf_file, validate_file_size_10mb]
    )
    excel_file = models.FileField(
        upload_to='daily_port/',
        verbose_name="Excel File",
        validators=[validate_excel_file, validate_file_size_10mb]
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='daily_ports_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-date']
        verbose_name = "Daily Port"
        verbose_name_plural = "Daily Ports"

    def __str__(self):
        return f"Daily Port — {self.date.strftime('%d %b %Y')}"


class WorkProgram(models.Model):
    """
    Work Program - Document prepared each day stating tonnages of cocoa to be loaded.
    Operations desk creates and manages these documents.
    """
    date = models.DateField(
        verbose_name="Program Date",
        help_text="Date for this work program"
    )
    pdf_file = models.FileField(
        upload_to='work_programs/',
        verbose_name="Work Program PDF",
        help_text="Upload the work program document (PDF)",
        validators=[validate_pdf_file, validate_file_size_10mb]
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Additional notes or comments"
    )

    # Audit trail
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='work_programs_created',
        verbose_name="Created By"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='work_programs_updated',
        verbose_name="Updated By"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ['-date']
        verbose_name = "Work Program"
        verbose_name_plural = "Work Programs"
        unique_together = ['date']  # One work program per date

    def __str__(self):
        return f"Work Program — {self.date.strftime('%d %b %Y')}"
