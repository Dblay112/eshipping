from django.db import models
from django.conf import settings
from apps.core.validators import validate_excel_file, validate_file_size_25mb


SHIFT_CHOICES = [
    ('DAY', 'Day Shift'),
    ('NIGHT', 'Night Shift'),
]


class Evacuation(models.Model):
    """
    Daily evacuation record tracking container movements to port.

    One record per date + shift combination (Day or Night).
    Contains multiple evacuation lines, each representing one SD's containers.

    Features:
    - Date and shift-based organization
    - Multiple SD lines per evacuation
    - Optional notes for shift details
    - Audit trail with created_by/updated_by

    Relationships:
    - Has many: EvacuationLine (SD-level container details)
    - Belongs to: Account (created_by, updated_by)

    Fields:
        date: Evacuation date
        shift: Day or Night shift
        notes: Optional shift notes (vessel changes, issues, etc.)
        created_by: User who created the record
        updated_by: User who last edited the record
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> evacuation = Evacuation.objects.create(
        ...     date='2026-03-19',
        ...     shift='DAY',
        ...     notes='MV NAVIOS MAGNOLIA - 24x40 to MPS T3',
        ...     created_by=user
        ... )
        >>> evacuation.total_lines
        0
    """
    date = models.DateField(verbose_name="Evacuation Date")
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES, verbose_name="Shift")
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='evacuations_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='evacuations_updated',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'shift']
        verbose_name = "Evacuation"
        verbose_name_plural = "Evacuations"

    def __str__(self):
        return f"Evacuation {self.date} — {self.get_shift_display()}"

    @property
    def total_lines(self):
        """
        Total number of SD lines in this evacuation.

        Returns:
            int: Count of EvacuationLine records linked to this evacuation
        """
        return self.lines.count()


class EvacuationLine(models.Model):
    """
    Individual SD line within an evacuation record.

    Each line represents one SD's containers being evacuated in a shift.
    Multiple SDs can be evacuated in the same shift.

    Auto-Linking:
    - When SD record is created, orphaned lines with matching sd_number are linked
    - Vessel and agent can be auto-populated from SD record if available

    Features:
    - SD number tracking (plain text for orphaned records)
    - Optional link to SDRecord (when SD exists)
    - Vessel and agent fields (editable)
    - Container list file upload (Excel, max 25MB)

    Relationships:
    - Belongs to: Evacuation (parent shift record)
    - Belongs to: SDRecord (optional, for auto-linking)
    - Has many: EvacuationContainer (individual container status)

    Fields:
        evacuation: Parent evacuation record
        sd_number: SD number (plain text)
        sd_record: Optional link to SDRecord (for auto-linking)
        vessel: Vessel name
        agent: Shipping agent
        container_file: Excel file with container list

    Example:
        >>> line = EvacuationLine.objects.create(
        ...     evacuation=evacuation,
        ...     sd_number='SD371',
        ...     vessel='MV NAVIOS MAGNOLIA',
        ...     agent='COSCO'
        ... )
        >>> line.sd_record  # None until SD371 is created
        None
    """
    evacuation = models.ForeignKey(
        Evacuation,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    sd_number = models.CharField(max_length=100, verbose_name="SD Number")
    sd_record = models.ForeignKey(
        'operations.SDRecord',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='evacuation_lines',
    )
    vessel = models.CharField(max_length=200, blank=True, verbose_name="Vessel Name")
    agent = models.CharField(max_length=200, blank=True, verbose_name="Agent")
    container_file = models.FileField(
        upload_to='evacuation_files/',
        null=True, blank=True,
        verbose_name="Container List File",
        validators=[validate_excel_file, validate_file_size_25mb]
    )

    class Meta:
        ordering = ['sd_number']
        verbose_name = "Evacuation Line"
        verbose_name_plural = "Evacuation Lines"

    def __str__(self):
        return f"SD {self.sd_number} — {self.evacuation}"


class EvacuationContainer(models.Model):
    """
    Individual container tracked under an evacuation line.

    Tracks status of each container (Lifted or Failed) for detailed reporting.
    Multiple containers can be tracked per evacuation line.

    Features:
    - Container number tracking
    - Status tracking (LIFTED or FAILED)
    - Linked to parent evacuation line

    Relationships:
    - Belongs to: EvacuationLine (parent SD line)

    Fields:
        evacuation_line: Parent evacuation line
        container_number: Container number (e.g., OOCU6341535)
        status: LIFTED (successfully evacuated) or FAILED (appointment issue)

    Example:
        >>> container = EvacuationContainer.objects.create(
        ...     evacuation_line=line,
        ...     container_number='OOCU6341535',
        ...     status='FAILED'
        ... )
        >>> container.get_status_display()
        'Failed'
    """
    STATUS = [
        ('LIFTED', 'Lifted'),
        ('FAILED', 'Failed'),
    ]
    evacuation_line = models.ForeignKey(
        EvacuationLine,
        on_delete=models.CASCADE,
        related_name='containers',
    )
    container_number = models.CharField(max_length=100, verbose_name="Container Number")
    status = models.CharField(max_length=10, choices=STATUS, verbose_name="Status")


    class Meta:
        ordering = ['container_number']
        verbose_name = "Evacuation Container"
        verbose_name_plural = "Evacuation Containers"

    def __str__(self):
        return f"{self.container_number} — {self.status}"
