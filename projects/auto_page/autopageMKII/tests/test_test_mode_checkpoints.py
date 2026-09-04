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


if __name__ == "__main__":
    unittest.main()
