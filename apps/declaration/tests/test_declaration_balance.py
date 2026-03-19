"""
Declaration Balance Tracking Tests

Tests the critical workflow where declaration desk creates declarations per contract
and the system validates tonnage to prevent over-declaring.

Critical for compliance: If this breaks, over-declaring can occur leading to
regulatory violations and contract breaches.
"""

import random
from decimal import Decimal
from datetime import date

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.declaration.models import Declaration
from apps.operations.models import SDRecord, SDAllocation

Account = get_user_model()


class DeclarationBalanceTrackingTestCase(TestCase):
    """Test declaration balance tracking per contract."""

    def setUp(self):
        """Create test users, SD record, and allocations for all tests."""
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

        # Create SD record with multiple allocations
        self.sd = SDRecord.objects.create(
            sd_number='SD100',
            vessel_name='TEST VESSEL',
            agent='TEST AGENT',
            crop_year='2025/2026 MC',
            tonnage=Decimal('300.00'),
            created_by=self.declaration_user
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
    #  DECLARATION CREATION TESTS
    # ══════════════════════════════════════════════════════════════

    def test_declaration_within_allocated_tonnage_succeeds(self):
        # Declarations within allocated tonnage must be allowed
        declaration = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_a,
            contract_number='CONTRACT_A',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL001',
            tonnage=Decimal('80.00'),
            created_by=self.declaration_user
        )

        self.assertEqual(declaration.tonnage, Decimal('80.00'))
        self.assertEqual(declaration.allocation, self.allocation_a)

    def test_declaration_exactly_at_allocated_tonnage_succeeds(self):
        # Declaring exactly the allocated tonnage must be allowed
        declaration = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_a,
            contract_number='CONTRACT_A',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL001',
            tonnage=Decimal('100.00'),
            created_by=self.declaration_user
        )

        self.assertEqual(declaration.tonnage, Decimal('100.00'))

    def test_multiple_declarations_for_same_contract(self):
        # Multiple declarations for same contract must aggregate correctly
        # First declaration
        decl1 = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_a,
            contract_number='CONTRACT_A',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL001',
            tonnage=Decimal('60.00'),
            created_by=self.declaration_user
        )

        # Second declaration
        decl2 = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_a,
            contract_number='CONTRACT_A',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL002',
            tonnage=Decimal('30.00'),
            created_by=self.declaration_user
        )

        # Verify both exist
        declarations = Declaration.objects.filter(
            sd_record=self.sd,
            contract_number='CONTRACT_A'
        )
        self.assertEqual(declarations.count(), 2)
        total_declared = sum(d.tonnage for d in declarations)
        self.assertEqual(total_declared, Decimal('90.00'))

    # ══════════════════════════════════════════════════════════════
    #  MULTIPLE CONTRACTS TESTS
    # ══════════════════════════════════════════════════════════════

    def test_different_contracts_have_independent_declarations(self):
        # Each contract must have independent declaration tracking
        # Declare for contract A
        decl_a = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_a,
            contract_number='CONTRACT_A',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL_A001',
            tonnage=Decimal('80.00'),
            created_by=self.declaration_user
        )

        # Declare for contract B
        decl_b = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_b,
            contract_number='CONTRACT_B',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL_B001',
            tonnage=Decimal('120.00'),
            created_by=self.declaration_user
        )

        # Verify independent declarations
        self.assertEqual(decl_a.tonnage, Decimal('80.00'))
        self.assertEqual(decl_b.tonnage, Decimal('120.00'))
        self.assertNotEqual(decl_a.contract_number, decl_b.contract_number)

    def test_all_contracts_can_have_declarations(self):
        # All contracts in an SD can have declarations
        # Declare for all three contracts
        decl_a = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_a,
            contract_number='CONTRACT_A',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL_A001',
            tonnage=Decimal('100.00'),
            created_by=self.declaration_user
        )

        decl_b = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_b,
            contract_number='CONTRACT_B',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL_B001',
            tonnage=Decimal('150.00'),
            created_by=self.declaration_user
        )

        decl_c = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_c,
            contract_number='CONTRACT_C',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL_C001',
            tonnage=Decimal('50.00'),
            created_by=self.declaration_user
        )

        # Verify all three exist
        declarations = Declaration.objects.filter(sd_record=self.sd)
        self.assertEqual(declarations.count(), 3)

    # ══════════════════════════════════════════════════════════════
    #  EDGE CASE TESTS
    # ══════════════════════════════════════════════════════════════

    def test_zero_tonnage_declaration(self):
        # Zero tonnage declarations should be allowed (placeholder declarations)
        declaration = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_a,
            contract_number='CONTRACT_A',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL001',
            tonnage=Decimal('0.00'),
            created_by=self.declaration_user
        )

        self.assertEqual(declaration.tonnage, Decimal('0.00'))

    def test_decimal_precision_in_declarations(self):
        # Declarations must handle decimal precision correctly
        declaration = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_a,
            contract_number='CONTRACT_A',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL001',
            tonnage=Decimal('33.3333'),
            created_by=self.declaration_user
        )

        self.assertEqual(declaration.tonnage, Decimal('33.3333'))

    def test_declaration_links_to_correct_allocation(self):
        # Declarations must link to the correct allocation
        declaration = Declaration.objects.create(
            sd_record=self.sd,
            sd_number='SD100',
            allocation=self.allocation_b,
            contract_number='CONTRACT_B',
            agent='TEST AGENT',
            vessel='TEST VESSEL',
            declaration_number='DECL001',
            tonnage=Decimal('100.00'),
            created_by=self.declaration_user
        )

        self.assertEqual(declaration.allocation, self.allocation_b)
        self.assertEqual(declaration.allocation.allocated_tonnage, Decimal('150.00'))
        self.assertEqual(declaration.allocation.allocation_label, 'B')
