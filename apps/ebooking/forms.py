from django import forms
from django.forms import formset_factory
from django.utils.html import escape
from .models import BookingRecord, BookingLine, BookingDetail


class BookingRecordForm(forms.ModelForm):
    """
    Form for creating/editing booking records.

    Fields:
    - sd_number: SD number (with auto-prefix support)
    - vessel: Vessel name
    - agent: Shipping line/agent
    - notes: Optional notes

    Security: Notes field sanitized to prevent XSS attacks
    """
    class Meta:
        model = BookingRecord
        fields = ['sd_number', 'vessel', 'agent', 'notes']
        widgets = {
            'sd_number': forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-mono',
                'id': 'id_sd_number_booking',
                'placeholder': 'e.g. SD100',
                'autocomplete': 'off',
            }),
            'vessel': forms.TextInput(attrs={
                'class': 'sdt-si-input',
                'placeholder': 'e.g. MSC IKARIA VI',
            }),
            'agent': forms.TextInput(attrs={
                'class': 'sdt-si-input',
                'placeholder': 'e.g. MSC, Cosco',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'sdt-si-textarea',
                'rows': 3,
                'placeholder': 'Optional notes about this booking...',
            }),
        }

    def clean_notes(self):
        """
        Sanitize notes field to prevent XSS attacks.

        Returns:
            Escaped notes string safe for HTML rendering
        """
        notes = self.cleaned_data.get('notes', '')
        return escape(notes) if notes else ''


class BookingDetailForm(forms.ModelForm):
    """
    Flat form for booking details with contract_number included.

    Each row represents one booking/bill entry with its contract.
    Used in dynamic formsets for multi-contract booking creation.

    Fields:
    - contract_number: Contract number for this booking
    - booking_number: Booking reference number
    - bill_number: Bill of Lading number
    - tonnage_booked: Tonnage in metric tons
    - file: Optional PDF document
    """
    contract_number = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'sdt-si-input sdt-si-mono booking-contract-input',
            'placeholder': 'e.g. NJ2604251911 PT',
            'autocomplete': 'off',
        })
    )

    class Meta:
        model = BookingDetail
        fields = ['booking_number', 'bill_number', 'tonnage_booked', 'file']
        widgets = {
            'booking_number': forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-mono',
                'placeholder': 'e.g. BKG-2025-001',
            }),
            'bill_number': forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-mono',
                'placeholder': 'e.g. BL-2025-001',
            }),
            'tonnage_booked': forms.NumberInput(attrs={
                'class': 'sdt-si-input sdt-si-num booking-tonnage-input',
                'step': '0.0001',
                'placeholder': '0',
            }),
            'file': forms.ClearableFileInput(attrs={'class': 'booking-line-file'}),
        }


# Flat formset for booking details (not nested)
# Each form includes contract_number + booking details
BookingDetailFormSet = formset_factory(
    BookingDetailForm,
    extra=1,
    can_delete=True
)
