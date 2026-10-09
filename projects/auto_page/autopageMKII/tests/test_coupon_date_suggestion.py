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


if __name__ == "__main__":
    unittest.main()





