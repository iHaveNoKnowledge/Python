import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from openpyxl import load_workbook
from functions.accel_mode import AccelMode


class TestAccelUnifiedProcessedLogs(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.test_excel = os.path.join(self.tmp_dir.name, "test_accel_unified.xlsx")

        # Create basic Excel file with Sheet1
        df_sheet1 = pd.DataFrame({"orders": ["ORD101", "ORD102"], "SP2-001": ["SN001", "SN002"]})
        with pd.ExcelWriter(self.test_excel, engine="openpyxl") as writer:
            df_sheet1.to_excel(writer, sheet_name="Sheet1", index=False)

        class DummyApp:
            def __init__(self):
                self.tracking_from_data = ["TH11223344"]
                self.filter_data = None
                self.data_frame = None

        self.app = DummyApp()
        self.accel = AccelMode(self.app)
        self.accel.accel_file_dir = self.test_excel

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_record_failed_order_creates_processed_logs(self):
        """ทดสอบว่า record_failed_order บันทึกลง Processed_Logs ด้วย 9 คอลัมน์มาตรฐาน"""
        self.accel.record_failed_order("ORD101", "จำนวน SN ไม่พอสำหรับ SKU SP2-001")

        with pd.ExcelFile(self.test_excel) as xl:
            self.assertIn("Processed_Logs", xl.sheet_names)
            df_proc = xl.parse("Processed_Logs")

        expected_cols = ['timestamp', 'tracking', 'orders', 'status', 'bill_no', 'price', 'sn', 'error_category', 'remark']
        self.assertEqual(list(df_proc.columns), expected_cols)
        self.assertEqual(len(df_proc), 1)

        row = df_proc.iloc[0]
        self.assertEqual(row['orders'], 'ORD101')
        self.assertEqual(row['status'], 'Failed')
        self.assertEqual(row['tracking'], 'TH11223344')
        self.assertEqual(row['error_category'], 'SN_SHORTAGE')
        self.assertIn('จำนวน SN ไม่พอ', str(row['remark']))
        self.assertEqual(str(row['bill_no']).strip().replace('nan', ''), '')

    def test_record_completed_order_creates_processed_logs(self):
        """ทดสอบว่า record_completed_order บันทึกลง Processed_Logs พร้อม bill_no, sn, price"""
        self.accel.record_completed_order(
            order="ORD102",
            tracking="TH998877",
            bill_no="B0183-000999",
            status="Completed",
            price="1590",
            serials=[{"sku": "SP2-001", "sn": "SN001"}],
            pricing_detail="[ราคาตรง 1590]"
        )

        with pd.ExcelFile(self.test_excel) as xl:
            self.assertIn("Processed_Logs", xl.sheet_names)
            df_proc = xl.parse("Processed_Logs")

        self.assertEqual(len(df_proc), 1)
        row = df_proc.iloc[0]
        self.assertEqual(row['orders'], 'ORD102')
        self.assertEqual(row['status'], 'Completed')
        self.assertEqual(row['tracking'], 'TH998877')
        self.assertEqual(row['bill_no'], 'B0183-000999')
        self.assertEqual(str(row['price']), '1590')
        self.assertEqual(row['sn'], 'SN001')
        self.assertEqual(row['remark'], '[ราคาตรง 1590]')
        self.assertEqual(str(row['error_category']).strip().replace('nan', ''), '')

    def test_retry_flow_updates_failed_to_completed_and_cleans_legacy_failed(self):
        """ทดสอบ Retry Flow:
        1. ออเดอร์ fail ครั้งแรก -> อยู่ใน Processed_Logs (Failed) และ Failed_Orders
        2. รัน retry จนสำเร็จ -> Processed_Logs อัปเดตแถวเดิมเป็น Completed และถูกลบออกจาก Failed_Orders
        3. ไม่มีเลขออเดอร์ซ้ำใน Processed_Logs
        """
        # Step 1: Failed attempt
        self.accel.record_failed_order("ORD_RETRY_1", "ขอวิธีปรับราคาครับ diff: -100")

        with pd.ExcelFile(self.test_excel) as xl:
            df_proc = xl.parse("Processed_Logs")
            df_failed = xl.parse("Failed_Orders")

        self.assertEqual(len(df_proc), 1)
        self.assertEqual(df_proc.iloc[0]['status'], 'Failed')
        self.assertEqual(len(df_failed), 1)
        self.assertEqual(df_failed.iloc[0]['orders'], 'ORD_RETRY_1')

        # Step 2: Successful Retry
        self.accel.record_completed_order(
            order="ORD_RETRY_1",
            tracking="TH_RETRY_TRACK",
            bill_no="B0183-RETRY-01",
            status="Completed",
            price="2000",
            serials="SN_RETRY_888",
            pricing_detail="[ปรับราคาสำเร็จ]"
        )

        with pd.ExcelFile(self.test_excel) as xl:
            df_proc = xl.parse("Processed_Logs")
            df_failed = xl.parse("Failed_Orders")
            df_comp = xl.parse("Completed_Orders")

        # Processed_Logs ต้องมีเพียง 1 แถว และเปลี่ยนสถานะเป็น Completed
        self.assertEqual(len(df_proc), 1)
        row = df_proc.iloc[0]
        self.assertEqual(row['orders'], 'ORD_RETRY_1')
        self.assertEqual(row['status'], 'Completed')
        self.assertEqual(row['bill_no'], 'B0183-RETRY-01')
        self.assertEqual(row['sn'], 'SN_RETRY_888')

        # Failed_Orders ต้องถูกเคลียร์ออก ไม่เหลือออเดอร์นี้
        self.assertEqual(len(df_failed), 0)

        # Completed_Orders ต้องมีออเดอร์นี้
        self.assertEqual(len(df_comp), 1)
        self.assertEqual(df_comp.iloc[0]['orders'], 'ORD_RETRY_1')


if __name__ == '__main__':
    unittest.main()
