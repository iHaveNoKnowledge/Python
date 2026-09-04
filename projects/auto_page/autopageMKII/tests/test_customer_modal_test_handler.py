import os
import sys
import unittest
from unittest.mock import MagicMock, patch

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from functions.pos.customer_test_handler import CustomerModalTestHandler
from functions.utils.report_manager import TestReportManager


class TestCustomerModalTestHandler(unittest.TestCase):
    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_app = MagicMock()
        self.mock_driver = MagicMock()
        self.mock_wait50 = MagicMock()

        self.mock_bot.app = self.mock_app
        self.mock_bot.driver = self.mock_driver
        self.mock_bot.wait50 = self.mock_wait50
        self.mock_bot.cus_order = "240904TEST001"
        self.mock_app.cus_order.get.return_value = "240904TEST001"
        self.mock_app.marketplace_target.get.return_value = "SHOPEE"

        self.report_mgr = TestReportManager(output_dir=os.path.join(PROJECT_DIR, "reports"))
        self.mock_bot.report_manager = self.report_mgr

        self.handler = CustomerModalTestHandler(self.mock_bot)

    def _create_mock_element(self, value="", title="", text="", disabled=None, is_enabled=True):
        el = MagicMock()
        def mock_attr(name):
            if name == "value":
                return value
            if name == "title":
                return title
            if name == "disabled":
                return disabled
            return ""
        el.get_attribute.side_effect = mock_attr
        el.text = text
        el.is_enabled.return_value = is_enabled
        return el

    def test_clean_place_name(self):
        """ตรวจสอบว่า clean_place_name ตัดคำนำหน้าภาษาไทยได้ถูกต้อง"""
        self.assertEqual(self.handler.clean_place_name("จังหวัดกรุงเทพมหานคร"), "กรุงเทพมหานคร")
        self.assertEqual(self.handler.clean_place_name("เขตวัฒนา"), "วัฒนา")
        self.assertEqual(self.handler.clean_place_name("อำเภอเมือง"), "เมือง")
        self.assertEqual(self.handler.clean_place_name("แขวงคลองเตยเหนือ"), "คลองเตยเหนือ")
        self.assertEqual(self.handler.clean_place_name("ต.สระตะเคียน"), "สระตะเคียน")

    def test_match_place_value_thai_and_english(self):
        """ตรวจสอบว่า match_place_value รองรับทั้งคำภาษาไทยและอังกฤษ"""
        # ภาษาไทยตรงกัน
        self.assertTrue(self.handler.match_place_value("กรุงเทพมหานคร", "กรุงเทพมหานคร", "province"))
        self.assertTrue(self.handler.match_place_value("จังหวัดนนทบุรี", "นนทบุรี", "province"))

        # ภาษาอังกฤษตรงกัน
        self.assertTrue(self.handler.match_place_value("Bangkok", "Bangkok", "province"))

        # ผ่าน translation lookup table ของ bot
        self.mock_bot.translate_eng_to_thai_place.side_effect = lambda val, p_type: "วัฒนา" if "watthana" in val.lower() else val
        self.assertTrue(self.handler.match_place_value("วัฒนา", "Watthana", "district"))
        self.assertTrue(self.handler.match_place_value("Watthana", "วัฒนา", "district"))

    def test_run_test_success_when_all_match_and_disabled_removed(self):
        """กรณีทุก field ตรงครบ และ attribute disabled หายไป -> ผลการทดสอบต้องเป็น PASS"""
        # 1. Setup mock elements
        save_btn_initial = self._create_mock_element(disabled="disabled", is_enabled=False)
        save_btn_final = self._create_mock_element(disabled=None, is_enabled=True)

        name_th_el = self._create_mock_element(value="บริษัท ทดสอบ จำกัด (สำนักงานใหญ่)")
        name_en_el = self._create_mock_element(value="บริษัท ทดสอบ จำกัด (สำนักงานใหญ่)")
        id_el = self._create_mock_element(value="0105555000000")
        addr_el = self._create_mock_element(value="99/99 อาคารทดสอบ")
        prov_el = self._create_mock_element(title="กรุงเทพมหานคร")
        dist_el = self._create_mock_element(title="วัฒนา")
        subdist_el = self._create_mock_element(title="คลองเตยเหนือ")
        zip_el = self._create_mock_element(title="10110")
        cancel_btn = self._create_mock_element()

        # Save button transition: first call (init check) disabled, second call (final check) enabled
        save_call_count = [0]
        def mock_save_find():
            save_call_count[0] += 1
            if save_call_count[0] == 1:
                return save_btn_initial
            return save_btn_final

        def mock_find_element(by, xpath):
            if "saveNewMember" in xpath:
                return mock_save_find()
            elif "memNameTh" in xpath:
                return name_th_el
            elif "memNameEn" in xpath:
                return name_en_el
            elif "identity" in xpath:
                return id_el
            elif "addressCustomer" in xpath:
                return addr_el
            elif "select2-province-container" in xpath:
                return prov_el
            elif "select2-district-container" in xpath:
                return dist_el
            elif "select2-subDistrict-container" in xpath:
                return subdist_el
            elif "select2-zipCodeSel-container" in xpath:
                return zip_el
            elif "button[2]" in xpath:
                return cancel_btn
            return self._create_mock_element()

        self.mock_driver.find_element.side_effect = mock_find_element

        cust_data = {
            "name": "บริษัท ทดสอบ จำกัด (สำนักงานใหญ่)",
            "tax_id": "0105555000000",
            "address": "99/99 อาคารทดสอบ",
            "province": "กรุงเทพมหานคร",
            "district": "วัฒนา",
            "sub_district": "คลองเตยเหนือ",
            "postcode": "10110",
        }

        result = self.handler.run_test(customer_data=cust_data, close_modal_after_test=True)

        self.assertTrue(result["passed"], f"Test should pass but failed: {result['fail_reasons']}")
        self.assertTrue(result["initial_disabled_check"])
        self.assertTrue(result["name_th_match"])
        self.assertTrue(result["name_en_match"])
        self.assertTrue(result["names_identical"])
        self.assertTrue(result["save_btn_disabled_removed"])
        self.assertEqual(len(result["fail_reasons"]), 0)

        # ตรวจสอบว่า record เข้า TestReportManager
        rec = self.report_mgr.records.get("240904TEST001")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["customer_status"], "SUCCESS")
        self.assertEqual(rec["overall_status"], "SUCCESS")

    def test_run_test_fails_when_save_button_remains_disabled(self):
        """กรณีปุ่ม saveNewMember ยังคงมี attribute disabled='disabled' อยู่หลังกรอก -> ต้องเป็น FAIL"""
        save_btn = self._create_mock_element(disabled="disabled", is_enabled=False)
        name_el = self._create_mock_element(value="ชื่อลูกค้า")
        id_el = self._create_mock_element(value="1234567890123")
        addr_el = self._create_mock_element(value="ที่อยู่")
        prov_el = self._create_mock_element(title="นนทบุรี")
        dist_el = self._create_mock_element(title="เมืองนนทบุรี")
        subdist_el = self._create_mock_element(title="บางเขน")
        zip_el = self._create_mock_element(title="11000")
        cancel_btn = self._create_mock_element()

        def mock_find_element(by, xpath):
            if "saveNewMember" in xpath:
                return save_btn
            elif "memNameTh" in xpath or "memNameEn" in xpath:
                return name_el
            elif "identity" in xpath:
                return id_el
            elif "addressCustomer" in xpath:
                return addr_el
            elif "select2-province-container" in xpath:
                return prov_el
            elif "select2-district-container" in xpath:
                return dist_el
            elif "select2-subDistrict-container" in xpath:
                return subdist_el
            elif "select2-zipCodeSel-container" in xpath:
                return zip_el
            elif "button[2]" in xpath:
                return cancel_btn
            return self._create_mock_element()

        self.mock_driver.find_element.side_effect = mock_find_element

        cust_data = {
            "name": "ชื่อลูกค้า",
            "tax_id": "1234567890123",
            "address": "ที่อยู่",
            "province": "นนทบุรี",
            "district": "เมืองนนทบุรี",
            "sub_district": "บางเขน",
            "postcode": "11000",
        }

        result = self.handler.run_test(customer_data=cust_data, close_modal_after_test=True)

        self.assertFalse(result["passed"])
        self.assertFalse(result["save_btn_disabled_removed"])
        self.assertTrue(any("disabled" in r for r in result["fail_reasons"]))

        # ตรวจสอบว่า record ใน report manager กลายเป็น FAILED
        rec = self.report_mgr.records.get("240904TEST001")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["customer_status"], "FAILED")
        self.assertEqual(rec["overall_status"], "FAILED")

    def test_run_test_fails_when_dropdown_mismatch(self):
        """กรณี Dropdown ไม่ตรงกับข้อมูลต้นทาง -> ต้องเป็น FAIL พร้อมระบุสาเหตุที่ชัดเจน"""
        save_btn_initial = self._create_mock_element(disabled="disabled", is_enabled=False)
        save_btn_final = self._create_mock_element(disabled=None, is_enabled=True)

        name_el = self._create_mock_element(value="บริษัท ทดสอบ จำกัด")
        id_el = self._create_mock_element(value="0105555000000")
        addr_el = self._create_mock_element(value="99/99 อาคารทดสอบ")
        prov_el = self._create_mock_element(title="เชียงใหม่")  # ไม่ตรงกับที่คาดหวัง (กรุงเทพมหานคร)
        dist_el = self._create_mock_element(title="วัฒนา")
        subdist_el = self._create_mock_element(title="คลองเตยเหนือ")
        zip_el = self._create_mock_element(title="10110")
        cancel_btn = self._create_mock_element()

        save_call_count = [0]
        def mock_save_find():
            save_call_count[0] += 1
            if save_call_count[0] == 1:
                return save_btn_initial
            return save_btn_final

        def mock_find_element(by, xpath):
            if "saveNewMember" in xpath:
                return mock_save_find()
            elif "memNameTh" in xpath or "memNameEn" in xpath:
                return name_el
            elif "identity" in xpath:
                return id_el
            elif "addressCustomer" in xpath:
                return addr_el
            elif "select2-province-container" in xpath:
                return prov_el
            elif "select2-district-container" in xpath:
                return dist_el
            elif "select2-subDistrict-container" in xpath:
                return subdist_el
            elif "select2-zipCodeSel-container" in xpath:
                return zip_el
            elif "button[2]" in xpath:
                return cancel_btn
            return self._create_mock_element()

        self.mock_driver.find_element.side_effect = mock_find_element

        cust_data = {
            "name": "บริษัท ทดสอบ จำกัด",
            "tax_id": "0105555000000",
            "address": "99/99 อาคารทดสอบ",
            "province": "กรุงเทพมหานคร",
            "district": "วัฒนา",
            "sub_district": "คลองเตยเหนือ",
            "postcode": "10110",
        }

        result = self.handler.run_test(customer_data=cust_data, close_modal_after_test=True)

        self.assertFalse(result["passed"])
        self.assertFalse(result["province_match"])
        self.assertTrue(any("จังหวัด" in r for r in result["fail_reasons"]))

    def test_run_test_uses_order_id_from_customer_data(self):
        """ตรวจสอบว่า run_test นำ order_id จาก customer_data ไปใช้ในผลลัพธ์และรายงาน"""
        save_btn_initial = self._create_mock_element(disabled="disabled", is_enabled=False)
        save_btn_final = self._create_mock_element(disabled=None, is_enabled=True)
        name_el = self._create_mock_element(value="ลูกค้าทดสอบ")
        addr_el = self._create_mock_element(value="123 ถ.สุขุมวิท")
        prov_el = self._create_mock_element(title="กรุงเทพมหานคร")
        dist_el = self._create_mock_element(title="วัฒนา")
        subdist_el = self._create_mock_element(title="คลองเตยเหนือ")
        zip_el = self._create_mock_element(title="10110")

        save_call_count = [0]
        def mock_save_find():
            save_call_count[0] += 1
            return save_btn_initial if save_call_count[0] == 1 else save_btn_final

        def mock_find_element(by, xpath):
            if "saveNewMember" in xpath:
                return mock_save_find()
            elif "memNameTh" in xpath or "memNameEn" in xpath:
                return name_el
            elif "addressCustomer" in xpath:
                return addr_el
            elif "select2-province-container" in xpath:
                return prov_el
            elif "select2-district-container" in xpath:
                return dist_el
            elif "select2-subDistrict-container" in xpath:
                return subdist_el
            elif "select2-zipCodeSel-container" in xpath:
                return zip_el
            return self._create_mock_element()

        self.mock_driver.find_element.side_effect = mock_find_element

        custom_order = "240904SPECIFIC999"
        cust_data = {
            "order_id": custom_order,
            "name": "ลูกค้าทดสอบ",
            "tax_id": "",
            "address": "123 ถ.สุขุมวิท",
            "province": "กรุงเทพมหานคร",
            "district": "วัฒนา",
            "sub_district": "คลองเตยเหนือ",
            "postcode": "10110",
        }

        result = self.handler.run_test(customer_data=cust_data, close_modal_after_test=True)
        self.assertEqual(result["order_id"], custom_order)
        self.assertTrue(result["passed"])

        # ตรวจสอบว่า record ใน TestReportManager ถูกบันทึกด้วย order_id ที่ระบุ
        rec = self.report_mgr.records.get(custom_order)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["customer_status"], "SUCCESS")

    def test_gather_customer_data_from_app_with_entered_order(self):
        """ตรวจสอบว่า _gather_customer_data_from_app อ่าน order_id จาก entered_order ได้หาก cus_order ว่าง"""
        self.mock_app.cus_order.get.return_value = ""
        self.mock_app.entered_order = MagicMock()
        self.mock_app.entered_order.get.return_value = "ORDER_FROM_ENTRY_BOX"
        self.mock_app.cus_name.get.return_value = "คุณลูกค้า สบายดี"
        self.mock_app.tax_num.get.return_value = ""
        self.mock_app.address = "12/34 ม.5"
        self.mock_app.cus_province.get.return_value = "เชียงใหม่"
        self.mock_app.cus_district.get.return_value = "เมืองเชียงใหม่"
        self.mock_app.cus_sub_district.get.return_value = "สุเทพ"
        self.mock_app.cus_postcode.get.return_value = "50200"

        data = self.handler._gather_customer_data_from_app()
        self.assertEqual(data["order_id"], "ORDER_FROM_ENTRY_BOX")
        self.assertEqual(data["name"], "คุณลูกค้า สบายดี")
        self.assertEqual(data["province"], "เชียงใหม่")
        self.assertEqual(data["tax_id"], "")

    def test_gather_customer_data_from_app_with_nondistortedData_fallback(self):
        """ตรวจสอบ fallback ไปยัง nondistortedData เมื่อค่าใน StringVar ว่าง (เช่น ออเดอร์ไม่ขอใบกำกับ)"""
        self.mock_app.cus_order.get.return_value = "240904FALLBACK01"
        self.mock_app.cus_name.get.return_value = "ลูกค้า ทั่วไป"
        self.mock_app.tax_num.get.return_value = ""
        self.mock_app.address = ""
        self.mock_app.cus_province.get.return_value = ""
        self.mock_app.cus_district.get.return_value = ""
        self.mock_app.cus_sub_district.get.return_value = ""
        self.mock_app.cus_postcode.get.return_value = ""
        self.mock_app.nondistortedData = {
            'จังหวัด.1': 'ชลบุรี',
            'เขต/อำเภอ.1': 'บางละมุง',
            'แขวง/ตำบล': 'หนองปรือ',
            'รหัสไปรษณีย์.1': '20150',
            'รายละเอียดที่อยู่': '55/66 พัทยากลาง'
        }

        data = self.handler._gather_customer_data_from_app()
        self.assertEqual(data["order_id"], "240904FALLBACK01")
        self.assertEqual(data["province"], "ชลบุรี")
        self.assertEqual(data["district"], "บางละมุง")
        self.assertEqual(data["sub_district"], "หนองปรือ")
        self.assertEqual(data["postcode"], "20150")
        self.assertEqual(data["address"], "55/66 พัทยากลาง")


if __name__ == "__main__":
    unittest.main()
