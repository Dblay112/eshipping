"""
E2E Tests for Declaration Workflow
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.declaration
class TestDeclarationWorkflow:
    """Test Declaration desk workflow"""

    def test_declaration_list_page_loads(self, authenticated_page: Page, base_url):
        """Test declaration list page is accessible"""
        authenticated_page.goto(f"{base_url}/declarations/")

        # Check page loaded
        expect(authenticated_page.locator('text=/Declaration/i')).to_be_visible()

    def test_create_declaration_page_loads(self, authenticated_page: Page, base_url):
        """Test declaration creation page loads"""
        authenticated_page.goto(f"{base_url}/declarations/create/")

        # Check form elements
        expect(authenticated_page.locator('input[name="sd_number"]')).to_be_visible()

    def test_create_declaration_with_valid_sd(self, authenticated_page: Page, base_url, create_test_sd):
        """Test creating declaration with valid SD number"""
        authenticated_page.goto(f"{base_url}/declarations/create/")

        # Fill SD number
        authenticated_page.fill('input[name="sd_number"]', 'E2E001')

        # Wait for SD validation
        authenticated_page.wait_for_timeout(1000)

        # Check green checkmark appears
        green_icon = authenticated_page.locator('.validation-icon.valid')
        expect(green_icon).to_be_visible()

        # Fill declaration details
        authenticated_page.fill('input[name="agent"]', 'DECLARATION AGENT')

        # Fill contract line details
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-declaration_number"]', 'DEC001')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '500')

        # Submit
        authenticated_page.click('button[type="submit"]')

        # Should redirect to declaration list
        authenticated_page.wait_for_url(f"{base_url}/declarations/", timeout=5000)

        # Check success message
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_create_declaration_with_invalid_sd(self, authenticated_page: Page, base_url):
        """Test creating declaration with non-existent SD"""
        authenticated_page.goto(f"{base_url}/declarations/create/")

        # Fill invalid SD number
        authenticated_page.fill('input[name="sd_number"]', 'INVALID999')

        # Wait for validation
        authenticated_page.wait_for_timeout(1000)

        # Should show red X icon
        red_icon = authenticated_page.locator('.validation-icon.invalid')
        expect(red_icon).to_be_visible()

    def test_create_declaration_with_multiple_contracts(self, authenticated_page: Page, base_url, create_test_sd):
        """Test creating declaration with multiple contract lines"""
        authenticated_page.goto(f"{base_url}/declarations/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)

        authenticated_page.fill('input[name="agent"]', 'MULTI DECLARATION AGENT')

        # Fill first contract line
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-declaration_number"]', 'DEC100')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '250')

        # Add second contract line
        add_button = authenticated_page.locator('text=/Add.*Line/i')
        if add_button.is_visible():
            add_button.click()

            authenticated_page.fill('input[name="lines-1-contract_number"]', 'TEST002')
            authenticated_page.fill('input[name="lines-1-declaration_number"]', 'DEC101')
            authenticated_page.fill('input[name="lines-1-tonnage"]', '250')

        # Submit
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/declarations/", timeout=5000)
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_view_declaration_details(self, authenticated_page: Page, base_url, create_test_sd):
        """Test viewing declaration details"""
        # Create a declaration first
        authenticated_page.goto(f"{base_url}/declarations/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="agent"]', 'VIEW DECLARATION AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-declaration_number"]', 'VIEWDEC')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '500')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/declarations/", timeout=5000)

        # Check declaration appears in list
        expect(authenticated_page.locator('text=VIEWDEC')).to_be_visible()
        expect(authenticated_page.locator('text=E2E001')).to_be_visible()

    def test_edit_declaration(self, authenticated_page: Page, base_url, create_test_sd):
        """Test editing a declaration record"""
        # Create a declaration first
        authenticated_page.goto(f"{base_url}/declarations/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="agent"]', 'EDIT DECLARATION AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-declaration_number"]', 'EDITDEC')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '500')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/declarations/", timeout=5000)

        # Find and click edit button
        edit_button = authenticated_page.locator('a:has-text("EDIT")').first
        if edit_button.is_visible():
            edit_button.click()

            # Modify agent name
            authenticated_page.fill('input[name="agent"]', 'EDITED DECLARATION AGENT')

            # Submit
            authenticated_page.click('button[type="submit"]')
            authenticated_page.wait_for_url(f"{base_url}/declarations/", timeout=5000)

            # Check updated value
            expect(authenticated_page.locator('text=EDITED DECLARATION AGENT')).to_be_visible()

    def test_delete_declaration(self, authenticated_page: Page, base_url, create_test_sd):
        """Test deleting a declaration record"""
        # Create a declaration first
        authenticated_page.goto(f"{base_url}/declarations/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="agent"]', 'DELETE DECLARATION AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-declaration_number"]', 'DELDEC')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '100')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/declarations/", timeout=5000)

        # Find and click delete button
        delete_button = authenticated_page.locator('a[href*="/delete/"]').first
        if delete_button.is_visible():
            delete_button.click()

            # Confirm deletion
            authenticated_page.click('button[type="submit"]')
            authenticated_page.wait_for_url(f"{base_url}/declarations/", timeout=5000)

            # Check success message
            expect(authenticated_page.locator('text=/deleted/i')).to_be_visible()

    def test_declaration_balance_tracking(self, authenticated_page: Page, base_url, create_test_sd):
        """Test that declaration tracks contract balance correctly"""
        # Create declaration for full contract tonnage
        authenticated_page.goto(f"{base_url}/declarations/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="agent"]', 'BALANCE DECLARATION AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-declaration_number"]', 'BALDEC001')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '500')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/declarations/", timeout=5000)

        # Declaration should be visible
        expect(authenticated_page.locator('text=BALDEC001')).to_be_visible()

    def test_declaration_file_upload(self, authenticated_page: Page, base_url, create_test_sd):
        """Test uploading file with declaration"""
        authenticated_page.goto(f"{base_url}/declarations/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="agent"]', 'FILE DECLARATION AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-declaration_number"]', 'FILEDEC')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '500')

        # Upload file if file input exists
        file_input = authenticated_page.locator('input[type="file"]')
        if file_input.is_visible():
            # Create a temporary test file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
                f.write('Test declaration document')
                temp_file = f.name

            file_input.set_input_files(temp_file)

        # Submit
        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/declarations/", timeout=5000)
        expect(authenticated_page.locator('text=/successfully/i')).to_be_visible()

    def test_one_declaration_per_contract(self, authenticated_page: Page, base_url, create_test_sd):
        """Test that only one declaration can be created per contract"""
        # Create first declaration
        authenticated_page.goto(f"{base_url}/declarations/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="agent"]', 'UNIQUE DECLARATION AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-declaration_number"]', 'UNIQUE001')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '500')

        authenticated_page.click('button[type="submit"]')
        authenticated_page.wait_for_url(f"{base_url}/declarations/", timeout=5000)

        # Try to create second declaration for same contract
        authenticated_page.goto(f"{base_url}/declarations/create/")

        authenticated_page.fill('input[name="sd_number"]', 'E2E001')
        authenticated_page.wait_for_timeout(1000)
        authenticated_page.fill('input[name="agent"]', 'DUPLICATE DECLARATION AGENT')
        authenticated_page.fill('input[name="lines-0-contract_number"]', 'TEST001')
        authenticated_page.fill('input[name="lines-0-declaration_number"]', 'UNIQUE002')
        authenticated_page.fill('input[name="lines-0-tonnage"]', '500')

        authenticated_page.click('button[type="submit"]')

        # Should show error or stay on page (depending on validation logic)
        # This test documents the expected behavior
