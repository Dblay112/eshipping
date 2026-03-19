"""
Tally Approval Workflow Tests

Tests the critical workflow where clerks create tallies, submit to terminal supervisors
for approval, and supervisors approve or reject. Only approved tallies sync data to SD records.

Critical for operations: If this breaks, loading operations stop and clerks can't track work.
"""

import random
from decimal import Decimal
from datetime import date

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tally.models import TallyInfo, TallyContainer, Terminal
from apps.operations.models import SDRecord

Account = get_user_model()


class TallyApprovalWorkflowTestCase(TestCase):
    """Test tally approval workflow and permissions."""

    def setUp(self):
        """Create test users, terminal, and SD record for all tests."""
        # Create terminal
        self.terminal = Terminal.objects.create(
            name='TEST TERMINAL',
            location='TEMA'
        )

        # Create supervisor for terminal
        self.supervisor = Account.objects.create_user(
            staff_number=random.randint(10000, 99999),
            first_name='Terminal',
            last_name='Supervisor',
            rank='SENIOR SHIPPING OFFICER',
            email=f'supervisor{random.randint(1000, 9999)}@example.com',
            password='testpass123',
            force_password_change=False
        )
        self.terminal.supervisors.add(self.supervisor)

        # Create supervisor for different terminal
        self.other_terminal = Terminal.objects.create(
            name='OTHER TERMINAL',
            location='TEMA'
        )
        self.other_supervisor = Account.objects.create_user(
            staff_number=random.randint(10000, 99999),
            first_name='Other',
            last_name='Supervisor',
            rank='SENIOR SHIPPING OFFICER',
            email=f'othersup{random.randint(1000, 9999)}@example.com',
            password='testpass123',
            force_password_change=False
        )
        self.other_terminal.supervisors.add(self.other_supervisor)

        # Create regular clerk (no supervisor permissions)
        self.clerk = Account.objects.create_user(
            staff_number=random.randint(10000, 99999),
            first_name='Regular',
            last_name='Clerk',
            rank='SHIPPING CLERK',
            email=f'clerk{random.randint(1000, 9999)}@example.com',
            password='testpass123',
            force_password_change=False
        )

        # Create SD record for tallies
        self.sd = SDRecord.objects.create(
            sd_number='SD100',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('100.00'),
            created_by=self.supervisor
        )

        self.client = Client()

    # ══════════════════════════════════════════════════════════════
    #  TALLY STATUS TRANSITION TESTS
    # ══════════════════════════════════════════════════════════════

    def test_new_tally_starts_as_draft(self):
        # New tallies must start as DRAFT (not submitted yet)
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD100',
            sd_record=self.sd,
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.clerk
        )
        self.assertEqual(tally.status, 'DRAFT')

    def test_submit_tally_changes_status_to_pending(self):
        # Submitting a DRAFT tally must change status to PENDING_APPROVAL
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD100',
            sd_record=self.sd,
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.clerk,
            status='DRAFT'
        )

        # Submit tally
        self.client.force_login(self.clerk)
        response = self.client.post(reverse('submit_tally', args=[tally.pk]))

        # Verify status changed
        tally.refresh_from_db()
        self.assertEqual(tally.status, 'PENDING_APPROVAL')

    def test_approve_tally_changes_status_to_approved(self):
        # Supervisor approving a tally must change status to APPROVED
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD100',
            sd_record=self.sd,
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.clerk,
            status='PENDING_APPROVAL'
        )

        # Approve tally
        self.client.force_login(self.supervisor)
        response = self.client.post(reverse('approve_tally', args=[tally.pk]))

        # Verify status changed
        tally.refresh_from_db()
        self.assertEqual(tally.status, 'APPROVED')
        self.assertEqual(tally.approved_by, self.supervisor)
        self.assertIsNotNone(tally.approved_at)

    def test_reject_tally_changes_status_to_rejected(self):
        # Supervisor rejecting a tally must change status to REJECTED
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD100',
            sd_record=self.sd,
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.clerk,
            status='PENDING_APPROVAL'
        )

        # Reject tally
        self.client.force_login(self.supervisor)
        response = self.client.post(
            reverse('reject_tally', args=[tally.pk]),
            {'rejection_reason': 'Container numbers incorrect'}
        )

        # Verify status changed
        tally.refresh_from_db()
        self.assertEqual(tally.status, 'REJECTED')
        self.assertEqual(tally.rejection_reason, 'Container numbers incorrect')

    def test_resubmit_rejected_tally_changes_status_to_pending(self):
        # Resubmitting a REJECTED tally must change status back to PENDING_APPROVAL
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD100',
            sd_record=self.sd,
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.clerk,
            status='REJECTED',
            rejection_reason='Fix container numbers'
        )

        # Resubmit tally
        self.client.force_login(self.clerk)
        response = self.client.post(reverse('submit_tally', args=[tally.pk]))

        # Verify status changed back to pending
        tally.refresh_from_db()
        self.assertEqual(tally.status, 'PENDING_APPROVAL')

    # ══════════════════════════════════════════════════════════════
    #  PERMISSION TESTS
    # ══════════════════════════════════════════════════════════════

    def test_regular_clerk_cannot_approve_tally(self):
        # Only supervisors can approve tallies (prevents unauthorized approvals)
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD100',
            sd_record=self.sd,
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.clerk,
            status='PENDING_APPROVAL'
        )

        # Try to approve as clerk
        self.client.force_login(self.clerk)
        response = self.client.post(reverse('approve_tally', args=[tally.pk]))

        # Verify approval was denied
        self.assertEqual(response.status_code, 302)  # Redirect
        tally.refresh_from_db()
        self.assertEqual(tally.status, 'PENDING_APPROVAL')  # Status unchanged

    def test_supervisor_cannot_approve_tally_from_other_terminal(self):
        # Supervisors can only approve tallies from their assigned terminals (security)
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD100',
            sd_record=self.sd,
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.other_terminal,  # Different terminal
            loading_date=date.today(),
            created_by=self.clerk,
            status='PENDING_APPROVAL'
        )

        # Try to approve as supervisor from different terminal
        self.client.force_login(self.supervisor)
        response = self.client.post(reverse('approve_tally', args=[tally.pk]))

        # Verify approval was denied
        self.assertEqual(response.status_code, 302)  # Redirect
        tally.refresh_from_db()
        self.assertEqual(tally.status, 'PENDING_APPROVAL')  # Status unchanged

    def test_supervisor_can_approve_tally_from_own_terminal(self):
        # Supervisors can approve tallies from their assigned terminals
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD100',
            sd_record=self.sd,
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,  # Supervisor's terminal
            loading_date=date.today(),
            created_by=self.clerk,
            status='PENDING_APPROVAL'
        )

        # Approve as supervisor
        self.client.force_login(self.supervisor)
        response = self.client.post(reverse('approve_tally', args=[tally.pk]))

        # Verify approval succeeded
        tally.refresh_from_db()
        self.assertEqual(tally.status, 'APPROVED')

    # ══════════════════════════════════════════════════════════════
    #  APPROVED TALLY IMMUTABILITY TESTS
    # ══════════════════════════════════════════════════════════════

    def test_rejected_tally_can_be_edited(self):
        # Rejected tallies must be editable (so clerk can fix errors)
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD100',
            sd_record=self.sd,
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.clerk,
            status='REJECTED',
            rejection_reason='Fix container numbers'
        )

        # Try to edit rejected tally
        self.client.force_login(self.clerk)
        response = self.client.get(reverse('tally_edit', args=[tally.pk]))

        # Verify edit was allowed
        self.assertEqual(response.status_code, 200)
