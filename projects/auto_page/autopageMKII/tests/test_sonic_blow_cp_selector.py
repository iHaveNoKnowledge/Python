import os
import sys
import time
import unittest
from unittest.mock import MagicMock, call
from selenium.webdriver.common.by import By

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from functions.pos.pricing_engine import POSPricingReconciler


class TestSonicBlowCPSelector(unittest.TestCase):
    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_app = MagicMock()
        self.mock_driver = MagicMock()

        self.mock_bot.app = self.mock_app
        self.mock_bot.driver = self.mock_driver
        self.mock_bot.merged_dict = {'SMCO :: เปิดการขาย': 'mock_window_handle'}

        # Mock items in app
        self.mock_app.items = [
            {'เลขอ้างอิง SKU (SKU Reference No.)': 'SP2-001845, SP2-001846, SP2-001847, SP2-001848'}
        ]
        self.mock_app.correct_sku_pattern.return_value = [
            'SP2-001845', 'SP2-001846', 'SP2-001847', 'SP2-001848'
        ]

        self.reconciler = POSPricingReconciler(self.mock_bot)

    def _setup_dom_mock(self, num_items=4):
        """ตั้งค่า DOM Mock ให้จำลองหน้า POS ของ SMCO ที่มีสินค้าหลายรายการ"""
        # Panel innerText ของแต่ละรายการบน POS
        panel_texts = [f"SP2-00184{5 + i} Panel Information" for i in range(num_items)]

        def mock_execute_script(script, *args):
            if "querySelectorAll('.col-sm-12.panel.panel-default.ng-scope')" in script:
                return panel_texts
            return None

        self.mock_driver.execute_script.side_effect = mock_execute_script

        # Mock coupon buttons สำหรับแต่ละแถวสินค้าบน POS
        self.coupon_buttons = []
        for i in range(num_items):
            btn = MagicMock(name=f"coupon_btn_{i}")
            btn.is_displayed.return_value = True
            self.coupon_buttons.append(btn)

        # Mock coupon modal elements
        self.modal_coupon_names = []
        self.modal_coupon_select_btns = []
        for i in range(5):
            name_el = MagicMock(name=f"cp_name_{i}")
            name_el.text = f"CP260831003{i+1}"
            name_el.is_displayed.return_value = True
            self.modal_coupon_names.append(name_el)

            sel_btn = MagicMock(name=f"cp_select_btn_{i}")
            sel_btn.is_displayed.return_value = True
            self.modal_coupon_select_btns.append(sel_btn)

        # Mock OK agree button in modal
        self.ok_btn = MagicMock(name="ok_agree_btn")
        self.ok_btn.is_displayed.return_value = True

        def mock_find_elements(by, locator):
            # ตรวจสอบปุ่ม coupon ในรายการสินค้า
            if by == By.XPATH and "//button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]" in locator:
                return self.coupon_buttons
            # ตรวจสอบปุ่มเลือกคูปองใน Modal
            if by == By.XPATH and "selectCoupon" in locator:
                return self.modal_coupon_select_btns
            # ตรวจสอบชื่อคูปองใน Modal
            if by == By.XPATH and "price-sku-h1" in locator:
                return self.modal_coupon_names
            # ตรวจสอบปุ่มยืนยัน OK ใน Modal
            if by == By.CSS_SELECTOR and locator == 'button[ng-click="okCoupon()"]':
                return [self.ok_btn]
            # ตรวจสอบ Modal backdrop
            if by == By.CSS_SELECTOR and "modal-backdrop" in locator:
                return []
            return []

        self.mock_driver.find_elements.side_effect = mock_find_elements

    def test_uses_exact_xpath_locator_and_interacts_all_items(self):
        """
        ทดสอบว่า cp_sonic_blow_process ใช้ XPath ที่ถูกต้อง:
        //button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]
        และกดเลือก coupon ครบทุก 4 ไอเทม โดยไม่มีไอเทมใดถูกข้าม
        """
        self._setup_dom_mock(num_items=4)

        result = self.reconciler.cp_sonic_blow_process(item_no=1, cp_no="4")

        self.assertTrue(result, "การเลือกคูปองควรคืนค่าความสำเร็จ (True)")

        # ตรวจสอบว่า find_elements ถูกเรียกด้วย XPath แม่นยำตัวใหม่
        xpath_calls = [
            call_args for call_args in self.mock_driver.find_elements.call_args_list
            if call_args[0][0] == By.XPATH and "//button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]" in call_args[0][1]
        ]
        self.assertTrue(len(xpath_calls) >= 4, "ต้องค้นหาปุ่ม coupon ด้วย XPath ใหม่อย่างน้อย 4 ครั้ง (รอบละ 1 สินค้า)")

        # ตรวจสอบว่าปุ่ม coupon ของสินค้าทั้ง 4 ตัวถูกคลิกครบถ้วน
        for i, btn in enumerate(self.coupon_buttons):
            self.assertTrue(btn.click.called, f"ปุ่ม coupon ของสินค้าลำดับที่ {i+1} (index {i}) ต้องถูกคลิก")

        # ตรวจสอบว่าปุ่ม OK ใน Modal ถูกคลิกครบ 4 รอบ
        self.assertEqual(self.ok_btn.click.call_count, 4, "ปุ่ม OK ต้องถูกคลิกครบ 4 รอบ (1 รอบต่อ 1 สินค้า)")

    def test_avoids_hidden_duplicate_elements_pitfall(self):
        """
        จำลองบัคเดิมที่เคยเจอ 8 elements (แท้ 4, ซ่อน 4)
        ทดสอบว่าโค้ดใหม่ไม่ใช้ CSS Selector แบบกว้างที่ดึงเจอ element แฝง
        """
        self._setup_dom_mock(num_items=4)

        self.reconciler.cp_sonic_blow_process(item_no=1, cp_no="4")

        # ยืนยันว่าไม่มีการเรียกใช้ CSS Selector ตัวเก่าใน find_elements สำหรับปุ่ม coupon
        old_css_calls = [
            call_args for call_args in self.mock_driver.find_elements.call_args_list
            if call_args[0][0] == By.CSS_SELECTOR and "button.btn-coupon.btn.btn-sm" in call_args[0][1]
        ]
        self.assertEqual(len(old_css_calls), 0, "ต้องไม่มีการเรียกใช้ CSS Selector เก่าที่เสี่ยงดึง element ซ่อน")

    def test_coupon_selection_by_index_and_memorization(self):
        """
        ทดสอบการเลือกคูปองด้วยตัวเลขลำดับ (เช่น '4')
        และระบบจดจำชื่อคูปองเพื่อใช้เลือกในสินค้าถัดไป
        """
        self._setup_dom_mock(num_items=4)

        result = self.reconciler.cp_sonic_blow_process(item_no=1, cp_no="4")
        self.assertTrue(result)

        # Index 4 คือ item ที่ 4 (0-based index = 3 -> modal_coupon_select_btns[3])
        target_coupon_btn = self.modal_coupon_select_btns[3]
        self.assertTrue(target_coupon_btn.click.called, "ปุ่มคูปองที่ index 3 ต้องถูกคลิก")

    def test_fast_execution_without_excessive_delays(self):
        """
        ทดสอบว่าไม่มีการใส่ sleep นานเกินไป (เช่น 0.8s, 0.6s) ในรอบการทำงาน
        การรัน 4 สินค้าด้วย Mock ต้องเสร็จสิ้นในเวลารวดเร็ว
        """
        self._setup_dom_mock(num_items=4)

        start_time = time.time()
        self.reconciler.cp_sonic_blow_process(item_no=1, cp_no="4")
        duration = time.time() - start_time

        # เมื่อตัด 0.8s, 0.6s, 0.5s ออกและมีเพียง 0.1s UI update ต่อ token
        # 4 สินค้าควรใช้เวลาไม่เกิน 1.5 วินาที
        self.assertLess(duration, 1.5, f"การทำงานต้องรวดเร็ว ไม่หน่วงเวลานานเกินไป (ใช้เวลา {duration:.2f} วินาที)")

    def test_scan_matching_cp_candidates_uses_exact_xpath(self):
        """
        ทดสอบว่า scan_matching_cp_candidates_on_smco ก็ถูกปรับมาใช้ XPath ที่ถูกต้องเช่นกัน
        """
        self._setup_dom_mock(num_items=4)

        cp_candidates = [
            {"cp_name": "CP2608310031"},
            {"cp_name": "NONE"}
        ]

        matched = self.reconciler.scan_matching_cp_candidates_on_smco(item_no=1, cp_candidates=cp_candidates)

        # ตรวจสอบว่า find_elements ในฟังก์ชัน scan ถูกเรียกด้วย XPath ใหม่
        xpath_calls = [
            call_args for call_args in self.mock_driver.find_elements.call_args_list
            if call_args[0][0] == By.XPATH and "//button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]" in call_args[0][1]
        ]
        self.assertTrue(len(xpath_calls) >= 1, "scan_matching_cp_candidates_on_smco ต้องใช้ XPath ใหม่")
        self.assertEqual(len(matched), 2, "ควร match ทั้งคูปองที่มีอยู่จริงและ NONE")


if __name__ == "__main__":
    unittest.main()
