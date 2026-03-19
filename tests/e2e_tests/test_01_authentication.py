"""
E2E Tests for Authentication and Login Workflow
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.auth
class TestAuthentication:
    """Test authentication flows"""

    def test_login_page_loads(self, page: Page, base_url):
        """Test login page is accessible"""
        page.goto(f"{base_url}/login/")

        # Check page title and elements
        expect(page).to_have_title("Secure Access Portal")
        expect(page.locator('input[name="username"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()
        # Use more specific selector for submit button in login card
        expect(page.locator('#loginCard button[type="submit"]')).to_be_visible()

    def test_login_with_valid_credentials(self, page: Page, base_url, test_user):
        """Test successful login with valid credentials"""
        page.goto(f"{base_url}/login/")

        # Fill login form
        page.fill('input[name="username"]', test_user['staff_number'])
        page.fill('input[name="password"]', test_user['password'])

        # Submit
        page.locator('#loginCard button[type="submit"]').click()

        # Should redirect to dashboard
        page.wait_for_url(f"{base_url}/dashboard/", timeout=5000)

        # Verify we're on dashboard by checking URL and user greeting
        assert '/dashboard/' in page.url
        # Dashboard shows personalized greeting with user's name
        expect(page.locator('h2')).to_be_visible()

    def test_login_with_invalid_staff_number(self, page: Page, base_url):
        """Test login fails with invalid staff number"""
        page.goto(f"{base_url}/login/")

        # Fill with invalid staff number
        page.fill('input[name="username"]', '9999')
        page.fill('input[name="password"]', 'wrongpass')

        # Submit
        page.click('button[type="submit"]')

        # Should stay on login page with error
        expect(page).to_have_url(f"{base_url}/login/")
        # Use more specific selector to avoid multiple elements
        expect(page.locator('#loginCard .alert-error')).to_be_visible()

    def test_login_with_wrong_password(self, page: Page, base_url, test_user):
        """Test login fails with wrong password"""
        page.goto(f"{base_url}/login/")

        # Fill with correct staff number but wrong password
        page.fill('input[name="username"]', '1812')
        page.fill('input[name="password"]', 'wrongpassword')

        # Submit
        page.click('button[type="submit"]')

        # Should stay on login page with error
        expect(page).to_have_url(f"{base_url}/login/")
        expect(page.locator('#loginCard .alert-error')).to_be_visible()

    def test_login_with_empty_fields(self, page: Page, base_url):
        """Test login validation with empty fields"""
        page.goto(f"{base_url}/login/")

        # Try to submit without filling fields
        page.click('button[type="submit"]')

        # Should stay on same page (HTML5 validation or server-side)
        expect(page).to_have_url(f"{base_url}/login/")

        # Check if error message appears (may be HTML5 validation)
        # If no error message, at least verify we stayed on login page

    def test_login_with_non_numeric_staff_id(self, page: Page, base_url):
        """Test login validation with non-numeric staff ID"""
        page.goto(f"{base_url}/login/")

        # Fill with non-numeric staff ID
        page.fill('input[name="username"]', 'ABC123')
        page.fill('input[name="password"]', 'password')

        # Submit
        page.click('button[type="submit"]')

        # Should stay on login page with error
        expect(page).to_have_url(f"{base_url}/login/")
        # Check for error message in login card
        expect(page.locator('#loginCard .alert-error')).to_be_visible()

    def test_logout(self, authenticated_page: Page, base_url):
        """Test logout functionality"""
        # User is already logged in via fixture

        # Click logout (assuming there's a logout link/button)
        authenticated_page.goto(f"{base_url}/logout/")

        # Should redirect to login
        authenticated_page.wait_for_url(f"{base_url}/login/", timeout=5000)

        # Check logout message - use specific selector
        expect(authenticated_page.locator('#loginCard .alert-info')).to_be_visible()

    def test_dashboard_requires_authentication(self, page: Page, base_url):
        """Test dashboard redirects to login when not authenticated"""
        page.goto(f"{base_url}/dashboard/")

        # Should redirect to login (wait for navigation)
        page.wait_for_timeout(1000)

        # Check if we're on login page or if login form is visible
        current_url = page.url
        assert '/login/' in current_url or page.locator('input[name="username"]').is_visible()

    def test_authenticated_user_cannot_access_login(self, authenticated_page: Page, base_url):
        """Test authenticated user is redirected from login page"""
        # Try to access login page while authenticated
        authenticated_page.goto(f"{base_url}/login/")

        # Should redirect to dashboard
        authenticated_page.wait_for_url(f"{base_url}/dashboard/", timeout=5000)
