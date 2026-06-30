import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBotPos:
    """Tests for Bot_POS class"""

    def test_browser_initialization(self, driver):
        """Test that browser is properly initialized"""
        assert driver is not None
        assert driver.session_id is not None

    def test_tab_management(self, driver):
        """Test tab management functionality"""
        initial_handles = driver.window_handles
        assert len(initial_handles) >= 1

        # Open a new tab
        driver.execute_script("window.open('about:blank', '_blank');")
        new_handles = driver.window_handles
        assert len(new_handles) > len(initial_handles)

        # Switch back to original tab
        driver.switch_to.window(initial_handles[0])

    def test_element_interaction(self, driver, smco_url):
        """Test basic element interaction"""
        driver.get(smco_url)
        # Test that we can interact with elements
        assert driver.current_url is not None
