"""
Booking Balance Tracking Tests

Tests the critical workflow where ebooking desk creates bookings per contract
and the system tracks balance to prevent over-booking.

Critical for financial integrity: If this breaks, over-booking can occur leading
to direct financial loss and contract violations.
"""

import random
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.ebooking.models import BookingRecord, BookingLine, BookingDetail
from apps.operations.models import SDRecord, SDAllocation

Account = get_user_model()


class BookingBalanceTrackingTestCase(TestCase):
    """Test booking balance tracking per contract."""

    def setUp(self):
        """Create test users, SD record, and allocations for all tests."""
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

        # Create SD record with multiple allocations
        self.sd = SDRecord.objects.create(
            sd_number='SD100',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('300.00'),
            created_by=self.ebooking_user
        )

        # Create allocations
        self.allocation_a = SDAllocation.objects.create(
            sd_record=self.sd,
            contract_number='CONTRACT_A',
            allocated_tonnage=Decimal('100.00'),
            allocation_label='A',
            mk_number='MK001'
        )

        self.allocation_b = SDAllocation.objects.create(
            sd_record=self.sd,
            contract_number='CONTRACT_B',
            allocated_tonnage=Decimal('150.00'),
            allocation_label='B',
            mk_number='MK002'
        )

        self.allocation_c = SDAllocation.objects.create(
            sd_record=self.sd,
            contract_number='CONTRACT_C',
            allocated_tonnage=Decimal('50.00'),
            allocation_label='C',
            mk_number='MK003'
        )

    # ══════════════════════════════════════════════════════════════
    #  BALANCE CALCULATION TESTS
    # ══════════════════════════════════════════════════════════════

    def test_initial_balance_equals_allocated_tonnage(self):
        # Before any bookings, balance must equal allocated tonnage
        # Create booking record (no details yet)
        booking = BookingRecord.objects.create(
            sd_number='SD100',
            sd_record=self.sd,
            vessel='TEST VESSEL',
            agent='TEST AGENT',
            created_by=self.ebooking_user
        )

        # Create booking line for allocation A (no allocation FK, just contract_number)
        line = BookingLine.objects.create(
            booking_record=booking,
            contract_number='CONTRACT_A'
        )

        # Balance should equal allocated tonnage (no bookings yet)
        self.assertEqual(line.contract_balance, Decimal('100.00'))

    def test_balance_decreases_after_booking(self):
        # Balance must decrease by booked amount (prevents over-booking)
        # Create booking record
        booking = BookingRecord.objects.create(
            sd_number='SD100',
            sd_record=self.sd,
            vessel='TEST VESSEL',
            agent='TEST AGENT',
            created_by=self.ebooking_user
        )

        # Create booking line
        line = BookingLine.objects.create(
            booking_record=booking,
            
            contract_number='CONTRACT_A'
        )

        # Create booking detail (60 MT booked)
        detail = BookingDetail.objects.create(
            booking_line=line,
            booking_number='BOOK001',
            bill_number='BILL001',
            tonnage_booked=Decimal('60.00')
        )

        # Balance should be 100 - 60 = 40
        self.assertEqual(line.contract_balance, Decimal('40.00'))

    def test_multiple_bookings_aggregate_correctly(self):
        # Multiple bookings for same contract must aggregate (prevents over-booking)
        # Create booking record
        booking = BookingRecord.objects.create(
            sd_number='SD100',
            sd_record=self.sd,
            vessel='TEST VESSEL',
            agent='TEST AGENT',
            created_by=self.ebooking_user
        )

        # Create booking line
        line = BookingLine.objects.create(
            booking_record=booking,
            
            contract_number='CONTRACT_A'
        )

        # Create first booking detail (60 MT)
        detail1 = BookingDetail.objects.create(
            booking_line=line,
            booking_number='BOOK001',
            bill_number='BILL001',
            tonnage_booked=Decimal('60.00')
        )

        # Create second booking detail (30 MT)
        detail2 = BookingDetail.objects.create(
            booking_line=line,
            booking_number='BOOK002',
            bill_number='BILL002',
            tonnage_booked=Decimal('30.00')
        )

        # Balance should be 100 - 60 - 30 = 10
        self.assertEqual(line.contract_balance, Decimal('10.00'))

    def test_balance_reaches_zero_when_fully_booked(self):
        # Balance must reach exactly zero when fully booked (no over/under booking)
        # Create booking record
        booking = BookingRecord.objects.create(
            sd_number='SD100',
            sd_record=self.sd,
            vessel='TEST VESSEL',
            agent='TEST AGENT',
            created_by=self.ebooking_user
        )

        # Create booking line
        line = BookingLine.objects.create(
            booking_record=booking,
            
            contract_number='CONTRACT_A'
        )

        # Book exactly the allocated amount
        detail = BookingDetail.objects.create(
            booking_line=line,
            booking_number='BOOK001',
            bill_number='BILL001',
            tonnage_booked=Decimal('100.00')
        )

        # Balance should be exactly zero
        self.assertEqual(line.contract_balance, Decimal('0.00'))

    def test_balance_negative_when_overbooked(self):
        # Balance goes negative when over-booked (validation should prevent this)
        # Create booking record
        booking = BookingRecord.objects.create(
            sd_number='SD100',
            sd_record=self.sd,
            vessel='TEST VESSEL',
            agent='TEST AGENT',
            created_by=self.ebooking_user
        )

        # Create booking line
        line = BookingLine.objects.create(
            booking_record=booking,
            
            contract_number='CONTRACT_A'
        )

        # Book more than allocated (should be prevented by validation)
        detail = BookingDetail.objects.create(
            booking_line=line,
            booking_number='BOOK001',
            bill_number='BILL001',
            tonnage_booked=Decimal('120.00')
        )

        # Balance is negative (indicates over-booking)
        self.assertEqual(line.contract_balance, Decimal('-20.00'))

    # ══════════════════════════════════════════════════════════════
    #  MULTIPLE CONTRACTS TESTS
    # ══════════════════════════════════════════════════════════════

    def test_different_contracts_have_independent_balances(self):
        # Each contract must have independent balance tracking
        # Create booking record
        booking = BookingRecord.objects.create(
            sd_number='SD100',
            sd_record=self.sd,
            vessel='TEST VESSEL',
            agent='TEST AGENT',
            created_by=self.ebooking_user
        )

        # Create booking lines for different contracts
        line_a = BookingLine.objects.create(
            booking_record=booking,
            
            contract_number='CONTRACT_A'
        )

        line_b = BookingLine.objects.create(
            booking_record=booking,
            
            contract_number='CONTRACT_B'
        )

        # Book 60 MT on contract A
        detail_a = BookingDetail.objects.create(
            booking_line=line_a,
            booking_number='BOOK001',
            bill_number='BILL001',
            tonnage_booked=Decimal('60.00')
        )

        # Book 100 MT on contract B
        detail_b = BookingDetail.objects.create(
            booking_line=line_b,
            booking_number='BOOK002',
            bill_number='BILL002',
            tonnage_booked=Decimal('100.00')
        )

        # Verify independent balances
        self.assertEqual(line_a.contract_balance, Decimal('40.00'))  # 100 - 60
        self.assertEqual(line_b.contract_balance, Decimal('50.00'))  # 150 - 100

    # ══════════════════════════════════════════════════════════════
    #  EDGE CASE TESTS
    # ══════════════════════════════════════════════════════════════

    def test_zero_tonnage_booking_does_not_affect_balance(self):
        # Zero tonnage bookings should not affect balance
        # Create booking record
        booking = BookingRecord.objects.create(
            sd_number='SD100',
            sd_record=self.sd,
            vessel='TEST VESSEL',
            agent='TEST AGENT',
            created_by=self.ebooking_user
        )

        # Create booking line
        line = BookingLine.objects.create(
            booking_record=booking,
            
            contract_number='CONTRACT_A'
        )

        # Create booking with zero tonnage
        detail = BookingDetail.objects.create(
            booking_line=line,
            booking_number='BOOK001',
            bill_number='BILL001',
            tonnage_booked=Decimal('0.00')
        )

        # Balance should still be 100
        self.assertEqual(line.contract_balance, Decimal('100.00'))

    def test_decimal_precision_in_balance_calculation(self):
        # Balance calculations must handle decimal precision correctly
        # Create booking record
        booking = BookingRecord.objects.create(
            sd_number='SD100',
            sd_record=self.sd,
            vessel='TEST VESSEL',
            agent='TEST AGENT',
            created_by=self.ebooking_user
        )

        # Create booking line
        line = BookingLine.objects.create(
            booking_record=booking,
            
            contract_number='CONTRACT_A'
        )

        # Book with decimal values
        detail1 = BookingDetail.objects.create(
            booking_line=line,
            booking_number='BOOK001',
            bill_number='BILL001',
            tonnage_booked=Decimal('33.33')
        )

        detail2 = BookingDetail.objects.create(
            booking_line=line,
            booking_number='BOOK002',
            bill_number='BILL002',
            tonnage_booked=Decimal('33.34')
        )

        # Balance should be 100 - 33.33 - 33.34 = 33.33
        self.assertEqual(line.contract_balance, Decimal('33.33'))

    def test_balance_with_no_bookings(self):
        # Contract with no bookings should show full allocated tonnage as balance
        # Create booking record
        booking = BookingRecord.objects.create(
            sd_number='SD100',
            sd_record=self.sd,
            vessel='TEST VESSEL',
            agent='TEST AGENT',
            created_by=self.ebooking_user
        )

        # Create booking line (no details)
        line = BookingLine.objects.create(
            booking_record=booking,
            
            contract_number='CONTRACT_C'
        )

        # Balance should equal allocated tonnage
        self.assertEqual(line.contract_balance, Decimal('50.00'))
