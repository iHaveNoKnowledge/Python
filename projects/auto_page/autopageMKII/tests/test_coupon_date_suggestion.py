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
    extract_target_price_from_text,
    format_cp_excel,
    format_smart_datetime_str,
    get_coupon_start_and_end_dates,
    is_coupon_valid_for_order,
    parse_smart_date,
    parse_smart_datetime,
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

        # ทดสอบรูปแบบปี 2 หลัก และคำเชื่อม 'ถึง', 'to'
        text3 = 'Promotion 01/09/26 - 30/09/26'
        s3, e3 = extract_coupon_date_range(text3)
        self.assertEqual(s3, datetime.date(2026, 9, 1))
        self.assertEqual(e3, datetime.date(2026, 9, 30))

        text4 = '01-09-2026 to 30-09-2026'
        s4, e4 = extract_coupon_date_range(text4)
        self.assertEqual(s4, datetime.date(2026, 9, 1))
        self.assertEqual(e4, datetime.date(2026, 9, 30))

        text5 = '01/09/2026 ถึง 30/09/2026'
        s5, e5 = extract_coupon_date_range(text5)
        self.assertEqual(s5, datetime.date(2026, 9, 1))
        self.assertEqual(e5, datetime.date(2026, 9, 30))

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

    def test_find_suggested_cp_from_remark_target_price(self):
        """
        ทดสอบการเลือกคูปองสำหรับสินค้า Multi-SKU Combo Set
        ที่ส่วนลดรายชิ้น (321.-) ไม่เท่ากับส่วนต่างราคา (1827.-)
        แต่ใน Remark ระบุราคาเป้าหมายของเซ็ตไว้ชัดเจน: 'Dynamic ก.ย. Shp ราคา 9673'
        """
        # ทดสอบการสกัดราคาเป้าหมายจากข้อความ
        self.assertEqual(extract_target_price_from_text("Dynamic ก.ย. Shp ราคา 9673"), 9673.0)
        self.assertEqual(extract_target_price_from_text("Remark: ราคา 9,673.-"), 9673.0)
        self.assertEqual(extract_target_price_from_text("ราคาเป้าหมาย: 1861"), 1861.0)
        self.assertIsNone(extract_target_price_from_text("ไม่มีราคาเป้าหมาย"))

        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "CP2609090005",
                "discount": 321.0,
                "desc": "Promotion Printer BROTHER Dynamic Shp วันที่ 09 Sep - 08 Oct 26 Addon SITS1 Broth",
                "remark": "Dynamic ก.ย. Shp ราคา 9673",
                "remark_target_price": 9673.0,
                "start_date": datetime.date(2026, 9, 9),
                "end_date": datetime.date(2026, 10, 8),
                "is_expired": False
            },
            {
                "code": "DC2608310029",
                "discount": 100.0,
                "desc": "Discount 100",
                "remark": "",
                "remark_target_price": None,
                "start_date": datetime.date(2026, 9, 1),
                "end_date": datetime.date(2026, 9, 30),
                "is_expired": False
            }
        ]

        # เรียกค้นหาคูปองโดยส่ง target_discount=1827.0 และ expected_price=9673.0
        sugg = reconciler.find_suggested_cp_for_discount(
            target_discount=1827.0,
            require_seller_voucher=False,
            order_date="15/09/2026",
            expected_price=9673.0
        )
        self.assertIsNotNone(sugg)
        self.assertEqual(sugg["suggested_code"], "CP2609090005")
        self.assertEqual(sugg["suggested_start_date"], datetime.date(2026, 9, 9))
        self.assertEqual(sugg["suggested_end_date"], datetime.date(2026, 10, 8))

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

    def test_datetime_helpers(self):
        """ทดสอบ parse_smart_datetime และ format_smart_datetime_str ในการแปลงและรักษาเวลา"""
        from functions.pos.pricing_engine import parse_smart_datetime, format_smart_datetime_str

        # มีเวลาในรูปแบบ AM/PM
        dt1 = parse_smart_datetime("Sep 17, 2026 12:00:01 AM")
        self.assertIsNotNone(dt1)
        self.assertEqual(format_smart_datetime_str(dt1), "17/09/2026 00:00:01")

        dt2 = parse_smart_datetime("Sep 30, 2026 11:59:59 PM")
        self.assertIsNotNone(dt2)
        self.assertEqual(format_smart_datetime_str(dt2), "30/09/2026 23:59:59")

        # รูปแบบวันที่ล้วน
        dt3 = parse_smart_datetime("15/09/2026")
        self.assertEqual(format_smart_datetime_str(dt3), "15/09/2026")

    def test_ranking_and_remark_suggestions(self):
        """
        ทดสอบกฎการเลือกและ Suggest วันที่ / เวลา / Remark:
        1. วันเริ่มใหม่กว่า -> เลือกตัวนั้น (CP1: 01/09 - 30/09 vs CP2: 15/09 - 30/09 -> เลือก CP2)
        2. วันเริ่มเท่ากัน -> เลือกตัวที่หมดไวกว่า (CP1: 15/09 - 22/09 vs CP2: 15/09 - 30/09 -> เลือก CP1)
        3. ดึง Remark มาด้วย
        """
        reconciler = POSPricingReconciler(self.mock_bot)

        # Case 1: CP1 (01/09) vs CP2 (15/09) -> เลือก CP2 (Newest start date)
        reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "CP1",
                "discount": 50.0,
                "start_date": datetime.date(2026, 9, 1),
                "end_date": datetime.date(2026, 9, 30),
                "remark": "Promo Early Sept",
                "is_expired": False
            },
            {
                "code": "CP2",
                "discount": 50.0,
                "start_date": datetime.date(2026, 9, 15),
                "end_date": datetime.date(2026, 9, 30),
                "remark": "Mid Month Special",
                "is_expired": False
            }
        ]
        sugg1 = reconciler.find_suggested_cp_for_discount(50.0, order_date="20/09/2026")
        self.assertIsNotNone(sugg1)
        self.assertEqual(sugg1["suggested_code"], "CP2")
        self.assertEqual(sugg1["suggested_start_date"], datetime.date(2026, 9, 15))
        self.assertEqual(sugg1["suggested_end_date"], datetime.date(2026, 9, 30))
        self.assertEqual(sugg1["suggested_remark"], "Mid Month Special")

        # Case 2: วันเริ่มเท่ากัน (15/09) -> เลือกตัวที่หมดไวกว่า (22/09 < 30/09)
        reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "CP1",
                "discount": 50.0,
                "start_date": datetime.date(2026, 9, 15),
                "end_date": datetime.date(2026, 9, 22),
                "remark": "Flash 7 Days",
                "is_expired": False
            },
            {
                "code": "CP2",
                "discount": 50.0,
                "start_date": datetime.date(2026, 9, 15),
                "end_date": datetime.date(2026, 9, 30),
                "remark": "Monthly Promo",
                "is_expired": False
            }
        ]
        sugg2 = reconciler.find_suggested_cp_for_discount(50.0, order_date="20/09/2026")
        self.assertIsNotNone(sugg2)
        self.assertEqual(sugg2["suggested_code"], "CP1")
        self.assertEqual(sugg2["suggested_start_date"], datetime.date(2026, 9, 15))
        self.assertEqual(sugg2["suggested_end_date"], datetime.date(2026, 9, 22))
        self.assertEqual(sugg2["suggested_remark"], "Flash 7 Days")

    def test_add_missing_cp_to_excel_writes_dates_and_formats(self):
        """ทดสอบการบันทึก suggested_cp, suggested_usage_start_date, suggested_usage_end_date, suggested_remark เรียงคอลัมน์ตรงกับ cp_name, usage_start_date, usage_end_date, remark"""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # สร้างไฟล์เริ่มต้น
            df_init = pd.DataFrame({
                "sku": ["SKU-EXISTING"],
                "sale_price": [500.0],
                "cp_name": ["CP_OLD"],
                "usage_start_date": ["01/09/2026"],
                "usage_end_date": ["30/09/2026"],
                "remark": ["Old Remark"],
                "suggested_cp": [""],
                "suggested_usage_start_date": [""],
                "suggested_usage_end_date": [""],
                "suggested_remark": [""]
            })
            df_init.to_excel(tmp_path, index=False)

            reconciler = POSPricingReconciler(self.mock_bot)
            self.mock_app.cp_table_location = tmp_path
            self.mock_app.cp_df = df_init.copy()

            reconciler.add_missing_cp_to_excel(
                sku_key="SKU-NEW-01",
                expected_price=350.0,
                suggested_cp="DC2609070013",
                start_date=datetime.datetime(2026, 9, 8, 0, 0, 1),
                end_date=datetime.datetime(2026, 9, 30, 23, 59, 59),
                remark="New Launch Promo"
            )

            # อ่านไฟล์ Excel ตรวจสอบข้อมูล
            df_saved = pd.read_excel(tmp_path)
            row_new = df_saved[df_saved["sku"] == "SKU-NEW-01"]
            self.assertEqual(len(row_new), 1)
            self.assertEqual(row_new["suggested_cp"].iloc[0], "DC2609070013")
            self.assertEqual(row_new["suggested_usage_start_date"].iloc[0], "08/09/2026 00:00:01")
            self.assertEqual(row_new["suggested_usage_end_date"].iloc[0], "30/09/2026 23:59:59")
            self.assertEqual(row_new["suggested_remark"].iloc[0], "New Launch Promo")
            # ตรวจสอบคอลัมน์ last_updated
            self.assertTrue(pd.notna(row_new["last_updated"].iloc[0]))
            self.assertTrue(len(str(row_new["last_updated"].iloc[0])) > 10)

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


    def test_record_and_aggregate_combo_coupons(self):
        """
        ทดสอบการบันทึก Network Response จาก getProductMasterInfoPOSV3.htm
        และการรวบรวมส่วนลดข้าม Sub-SKU ของ Combo Set (couponDetailCash + couponDetailDisc)
        พร้อมการตรวจสอบ JWT session context และ branch filtering
        """
        reconciler = POSPricingReconciler(self.mock_bot)

        # Mock JWT context: emp_id=1234, branch_id=180, store_id=208
        reconciler._session_ctx = {"emp_id": "1234", "branch_id": 180, "store_id": 208}

        # Mock Network Response data สำหรับ 2 Sub-SKU ของ Combo Set
        sku1_resp = {
            "coupons": [
                {
                    "couponId": 142599,
                    "couponCode": "DC2609160013",
                    "couponDetailCash": 140.0,
                    "couponDetailDisc": 60.0,
                    "startDate": "Sep 17, 2026 12:00:01 AM",
                    "endDate": "Sep 30, 2026 11:59:59 PM",
                    "couponDesc": "DC Combo Set Part 1",
                    "couponDetailRemark": "Dynamic Combo Promo",
                    "usedFlag": False,
                    "couponBranchs": [{"couponBranchId": 180, "couponStoreId": 208}]
                },
                {
                    "couponId": 999999,
                    "couponCode": "OTHER_BRANCH_CP",
                    "couponDetailCash": 500.0,
                    "couponDetailDisc": 0.0,
                    "startDate": "Sep 17, 2026 12:00:01 AM",
                    "endDate": "Sep 30, 2026 11:59:59 PM",
                    "usedFlag": False,
                    "couponBranchs": [{"couponBranchId": 999, "couponStoreId": 999}]
                }
            ]
        }

        sku2_resp = {
            "coupons": [
                {
                    "couponId": 142600,
                    "couponCode": "DC2609160013",
                    "couponDetailCash": 100.0,
                    "couponDetailDisc": 50.0,
                    "startDate": "Sep 17, 2026 12:00:01 AM",
                    "endDate": "Sep 30, 2026 11:59:59 PM",
                    "couponDesc": "DC Combo Set Part 2",
                    "couponDetailRemark": "Dynamic Combo Promo",
                    "usedFlag": False,
                    "couponBranchs": [{"couponBranchId": 180, "couponStoreId": 208}]
                }
            ]
        }

        # บันทึก Network Response
        reconciler.record_product_master_response("SKU-PART-A", sku1_resp)
        reconciler.record_product_master_response("SKU-PART-B", sku2_resp)

        # ตรวจสอบการ Aggregate ของ SKU-PART-A+SKU-PART-B
        agg = reconciler.get_aggregated_combo_coupons("SKU-PART-A+SKU-PART-B")
        self.assertEqual(len(agg), 1)
        self.assertEqual(agg[0]["code"], "DC2609160013")
        self.assertEqual(agg[0]["discount"], 350.0)
        self.assertEqual(agg[0]["raw_discount"], "350.00.-")
        self.assertTrue(agg[0]["is_aggregated"])

        # ตรวจสอบการ Suggest คูปองด้วยมูลค่ารวม 350 บาท
        reconciler.last_scanned_smco_coupon_details = agg
        sugg = reconciler.find_suggested_cp_for_discount(350.0, order_date="20/09/2026")
        self.assertIsNotNone(sugg)
        self.assertEqual(sugg["suggested_code"], "DC2609160013")
        self.assertEqual(sugg["suggested_remark"], "Dynamic Combo Promo")

    def test_aggregated_combo_coupons_4_part_sku_and_coupon_detail_format(self):
        """ทดสอบการผสานคูปองสำหรับสินค้าเซ็ต 4 รายการ (เช่น Canon 4 สี) พร้อมโครงสร้าง couponDetail ของ SmartPOS v3"""
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler._session_ctx = {"emp_id": "9999", "branch_id": 180, "store_id": 208, "token": "dummy"}

        sub_skus = ["SP2-001610", "SP2-001611", "SP2-001612", "SP2-001613"]
        # ส่วนลดรวม 4 ตัว = 66.50 * 4 = 266.0 บาท
        for sku in sub_skus:
            resp = [
                {
                    "productId": 1001,
                    "productCode": sku,
                    "couponDetail": [
                        {
                            "couponId": 142599,
                            "couponDetailId": 2410602,
                            "startDate": "Sep 17, 2026 12:00:01 AM",
                            "endDate": "Sep 30, 2026 11:59:59 PM",
                            "couponCode": "CP2609160013",
                            "couponDetailCash": 40.0,
                            "couponDetailDisc": 26.5,
                            "couponDesc": "Canon Pack 4 Colors Discount",
                            "couponDetailRemark": "Dynamic Sep Shp GI-790",
                            "usedFlag": False,
                            "couponBranchs": [{"couponBranchId": 180, "couponStoreId": 208}]
                        }
                    ]
                }
            ]
            reconciler.record_product_master_response(sku, resp)

        combo_sku = "SP2-001610+SP2-001611+SP2-001612+SP2-001613"
        agg = reconciler.get_aggregated_combo_coupons(combo_sku)
        self.assertEqual(len(agg), 1)
        self.assertEqual(agg[0]["code"], "CP2609160013")
        self.assertEqual(agg[0]["discount"], 266.0)
        self.assertEqual(agg[0]["start_date"], datetime.datetime(2026, 9, 17, 0, 0, 1))
        self.assertEqual(agg[0]["end_date"], datetime.datetime(2026, 9, 30, 23, 59, 59))

        reconciler.last_scanned_smco_coupon_details = agg
        sugg = reconciler.find_suggested_cp_for_discount(266.0, order_date="2026-09-29 10:18", expected_price=1234.0)
        self.assertIsNotNone(sugg)
        self.assertEqual(sugg["suggested_code"], "CP2609160013")
        self.assertEqual(format_smart_datetime_str(sugg["start_date"]), "17/09/2026 00:00:01")
        self.assertEqual(format_smart_datetime_str(sugg["end_date"]), "30/09/2026 23:59:59")
        self.assertEqual(sugg["suggested_remark"], "Dynamic Sep Shp GI-790")

    def test_canon_gi71_postman_remark_price_match(self):
        """ทดสอบการ Suggest คูปอง Canon GI-71 (CP2609220007) จาก Remark 'Shp/TT เดือน ก.ย. ราคาเซ็ทละ 1449' ตรงตาม Postman"""
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler._session_ctx = {"emp_id": "62078", "branch_id": 180, "store_id": 208, "token": "dummy"}

        # จำลอง Response จริงจาก /getProductMasterInfoPOSV3.htm ซึ่งมี key "productCouponDetail"
        # และค่า couponDetailDisc ของแต่ละ Sub-SKU มีค่าต่างกัน (68.0 vs 69.0)
        # SP2-001792: 49 + 68 = 117
        # SP2-001793: 49 + 69 = 118
        # SP2-001794: 49 + 68 = 117
        # SP2-001795: 49 + 70 = 119
        # รวมทั้ง 4 SKU = 117 + 118 + 117 + 119 = 471.0 บาท พอดีเป๊ะ
        sub_sku_discs = {
            "SP2-001792": 68.0,  # 49 + 68 = 117
            "SP2-001793": 69.0,  # 49 + 69 = 118
            "SP2-001794": 68.0,  # 49 + 68 = 117
            "SP2-001795": 70.0,  # 49 + 70 = 119 -> Total = 471.0
        }
        for sku, disc_val in sub_sku_discs.items():
            resp = [
                {
                    "productId": 1002,
                    "productCode": sku,
                    "productCouponDetail": [
                        {
                            "couponId": 142727,
                            "couponDetailId": 2417462,
                            "startDate": "Sep 23, 2026 12:00:01 AM",
                            "endDate": "Oct 9, 2026 11:59:59 PM",
                            "couponCode": "CP2609220007",
                            "couponDetailCash": 49.0,
                            "couponDetailDisc": disc_val,
                            "requirementFlag": False,
                            "couponDetailRemark": "Shp/TT เดือน ก.ย. ราคาเซ็ทละ 1449",
                            "couponDesc": "Promotion Canon Shp/Tiktok วันที่ 23 Sep - 9 Oct 2026 Addon Online SITS1,STIKTO",
                            "couponType": 10520005,
                            "usedFlag": False,
                            "couponBranchs": [
                                {"couponBranchId": 180, "couponStoreId": 208},
                                {"couponBranchId": 180, "couponStoreId": 642}
                            ]
                        }
                    ]
                }
            ]
            reconciler.record_product_master_response(sku, resp)

        combo_sku = "SP2-001792+SP2-001793+SP2-001794+SP2-001795"
        agg = reconciler.get_aggregated_combo_coupons(combo_sku)
        self.assertEqual(len(agg), 1)
        self.assertEqual(agg[0]["code"], "CP2609220007")
        self.assertEqual(agg[0]["discount"], 471.0)  # ยอดรวมคูปองทั้ง 4 Sub-SKU = 471.0 บาท พอดีเป๊ะ
        self.assertEqual(agg[0]["remark_target_price"], 1449.0)

        reconciler.last_scanned_smco_coupon_details = agg
        # ค้นหาคูปองสำหรับออเดอร์ส่วนต่าง 471.0 บาท (1920 - 1449 = 471)
        sugg = reconciler.find_suggested_cp_for_discount(471.0, order_date="2026-09-28 08:48", expected_price=1449.0, sku=combo_sku)
        self.assertIsNotNone(sugg)
        self.assertEqual(sugg["suggested_code"], "CP2609220007")
        self.assertEqual(format_smart_datetime_str(sugg["start_date"]), "23/09/2026 00:00:01")
        self.assertEqual(format_smart_datetime_str(sugg["end_date"]), "09/10/2026 23:59:59")
        self.assertEqual(sugg["suggested_remark"], "Shp/TT เดือน ก.ย. ราคาเซ็ทละ 1449")


    def test_gas_payload_sync_and_deduplication(self):
        """ทดสอบว่า payload ที่ส่งไปยัง GAS มีคอลัมน์ครบถ้วน (suggested_cp, dates, remark, last_updated) และ _is_exact_duplicate ไม่บล็อกข้อมูลใหม่"""
        from functions.pos.cp_data_loader import DualSourceCPLoader
        from unittest.mock import MagicMock

        loader = DualSourceCPLoader(gas_url="https://mock-gas-url/exec")
        loader._cached_df = pd.DataFrame([
            {
                "sku": "SP2-001792",
                "sale_price": 350.0,
                "cp_name": "",
                "suggested_cp": "CP2609220007",
                "suggested_usage_start_date": "",
                "suggested_usage_end_date": "",
                "suggested_remark": ""
            }
        ])

        # กรณีที่ 1: ข้อมูลเดิมในแคชไม่มีวันที่ แต่ payload ใหม่มีวันที่ -> ต้องไม่ใช่ duplicate (ต้องส่งขึ้น GAS ได้)
        new_payload = {
            "sku": "SP2-001792",
            "sale_price": 350.0,
            "suggested_cp": "CP2609220007",
            "suggested_usage_start_date": "23/09/2026 00:00:01",
            "suggested_usage_end_date": "09/10/2026 23:59:59",
            "suggested_remark": "Shp/TT Promo",
            "last_updated": "01/10/2026 12:00:00"
        }
        self.assertFalse(loader._is_exact_duplicate(new_payload))

        # กรณีที่ 2: อัปเดตแคชให้ตรงกับข้อมูลใหม่แล้ว -> คราวนี้ต้องถือเป็น duplicate
        loader._cached_df = pd.DataFrame([new_payload])
        self.assertTrue(loader._is_exact_duplicate(new_payload))

        # กรณีที่ 3: ตรวจสอบการส่ง payload จาก add_missing_cp_to_excel ไปยัง push_record_to_gas
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            pd.DataFrame([{"sku": "SP2-001792", "sale_price": 350.0, "suggested_cp": ""}]).to_excel(tmp_path, index=False)
            reconciler = POSPricingReconciler(self.mock_bot)
            self.mock_app.cp_table_location = tmp_path
            self.mock_app.cp_df = pd.DataFrame([{"sku": "SP2-001792", "sale_price": 350.0}])

            mock_loader = MagicMock()
            reconciler._dual_cp_loader = mock_loader

            reconciler.add_missing_cp_to_excel(
                sku_key="SP2-001792",
                expected_price=350.0,
                suggested_cp="CP2609220007",
                start_date=datetime.datetime(2026, 9, 23, 0, 0, 1),
                end_date=datetime.datetime(2026, 10, 9, 23, 59, 59),
                remark="Canon GI-71 Set"
            )

            mock_loader.push_record_to_gas.assert_called_once()
            called_payload = mock_loader.push_record_to_gas.call_args[0][0]

            self.assertEqual(called_payload["sku"], "SP2-001792")
            self.assertEqual(called_payload["sale_price"], 350.0)
            self.assertEqual(called_payload["expected_price"], 350.0)
            self.assertEqual(called_payload["suggested_cp"], "CP2609220007")
            self.assertEqual(called_payload["suggested_usage_start_date"], "23/09/2026 00:00:01")
            self.assertEqual(called_payload["suggested_usage_end_date"], "09/10/2026 23:59:59")
            self.assertEqual(called_payload["suggested_remark"], "Canon GI-71 Set")
            self.assertIn("last_updated", called_payload)
            self.assertTrue(len(called_payload["last_updated"]) > 10)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_filter_out_payment_and_installment_is_coupons(self):
        """
        ทดสอบว่าระบบกรองคูปองประเภท Payment / ผ่อนชำระ (เช่น IS2604170001, couponTypeEn='Payment') ออก
        และรับเฉพาะคูปอง Topup และ Add-on ที่มี Prefix เป็น CP หรือ DC เท่านั้น (เช่นสำหรับ SKU: PR5-000673)
        """
        reconciler = POSPricingReconciler(self.mock_bot)
        sku = "PR5-000673"

        # จำลอง Response จาก POS ที่มีทั้งคูปอง Payment (IS) และคูปอง Topup/Addon (CP/DC)
        mock_response = [
            {
                "productCode": sku,
                "productCouponDetail": [
                    {
                        "couponCode": "IS2604170001",
                        "couponDesc": "Promotion ผ่อน 0% 10 เดือน ธนาคารกสิกรไทย",
                        "couponTypeEn": "Payment",
                        "couponTypeTh": "Payment",
                        "couponDetailCash": 0.0,
                        "couponDetailDisc": 500.0,
                        "usedFlag": False
                    },
                    {
                        "couponCode": "IS2608010005",
                        "couponDesc": "Promotion ผ่อนชำระ Krungsri First Choice",
                        "couponTypeEn": "Payment",
                        "couponTypeTh": "Payment",
                        "couponDetailCash": 0.0,
                        "couponDetailDisc": 300.0,
                        "usedFlag": False
                    },
                    {
                        "couponCode": "CP2609010012",
                        "couponDesc": "Promotion Topup Campaign Online",
                        "couponTypeEn": "Topup",
                        "couponTypeTh": "Topup",
                        "couponDetailCash": 0.0,
                        "couponDetailDisc": 250.0,
                        "usedFlag": False
                    },
                    {
                        "couponCode": "DC2609150020",
                        "couponDesc": "Promotion Add-on Flash Sale",
                        "couponTypeEn": "Add-on",
                        "couponTypeTh": "Add-on",
                        "couponDetailCash": 0.0,
                        "couponDetailDisc": 150.0,
                        "usedFlag": False
                    }
                ]
            }
        ]

        reconciler.record_product_master_response(sku, mock_response)
        extracted = reconciler.get_aggregated_combo_coupons(sku)

        # ต้องได้เฉพาะ CP2609010012 และ DC2609150020 (ต้องไม่มี IS2604170001 หรือ IS2608010005)
        extracted_codes = [c["code"] for c in extracted]
        self.assertIn("CP2609010012", extracted_codes)
        self.assertIn("DC2609150020", extracted_codes)
        self.assertNotIn("IS2604170001", extracted_codes)
        self.assertNotIn("IS2608010005", extracted_codes)
        self.assertEqual(len(extracted), 2)

    def test_record_pos_cart_summary_sets_cp_name_none_when_no_coupon(self):
        """ทดสอบว่าเมื่อไม่มีการใช้ CP/DC ระบบจะบันทึก cp_name เป็น 'NONE'"""
        with tempfile.TemporaryDirectory() as tmpdir:
            excel_path = os.path.join(tmpdir, "cp_data.xlsx")
            df = pd.DataFrame([
                {"sku": "MNL-002484", "sale_price": 4507.0, "cp_name": "", "usage_start_date": "", "usage_end_date": ""}
            ])
            df.to_excel(excel_path, index=False)

            self.mock_app.cp_table_location = excel_path
            self.mock_app.cp_df = df
            self.mock_app.items = [{"เลขอ้างอิง SKU (SKU Reference No.)": "MNL-002484", "ราคาขายสุทธิ": 4507.0}]

            reconciler = POSPricingReconciler(self.mock_bot)
            reconciler.scrape_pos_cart_items = MagicMock(return_value=[
                {"sku": "MNL-002484", "unit_net": 4507.0, "coupons": ""}
            ])

            reconciler.record_pos_cart_summary_to_excel("ORDER_TEST_NONE_01")

            res_df = pd.read_excel(excel_path)
            self.assertEqual(str(res_df.loc[0, "cp_name"]).strip(), "NONE")
            self.assertEqual(str(res_df.loc[0, "last_adjustment_method"]).strip(), "NONE")

    def test_record_pos_cart_summary_populates_dates_from_coupon_code_fallback(self):
        """ทดสอบว่าเมื่อมี CP/DC แม้ไม่ได้เปิด Modal ระบบจะดึงวันที่เริ่มต้นจากรหัสคูปองมาบันทึก usage_start_date"""
        with tempfile.TemporaryDirectory() as tmpdir:
            excel_path = os.path.join(tmpdir, "cp_data.xlsx")
            df = pd.DataFrame([
                {"sku": "MNL-002418", "sale_price": 2849.0, "cp_name": "", "usage_start_date": "", "usage_end_date": ""}
            ])
            df.to_excel(excel_path, index=False)

            self.mock_app.cp_table_location = excel_path
            self.mock_app.cp_df = df
            self.mock_app.items = [{"เลขอ้างอิง SKU (SKU Reference No.)": "MNL-002418", "ราคาขายสุทธิ": 2849.0}]

            reconciler = POSPricingReconciler(self.mock_bot)
            # คูปอง DC2609280008 ถูกเลือกอัตโนมัติบน POS (ไม่มีการเปิด Modal สแกน)
            reconciler.scrape_pos_cart_items = MagicMock(return_value=[
                {"sku": "MNL-002418", "unit_net": 2849.0, "coupons": "DC2609280008"}
            ])

            reconciler.record_pos_cart_summary_to_excel("ORDER_TEST_DATE_01")

            res_df = pd.read_excel(excel_path)
            self.assertEqual(str(res_df.loc[0, "cp_name"]).strip(), "DC2609280008")
            self.assertEqual(str(res_df.loc[0, "usage_start_date"]).strip(), "28/09/2026")

    def test_resolve_multi_coupon_info_hierarchy_newest_start_and_shortest_end(self):
        """ทดสอบตรรกะ Multi-Coupon: วันที่ใหม่สุด และถ้าวันเริ่มเท่ากัน ให้เลือกวันจบที่สั้นที่สุด"""
        reconciler = POSPricingReconciler(self.mock_bot)
        # Mock Modal details ที่มี 3 คูปอง
        reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "CP2609010001",
                "start_date": datetime.date(2026, 9, 1),
                "end_date": datetime.date(2026, 9, 30),
                "remark": "Promo Sep"
            },
            {
                "code": "CP2609150001",
                "start_date": datetime.date(2026, 9, 15),
                "end_date": datetime.date(2026, 10, 31),
                "remark": "Promo Mid-Sep Long"
            },
            {
                "code": "CP2609150002",
                "start_date": datetime.date(2026, 9, 15),
                "end_date": datetime.date(2026, 9, 25),
                "remark": "Promo Mid-Sep Short"
            }
        ]

        # กรณี 1: CP2609010001 vs CP2609150001 -> วันเริ่ม 15/09/2026 ใหม่กว่า 01/09/2026
        rem1, s1, e1 = reconciler.resolve_multi_coupon_info("CP2609010001 CP2609150001")
        self.assertEqual(s1, datetime.date(2026, 9, 15))
        self.assertEqual(e1, datetime.date(2026, 10, 31))

        # กรณี 2: CP2609150001 vs CP2609150002 -> วันเริ่มเท่ากัน (15/09) แต่ CP2609150002 จบไวกว่า (25/09 < 31/10)
        rem2, s2, e2 = reconciler.resolve_multi_coupon_info("CP2609150001 CP2609150002")
        self.assertEqual(s2, datetime.date(2026, 9, 15))
        self.assertEqual(e2, datetime.date(2026, 9, 25))


    def test_add_missing_cp_to_excel_updates_empty_placeholder_and_splits_multi_patterns(self):
        """
        ทดสอบว่า:
        1. หาก cp_data มีแถวที่มีแค่ SKU และ sale_price (แต่ cp_name ว่าง)
           เมื่อได้รับ Suggestion ระบบจะอัปเดตลงช่อง suggested_* ของแถวเดิมนั้นโดยไม่แตะ cp_name
        2. หากพบหลาย Pattern สำหรับ SKU และราคาเดียวกัน Pattern ที่ 2 จะถูกสร้างเป็นแถวใหม่
           โดยทั้งสองแถวยังคงมี cp_name ว่าง เพื่อรอการยิงจริง
        """
        reconciler = POSPricingReconciler(self.mock_bot)
        with tempfile.TemporaryDirectory() as test_dir:
            test_file = os.path.join(test_dir, "test_placeholder_update.xlsx")
            initial_df = pd.DataFrame([
                {
                    "sku": "MNL-009999",
                    "sale_price": 5000.0,
                    "cp_name": "",
                    "usage_start_date": "",
                    "usage_end_date": "",
                    "suggested_cp": "",
                    "suggested_usage_start_date": "",
                    "suggested_usage_end_date": "",
                    "suggested_remark": ""
                }
            ])
            initial_df.to_excel(test_file, index=False)
            self.mock_app.cp_table_location = test_file

            # 1. ส่ง Pattern ที่ 1 เข้ามา -> ต้องอัปเดตลงแถวเดิมที่มีช่องว่าง
            reconciler.add_missing_cp_to_excel(
                "MNL-009999",
                5000.0,
                suggested_cp="CP2610010001",
                start_date="01/10/2026",
                end_date="31/10/2026",
                remark="Pattern 1 Single"
            )

            df1 = pd.read_excel(test_file)
            self.assertEqual(len(df1), 1)
            self.assertTrue(pd.isna(df1.iloc[0]['cp_name']) or df1.iloc[0]['cp_name'] == "")
            self.assertEqual(df1.iloc[0]['suggested_cp'], "CP2610010001")
            self.assertEqual(df1.iloc[0]['suggested_usage_start_date'], "01/10/2026")
            self.assertEqual(df1.iloc[0]['suggested_usage_end_date'], "31/10/2026")
            self.assertEqual(df1.iloc[0]['suggested_remark'], "Pattern 1 Single")

            # 2. ส่ง Pattern ที่ 2 เข้ามา (สูตรคูปองต่างกัน: CP2610010002 DC2610010001) -> ต้อง Insert แถวใหม่
            reconciler.add_missing_cp_to_excel(
                "MNL-009999",
                5000.0,
                suggested_cp="CP2610010002 DC2610010001",
                start_date="01/10/2026",
                end_date="15/10/2026",
                remark="Pattern 2 Combo"
            )

            df2 = pd.read_excel(test_file)
            self.assertEqual(len(df2), 2)
            # ตรวจสอบว่าทั้ง 2 แถวมี cp_name ว่าง (ไม่แตะช่องจริง)
            for _, row in df2.iterrows():
                self.assertTrue(pd.isna(row['cp_name']) or row['cp_name'] == "")
                self.assertEqual(row['sku'], "MNL-009999")
                self.assertEqual(row['sale_price'], 5000.0)

            # แถวแรกมี Pattern 1 และแถวสองมี Pattern 2
            sugg_cps = df2['suggested_cp'].tolist()
            self.assertIn("CP2610010001", sugg_cps)
            self.assertIn("CP2610010002 DC2610010001", sugg_cps)

    def test_mnl_002358_standalone_coupon_selected_without_preselected(self):
        """
        ทดสอบกรณี SKU MNL-002358:
        บน POS มี Top-up CP2609290086 (ลด 300) ติดมาอัตโนมัติ ทำให้ราคาเป็น 2,202
        ต้องการขายที่ 2,157 (ส่วนต่างบน POS = 45 บาท, แต่ลดจาก Base Price 2502 คือ 345 บาท)
        พบคูปอง dynamic CP2610090037 (ลด 345) ระบุ Remark 'ใช้คูปอง dynamic นี้ราคาขายยิงขึ้น 2157'
        ระบบต้องเลือก CP2610090037 ใบเดียว โดยไม่พ่วง CP2609290086 มาซ้ำซ้อน
        """
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP2609290086", "discount": 300.0, "desc": "Top-up 300", "is_selected": True},
            {"code": "CP2610090037", "discount": 345.0, "desc": "Addon 345", "remark": "ใช้คูปอง dynamic นี้ราคาขายยิงขึ้น 2157", "is_selected": False},
        ]
        reconciler.last_preselected_smco_coupons = ["CP2609290086"]

        res = reconciler.find_suggested_cp_for_discount(45.0, expected_price=2157.0, sku="MNL-002358")
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "CP2610090037")
        self.assertEqual(res["preselected_codes"], [])
        self.assertEqual(res["new_code"], "CP2610090037")
        self.assertEqual(res["discount"], 345.0)
        self.assertEqual(res["remark"], "ใช้คูปอง dynamic นี้ราคาขายยิงขึ้น 2157")

    def test_mnl_002120_live_fetch_and_resolve_coupon_dates_from_smco(self):
        """
        ทดสอบกรณี SKU MNL-002120:
        เมื่อดึงข้อมูลสดผ่าน fetch_product_master_info / resolve_multi_coupon_info
        ต้องได้ช่วงวันที่ 01/10/2026 - 31/10/2026 ตามที่ SMCO POS API ส่งกลับมา
        ไม่ใช่ 30/09/2026 ที่เดามาจากรหัสคูปอง
        """
        reconciler = POSPricingReconciler(self.mock_bot)
        mock_driver = MagicMock()
        reconciler.driver = mock_driver

        mock_driver.execute_async_script.return_value = [
            {
                "productId": 9999,
                "productCode": "MNL-002120",
                "productCouponDetail": [
                    {
                        "couponId": 12345,
                        "couponCode": "CP2609300027",
                        "couponDesc": "Promotion 900.- (01/10/2026 - 31/10/2026)",
                        "couponDetailRemark": "Promotion 900.-",
                        "startDate": "Oct 1, 2026 12:00:01 AM",
                        "endDate": "Oct 31, 2026 11:59:59 PM",
                        "couponDetailCash": 900.0,
                        "couponDetailDisc": 0.0
                    }
                ]
            }
        ]

        rem, s_dt, e_dt = reconciler.resolve_multi_coupon_info(
            "CP2609300027", expected_price=7225.0, sku="MNL-002120"
        )
        self.assertEqual(rem, "Promotion 900.-")
        s_date_val = s_dt.date() if isinstance(s_dt, datetime.datetime) else s_dt
        e_date_val = e_dt.date() if isinstance(e_dt, datetime.datetime) else e_dt
        self.assertEqual(s_date_val, datetime.date(2026, 10, 1))
        self.assertEqual(e_date_val, datetime.date(2026, 10, 31))

    def test_sync_product_master_coupon_dates_updates_excel_and_cp_df(self):
        """ทดสอบว่าเมื่อยิง SKU และดักจับ Network Response ได้ ระบบจะสกัด startDate/endDate และอัปเดตลง Excel กับ cp_df ทันที"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "cp_data.xlsx")
            initial_df = pd.DataFrame([
                {
                    "sku": "MNL-002120",
                    "sale_price": 7225.0,
                    "cp_name": "CP2609300027",
                    "usage_start_date": "30/09/2026",
                    "usage_end_date": "",
                    "suggested_cp": "CP2609300027",
                    "suggested_usage_start_date": "30/09/2026",
                    "suggested_usage_end_date": "",
                    "suggested_remark": ""
                }
            ])
            initial_df.to_excel(test_file, index=False)
            self.mock_app.cp_table_location = test_file
            self.mock_app.cp_df = initial_df.copy()

            reconciler = POSPricingReconciler(self.mock_bot)

            # จำลอง response ที่ดักจับได้จากการยิง SKU
            captured_response = [
                {
                    "productId": 9999,
                    "productCode": "MNL-002120",
                    "productCouponDetail": [
                        {
                            "couponId": 12345,
                            "couponCode": "CP2609300027",
                            "couponDesc": "Promotion 900.- (01/10/2026 - 31/10/2026)",
                            "couponDetailRemark": "Promotion 900.-",
                            "startDate": "Oct 1, 2026 12:00:01 AM",
                            "endDate": "Oct 31, 2026 11:59:59 PM",
                            "couponDetailCash": 900.0,
                            "couponDetailDisc": 0.0
                        }
                    ]
                }
            ]

            reconciler.record_product_master_response("MNL-002120", captured_response)

            updated_df = pd.read_excel(test_file)
            self.assertEqual(len(updated_df), 1)
            row = updated_df.iloc[0]
            self.assertEqual(str(row["usage_start_date"]).strip(), "01/10/2026")
            self.assertEqual(str(row["usage_end_date"]).strip(), "31/10/2026")
            self.assertEqual(str(row["suggested_usage_start_date"]).strip(), "01/10/2026")
            self.assertEqual(str(row["suggested_usage_end_date"]).strip(), "31/10/2026")
            self.assertEqual(str(row["suggested_remark"]).strip(), "Promotion 900.-")

            # ตรวจสอบ cp_df ใน memory ด้วย
            self.assertIsNotNone(self.mock_app.cp_df)
            mem_row = self.mock_app.cp_df.iloc[0]
            self.assertEqual(str(mem_row["usage_start_date"]).strip(), "01/10/2026")
            self.assertEqual(str(mem_row["usage_end_date"]).strip(), "31/10/2026")


    def test_fetch_product_master_info_uses_cache_and_avoids_duplicate_fetch(self):
        """ทดสอบว่า fetch_product_master_info จะใช้ข้อมูลจาก cache ทันที และไม่เรียก execute_async_script ซ้ำหากมีข้อมูลอยู่แล้ว"""
        reconciler = POSPricingReconciler(self.mock_bot)
        test_sku = "TEST-SKU-CACHE"
        cached_data = [{"productCode": test_sku, "productCouponDetail": []}]
        reconciler._product_master_cache = {test_sku: cached_data}

        # เรียก fetch_product_master_info
        result = reconciler.fetch_product_master_info(test_sku)

        # ผลลัพธ์ต้องเป็น cached_data ทันที
        self.assertEqual(result, cached_data)
        # mock_driver.execute_async_script ต้องไม่ถูกเรียกเลย
        self.mock_driver.execute_async_script.assert_not_called()


    def test_sync_product_master_coupon_dates_filters_store_and_branch_by_session_context(self):
        """ทดสอบว่า sync_product_master_coupon_dates_to_excel จะกรองคูปองจาก store อื่นทิ้ง ไม่บันทึกข้าม store"""
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler._session_ctx = {"branch_id": 180, "store_id": 208}  # สมมติเป็น Shopee store 208

        sku = "MNL-002420"
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = os.path.join(tmp_dir, "cp_data.xlsx")
            init_df = pd.DataFrame([{
                "sku": sku,
                "sale_price": 3601.0,
                "cp_name": "",
                "suggested_cp": "",
                "usage_start_date": "",
                "usage_end_date": "",
                "suggested_usage_start_date": "",
                "suggested_usage_end_date": "",
                "suggested_remark": ""
            }])
            init_df.to_excel(test_file, index=False)
            self.mock_app.cp_table_location = test_file

            # จำลอง Response จาก POS:
            # - CP2609290086 สำหรับ store 208 (Shopee) -> ต้องผ่าน
            # - CP2610050011 สำหรับ store 642 (store อื่น) -> ต้องถูกกรองทิ้ง!
            response_data = [{
                "productCode": sku,
                "productCouponDetail": [
                    {
                        "couponCode": "CP2610050011",
                        "startDate": "2026-10-05 00:00:00",
                        "endDate": "2026-10-11 23:59:59",
                        "couponDetailRemark": "Other Store Promo",
                        "couponBranchs": [{"couponBranchId": 180, "couponStoreId": 642}]
                    },
                    {
                        "couponCode": "CP2609290086",
                        "startDate": "2026-10-01 00:00:00",
                        "endDate": "2026-10-31 23:59:59",
                        "couponDetailRemark": "Shopee Promo 300.-",
                        "couponBranchs": [{"couponBranchId": 180, "couponStoreId": 208}]
                    }
                ]
            }]

            reconciler.sync_product_master_coupon_dates_to_excel(sku, response_data)

            res_df = pd.read_excel(test_file)
            row = res_df.iloc[0]
            # ต้องได้ CP2609290086 ไม่ใช่ CP2610050011 จาก store 642
            self.assertEqual(row["suggested_cp"], "CP2609290086")
            self.assertEqual(row["suggested_usage_start_date"], "01/10/2026")
            self.assertEqual(row["suggested_usage_end_date"], "31/10/2026")
            self.assertIn("Shopee Promo", row["suggested_remark"])


if __name__ == "__main__":
    unittest.main()





