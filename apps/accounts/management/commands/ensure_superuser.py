import secrets
import string
from django.core.management.base import BaseCommand
from apps.accounts.models import Account


def generate_secure_password(length=16):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


class Command(BaseCommand):
    help = 'Creates default superuser only if NO superuser exists (protects site)'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("[ENSURE_SUPERUSER] Checking for existing superusers...")

        # Check if ANY superuser exists in the database
        superuser_count = Account.objects.filter(is_superuser=True).count()
        self.stdout.write(f"[ENSURE_SUPERUSER] Found {superuser_count} existing superuser(s)")

        if superuser_count > 0:
            self.stdout.write("[ENSURE_SUPERUSER] Superuser already exists - skipping creation")
            self.stdout.write("[ENSURE_SUPERUSER] Site is protected - only one superuser allowed")
            self.stdout.write("=" * 80)
            return

        # No superuser exists - create default one with random password
        self.stdout.write("[ENSURE_SUPERUSER] No superuser found - creating default superuser...")

        # Generate secure random password
        random_password = generate_secure_password(16)

        try:
            user = Account.objects.create_superuser(
                staff_number='1000',
                password=random_password,
                first_name='Admin',
                last_name='User',
                email='admin@eshipping.com',
                rank='System Administrator'
            )
            self.stdout.write(self.style.SUCCESS("[ENSURE_SUPERUSER] SUCCESS: Default superuser created"))
            self.stdout.write("=" * 80)
            self.stdout.write(self.style.WARNING("IMPORTANT: Save these credentials securely!"))
            self.stdout.write(f"Staff ID: 1000")
            self.stdout.write(f"Password: {random_password}")
            self.stdout.write(self.style.WARNING("Change password immediately after first login!"))
            self.stdout.write("=" * 80)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ENSURE_SUPERUSER] ERROR: {e}"))
            self.stdout.write("=" * 80)
