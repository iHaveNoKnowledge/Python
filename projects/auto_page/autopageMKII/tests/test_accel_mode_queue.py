import os
import sys
import unittest
from unittest.mock import MagicMock

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from functions.accel_mode import AccelMode


class TestAccelModeQueue(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_app.is_accel_mode_activated = MagicMock()
        self.mock_app.is_accel_mode_activated.get.return_value = True

        self.accel = AccelMode(self.mock_app)
        self.accel.reload_accel_file_if_modified = MagicMock()

    def test_sequential_order_processing_with_deletion(self):
        """
        ทดสอบว่าเมื่อออเดอร์ก่อนหน้าสำเร็จและถูกลบออกจาก Excel/State
        ออเดอร์ถัดไปจะต้องถูกหยิบตามลำดับเป๊ะๆ (1 -> 2 -> 3 -> 4 -> 5)
        โดยไม่ข้ามออเดอร์ที่ 2 (แก้ปัญหา Index Shifting Bug)
        """
        initial_orders = [
            '260908G1079QH8',
            '260908GDUJVVGH',
            '260909H1WVFVHG',
            '260909H1XJDJM6',
            '260909H1XP7H2Q'
        ]
        self.accel.accel_orders_list = list(initial_orders)

        fed_orders = []

        def mock_search_order(order, callback):
            fed_orders.append(order)
            # จำลองการตัดออเดอร์ออกจาก State/Excel เมื่อทำงานเสร็จ
            if order in self.accel.accel_orders_list:
                self.accel.accel_orders_list.remove(order)
            # เรียก callback เพื่อเริ่มออเดอร์ถัดไป
            if callback:
                callback()

        self.mock_app.search_order.side_effect = mock_search_order

        # เริ่มค้นหาออเดอร์ในโหมด Accel
        self.accel.accel_search()

        # ตรวจสอบว่าทุกออเดอร์ถูกส่งเข้า search_order เรียงตามลำดับ 100%
        self.assertEqual(fed_orders, initial_orders, "ออเดอร์ต้องถูกส่งเข้าทำงานเรียงลำดับครบทุกตัวโดยไม่ข้าม")
        self.assertEqual(fed_orders[1], '260908GDUJVVGH', "ออเดอร์ลำดับที่ 2 ต้องไม่ถูกข้าม")

    def test_failed_order_does_not_infinite_loop(self):
        """
        ทดสอบว่ากรณีออเดอร์เกิดข้อผิดพลาด (Failed/ข้าม) และไม่ได้ถูกลบออกจาก Sheet1
        ระบบ Processed Queue Tracker จะไม่วนซ้ำออเดอร์เดิม แต่จะข้ามไปหยิบออเดอร์ถัดไป
        """
        initial_orders = ['ORDER_FAIL_1', 'ORDER_OK_2', 'ORDER_OK_3']
        self.accel.accel_orders_list = list(initial_orders)

        fed_orders = []

        def mock_search_order(order, callback):
            fed_orders.append(order)
            # จำลอง: ถ้าเป็น ORDER_FAIL_1 จะไม่ถูกลบออกจาก accel_orders_list
            if order != 'ORDER_FAIL_1' and order in self.accel.accel_orders_list:
                self.accel.accel_orders_list.remove(order)
            if callback:
                callback()

        self.mock_app.search_order.side_effect = mock_search_order

        self.accel.accel_search()

        # ORDER_FAIL_1 ต้องถูกพยายามเพียงครั้งเดียว และระบบต้องทำ ORDER_OK_2 และ ORDER_OK_3 ต่อจนครบ
        self.assertEqual(fed_orders, ['ORDER_FAIL_1', 'ORDER_OK_2', 'ORDER_OK_3'])
        # ใน State ยังคงเหลือ ORDER_FAIL_1 อยู่ (ไม่ถูกลบ)
        self.assertIn('ORDER_FAIL_1', self.accel.accel_orders_list)

    def test_accel_mode_clean_termination(self):
        """
        ทดสอบว่าเมื่อรันครบทุกออเดอร์แล้ว ระบบจะปิดโหมด Accel Mode อย่างถูกต้อง
        """
        self.accel.accel_orders_list = ['ORDER_A', 'ORDER_B']

        def mock_search_order(order, callback):
            if order in self.accel.accel_orders_list:
                self.accel.accel_orders_list.remove(order)
            if callback:
                callback()

        self.mock_app.search_order.side_effect = mock_search_order

        self.accel.accel_search()

        # is_accel_mode_activated.set(False) ต้องถูกเรียกเพื่อจบโหมด
        self.mock_app.is_accel_mode_activated.set.assert_called_with(False)


if __name__ == "__main__":
    unittest.main()
