import datetime
import unittest
from unittest.mock import MagicMock, patch

from functions.pos.pricing_engine import (
    POSPricingReconciler,
    extract_target_price_from_text,
    is_coupon_valid_for_order,
)


class TestRealtimeAmbiguityAndRemark(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_app.items = [
            {"เลขอ้างอิง SKU (SKU Reference No.)": "SP2-001753+SP2-001755", "จำนวน": 1, "ราคาขาย": 993.0, "ชื่อสินค้า": "Set Item"}
        ]
        self.mock_app.correct_sku_pattern = lambda s: [x.strip() for x in str(s).split('+')]
        self.mock_app.cus_purchase_time.get.return_value = "2026-10-03 14:00:00"
        self.mock_app.marketplace_target.get.return_value = "Shopee"
        self.mock_app.is_auto_invoice_mode.get.return_value = True
        self.mock_app.financials.seller_voucher = 0.0
        self.mock_app.cp_table_location = ""
        self.mock_app.cp_df = None

        self.mock_bot = MagicMock()
        self.mock_bot.cus_order = "261003K6J8B8H5"
        self.mock_bot.merged_dict = {'SMCO :: เปิดการขาย': 'handle_pos'}

        self.reconciler = POSPricingReconciler(self.mock_bot)
        self.reconciler.app = self.mock_app

    def test_extract_target_price_from_text(self):
        """ทดสอบการสกัดราคาเป้าหมายจาก Remark ต่างๆ"""
        self.assertEqual(extract_target_price_from_text("FS Shp Rebate ราคาเซ็ทละ 993"), 993.0)
        self.assertEqual(extract_target_price_from_text("Shp/TT เดือน ต.ค. ราคา 409"), 409.0)
        self.assertEqual(extract_target_price_from_text("Dynamic ก.ย. Shp ราคา 9673"), 9673.0)
        self.assertEqual(extract_target_price_from_text("ราคาคู่ละ 1,017.-"), 1017.0)

    def test_is_coupon_valid_for_order_with_live_smco_promotion(self):
        """
        ทดสอบว่าคูปองใหม่ที่เริ่มใช้งานบน SMCO (เช่น 05/10/2026)
        สามารถเป็น candidate ที่ถูกต้องสำหรับการออกบิลออเดอร์ที่สั่งเมื่อ 05/10/2026 ได้
        """
        c_dict = {
            "code": "CP2610050027",
            "start_date": "05/10/2026",
            "end_date": "31/10/2026",
            "is_expired": False,
            "desc": "FS Shp Rebate ราคาเซ็ทละ 993"
        }
        order_date_str = "2026-10-05 14:00:00"
        self.assertTrue(is_coupon_valid_for_order(c_dict, order_date_str))

    def test_coupon_with_mismatched_remark_price_is_not_matched_for_discount(self):
        """
        ทดสอบว่าคูปองที่มี Remark ระบุราคา 409 (เช่น ของ SKU เดี่ยว)
        จะไม่ถูกจับคู่ลดราคาให้กับ Combo set ที่ราคา 993 หรือ 1056
        """
        self.reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "CP2609300040",
                "discount": 63.0,
                "remark": "Shp/TT เดือน ต.ค. ราคา 409",
                "remark_target_price": 409.0,
                "desc": "Shp/TT เดือน ต.ค. ราคา 409",
                "start_date": datetime.date(2026, 10, 1),
                "end_date": datetime.date(2026, 10, 31),
                "is_expired": False
            }
        ]

        # Target discount 63 บาท แต่ expected_price คือ 993 (remark_target_price 409 != 993)
        res = self.reconciler.find_suggested_cp_for_discount(
            target_discount=63.0,
            expected_price=993.0,
            order_date="2026-10-03",
            sku="SP2-001753+SP2-001755"
        )
        self.assertIsNone(res)

        direct_matches = self.reconciler.find_all_matching_coupons_on_smco(
            target_discount=63.0,
            expected_price=993.0,
            order_date="2026-10-03",
            sku="SP2-001753+SP2-001755"
        )
        self.assertEqual(len(direct_matches), 0)

    def test_ambiguity_detection_halts_order_when_multiple_recipes_found(self):
        """
        ทดสอบว่าเมื่อพบทั้งสูตรเก่าจากตาราง (CP2609140012 + OC 5 4)
        และคูปองใหม่สดๆ บน SMCO (CP2610050027 สำหรับราคา 993)
        ระบบจะตรวจพบ Ambiguity Alert และ raise ValueError เพื่อหยุดบอททันที
        """
        sku_key = "SP2-001753+SP2-001755"
        verification_result = {
            "all_ok": False,
            "price": {
                sku_key: {
                    "ok": False,
                    "actual": 1056.0,
                    "expected": 993.0,
                    "diff": -63.0
                }
            }
        }

        # จำลอง candidates จากตาราง cp_data.xlsx (สูตรเก่า)
        self.reconciler.find_all_cp_candidates_from_excel = MagicMock(return_value=[
            {"cp_name": "CP2609140012", "oc_amount": "5 4", "dc_amount": ""}
        ])

        # จำลองว่า CP2609140012 ยังมีอยู่บน SMCO
        self.reconciler.scan_matching_cp_candidates_on_smco = MagicMock(return_value=[
            {"cp_name": "CP2609140012", "oc_amount": "5 4", "dc_amount": ""}
        ])

        # จำลองว่าพบคูปองใหม่ CP2610050027 บน SMCO ที่ตรงกับราคา 993 พอดี
        self.reconciler.find_all_matching_coupons_on_smco = MagicMock(return_value=[
            {
                "cp_name": "CP2610050027",
                "oc_amount": "",
                "dc_amount": "",
                "start_date": datetime.date(2026, 10, 5),
                "end_date": datetime.date(2026, 10, 31),
                "remark": "FS Shp Rebate ราคาเซ็ทละ 993",
                "source": "SMCO"
            }
        ])

        self.reconciler._record_missing_cp_with_dates = MagicMock()

        # ต้อง raise ValueError จาก _raise_ambiguous_cp_guide
        with self.assertRaises(ValueError) as cm:
            self.reconciler.process_price_mismatches(verification_result)

        self.assertIn("ขอวิธีปรับราคา", str(cm.exception))
        self.assertIn("CP2609140012", str(cm.exception))
        self.assertIn("CP2610050027", str(cm.exception))
        self.reconciler._record_missing_cp_with_dates.assert_called()

    def test_add_missing_cp_to_excel_sanitizes_conflicting_remark_and_syncs_gas(self):
        """
        ทดสอบว่า add_missing_cp_to_excel เมื่อราคาเป้าหมายคือ 1056 แต่ remark ระบุ 'ราคา 409'
        จะ sanitize remark ให้เป็นค่าว่างใน local Excel และส่ง '-' ให้ GAS เพื่อเคลียร์ค่าเดิม
        """
        import os
        import tempfile
        import pandas as pd

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # เริ่มต้นด้วยแถวที่มี suggested_remark ขัดแย้งกับราคา
            df_init = pd.DataFrame({
                "sku": ["SP2-001753+SP2-001755"],
                "sale_price": [1056.0],
                "cp_name": ["CP2609300040"],
                "suggested_cp": ["CP2609300040"],
                "suggested_remark": ["Shp/TT เดือน ต.ค. ราคา 409"]
            })
            df_init.to_excel(tmp_path, index=False)

            self.mock_app.cp_table_location = tmp_path
            self.mock_app.cp_df = df_init.copy()
            mock_gas_loader = MagicMock()
            self.reconciler._dual_cp_loader = mock_gas_loader

            # สั่ง add_missing_cp_to_excel โดยไม่ระบุ remark หรือ remark ขัดแย้ง
            self.reconciler.add_missing_cp_to_excel(
                sku_key="SP2-001753+SP2-001755",
                expected_price=1056.0,
                suggested_cp="CP2609300040",
                remark=""
            )

            # ตรวจสอบว่าในไฟล์ Excel เคลียร์ suggested_remark ให้ว่าง
            df_saved = pd.read_excel(tmp_path)
            row = df_saved[df_saved["sku"] == "SP2-001753+SP2-001755"]
            self.assertEqual(len(row), 1)
            rem_val = str(row["suggested_remark"].iloc[0])
            self.assertTrue(rem_val in ("", "nan", "None") or pd.isna(row["suggested_remark"].iloc[0]))

            # ตรวจสอบ payload ที่ส่งให้ GAS ว่าส่ง suggested_remark เป็น '-' เพื่อบังคับเขียนทับ
            mock_gas_loader.push_record_to_gas.assert_called_once()
            call_payload = mock_gas_loader.push_record_to_gas.call_args[0][0]
            self.assertEqual(call_payload["sku"], "SP2-001753+SP2-001755")
            self.assertEqual(call_payload["suggested_remark"], "-")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_dual_cp_loader_sync_to_local_excel(self):
        """
        ทดสอบว่า DualSourceCPLoader เมื่อ fetch จาก GAS ได้ จะ sync ข้อมูลลง local Excel อัตโนมัติ
        """
        import os
        import tempfile
        import pandas as pd
        from functions.pos.cp_data_loader import DualSourceCPLoader

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # สร้าง local excel เดิม
            df_local = pd.DataFrame({
                "sku": ["SP2-001753+SP2-001755"],
                "sale_price": [993.0],
                "cp_name": ["CP2609140012"],
                "suggested_cp": [""],
                "suggested_remark": [""]
            })
            df_local.to_excel(tmp_path, index=False)

            loader = DualSourceCPLoader(gas_url="https://fake-gas-url/exec", local_excel_path=tmp_path)

            # mock fetch_from_gas ให้ได้ข้อมูลใหม่ที่มี suggested_cp และ suggested_remark
            df_gas_data = pd.DataFrame({
                "sku": ["SP2-001753+SP2-001755"],
                "sale_price": [993.0],
                "cp_name": ["CP2609140012"],
                "suggested_cp": ["CP2610050027"],
                "suggested_remark": ["FS Shp Rebate ราคาเซ็ทละ 993"]
            })
            loader.fetch_from_gas = MagicMock(return_value=df_gas_data)

            # โหลด CP
            loaded_df = loader.load_cp_df(force_refresh=True)
            self.assertFalse(loaded_df.empty)

            # ตรวจสอบว่า local Excel ถูก sync อัปเดตข้อมูลจาก GAS เรียบร้อย
            df_synced = pd.read_excel(tmp_path)
            self.assertEqual(df_synced.loc[0, "suggested_cp"], "CP2610050027")
            self.assertEqual(df_synced.loc[0, "suggested_remark"], "FS Shp Rebate ราคาเซ็ทละ 993")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_is_exact_duplicate_detects_cleared_field(self):
        """
        ทดสอบว่า _is_exact_duplicate จะไม่มองข้ามกรณีที่มีการเคลียร์ฟิลด์ (เช่น ค่าเดิมมี แต่ค่าใหม่ส่ง '-' หรือ '')
        """
        import pandas as pd
        from functions.pos.cp_data_loader import DualSourceCPLoader

        loader = DualSourceCPLoader(gas_url="", local_excel_path=None)
        loader._cached_df = pd.DataFrame([{
            "sku": "SP2-001753+SP2-001755",
            "sale_price": 1056.0,
            "suggested_remark": "Shp/TT เดือน ต.ค. ราคา 409"
        }])

        # เมื่อส่ง payload ที่ต้องการเคลียร์ suggested_remark ให้เป็น '-'
        payload = {
            "sku": "SP2-001753+SP2-001755",
            "sale_price": 1056.0,
            "suggested_remark": "-"
        }
        # ต้องไม่ใช่ duplicate (is_exact_duplicate = False) เพื่อให้ส่ง POST ไปอัปเดตบน Google Sheet ได้
        self.assertFalse(loader._is_exact_duplicate(payload))

    def test_add_missing_cp_to_excel_separates_distinct_patterns_and_prevents_oc_leak(self):
        """
        ทดสอบว่า add_missing_cp_to_excel เมื่อมี Pattern เดิม (เช่น CP2609140012 + OC 5 4)
        แล้วมี Pattern ใหม่เข้ามา (เช่น CP2610050027 ที่ไม่มี OC/DC):
        1. ต้องแยกบันทึกเป็นคนละแถว ไม่เขียนทับแถวเดิม
        2. ค่า oc_amount ของแถวเดิมต้องไม่รั่วไหล (leak) ไปยัง Pattern ใหม่
        3. payload ที่ส่งให้ GAS ต้องไม่มี oc_amount ของแถวเดิม
        """
        import os
        import tempfile
        import pandas as pd

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # เริ่มต้นด้วยตารางที่มีเฉพาะ Pattern เดิม (CP2609140012 + OC '5 4')
            df_init = pd.DataFrame([{
                "sku": "SP2-001753+SP2-001755",
                "sale_price": 993.0,
                "cp_name": "CP2609140012",
                "usage_start_date": "2026-09-14 00:00:01",
                "usage_end_date": "2026-10-09 00:00:00",
                "oc_amount": "5 4",
                "dc_amount": "",
                "suggested_cp": "",
                "suggested_remark": ""
            }])
            df_init.to_excel(tmp_path, index=False)

            self.mock_app.cp_table_location = tmp_path
            self.mock_app.cp_df = df_init.copy()
            mock_gas_loader = MagicMock()
            self.reconciler._dual_cp_loader = mock_gas_loader

            # บันทึก Candidate สูตรใหม่ CP2610050027 (ไม่มีการปรับราคา OC หรือ DC)
            self.reconciler.add_missing_cp_to_excel(
                sku_key="SP2-001753+SP2-001755",
                expected_price=993.0,
                suggested_cp="CP2610050027",
                start_date="2026-10-05 00:00:01",
                end_date="2026-10-20 23:59:59",
                remark="FS Shp ถูกชัวร์ ราคาเซ็ทละ 993",
                oc_amount="",
                dc_amount=""
            )

            # ตรวจสอบไฟล์ Excel ต้องมี 2 แถวสำหรับ SKU และราคานี้
            df_saved = pd.read_excel(tmp_path)
            rows = df_saved[df_saved["sku"] == "SP2-001753+SP2-001755"]
            self.assertEqual(len(rows), 2, "ต้องมี 2 แถวแยกกันสำหรับ 2 Pattern ที่ต่างกัน")

            # แถวเดิม: ต้องคงสภาพเดิม ไม่ถูกเขียนทับ
            row_old = rows[rows["cp_name"] == "CP2609140012"].iloc[0]
            self.assertEqual(str(row_old["oc_amount"]).strip(), "5 4")
            self.assertTrue(pd.isna(row_old["suggested_cp"]) or str(row_old["suggested_cp"]).strip() in ("", "-"))

            # แถวใหม่: ต้องมี suggested_cp='CP2610050027' และ oc_amount ต้องว่าง (ห้ามเอา 5 4 จากแถวเดิมมาใช้!)
            row_new = rows[rows["suggested_cp"] == "CP2610050027"].iloc[0]
            self.assertEqual(row_new["suggested_remark"], "FS Shp ถูกชัวร์ ราคาเซ็ทละ 993")
            self.assertTrue(pd.isna(row_new["oc_amount"]) or str(row_new["oc_amount"]).strip() in ("", "-"))

            # ตรวจสอบ payload ที่ส่งให้ GAS: ต้องไม่นำ oc_amount ของแถวเดิมติดมาด้วย
            mock_gas_loader.push_record_to_gas.assert_called_once()
            gas_payload = mock_gas_loader.push_record_to_gas.call_args[0][0]
            self.assertEqual(gas_payload["suggested_cp"], "CP2610050027")
            self.assertEqual(gas_payload["suggested_remark"], "FS Shp ถูกชัวร์ ราคาเซ็ทละ 993")
            self.assertEqual(gas_payload["oc_amount"], "", "GAS payload ต้องไม่มี oc_amount ที่ตกค้างจาก pattern เก่า")
            self.assertNotIn("cp_name", gas_payload)  # ห้ามส่ง cp_name ของแถวเดิม

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_dual_cp_loader_merge_preserves_distinct_recipes_same_sku_price(self):
        """
        ทดสอบว่า DualSourceCPLoader._merge_dfs จะไม่ drop แถวที่เป็นคนละสูตร (คนละคูปอง หรือคนละ OC/DC)
        แม้จะเป็น SKU เดียวกันและราคาขายเดียวกัน
        """
        import pandas as pd
        from functions.pos.cp_data_loader import DualSourceCPLoader

        loader = DualSourceCPLoader(gas_url="", local_excel_path=None)

        df_gas = pd.DataFrame([{
            "sku": "SP2-001753+SP2-001755",
            "sale_price": 993.0,
            "cp_name": "CP2609140012",
            "oc_amount": "5 4",
            "dc_amount": "",
            "suggested_cp": ""
        }])

        df_local = pd.DataFrame([
            {
                "sku": "SP2-001753+SP2-001755",
                "sale_price": 993.0,
                "cp_name": "CP2609140012",
                "oc_amount": "5 4",
                "dc_amount": "",
                "suggested_cp": ""
            },
            {
                "sku": "SP2-001753+SP2-001755",
                "sale_price": 993.0,
                "cp_name": "CP2610050027",
                "oc_amount": "",
                "dc_amount": "",
                "suggested_cp": "CP2610050027"
            }
        ])

        merged = loader._merge_dfs(df_gas, df_local)
        sku_rows = merged[merged["sku"] == "SP2-001753+SP2-001755"]
        self.assertEqual(len(sku_rows), 2, "ต้องเก็บรักษาทั้ง 2 สูตร (Pattern) ไม่ตัดแถวใดแถวหนึ่งทิ้ง")

    def test_is_exact_duplicate_differentiates_adjustments(self):
        """
        ทดสอบว่า _is_exact_duplicate จะแยกความแตกต่างของ oc_amount / dc_amount
        ไม่มองว่าข้อมูลที่มี oc_amount ต่างกันเป็น duplicate
        """
        import pandas as pd
        from functions.pos.cp_data_loader import DualSourceCPLoader

        loader = DualSourceCPLoader(gas_url="", local_excel_path=None)
        loader._cached_df = pd.DataFrame([{
            "sku": "SP2-001753+SP2-001755",
            "sale_price": 993.0,
            "cp_name": "CP2609140012",
            "oc_amount": "5 4",
            "dc_amount": ""
        }])

        # เมื่อส่งข้อมูลสูตรใหม่ที่ไม่มี oc_amount
        payload = {
            "sku": "SP2-001753+SP2-001755",
            "sale_price": 993.0,
            "suggested_cp": "CP2610050027",
            "oc_amount": "",
            "dc_amount": ""
        }
        self.assertFalse(loader._is_exact_duplicate(payload))

    def test_find_suggested_cp_prefers_campaign_desc_when_detail_remark_conflicts(self):
        """
        ทดสอบกรณี SKU เซ็ท (Combo) ที่คูปองมี desc ระบุราคาเซ็ท 1056
        แต่ sub-SKU มี detail remark ระบุราคาแยกชิ้น 409
        ระบบจะต้องเลือก desc ที่ตรงกับ expected_price (1056) และไม่ตัดคูปองทิ้ง
        """
        self.reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "CP2609300040",
                "discount": 63.0,
                "remark": "Shp/TT เดือน ต.ค. ราคา 409",
                "remark_target_price": 409.0,
                "desc": "Shp/TT เดือน ต.ค. ราคาเซ็ทละ 1056",
                "start_date": datetime.date(2026, 10, 1),
                "end_date": datetime.date(2026, 10, 31),
                "is_expired": False
            }
        ]

        # Target discount 63 บาท สำหรับ expected_price 1056
        res = self.reconciler.find_suggested_cp_for_discount(
            target_discount=63.0,
            expected_price=1056.0,
            order_date="2026-10-03",
            sku="SP2-001753+SP2-001755"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "CP2609300040")
        self.assertEqual(res["remark"], "Shp/TT เดือน ต.ค. ราคาเซ็ทละ 1056")

        direct_matches = self.reconciler.find_all_matching_coupons_on_smco(
            target_discount=63.0,
            expected_price=1056.0,
            order_date="2026-10-03",
            sku="SP2-001753+SP2-001755"
        )
        self.assertEqual(len(direct_matches), 1)
        self.assertEqual(direct_matches[0]["cp_name"], "CP2609300040")
        self.assertEqual(direct_matches[0]["remark"], "Shp/TT เดือน ต.ค. ราคาเซ็ทละ 1056")

    def test_multi_coupon_comma_separated_remark_and_date_rules(self):
        """
        ทดสอบกรณี SKU มีคูปองหลายตัว (เช่น Combo หรือมีทั้ง CP และ DC):
        1. suggested_remark ต้องนำ remark มาต่อกันตามลำดับของ cp/dc คั่นด้วย ', '
        2. เวลา: คูปองที่มี start_date ใหม่กว่าจะได้รับการเลือก
        3. หาก start_date เท่ากัน คูปองที่มี end_date สั้นกว่าจะได้รับการเลือก
        """
        self.reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "CP2609010001",
                "discount": 50.0,
                "remark": "Remark คูปอง CP ตัวแรก",
                "desc": "Promo CP",
                "start_date": datetime.date(2026, 9, 1),
                "end_date": datetime.date(2026, 9, 30),
                "is_expired": False
            },
            {
                "code": "DC2609100002",
                "discount": 50.0,
                "remark": "Remark ส่วนลด DC ตัวที่สอง",
                "desc": "Promo DC",
                "start_date": datetime.date(2026, 9, 10),
                "end_date": datetime.date(2026, 9, 25),
                "is_expired": False
            }
        ]

        # 1. ทดสอบ start_date ใหม่กว่า (Sep 10 > Sep 1)
        rem, s_dt, e_dt = self.reconciler.resolve_multi_coupon_info("CP2609010001 DC2609100002")
        self.assertEqual(rem, "Remark คูปอง CP ตัวแรก, Remark ส่วนลด DC ตัวที่สอง")
        self.assertEqual(s_dt, datetime.date(2026, 9, 10))
        self.assertEqual(e_dt, datetime.date(2026, 9, 25))

        # 2. ทดสอบกรณี start_date เท่ากัน ให้เลือก end_date ที่สั้นกว่า
        self.reconciler.last_scanned_smco_coupon_details = [
            {
                "code": "CP2609100001",
                "discount": 50.0,
                "remark": "CP ตัวแรก",
                "desc": "Promo CP",
                "start_date": datetime.date(2026, 9, 10),
                "end_date": datetime.date(2026, 9, 30),  # ยาวกว่า
                "is_expired": False
            },
            {
                "code": "DC2609100002",
                "discount": 50.0,
                "remark": "DC ตัวสอง",
                "desc": "Promo DC",
                "start_date": datetime.date(2026, 9, 10),  # เท่ากัน
                "end_date": datetime.date(2026, 9, 20),  # สั้นกว่า
                "is_expired": False
            }
        ]
        rem2, s_dt2, e_dt2 = self.reconciler.resolve_multi_coupon_info("CP2609100001 DC2609100002")
        self.assertEqual(rem2, "CP ตัวแรก, DC ตัวสอง")
        self.assertEqual(s_dt2, datetime.date(2026, 9, 10))
        self.assertEqual(e_dt2, datetime.date(2026, 9, 20))


if __name__ == "__main__":
    unittest.main()


