import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
PYTHON_WORKSPACE = os.path.abspath(os.path.join(PROJECT_ROOT, "..", ".."))

for path in [PROJECT_ROOT, PYTHON_WORKSPACE]:
    if path not in sys.path:
        sys.path.insert(0, path)

from functions.accel_mode import AccelMode
from functions.product_manager import ProductManager


class TestAccelMultiQtySN(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_app.correct_sku_pattern = lambda text: [
            s.strip() for s in str(text).replace(" ", "").split("+") if s.strip()
        ]
        self.mock_app.items = []
        self.mock_app.is_auto_invoice_mode = MagicMock()
        self.mock_app.is_auto_invoice_mode.get.return_value = False
        self.mock_app.cus_order = MagicMock()
        self.mock_app.cus_order.get.return_value = "ORDER_TEST_001"

        # Mock AccelMode without running full __init__
        self.accel = AccelMode.__new__(AccelMode)
        self.accel.main_app = self.mock_app
        self.accel.used_serials = []
        self.accel.sn_shortage = []
        self.accel.obj_data_from_accel_file = {}
        self.accel.accel_df_state = MagicMock()
        self.accel.accel_df_state.empty = True

    def test_aggregate_order_skus_single_and_combo(self):
        """ทดสอบการรวม QTY ของ SKU แบบเดี่ยวและคอมโบ (+) ให้ผลรวมตรงตามจริง"""
        # ออเดอร์ตัวอย่างตรงตามที่ user ระบุ:
        # รายการ 1: SP2-001703+SP2-001596+SP2-001597+SP2-001598 (qty=1)
        # รายการ 2: SP2-001703 (qty=1)
        items = [
            {
                'เลขอ้างอิง SKU (SKU Reference No.)': 'SP2-001703+SP2-001596+SP2-001597+SP2-001598',
                'จำนวน': 1,
                'ชื่อสินค้า': 'Combo Pack'
            },
            {
                'เลขอ้างอิง SKU (SKU Reference No.)': 'SP2-001703',
                'จำนวน': 1,
                'ชื่อสินค้า': 'Single Item'
            }
        ]

        agg = self.accel._aggregate_order_skus(items)

        self.assertEqual(agg['SP2-001703']['qty'], 2)
        self.assertEqual(agg['SP2-001596']['qty'], 1)
        self.assertEqual(agg['SP2-001597']['qty'], 1)
        self.assertEqual(agg['SP2-001598']['qty'], 1)

    def test_restore_uncommitted_serials(self):
        """ทดสอบการคืน SN ที่ verify ไปแล้วกลับเข้าคิวเมื่อรอบนั้นไม่สำเร็จ"""
        self.accel.obj_data_from_accel_file = {
            'SP2-001703': ['SN_REMAINING']
        }
        self.accel.used_serials = [
            {'sku': 'SP2-001703', 'sn': 'SN_PASSED_1'}
        ]

        self.accel.restore_uncommitted_serials()

        # ตรวจสอบว่า SN_PASSED_1 ถูกคืนกลับเข้าหัวคิว
        self.assertIn('SN_PASSED_1', self.accel.obj_data_from_accel_file['SP2-001703'])
        self.assertEqual(self.accel.obj_data_from_accel_file['SP2-001703'][0], 'SN_PASSED_1')
        # ตรวจสอบว่า used_serials ถูกล้าง
        self.assertEqual(self.accel.used_serials, [])

    def test_routing_inline_vs_modal(self):
        """ทดสอบว่า qty == 1 วิ่งเข้า _fill_single_sku_inline และ qty > 1 วิ่งเข้า _fill_multi_sku_modal"""
        self.accel.obj_data_from_accel_file = {
            'SKU_SINGLE': ['SN_S1'],
            'SKU_MULTI': ['SN_M1', 'SN_M2']
        }
        self.mock_app.items = [
            {'เลขอ้างอิง SKU (SKU Reference No.)': 'SKU_SINGLE', 'จำนวน': 1, 'ชื่อสินค้า': 'Item 1'},
            {'เลขอ้างอิง SKU (SKU Reference No.)': 'SKU_MULTI', 'จำนวน': 2, 'ชื่อสินค้า': 'Item 2'}
        ]

        self.accel._fill_single_sku_inline = MagicMock(return_value=True)
        self.accel._fill_multi_sku_modal = MagicMock(return_value=True)

        mock_driver = MagicMock()
        mock_op_thread = MagicMock()
        mock_op_thread.is_set.return_value = False

        self.accel.accel_fill_sku(mock_driver, mock_op_thread)

        self.accel._fill_single_sku_inline.assert_called_once()
        self.accel._fill_multi_sku_modal.assert_called_once()

        single_call_args = self.accel._fill_single_sku_inline.call_args[0]
        self.assertEqual(single_call_args[2], 'SKU_SINGLE')

        multi_call_args = self.accel._fill_multi_sku_modal.call_args[0]
        self.assertEqual(multi_call_args[2], 'SKU_MULTI')
        self.assertEqual(multi_call_args[4], 2)  # target_qty = 2

    def test_modal_shortage_in_manual_mode_pauses_and_does_not_raise(self):
        """ในโหมด Manual เมื่อ SN ในไฟล์ไม่พอ ต้องหยุดบอท (Your Turn) และไม่ raise error"""
        self.mock_app.is_auto_invoice_mode.get.return_value = False
        self.accel.obj_data_from_accel_file = {'SKU_MULTI': ['ONLY_ONE_SN']}

        mock_driver = MagicMock()
        mock_sku_el = MagicMock()
        mock_sku_el.text = 'SKU_MULTI'
        mock_serial_btn = MagicMock()
        mock_inp1 = MagicMock()
        mock_inp2 = MagicMock()
        mock_inp1.is_displayed.return_value = True
        mock_inp2.is_displayed.return_value = True

        def mock_find(by, val):
            if 'productNameChangeChk' in val:
                return [mock_sku_el]
            if 'btn-serial' in val:
                return [mock_serial_btn]
            if '_verifyInsertSerial' in val:
                return [MagicMock()]
            if 'element.serialNo' in val and 'ng-empty' in val:
                return [mock_inp1, mock_inp2]
            return []

        mock_driver.find_elements.side_effect = mock_find

        mock_op_thread = MagicMock()
        mock_op_thread.is_set.return_value = False

        result = self.accel._fill_multi_sku_modal(
            mock_driver, mock_op_thread, 'SKU_MULTI', 'SKU_MULTI', 2, 'Item Test', []
        )

        # ต้อง return False
        self.assertFalse(result)
        # ต้องเซ็ต stop flag ของ operation_thread
        mock_op_thread.set.assert_called_once()
        # ต้องอัปเดตสถานะ Your Turn
        self.mock_app.display_bot_status_label.configure.assert_called_with(
            text="Your Turn", text_color="#F39C12"
        )

    def test_modal_shortage_in_auto_inv_records_shortage(self):
        """ในโหมด Auto Inv เมื่อ SN ไม่พอ ต้องคืน SN ที่ผ่าน บันทึก shortage และปิด modal"""
        self.mock_app.is_auto_invoice_mode.get.return_value = True
        self.accel.obj_data_from_accel_file = {'SKU_MULTI': []}

        mock_driver = MagicMock()
        mock_sku_el = MagicMock()
        mock_sku_el.text = 'SKU_MULTI'
        mock_serial_btn = MagicMock()
        mock_inp1 = MagicMock()
        mock_inp1.is_displayed.return_value = True

        def mock_find(by, val):
            if 'productNameChangeChk' in val:
                return [mock_sku_el]
            if 'btn-serial' in val:
                return [mock_serial_btn]
            if '_verifyInsertSerial' in val:
                return [MagicMock()]
            if 'element.serialNo' in val and 'ng-empty' in val:
                return [mock_inp1]
            return []

        mock_driver.find_elements.side_effect = mock_find

        mock_op_thread = MagicMock()
        mock_op_thread.is_set.return_value = False

        self.accel._safe_close_modal = MagicMock()

        result = self.accel._fill_multi_sku_modal(
            mock_driver, mock_op_thread, 'SKU_MULTI', 'SKU_MULTI', 2, 'Item Test', []
        )

        self.assertFalse(result)
        self.accel._safe_close_modal.assert_called_once()
        self.assertEqual(len(self.accel.sn_shortage), 1)
        self.assertEqual(self.accel.sn_shortage[0]['short'], 2)

    def test_product_manager_handles_combo_with_partial_accel_items(self):
        """ทดสอบ ProductManager: คอมโบที่มีทั้ง SKU มี SN และไม่มี SN ต้องแอดเฉพาะตัวที่ไม่มี SN"""
        app = MagicMock()
        app.correct_sku_pattern = lambda s: [x.strip() for x in s.split('+')]
        app.items = [
            {'เลขอ้างอิง SKU (SKU Reference No.)': 'NORMAL_SKU+SERIAL_SKU', 'จำนวน': 1}
        ]

        # Accel has SERIAL_SKU
        app.accel_mode.obj_data_from_accel_file = {'SERIAL_SKU': ['SN1']}

        bot = MagicMock()
        driver = MagicMock()
        wait = MagicMock()
        pm = ProductManager(driver=driver, wait=wait, app=app, bot=bot)

        pm.auto_add_all_items()

        # ต้องแอดเฉพาะ NORMAL_SKU
        bot.AutoAddProduct.auto_add_product.assert_called_once_with(['NORMAL_SKU'], 1)


if __name__ == '__main__':
    unittest.main()
