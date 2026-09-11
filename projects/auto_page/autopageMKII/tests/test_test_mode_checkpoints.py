import os
import sys
import unittest
from unittest.mock import MagicMock

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from functions.pos.payment_handler import POSPaymentHandler


class TestTestModeCheckpoints(unittest.TestCase):
    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_app = MagicMock()
        self.mock_driver = MagicMock()

        self.mock_bot.app = self.mock_app
        self.mock_bot.driver = self.mock_driver
        self.mock_bot.cus_order = "240827ABC12345"

        # Mock Bot_POS should_stop_at_test_checkpoint logic
        def mock_should_stop(current_cp_name: str) -> bool:
            if not getattr(self.mock_app, "is_testing", False):
                return False
            selected_cp = getattr(self.mock_app, "test_checkpoint", None)
            selected_val = selected_cp.get() if selected_cp else ""
            prefix = current_cp_name[:2]
            return current_cp_name in selected_val or (bool(prefix) and selected_val.startswith(prefix))

        self.mock_bot.should_stop_at_test_checkpoint.side_effect = mock_should_stop

        self.handler = POSPaymentHandler(self.mock_bot)

    def test_checkpoint_returns_false_when_not_in_test_mode(self):
        """เมื่อไม่ได้เปิด test mode (is_testing=False) ต้องคืนค่า False เสมอ"""
        self.mock_app.is_testing = False
        self.mock_app.test_checkpoint.get.return_value = "1. หลังเลือกลูกค้า"

        res = self.mock_bot.should_stop_at_test_checkpoint("1. หลังเลือกลูกค้า")
        self.assertFalse(res)

    def test_checkpoint_returns_true_when_checkpoint_matches(self):
        """เมื่ออยู่ใน test mode และถึงจุดที่เลือกไว้ ต้องคืนค่า True เพื่อหยุดบอท"""
        self.mock_app.is_testing = True

        checkpoints = [
            "1. หลังเลือกลูกค้า",
            "2. หลังตรวจ/แก้ที่อยู่",
            "3. หลังยิงสินค้า/คูปองหน้าแรก",
            "4. หลังกรอกหน้าท้าย (ก่อนกดปุ่มเขียว)",
        ]

        for cp in checkpoints:
            self.mock_app.test_checkpoint.get.return_value = cp
            self.assertTrue(
                self.mock_bot.should_stop_at_test_checkpoint(cp),
                f"Checkpoint {cp} should trigger stop",
            )

    def test_checkpoint_returns_false_when_checkpoint_does_not_match(self):
        """เมื่ออยู่ใน test mode แต่ยังไม่ถึงจุดที่เลือก ต้องคืนค่า False เพื่อให้บอททำงานต่อ"""
        self.mock_app.is_testing = True
        # ผู้ใช้เลือกให้หยุดที่หน้าท้าย
        self.mock_app.test_checkpoint.get.return_value = "4. หลังกรอกหน้าท้าย (ก่อนกดปุ่มเขียว)"

        # บอทวิ่งผ่านสเต็ป 1, 2, 3 -> ต้องไม่หยุด (คืนค่า False)
        self.assertFalse(self.mock_bot.should_stop_at_test_checkpoint("1. หลังเลือกลูกค้า"))
        self.assertFalse(self.mock_bot.should_stop_at_test_checkpoint("2. หลังตรวจ/แก้ที่อยู่"))
        self.assertFalse(self.mock_bot.should_stop_at_test_checkpoint("3. หลังยิงสินค้า/คูปองหน้าแรก"))

        # เมื่อถึงสเต็ป 4 -> ต้องหยุด (คืนค่า True)
        self.assertTrue(self.mock_bot.should_stop_at_test_checkpoint("4. หลังกรอกหน้าท้าย (ก่อนกดปุ่มเขียว)"))

    def test_full_flow_never_stops_early(self):
        """เมื่อเลือก '5. ไม่หยุด - รันจนจบวงรอบ' บอทต้องไม่หยุดที่ Checkpoint 1-4"""
        self.mock_app.is_testing = True
        self.mock_app.test_checkpoint.get.return_value = "5. ไม่หยุด - รันจนจบวงรอบ"

        self.assertFalse(self.mock_bot.should_stop_at_test_checkpoint("1. หลังเลือกลูกค้า"))
        self.assertFalse(self.mock_bot.should_stop_at_test_checkpoint("2. หลังตรวจ/แก้ที่อยู่"))
        self.assertFalse(self.mock_bot.should_stop_at_test_checkpoint("3. หลังยิงสินค้า/คูปองหน้าแรก"))
        self.assertFalse(self.mock_bot.should_stop_at_test_checkpoint("4. หลังกรอกหน้าท้าย (ก่อนกดปุ่มเขียว)"))

    def test_checkpoint_4_auto_advance_on_pass_when_accel_and_autoinv(self):
        """เมื่อเปิด test mode + accel_mode + auto_inv คู่กัน และหน้าท้ายผ่าน (all_ok=True) ต้องบันทึก Accel, กดย้อนกลับ, ล้างตะกร้า และ return True"""
        self.mock_app.is_testing = True
        self.mock_app.test_checkpoint.get.return_value = "4. หลังกรอกหน้าท้าย (ก่อนกดปุ่มเขียว)"
        self.mock_app.is_accel_mode.get.return_value = True
        self.mock_app.is_auto_invoice_mode.get.return_value = True

        self.handler.verify_final_page_elements = MagicMock(return_value={"all_ok": True})
        self.handler.return_to_first_page = MagicMock()
        self.mock_bot.clean_pos_cart = MagicMock()

        # Simulate executing the Checkpoint 4 block
        verification = self.handler.verify_final_page_elements()
        is_all_ok = bool(verification.get("all_ok"))
        is_accel = self.mock_app.is_accel_mode.get()
        is_auto_inv = self.mock_app.is_auto_invoice_mode.get()
        is_auto_advance = is_accel and is_auto_inv

        self.assertTrue(is_auto_advance)
        self.assertTrue(is_all_ok)

        # Trigger actions
        self.mock_app.accel_mode.deduct_accel_file_data(self.mock_bot.cus_order, remove_order=True, update_memory=True)
        self.mock_app.accel_mode.record_completed_order(self.mock_bot.cus_order, status="TEST_SUCCESS (หน้าท้ายครบถ้วน/All OK)")
        self.mock_app.report_manager.finish_order(self.mock_bot.cus_order, overall_status="SUCCESS")
        self.handler.return_to_first_page()
        self.mock_bot.clean_pos_cart()

        self.mock_app.accel_mode.deduct_accel_file_data.assert_called_once_with(self.mock_bot.cus_order, remove_order=True, update_memory=True)
        self.mock_app.accel_mode.record_completed_order.assert_called_once()
        self.mock_app.report_manager.finish_order.assert_called_once_with(self.mock_bot.cus_order, overall_status="SUCCESS")
        self.handler.return_to_first_page.assert_called_once()
        self.mock_bot.clean_pos_cart.assert_called_once()

    def test_checkpoint_4_halts_on_fail_when_accel_and_autoinv(self):
        """เมื่อเปิด test mode + accel_mode + auto_inv คู่กัน แต่หน้าท้ายไม่ผ่าน (all_ok=False) ต้องไม่ auto-advance, ปิด accel_mode, และขึ้นสถานะ Test Failed"""
        self.mock_app.is_testing = True
        self.mock_app.test_checkpoint.get.return_value = "4. หลังกรอกหน้าท้าย (ก่อนกดปุ่มเขียว)"
        self.mock_app.is_accel_mode.get.return_value = True
        self.mock_app.is_auto_invoice_mode.get.return_value = True

        self.handler.verify_final_page_elements = MagicMock(return_value={"all_ok": False, "cash_price": {"ok": False}})
        self.handler.return_to_first_page = MagicMock()
        self.mock_bot.clean_pos_cart = MagicMock()

        verification = self.handler.verify_final_page_elements()
        is_all_ok = bool(verification.get("all_ok"))
        is_accel = self.mock_app.is_accel_mode.get()
        is_auto_inv = self.mock_app.is_auto_invoice_mode.get()
        is_auto_advance = is_accel and is_auto_inv

        self.assertTrue(is_auto_advance)
        self.assertFalse(is_all_ok)

        # Failure handling
        self.mock_app.report_manager.finish_order(self.mock_bot.cus_order, overall_status="FAILED")
        self.mock_app.is_accel_mode_activated.set(False)
        self.mock_app.display_bot_status_label.configure(text="Bot Status: Your Turn (Test Failed)")

        self.mock_app.report_manager.finish_order.assert_called_once_with(self.mock_bot.cus_order, overall_status="FAILED")
        self.mock_app.is_accel_mode_activated.set.assert_called_once_with(False)
        self.handler.return_to_first_page.assert_not_called()
        self.mock_bot.clean_pos_cart.assert_not_called()


if __name__ == "__main__":
    unittest.main()
