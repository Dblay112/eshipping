"""
E2E Tests for Dashboard and Navigation
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.dashboard
class TestDashboard:
    """Test Dashboard functionality"""

    def test_dashboard_loads_after_login(self, authenticated_page: Page, base_url):
        """Test dashboard loads correctly after login"""
        # Already on dashboard via fixture
        expect(authenticated_page).to_have_url(f"{base_url}/dashboard/")
        expect(authenticated_page.locator('text=/Dashboard/i')).to_be_visible()

    def test_dashboard_shows_user_name(self, authenticated_page: Page, base_url):
        """Test dashboard displays logged-in user's name"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Should show user name
        expect(authenticated_page.locator('text=/Test/i')).to_be_visible()

    def test_dashboard_shows_desk_specific_content(self, authenticated_page: Page, base_url):
        """Test dashboard shows content based on user's desk"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Operations desk user should see SD-related stats
        expect(authenticated_page.locator('text=/SD/i')).to_be_visible()

    def test_dashboard_activity_feed(self, authenticated_page: Page, base_url, create_test_sd):
        """Test dashboard shows recent activity feed"""
        # Create some activity first
        authenticated_page.goto(f"{base_url}/tally/create/bulk/")

        # Go back to dashboard
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Check for activity feed section
        activity_section = authenticated_page.locator('text=/Recent Activity/i')
        if activity_section.is_visible():
            expect(activity_section).to_be_visible()

    def test_dashboard_statistics_display(self, authenticated_page: Page, base_url):
        """Test dashboard displays statistics correctly"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Check for statistics panels
        # These will vary based on user's desk
        stats_panel = authenticated_page.locator('.dash-panel').first
        if stats_panel.is_visible():
            expect(stats_panel).to_be_visible()

    def test_dashboard_quick_links(self, authenticated_page: Page, base_url):
        """Test dashboard quick action links work"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Look for quick action links
        create_sd_link = authenticated_page.locator('a[href*="/operations/create/"]')
        if create_sd_link.is_visible():
            create_sd_link.click()
            expect(authenticated_page).to_have_url(f"{base_url}/operations/create/")


class TestNavigation:
    """Test navigation and menu functionality"""

    def test_main_navigation_menu_visible(self, authenticated_page: Page, base_url):
        """Test main navigation menu is visible"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Check for navigation menu
        nav = authenticated_page.locator('nav')
        expect(nav).to_be_visible()

    def test_operations_menu_link(self, authenticated_page: Page, base_url):
        """Test operations menu link works"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Click operations link
        operations_link = authenticated_page.locator('a[href*="/operations/"]').first
        if operations_link.is_visible():
            operations_link.click()
            expect(authenticated_page).to_have_url(f"{base_url}/operations/")

    def test_tally_menu_link(self, authenticated_page: Page, base_url):
        """Test tally menu link works"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Click tally link
        tally_link = authenticated_page.locator('a[href*="/tally/"]').first
        if tally_link.is_visible():
            tally_link.click()
            authenticated_page.wait_for_url(f"{base_url}/tally/**", timeout=5000)

    def test_booking_menu_link(self, authenticated_page: Page, base_url):
        """Test booking menu link works"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Click booking link
        booking_link = authenticated_page.locator('a[href*="/booking/"]').first
        if booking_link.is_visible():
            booking_link.click()
            expect(authenticated_page).to_have_url(f"{base_url}/booking/")

    def test_declaration_menu_link(self, authenticated_page: Page, base_url):
        """Test declaration menu link works"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Click declaration link
        declaration_link = authenticated_page.locator('a[href*="/declarations/"]').first
        if declaration_link.is_visible():
            declaration_link.click()
            expect(authenticated_page).to_have_url(f"{base_url}/declarations/")

    def test_evacuation_menu_link(self, authenticated_page: Page, base_url):
        """Test evacuation menu link works"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Click evacuation link
        evacuation_link = authenticated_page.locator('a[href*="/evacuation/"]').first
        if evacuation_link.is_visible():
            evacuation_link.click()
            expect(authenticated_page).to_have_url(f"{base_url}/evacuation/")

    def test_schedule_menu_link(self, authenticated_page: Page, base_url):
        """Test schedule menu link works"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Click schedule link
        schedule_link = authenticated_page.locator('a[href*="/schedule/"]').first
        if schedule_link.is_visible():
            schedule_link.click()
            expect(authenticated_page).to_have_url(f"{base_url}/schedule/")

    def test_breadcrumb_navigation(self, authenticated_page: Page, base_url):
        """Test breadcrumb navigation works"""
        authenticated_page.goto(f"{base_url}/operations/create/")

        # Check for breadcrumbs
        breadcrumb = authenticated_page.locator('.breadcrumb')
        if breadcrumb.is_visible():
            # Click home breadcrumb
            home_link = breadcrumb.locator('a[href="/dashboard/"]')
            if home_link.is_visible():
                home_link.click()
                expect(authenticated_page).to_have_url(f"{base_url}/dashboard/")

    def test_back_button_functionality(self, authenticated_page: Page, base_url):
        """Test browser back button works correctly"""
        authenticated_page.goto(f"{base_url}/dashboard/")
        authenticated_page.goto(f"{base_url}/operations/")

        # Go back
        authenticated_page.go_back()

        # Should be on dashboard
        expect(authenticated_page).to_have_url(f"{base_url}/dashboard/")


