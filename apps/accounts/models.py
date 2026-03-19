from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from apps.core.validators import validate_image_file, validate_file_size_2mb


DESK_CHOICES = [
    ('MANAGER', 'Manager'),
    ('OPERATIONS', 'Operations Desk'),
    ('EBOOKING', 'E-Booking Desk'),
    ('DECLARATION', 'Declaration Desk'),
    ('TERMINAL_SUPERVISOR', 'Terminal Supervisor'),
    ('EVACUATION', 'Evacuation Desk'),
    ('OTHER', 'Other'),
]

LOCATION_CHOICES = [
    ('TEMA', 'Tema'),
    ('TAKORADI', 'Takoradi'),
    ('ACCRA', 'Accra'),
    ('KUMASI', 'Kumasi'),
]

EMPLOYMENT_TYPE_CHOICES = [
    ('PERMANENT', 'Permanent'),
    ('CONTRACT', 'Contract'),
]


class MyAccountsManager(BaseUserManager):
    """
    Custom manager for Account model with staff number authentication.

    Provides methods to create regular users and superusers with staff numbers
    as the primary authentication field instead of usernames.

    Methods:
        create_user: Create a regular staff user
        create_superuser: Create a superuser with admin privileges
    """
    def create_user(self, staff_number, first_name, last_name, rank, email, password=None, force_password_change=True):
        """
        Create and save a regular user with staff number authentication.

        Args:
            staff_number: Unique staff identification number
            first_name: User's first name
            last_name: User's last name
            rank: Job rank/position
            email: Email address (normalized)
            password: Plain text password (will be hashed)
            force_password_change: Whether to force password change on first login

        Returns:
            Account: Created user instance

        Raises:
            ValueError: If staff_number or email is missing

        Example:
            >>> user = Account.objects.create_user(
            ...     staff_number=1812,
            ...     first_name='John',
            ...     last_name='Doe',
            ...     rank='SHIPPING OFFICER',
            ...     email='john.doe@example.com',
            ...     password='secure123'
            ... )
        """
        if staff_number is None:
            raise ValueError("User must have a staff number")
        if not email:
            raise ValueError("No email available for this user")

        email = self.normalize_email(email)

        user = self.model(
            staff_number=staff_number,
            first_name=first_name,
            last_name=last_name,
            rank=rank,
            email=email,
        )
        user.set_password(password)
        user.is_active = True
        user.force_password_change = force_password_change
        user.save(using=self._db)
        return user

    def create_superuser(self, staff_number, first_name, last_name, email, rank, password):
        """
        Create and save a superuser with full admin privileges.

        Superusers have:
        - is_admin=True
        - is_staff=True (Django admin access)
        - is_superuser=True (all permissions)
        - force_password_change=False (no forced change)

        Args:
            staff_number: Unique staff identification number
            first_name: User's first name
            last_name: User's last name
            email: Email address
            rank: Job rank/position
            password: Plain text password (will be hashed)

        Returns:
            Account: Created superuser instance

        Example:
            >>> superuser = Account.objects.create_superuser(
            ...     staff_number=1000,
            ...     first_name='Admin',
            ...     last_name='User',
            ...     email='admin@example.com',
            ...     rank='MANAGER',
            ...     password='admin123'
            ... )
        """
        user = self.create_user(
            staff_number=staff_number,
            first_name=first_name,
            last_name=last_name,
            email=email,
            rank=rank,
            password=password,
            force_password_change=False,
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for shipping department staff authentication.

    Uses staff number as the primary authentication field instead of username.
    Supports multi-desk assignments for staff who work across multiple departments.

    Authentication:
    - USERNAME_FIELD: staff_number (unique integer)
    - Password: Hashed with Django's default hasher
    - Force password change on first login (configurable)

    Multi-Desk System:
    - desks: JSONField storing list of desk codes (e.g., ['OPERATIONS', 'EBOOKING'])
    - desk: Legacy single desk field (kept for backward compatibility)
    - Convenience properties: is_manager, is_operations, is_ebooking, etc.

    Desk Types:
    - MANAGER: Can create schedules, manage staff, assign terminals
    - OPERATIONS: Can create SD records, work programs, daily port reports
    - EBOOKING: Can create bookings and handle corrections
    - DECLARATION: Can create declarations
    - TERMINAL_SUPERVISOR: Can approve tallies for assigned terminals
    - EVACUATION: Can log evacuation records

    Relationships:
    - profile: One-to-one with StaffProfile (extended profile data)
    - tallies: One-to-many with TallyInfo (tallies created by this user)
    - supervised_terminals: Many-to-many with Terminal (terminals supervised)

    Fields:
        staff_number: Unique staff ID (authentication field)
        first_name: First name
        last_name: Last name
        email: Email address (unique)
        rank: Job rank/position
        desks: List of assigned desk codes
        location: Work location (TEMA, TAKORADI, ACCRA, KUMASI)
        employment_type: PERMANENT or CONTRACT
        force_password_change: Whether to force password change on next login

    Example:
        >>> user = Account.objects.get(staff_number=1812)
        >>> user.get_desks_list()
        ['OPERATIONS', 'EBOOKING']
        >>> user.is_operations
        True
        >>> user.get_desks_display()
        'Operations Desk, E-Booking Desk'
    """
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    staff_number = models.PositiveIntegerField(unique=True)
    email = models.EmailField(max_length=100, unique=True)
    rank = models.CharField(max_length=300)

    first_login = models.DateTimeField(auto_now_add=True)
    force_password_change = models.BooleanField(default=True)

    is_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Legacy single desk field (kept for backward compatibility during migration)
    desk = models.CharField(
        max_length=30, choices=DESK_CHOICES, default='OTHER', blank=True)

    # New multi-desk field - stores list of desk codes
    desks = models.JSONField(
        default=list,
        blank=True,
        help_text="List of desks this staff member is assigned to (e.g., ['OPERATIONS', 'EBOOKING'])"
    )

    location = models.CharField(
        max_length=30, choices=LOCATION_CHOICES, default='TEMA')
    employment_type = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_TYPE_CHOICES,
        default='PERMANENT',
        verbose_name='Employment Type'
    )
    is_contract_staff = models.BooleanField(
        default=False,
        help_text="Contract / temporary staff (uses placeholder staff number)"
    )

    objects = MyAccountsManager()

    USERNAME_FIELD = "staff_number"
    REQUIRED_FIELDS = ["email", "first_name", "last_name", "rank"]

    class Meta:
        app_label = 'accounts'

    def __str__(self):
        return f"{self.staff_number} - {self.first_name} {self.last_name}"

    def has_perm(self, perm, obj=None):
        """Check if user has a specific permission."""
        if self.is_superuser:
            return True
        # For admins, check actual permissions instead of blanket approval
        if self.is_admin:
            return super().has_perm(perm, obj)
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        return True

    def get_desks_list(self):
        """Get list of desks, handling both old and new format"""
        if self.desks:
            return self.desks
        elif self.desk and self.desk != 'OTHER':
            return [self.desk]
        return []

    def get_desks_display(self):
        """Get comma-separated display names of assigned desks"""
        desk_dict = dict(DESK_CHOICES)
        desks_list = self.get_desks_list()
        if not desks_list:
            return "No Desk Assigned"
        return ", ".join([desk_dict.get(d, d) for d in desks_list])

    @property
    def is_manager(self):
        return 'MANAGER' in self.get_desks_list() or self.is_superuser

    @property
    def is_operations(self):
        return 'OPERATIONS' in self.get_desks_list() or self.is_superuser

    @property
    def is_ebooking(self):
        return 'EBOOKING' in self.get_desks_list() or self.is_superuser

    @property
    def is_declaration(self):
        return 'DECLARATION' in self.get_desks_list() or self.is_superuser

    @property
    def is_terminal_supervisor(self):
        return 'TERMINAL_SUPERVISOR' in self.get_desks_list() or self.is_superuser

    @property
    def is_evacuation(self):
        return 'EVACUATION' in self.get_desks_list() or self.is_superuser


class StaffProfile(models.Model):
    """
    Extended profile information for staff members.

    One-to-one relationship with Account model. Stores additional profile data
    like profile picture, employment date, and password change tracking.

    Relationships:
    - staff: One-to-one with Account (parent user account)

    Fields:
        profile_picture: Optional profile image (max 2MB)
        rank: Job rank (duplicated from Account for historical reasons)
        date_employed: Employment start date
        years_served: Manually entered years of service
        password_changed_at: Timestamp of last password change
        first_login: Timestamp of profile creation

    Properties:
        calculated_years_served: Auto-calculated years from employment date

    Example:
        >>> profile = user.profile
        >>> profile.calculated_years_served
        5
        >>> profile.profile_picture.url
        '/media/staffprofile/1812.jpg'
    """
    staff = models.OneToOneField(
        Account, on_delete=models.CASCADE, related_name="profile")
    profile_picture = models.ImageField(
        upload_to="staffprofile",
        blank=True,
        validators=[validate_image_file, validate_file_size_2mb]
    )
    rank = models.CharField(max_length=200, blank=True)
    date_employed = models.DateTimeField(null=True, blank=True)
    years_served = models.PositiveIntegerField(blank=True, null=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    first_login = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.staff)

    @property
    def calculated_years_served(self):
        """Calculate years served from employment date to current year"""
        if self.date_employed:
            from datetime import date
            current_year = date.today().year
            employment_year = self.date_employed.year
            return current_year - employment_year
        return None
