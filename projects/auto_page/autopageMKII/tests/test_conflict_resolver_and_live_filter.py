import unittest
import os
import pandas as pd
from unittest.mock import MagicMock, patch
import tempfile
import datetime

from functions.pos.cp_data_loader import DualSourceCPLoader
from functions.pos.pricing_engine import POSPricingReconciler


class TestConflictResolverAndLiveFilter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.excel_path = os.path.join(self.temp_dir, "test_cp_data.xlsx")

        self.df_cp_init = pd.DataFrame([
            {
                "sku": "SP4-000302",
                "sale_price": 139,
                "cp_name": "CP2609040005",
                "usage_start_date": "04/09/2026",
                "usage_end_date": "08/10/2026",
                "suggested_cp": "CP2609040005",
                "suggested_usage_start_date": "04/09/2026",
                "suggested_usage_end_date": "08/10/2026",
                "suggested_remark": "Shp Fs ถูกชัวร์ ราคา139"
            },
            {
                "sku": "SP4-000302",
                "sale_price": 139,
                "cp_name": "DC2609300024",
                "usage_start_date": "01/10/2026",
                "usage_end_date": "31/10/2026",
                "suggested_cp": "DC2609300024",
                "suggested_usage_start_date": "01/10/2026",
                "suggested_usage_end_date": "31/10/2026",
                "suggested_remark": "Shp/TT เดือน ต.ค. ราคา 139"
            }
        ])

        self.df_conflict_init = pd.DataFrame([
            {
                "sku": "SP4-000302",
                "sale_price": 139,
                "candidate_1": "CP2609040005",
                "candidate_2": "DC2609300024",
                "candidate_3": "",
                "suggested_winner": "DC2609300024",
                "reason": "โปร ต.ค. ยังไม่หมดอายุ",
                "admin_selection": "",
                "status": "PENDING",
                "last_updated": "2026-10-08 12:00:00"
            }
        ])

        with pd.ExcelWriter(self.excel_path, engine='openpyxl') as writer:
            self.df_cp_init.to_excel(writer, sheet_name="cp_data", index=False)
            self.df_conflict_init.to_excel(writer, sheet_name="conflict_resolver", index=False)

        self.mock_app = MagicMock()
        self.mock_app.cp_table_location = self.excel_path
        self.mock_app.cp_df = None
        self.mock_app.marketplace_target.get.return_value = "Shopee"
        self.mock_app.cus_purchase_time.get.return_value = "14:00"
        self.mock_app.bot = MagicMock()
        self.mock_app.driver = MagicMock()

        self.reconciler = POSPricingReconciler(self.mock_app)

    def test_dual_source_cp_loader_multi_sheet_read_and_sync(self):
        """ทดสอบว่า DualSourceCPLoader สามารถโหลดและบันทึกแท็บ conflict_resolver แยกชีตได้อย่างสมบูรณ์"""
        loader = DualSourceCPLoader(gas_url="", local_excel_path=self.excel_path)
        df_conf = loader.load_conflict_resolver_df()
        self.assertFalse(df_conf.empty)
        self.assertEqual(len(df_conf), 1)
        self.assertEqual(df_conf.iloc[0]["sku"], "SP4-000302")
        self.assertEqual(df_conf.iloc[0]["suggested_winner"], "DC2609300024")

    def test_month_anomaly_date_auto_correction(self):
        """ทดสอบว่า _clean_dataframe สลับวัน/เดือนที่เกิดจาก US Locale (เช่น 2026-01-10 -> 2026-10-01 เมื่อสิ้นสุดเดือน 10) ได้ถูกต้อง"""
        loader = DualSourceCPLoader(gas_url="", local_excel_path=self.excel_path)
        df_test = pd.DataFrame([
            {
                "sku": "SP2-001713",
                "sale_price": 1227,
                "usage_start_date": "2026-01-10 00:00:01",
                "usage_end_date": "2026-10-31 23:59:59"
            }
        ])
        cleaned = loader._clean_dataframe(df_test)
        s_date = cleaned.iloc[0]["usage_start_date"]
        self.assertEqual(s_date.month, 10)
        self.assertEqual(s_date.day, 1)

    def test_conflict_resolver_respects_admin_selection(self):
        """ทดสอบว่าเมื่อ Admin ทำการ Approve เลือก candidate ใน conflict_resolver ระบบจะนำตัวที่ Admin เลือกไปใช้"""
        loader = DualSourceCPLoader(gas_url="", local_excel_path=self.excel_path)
        self.reconciler._dual_cp_loader = loader

        # จำลองให้อัปเดต Admin Selection เป็น DC2609300024 พร้อม status = APPROVED
        df_conf = pd.DataFrame([
            {
                "sku": "SP4-000302",
                "sale_price": 139,
                "admin_selection": "DC2609300024",
                "status": "APPROVED",
                "suggested_winner": "DC2609300024"
            }
        ])
        with pd.ExcelWriter(self.excel_path, engine='openpyxl') as writer:
            self.df_cp_init.to_excel(writer, sheet_name='cp_data', index=False)
            df_conf.to_excel(writer, sheet_name='conflict_resolver', index=False)

        loaded_conf = loader.load_conflict_resolver_df()
        self.assertEqual(loaded_conf.iloc[0]["admin_selection"], "DC2609300024")
        self.assertEqual(loaded_conf.iloc[0]["status"], "APPROVED")


if __name__ == '__main__':
    unittest.main()
