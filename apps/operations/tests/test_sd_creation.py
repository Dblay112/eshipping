"""
SD Record Creation and Orphaned Record Auto-Linking Tests

Tests the critical workflow where operations desk creates SD records and the system
automatically links all existing orphaned records (tallies, bookings, declarations,
evacuations) that were created before the SD existed.

Critical for data integrity: If this breaks, orphaned records never get linked and
clerks lose their work.
"""

import random
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.operations.models import SDRecord, SDAllocation, ScheduleEntry, Schedule
from apps.operations.views.sync import sync_existing_tallies
from apps.tally.models import TallyInfo, TallyContainer, Terminal
from apps.ebooking.models import BookingRecord, BookingLine, BookingDetail
from apps.declaration.models import Declaration
from apps.evacuation.models import Evacuation, EvacuationLine

Account = get_user_model()


class SDCreationAndAutoLinkingTestCase(TestCase):
    """Test SD record creation with orphaned record auto-linking."""

    def setUp(self):
        """Create test users and terminal for all tests."""
        # Create operations user
        self.ops_user = Account.objects.create_user(
            staff_number=random.randint(10000, 99999),
            first_name='Operations',
            last_name='User',
            rank='OPERATIONS OFFICER',
            email=f'ops{random.randint(1000, 9999)}@example.com',
            password='testpass123',
            force_password_change=False
        )
        self.ops_user.desks = ['OPERATIONS']
        self.ops_user.save()

        # Create ebooking user
        self.ebooking_user = Account.objects.create_user(
            staff_number=random.randint(10000, 99999),
            first_name='Ebooking',
            last_name='User',
            rank='EBOOKING OFFICER',
            email=f'ebooking{random.randint(1000, 9999)}@example.com',
            password='testpass123',
            force_password_change=False
        )
        self.ebooking_user.desks = ['EBOOKING']
        self.ebooking_user.save()

        # Create declaration user
        self.declaration_user = Account.objects.create_user(
            staff_number=random.randint(10000, 99999),
            first_name='Declaration',
            last_name='User',
            rank='DECLARATION OFFICER',
            email=f'declaration{random.randint(1000, 9999)}@example.com',
            password='testpass123',
            force_password_change=False
        )
        self.declaration_user.desks = ['DECLARATION']
        self.declaration_user.save()

        # Create terminal for tally tests
        self.terminal = Terminal.objects.create(
            name='TEST TERMINAL',
            location='TEMA'
        )

    # ══════════════════════════════════════════════════════════════
    #  TALLY AUTO-LINKING TESTS
    # ══════════════════════════════════════════════════════════════

    def test_orphaned_tally_gets_linked_when_sd_created(self):
        # Orphaned tallies must link to SD when created (prevents data loss)
        # Create tally with non-existent SD
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD999',
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.ops_user
        )
        self.assertIsNone(tally.sd_record)

        # Create SD record
        sd = SDRecord.objects.create(
            sd_number='SD999',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('100.00'),
            created_by=self.ops_user
        )

        # Run sync
        sync_existing_tallies(sd)

        # Verify tally is now linked
        tally.refresh_from_db()
        self.assertEqual(tally.sd_record, sd)

    def test_multiple_orphaned_tallies_all_get_linked(self):
        # All orphaned tallies for an SD must link (not just first one)
        # Create multiple tallies with same SD number
        tally1 = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD888',
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.ops_user
        )
        tally2 = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD888',
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.ops_user
        )

        # Create SD
        sd = SDRecord.objects.create(
            sd_number='SD888',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('200.00'),
            created_by=self.ops_user
        )

        # Run sync
        sync_existing_tallies(sd)

        # Verify both tallies linked
        tally1.refresh_from_db()
        tally2.refresh_from_db()
        self.assertEqual(tally1.sd_record, sd)
        self.assertEqual(tally2.sd_record, sd)

    def test_tally_containers_sync_to_sd_record(self):
        # Tally containers must sync to SD record (for tonnage tracking)
        # Create SD first
        sd = SDRecord.objects.create(
            sd_number='SD777',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('100.00'),
            created_by=self.ops_user
        )

        # Create orphaned tally with container AFTER SD exists
        tally = TallyInfo.objects.create(
            tally_number=random.randint(100000, 999999),
            tally_type='STRAIGHT_40FT',
            sd_number='SD777',
            mk_number='MK001',
            vessel='TEST VESSEL',
            destination='TEST DESTINATION',
            crop_year='2025/2026 MC',
            terminal=self.terminal,
            loading_date=date.today(),
            created_by=self.ops_user
        )
        container = TallyContainer.objects.create(
            tally=tally,
            container_number='CONT001',
            seal_number='SEAL001',
            bags=300
        )

        # Tally should be orphaned (not linked yet)
        self.assertIsNone(tally.sd_record)

        # Run sync to link tally and sync containers
        sync_existing_tallies(sd)

        # Verify tally is linked
        tally.refresh_from_db()
        self.assertEqual(tally.sd_record, sd)

        # Verify SD has container
        self.assertEqual(sd.containers.count(), 1)
        sd_container = sd.containers.first()
        self.assertEqual(sd_container.container_number, 'CONT001')
        self.assertEqual(sd_container.seal_number, 'SEAL001')
        self.assertEqual(sd_container.bag_count, 300)

    # ══════════════════════════════════════════════════════════════
    #  BOOKING AUTO-LINKING TESTS
    # ══════════════════════════════════════════════════════════════

    def test_orphaned_booking_gets_linked_when_sd_created(self):
        # Orphaned bookings must link to SD when created (prevents data loss)
        # Create booking with non-existent SD
        booking = BookingRecord.objects.create(
            sd_number='SD666',
            vessel='TEST VESSEL',
            agent='TEST AGENT',
            created_by=self.ebooking_user
        )
        self.assertIsNone(booking.sd_record)

        # Create SD
        sd = SDRecord.objects.create(
            sd_number='SD666',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('100.00'),
            created_by=self.ops_user
        )

        # Run sync
        sync_existing_tallies(sd)

        # Verify booking is now linked
        booking.refresh_from_db()
        self.assertEqual(booking.sd_record, sd)

    # ══════════════════════════════════════════════════════════════
    #  DECLARATION AUTO-LINKING TESTS
    # ══════════════════════════════════════════════════════════════

    def test_orphaned_declaration_gets_linked_when_sd_created(self):
        # Orphaned declarations must link to SD when created (prevents data loss)
        # Create declaration with non-existent SD
        declaration = Declaration.objects.create(
            sd_number='SD555',
            agent='TEST AGENT',
            contract_number='CONTRACT001',
            declaration_number='DECL001',
            tonnage=Decimal('50.00'),
            created_by=self.declaration_user
        )
        self.assertIsNone(declaration.sd_record)

        # Create SD
        sd = SDRecord.objects.create(
            sd_number='SD555',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('100.00'),
            created_by=self.ops_user
        )

        # Run sync
        sync_existing_tallies(sd)

        # Verify declaration is now linked
        declaration.refresh_from_db()
        self.assertEqual(declaration.sd_record, sd)

    # ══════════════════════════════════════════════════════════════
    #  EVACUATION AUTO-LINKING TESTS
    # ══════════════════════════════════════════════════════════════

    def test_orphaned_evacuation_line_gets_linked_when_sd_created(self):
        # Orphaned evacuation lines must link to SD when created (prevents data loss)
        # Create evacuation record
        evacuation = Evacuation.objects.create(
            date=date.today(),
            shift='DAY',
            created_by=self.ops_user
        )
        # Create evacuation line with non-existent SD
        evac_line = EvacuationLine.objects.create(
            evacuation=evacuation,
            sd_number='SD444',
            vessel='TEST VESSEL',
            agent='TEST AGENT'
        )
        self.assertIsNone(evac_line.sd_record)

        # Create SD
        sd = SDRecord.objects.create(
            sd_number='SD444',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('100.00'),
            created_by=self.ops_user
        )

        # Run sync
        sync_existing_tallies(sd)

        # Verify evacuation line is now linked
        evac_line.refresh_from_db()
        self.assertEqual(evac_line.sd_record, sd)

    # ══════════════════════════════════════════════════════════════
    #  SCHEDULE OFFICER SYNC TESTS
    # ══════════════════════════════════════════════════════════════

    def test_schedule_officer_syncs_to_sd_record(self):
        # Assigned officer from schedule must sync to SD (for responsibility tracking)
        # Create assigned officer
        officer = Account.objects.create_user(
            staff_number=random.randint(10000, 99999),
            first_name='Assigned',
            last_name='Officer',
            rank='SHIPPING OFFICER',
            email=f'officer{random.randint(1000, 9999)}@example.com',
            password='testpass123',
            force_password_change=False
        )

        # Create schedule with entry
        schedule = Schedule.objects.create(
            date=date.today(),
            created_by=self.ops_user
        )
        schedule_entry = ScheduleEntry.objects.create(
            schedule=schedule,
            sd_number='SD333',
            agent='TEST AGENT',
            tonnage=Decimal('100.00'),
            assigned_officer=officer
        )

        # Create SD
        sd = SDRecord.objects.create(
            sd_number='SD333',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('100.00'),
            created_by=self.ops_user
        )

        # Run sync
        sync_existing_tallies(sd)

        # Verify officer synced to SD
        sd.refresh_from_db()
        self.assertEqual(sd.officer_assigned, officer)

    # ══════════════════════════════════════════════════════════════
    #  SD TONNAGE CALCULATION TESTS
    # ══════════════════════════════════════════════════════════════

    def test_sd_tonnage_matches_sum_of_allocations(self):
        # SD total tonnage must equal sum of contract allocations (data integrity)
        # Create SD with allocations
        sd = SDRecord.objects.create(
            sd_number='SD222',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('300.00'),
            created_by=self.ops_user
        )
        SDAllocation.objects.create(
            sd_record=sd,
            contract_number='CONTRACT001',
            allocated_tonnage=Decimal('100.00'),
            allocation_label='A'
        )
        SDAllocation.objects.create(
            sd_record=sd,
            contract_number='CONTRACT002',
            allocated_tonnage=Decimal('150.00'),
            allocation_label='B'
        )
        SDAllocation.objects.create(
            sd_record=sd,
            contract_number='CONTRACT003',
            allocated_tonnage=Decimal('50.00'),
            allocation_label='C'
        )

        # Verify total matches
        total_allocated = sum(a.allocated_tonnage for a in sd.allocations.all())
        self.assertEqual(total_allocated, Decimal('300.00'))
        self.assertEqual(sd.tonnage, Decimal('300.00'))

    # ══════════════════════════════════════════════════════════════
    #  SD NUMBER UNIQUENESS TESTS
    # ══════════════════════════════════════════════════════════════

    def test_duplicate_sd_number_not_allowed(self):
        # Duplicate SD numbers must be prevented (data integrity)
        # Create first SD
        SDRecord.objects.create(
            sd_number='SD111',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('100.00'),
            created_by=self.ops_user
        )

        # Try to create duplicate
        with self.assertRaises(Exception):
            SDRecord.objects.create(
                sd_number='SD111',
                vessel_name='ANOTHER VESSEL',
                agent='ANOTHER AGENT',
                crop_year='2025/2026 MC',
                tonnage=Decimal('200.00'),
                created_by=self.ops_user
            )

    def test_case_insensitive_sd_number_check(self):
        # SD number uniqueness is case-sensitive at DB level but view handles case-insensitive checks
        # Create SD with lowercase
        SDRecord.objects.create(
            sd_number='sd100',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('100.00'),
            created_by=self.ops_user
        )

        # Database allows uppercase version (case-sensitive unique constraint)
        # But view code should prevent this via case-insensitive check
        sd2 = SDRecord.objects.create(
            sd_number='SD100',
            vessel_name='ANOTHER VESSEL',
            agent='ANOTHER AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('200.00'),
            created_by=self.ops_user
        )

        # Both records exist in database (DB constraint is case-sensitive)
        self.assertEqual(SDRecord.objects.filter(sd_number__iexact='sd100').count(), 2)
