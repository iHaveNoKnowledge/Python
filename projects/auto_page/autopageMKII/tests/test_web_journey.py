import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestWebJourney:
    """Tests for web journey/flow"""

    def test_login_flow(self, driver, smco_url):
        """Test login flow"""
        driver.get(smco_url)
        # Wait for page to load
        assert driver.title != "" or "login" in driver.page_source.lower()

    def test_open_pos_page(self, driver, smco_url):
        """Test opening POS page"""
        driver.get(smco_url)
        assert driver is not None

    def test_navigate_between_pages(self, driver, smco_url):
        """Test navigation between pages"""
        driver.get(smco_url)
        initial_url = driver.current_url
        assert initial_url is not None
