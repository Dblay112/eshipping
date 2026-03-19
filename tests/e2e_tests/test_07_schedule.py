"""
E2E Tests for Schedule Workflow
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.schedule
class TestScheduleWorkflow:
    """Test Schedule management workflow"""

    def test_schedule_view_page_loads(self, authenticated_page: Page, base_url):
        """Test schedule view page is accessible"""
        authenticated_page.goto(f"{base_url}/schedule/")

        # Check page loaded
        expect(authenticated_page.locator('text=/Schedule/i')).to_be_visible()

    def test_create_schedule_page_loads(self, authenticated_page: Page, base_url):
        """Test schedule creation page loads for authorized users"""
        authenticated_page.goto(f"{base_url}/schedule/create/")

        # Check form elements (or redirect if not authorized)
        # Superuser should have access
        expect(authenticated_page.locator('input[name="date"]')).to_be_visible()

    def test_create_schedule_with_valid_data(self, authenticated_page: Page, base_url, create_test_sd):
        """Test creating schedule with valid SD assignments"""
        authenticated_page.goto(f"{base_url}/schedule/create/")

        # Fill date
        authenticated_page.fill('input[name="date"]', '2026-02-28')

        # Fill first SD assignment
        authenticated_page.fill('input[name="assignments-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)

        # Assign staff
        authenticated_page.fill('input[name="assignments-0-staff_assigned"]', '1812')

        # Submit
        authenticated_page.click('button[type="submit"]')

        # Should redirect to schedule view
        authenticated_page.wait_for_url(f"{base_url}/schedule/**", timeout=5000)

        # Check success message
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_create_schedule_with_invalid_sd(self, authenticated_page: Page, base_url):
        """Test creating schedule with non-existent SD"""
        authenticated_page.goto(f"{base_url}/schedule/create/")

        authenticated_page.fill('input[name="date"]', '2026-02-28')
        authenticated_page.fill('input[name="assignments-0-sd_number"]', 'INVALID999')

        # Wait for validation
        authenticated_page.wait_for_timeout(1000)

        # Should show red X icon
        red_icon = authenticated_page.locator('.validation-icon.invalid')
        expect(red_icon).to_be_visible()

    def test_create_schedule_with_multiple_assignments(self, authenticated_page: Page, base_url, create_test_sd):
        """Test creating schedule with multiple SD assignments"""
        authenticated_page.goto(f"{base_url}/schedule/create/")

        authenticated_page.fill('input[name="date"]', '2026-03-01')

        # Fill first assignment
        authenticated_page.fill('input[name="assignments-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="assignments-0-staff_assigned"]', '1812')

        # Add second assignment
        add_button = authenticated_page.locator('text=/Add.*Assignment/i')
        if add_button.is_visible():
            add_button.click()

            authenticated_page.fill('input[name="assignments-1-sd_number"]', 'E2E001')
            authenticated_page.wait_for_timeout(1000)
            authenticated_page.fill('input[name="assignments-1-staff_assigned"]', '2001')

        # Submit
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/schedule/**", timeout=5000)
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_view_schedule_by_date(self, authenticated_page: Page, base_url, create_test_sd):
        """Test viewing schedule for specific date"""
        # Create a schedule first
        authenticated_page.goto(f"{base_url}/schedule/create/")

        authenticated_page.fill('input[name="date"]', '2026-03-05')
        authenticated_page.fill('input[name="assignments-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="assignments-0-staff_assigned"]', '1812')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/schedule/**", timeout=5000)

        # Navigate to schedule view for that date
        authenticated_page.goto(f"{base_url}/schedule/?date=2026-03-05")

        # Check schedule is displayed
        expect(authenticated_page.locator('text=E2E001')).to_be_visible()
        expect(authenticated_page.locator('text=1812')).to_be_visible()

    def test_edit_schedule(self, authenticated_page: Page, base_url, create_test_sd):
        """Test editing an existing schedule"""
        # Create a schedule first
        authenticated_page.goto(f"{base_url}/schedule/create/")

        authenticated_page.fill('input[name="date"]', '2026-03-10')
        authenticated_page.fill('input[name="assignments-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="assignments-0-staff_assigned"]', '1812')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/schedule/**", timeout=5000)

        # Find and click edit button
        edit_button = authenticated_page.locator('a:has-text("EDIT")').first
        if edit_button.is_visible():
            edit_button.click()

            # Modify staff assignment
            authenticated_page.fill('input[name="assignments-0-staff_assigned"]', '2001')

            # Submit
            authenticated_page.click('button[type="submit"]')
            authenticated_page.wait_for_url(f"{base_url}/schedule/**", timeout=5000)

            # Check updated value
            expect(authenticated_page.locator('text=2001')).to_be_visible()

    def test_delete_schedule(self, authenticated_page: Page, base_url, create_test_sd):
        """Test deleting a schedule"""
        # Create a schedule first
        authenticated_page.goto(f"{base_url}/schedule/create/")

        authenticated_page.fill('input[name="date"]', '2026-03-15')
        authenticated_page.fill('input[name="assignments-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="assignments-0-staff_assigned"]', '1812')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/schedule/**", timeout=5000)

        # Find and click delete button
        delete_button = authenticated_page.locator('a[href*="/delete/"]').first
        if delete_button.is_visible():
            delete_button.click()

            # Confirm deletion
            authenticated_page.click('button[type="submit"]')
            authenticated_page.wait_for_url(f"{base_url}/schedule/", timeout=5000)

            # Check success message
            expect(authenticated_page.locator('text=/deleted/i')).to_be_visible()

    def test_terminal_schedule_page_loads(self, authenticated_page: Page, base_url):
        """Test terminal schedule page is accessible"""
        authenticated_page.goto(f"{base_url}/schedule/terminal/")

        # Check page loaded
        expect(authenticated_page.locator('text=/Terminal/i')).to_be_visible()

    def test_create_terminal_schedule(self, authenticated_page: Page, base_url, supervisor_user):
        """Test creating terminal schedule"""
        authenticated_page.goto(f"{base_url}/schedule/terminal/create/")

        # Fill terminal name
        authenticated_page.fill('input[name="terminal_name"]', 'NEW TERMINAL')

        # Fill supervisor staff number
        authenticated_page.fill('input[name="supervisor"]', '3001')

        # Submit
        authenticated_page.click('button[type="submit"]')

        # Should redirect to terminal schedule list
        authenticated_page.wait_for_url(f"{base_url}/schedule/terminal/", timeout=5000)

        # Check success message
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_schedule_calendar_navigation(self, authenticated_page: Page, base_url):
        """Test navigating schedule calendar"""
        authenticated_page.goto(f"{base_url}/schedule/")

        # Check calendar is displayed
        expect(authenticated_page.locator('.calendar')).to_be_visible()

        # Click next month button if exists
        next_button = authenticated_page.locator('button:has-text("Next")')
        if next_button.is_visible():
            next_button.click()

            # Calendar should update
            authenticated_page.wait_for_timeout(500)

        # Click previous month button if exists
        prev_button = authenticated_page.locator('button:has-text("Previous")')
        if prev_button.is_visible():
            prev_button.click()

            # Calendar should update
            authenticated_page.wait_for_timeout(500)

    def test_only_manager_can_create_schedule(self, authenticated_page: Page, base_url):
        """Test that only managers/superusers can create schedules"""
        # Logout and login as non-manager user
        authenticated_page.goto(f"{base_url}/logout/")
        authenticated_page.wait_for_url(f"{base_url}/login/", timeout=5000)

        authenticated_page.fill('input[name="username"]', '2001')
        authenticated_page.fill('input[name="password"]', 'testpass123')
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/dashboard/", timeout=5000)

        # Try to access schedule create page
        authenticated_page.goto(f"{base_url}/schedule/create/")

        # Should be redirected or show error
        # Either stays on dashboard or shows permission denied
        current_url = authenticated_page.url
        assert '/schedule/create/' not in current_url or authenticated_page.locator('text=/permission/i').is_visible()
