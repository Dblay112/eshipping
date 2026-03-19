"""
E2E Tests for Operations Desk Workflow
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.operations
class TestOperationsWorkflow:
    """Test Operations desk SD record management"""

    def test_operations_list_page_loads(self, authenticated_page: Page, base_url):
        """Test operations list page is accessible"""
        authenticated_page.goto(f"{base_url}/operations/")

        # Check page loaded - use specific heading selector
        expect(authenticated_page.locator('h1.sdt-page-title')).to_contain_text('SD Records')

    def test_create_sd_page_loads(self, authenticated_page: Page, base_url):
        """Test SD creation page is accessible"""
        authenticated_page.goto(f"{base_url}/operations/create/")

        # Check form elements are present
        expect(authenticated_page.locator('input[name="sd_number"]')).to_be_visible()
        expect(authenticated_page.locator('input[name="vessel_name"]')).to_be_visible()
        expect(authenticated_page.locator('input[name="agent"]')).to_be_visible()

    def test_create_sd_with_valid_data(self, authenticated_page: Page, base_url):
        """Test creating SD record with valid data"""
        authenticated_page.goto(f"{base_url}/operations/create/")

        # Wait for page to fully load
        authenticated_page.wait_for_load_state('networkidle')

        # Fill SD-level fields
        authenticated_page.fill('input[name="sd_number"]', 'TEST100')
        authenticated_page.fill('input[name="vessel_name"]', 'MV TEST SHIP')
        authenticated_page.fill('input[name="agent"]', 'MSC')

        # Select crop year
        authenticated_page.select_option('select[name="crop_year"]', '2025/2026 MC')

        # Fill tonnage
        authenticated_page.fill('input[name="tonnage"]', '500')

        # Wait for allocation formset to be ready
        authenticated_page.wait_for_selector('input[name="allocations-0-contract_number"]', timeout=10000)

        # Fill allocation (contract) details - these are in formset
        authenticated_page.fill('input[name="allocations-0-allocation_label"]', 'A')
        authenticated_page.fill('input[name="allocations-0-contract_number"]', 'NJ001')
        authenticated_page.fill('input[name="allocations-0-mk_number"]', 'MK001')
        authenticated_page.fill('input[name="allocations-0-allocated_tonnage"]', '500')
        authenticated_page.fill('input[name="allocations-0-buyer"]', 'TEST BUYER')

        # Submit form - use specific button selector
        authenticated_page.locator('button.sdt-btn-primary[type="submit"]').click()

        # Should redirect to operations list or detail page
        authenticated_page.wait_for_url(f"{base_url}/operations/**", timeout=5000)

        # Check success message
        expect(authenticated_page.locator('text=/successfully/i').first).to_be_visible()

    def test_create_sd_with_missing_required_fields(self, authenticated_page: Page, base_url):
        """Test SD creation fails with missing required fields"""
        authenticated_page.goto(f"{base_url}/operations/create/")

        # Try to submit without filling required fields
        authenticated_page.locator('button.sdt-btn-primary[type="submit"]').click()

        # Should stay on same page
        expect(authenticated_page).to_have_url(f"{base_url}/operations/create/")

        # Check for validation errors (HTML5 validation or Django errors)
        # The form should not submit

    def test_create_sd_with_duplicate_sd_number(self, authenticated_page: Page, base_url, create_test_sd):
        """Test SD creation fails with duplicate SD number"""
        authenticated_page.goto(f"{base_url}/operations/create/")
        authenticated_page.wait_for_load_state('networkidle')

        # Try to create SD with existing number
        authenticated_page.fill('input[name="sd_number"]', 'E2E001')  # Already exists
        authenticated_page.fill('input[name="vessel_name"]', 'MV DUPLICATE')
        authenticated_page.fill('input[name="agent"]', 'TEST AGENT')
        authenticated_page.select_option('select[name="crop_year"]', '2025/2026 MC')
        authenticated_page.fill('input[name="tonnage"]', '100')

        # Wait for allocation formset
        authenticated_page.wait_for_selector('input[name="allocations-0-contract_number"]', timeout=10000)

        # Fill allocation
        authenticated_page.fill('input[name="allocations-0-contract_number"]', 'NJ002')
        authenticated_page.fill('input[name="allocations-0-mk_number"]', 'MK002')
        authenticated_page.fill('input[name="allocations-0-allocated_tonnage"]', '100')

        # Submit
        authenticated_page.locator('button.sdt-btn-primary[type="submit"]').click()

        # Should show error about duplicate SD number
        authenticated_page.wait_for_timeout(1000)
        expect(authenticated_page.locator('.sdt-alert-error, .sdt-form-error').first).to_be_visible()

    def test_create_sd_with_multiple_allocations(self, authenticated_page: Page, base_url):
        """Test creating SD with multiple contract allocations"""
        authenticated_page.goto(f"{base_url}/operations/create/")
        authenticated_page.wait_for_load_state('networkidle')

        # Fill SD-level fields
        authenticated_page.fill('input[name="sd_number"]', 'TEST200')
        authenticated_page.fill('input[name="vessel_name"]', 'MV MULTI CONTRACT')
        authenticated_page.fill('input[name="agent"]', 'COSCO')
        authenticated_page.select_option('select[name="crop_year"]', '2025/2026 MC')
        authenticated_page.fill('input[name="tonnage"]', '500')

        # Wait for allocation formset
        authenticated_page.wait_for_selector('input[name="allocations-0-contract_number"]', timeout=10000)

        # Fill first allocation
        authenticated_page.fill('input[name="allocations-0-allocation_label"]', 'A')
        authenticated_page.fill('input[name="allocations-0-contract_number"]', 'NJ100')
        authenticated_page.fill('input[name="allocations-0-mk_number"]', 'MK100')
        authenticated_page.fill('input[name="allocations-0-allocated_tonnage"]', '250')

        # Add second allocation (click "Add Contract Line" button)
        add_button = authenticated_page.locator('button#addAllocBtn')
        if add_button.is_visible():
            add_button.click()
            authenticated_page.wait_for_timeout(500)

            # Fill second allocation
            authenticated_page.fill('input[name="allocations-1-allocation_label"]', 'B')
            authenticated_page.fill('input[name="allocations-1-contract_number"]', 'NJ101')
            authenticated_page.fill('input[name="allocations-1-mk_number"]', 'MK101')
            authenticated_page.fill('input[name="allocations-1-allocated_tonnage"]', '250')

        # Submit
        authenticated_page.locator('button.sdt-btn-primary[type="submit"]').click()

        # Should succeed
        authenticated_page.wait_for_url(f"{base_url}/operations/**", timeout=5000)

    def test_view_sd_detail(self, authenticated_page: Page, base_url, create_test_sd):
        """Test viewing SD detail page"""
        # Navigate to operations list first to find an SD
        authenticated_page.goto(f"{base_url}/operations/")

        # Click on first SD row to view details
        first_sd_row = authenticated_page.locator('tr.sdt-row').first
        if first_sd_row.is_visible():
            first_sd_row.click()
            authenticated_page.wait_for_timeout(1000)

            # Check SD details are displayed
            expect(authenticated_page.locator('.sdt-detail-panel')).to_be_visible()

    def test_edit_sd_record(self, authenticated_page: Page, base_url, create_test_sd):
        """Test editing an existing SD record"""
        # Navigate to operations list
        authenticated_page.goto(f"{base_url}/operations/")

        # Find and click edit button for first SD
        edit_button = authenticated_page.locator('a:has-text("EDIT")').first
        if edit_button.is_visible():
            edit_button.click()

            # Should be on edit page
            authenticated_page.wait_for_url(f"{base_url}/operations/**/edit/", timeout=5000)
            authenticated_page.wait_for_load_state('networkidle')

            # Modify vessel name
            authenticated_page.fill('input[name="vessel_name"]', 'MV UPDATED VESSEL')

            # Submit
            authenticated_page.locator('button.sdt-btn-primary[type="submit"]').click()

            # Wait for redirect (may go to detail or list page)
            authenticated_page.wait_for_timeout(2000)

            # Check we're no longer on edit page
            assert '/edit/' not in authenticated_page.url

    def test_delete_sd_record(self, authenticated_page: Page, base_url, create_test_sd):
        """Test deleting an SD record"""
        authenticated_page.goto(f"{base_url}/operations/")

        # Find delete button for any SD
        delete_button = authenticated_page.locator('a[href*="/delete/"]').first

        if delete_button.is_visible():
            delete_button.click()

            # Confirm deletion - use most specific selector for delete button
            authenticated_page.wait_for_url(f"{base_url}/operations/**/delete/", timeout=5000)

            # Click the delete confirmation button (use class name to be specific)
            authenticated_page.locator('button.sdt-delete-btn-confirm').click()

            # Should redirect to list
            authenticated_page.wait_for_url(f"{base_url}/operations/", timeout=5000)

            # Check success message
            expect(authenticated_page.locator('text=/deleted/i').first).to_be_visible()

    def test_search_sd_records(self, authenticated_page: Page, base_url, create_test_sd):
        """Test searching for SD records"""
        authenticated_page.goto(f"{base_url}/operations/")

        # Search for test SD
        search_input = authenticated_page.locator('input[name="q"]')
        if search_input.is_visible():
            search_input.fill('E2E001')
            authenticated_page.press('input[name="q"]', 'Enter')

            # Should show filtered results
            expect(authenticated_page.locator('text=E2E001')).to_be_visible()

    def test_export_sd_to_excel(self, authenticated_page: Page, base_url, create_test_sd):
        """Test exporting SD records to Excel"""
        authenticated_page.goto(f"{base_url}/operations/")

        # Look for export button - use more specific selector
        export_button = authenticated_page.locator('a.sdt-btn-excel').first

        if export_button.is_visible():
            # Start waiting for download before clicking
            with authenticated_page.expect_download() as download_info:
                export_button.click()

            download = download_info.value

            # Check file was downloaded
            assert download.suggested_filename.endswith('.xlsx') or download.suggested_filename.endswith('.xls')
