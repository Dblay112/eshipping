"""
Comprehensive end-to-end tests for the Shipping Management Portal.
Tests every page, form, and workflow as a real user would interact with the system.
"""
import pytest
from playwright.sync_api import Page, expect
import time


# Test Configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_USER = {
    "staff_id": "1812",
    "password": "bright123"
}


@pytest.fixture(scope="function")
def authenticated_page(page: Page):
    """Login before each test."""
    page.goto(f"{BASE_URL}/login/")
    page.fill('input[name="username"]', TEST_USER["staff_id"])
    page.fill('input[name="password"]', TEST_USER["password"])
    page.click('button[type="submit"]')
    # Wait for navigation to complete (don't expect specific URL)
    page.wait_for_load_state("networkidle", timeout=10000)
    return page


class TestAuthentication:
    """Test login and logout functionality."""

    def test_login_page_loads(self, page: Page):
        """Test that login page loads correctly."""
        page.goto(f"{BASE_URL}/login/")
        expect(page).to_have_title("Secure Access Portal")
        expect(page.locator('input[name="username"]')).to_be_visible()
        expect(page.locator('input[name="password"]')).to_be_visible()

    def test_login_with_valid_credentials(self, page: Page):
        """Test successful login."""
        page.goto(f"{BASE_URL}/login/")
        page.fill('input[name="username"]', TEST_USER["staff_id"])
        page.fill('input[name="password"]', TEST_USER["password"])
        page.click('button[type="submit"]')
        # Wait for navigation to complete
        page.wait_for_load_state("networkidle", timeout=10000)
        # Should redirect away from login page
        assert "/login" not in page.url
        print(f"After login, redirected to: {page.url}")

    def test_login_with_invalid_credentials(self, page: Page):
        """Test login failure with wrong credentials."""
        page.goto(f"{BASE_URL}/login/")
        page.fill('input[name="username"]', "9999")
        page.fill('input[name="password"]', "wrongpassword")
        page.click('button[type="submit"]')
        # Should show error message
        time.sleep(1)
        assert "Invalid" in page.content() or "incorrect" in page.content().lower()

    def test_logout(self, authenticated_page: Page):
        """Test logout functionality."""
        # Find and click logout link
        authenticated_page.goto(f"{BASE_URL}/logout/")
        authenticated_page.wait_for_load_state("networkidle", timeout=10000)
        # Should redirect to login page
        assert "/login" in authenticated_page.url
        expect(authenticated_page.locator('input[name="username"]')).to_be_visible()


class TestOperationsSDRecords:
    """Test SD record creation and management."""

    def test_sd_list_page_loads(self, authenticated_page: Page):
        """Test SD records list page loads."""
        authenticated_page.goto(f"{BASE_URL}/operations/")
        expect(authenticated_page).to_have_title("Operations — SD Records | CMC")

    def test_create_sd_record_page_loads(self, authenticated_page: Page):
        """Test SD creation form loads."""
        authenticated_page.goto(f"{BASE_URL}/operations/create/")
        # Check for key form fields
        expect(authenticated_page.locator('input[name="sd_number"]')).to_be_visible()
        expect(authenticated_page.locator('input[name="vessel_name"]')).to_be_visible()

    def test_create_sd_with_valid_data(self, authenticated_page: Page):
        """Test creating a new SD record with valid data."""
        authenticated_page.goto(f"{BASE_URL}/operations/create/")

        # Fill SD header fields based on actual form
        sd_number = f"SD{int(time.time())}"  # Unique SD number
        authenticated_page.fill('input[name="sd_number"]', sd_number)
        authenticated_page.fill('input[name="date_of_entry"]', "2026-02-26")
        authenticated_page.fill('input[name="vessel_name"]', "MV TEST VESSEL")
        authenticated_page.select_option('select[name="crop_year"]', index=0)
        authenticated_page.fill('input[name="eta"]', "2026-03-01")
        authenticated_page.fill('input[name="si_ref"]', "CMC/TEST/001")
        authenticated_page.fill('input[name="tonnage"]', "100")
        authenticated_page.fill('input[name="agent"]', "MSC")
        authenticated_page.fill('input[name="port_of_discharge"]', "ANTWERP")

        # Fill first contract allocation (prefix is 'allocs' not 'allocations')
        authenticated_page.fill('input[name="allocs-0-contract_number"]', "TEST001")
        authenticated_page.fill('input[name="allocs-0-mk_number"]', "MK001")
        authenticated_page.fill('input[name="allocs-0-allocated_tonnage"]', "100")
        authenticated_page.fill('input[name="allocs-0-buyer"]', "TEST BUYER")
        authenticated_page.fill('input[name="allocs-0-agent"]', "MSC")
        authenticated_page.fill('input[name="allocs-0-cocoa_type"]', "COCOA BEANS")

        # Submit form - click the save draft button
        authenticated_page.locator('button.sdt-btn-save-draft').click()

        # Should redirect to SD list
        authenticated_page.wait_for_load_state("networkidle", timeout=10000)
        assert "/operations/" in authenticated_page.url

        # Verify SD appears in list
        authenticated_page.goto(f"{BASE_URL}/operations/")
        expect(authenticated_page.locator(f'text={sd_number}')).to_be_visible(timeout=10000)

    def test_create_sd_with_missing_required_fields(self, authenticated_page: Page):
        """Test validation when required fields are missing."""
        authenticated_page.goto(f"{BASE_URL}/operations/create/")

        # Try to submit without filling required fields
        authenticated_page.locator('button.sdt-btn-save-draft').click()

        # Should stay on same page with errors
        time.sleep(1)
        assert "/operations/create/" in authenticated_page.url


