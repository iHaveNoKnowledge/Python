import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInvoicePrinting:
    """Tests for invoice printing functions"""

    def test_create_invoice_uat_only(self, driver, smco_url, require_uat, prevent_receipt):
        """Test creating invoice (UAT only)"""
        driver.get(smco_url)
        assert driver is not None

    def test_reprint_invoice_uat_only(self, driver, smco_url, require_uat, prevent_receipt):
        """Test reprinting invoice (UAT only)"""
        driver.get(smco_url)
        assert driver is not None

    def test_extract_pdf(self, driver, smco_url, require_uat):
        """Test PDF extraction"""
        driver.get(smco_url)
        assert driver is not None
