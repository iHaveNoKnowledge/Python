import datetime
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import openpyxl
import pandas as pd
from functions.pos.pricing_engine import (
    POSPricingReconciler,
    extract_coupon_date_range,
    format_cp_excel,
    get_coupon_start_and_end_dates,
    is_coupon_valid_for_order,
    parse_smart_date,
)


class TestCouponDateSuggestion(unittest.TestCase):
    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_app = MagicMock()
        self.mock_driver = MagicMock()
        self.mock_bot.app = self.mock_app
        self.mock_bot.driver = self.mock_driver

    def test_extract_coupon_date_range(self):
        """ทดสอบการดึงช่วงวันที่จากข้อความ HTML ของคูปอง"""
        text1 = '(01/09/2026 - 30/09/2026)'
        s1, e1 = extract_coupon_date_range(text1)
        self.assertEqual(s1, datetime.date(2026, 9, 1))
        self.assertEqual(e1, datetime.date(2026, 9, 30))

        text2 = 'Promotion Epson Flashsale (04/09/2026 - 08/10/2026)'
        s2, e2 = extract_coupon_date_range(text2)
        self.assertEqual(s2, datetime.date(2026, 9, 4))
        self.assertEqual(e2, datetime.date(2026, 10, 8))

        s_none, e_none = extract_coupon_date_range("ไม่มีวันที่ระบุ")
        self.assertIsNone(s_none)
        self.assertIsNone(e_none)

    def test_get_coupon_start_and_end_dates(self):
        """ทดสอบการดึง start_date และ end_date พร้อม fallback จากรหัสคูปอง"""
        # กรณีระบุวันที่ชัดเจนใน dict
        c1 = {"code": "DC2608280010", "start_date": datetime.date(2026, 9, 1), "end_date": datetime.date(2026, 9, 30)}
        s1, e1 = get_coupon_start_and_end_dates(c1)
        self.assertEqual(s1, datetime.date(2026, 9, 1))
        self.assertEqual(e1, datetime.date(2026, 9, 30))

        # กรณีดึงจาก desc
        c2 = {"code": "DC2608310030", "desc": "DC Promotion Epson (01/09/2026 - 30/09/2026)"}
        s2, e2 = get_coupon_start_and_end_dates(c2)
        self.assertEqual(s2, datetime.date(2026, 9, 1))
        self.assertEqual(e2, datetime.date(2026, 9, 30))

        # กรณี fallback จาก code
        c3 = {"code": "CP2609040005", "desc": "No date"}
        s3, e3 = get_coupon_start_and_end_dates(c3)
        self.assertEqual(s3, datetime.date(2026, 9, 4))
        self.assertIsNone(e3)

    def test_coupon_valid_for_order(self):
        """ทดสอบการตรวจสอบว่าคูปองครอบคลุมวันที่สั่งซื้อหรือไม่"""
        c = {
            "code": "CP1",
            "start_date": datetime.date(2026, 9, 4),
            "end_date": datetime.date(2026, 10, 8),
            "is_expired": False
        }
        # วันที่สั่งซื้อก่อนวันเริ่ม
        self.assertFalse(is_coupon_valid_for_order(c, "01/09/2026"))
        # วันที่สั่งซื้ออยู่ในช่วง
        self.assertTrue(is_coupon_valid_for_order(c, "14/09/2026"))
        # วันที่สั่งซื้อหลังวันสิ้นสุด
        self.assertFalse(is_coupon_valid_for_order(c, "09/10/2026"))

        # คูปองหมดอายุ
        c_exp = dict(c, is_expired=True)
        self.assertFalse(is_coupon_valid_for_order(c_exp, "14/09/2026"))

    def test_find_suggested_cp_ranking_newest_start_date(self):
        """
        ทดสอบการเลือกคูปองที่มีวันเริ่มใหม่สุด (Newest start_date)
        ตามข้อมูลตัวอย่าง HTML ของผู้ใช้:
        DC2608280010: 23.- (01/09/2026 - 30/09/2026)
        DC2608310030: 17.- (01/09/2026 - 30/09/2026)
        CP2609040005: 21.- (04/09/2026 - 08/10/2026)
        DC2609070013: 17.- (08/09/2026 - 30/09/2026)
        DC2609140005: 19.- (14/09/2026 - 09/10/2026)
        """
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "DC2608310030",
                "discount": 17.0,
                "start_date": datetime.date(2026, 9, 1),
                "end_date": datetime.date(2026, 9, 30),
                "desc": "(01/09/2026 - 30/09/2026)",
                "is_expired": False
            },
            {
                "code": "DC2609070013",
                "discount": 17.0,
                "start_date": datetime.date(2026, 9, 8),
                "end_date": datetime.date(2026, 9, 30),
                "desc": "(08/09/2026 - 30/09/2026)",
                "is_expired": False
            }
        ]

        # ออเดอร์วันที่ 14/09/2026 ต้องการส่วนลด 17 บาท
        # ทั้งสองคูปองครอบคลุมวันที่ 14/09 แต่ DC2609070013 เริ่มวันที่ 08/09 (ใหม่กว่า 01/09) -> ต้องเลือก DC2609070013
        sugg = reconciler.find_suggested_cp_for_discount(17.0, order_date="14/09/2026")
        self.assertIsNotNone(sugg)
        self.assertEqual(sugg["suggested_code"], "DC2609070013")
        self.assertEqual(sugg["suggested_start_date"], datetime.date(2026, 9, 8))
        self.assertEqual(sugg["suggested_end_date"], datetime.date(2026, 9, 30))

        # ออเดอร์วันที่ 05/09/2026 ต้องการส่วนลด 17 บาท
        # DC2609070013 ยังไม่เริ่ม (เริ่ม 08/09) จึงต้องเลือก DC2608310030 (เริ่ม 01/09)
        sugg_early = reconciler.find_suggested_cp_for_discount(17.0, order_date="05/09/2026")
        self.assertIsNotNone(sugg_early)
        self.assertEqual(sugg_early["suggested_code"], "DC2608310030")
        self.assertEqual(sugg_early["suggested_start_date"], datetime.date(2026, 9, 1))

    def test_find_suggested_cp_tie_breaking_earliest_end_date(self):
        """ทดสอบกรณี start_date เท่ากัน ให้เลือกตัวที่หมดอายุไวกว่า (Earliest end_date)"""
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "CP_A",
                "discount": 50.0,
                "start_date": datetime.date(2026, 9, 1),
                "end_date": datetime.date(2026, 9, 30),
                "desc": "(01/09/2026 - 30/09/2026)",
                "is_expired": False
            },
            {
                "code": "CP_B",
                "discount": 50.0,
                "start_date": datetime.date(2026, 9, 1),
                "end_date": datetime.date(2026, 9, 15),
                "desc": "(01/09/2026 - 15/09/2026)",
                "is_expired": False
            }
        ]

        sugg = reconciler.find_suggested_cp_for_discount(50.0, order_date="10/09/2026")
        self.assertIsNotNone(sugg)
        # วันเริ่มเท่ากัน (01/09) แต่ CP_B สิ้นสุดไวกว่า (15/09 < 30/09) -> เลือก CP_B
        self.assertEqual(sugg["suggested_code"], "CP_B")

    def test_combo_coupon_suggestion_dates(self):
        """ทดสอบการคำนวณช่วงวันที่ร่วมของคู่ผสม (Combo): max(start_dates), min(end_dates)"""
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "CP_PART1",
                "discount": 20.0,
                "start_date": datetime.date(2026, 9, 1),
                "end_date": datetime.date(2026, 9, 30),
                "is_expired": False
            },
            {
                "code": "CP_PART2",
                "discount": 30.0,
                "start_date": datetime.date(2026, 9, 5),
                "end_date": datetime.date(2026, 9, 20),
                "is_expired": False
            }
        ]

        sugg = reconciler.find_suggested_cp_for_discount(50.0, order_date="10/09/2026")
        self.assertIsNotNone(sugg)
        self.assertIn("CP_PART1", sugg["suggested_code"])
        self.assertIn("CP_PART2", sugg["suggested_code"])
        # ช่วงวันที่ร่วม: เริ่ม 2026-09-05, สิ้นสุด 2026-09-20
        self.assertEqual(sugg["suggested_start_date"], datetime.date(2026, 9, 5))
        self.assertEqual(sugg["suggested_end_date"], datetime.date(2026, 9, 20))

    def test_format_cp_excel(self):
        """ทดสอบฟังก์ชัน format_cp_excel: freeze row 1, auto-filter, column A width 32.0 (2.5 นิ้ว)"""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            df = pd.DataFrame({
                "sku": ["SKU01", "SKU02"],
                "price": [100.0, 200.0],
                "suggested_cp": ["CP1", "CP2"],
                "usage_start_date": ["01/09/2026", "04/09/2026"],
                "usage_end_date": ["30/09/2026", "08/10/2026"]
            })
            df.to_excel(tmp_path, index=False)

            # จัดรูปแบบ
            format_cp_excel(tmp_path)

            wb = openpyxl.load_workbook(tmp_path)
            ws = wb.active

            # 1. Freeze row 1 (A2)
            self.assertEqual(ws.freeze_panes, "A2")

            # 2. Auto Filter
            self.assertIsNotNone(ws.auto_filter.ref)
            self.assertTrue(ws.auto_filter.ref.startswith("A1:"))

            # 3. Column 1 (A) width = 32.0 (~2.5")
            self.assertEqual(ws.column_dimensions['A'].width, 32.0)

            wb.close()
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_add_missing_cp_to_excel_writes_dates_and_formats(self):
        """ทดสอบการบันทึก suggested_cp พร้อม usage_start_date และ usage_end_date และจัดรูปแบบไฟล์"""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # สร้างไฟล์เริ่มต้น
            df_init = pd.DataFrame({
                "sku": ["SKU-EXISTING"],
                "sale_price": [500.0],
                "suggested_cp": [""],
                "usage_start_date": [""],
                "usage_end_date": [""]
            })
            df_init.to_excel(tmp_path, index=False)

            reconciler = POSPricingReconciler(self.mock_bot)
            self.mock_app.cp_table_location = tmp_path
            self.mock_app.cp_df = df_init.copy()

            reconciler.add_missing_cp_to_excel(
                sku_key="SKU-NEW-01",
                expected_price=350.0,
                suggested_cp="DC2609070013",
                start_date=datetime.date(2026, 9, 8),
                end_date=datetime.date(2026, 9, 30)
            )

            # อ่านไฟล์ Excel ตรวจสอบข้อมูล
            df_saved = pd.read_excel(tmp_path)
            row_new = df_saved[df_saved["sku"] == "SKU-NEW-01"]
            self.assertEqual(len(row_new), 1)
            self.assertEqual(row_new["suggested_cp"].iloc[0], "DC2609070013")
            self.assertEqual(row_new["usage_start_date"].iloc[0], "08/09/2026")
            self.assertEqual(row_new["usage_end_date"].iloc[0], "30/09/2026")

            # ตรวจสอบรูปแบบ format_cp_excel
            wb = openpyxl.load_workbook(tmp_path)
            ws = wb.active
            self.assertEqual(ws.freeze_panes, "A2")
            self.assertTrue(ws.auto_filter.ref.startswith("A1:"))
            self.assertEqual(ws.column_dimensions['A'].width, 32.0)
            wb.close()

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
