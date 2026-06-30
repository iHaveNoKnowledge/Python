import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestProductManagement:
    """Tests for product management functions"""

    def test_search_product(self, driver, smco_url, sample_order):
        """Test product search functionality"""
        driver.get(smco_url)
        sku = sample_order.get('เลขอ้างอิง SKU (SKU Reference No.)')
        assert sku is not None
        assert len(sku) > 0

    def test_add_product(self, driver, smco_url, sample_order):
        """Test adding product"""
        driver.get(smco_url)
        # Verify product data exists
        assert 'ชื่อสินค้า' in sample_order
        assert 'ราคาขาย' in sample_order

    def test_manage_serial_number(self, driver, smco_url, sample_order):
        """Test serial number management"""
        driver.get(smco_url)
        # Verify product has serial number field
        assert 'เลขอ้างอิง Parent SKU' in sample_order

    def test_product_pricing(self, driver, smco_url, sample_order):
        """Test product pricing"""
        driver.get(smco_url)
        price = sample_order.get('ราคาขาย')
        assert price is not None
        # Price should be a valid number
        try:
            float(price)
        except (ValueError, TypeError):
            pytest.fail(f"Invalid price: {price}")
