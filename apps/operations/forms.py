from django import forms
from django.forms import inlineformset_factory
from django.utils.html import escape
from .models import Schedule, ScheduleEntry, SDRecord, SDAllocation, SDContainer, SDClerk, ContainerListUpload, DailyPort, WorkProgram


# ── Schedule forms ────────────────────────────────────────────────

class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['date', 'notes']
        widgets = {
            'date':  forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Optional notes...'}),
        }

    def validate_unique(self):
        """
        Override to skip unique validation for date field.
        The view handles duplicate dates by redirecting to edit page.
        """
        # Skip unique validation - let the view handle it
        pass

    def clean_notes(self):
        """SECURITY: Sanitize notes field to prevent XSS attacks."""
        notes = self.cleaned_data.get('notes', '')
        return escape(notes) if notes else ''


class ScheduleEntryForm(forms.ModelForm):
    class Meta:
        model = ScheduleEntry
        fields = ['sd_number', 'agent', 'tonnage', 'assigned_officer', 'notes']
        widgets = {
            'sd_number':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. SD100'}),
            'agent':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MSC, COCSCO'}),
            'tonnage':          forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': '0'}),
            'assigned_officer': forms.Select(attrs={'class': 'form-select'}),
            'notes':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['assigned_officer'].queryset = User.objects.filter(
            is_active=True).order_by('first_name')
        self.fields['assigned_officer'].empty_label = '— Assign Officer —'
        self.fields['assigned_officer'].required = False

    def clean_sd_number(self):
        """
        Allow any SD number - no validation required.
        Records can be created before or after operations creates the SD.
        Automatic linkage happens via sd_record ForeignKey when SD is created.
        """
        sd_number = self.cleaned_data.get('sd_number', '').strip()
        return sd_number


ScheduleEntryFormSet = inlineformset_factory(
    Schedule, ScheduleEntry,
    form=ScheduleEntryForm,
    extra=0, can_delete=True, min_num=1, validate_min=True,
)


# ── SD Record forms ───────────────────────────────────────────────

class SDRecordForm(forms.ModelForm):
    class Meta:
        model = SDRecord
        fields = [
            'sd_number', 'si_ref', 'vessel_name', 'eta',
            'tonnage', 'buyer', 'agent',
            'crop_year', 'shipment_period',
            'port_of_loading', 'port_of_discharge',
            'container_size', 'loading_type', 'bags_per_container',
            'opening_balance', 'tonnage_loaded',
            'stock_allocation_notes', 'is_complete',
            'officer_assigned', 'sd_document', 'container_list',
        ]
        widgets = {
            'sd_number':              forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CMC/SD/FAC/TEM/25-26/416'}),
            'si_ref':                 forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. TO25434'}),
            'vessel_name':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MV MSC LUASNNE VI'}),
            'eta':                    forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tonnage':                forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': '0'}),
            'buyer':                  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AGRI, TOUTON, FEDCO'}),
            'agent':                  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MSC, COSCO'}),
            'crop_year':              forms.Select(attrs={'class': 'form-select'}),
            'shipment_period':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. JAN 2025 – MAR 2025'}),
            'port_of_loading':        forms.Select(attrs={'class': 'form-select'}),
            'port_of_discharge':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. ANTWERP, TORONTO'}),
            'container_size':         forms.Select(attrs={'class': 'form-select'}),
            'loading_type':           forms.Select(attrs={'class': 'form-select'}),
            'bags_per_container':     forms.NumberInput(attrs={'class': 'form-control'}),
            'opening_balance':        forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': '0'}),
            'tonnage_loaded':         forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': '0'}),
            'stock_allocation_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Any extra allocation notes...'}),
            'is_complete':            forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'officer_assigned':       forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set dynamic crop year choices
        from .models import get_current_crop_year_choices
        self.fields['crop_year'].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=[('', '— Select —')] + get_current_crop_year_choices()
        )

        self.fields['container_size'].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=[('', '— Select —'), ('20FT', '20FT'), ('40FT', '40FT')]
        )

        # Set officer_assigned queryset
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['officer_assigned'].queryset = User.objects.filter(
            is_active=True).order_by('first_name')
        self.fields['officer_assigned'].empty_label = '— Assign Officer —'
        self.fields['officer_assigned'].required = False

        # Make file fields NOT required on edit (files already uploaded)
        # Users can leave them blank to keep existing files
        self.fields['sd_document'].required = False
        self.fields['container_list'].required = False

    def clean_sd_number(self):
        """Validate that SD number is unique (prevent duplicates)."""
        sd_number = self.cleaned_data.get('sd_number', '').strip()

        # For edit mode, exclude current instance from uniqueness check
        if self.instance and self.instance.pk:
            if SDRecord.objects.filter(sd_number__iexact=sd_number).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(
                    f"SD number '{sd_number}' already exists. Please use a unique SD number."
                )
        else:
            # For create mode, check if SD number already exists
            if SDRecord.objects.filter(sd_number__iexact=sd_number).exists():
                raise forms.ValidationError(
                    f"SD number '{sd_number}' already exists. Please use a unique SD number."
                )

        return sd_number

    def clean_stock_allocation_notes(self):
        """SECURITY: Sanitize notes field to prevent XSS attacks."""
        notes = self.cleaned_data.get('stock_allocation_notes', '')
        return escape(notes) if notes else ''