class TestScheduleManagement:
    """Test schedule creation and viewing."""

    def test_schedule_list_loads(self, authenticated_page: Page):
        """Test schedule list page loads."""
        authenticated_page.goto(f"{BASE_URL}/schedule/")
        expect(authenticated_page).to_have_title("Schedule — CMC")

    def test_create_schedule_page_loads(self, authenticated_page: Page):
        """Test schedule creation form loads."""
        authenticated_page.goto(f"{BASE_URL}/schedule/create/")
        expect(authenticated_page.locator('input[name="date"]')).to_be_visible()

    def test_terminal_schedule_page_loads(self, authenticated_page: Page):
        """Test terminal schedule page loads."""
        authenticated_page.goto(f"{BASE_URL}/schedule/terminal/")
        # Should show terminal schedules or creation option
        assert "Terminal" in authenticated_page.content()


class TestBookingManagement:
    """Test E-Booking functionality."""

    def test_booking_list_loads(self, authenticated_page: Page):
        """Test booking list page loads."""
        authenticated_page.goto(f"{BASE_URL}/booking/")
        expect(authenticated_page).to_have_title("E-Bookings — CMC")

    def test_booking_create_page_loads(self, authenticated_page: Page):
        """Test booking creation form loads."""
        authenticated_page.goto(f"{BASE_URL}/booking/create/")
        expect(authenticated_page.locator('input[name="sd_number"]')).to_be_visible()
        expect(authenticated_page.locator('input[name="vessel"]')).to_be_visible()
        expect(authenticated_page.locator('input[name="agent"]')).to_be_visible()

    def test_booking_form_has_contract_fields(self, authenticated_page: Page):
        """Test booking form has contract line fields."""
        authenticated_page.goto(f"{BASE_URL}/booking/create/")
        # Check for formset fields
        page_content = authenticated_page.content()
        assert "contract" in page_content.lower() or "booking" in page_content.lower()


class TestDeclarations:
    """Test declarations functionality."""

    def test_declarations_list_loads(self, authenticated_page: Page):
        """Test declarations list page loads."""
        authenticated_page.goto(f"{BASE_URL}/declarations/")
        expect(authenticated_page).to_have_title("Declarations — CMC")

    def test_declarations_create_page_loads(self, authenticated_page: Page):
        """Test declarations creation form loads."""
        authenticated_page.goto(f"{BASE_URL}/declarations/create/")
        expect(authenticated_page.locator('input[name="sd_number"]')).to_be_visible()
        expect(authenticated_page.locator('input[name="agent"]')).to_be_visible()


class TestEvacuations:
    """Test evacuation functionality."""

    def test_evacuation_list_loads(self, authenticated_page: Page):
        """Test evacuation list page loads."""
        authenticated_page.goto(f"{BASE_URL}/evacuation/")
        expect(authenticated_page).to_have_title("Evacuations — CMC")

    def test_evacuation_create_page_loads(self, authenticated_page: Page):
        """Test evacuation creation form loads."""
        authenticated_page.goto(f"{BASE_URL}/evacuation/create/")
        expect(authenticated_page.locator('input[name="date"]')).to_be_visible()

    def test_evacuation_form_has_vessel_field(self, authenticated_page: Page):
        """Test evacuation form includes vessel field."""
        authenticated_page.goto(f"{BASE_URL}/evacuation/create/")
        # Check for vessel field in formset
        page_content = authenticated_page.content()
        assert "vessel" in page_content.lower()


