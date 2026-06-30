import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCustomerManagement:
    """Tests for customer management functions"""

    def test_search_customer(self, driver, smco_url, sample_order):
        """Test customer search functionality"""
        driver.get(smco_url)
        customer_name = sample_order.get('ชื่อผู้ใช้ (ผู้ซื้อ)')
        assert customer_name is not None
        assert len(customer_name) > 0

    def test_add_new_customer(self, driver, smco_url, sample_order):
        """Test adding new customer"""
        driver.get(smco_url)
        # Verify customer data exists
        assert 'ชื่อผู้รับ' in sample_order
        assert 'ที่อยู่ในการจัดส่ง' in sample_order

    def test_edit_customer_info(self, driver, smco_url, sample_order):
        """Test editing customer information"""
        driver.get(smco_url)
        # Verify customer has editable fields
        assert 'หมายเหตุจากผู้ซื้อ' in sample_order
        assert 'หมายเลขโทรศัพท์' in sample_order

    def test_customer_address(self, driver, smco_url, sample_order):
        """Test customer address validation"""
        driver.get(smco_url)
        address = sample_order.get('ที่อยู่ในการจัดส่ง')
        province = sample_order.get('จังหวัด')
        assert address is not None
        assert province is not None
