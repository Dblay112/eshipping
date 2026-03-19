from django.db import models
from django.conf import settings
from apps.accounts.models import LOCATION_CHOICES
from apps.core.validators import validate_image_file, validate_file_size_5mb


SUPERINTENDANT_CHOICES = (
    ("NONE", "NONE"),
    ("JLB", "JLB"),
    ("CWT", "CWT"),
    ("CWT + JLB", "CWT + JLB"),
)

TALLY_TYPE_CHOICES = (
    ("BULK", "BULK_LOADING"),
    ("STRAIGHT_20FT", "STRAIGHT_20FT"),
    ("STRAIGHT_40FT", "STRAIGHT_40FT"),
    ("JAPAN_STRAIGHT_40FT", "JAPAN_STRAIGHT_40FT"),
)

LOADING_TYPE = (
    ("STRAIGHT", "STRAIGHT"),
    ("BULK", "BULK"),
)

STRAIGHT_TYPE_CHOICES = (
    ("BULK", "BULK"),
    ("STRAIGHT_20FT", "STRAIGHT_20FT"),
    ("STRAIGHT_40FT", "STRAIGHT_40FT"),
    ("JAPAN_STRAIGHT_40FT", "JAPAN_STRAIGHT_40FT"),
)

TALLY_STATUS_CHOICES = [
    ('DRAFT', 'Draft'),
    ('PENDING_APPROVAL', 'Pending Approval'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
]


class Terminal(models.Model):
    """
    Terminal (warehouse) model for cocoa storage and loading operations.

    Terminals are physical warehouses in Tema where cocoa is stored before loading.
    Each terminal has assigned supervisors who approve tallies for that terminal.

    Standard terminals in Tema:
    - CWC
    - COMMODITY
    - DZATA BU
    - OTHER PRODUCE
    - ARMAJARO GLOBAL ANNEX

    Relationships:
    - supervisors: Many-to-many with Account (staff who can approve tallies)
    - tallies: One-to-many with TallyInfo (tallies created at this terminal)

    Fields:
        name: Terminal name (unique)
        location: Location choice (default: TEMA)
        supervisors: Staff members who supervise this terminal

    Example:
        >>> terminal = Terminal.objects.create(name='COMMODITY', location='TEMA')
        >>> terminal.supervisors.add(supervisor_user)
        >>> terminal.tallies.count()
        42
    """
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=30, choices=LOCATION_CHOICES, default='TEMA')
    supervisors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='supervised_terminals',
    )

    class Meta:
        verbose_name = "Terminal"
        verbose_name_plural = "Terminals"

    def __str__(self):
        return f"{self.name} ({self.get_location_display()})"