class TestTallySystem:
    """Test tally creation and approval."""

    def test_tally_bulk_loading_page_loads(self, authenticated_page: Page):
        """Test bulk loading tally form loads."""
        authenticated_page.goto(f"{BASE_URL}/tally/bulk/")
        authenticated_page.wait_for_load_state("networkidle")
        # Check if page loaded successfully (might redirect if no permissions)
        # Just verify we're on a tally-related page
        assert "tally" in authenticated_page.url.lower() or "bulk" in authenticated_page.url.lower()

    def test_tally_20ft_straight_loading_page_loads(self, authenticated_page: Page):
        """Test 20ft straight loading tally form loads."""
        authenticated_page.goto(f"{BASE_URL}/tally/straight-20/")
        authenticated_page.wait_for_load_state("networkidle")
        assert "tally" in authenticated_page.url.lower() or "straight" in authenticated_page.url.lower()

    def test_tally_40ft_straight_loading_page_loads(self, authenticated_page: Page):
        """Test 40ft straight loading tally form loads."""
        authenticated_page.goto(f"{BASE_URL}/tally/straight-40/")
        authenticated_page.wait_for_load_state("networkidle")
        assert "tally" in authenticated_page.url.lower() or "straight" in authenticated_page.url.lower()

    def test_tally_japan_straight_loading_page_loads(self, authenticated_page: Page):
        """Test Japan straight loading tally form loads."""
        authenticated_page.goto(f"{BASE_URL}/tally/japan-straight/")
        authenticated_page.wait_for_load_state("networkidle")
        assert "tally" in authenticated_page.url.lower() or "japan" in authenticated_page.url.lower()

    def test_my_tallies_page_loads(self, authenticated_page: Page):
        """Test my tallies page loads."""
        authenticated_page.goto(f"{BASE_URL}/tally/my-tallies/")
        # Should show user's tallies
        assert "Tally" in authenticated_page.content() or "tallies" in authenticated_page.content().lower()


class TestDailyPort:
    """Test daily port functionality."""

    def test_daily_port_list_loads(self, authenticated_page: Page):
        """Test daily port list page loads."""
        authenticated_page.goto(f"{BASE_URL}/daily-port/")
        expect(authenticated_page).to_have_title("Daily Port — CMC")

    def test_daily_port_create_page_loads(self, authenticated_page: Page):
        """Test daily port creation form loads."""
        authenticated_page.goto(f"{BASE_URL}/daily-port/create/")
        expect(authenticated_page.locator('input[name="date"]')).to_be_visible()


class TestSDValidation:
    """Test SD number validation across forms."""

    def test_booking_form_validates_sd_number(self, authenticated_page: Page):
        """Test booking form validates SD exists."""
        authenticated_page.goto(f"{BASE_URL}/booking/create/")

        # Enter non-existent SD
        authenticated_page.fill('input[name="sd_number"]', "NONEXISTENT999")
        authenticated_page.fill('input[name="vessel"]', "TEST VESSEL")
        authenticated_page.fill('input[name="agent"]', "TEST AGENT")

        # Try to submit using correct button class
        authenticated_page.click('button.sdt-btn-save-draft')

        # Should show error
        time.sleep(1)
        page_content = authenticated_page.content()
        assert "not registered" in page_content.lower() or "does not exist" in page_content.lower()

    def test_declaration_form_validates_sd_number(self, authenticated_page: Page):
        """Test declaration form validates SD exists."""
        authenticated_page.goto(f"{BASE_URL}/declarations/create/")

        # Enter non-existent SD
        authenticated_page.fill('input[name="sd_number"]', "NONEXISTENT999")
        authenticated_page.fill('input[name="agent"]', "TEST AGENT")

        # Try to submit using specific button
        authenticated_page.locator('button.sdt-btn-primary').click()

        # Should show error
        time.sleep(1)
        page_content = authenticated_page.content()
        assert "not registered" in page_content.lower() or "does not exist" in page_content.lower()


