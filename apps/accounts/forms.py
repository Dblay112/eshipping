from django import forms
from .models import Account, DESK_CHOICES, LOCATION_CHOICES, EMPLOYMENT_TYPE_CHOICES


class AddStaffForm(forms.ModelForm):
    """
    Form for managers to add new staff members with multi-desk assignments.

    Features:
    - Auto-generated secure password with confirmation
    - Multi-desk assignment (primary + additional desks)
    - Employment date tracking
    - Superuser/admin assignment
    - Email and staff number uniqueness validation
    - Force password change on first login

    Fields:
        password: Temporary password (min 6 characters)
        confirm_password: Password confirmation
        date_employed: Employment start date (optional)
        primary_desk: Main desk assignment (dropdown)
        additional_desks: Additional desk assignments (checkboxes)
        is_superuser: Admin privileges checkbox

    Validation:
    - Password minimum 6 characters
    - Passwords must match
    - Staff number must be unique
    - Email must be unique

    Usage:
        >>> form = AddStaffForm(request.POST)
        >>> if form.is_valid():
        ...     user = form.save()
        ...     # User created with force_password_change=True
    """

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'sdt-si-input',
            'placeholder': 'Temporary password'
        }),
        label="Temporary Password",
        help_text="Staff will be required to change this password on first login"
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'sdt-si-input',
            'placeholder': 'Confirm password'
        }),
        label="Confirm Password"
    )

    date_employed = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'sdt-si-input',
            'type': 'date',
            'placeholder': 'YYYY-MM-DD'
        }),
        label="Date Employed",
        help_text="Date when staff member was employed"
    )

    # Filter out TERMINAL_SUPERVISOR from desk choices (assigned via terminal page)
    DESK_CHOICES_FILTERED = [choice for choice in DESK_CHOICES if choice[0] != 'TERMINAL_SUPERVISOR']

    # Primary desk assignment (dropdown)
    primary_desk = forms.ChoiceField(
        choices=[('', 'Select Primary Desk')] + DESK_CHOICES_FILTERED,
        widget=forms.Select(attrs={
            'class': 'sdt-si-select',
            'id': 'id_primary_desk'
        }),
        required=False,
        label="Desk Assignment",
        help_text="Select primary desk or 'Other' for staff not assigned to any specific desk"
    )

    # Additional desk assignments (checkboxes for multi-desk)
    additional_desks = forms.MultipleChoiceField(
        choices=DESK_CHOICES_FILTERED,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'desk-checkbox'
        }),
        required=False,
        label="Additional Desk Assignments",
        help_text="Select any additional desks this staff member will work on"
    )

    # Admin/Superuser assignment
    is_superuser = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Assign as Administrator",
        help_text="⚠️ Administrators have full access to all system features including staff management"
    )

    class Meta:
        model = Account
        fields = [
            'first_name',
            'last_name',
            'staff_number',
            'email',
            'rank',
            'location',
            'employment_type',
            'is_superuser'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-upper',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-upper',
                'placeholder': 'Last name'
            }),
            'staff_number': forms.NumberInput(attrs={
                'class': 'sdt-si-input',
                'placeholder': 'Staff ID number',
                'style': 'max-width: 150px;',
                'pattern': '[0-9]+',
                'inputmode': 'numeric',
                'title': 'Please enter numbers only'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'sdt-si-input',
                'placeholder': 'email@example.com'
            }),
            'rank': forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-upper',
                'placeholder': 'e.g. Senior Officer, Clerk, etc.'
            }),
            'location': forms.Select(attrs={
                'class': 'sdt-si-select',
                'style': 'max-width: 200px;'
            }),
            'employment_type': forms.Select(attrs={
                'class': 'sdt-si-select',
                'style': 'max-width: 200px;'
            })
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'staff_number': 'Staff Number (ID)',
            'email': 'Email Address',
            'rank': 'Rank/Position',
            'location': 'Location',
            'employment_type': 'Employment Type'
        }
        help_texts = {
            'staff_number': 'Unique staff identification number',
            'employment_type': 'Permanent or Contract staff'
        }

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')

        if password and len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match")

        return confirm_password

    def clean_staff_number(self):
        staff_number = self.cleaned_data.get('staff_number')

        if Account.objects.filter(staff_number=staff_number).exists():
            raise forms.ValidationError("A staff member with this staff number already exists")

        return staff_number

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if Account.objects.filter(email=email).exists():
            raise forms.ValidationError("A staff member with this email already exists")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.force_password_change = True  # Force password change on first login
        user.is_active = True

        # Combine primary desk and additional desks
        desks_list = []
        primary_desk = self.cleaned_data.get('primary_desk')
        if primary_desk:
            desks_list.append(primary_desk)

        additional_desks = self.cleaned_data.get('additional_desks', [])
        for desk in additional_desks:
            if desk not in desks_list:  # Avoid duplicates
                desks_list.append(desk)

        user.desks = desks_list

        # Handle superuser assignment
        is_superuser = self.cleaned_data.get('is_superuser', False)
        user.is_superuser = is_superuser
        user.is_staff = is_superuser  # Django requires is_staff=True for admin access

        if commit:
            user.save()

            # Create or update staff profile with date_employed
            from .models import StaffProfile
            profile, created = StaffProfile.objects.get_or_create(staff=user)
            date_employed = self.cleaned_data.get('date_employed')
            if date_employed:
                profile.date_employed = date_employed
                profile.save()

        return user


