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


if __name__ == "__main__":
    unittest.main()
