"""
Integration tests for CMC Shipping Portal views
Tests all major views for correct HTTP responses and template rendering
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date

User = get_user_model()


class ViewsIntegrationTest(TestCase):
    """Test all major views return correct status codes and use correct templates"""

    def setUp(self):
        """Create test user and login"""
        self.client = Client()
        self.user = User.objects.create(
            staff_number=9003,
            first_name='Test',
            last_name='User',
            email='test@example.com',
            rank='Officer',
            desk='OPERATIONS',
            location='TEMA'
        )
        self.user.set_password('testpass123')
        self.user.save()
        self.client.login(staff_number=9003, password='testpass123')

    def test_login_page_loads(self):
        """Test login page is accessible"""
        self.client.logout()
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_dashboard_requires_login(self):
        """Test dashboard redirects when not logged in"""
        self.client.logout()
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_loads_for_authenticated_user(self):
        """Test dashboard loads with correct template"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/dashboard.html')
        # Check context variables
        self.assertIn('today', response.context)
        self.assertIn('desk', response.context)

    def test_operations_list_loads(self):
        """Test operations SD list page loads"""
        response = self.client.get(reverse('operations_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'operations/operations_list.html')

    def test_schedule_view_loads(self):
        """Test schedule view page loads"""
        response = self.client.get(reverse('schedule_view'))
        self.assertEqual(response.status_code, 200)

    def test_my_tallies_loads(self):
        """Test my tallies page loads"""
        response = self.client.get(reverse('my_tallies'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tally_details/my_tallies.html')

    def test_booking_list_loads(self):
        """Test booking list page loads"""
        response = self.client.get(reverse('booking_list'))
        self.assertEqual(response.status_code, 200)

    def test_declaration_list_loads(self):
        """Test declaration list page loads"""
        response = self.client.get(reverse('declaration_list'))
        self.assertEqual(response.status_code, 200)

    def test_evacuation_list_loads(self):
        """Test evacuation list page loads"""
        response = self.client.get(reverse('evacuation_list'))
        self.assertEqual(response.status_code, 200)

    def test_api_sd_details_endpoint(self):
        """Test SD details API endpoint"""
        from sd_tracker.models import SDRecord, SDAllocation

        # Create test SD
        sd = SDRecord.objects.create(
            sd_number='TEST100',
            vessel_name='Test Vessel',
            agent='Test Agent',
            buyer='Test Buyer',
            crop_year='2025/2026 MC',
            tonnage=Decimal('100.00'),
            container_size='40ft',
            loading_type='BULK',
            port_of_loading='TEMA',
            created_by=self.user
        )

        SDAllocation.objects.create(
            sd_record=sd,
            allocation_label='PT',
            contract_number='TEST001',
            mk_number='MK001',
            allocated_tonnage=Decimal('100.00'),
            buyer='Test Buyer',
            agent='Test Agent'
        )

        response = self.client.get(reverse('sd_details_json'), {'sd_number': 'TEST100'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['exists'])
        self.assertEqual(data['sd_number'], 'TEST100')
        self.assertEqual(data['vessel_name'], 'Test Vessel')
        self.assertEqual(len(data['allocations']), 1)

    def test_api_bookings_by_sd_endpoint(self):
        """Test bookings by SD API endpoint"""
        from sd_tracker.models import SDRecord
        from ebooking.models import BookingRecord

        # Create test SD
        sd = SDRecord.objects.create(
            sd_number='TEST200',
            vessel_name='Test Vessel 2',
            agent='Test Agent 2',
            buyer='Test Buyer',
            crop_year='2025/2026 MC',
            tonnage=Decimal('200.00'),
            container_size='40ft',
            loading_type='BULK',
            port_of_loading='TEMA',
            created_by=self.user
        )

        # Create booking
        BookingRecord.objects.create(
            sd_record=sd,
            sd_number='TEST200',
            vessel='Test Vessel 2',
            agent='Test Agent 2',
            created_by=self.user
        )

        response = self.client.get(reverse('bookings_by_sd_json'), {'sd_number': 'TEST200'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['bookings']), 1)
        self.assertEqual(data['bookings'][0]['vessel'], 'Test Vessel 2')


class TemplateContextTest(TestCase):
    """Test that views pass correct context variables to templates"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            staff_number=9004,
            first_name='Context',
            last_name='Tester',
            email='context@example.com',
            rank='Officer',
            desk='OPERATIONS',
            location='TEMA'
        )
        self.user.set_password('testpass123')
        self.user.save()
        self.client.login(staff_number=9004, password='testpass123')

    def test_dashboard_context_variables(self):
        """Test dashboard passes all required context variables"""
        response = self.client.get(reverse('dashboard'))

        # Required context variables
        required_vars = ['today', 'now', 'desk', 'all_desks']
        for var in required_vars:
            self.assertIn(var, response.context, f"Missing context variable: {var}")

    def test_operations_list_context(self):
        """Test operations list passes correct context"""
        response = self.client.get(reverse('operations_list'))

        self.assertIn('sds', response.context)
        self.assertIn('can_manage', response.context)

    def test_my_tallies_context(self):
        """Test my tallies passes correct context"""
        response = self.client.get(reverse('my_tallies'))

        self.assertIn('tallies', response.context)
        self.assertIn('total_tallies', response.context)


class PermissionsTest(TestCase):
    """Test permission checks work correctly"""

    def setUp(self):
        self.client = Client()

    def test_operations_create_requires_operations_desk(self):
        """Test only operations desk can create SD records"""
        # Create non-operations user
        user = User.objects.create(
            staff_number=9005,
            first_name='Non',
            last_name='Operations',
            email='nonops@example.com',
            rank='Officer',
            desk='EBOOKING',
            location='TEMA'
        )
        user.set_password('testpass123')
        user.save()
        self.client.login(staff_number=9005, password='testpass123')

        response = self.client.get(reverse('sd_create'))
        # Should redirect or show error
        self.assertIn(response.status_code, [302, 403])

    def test_tally_edit_blocked_for_approved(self):
        """Test approved tallies cannot be edited"""
        from tally.models import TallyInfo, Terminal

        user = User.objects.create(
            staff_number=9006,
            first_name='Tally',
            last_name='Creator',
            email='tally@example.com',
            rank='Officer',
            desk='OTHER',
            location='TEMA'
        )
        user.set_password('testpass123')
        user.save()
        self.client.login(staff_number=9006, password='testpass123')

        # Create terminal
        terminal = Terminal.objects.create(name='Test Terminal')

        # Create approved tally
        tally = TallyInfo.objects.create(
            tally_number=9100001,
            tally_type='BULK',
            crop_year='2025/2026 MC',
            sd_number='TEST300',
            mk_number='MK001',
            vessel='Test Vessel',
            agent='Test Agent',
            destination='Test Port',
            loading_date=date.today(),
            status='APPROVED',
            created_by=user,
            terminal=terminal
        )

        response = self.client.get(reverse('tally_edit', args=[tally.pk]))
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)

