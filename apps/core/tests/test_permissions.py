"""
Permission System Tests

Tests the multi-desk permission system that controls access to all
sensitive operations (SD records, bookings, declarations, evacuations, schedules).

Critical for security: If these tests fail, unauthorized users could access
financial data or create fraudulent records.
"""

import random
from django.test import TestCase
from django.contrib.auth.models import AnonymousUser

from apps.accounts.models import Account
from apps.core.permissions import _get_user_desks
from apps.operations.permissions import (
    can_manage_schedules,
    can_manage_sd_records,
    is_terminal_supervisor,
)
from apps.ebooking.permissions import can_manage_bookings
from apps.declaration.permissions import can_manage_declarations
from apps.evacuation.permissions import can_manage_evacuations


class PermissionSystemTestCase(TestCase):
    """Test multi-desk permission system."""

    def make_user(self, desks=None, legacy_desk=None, is_superuser=False):
        """Helper to create test users with specific desk assignments."""
        staff_number = random.randint(10000, 99999)
        user = Account.objects.create_user(
            staff_number=staff_number,
            first_name='Test',
            last_name='User',
            rank='TEST RANK',
            email=f'test{staff_number}@example.com',
            password='testpass123',
            force_password_change=False
        )
        if desks:
            user.desks = desks
        if legacy_desk:
            user.desk = legacy_desk
        if is_superuser:
            user.is_superuser = True
            user.is_staff = True
        user.save()
        return user

    # ══════════════════════════════════════════════════════════════
    #  _get_user_desks() TESTS (Foundation)
    # ══════════════════════════════════════════════════════════════

    def test_unauthenticated_user_returns_empty_set(self):
        # Unauthenticated users should have no desk access
        user = AnonymousUser()
        result = _get_user_desks(user)
        self.assertEqual(result, set())

    def test_user_with_no_desks_returns_empty_set(self):
        # Users with no desk assignments should have no permissions
        user = self.make_user()
        result = _get_user_desks(user)
        self.assertEqual(result, set())

    def test_user_with_new_desks_field_returns_correct_set(self):
        # New multi-desk field should return all assigned desks
        user = self.make_user(desks=['OPERATIONS', 'EBOOKING'])
        result = _get_user_desks(user)
        self.assertEqual(result, {'OPERATIONS', 'EBOOKING'})

    def test_user_with_legacy_desk_field_returns_correct_set(self):
        # Legacy single desk field should still work for backward compatibility
        user = self.make_user(legacy_desk='OPERATIONS')
        result = _get_user_desks(user)
        self.assertEqual(result, {'OPERATIONS'})

    def test_user_with_both_fields_returns_combined_set(self):
        # Users with both old and new fields should get combined permissions
        user = self.make_user(desks=['EBOOKING'], legacy_desk='OPERATIONS')
        result = _get_user_desks(user)
        self.assertEqual(result, {'OPERATIONS', 'EBOOKING'})

    def test_user_with_legacy_other_desk_excluded(self):
        # Legacy 'OTHER' desk should not grant any permissions
        user = self.make_user(legacy_desk='OTHER')
        result = _get_user_desks(user)
        self.assertEqual(result, set())

    # ══════════════════════════════════════════════════════════════
    #  can_manage_sd_records() TESTS
    # ══════════════════════════════════════════════════════════════

    def test_operations_desk_can_manage_sd_records(self):
        # Operations desk creates SD records daily - must have access
        user = self.make_user(desks=['OPERATIONS'])
        self.assertTrue(can_manage_sd_records(user))

    def test_non_operations_desk_cannot_manage_sd_records(self):
        # Only operations desk should create SD records (prevents unauthorized access)
        user = self.make_user(desks=['EBOOKING'])
        self.assertFalse(can_manage_sd_records(user))

    def test_superuser_can_manage_sd_records(self):
        # Superusers need access for emergency fixes and audits
        user = self.make_user(is_superuser=True)
        self.assertTrue(can_manage_sd_records(user))

    def test_unauthenticated_cannot_manage_sd_records(self):
        # Unauthenticated users must never access SD records (security)
        user = AnonymousUser()
        self.assertFalse(can_manage_sd_records(user))

    # ══════════════════════════════════════════════════════════════
    #  can_manage_bookings() TESTS
    # ══════════════════════════════════════════════════════════════

    def test_ebooking_desk_can_manage_bookings(self):
        # Ebooking desk creates bookings daily - must have access
        user = self.make_user(desks=['EBOOKING'])
        self.assertTrue(can_manage_bookings(user))

    def test_non_ebooking_desk_cannot_manage_bookings(self):
        # Only ebooking desk should create bookings (prevents unauthorized bookings)
        user = self.make_user(desks=['OPERATIONS'])
        self.assertFalse(can_manage_bookings(user))

    def test_superuser_can_manage_bookings(self):
        # Superusers need access for emergency fixes and audits
        user = self.make_user(is_superuser=True)
        self.assertTrue(can_manage_bookings(user))

    # ══════════════════════════════════════════════════════════════
    #  can_manage_declarations() TESTS
    # ══════════════════════════════════════════════════════════════

    def test_declaration_desk_can_manage_declarations(self):
        # Declaration desk creates declarations daily - must have access
        user = self.make_user(desks=['DECLARATION'])
        self.assertTrue(can_manage_declarations(user))

    def test_non_declaration_desk_cannot_manage_declarations(self):
        # Only declaration desk should create declarations (compliance requirement)
        user = self.make_user(desks=['OPERATIONS'])
        self.assertFalse(can_manage_declarations(user))

    def test_superuser_can_manage_declarations(self):
        # Superusers need access for emergency fixes and audits
        user = self.make_user(is_superuser=True)
        self.assertTrue(can_manage_declarations(user))

    # ══════════════════════════════════════════════════════════════
    #  can_manage_evacuations() TESTS
    # ══════════════════════════════════════════════════════════════

    def test_evacuation_desk_can_manage_evacuations(self):
        # Evacuation desk logs evacuations daily - must have access
        user = self.make_user(desks=['EVACUATION'])
        self.assertTrue(can_manage_evacuations(user))

    def test_superuser_can_manage_evacuations(self):
        # Superusers need access for emergency fixes and audits
        user = self.make_user(is_superuser=True)
        self.assertTrue(can_manage_evacuations(user))

    # ══════════════════════════════════════════════════════════════
    #  can_manage_schedules() TESTS
    # ══════════════════════════════════════════════════════════════

    def test_manager_desk_can_manage_schedules(self):
        # Manager creates daily schedules - must have access
        user = self.make_user(desks=['MANAGER'])
        self.assertTrue(can_manage_schedules(user))

    def test_non_manager_cannot_manage_schedules(self):
        # Only manager should create schedules (prevents unauthorized assignments)
        user = self.make_user(desks=['OPERATIONS'])
        self.assertFalse(can_manage_schedules(user))

    def test_superuser_can_manage_schedules(self):
        # Superusers need access for emergency fixes and audits
        user = self.make_user(is_superuser=True)
        self.assertTrue(can_manage_schedules(user))

    # ══════════════════════════════════════════════════════════════
    #  MULTI-DESK TESTS (Critical for Business)
    # ══════════════════════════════════════════════════════════════

    def test_user_with_operations_and_ebooking_desks(self):
        # Staff assigned to multiple desks should have all permissions
        user = self.make_user(desks=['OPERATIONS', 'EBOOKING'])
        self.assertTrue(can_manage_sd_records(user))
        self.assertTrue(can_manage_bookings(user))

    def test_user_with_wrong_desk_cannot_access_others(self):
        # Operations user should NOT have ebooking permissions (security)
        user = self.make_user(desks=['OPERATIONS'])
        self.assertTrue(can_manage_sd_records(user))
        self.assertFalse(can_manage_bookings(user))
        self.assertFalse(can_manage_declarations(user))
        self.assertFalse(can_manage_evacuations(user))

    # ══════════════════════════════════════════════════════════════
    #  LEGACY COMPATIBILITY TESTS
    # ══════════════════════════════════════════════════════════════

    def test_legacy_single_desk_grants_permission(self):
        # Users with old desk field should still have permissions (backward compatibility)
        user = self.make_user(legacy_desk='OPERATIONS')
        self.assertTrue(can_manage_sd_records(user))

    def test_legacy_other_desk_grants_no_permission(self):
        # Legacy 'OTHER' desk should not grant any permissions
        user = self.make_user(legacy_desk='OTHER')
        self.assertFalse(can_manage_sd_records(user))
        self.assertFalse(can_manage_bookings(user))
        self.assertFalse(can_manage_declarations(user))
        self.assertFalse(can_manage_evacuations(user))
        self.assertFalse(can_manage_schedules(user))
