"""
E2E Tests for Evacuation Workflow
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.evacuation
class TestEvacuationWorkflow:
    """Test Evacuation desk workflow"""

    def test_evacuation_list_page_loads(self, authenticated_page: Page, base_url):
        """Test evacuation list page is accessible"""
        authenticated_page.goto(f"{base_url}/evacuation/")

        # Check page loaded
        expect(authenticated_page.locator('text=/Evacuation/i')).to_be_visible()

    def test_create_evacuation_page_loads(self, authenticated_page: Page, base_url):
        """Test evacuation creation page loads"""
        authenticated_page.goto(f"{base_url}/evacuation/create/")

        # Check form elements
        expect(authenticated_page.locator('input[name="date"]')).to_be_visible()

    def test_create_evacuation_with_valid_sd(self, authenticated_page: Page, base_url, create_test_sd):
        """Test creating evacuation with valid SD number"""
        authenticated_page.goto(f"{base_url}/evacuation/create/")

        # Fill date
        authenticated_page.fill('input[name="date"]', '2026-02-26')

        # Fill first entry
        authenticated_page.fill('input[name="entries-0-sd_number"]', 'E2E001')

        # Wait for SD validation and auto-fill
        authenticated_page.wait_for_timeout(1000)

        # Check green checkmark appears
        green_icon = authenticated_page.locator('.validation-icon.valid').first
        expect(green_icon).to_be_visible()

        # Vessel and agent should be auto-filled if booking exists
        # Fill remaining fields
        authenticated_page.select_option('select[name="entries-0-shift"]', 'DAY')

        # Upload Excel file
        file_input = authenticated_page.locator('input[name="entries-0-excel_file"]')
        if file_input.is_visible():
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xlsx', delete=False) as f:
                f.write('Test evacuation data')
                temp_file = f.name

            file_input.set_input_files(temp_file)

        # Submit
        authenticated_page.click('button[type="submit"]')

        # Should redirect to evacuation list
        authenticated_page.wait_for_url(f"{base_url}/evacuation/", timeout=5000)

        # Check success message
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_create_evacuation_with_invalid_sd(self, authenticated_page: Page, base_url):
        """Test creating evacuation with non-existent SD"""
        authenticated_page.goto(f"{base_url}/evacuation/create/")

        authenticated_page.fill('input[name="date"]', '2026-02-26')
        authenticated_page.fill('input[name="entries-0-sd_number"]', 'INVALID999')

        # Wait for validation
        authenticated_page.wait_for_timeout(1000)

        # Should show red X icon
        red_icon = authenticated_page.locator('.validation-icon.invalid')
        expect(red_icon).to_be_visible()

    def test_create_evacuation_with_multiple_sds(self, authenticated_page: Page, base_url, create_test_sd):
        """Test creating evacuation with multiple SD entries"""
        authenticated_page.goto(f"{base_url}/evacuation/create/")

        authenticated_page.fill('input[name="date"]', '2026-02-26')

        # Fill first entry
        authenticated_page.fill('input[name="entries-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option('select[name="entries-0-shift"]', 'DAY')

        # Add second entry
        add_button = authenticated_page.locator('text=/Add.*Entry/i')
        if add_button.is_visible():
            add_button.click()

            authenticated_page.fill('input[name="entries-1-sd_number"]', 'E2E001')
            authenticated_page.wait_for_timeout(1000)
            authenticated_page.select_option('select[name="entries-1-shift"]', 'NIGHT')

        # Submit
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/evacuation/", timeout=5000)
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_view_evacuation_details(self, authenticated_page: Page, base_url, create_test_sd):
        """Test viewing evacuation details"""
        # Create an evacuation first
        authenticated_page.goto(f"{base_url}/evacuation/create/")

        authenticated_page.fill('input[name="date"]', '2026-02-26')
        authenticated_page.fill('input[name="entries-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option('select[name="entries-0-shift"]', 'DAY')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/evacuation/", timeout=5000)

        # Check evacuation appears in list
        expect(authenticated_page.locator('text=E2E001')).to_be_visible()
        expect(authenticated_page.locator('text=2026-02-26')).to_be_visible()

    def test_edit_evacuation_line(self, authenticated_page: Page, base_url, create_test_sd):
        """Test editing a single SD line from an evacuation record"""
        # Create an evacuation first
        authenticated_page.goto(f"{base_url}/evacuation/create/")

        authenticated_page.fill('input[name="date"]', '2026-02-26')
        authenticated_page.fill('input[name="shift"]', 'DAY')

        # Fill first SD line
        authenticated_page.fill('input[name="lines-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="lines-0-vessel"]', 'MV ORIGINAL VESSEL')
        authenticated_page.fill('input[name="lines-0-agent"]', 'ORIGINAL AGENT')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/evacuation/", timeout=5000)

        # Find and click edit button for the SD line
        edit_button = authenticated_page.locator('a:has-text("EDIT")').first
        if edit_button.is_visible():
            edit_button.click()

            # Modify vessel and agent
            authenticated_page.fill('input[name="vessel"]', 'MV UPDATED VESSEL')
            authenticated_page.fill('input[name="agent"]', 'UPDATED AGENT')

            # Submit
            authenticated_page.click('button[type="submit"]')
            authenticated_page.wait_for_url(f"{base_url}/evacuation/", timeout=5000)

            # Check updated values appear in list
            expect(authenticated_page.locator('text=MV UPDATED VESSEL')).to_be_visible()
            expect(authenticated_page.locator('text=UPDATED AGENT')).to_be_visible()

    def test_delete_evacuation(self, authenticated_page: Page, base_url, create_test_sd):
        """Test deleting an evacuation record"""
        # Create an evacuation first
        authenticated_page.goto(f"{base_url}/evacuation/create/")

        authenticated_page.fill('input[name="date"]', '2026-02-26')
        authenticated_page.fill('input[name="entries-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option('select[name="entries-0-shift"]', 'DAY')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/evacuation/", timeout=5000)

        # Find and click delete button
        delete_button = authenticated_page.locator('a[href*="/delete/"]').first
        if delete_button.is_visible():
            delete_button.click()

            # Confirm deletion
            authenticated_page.click('button[type="submit"]')
            authenticated_page.wait_for_url(f"{base_url}/evacuation/", timeout=5000)

            # Check success message
            expect(authenticated_page.locator('text=/deleted/i')).to_be_visible()

    def test_multiple_evacuations_per_sd(self, authenticated_page: Page, base_url, create_test_sd):
        """Test that multiple evacuations can be created for same SD"""
        # Create first evacuation
        authenticated_page.goto(f"{base_url}/evacuation/create/")

        authenticated_page.fill('input[name="date"]', '2026-02-26')
        authenticated_page.fill('input[name="entries-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option('select[name="entries-0-shift"]', 'DAY')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/evacuation/", timeout=5000)

        # Create second evacuation for same SD
        authenticated_page.goto(f"{base_url}/evacuation/create/")

        authenticated_page.fill('input[name="date"]', '2026-02-27')
        authenticated_page.fill('input[name="entries-0-sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.select_option('select[name="entries-0-shift"]', 'NIGHT')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/evacuation/", timeout=5000)

        # Both evacuations should be visible
        expect(authenticated_page.locator('text=2026-02-26')).to_be_visible()
        expect(authenticated_page.locator('text=2026-02-27')).to_be_visible()

    def test_evacuation_vessel_agent_autofill_from_booking(self, authenticated_page: Page, base_url, create_test_sd):
        """Test that vessel and agent auto-fill from booking records"""
        # First create a booking
        authenticated_page.goto(f"{base_url}/booking/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="vessel"]', 'MV AUTOFILL VESSEL')
        authenticated_page.fill('input[name="agent"]', 'AUTOFILL AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-booking_number"]', 'AUTOBK')
        authenticated_page.fill('input[name="lines-0-bill_number"]', 'AUTOBILL')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '100')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)

        # Now create evacuation
        authenticated_page.goto(f"{base_url}/evacuation/create/")

        authenticated_page.fill('input[name="date"]', '2026-02-26')
        authenticated_page.fill('input[name="entries-0-sd_number"]', 'E2E001')

        # Wait for auto-fill
        authenticated_page.wait_for_timeout(1500)

        # Check vessel and agent were auto-filled
        vessel_input = authenticated_page.locator('input[name="entries-0-vessel"]')
        agent_input = authenticated_page.locator('input[name="entries-0-agent"]')

        if vessel_input.is_visible():
            expect(vessel_input).to_have_value('MV AUTOFILL VESSEL')
        if agent_input.is_visible():
            expect(agent_input).to_have_value('AUTOFILL AGENT')