class TallyInfo(models.Model):
    """
    Tally record for cocoa loading operations.

    A tally is a detailed record of cocoa loading into containers. Created by clerks
    during loading operations and approved by terminal supervisors. Each tally tracks
    containers, bags, tonnage, and personnel involved.

    Tally Types:
    - BULK: Loose bags loaded into containers at terminal
    - STRAIGHT_20FT: Pre-stuffed 20-foot containers
    - STRAIGHT_40FT: Pre-stuffed 40-foot containers
    - JAPAN_STRAIGHT_40FT: Japan-specific 40-foot containers with seller codes

    Approval Workflow:
    - DRAFT: Initial creation state
    - PENDING_APPROVAL: Submitted to supervisor for review
    - APPROVED: Supervisor approved (data syncs to SD record)
    - REJECTED: Supervisor rejected (clerk can edit and resubmit)

    Auto-Linking:
    - When SD record is created, orphaned tallies with matching sd_number are linked
    - Tally containers sync to SD record when approved

    Relationships:
    - created_by: ForeignKey to Account (clerk who created tally)
    - updated_by: ForeignKey to Account (last person to edit)
    - approved_by: ForeignKey to Account (supervisor who approved)
    - sd_record: ForeignKey to SDRecord (linked SD, nullable for orphaned tallies)
    - terminal: ForeignKey to Terminal (where loading occurred)
    - containers: One-to-many with TallyContainer (container details)
    - recall_requests: One-to-many with RecallRequest (recall history)

    Fields:
        tally_number: Unique auto-generated number (YYYYMMDD + sequence)
        tally_type: Type of loading operation
        crop_year: Cocoa crop year (e.g., "2024/2025 MC")
        sd_number: SD number (plain text, for orphaned tallies)
        mk_number: Mark number
        vessel: Vessel name
        destination: Port of discharge
        loading_date: Date of loading operation
        total_bags: Total bags loaded
        total_tonnage: Total tonnage loaded
        status: Approval status (DRAFT, PENDING_APPROVAL, APPROVED, REJECTED)
        expected_bags: Expected bags (BULK only)
        actual_bags: Actual bags loaded (BULK only)
        bags_saved: Difference between expected and actual (BULK only)
        seller_codes: Seller codes (JAPAN only)
        color_tag_entries: Color tag entries (JAPAN only)

    Example:
        >>> tally = TallyInfo.objects.create(
        ...     tally_number=202603191,
        ...     tally_type='BULK',
        ...     sd_number='SD100',
        ...     vessel='MSC IKARIA VI',
        ...     created_by=clerk_user
        ... )
        >>> tally.status
        'DRAFT'
        >>> tally.submit()  # Changes to PENDING_APPROVAL
        >>> tally.approve(supervisor_user)  # Changes to APPROVED
    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='tallies', null=True, blank=True)
    tally_number = models.PositiveBigIntegerField(unique=True)
    tally_type = models.CharField(max_length=30, choices=TALLY_TYPE_CHOICES)

    produce = models.CharField(max_length=100, default="RAW COCOA BEANS")

    crop_year = models.CharField(max_length=30)

    # Legacy plain-text SD number field (kept for backward compatibility)
    sd_number = models.CharField(max_length=20)
    # New FK to SDRecord model
    sd_record = models.ForeignKey(
        'operations.SDRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tallies',
        verbose_name='Linked SD Record'
    )

    mk_number = models.CharField(max_length=20)

    agent = models.CharField(max_length=100, blank=True, default="")

    vessel = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)

    # Legacy plain-text terminal field (kept for backward compatibility)
    terminal_name = models.CharField(max_length=50, blank=True, default="")
    # New FK to Terminal model
    terminal = models.ForeignKey(
        Terminal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tallies',
    )

    loading_type = models.CharField(
        max_length=20, blank=True, null=True, choices=LOADING_TYPE)
    straight_type = models.CharField(
        null=True, blank=True, choices=STRAIGHT_TYPE_CHOICES)
    loading_date = models.DateField()
    marks_and_numbers = models.CharField(max_length=100)

    cocoa_type = models.CharField(max_length=100, blank=True, default="")

    superintendent_type = models.CharField(
        max_length=20, choices=SUPERINTENDANT_CHOICES, default="NONE")
    superintendent_name = models.JSONField(default=list, blank=True)
    clerk_name = models.JSONField(default=list)

    dry_bags = models.CharField(null=True, blank=True)

    total_bags = models.PositiveIntegerField(default=0)
    total_tonnage = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True)

    expected_bags = models.PositiveIntegerField(null=True, blank=True)
    actual_bags = models.PositiveIntegerField(null=True, blank=True)
    bags_saved = models.IntegerField(default=0)

    seller_codes = models.JSONField(default=list, blank=True)
    color_tag_entries = models.JSONField(default=list, blank=True)

    date_created = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tallies_updated',
        verbose_name='Last Updated By'
    )
    updated_at = models.DateTimeField(auto_now=True)

    # Approval workflow
    status = models.CharField(
        max_length=20, choices=TALLY_STATUS_CHOICES, default='DRAFT')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_tallies',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    @property
    def can_be_recalled(self):
        """Check if tally can be recalled (approved within last 48 hours)."""
        if not self.approved_at or self.status != 'APPROVED':
            return False
        from django.utils import timezone
        from datetime import timedelta
        time_since_approval = timezone.now() - self.approved_at
        return time_since_approval < timedelta(hours=48)

    class Meta:
        verbose_name = "Tally"
        verbose_name_plural = "TALLIES"

    def save(self, *args, **kwargs):
        if self.tally_type == "BULK":
            if self.expected_bags is not None and self.actual_bags is not None:
                self.bags_saved = self.expected_bags - self.actual_bags
            else:
                self.bags_saved = 0
        super().save(*args, **kwargs)

    def __str__(self):
        first_clerk = ""
        if isinstance(self.clerk_name, list) and self.clerk_name:
            first_clerk = str(self.clerk_name[0])
        return f"{self.tally_number} {first_clerk}"


class TallyContainer(models.Model):
    """
    Container details for a tally record.

    Each tally has multiple containers with their specific details (number, seal,
    bags, tonnage). Container data varies by tally type:

    BULK Tallies:
    - bags_cut: Number of bags loaded into container
    - tonnage: Actual tonnage measured

    STRAIGHT Tallies (20ft, 40ft, Japan):
    - bags: Number of bags in pre-stuffed container
    - tonnage: Calculated from bags (bags / 16) or manually entered

    Relationships:
    - tally: ForeignKey to TallyInfo (parent tally record)

    Fields:
        container_number: Container identification number
        seal_number: Seal number for security
        tonnage: Tonnage in metric tons
        bags_cut: Bags cut/loaded (BULK only)
        bags: Total bags in container (STRAIGHT only)

    Example:
        >>> container = TallyContainer.objects.create(
        ...     tally=tally,
        ...     container_number='TCLU1234567',
        ...     seal_number='ABC123',
        ...     bags=320,
        ...     tonnage=Decimal('20.000')
        ... )
    """
    tally = models.ForeignKey(
        TallyInfo, on_delete=models.CASCADE, related_name="containers")
    container_number = models.CharField(max_length=30)
    seal_number = models.CharField(max_length=30)
    tonnage = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True)
    bags_cut = models.PositiveIntegerField(null=True, blank=True)
    bags = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "Container"
        verbose_name_plural = "Containers"

    def __str__(self):
        return f"{self.tally.tally_number}"


RECALL_REQUEST_STATUS = (
    ('PENDING', 'Pending Operations Approval'),
    ('APPROVED', 'Approved - Tally Recalled'),
    ('REJECTED', 'Rejected by Operations'),
)


class RecallRequest(models.Model):
    """Track recall requests from supervisors to operations desk."""
    tally = models.ForeignKey(
        TallyInfo,
        on_delete=models.CASCADE,
        related_name='recall_requests'
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='recall_requests_made',
        help_text='Supervisor who requested the recall'
    )
    reason = models.TextField(
        help_text='Reason for requesting recall'
    )
    status = models.CharField(
        max_length=20,
        choices=RECALL_REQUEST_STATUS,
        default='PENDING'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recall_requests_approved',
        help_text='Operations staff who approved/rejected the request'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    operations_notes = models.TextField(
        blank=True,
        help_text='Notes from operations desk when processing request'
    )

    class Meta:
        verbose_name = "Recall Request"
        verbose_name_plural = "Recall Requests"
        ordering = ['-created_at']

    def __str__(self):
        return f"Recall Request for Tally {self.tally.tally_number} by {self.requested_by.staff_number}"
