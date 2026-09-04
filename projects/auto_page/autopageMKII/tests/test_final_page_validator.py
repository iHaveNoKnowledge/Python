import os
import sys
import unittest
from unittest.mock import MagicMock, patch

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from functions.pos.payment_handler import POSPaymentHandler
from selenium.webdriver.common.by import By


class TestFinalPageValidator(unittest.TestCase):
    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_app = MagicMock()
        self.mock_driver = MagicMock()
        self.mock_wait50 = MagicMock()

        self.mock_bot.app = self.mock_app
        self.mock_bot.driver = self.mock_driver
        self.mock_bot.wait50 = self.mock_wait50
        self.mock_bot.cus_order = "240827ABC12345"
        self.mock_app.cus_order.get.return_value = "240827ABC12345"
        self.mock_app.cus_name.get.return_value = "สมชาย รักดี"
        self.mock_app.final_price = 1250.00

        self.handler = POSPaymentHandler(self.mock_bot)

    def _create_mock_element(self, value: str = "", text: str = "", is_displayed: bool = True):
        el = MagicMock()
        el.get_attribute.side_effect = lambda attr: value if attr in ["value", "title"] else ""
        el.text = text
        el.is_displayed.return_value = is_displayed
        return el

    def test_verify_all_elements_valid(self):
        """ทุก Element มีค่าครบถ้วนและถูกต้อง -> all_ok ต้องเป็น True"""
        po_el = self._create_mock_element(value="240827ABC12345")
        name_el = self._create_mock_element(value="สมชาย รักดี")
        cash_el = self._create_mock_element(value="1,250.00")
        remark_el = self._create_mock_element(value="240827ABC12345 TH1234567890")
        balance_el = self._create_mock_element(text="0.00")
        btn_el = self._create_mock_element(is_displayed=True)

        def mock_find(by, xpath):
            if "textbox81037000102" in xpath:
                return po_el
            elif "textbox81037000101" in xpath:
                return name_el
            elif "ripCash00" in xpath:
                return cash_el
            elif "cnRemark" in xpath:
                return remark_el
            elif "wrimagecard-lightGray" in xpath:
                return balance_el
            elif "btnPayment" in xpath:
                return btn_el
            raise ValueError(f"Unexpected xpath: {xpath}")

        self.mock_driver.find_element.side_effect = mock_find

        res = self.handler.verify_final_page_elements(
            expected_po="240827ABC12345",
            expected_cus_name="สมชาย รักดี",
            expected_price=1250.00,
        )

        self.assertTrue(res["all_ok"])
        self.assertTrue(res["po_no"]["ok"])
        self.assertTrue(res["cus_name"]["ok"])
        self.assertTrue(res["cash_price"]["ok"])
        self.assertTrue(res["cn_remark"]["ok"])
        self.assertTrue(res["balance"]["ok"])
        self.assertTrue(res["btn_payment"]["ok"])

    def test_verify_fails_when_po_no_empty(self):
        """PO No. ว่างเปล่า -> all_ok ต้องเป็น False"""
        po_el = self._create_mock_element(value="")
        name_el = self._create_mock_element(value="สมชาย รักดี")
        cash_el = self._create_mock_element(value="1,250.00")
        remark_el = self._create_mock_element(value="240827ABC12345")
        balance_el = self._create_mock_element(text="0.00")
        btn_el = self._create_mock_element(is_displayed=True)

        def mock_find(by, xpath):
            if "textbox81037000102" in xpath:
                return po_el
            elif "textbox81037000101" in xpath:
                return name_el
            elif "ripCash00" in xpath:
                return cash_el
            elif "cnRemark" in xpath:
                return remark_el
            elif "wrimagecard-lightGray" in xpath:
                return balance_el
            elif "btnPayment" in xpath:
                return btn_el
            raise ValueError(f"Unexpected xpath: {xpath}")

        self.mock_driver.find_element.side_effect = mock_find

        res = self.handler.verify_final_page_elements(
            expected_po="240827ABC12345",
            expected_cus_name="สมชาย รักดี",
            expected_price=1250.00,
        )

        self.assertFalse(res["all_ok"])
        self.assertFalse(res["po_no"]["ok"])
        self.assertEqual(res["po_no"]["value"], "")

    def test_verify_fails_when_cash_price_mismatch(self):
        """ยอดเงินใน Cash ไม่ตรงกับ expected_price -> all_ok ต้องเป็น False"""
        po_el = self._create_mock_element(value="240827ABC12345")
        name_el = self._create_mock_element(value="สมชาย รักดี")
        cash_el = self._create_mock_element(value="1,000.00")  # ไม่ตรงกับ 1250
        remark_el = self._create_mock_element(value="240827ABC12345")
        balance_el = self._create_mock_element(text="0.00")
        btn_el = self._create_mock_element(is_displayed=True)

        def mock_find(by, xpath):
            if "textbox81037000102" in xpath:
                return po_el
            elif "textbox81037000101" in xpath:
                return name_el
            elif "ripCash00" in xpath:
                return cash_el
            elif "cnRemark" in xpath:
                return remark_el
            elif "wrimagecard-lightGray" in xpath:
                return balance_el
            elif "btnPayment" in xpath:
                return btn_el
            raise ValueError(f"Unexpected xpath: {xpath}")

        self.mock_driver.find_element.side_effect = mock_find

        res = self.handler.verify_final_page_elements(
            expected_po="240827ABC12345",
            expected_cus_name="สมชาย รักดี",
            expected_price=1250.00,
        )

        self.assertFalse(res["all_ok"])
        self.assertFalse(res["cash_price"]["ok"])
        self.assertEqual(res["cash_price"]["value"], 1000.00)

    def test_verify_fails_when_balance_not_zero(self):
        """ยอดคงเหลือ wrimagecard ไม่ใช่ 0.00 -> all_ok ต้องเป็น False"""
        po_el = self._create_mock_element(value="240827ABC12345")
        name_el = self._create_mock_element(value="สมชาย รักดี")
        cash_el = self._create_mock_element(value="1,250.00")
        remark_el = self._create_mock_element(value="240827ABC12345")
        balance_el = self._create_mock_element(text="250.00")  # ยังค้างจ่าย 250
        btn_el = self._create_mock_element(is_displayed=True)

        def mock_find(by, xpath):
            if "textbox81037000102" in xpath:
                return po_el
            elif "textbox81037000101" in xpath:
                return name_el
            elif "ripCash00" in xpath:
                return cash_el
            elif "cnRemark" in xpath:
                return remark_el
            elif "wrimagecard-lightGray" in xpath:
                return balance_el
            elif "btnPayment" in xpath:
                return btn_el
            raise ValueError(f"Unexpected xpath: {xpath}")

        self.mock_driver.find_element.side_effect = mock_find

        res = self.handler.verify_final_page_elements(
            expected_po="240827ABC12345",
            expected_cus_name="สมชาย รักดี",
            expected_price=1250.00,
        )

        self.assertFalse(res["all_ok"])
        self.assertFalse(res["balance"]["ok"])
        self.assertEqual(res["balance"]["value"], 250.00)

    def test_verify_fails_when_btn_payment_hidden(self):
        """ปุ่มเขียวไม่แสดงผล -> all_ok ต้องเป็น False"""
        po_el = self._create_mock_element(value="240827ABC12345")
        name_el = self._create_mock_element(value="สมชาย รักดี")
        cash_el = self._create_mock_element(value="1,250.00")
        remark_el = self._create_mock_element(value="240827ABC12345")
        balance_el = self._create_mock_element(text="0.00")
        btn_el = self._create_mock_element(is_displayed=False)

        def mock_find(by, xpath):
            if "textbox81037000102" in xpath:
                return po_el
            elif "textbox81037000101" in xpath:
                return name_el
            elif "ripCash00" in xpath:
                return cash_el
            elif "cnRemark" in xpath:
                return remark_el
            elif "wrimagecard-lightGray" in xpath:
                return balance_el
            elif "btnPayment" in xpath:
                return btn_el
            raise ValueError(f"Unexpected xpath: {xpath}")

        self.mock_driver.find_element.side_effect = mock_find

        res = self.handler.verify_final_page_elements(
            expected_po="240827ABC12345",
            expected_cus_name="สมชาย รักดี",
            expected_price=1250.00,
        )

        self.assertFalse(res["all_ok"])
        self.assertFalse(res["btn_payment"]["ok"])

    def test_recover_missing_elements(self):
        """ทดสอบฟังก์ชัน _recover_missing_elements ต้องสั่ง js_input_value ให้กับ element ที่ขาด"""
        failed_verification = {
            "po_no": {"ok": False},
            "cus_name": {"ok": False},
            "cash_price": {"ok": False},
            "cn_remark": {"ok": False},
            "balance": {"ok": True},
            "btn_payment": {"ok": True},
            "all_ok": False,
        }

        mock_el = MagicMock()
        self.mock_driver.find_element.return_value = mock_el

        self.handler._recover_missing_elements(
            failed_verification, final_price=1500.0, cus_name_val="ทดสอบ"
        )

        # ต้องมีการเรียก js_input_value 4 ครั้งสำหรับ 4 fields ที่ ok=False
        self.assertEqual(self.mock_bot.js_input_value.call_count, 4)


if __name__ == "__main__":
    unittest.main()