# ── Allocation (contract lines) ───────────────────────────────────

class SDAllocationForm(forms.ModelForm):
    def clean_allocated_tonnage(self):
        allocated = self.cleaned_data.get('allocated_tonnage')
        if allocated is None:
            return allocated
        if allocated < 0:
            raise forms.ValidationError('Allocated tonnage cannot be negative.')
        return allocated

    def clean_tonnage_loaded(self):
        loaded = self.cleaned_data.get('tonnage_loaded')
        if loaded is None:
            return loaded
        if loaded < 0:
            raise forms.ValidationError('Tonnage loaded cannot be negative.')
        return loaded

    def clean(self):
        cleaned = super().clean()
        allocated = cleaned.get('allocated_tonnage')
        loaded = cleaned.get('tonnage_loaded')

        # Allow 0 = nothing loaded
        if allocated is not None and loaded is not None and loaded > allocated:
            self.add_error('tonnage_loaded', 'Tonnage loaded cannot exceed allocated tonnage for this contract.')

        return cleaned

    class Meta:
        model = SDAllocation
        fields = ['allocation_label', 'contract_number', 'mk_number',
                  'allocated_tonnage', 'tonnage_loaded', 'buyer', 'si_ref', 'agent', 'cocoa_type', 'notes']
        widgets = {
            'allocation_label':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'A'}),
            'contract_number':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. NJ2604251911 PT'}),
            'mk_number':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MK 042519'}),
            'allocated_tonnage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': '0'}),
            'buyer':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. AGRI, TOUTON'}),
            'si_ref':            forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. TO25434'}),
            'agent':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MSC, COSCO'}),
            'cocoa_type':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CLT. 5, KUAPA'}),
            'notes':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
        }


SDAllocationFormSet = inlineformset_factory(
    SDRecord, SDAllocation,
    form=SDAllocationForm,
    extra=1, can_delete=True, min_num=1, validate_min=True,
)


# ── Container form (manual entries by operations) ─────────────────

class SDContainerForm(forms.ModelForm):
    class Meta:
        model = SDContainer
        fields = ['allocation', 'container_number', 'seal_number', 'bag_count',
                  'gross_weight', 'net_weight', 'loading_date', 'balance_after']
        widgets = {
            'allocation':       forms.Select(attrs={'class': 'form-select'}),
            'container_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. JM2403235916'}),
            'seal_number':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Seal No.'}),
            'bag_count':        forms.NumberInput(attrs={'class': 'form-control'}),
            'gross_weight':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': '0'}),
            'net_weight':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': '0'}),
            'loading_date':     forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'balance_after':    forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
        }

    def __init__(self, *args, **kwargs):
        sd_record = kwargs.pop('sd_record', None)
        super().__init__(*args, **kwargs)
        if sd_record:
            self.fields['allocation'].queryset = SDAllocation.objects.filter(
                sd_record=sd_record)
            self.fields['allocation'].empty_label = '— No contract assigned —'
        self.fields['allocation'].required = False