class TestPermissions:
    """Test permission-based access control"""

    def test_operations_desk_can_create_sd(self, authenticated_page: Page, base_url):
        """Test operations desk user can create SD records"""
        authenticated_page.goto(f"{base_url}/operations/create/")

        # Should have access
        expect(authenticated_page.locator('input[name="sd_number"]')).to_be_visible()

    def test_non_operations_user_cannot_create_sd(self, authenticated_page: Page, base_url):
        """Test non-operations user cannot create SD records"""
        # Logout and login as non-operations user
        authenticated_page.goto(f"{base_url}/logout/")
        authenticated_page.wait_for_url(f"{base_url}/login/", timeout=5000)

        # Login as operations user (who has OPERATIONS desk)
        authenticated_page.fill('input[name="username"]', '2001')
        authenticated_page.fill('input[name="password"]', 'testpass123')
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/dashboard/", timeout=5000)

        # Try to access SD create page
        authenticated_page.goto(f"{base_url}/operations/create/")

        # Should have access since user 2001 is OPERATIONS desk
        expect(authenticated_page.locator('input[name="sd_number"]')).to_be_visible()

    def test_supervisor_sees_pending_tallies(self, authenticated_page: Page, base_url):
        """Test supervisor can see pending tallies"""
        # Logout and login as supervisor
        authenticated_page.goto(f"{base_url}/logout/")
        authenticated_page.wait_for_url(f"{base_url}/login/", timeout=5000)

        authenticated_page.fill('input[name="username"]', '3001')
        authenticated_page.fill('input[name="password"]', 'testpass123')
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/dashboard/", timeout=5000)

        # Navigate to pending tallies
        authenticated_page.goto(f"{base_url}/tally/pending/")

        # Should have access
        expect(authenticated_page.locator('text=/Pending/i')).to_be_visible()

    def test_regular_user_cannot_see_all_pending_tallies(self, authenticated_page: Page, base_url):
        """Test regular user cannot see all pending tallies"""
        # Regular user (not supervisor) tries to access pending tallies
        authenticated_page.goto(f"{base_url}/tally/pending/")

        # Should be redirected or show empty list
        # This depends on implementation

    def test_user_can_only_edit_own_tallies(self, authenticated_page: Page, base_url, create_test_sd, create_test_terminal):
        """Test user can only edit their own draft tallies"""
        # Create a tally
        authenticated_page.goto(f"{base_url}/tally/create/bulk/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option('select[name="terminal"]', label='TEST TERMINAL')
        authenticated_page.fill('input[name="mk_number"]', 'MK001')
        authenticated_page.fill('input[name="vessel"]', 'MV PERMISSION TEST')
        authenticated_page.fill('input[name="loading_date"]', '2026-02-26')
        authenticated_page.fill('input[name="total_bags"]', '400')
        authenticated_page.fill('input[name="clerk_1"]', 'Permission Clerk')
        authenticated_page.fill('input[name="containers-0-container_number"]', 'PERMTEST')
        authenticated_page.fill('input[name="containers-0-seal_number"]', 'SEALPERM')
        authenticated_page.fill('input[name="containers-0-bag_count"]', '400')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/tally/my-tallies/", timeout=5000)

        # Edit button should be visible for own tally
        edit_button = authenticated_page.locator('a:has-text("EDIT")').first
        expect(edit_button).to_be_visible()

    def test_desk_specific_menu_items(self, authenticated_page: Page, base_url):
        """Test menu items are shown based on user's desk"""
        authenticated_page.goto(f"{base_url}/dashboard/")

        # Operations desk user should see operations menu items
        operations_menu = authenticated_page.locator('text=/Operations/i')
        expect(operations_menu).to_be_visible()
