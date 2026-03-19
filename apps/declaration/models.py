from django.db import models
from django.conf import settings
from django.db.models import Sum
from apps.core.validators import validate_pdf_file, validate_file_size_10mb


class Declaration(models.Model):
    """
    Declaration record for customs clearance of cocoa shipments.

    Created by the Declaration desk for each contract allocation within an SD.
    Tracks declaration numbers, tonnage declared, and supporting documents.
    Multiple declarations can be created for the same contract as long as total
    tonnage does not exceed allocated tonnage.

    Balance Tracking:
    - Each contract has allocated tonnage (from SDAllocation)
    - Multiple declarations can be created per contract
    - Balance = Allocated Tonnage - Sum of all declarations for that contract
    - System validates that total declared tonnage does not exceed allocated

    Auto-Linking:
    - When SD record is created, orphaned declarations with matching sd_number are linked
    - Agent and vessel auto-populated from SD record if available

    Relationships:
    - sd_record: ForeignKey to SDRecord (parent SD, nullable for orphaned declarations)
    - allocation: ForeignKey to SDAllocation (specific contract within SD)
    - created_by: ForeignKey to Account (declaration desk staff who created)
    - updated_by: ForeignKey to Account (last person to edit)

    Fields:
        sd_number: SD number (plain text, for orphaned declarations)
        allocation: Specific contract allocation within SD
        agent: Shipping agent (auto-populated from SD)
        vessel: Vessel name (auto-populated from SD)
        declaration_number: Customs declaration number
        contract_number: Contract number (from allocation)
        declaration_pdf: PDF document (max 10MB)
        tonnage: Tonnage declared in metric tons
        date: Declaration date (for calendar grouping)
        notes: Additional notes

    Example:
        >>> declaration = Declaration.objects.create(
        ...     sd_number='SD100',
        ...     allocation=allocation,
        ...     declaration_number='DEC2026001',
        ...     tonnage=Decimal('250.0000'),
        ...     created_by=user
        ... )
        >>> declaration.agent  # Auto-populated from SD record
        'MAERSK'
    """
    sd_number = models.CharField(max_length=100, verbose_name="SD Number")
    sd_record = models.ForeignKey(
        'operations.SDRecord',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='declarations',
    )
    allocation = models.ForeignKey(
        'operations.SDAllocation',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='declarations',
        verbose_name="Contract / Allocation",
    )
    agent = models.CharField(max_length=200, blank=True, verbose_name="Agent")
    vessel = models.CharField(max_length=200, blank=True, verbose_name="Vessel")
    declaration_number = models.CharField(max_length=100, verbose_name="Declaration Number")
    contract_number = models.CharField(max_length=100, blank=True, verbose_name="Contract Number")
    declaration_pdf = models.FileField(
        upload_to='declaration_docs/',
        null=True, blank=True,
        verbose_name="Declaration Document",
        validators=[validate_pdf_file, validate_file_size_10mb]
    )
    tonnage = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="Tonnage Declared (MT)"
    )
    notes = models.TextField(blank=True)

    # User-selected declaration date (used for calendar grouping)
    date = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='declarations_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='declarations_updated',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Declaration"
        verbose_name_plural = "Declarations"

    def __str__(self):
        return f"Declaration {self.declaration_number} — SD {self.sd_number}"

    def save(self, *args, **kwargs):
        """
        Auto-populate agent and vessel from linked SD record.

        If sd_record is linked and agent/vessel fields are empty,
        automatically populate them from the SD record for convenience.

        This ensures declaration records have complete information even
        when created before the SD record exists (orphaned declarations).
        """
        if self.sd_record and not self.agent:
            self.agent = self.sd_record.agent
        if self.sd_record and not self.vessel:
            self.vessel = self.sd_record.vessel_name
        super().save(*args, **kwargs)
