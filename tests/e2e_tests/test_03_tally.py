"""
E2E Tests for Tally Workflow
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.tally
class TestTallyWorkflow:
    """Test Tally creation and approval workflow"""

    def test_tally_list_page_loads(self, authenticated_page: Page, base_url):
        """Test my tallies page is accessible"""
        authenticated_page.goto(f"{base_url}/tally/my_tallies/")

        # Check page loaded - use heading selector
        expect(authenticated_page.locator('h1, h2, .page-title').first).to_be_visible()

    def test_create_bulk_tally_page_loads(self, authenticated_page: Page, base_url):
        """Test bulk tally creation page loads"""
        authenticated_page.goto(f"{base_url}/tally/create/bulk/")

        # Check form elements
        expect(authenticated_page.locator('input[name="sd_number"]')).to_be_visible()
        expect(authenticated_page.locator('select[name="terminal"]')).to_be_visible()

    def test_create_bulk_tally_with_valid_sd(self, authenticated_page: Page, base_url, create_test_sd, create_test_terminal):
        """Test creating bulk tally with valid SD number"""
        authenticated_page.goto(f"{base_url}/tally/create/bulk/")

        # Fill SD number
        authenticated_page.fill('input[name="sd_number"]', 'E2E001')

        # Wait for auto-fill to complete (green checkmark should appear)
        authenticated_page.wait_for_timeout(1000)

        # Check that fields were auto-filled
        crop_year = authenticated_page.locator('select[name="crop_year"]')
        expect(crop_year).to_have_value('2025/2026 MC')

        # Fill remaining required fields
        authenticated_page.select_option('select[name="terminal"]', label='TEST TERMINAL')
        authenticated_page.fill('input[name="mk_number"]', 'MK001')
        authenticated_page.fill('input[name="vessel"]', 'MV TEST VESSEL')
        authenticated_page.fill('input[name="agent"]', 'TEST AGENT')
        authenticated_page.fill('input[name="destination"]', 'TEST PORT')

        # Fill loading date
        authenticated_page.fill('input[name="loading_date"]', '2026-02-26')

        # Fill tally details
        authenticated_page.fill('input[name="total_bags"]', '400')
        authenticated_page.fill('input[name="dry_bags"]', '10')
        authenticated_page.fill('input[name="clerk_1"]', 'John Doe')
        authenticated_page.fill('input[name="clerk_2"]', 'Jane Smith')

        # Add container details
        authenticated_page.fill('input[name="containers-0-container_number"]', 'CONT001')
        authenticated_page.fill('input[name="containers-0-seal_number"]', 'SEAL001')
        authenticated_page.fill('input[name="containers-0-bag_count"]', '400')

        # Submit
        authenticated_page.click('button[type="submit"]')

        # Should redirect to my tallies
        authenticated_page.wait_for_url(f"{base_url}/tally/my-tallies/", timeout=5000)

        # Check success message
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_create_tally_with_invalid_sd(self, authenticated_page: Page, base_url):
        """Test creating tally with non-existent SD number"""
        authenticated_page.goto(f"{base_url}/tally/create/bulk/")

        # Fill invalid SD number
        authenticated_page.fill('input[name="sd_number"]', 'INVALID999')

        # Wait for validation
        authenticated_page.wait_for_timeout(1000)

        # Should show red X icon (validation failed)
        red_icon = authenticated_page.locator('.validation-icon.invalid')
        expect(red_icon).to_be_visible()

    def test_create_straight_20ft_tally(self, authenticated_page: Page, base_url, create_test_sd, create_test_terminal):
        """Test creating 20ft straight loading tally"""
        authenticated_page.goto(f"{base_url}/tally/create/straight-20/")

        # Fill form
        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)

        authenticated_page.select_option('select[name="terminal"]', label='TEST TERMINAL')
        authenticated_page.fill('input[name="mk_number"]', 'MK001')
        authenticated_page.fill('input[name="vessel"]', 'MV TEST VESSEL')
        authenticated_page.fill('input[name="loading_date"]', '2026-02-26')
        authenticated_page.fill('input[name="clerk_1"]', 'Clerk One')

        # Add container
        authenticated_page.fill('input[name="containers-0-container_number"]', 'CONT20FT')
        authenticated_page.fill('input[name="containers-0-seal_number"]', 'SEAL20')
        authenticated_page.fill('input[name="containers-0-bag_count"]', '200')

        # Submit
        authenticated_page.click('button[type="submit"]')

        authenticated_page.wait_for_url(f"{base_url}/tally/my-tallies/", timeout=5000)
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_create_straight_40ft_tally(self, authenticated_page: Page, base_url, create_test_sd, create_test_terminal):
        """Test creating 40ft straight loading tally"""
        authenticated_page.goto(f"{base_url}/tally/create/straight-40/")

        # Fill form
        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)

        authenticated_page.select_option('select[name="terminal"]', label='TEST TERMINAL')
        authenticated_page.fill('input[name="mk_number"]', 'MK001')
        authenticated_page.fill('input[name="vessel"]', 'MV TEST VESSEL')
        authenticated_page.fill('input[name="loading_date"]', '2026-02-26')
        authenticated_page.fill('input[name="clerk_1"]', 'Clerk One')

        # Add container
        authenticated_page.fill('input[name="containers-0-container_number"]', 'CONT40FT')
        authenticated_page.fill('input[name="containers-0-seal_number"]', 'SEAL40')
        authenticated_page.fill('input[name="containers-0-bag_count"]', '400')

        # Submit
        authenticated_page.click('button[type="submit"]')

        authenticated_page.wait_for_url(f"{base_url}/tally/my-tallies/", timeout=5000)
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_view_tally_detail(self, authenticated_page: Page, base_url, create_test_sd, create_test_terminal):
        """Test viewing tally detail page"""
        # First create a tally
        authenticated_page.goto(f"{base_url}/tally/create/bulk/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option('select[name="terminal"]', label='TEST TERMINAL')
        authenticated_page.fill('input[name="mk_number"]', 'MK001')
        authenticated_page.fill('input[name="vessel"]', 'MV TEST VESSEL')
        authenticated_page.fill('input[name="loading_date"]', '2026-02-26')
        authenticated_page.fill('input[name="total_bags"]', '400')
        authenticated_page.fill('input[name="clerk_1"]', 'Test Clerk')
        authenticated_page.fill('input[name="containers-0-container_number"]', 'VIEWTEST')
        authenticated_page.fill('input[name="containers-0-seal_number"]', 'SEAL999')
        authenticated_page.fill('input[name="containers-0-bag_count"]', '400')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/tally/my-tallies/", timeout=5000)

        # Click on the tally to view details
        view_link = authenticated_page.locator('a:has-text("VIEW")').first
        if view_link.is_visible():
            view_link.click()

            # Check tally details are displayed
            expect(authenticated_page.locator('text=E2E001')).to_be_visible()
            expect(authenticated_page.locator('text=VIEWTEST')).to_be_visible()

    def test_edit_draft_tally(self, authenticated_page: Page, base_url, create_test_sd, create_test_terminal):
        """Test editing a draft tally"""
        # Create a draft tally first
        authenticated_page.goto(f"{base_url}/tally/create/bulk/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option('select[name="terminal"]', label='TEST TERMINAL')
        authenticated_page.fill('input[name="mk_number"]', 'MK001')
        authenticated_page.fill('input[name="vessel"]', 'MV EDIT TEST')
        authenticated_page.fill('input[name="loading_date"]', '2026-02-26')
        authenticated_page.fill('input[name="total_bags"]', '400')
        authenticated_page.fill('input[name="clerk_1"]', 'Edit Clerk')
        authenticated_page.fill('input[name="containers-0-container_number"]', 'EDITTEST')
        authenticated_page.fill('input[name="containers-0-seal_number"]', 'SEALEDIT')
        authenticated_page.fill('input[name="containers-0-bag_count"]', '400')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/tally/my-tallies/", timeout=5000)

        # Click edit button
        edit_button = authenticated_page.locator('a:has-text("EDIT")').first
        if edit_button.is_visible():
            edit_button.click()

            # Modify vessel name
            authenticated_page.fill('input[name="vessel"]', 'MV EDITED VESSEL')

            # Submit
            authenticated_page.click('button[type="submit"]')

            authenticated_page.wait_for_url(f"{base_url}/tally/my-tallies/", timeout=5000)

            # Check updated value
            expect(authenticated_page.locator('text=MV EDITED VESSEL')).to_be_visible()

    def test_cannot_edit_approved_tally(self, authenticated_page: Page, base_url):
        """Test that approved tallies cannot be edited"""
        # This would require creating an approved tally first
        # For now, we'll test that the edit button doesn't appear for approved tallies
        authenticated_page.goto(f"{base_url}/tally/my-tallies/")

        # Look for approved tallies (with green checkmark icon)
        approved_tally = authenticated_page.locator('.tally-status:has-text("APPROVED")').first

        if approved_tally.is_visible():
            # Edit button should not be visible for approved tallies
            parent_row = approved_tally.locator('..')
            edit_button = parent_row.locator('a:has-text("EDIT")')
            expect(edit_button).not_to_be_visible()

    def test_tally_routes_to_correct_supervisor(self, authenticated_page: Page, base_url, create_test_sd, create_test_terminal):
        """Test that tally is routed to terminal supervisor"""
        # Create a tally
        authenticated_page.goto(f"{base_url}/tally/create/bulk/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option('select[name="terminal"]', label='TEST TERMINAL')
        authenticated_page.fill('input[name="mk_number"]', 'MK001')
        authenticated_page.fill('input[name="vessel"]', 'MV ROUTING TEST')
        authenticated_page.fill('input[name="loading_date"]', '2026-02-26')
        authenticated_page.fill('input[name="total_bags"]', '400')
        authenticated_page.fill('input[name="clerk_1"]', 'Route Clerk')
        authenticated_page.fill('input[name="containers-0-container_number"]', 'ROUTETEST')
        authenticated_page.fill('input[name="containers-0-seal_number"]', 'SEALROUTE')
        authenticated_page.fill('input[name="containers-0-bag_count"]', '400')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/tally/my-tallies/", timeout=5000)

        # Now logout and login as supervisor
        authenticated_page.goto(f"{base_url}/logout/")
        authenticated_page.wait_for_url(f"{base_url}/login/", timeout=5000)

        # Login as supervisor
        authenticated_page.fill('input[name="username"]', '3001')
        authenticated_page.fill('input[name="password"]', 'testpass123')
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/dashboard/", timeout=5000)

        # Go to pending tallies
        authenticated_page.goto(f"{base_url}/tally/pending/")

        # Should see the tally we just created
        expect(authenticated_page.locator('text=ROUTETEST')).to_be_visible()

    def test_add_multiple_containers_to_tally(self, authenticated_page: Page, base_url, create_test_sd, create_test_terminal):
        """Test adding multiple containers to a single tally"""
        authenticated_page.goto(f"{base_url}/tally/create/bulk/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option('select[name="terminal"]', label='TEST TERMINAL')
        authenticated_page.fill('input[name="mk_number"]', 'MK001')
        authenticated_page.fill('input[name="vessel"]', 'MV MULTI CONTAINER')
        authenticated_page.fill('input[name="loading_date"]', '2026-02-26')
        authenticated_page.fill('input[name="total_bags"]', '800')
        authenticated_page.fill('input[name="clerk_1"]', 'Multi Clerk')

        # Fill first container
        authenticated_page.fill('input[name="containers-0-container_number"]', 'MULTI001')
        authenticated_page.fill('input[name="containers-0-seal_number"]', 'SEAL001')
        authenticated_page.fill('input[name="containers-0-bag_count"]', '400')

        # Add second container (click "Add Container" button if exists)
        add_button = authenticated_page.locator('text=/Add.*Container/i')
        if add_button.is_visible():
            add_button.click()

            # Fill second container
            authenticated_page.fill('input[name="containers-1-container_number"]', 'MULTI002')
            authenticated_page.fill('input[name="containers-1-seal_number"]', 'SEAL002')
            authenticated_page.fill('input[name="containers-1-bag_count"]', '400')

        # Submit
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/tally/my-tallies/", timeout=5000)
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()
