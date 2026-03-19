"""
E2E Tests for E-Booking Workflow
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.booking
class TestBookingWorkflow:
    """Test E-Booking desk workflow"""

    def test_booking_list_page_loads(self, authenticated_page: Page, base_url):
        """Test booking list page is accessible"""
        authenticated_page.goto(f"{base_url}/booking/")

        # Check page loaded
        expect(authenticated_page.locator('text=/Booking/i')).to_be_visible()

    def test_create_booking_page_loads(self, authenticated_page: Page, base_url):
        """Test booking creation page loads"""
        authenticated_page.goto(f"{base_url}/booking/create/")

        # Check form elements
        expect(authenticated_page.locator('input[name="sd_number"]')).to_be_visible()

    def test_create_booking_with_valid_sd(self, authenticated_page: Page, base_url, create_test_sd):
        """Test creating booking with valid SD number"""
        authenticated_page.goto(f"{base_url}/booking/create/")

        # Fill SD number
        authenticated_page.fill('input[name="sd_number"]', 'E2E001')

        # Wait for SD validation
        authenticated_page.wait_for_timeout(1000)

        # Check green checkmark appears
        green_icon = authenticated_page.locator('.validation-icon.valid')
        expect(green_icon).to_be_visible()

        # Fill booking details
        authenticated_page.fill('input[name="vessel"]', 'MV BOOKING VESSEL')
        authenticated_page.fill('input[name="agent"]', 'BOOKING AGENT')

        # Fill contract line details
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-booking_number"]', 'BK001')
        authenticated_page.fill('input[name="lines-0-bill_number"]', 'BILL001')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '250')

        # Submit
        authenticated_page.click('button[type="submit"]')

        # Should redirect to booking list
        authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)

        # Check success message
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_create_booking_with_invalid_sd(self, authenticated_page: Page, base_url):
        """Test creating booking with non-existent SD"""
        authenticated_page.goto(f"{base_url}/booking/create/")

        # Fill invalid SD number
        authenticated_page.fill('input[name="sd_number"]', 'INVALID999')

        # Wait for validation
        authenticated_page.wait_for_timeout(1000)

        # Should show red X icon
        red_icon = authenticated_page.locator('.validation-icon.invalid')
        expect(red_icon).to_be_visible()

    def test_create_booking_with_multiple_contracts(self, authenticated_page: Page, base_url, create_test_sd):
        """Test creating booking with multiple contract lines"""
        authenticated_page.goto(f"{base_url}/booking/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)

        authenticated_page.fill('input[name="vessel"]', 'MV MULTI BOOKING')
        authenticated_page.fill('input[name="agent"]', 'MULTI AGENT')

        # Fill first contract line
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-booking_number"]', 'BK100')
        authenticated_page.fill('input[name="lines-0-bill_number"]', 'BILL100')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '100')

        # Add second contract line
        add_button = authenticated_page.locator('text=/Add.*Line/i')
        if add_button.is_visible():
            add_button.click()

            authenticated_page.fill('input[name="lines-1-contract_number"]', 'TEST002')
            authenticated_page.fill('input[name="lines-1-booking_number"]', 'BK101')
            authenticated_page.fill('input[name="lines-1-bill_number"]', 'BILL101')
            authenticated_page.fill('input[name="lines-1-tonnage"]', '150')

        # Submit
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_view_booking_details(self, authenticated_page: Page, base_url, create_test_sd):
        """Test viewing booking details"""
        # Create a booking first
        authenticated_page.goto(f"{base_url}/booking/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="vessel"]', 'MV VIEW BOOKING')
        authenticated_page.fill('input[name="agent"]', 'VIEW AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-booking_number"]', 'VIEWBK')
        authenticated_page.fill('input[name="lines-0-bill_number"]', 'VIEWBILL')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '100')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)

        # Check booking appears in list
        expect(authenticated_page.locator('text=VIEWBK')).to_be_visible()
        expect(authenticated_page.locator('text=E2E001')).to_be_visible()

    def test_edit_booking(self, authenticated_page: Page, base_url, create_test_sd):
        """Test editing a booking record"""
        # Create a booking first
        authenticated_page.goto(f"{base_url}/booking/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="vessel"]', 'MV EDIT BOOKING')
        authenticated_page.fill('input[name="agent"]', 'EDIT AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-booking_number"]', 'EDITBK')
        authenticated_page.fill('input[name="lines-0-bill_number"]', 'EDITBILL')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '100')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)

        # Find and click edit button
        edit_button = authenticated_page.locator('a:has-text("EDIT")').first
        if edit_button.is_visible():
            edit_button.click()

            # Modify vessel name
            authenticated_page.fill('input[name="vessel"]', 'MV EDITED BOOKING')

            # Submit
            authenticated_page.click('button[type="submit"]')
            authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)

            # Check updated value
            expect(authenticated_page.locator('text=MV EDITED BOOKING')).to_be_visible()

    def test_delete_booking(self, authenticated_page: Page, base_url, create_test_sd):
        """Test deleting a booking record"""
        # Create a booking first
        authenticated_page.goto(f"{base_url}/booking/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="vessel"]', 'MV DELETE BOOKING')
        authenticated_page.fill('input[name="agent"]', 'DELETE AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-booking_number"]', 'DELBK')
        authenticated_page.fill('input[name="lines-0-bill_number"]', 'DELBILL')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '50')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)

        # Find and click delete button
        delete_button = authenticated_page.locator('a[href*="/delete/"]').first
        if delete_button.is_visible():
            delete_button.click()

            # Confirm deletion
            authenticated_page.click('button[type="submit"]')
            authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)

            # Check success message
            expect(authenticated_page.locator('text=/deleted/i')).to_be_visible()

    def test_booking_balance_tracking(self, authenticated_page: Page, base_url, create_test_sd):
        """Test that booking tracks contract balance correctly"""
        # Create first booking for 250 MT
        authenticated_page.goto(f"{base_url}/booking/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="vessel"]', 'MV BALANCE TEST 1')
        authenticated_page.fill('input[name="agent"]', 'BALANCE AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-booking_number"]', 'BAL001')
        authenticated_page.fill('input[name="lines-0-bill_number"]', 'BALBILL001')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '250')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)

        # Create second booking for remaining 250 MT
        authenticated_page.goto(f"{base_url}/booking/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="vessel"]', 'MV BALANCE TEST 2')
        authenticated_page.fill('input[name="agent"]', 'BALANCE AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-booking_number"]', 'BAL002')
        authenticated_page.fill('input[name="lines-0-bill_number"]', 'BALBILL002')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '250')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)

        # Both bookings should be visible
        expect(authenticated_page.locator('text=BAL001')).to_be_visible()
        expect(authenticated_page.locator('text=BAL002')).to_be_visible()

    def test_booking_file_upload(self, authenticated_page: Page, base_url, create_test_sd):
        """Test uploading file with booking"""
        authenticated_page.goto(f"{base_url}/booking/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="vessel"]', 'MV FILE UPLOAD')
        authenticated_page.fill('input[name="agent"]', 'FILE AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-booking_number"]', 'FILEBK')
        authenticated_page.fill('input[name="lines-0-bill_number"]', 'FILEBILL')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '100')

        # Upload file if file input exists
        file_input = authenticated_page.locator('input[type="file"]')
        if file_input.is_visible():
            # Create a temporary test file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write('Test booking file')
                temp_file = f.name

            file_input.set_input_files(temp_file)

        # Submit
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/booking/", timeout=5000)
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()
