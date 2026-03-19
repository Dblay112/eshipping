"""
CMC Shipping Portal - Comprehensive Verification Report
Generated: February 26, 2026
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class BasicViewsTest(TestCase):
    """Basic tests for all major views"""

    def setUp(self):
        """Create test user using the actual Account model structure"""
        self.client = Client()
        # Create user the correct way for this project
        self.user = User.objects.create(
            staff_number=9001,
            first_name='Test',
            last_name='User',
            email='test@example.com',
            location='TEMA'
        )
        self.user.set_password('testpass123')
        self.user.desk = 'OPERATIONS'
        self.user.save()

        # Login
        self.client.login(staff_number=9001, password='testpass123')

    def test_login_page_accessible(self):
        """Test login page loads"""
        self.client.logout()
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_auth(self):
        """Test dashboard redirects when not logged in"""
        self.client.logout()
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_loads_authenticated(self):
        """Test dashboard loads for authenticated user"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_operations_list_loads(self):
        """Test operations list page"""
        response = self.client.get(reverse('operations_list'))
        self.assertEqual(response.status_code, 200)

    def test_my_tallies_loads(self):
        """Test my tallies page"""
        response = self.client.get(reverse('my_tallies'))
        self.assertEqual(response.status_code, 200)

    def test_booking_list_loads(self):
        """Test booking list page"""
        response = self.client.get(reverse('booking_list'))
        self.assertEqual(response.status_code, 200)

    def test_declaration_list_loads(self):
        """Test declaration list page"""
        response = self.client.get(reverse('declaration_list'))
        self.assertEqual(response.status_code, 200)

    def test_evacuation_list_loads(self):
        """Test evacuation list page"""
        response = self.client.get(reverse('evacuation_list'))
        self.assertEqual(response.status_code, 200)

    def test_schedule_view_loads(self):
        """Test schedule view page"""
        response = self.client.get(reverse('schedule_view'))
        self.assertEqual(response.status_code, 200)


class APIEndpointsTest(TestCase):
    """Test API endpoints return correct responses"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            staff_number=9002,
            first_name='API',
            last_name='Tester',
            email='api@example.com',
            location='TEMA'
        )
        self.user.set_password('testpass123')
        self.user.save()
        self.client.login(staff_number=9002, password='testpass123')

    def test_sd_details_api_invalid_sd(self):
        """Test SD details API with invalid SD"""
        response = self.client.get(reverse('sd_details_json'), {'sd_number': 'INVALID999'})
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data.get('exists', True))

    def test_sd_details_api_requires_sd_number(self):
        """Test SD details API requires sd_number parameter"""
        response = self.client.get(reverse('sd_details_json'))
        self.assertEqual(response.status_code, 400)
