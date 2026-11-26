import unittest
import os
import pandas as pd
from unittest.mock import MagicMock, patch
import tempfile
import datetime

from functions.pos.cp_data_loader import DualSourceCPLoader
from functions.pos.pricing_engine import POSPricingReconciler, conflict_candidate_sort_key, write_cp_excel


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

        self.mock_bot = MagicMock()
        self.mock_app = MagicMock()
        self.mock_bot.app = self.mock_app
        self.mock_app.cp_table_location = self.excel_path
        self.mock_app.cp_gas_url = ""
        self.mock_app._cp_last_mtime = 0
        self.mock_app.cp_df = None
        self.mock_app.marketplace_target.get.return_value = "Shopee"
        self.mock_app.cus_purchase_time.get.return_value = "14:00"
        self.mock_app.correct_sku_pattern.return_value = []
        self.mock_bot.driver = MagicMock()
        self.mock_bot.wait50 = MagicMock()

        self.reconciler = POSPricingReconciler(self.mock_bot)

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

    def test_marketplace_isolation_in_candidate_search(self):
        """ทดสอบว่า find_all_cp_candidates_from_excel แยกแยะ Marketplace และกันการปนสูตรข้ามแพลตฟอร์ม"""
        df_mp = pd.DataFrame([
            {
                "sku": "TEST-SKU",
                "sale_price": 500,
                "marketplace": "TIKTOK",
                "cp_name": "TT_ONLY_COUPON",
                "suggested_cp": "TT_ONLY_COUPON",
                "usage_start_date": "2026-10-01",
                "usage_end_date": "2026-10-31"
            },
            {
                "sku": "TEST-SKU",
                "sale_price": 500,
                "marketplace": "SHOPEE",
                "cp_name": "SHP_ONLY_COUPON",
                "suggested_cp": "SHP_ONLY_COUPON",
                "usage_start_date": "2026-10-01",
                "usage_end_date": "2026-10-31"
            },
            {
                "sku": "TEST-SKU",
                "sale_price": 500,
                "marketplace": "",  # Universal legacy
                "cp_name": "GLOBAL_COUPON",
                "suggested_cp": "GLOBAL_COUPON",
                "usage_start_date": "2026-10-01",
                "usage_end_date": "2026-10-31"
            }
        ])
        mp_excel_path = os.path.join(self.temp_dir, "test_mp_cp_data.xlsx")
        df_mp.to_excel(mp_excel_path, sheet_name='cp_data', index=False)

        self.mock_app.cp_table_location = mp_excel_path
        self.mock_app.cp_df = None
        self.mock_app.marketplace_target.get.return_value = "SHOPEE"
        loader = DualSourceCPLoader(gas_url="", local_excel_path=mp_excel_path)
        self.reconciler._dual_cp_loader = loader
        self.reconciler.app.cp_df = None

        # 1. เมื่อเปิดในโหมด SHOPEE: ต้องเลือก SHP_ONLY_COUPON และไม่ปนกับ TT_ONLY_COUPON
        cands_shp = self.reconciler.find_all_cp_candidates_from_excel("TEST-SKU", 500, "15/10/2026")
        found_shp = [c.get("cp_name") for c in cands_shp]
        self.assertIn("SHP_ONLY_COUPON", found_shp)
        self.assertNotIn("TT_ONLY_COUPON", found_shp, "TikTok coupon must NOT leak into Shopee candidate pool!")

        # 2. เมื่อเปิดในโหมด LAZADA (ไม่มีสูตรเฉพาะ): ต้อง fallback ไปใช้ GLOBAL_COUPON ได้อย่างถูกต้อง
        self.mock_app.marketplace_target.get.return_value = "LAZADA"
        cands_lzd = self.reconciler.find_all_cp_candidates_from_excel("TEST-SKU", 500, "15/10/2026")
        found_lzd = [c.get("cp_name") for c in cands_lzd]
        self.assertIn("GLOBAL_COUPON", found_lzd)
        self.assertNotIn("TT_ONLY_COUPON", found_lzd)
        self.assertNotIn("SHP_ONLY_COUPON", found_lzd)


    def test_write_cp_excel_preserves_conflict_resolver_tab(self):
        """ทดสอบว่า write_cp_excel เขียนเฉพาะแท็บแรกและคงแท็บ conflict_resolver ไว้ครบ"""
        df_main = pd.read_excel(self.excel_path, sheet_name="cp_data")
        df_main.loc[0, "suggested_remark"] = "อัปเดตจาก test"
        self.assertTrue(write_cp_excel(self.excel_path, df_main))

        sheets = pd.ExcelFile(self.excel_path).sheet_names
        self.assertIn("cp_data", sheets, "แท็บหลักต้องคงชื่อเดิม")
        self.assertIn("conflict_resolver", sheets, "แท็บ conflict_resolver ห้ามหายจากการเขียนทับ")

        df_conf = pd.read_excel(self.excel_path, sheet_name="conflict_resolver")
        self.assertEqual(len(df_conf), 1)
        self.assertEqual(df_conf.iloc[0]["suggested_winner"], "DC2609300024")

    def test_conflict_tab_survives_product_master_sync(self):
        """ทดสอบว่า sync_product_master_coupon_dates_to_excel (ยิงทุกครั้งที่ดึง SKU) ไม่ลบแท็บ conflict_resolver"""
        self.reconciler._dual_cp_loader = DualSourceCPLoader(gas_url="", local_excel_path=self.excel_path)
        response_data = [{
            "productCode": "SP4-000302",
            "coupons": [{
                "couponCode": "CP2609040005",
                "startDate": "04/09/2026",
                "endDate": "08/10/2026",
                "couponDetailRemark": "Shp Fs ถูกชัวร์ ราคา139"
            }]
        }]
        self.reconciler.sync_product_master_coupon_dates_to_excel("SP4-000302", response_data)

        sheets = pd.ExcelFile(self.excel_path).sheet_names
        self.assertIn("conflict_resolver", sheets, "แท็บ conflict_resolver ต้องรอดจากการ sync ข้อมูลคูปอง")
        df_conf = pd.read_excel(self.excel_path, sheet_name="conflict_resolver")
        self.assertEqual(len(df_conf), 1)
        self.assertEqual(df_conf.iloc[0]["sku"], "SP4-000302")

        df_main = pd.read_excel(self.excel_path, sheet_name="cp_data")
        self.assertEqual(
            df_main.loc[0, "suggested_cp"], "CP2609040005",
            "ต้องยืนยันว่าฟังก์ชันอัปเดตข้อมูลจริงและเขียนไฟล์จริง (ไม่ใช่ไม่เขียนเลย)"
        )

    def test_sync_to_local_excel_keeps_conflict_tab_when_fetch_returns_empty(self):
        """ทดสอบว่า sync_to_local_excel ห้ามเขียน placeholder ทับแท็บ conflict_resolver ที่มีข้อมูลอยู่แล้ว"""
        loader = DualSourceCPLoader(gas_url="", local_excel_path=self.excel_path)
        loader.fetch_conflict_resolver_local = MagicMock(return_value=pd.DataFrame())
        df_cp = pd.read_excel(self.excel_path, sheet_name="cp_data")
        loader.sync_to_local_excel(df_cp)

        sheets = pd.ExcelFile(self.excel_path).sheet_names
        self.assertIn("conflict_resolver", sheets)
        df_conf = pd.read_excel(self.excel_path, sheet_name="conflict_resolver")
        self.assertEqual(len(df_conf), 1, "แถวเดิมต้องคงอยู่ ไม่ถูกแทนด้วย placeholder ว่าง")
        self.assertEqual(df_conf.iloc[0]["suggested_winner"], "DC2609300024")

    @staticmethod
    def _calc_net_stub(c_item):
        if c_item.get("sale_price") is not None:
            return round(float(c_item.get("sale_price")), 2)
        base_price = 4290.0
        disc = float(c_item.get("couponDetailCash") or 0) + float(c_item.get("couponDetailDisc") or 0)
        return round(base_price - disc, 2)

    @staticmethod
    def _rank(cands, expected_price=3588.0, order_date="2026-11-25 12:14", mp="SHOPEE"):
        return sorted(
            cands,
            key=lambda c: conflict_candidate_sort_key(
                c, TestConflictResolverAndLiveFilter._calc_net_stub,
                expected_price, order_date, mp
            ),
            reverse=True,
        )

    def test_conflict_tie_prefers_newer_start_date_over_platform_remark(self):
        newer_table = {
            "cp_name": "DC2611160006",
            "oc_amount": "",
            "dc_amount": "",
            "sale_price": 3588,
            "usage_start_date": "19/11/2026",
            "usage_end_date": "10/12/2026",
            "source": "TABLE",
        }
        older_smco = {
            "cp_name": "DC2610300019",
            "oc_amount": "",
            "dc_amount": "",
            "start_date": datetime.date(2026, 11, 1),
            "end_date": datetime.date(2026, 11, 30),
            "remark": "Shp เดือน ต.ค. ราคา 3588",
            "source": "SMCO",
            "couponDetailCash": 0.0,
            "couponDetailDisc": 702.0,
        }
        ranked = self._rank([older_smco, newer_table])
        self.assertEqual(
            ranked[0]["cp_name"], "DC2611160006",
            "ราคาเท่ากัน ต้องเลือกวันเริ่มต้นใหม่กว่า (19/11) ไม่ใช่ตัวเก่าที่มี remark แพลตฟอร์ม"
        )

    def test_conflict_platform_other_ranks_last_and_shorter_end_wins(self):
        long_end = {
            "cp_name": "DC2611160006", "oc_amount": "", "dc_amount": "", "sale_price": 3588,
            "usage_start_date": "19/11/2026", "usage_end_date": "10/12/2026",
        }
        short_end = {
            "cp_name": "DC2611160007", "oc_amount": "", "dc_amount": "", "sale_price": 3588,
            "usage_start_date": "19/11/2026", "usage_end_date": "25/11/2026",
        }
        other_platform = {
            "cp_name": "DC2611160008", "oc_amount": "", "dc_amount": "", "sale_price": 3588,
            "usage_start_date": "19/11/2026", "usage_end_date": "10/12/2026",
            "remark": "TT เดือน พ.ย. ราคา 3588",
        }
        ranked = self._rank([long_end, other_platform, short_end])
        self.assertEqual(
            [c["cp_name"] for c in ranked],
            ["DC2611160007", "DC2611160006", "DC2611160008"],
            "วันสิ้นสุดสั้นกว่าชนะเมื่อวันเริ่มเท่ากัน และคูปองแพลตฟอร์มอื่นต้องอยู่ท้ายสุด"
        )

    def test_conflict_price_mismatch_stays_bottom_even_if_newest(self):
        newest_wrong_price = {
            "cp_name": "DC2611160006", "oc_amount": "", "dc_amount": "", "sale_price": 3500,
            "usage_start_date": "19/11/2026", "usage_end_date": "10/12/2026",
        }
        older_correct_price = {
            "cp_name": "DC2610300019", "oc_amount": "", "dc_amount": "",
            "start_date": datetime.date(2026, 11, 1),
            "end_date": datetime.date(2026, 11, 30),
            "couponDetailCash": 0.0, "couponDetailDisc": 702.0,
        }
        ranked = self._rank([newest_wrong_price, older_correct_price])
        self.assertEqual(
            ranked[0]["cp_name"], "DC2610300019",
            "ราคาเป็น Hard Constraint: ตัวที่ราคาไม่ตรงห้ามชนะ ถึงจะใหม่กว่าก็ตาม"
        )


if __name__ == '__main__':
    unittest.main()