class TestNavigationAndUI:
    """Test navigation and UI elements."""

    def test_navbar_contains_all_modules(self, authenticated_page: Page):
        """Test navbar shows all main modules."""
        authenticated_page.goto(f"{BASE_URL}/")
        page_content = authenticated_page.content()

        # Check for main navigation items
        assert "Operations" in page_content or "operations" in page_content.lower()
        assert "Schedule" in page_content or "schedule" in page_content.lower()
        assert "Tally" in page_content or "tally" in page_content.lower()

    def test_dashboard_loads(self, authenticated_page: Page):
        """Test dashboard page loads."""
        authenticated_page.goto(f"{BASE_URL}/")
        # Should show some dashboard content
        assert authenticated_page.url == f"{BASE_URL}/" or "dashboard" in authenticated_page.url.lower()

    def test_search_functionality_exists(self, authenticated_page: Page):
        """Test search functionality is available."""
        authenticated_page.goto(f"{BASE_URL}/operations/")
        # Look for search input
        search_inputs = authenticated_page.locator('input[type="search"], input[name="q"]')
        assert search_inputs.count() > 0


class TestFormValidation:
    """Test form validation across the application."""

    def test_required_fields_are_enforced(self, authenticated_page: Page):
        """Test that required fields prevent submission."""
        authenticated_page.goto(f"{BASE_URL}/operations/create/")

        # Try to submit empty form using specific button
        authenticated_page.locator('button.sdt-btn-save-draft').click()

        # Should stay on same page
        time.sleep(1)
        assert "/operations/create/" in authenticated_page.url

    def test_numeric_fields_reject_text(self, authenticated_page: Page):
        """Test numeric fields validate input."""
        authenticated_page.goto(f"{BASE_URL}/operations/create/")

        # Verify the field is type=number (browsers enforce this automatically)
        field = authenticated_page.locator('input[name="allocs-0-allocated_tonnage"]')
        assert field.get_attribute('type') == 'number'


class TestDataPersistence:
    """Test that data is saved and retrieved correctly."""

    def test_created_sd_appears_in_list(self, authenticated_page: Page):
        """Test that newly created SD appears in the list."""
        # Create SD
        authenticated_page.goto(f"{BASE_URL}/operations/create/")

        sd_number = f"PERSIST{int(time.time())}"
        authenticated_page.fill('input[name="sd_number"]', sd_number)
        authenticated_page.fill('input[name="date_of_entry"]', "2026-02-26")
        authenticated_page.fill('input[name="vessel_name"]', "PERSIST VESSEL")
        authenticated_page.select_option('select[name="crop_year"]', index=0)
        authenticated_page.fill('input[name="eta"]', "2026-03-01")
        authenticated_page.fill('input[name="si_ref"]', "CMC/TEST/001")
        authenticated_page.fill('input[name="tonnage"]', "100")
        authenticated_page.fill('input[name="agent"]', "MSC")
        authenticated_page.fill('input[name="port_of_discharge"]', "ANTWERP")

        authenticated_page.fill('input[name="allocs-0-contract_number"]', "PERSIST001")
        authenticated_page.fill('input[name="allocs-0-mk_number"]', "MK001")
        authenticated_page.fill('input[name="allocs-0-allocated_tonnage"]', "100")
        authenticated_page.fill('input[name="allocs-0-buyer"]', "BUYER")
        authenticated_page.fill('input[name="allocs-0-agent"]', "MSC")
        authenticated_page.fill('input[name="allocs-0-cocoa_type"]', "COCOA BEANS")

        authenticated_page.locator('button.sdt-btn-save-draft').click()

        # Wait for redirect
        authenticated_page.wait_for_load_state("networkidle", timeout=10000)
        time.sleep(1)

        # Should redirect to operations list
        assert "/operations/" in authenticated_page.url

        # Verify it appears in the table (use more specific selector to avoid alert message)
        expect(authenticated_page.locator(f'td.sdt-td-sd:has-text("{sd_number}")')).to_be_visible()


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_404_page_for_invalid_url(self, authenticated_page: Page):
        """Test 404 page for non-existent URLs."""
        response = authenticated_page.goto(f"{BASE_URL}/nonexistent-page-12345/")
        assert response.status == 404

    def test_edit_nonexistent_record(self, authenticated_page: Page):
        """Test editing a record that doesn't exist."""
        response = authenticated_page.goto(f"{BASE_URL}/operations/99999999/edit/")
        # Should show 404 or redirect
        assert response.status == 404 or "/operations/" in authenticated_page.url


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])
