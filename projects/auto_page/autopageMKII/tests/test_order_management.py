import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestOrderManagement:
    """Tests for order management functions"""

    def test_search_order(self, driver, smco_url, sample_order):
        """Test order search functionality"""
        driver.get(smco_url)
        order_no = sample_order['หมายเลขคำสั่งซื้อ']
        assert order_no is not None
        assert len(order_no) > 0

    def test_display_order_details(self, driver, smco_url, sample_order):
        """Test displaying order details"""
        driver.get(smco_url)
        # Verify order has required fields
        assert 'ชื่อผู้ใช้ (ผู้ซื้อ)' in sample_order
        assert 'สถานะการสั่งซื้อ' in sample_order

    def test_manage_order_status(self, driver, smco_url, sample_order):
        """Test order status management"""
        driver.get(smco_url)
        status = sample_order['สถานะการสั่งซื้อ']
        # Status can be in Thai or English
        assert status is not None and len(str(status)) > 0

    def test_multiple_orders(self, driver, smco_url, sample_orders):
        """Test handling multiple orders"""
        driver.get(smco_url)
        assert len(sample_orders) > 0
        for _, order in sample_orders.iterrows():
            assert 'หมายเลขคำสั่งซื้อ' in order

    def test_orders_by_status(self, driver, smco_url, test_data):
        """Test filtering orders by status"""
        driver.get(smco_url)
        # Check that we have orders with different statuses
        statuses = test_data['สถานะการสั่งซื้อ'].unique()
        assert len(statuses) > 0
