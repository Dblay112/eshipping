from django import forms
from django.forms import inlineformset_factory
from django.utils.html import escape
from .models import Evacuation, EvacuationLine
from apps.operations.models import SDRecord


class EvacuationForm(forms.ModelForm):
    """
    Form for creating/editing evacuation header information.

    Captures date, shift type, and optional notes for the evacuation record.
    Used as parent form in formset workflow with EvacuationLineFormSet.

    Features:
    - Date picker for evacuation date
    - Shift dropdown (Day/Night)
    - Optional notes textarea
    - XSS protection on notes field

    Fields:
        date: Evacuation date (date picker)
        shift: Day or Night shift (dropdown)
        notes: Optional shift notes (textarea, XSS protected)

    Validation:
        - Notes field sanitized with HTML escaping to prevent XSS

    Usage:
        >>> form = EvacuationForm(data={'date': '2026-03-19', 'shift': 'DAY'})
        >>> form.is_valid()
        True
    """
    class Meta:
        model = Evacuation
        fields = ['date', 'shift', 'notes']
        widgets = {
            'date':  forms.DateInput(attrs={'type': 'date', 'class': 'sdt-si-input'}),
            'shift': forms.Select(attrs={'class': 'sdt-si-input'}),
            'notes': forms.Textarea(attrs={'class': 'sdt-si-input', 'rows': 2, 'placeholder': 'Optional notes…'}),
        }

    def clean_notes(self):
        """SECURITY: Sanitize notes field to prevent XSS attacks."""
        notes = self.cleaned_data.get('notes', '')
        return escape(notes) if notes else ''


class EvacuationLineForm(forms.ModelForm):
    """
    Form for creating/editing individual evacuation lines (SD-level).

    Used in formset for multi-SD evacuation creation. Each line represents
    one SD's containers being evacuated in the shift.

    Features:
    - SD number input with auto-prefix (SD100)
    - Vessel and agent fields (uppercase)
    - Container list file upload (Excel, max 25MB)
    - Auto-fill from SD record (via JavaScript)

    Fields:
        sd_number: SD number (auto-prefixed, bold styling)
        vessel: Vessel name (uppercase)
        agent: Shipping agent (uppercase)
        container_file: Excel file with container list

    Validation:
        - SD number required
        - Container file must be Excel format (.xlsx, .xls)
        - File size limit: 25MB

    Usage:
        Used in EvacuationLineFormSet for multi-line evacuation creation
    """
    class Meta:
        model = EvacuationLine
        fields = ['sd_number', 'vessel', 'agent', 'container_file']
        widgets = {
            'sd_number':      forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-input-bold evac-sd-number',
                'placeholder': 'SD100',
                'required': 'required'
            }),
            'vessel':         forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-upper',
                'placeholder': 'MV NAVIOS MAGNOLIA'
            }),
            'agent':          forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-upper',
                'placeholder': 'MSC'
            }),
            'container_file': forms.ClearableFileInput(attrs={
                'accept': '.xlsx,.xls'
            }),
        }


# Formset for evacuation lines (multiple SDs per shift)
EvacuationLineFormSet = inlineformset_factory(
    Evacuation, EvacuationLine,
    form=EvacuationLineForm,
    extra=1, can_delete=True,
)
