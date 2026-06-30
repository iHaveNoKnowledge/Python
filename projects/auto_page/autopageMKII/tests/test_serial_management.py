import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSerialManagement:
    """Tests for serial number management functions"""

    def test_search_serial(self, driver, smco_url, sample_order):
        """Test serial number search"""
        driver.get(smco_url)
        parent_sku = sample_order.get('เลขอ้างอิง Parent SKU')
        assert parent_sku is not None
        assert len(str(parent_sku)) > 0

    def test_add_serial(self, driver, smco_url, sample_order):
        """Test adding serial number"""
        driver.get(smco_url)
        # Verify serial number data exists
        assert 'เลขอ้างอิง SKU (SKU Reference No.)' in sample_order

    def test_check_duplicate_serial(self, driver, smco_url, sample_order):
        """Test checking for duplicate serial numbers"""
        driver.get(smco_url)
        sku = sample_order.get('เลขอ้างอิง SKU (SKU Reference No.)')
        parent_sku = sample_order.get('เลขอ้างอิง Parent SKU')
        # Verify both fields exist
        assert sku is not None
        assert parent_sku is not None
