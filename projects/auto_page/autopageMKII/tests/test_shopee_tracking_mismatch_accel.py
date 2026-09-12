import os
import sys
import unittest
from unittest.mock import MagicMock, patch

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


class MockVar:
    def __init__(self, value=None):
        self._val = value

    def get(self):
        return self._val

    def set(self, val):
        self._val = val


class TestShopeeTrackingMismatchAccel(unittest.TestCase):
    def setUp(self):
        # Mock App
        self.mock_app = MagicMock()
        self.mock_app.is_accel_mode = MockVar(True)
        self.mock_app.is_accel_mode_activated = MockVar(True)
        self.mock_app.is_auto_invoice_mode = MockVar(True)
        self.mock_app.is_bot_browser_busy = MockVar(True)
        self.mock_app.is_finish_order_triggered = MockVar(True)
        self.mock_app.cus_order = MockVar("260904TESTSHOPEE01")
        self.mock_app.tracking_from_data_complete = False
        self.mock_app.filter_data = MagicMock(empty=False)

        # Mock Bot
        self.mock_bot = MagicMock()
        self.mock_bot.app = self.mock_app
        self.mock_bot.driver = MagicMock()
        self.mock_bot.wait50 = MagicMock()
        self.mock_bot.cus_order = "260904TESTSHOPEE01"
        self.mock_bot.autofinal = True
        self.mock_bot.is_forbid = False
        self.mock_bot.is_skip = False
        self.mock_bot.clean_pos_cart = MagicMock()

        # Mock Accel Mode
        self.mock_accel = MagicMock()
        self.mock_app.accel_mode = self.mock_accel

        # Mock Report Manager
        self.mock_report = MagicMock()
        self.mock_app.report_manager = self.mock_report

    @patch("time.sleep", return_value=None)
    def test_shopee_tracking_mismatch_aborts_and_cleans_in_accel_auto_inv(self, mock_sleep):
        """
        ทดสอบว่าเมื่อ Tracking บน Shopee ไม่ครบ (Cards > Trackings / ติดนัดรับ):
        1. บอทไม่ค้างรอ ไม่เข้าลูป Your Turn
        2. สั่ง return_to_first_page()
        3. สั่ง clean_pos_cart() ล้างตะกร้า
        4. บันทึก failed_order ด้วย TRACKING_ERROR
        5. ตัดออเดอร์ออกจาก Sheet1 ด้วย deduct_accel_file_data(remove_order=True)
        6. สรุป report_manager เป็น FAILED
        7. คืนค่า False และเซ็ต is_skip = True
        """
        from functions.pos.payment_handler import POSPaymentHandler

        handler = POSPaymentHandler(bot=self.mock_bot)
        handler.return_to_first_page = MagicMock()

        # Mock driver element for detecting final page
        final_page_el = MagicMock()
        final_page_el.is_displayed.return_value = True
        final_page_el.text = "Payment: ชำระเงิน"
        self.mock_bot.driver.find_elements.return_value = [final_page_el]
        self.mock_bot.driver.find_element.return_value = final_page_el

        # จำลอง tracking_manager raise ValueError เนื่องจาก Card > Tracking
        mismatch_msg = "เลข Tracking บน Shopee ไม่ครบตามจำนวน Package: พบ 1/2 Cards (รายการที่ขาดเลข Tracking หรือติดนัดรับ: [Package #2])"
        self.mock_bot.tracking_manager.collect_tracking.side_effect = ValueError(mismatch_msg)

        # Setup loop state
        handler.last_page = final_page_el
        self.mock_bot.operation_thread.is_set.return_value = False

        result = handler.process_final_payment()

        # 1. คืนค่า False ทันที ไม่ค้าง
        self.assertFalse(result)

        # 2. return_to_first_page และ clean_pos_cart ถูกเรียก
        handler.return_to_first_page.assert_called_once()
        self.mock_bot.clean_pos_cart.assert_called_once()

        # 3. record_failed_order ถูกเรียกด้วย TRACKING_ERROR
        self.mock_accel.record_failed_order.assert_called_once()
        args, kwargs = self.mock_accel.record_failed_order.call_args
        self.assertEqual(args[0], "260904TESTSHOPEE01")
        self.assertIn("ไม่ครบตามจำนวน Package", args[1])
        self.assertEqual(kwargs.get("category"), "TRACKING_ERROR")

        # 4. deduct_accel_file_data ถูกเรียกเพื่อลบออเดอร์ออกจาก Sheet1
        self.mock_accel.deduct_accel_file_data.assert_called_once_with(
            "260904TESTSHOPEE01", remove_order=True, update_memory=True
        )

        # 5. report_manager บันทึก FAILED
        self.mock_report.finish_order.assert_called_once_with(
            "260904TESTSHOPEE01", overall_status="FAILED", note=args[1]
        )

        # 6. ธงข้ามถูกเซ็ต
        self.assertTrue(self.mock_bot.is_skip)
        self.assertFalse(self.mock_bot.autofinal)

    @patch("time.sleep", return_value=None)
    def test_record_failed_with_checkpoint_deducts_and_cleans_in_accel_auto_inv(self, mock_sleep):
        """
        ทดสอบว่าเมื่อเกิดข้อผิดพลาดใดๆ ที่ทำให้เรียก record_failed_with_checkpoint:
        ในโหมด auto_inv + accel_mode จะต้องตัดออเดอร์ออกจาก Sheet1 และล้างตะกร้า POS เสมอ
        """
        import importlib.util
        module_path = os.path.join(PROJECT_DIR, "autopage_MKII_ver5.x.x.py")
        spec = importlib.util.spec_from_file_location("autopage_v5_test_mod", module_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        Bot_POS = getattr(mod, "Bot_POS")

        # สร้าง instance แบบจำลอง
        bot = Bot_POS.__new__(Bot_POS)
        bot.app = self.mock_app
        bot.current_checkpoint = "ทดสอบกรอก SKU"
        bot.payment_handler = MagicMock()
        bot.clean_pos_cart = MagicMock()

        bot.record_failed_with_checkpoint("SKU ผิดพลาด")

        # บันทึก Failed Order
        self.mock_accel.record_failed_order.assert_called_once_with(
            "260904TESTSHOPEE01", "SKU ผิดพลาด (ด่านที่ติด: ทดสอบกรอก SKU)"
        )
        # ตัดออกจาก Sheet1
        self.mock_accel.deduct_accel_file_data.assert_called_once_with(
            "260904TESTSHOPEE01", remove_order=True, update_memory=True
        )
        # ล้างตะกร้า POS
        bot.clean_pos_cart.assert_called_once()


if __name__ == "__main__":
    unittest.main()
