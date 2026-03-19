from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms

from .models import Account, StaffProfile


class AccountCreationForm(forms.ModelForm):
    """
    Form for creating new Account users in Django admin interface.

    Features:
    - Password confirmation validation
    - Staff number validation
    - Sets hashed password on save

    Fields:
        password1: Password input
        password2: Password confirmation
        staff_number: Unique staff ID
        email: Email address
        first_name: First name
        last_name: Last name
        rank: Job rank/position
        force_password_change: Whether to force password change on first login

    Validation:
        - Staff number is required
        - Passwords must match
    """
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = Account
        fields = ("staff_number", "email", "first_name",
                  "last_name", "rank", "force_password_change")

    def clean_staff_number(self):
        staff_number = self.cleaned_data.get("staff_number")
        if staff_number is None:
            raise forms.ValidationError("Staff number is required.")
        return staff_number

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AccountChangeForm(forms.ModelForm):
    """
    Form for editing existing Account users in Django admin interface.

    Features:
    - Read-only password hash field with link to password change form
    - All account fields editable except password
    - Supports groups and permissions management

    Fields:
        staff_number: Unique staff ID
        email: Email address
        first_name: First name
        last_name: Last name
        rank: Job rank/position
        password: Read-only password hash
        force_password_change: Whether to force password change
        is_active: Account active status
        is_staff: Django admin access
        is_admin: Admin privileges
        is_superuser: Superuser privileges
        groups: Permission groups
        user_permissions: Individual permissions
    """
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Raw passwords are not stored, so there is no way to see this user’s password, "
            "but you can change the password using <a href=\"../password/\">this form</a>."
        ),
    )

    class Meta:
        model = Account
        fields = (
            "staff_number",
            "email",
            "first_name",
            "last_name",
            "rank",
            "password",
            "force_password_change",
            "is_active",
            "is_staff",
            "is_admin",
            "is_superuser",
            "groups",
            "user_permissions",
        )


@admin.register(Account)
class AccountAdmin(BaseUserAdmin):
    """
    Django admin configuration for Account model.

    Features:
    - Custom list display with staff number, name, email, rank
    - Search by staff number, name, email, rank
    - Filter by staff status, admin status, active status
    - Custom fieldsets for organized editing
    - Separate add form with password fields
    - Read-only last login field

    List Display:
        - staff_number: Unique staff ID
        - first_name: First name
        - last_name: Last name
        - email: Email address
        - rank: Job rank/position
        - is_staff: Django admin access
        - is_admin: Admin privileges
        - is_active: Account active status
        - force_password_change: Password change required

    Fieldsets:
        - None: Staff number and password
        - Personal info: Name, email, rank
        - Access control: Password change, active, staff, admin, superuser
        - Permissions: Groups and user permissions
        - Important dates: Last login

    Usage:
        Access via Django admin at /admin/accounts/account/
    """
    form = AccountChangeForm
    add_form = AccountCreationForm
    model = Account

    list_display = (
        "staff_number",
        "first_name",
        "last_name",
        "email",
        "rank",
        "is_staff",
        "is_admin",
        "is_active",
        "force_password_change",
    )
    list_filter = ("is_staff", "is_admin", "is_active",
                   "force_password_change", "is_superuser")
    search_fields = ("staff_number", "first_name",
                     "last_name", "email", "rank")
    ordering = ("staff_number",)

    fieldsets = (
        (None, {"fields": ("staff_number", "password")}),
        ("Personal info", {
         "fields": ("first_name", "last_name", "email", "rank")}),
        ("Access control", {"fields": ("force_password_change",
         "is_active", "is_staff", "is_admin", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "staff_number",
                "email",
                "first_name",
                "last_name",
                "rank",
                "force_password_change",
                "password1",
                "password2",
                "is_active",
                "is_staff",
                "is_admin",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
    )

    readonly_fields = ("last_login",)

    def get_fieldsets(self, request, obj=None):
        return super().get_fieldsets(request, obj)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    """
    Django admin configuration for StaffProfile model.

    Features:
    - List display with staff info, employment date, years served
    - Search by staff number, email, name, rank
    - Simple admin interface for profile management

    List Display:
        - staff: Related Account (staff number and name)
        - rank: Job rank/position
        - date_employed: Employment start date
        - years_served: Years of service
        - password_changed_at: Last password change timestamp
        - first_login: Profile creation timestamp

    Search Fields:
        - staff__staff_number: Staff ID
        - staff__email: Email address
        - staff__first_name: First name
        - staff__last_name: Last name
        - rank: Job rank

    Usage:
        Access via Django admin at /admin/accounts/staffprofile/
    """
    list_display = ("staff", "rank", "date_employed",
                    "years_served", "password_changed_at", "first_login")
    search_fields = ("staff__staff_number", "staff__email",
                     "staff__first_name", "staff__last_name", "rank")
