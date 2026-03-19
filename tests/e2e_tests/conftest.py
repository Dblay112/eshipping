"""
Playwright E2E Test Configuration and Fixtures
"""
import pytest
import subprocess
import time
import os
from decimal import Decimal

# Test server configuration
BASE_URL = "http://localhost:8000"
SERVER_PROCESS = None


@pytest.fixture(scope="session", autouse=True)
def django_server():
    """Start Django development server for E2E tests"""
    global SERVER_PROCESS

    # Server should already be running
    # Just verify it's accessible
    import requests
    try:
        response = requests.get(f"{BASE_URL}/login/", timeout=5)
        if response.status_code == 200:
            print("Server is already running")
    except:
        print("Server not responding - please start it manually")
        raise Exception("Django server not running on port 8000")

    yield

    # No cleanup needed since we didn't start the server


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application"""
    return BASE_URL


@pytest.fixture(scope="session")
def test_user():
    """Use existing test user (staff_number=1812)"""
    # User should already exist in database
    return {'staff_number': '1812', 'password': 'bright123'}


@pytest.fixture(scope="session")
def operations_user():
    """Use existing operations user"""
    return {'staff_number': '2001', 'password': 'testpass123'}


@pytest.fixture(scope="session")
def supervisor_user():
    """Use existing supervisor user"""
    return {'staff_number': '3001', 'password': 'testpass123'}


@pytest.fixture
def authenticated_page(page, base_url, test_user):
    """Provide an authenticated Playwright page"""
    # Navigate to login
    page.goto(f"{base_url}/login/")

    # Fill login form
    page.fill('input[name="username"]', test_user['staff_number'])
    page.fill('input[name="password"]', test_user['password'])

    # Submit
    page.locator('#loginCard button[type="submit"]').click()

    # Wait for redirect to dashboard
    page.wait_for_url(f"{base_url}/dashboard/", timeout=5000)

    return page


@pytest.fixture(scope="session")
def create_test_sd():
    """Test SD should already exist in database (E2E001)"""
    return {'sd_number': 'E2E001'}


@pytest.fixture(scope="session")
def create_test_terminal():
    """Test terminal should already exist in database"""
    return {'name': 'TEST TERMINAL'}