class EditStaffForm(forms.ModelForm):
    """
    Form for editing existing staff members.

    Features:
    - Update personal information (name, email, rank)
    - Modify desk assignments (primary + additional)
    - Change location and employment type
    - Toggle admin/superuser status
    - Toggle active status (soft delete)
    - Update employment date

    Fields:
        date_employed: Employment start date (optional)
        primary_desk: Main desk assignment (dropdown)
        additional_desks: Additional desk assignments (checkboxes)
        is_superuser: Admin privileges checkbox
        is_active: Account active status

    Initialization:
    - Pre-populates current desk assignments
    - Pre-populates employment date from profile
    - Pre-populates superuser status

    Usage:
        >>> form = EditStaffForm(request.POST, instance=staff)
        >>> if form.is_valid():
        ...     user = form.save()
        ...     # User updated with new desk assignments
    """

    date_employed = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'sdt-si-input',
            'type': 'date',
            'placeholder': 'YYYY-MM-DD'
        }),
        label="Date Employed",
        help_text="Date when staff member was employed"
    )

    # Filter out TERMINAL_SUPERVISOR from desk choices (assigned via terminal page)
    DESK_CHOICES_FILTERED = [choice for choice in DESK_CHOICES if choice[0] != 'TERMINAL_SUPERVISOR']

    # Primary desk assignment (dropdown)
    primary_desk = forms.ChoiceField(
        choices=[('', 'Select Primary Desk')] + DESK_CHOICES_FILTERED,
        widget=forms.Select(attrs={
            'class': 'sdt-si-select',
            'id': 'id_primary_desk'
        }),
        required=False,
        label="Desk Assignment",
        help_text="Select primary desk or 'Other' for staff not assigned to any specific desk"
    )

    # Additional desk assignments (checkboxes for multi-desk)
    additional_desks = forms.MultipleChoiceField(
        choices=DESK_CHOICES_FILTERED,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'desk-checkbox'
        }),
        required=False,
        label="Additional Desk Assignments",
        help_text="Select any additional desks this staff member will work on"
    )

    # Admin/Superuser assignment
    is_superuser = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Assign as Administrator",
        help_text="⚠️ Administrators have full access to all system features including staff management"
    )

    class Meta:
        model = Account
        fields = [
            'first_name',
            'last_name',
            'email',
            'rank',
            'location',
            'employment_type',
            'is_superuser',
            'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-upper',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-upper',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'sdt-si-input',
                'placeholder': 'email@example.com'
            }),
            'rank': forms.TextInput(attrs={
                'class': 'sdt-si-input sdt-si-upper',
                'placeholder': 'e.g. Senior Officer, Clerk, etc.'
            }),
            'location': forms.Select(attrs={
                'class': 'sdt-si-select',
                'style': 'max-width: 200px;'
            }),
            'employment_type': forms.Select(attrs={
                'class': 'sdt-si-select',
                'style': 'max-width: 200px;'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
            'rank': 'Rank/Position',
            'location': 'Location',
            'employment_type': 'Employment Type',
            'is_active': 'Active Status'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate desk fields with current assignments
        if self.instance and self.instance.pk:
            current_desks = self.instance.get_desks_list()
            if current_desks:
                # First desk is primary
                self.initial['primary_desk'] = current_desks[0]
                # Rest are additional
                if len(current_desks) > 1:
                    self.initial['additional_desks'] = current_desks[1:]
            self.initial['is_superuser'] = self.instance.is_superuser

            # Pre-populate date_employed from profile
            if hasattr(self.instance, 'profile') and self.instance.profile.date_employed:
                self.initial['date_employed'] = self.instance.profile.date_employed

    def save(self, commit=True):
        user = super().save(commit=False)

        # Combine primary desk and additional desks
        desks_list = []
        primary_desk = self.cleaned_data.get('primary_desk')
        if primary_desk:
            desks_list.append(primary_desk)

        additional_desks = self.cleaned_data.get('additional_desks', [])
        for desk in additional_desks:
            if desk not in desks_list:  # Avoid duplicates
                desks_list.append(desk)

        user.desks = desks_list

        # Handle superuser assignment
        is_superuser = self.cleaned_data.get('is_superuser', False)
        user.is_superuser = is_superuser
        user.is_staff = is_superuser  # Django requires is_staff=True for admin access

        if commit:
            user.save()

            # Update staff profile with date_employed
            from .models import StaffProfile
            profile, created = StaffProfile.objects.get_or_create(staff=user)
            date_employed = self.cleaned_data.get('date_employed')
            if date_employed:
                profile.date_employed = date_employed
                profile.save()

        return user