def get_container_formset(sd_record=None):
    """Returns the SDContainerFormSet class with allocation queryset scoped to the SD."""
    FormSet = inlineformset_factory(
        SDRecord, SDContainer,
        form=SDContainerForm,
        extra=1, can_delete=True,
    )

    if sd_record:
        # Patch the form's __init__ to pass sd_record into each form
        alloc_qs = SDAllocation.objects.filter(sd_record=sd_record)

        class BoundContainerForm(SDContainerForm):
            def __init__(self, *args, **kw):
                super().__init__(*args, sd_record=sd_record, **kw)
                self.fields['allocation'].queryset = alloc_qs

        FormSet.form = BoundContainerForm

    return FormSet


# ── Clerk form ────────────────────────────────────────────────────

class SDClerkForm(forms.ModelForm):
    class Meta:
        model = SDClerk
        fields = ['officer', 'officer_name', 'tally_reference', 'date_worked']
        widgets = {
            'officer':         forms.Select(attrs={'class': 'form-select'}),
            'officer_name':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name (if not in system)'}),
            'tally_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. TALLY-001'}),
            'date_worked':     forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['officer'].queryset = User.objects.filter(
            is_active=True).order_by('first_name')
        self.fields['officer'].empty_label = '— Select from system —'
        self.fields['officer'].required = False
        self.fields['officer_name'].required = False


SDClerkFormSet = inlineformset_factory(
    SDRecord, SDClerk,
    form=SDClerkForm,
    extra=1, can_delete=True,
)


# ── Work Program form ──────────────────────────────────────────────

class WorkProgramForm(forms.ModelForm):
    class Meta:
        model = WorkProgram
        fields = ['date', 'pdf_file', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'sdt-si-input'}),
            'pdf_file': forms.FileInput(attrs={'class': 'sdt-si-input', 'accept': '.pdf'}),
            'notes': forms.Textarea(attrs={'class': 'sdt-si-input', 'rows': 4, 'placeholder': 'Optional notes about this work program...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].required = True
        self.fields['pdf_file'].required = True
        self.fields['notes'].required = False

        # Preload date with today's date for new records
        if not self.instance.pk:
            from datetime import date
            self.fields['date'].initial = date.today()


# ── Container List Upload form ─────────────────────────────────────

class ContainerListUploadForm(forms.ModelForm):
    class Meta:
        model = ContainerListUpload
        fields = ['allocation', 'contract_number', 'tonnage', 'excel_file', 'notes']
        widgets = {
            'allocation':      forms.Select(attrs={'class': 'form-select'}),
            'contract_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. NJ2604251911 PT'}),
            'tonnage':         forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'placeholder': '0'}),
            'notes':           forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes…'}),
        }

    def __init__(self, *args, **kwargs):
        sd_record = kwargs.pop('sd_record', None)
        super().__init__(*args, **kwargs)
        if sd_record:
            self.fields['allocation'].queryset = SDAllocation.objects.filter(sd_record=sd_record)
            self.fields['allocation'].empty_label = '— General / No Contract —'
        self.fields['allocation'].required = False
        self.fields['contract_number'].required = False
        self.fields['tonnage'].required = False


# ── Terminal Schedule form ─────────────────────────────────────────

class TerminalScheduleForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['supervisors'].queryset = User.objects.filter(
            is_active=True).order_by('staff_number')
        self.fields['supervisors'].required = False
        self.fields['supervisors'].label = 'Supervisors'
        # Portal is Tema-only; fix the location silently
        self.fields['location'].initial = 'TEMA'
        self.fields['location'].widget = forms.HiddenInput()
        self.fields['location'].required = False

    class Meta:
        from apps.tally.models import Terminal as _Terminal
        model = _Terminal
        fields = ['name', 'location', 'supervisors']
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. NEW TERMINAL'}),
            'location':    forms.HiddenInput(),
            'supervisors': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '8'}),
        }


# ── Daily Port form ──────────────────────────────────────────────

class DailyPortForm(forms.ModelForm):
    class Meta:
        model = DailyPort
        fields = ['date', 'pdf_file', 'excel_file', 'notes']
        widgets = {
            'date':  forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['notes'].required = False
