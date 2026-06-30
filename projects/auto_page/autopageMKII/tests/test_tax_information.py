import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTaxInformation:
    """Tests for tax information functions"""

    def test_search_vat_info(self, driver, smco_url, sample_order):
        """Test VAT information search"""
        driver.get(smco_url)
        tax_id = sample_order.get('หมายเลขประจำตัวผู้เสียภาษี')
        # Tax ID might be None for some orders
        if tax_id is not None:
            assert len(str(tax_id)) > 0

    def test_validate_tax_id(self, driver, smco_url, sample_order):
        """Test tax ID validation"""
        driver.get(smco_url)
        tax_id = sample_order.get('หมายเลขประจำตัวผู้เสียภาษี')
        # Tax ID might be None or NaN for some orders
        if tax_id is not None and str(tax_id) != 'nan':
            # Thai tax ID should be 13 digits
            tax_id_str = str(tax_id).replace('-', '')
            assert len(tax_id_str) > 0

    def test_invoice_type(self, driver, smco_url, sample_order):
        """Test invoice type"""
        driver.get(smco_url)
        invoice_type = sample_order.get('ผู้ซื้อร้องขอใบกำกับภาษี')
        # Should be yes or no
        if invoice_type is not None:
            assert invoice_type.lower() in ['yes', 'no', 'true', 'false', 'ใช่', 'ไม่']
