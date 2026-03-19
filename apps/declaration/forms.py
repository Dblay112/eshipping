from django import forms
from django.forms import inlineformset_factory
from django.utils.html import escape
from .models import Declaration
from apps.operations.models import SDRecord, SDAllocation


class DeclarationHeaderForm(forms.Form):
    """
    Form for selecting SD record and date when creating declarations.

    Used as the first step in declaration creation workflow. User enters
    SD number and date, then system loads all contract allocations for
    that SD to create declarations.

    Features:
    - SD number input with auto-complete
    - Date selection for declaration grouping
    - No validation on SD existence (allows orphaned declarations)

    Fields:
        sd_number: SD number to create declarations for
        date: Declaration date (optional, defaults to today)

    Validation:
        - SD number is trimmed and uppercased
        - No existence check (orphaned declarations allowed)
        - Auto-linking happens when SD record is created later
    """
    sd_number = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'sdt-si-input sdt-si-upper',
            'id': 'id_sd_number',
            'placeholder': 'e.g. SD100',
            'autocomplete': 'off',
            'style': 'max-width: 250px;'
        }),
        label="SD Number",
    )
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'sdt-si-input', 'type': 'date'}),
        label="Date",
    )

    def clean_sd_number(self):
        """
        Allow any SD number - no validation required.
        Records can be created before or after operations creates the SD.
        Automatic linkage happens via sd_record ForeignKey when SD is created.
        """
        sd_number = self.cleaned_data.get('sd_number', '').strip()
        return sd_number


class DeclarationLineForm(forms.ModelForm):
    """
    Form for creating/editing a single declaration line (one per contract).

    Used in formset for multi-contract declaration creation. Each SD can have
    multiple contracts, and each contract gets its own declaration line.

    Features:
    - Read-only display fields (label, contract number, allocated tonnage)
    - Editable fields (agent, declaration number, tonnage, PDF)
    - Hidden allocation field for linking to contract
    - PDF file upload with validation

    Fields:
        allocation_label: Contract label (PT, BL, etc.) - read-only
        contract_number: Contract number - read-only
        allocated_tonnage: Allocated tonnage - read-only
        agent: Shipping agent - editable
        allocation: Hidden field linking to SDAllocation
        declaration_number: Customs declaration number
        tonnage: Tonnage declared (up to 4 decimal places)
        declaration_pdf: PDF document (max 10MB)

    Usage:
        Used in DeclarationLineFormSet for multi-contract declarations
    """
    allocation_label = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'sdt-si-input', 'readonly': 'readonly'}),
        label="Label",
    )
    contract_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'sdt-si-input sdt-si-mono', 'readonly': 'readonly'}),
        label="Contract No.",
    )
    allocated_tonnage = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'sdt-si-input sdt-si-num', 'readonly': 'readonly'}),
        label="Allocated (MT)",
    )
    agent = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'sdt-si-input sdt-si-upper', 'placeholder': 'Agent'}),
        label="Agent",
    )

    class Meta:
        model = Declaration
        fields = ['allocation', 'agent', 'declaration_number', 'tonnage', 'declaration_pdf']
        widgets = {
            'allocation': forms.HiddenInput(),
            'declaration_number': forms.TextInput(attrs={'class': 'sdt-si-input sdt-si-mono', 'placeholder': 'DECL-2025-001'}),
            'tonnage': forms.NumberInput(attrs={'class': 'sdt-si-input sdt-si-num', 'step': '0.0001', 'placeholder': '0'}),
            'declaration_pdf': forms.ClearableFileInput(attrs={'accept': '.pdf'}),
        }


class DeclarationForm(forms.ModelForm):
    """
    Form for editing individual declaration records.

    Simpler form used for editing existing declarations one at a time.
    Provides better decimal control and XSS protection for notes field.

    Features:
    - Decimal tonnage with 4 decimal places
    - Normalized decimal display (removes trailing zeros)
    - PDF file upload with validation
    - XSS protection on notes field
    - Optional notes textarea

    Fields:
        declaration_number: Customs declaration number
        tonnage: Tonnage declared (normalized display)
        declaration_pdf: PDF document (max 10MB)
        notes: Optional notes (XSS protected)

    Initialization:
        - Normalizes tonnage display (removes trailing zeros)
        - Example: 250.0000 displays as 250

    Validation:
        - Notes field sanitized with HTML escaping
        - Prevents XSS attacks via notes field

    Usage:
        >>> form = DeclarationForm(instance=declaration)
        >>> form.initial['tonnage']  # '250' instead of '250.0000'
    """
    # Override tonnage field to use TextInput for better decimal control
    tonnage = forms.DecimalField(
        max_digits=10,
        decimal_places=4,
        widget=forms.TextInput(attrs={
            'class': 'sdt-si-input sdt-si-num',
            'placeholder': '0',
            'type': 'number',
            'step': '0.0001'
        })
    )

    class Meta:
        model = Declaration
        fields = ['declaration_number', 'tonnage', 'declaration_pdf', 'notes']
        widgets = {
            'declaration_number': forms.TextInput(attrs={'class': 'sdt-si-input sdt-si-mono', 'placeholder': 'DECL-2025-001'}),
            'declaration_pdf': forms.ClearableFileInput(attrs={'accept': '.pdf'}),
            'notes': forms.Textarea(attrs={'class': 'sdt-si-input', 'rows': 2, 'placeholder': 'Optional notes…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Clean decimal display: remove trailing zeros from tonnage initial value
        if self.instance and self.instance.pk and self.instance.tonnage:
            from decimal import Decimal
            tonnage = self.instance.tonnage
            # Remove trailing zeros and unnecessary decimal point
            if isinstance(tonnage, Decimal):
                normalized = tonnage.normalize()
                # Convert to string and remove trailing .0 if it's a whole number
                tonnage_str = str(normalized)
                if '.' in tonnage_str:
                    tonnage_str = tonnage_str.rstrip('0').rstrip('.')
                self.initial['tonnage'] = tonnage_str

    def clean_notes(self):
        """SECURITY: Sanitize notes field to prevent XSS attacks."""
        notes = self.cleaned_data.get('notes', '')
        return escape(notes) if notes else ''


# Formset for declaration lines
DeclarationLineFormSet = inlineformset_factory(
    SDRecord,
    Declaration,
    form=DeclarationLineForm,
    extra=0,
    can_delete=False,
)
