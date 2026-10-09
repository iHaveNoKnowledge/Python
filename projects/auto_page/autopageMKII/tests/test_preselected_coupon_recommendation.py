import unittest
from unittest.mock import MagicMock, patch
from functions.pos.pricing_engine import POSPricingReconciler


class TestPreselectedCouponRecommendation(unittest.TestCase):
    def setUp(self):
        self.mock_bot = MagicMock()
        self.app = self.mock_bot.app
        self.app.marketplace_target.get.return_value = "Shopee"
        self.app.cus_purchase_time.get.return_value = "2026-09-11 10:00:00"
        self.app.correct_sku_pattern.side_effect = lambda x: [x]
        self.mock_bot.merged_dict = {"SMCO :: เปิดการขาย": "window_handle_smco"}
        self.mock_bot.items = [{"เลขอ้างอิง SKU (SKU Reference No.)": "MNL-002281"}]
        self.app.items = self.mock_bot.items
        self.reconciler = POSPricingReconciler(self.mock_bot)

    def test_find_suggested_cp_without_preselected(self):
        """เมื่อไม่มีคูปองเริ่มต้น ให้แนะนำเฉพาะคูปองใหม่ที่ลดได้ตามเป้าหมาย"""
        self.reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP2608310072", "discount": 500.0, "desc": "Promo 500", "is_selected": False},
            {"code": "CP2608100001", "discount": 200.0, "desc": "Promo 200", "is_selected": False},
        ]
        self.reconciler.last_preselected_smco_coupons = []

        res = self.reconciler.find_suggested_cp_for_discount(500.0)
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "CP2608310072")
        self.assertEqual(res["new_code"], "CP2608310072")
        self.assertEqual(res["preselected_codes"], [])
        self.assertEqual(res["discount"], 500.0)

    def test_find_suggested_cp_combines_with_single_preselected_coupon(self):
        """เมื่อมีคูปองเริ่มต้น (เช่น CP2608280058) ให้รวมเป็น 'CP2608280058 CP2608310072'"""
        self.reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP2608280058", "discount": 200.0, "desc": "Default Promo", "is_selected": True},
            {"code": "CP2608310072", "discount": 300.0, "desc": "Add-on Promo", "is_selected": False},
        ]
        self.reconciler.last_preselected_smco_coupons = ["CP2608280058"]

        res = self.reconciler.find_suggested_cp_for_discount(300.0)
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "CP2608280058 CP2608310072")
        self.assertEqual(res["new_code"], "CP2608310072")
        self.assertEqual(res["preselected_codes"], ["CP2608280058"])
        self.assertEqual(res["discount"], 300.0)

    def test_find_suggested_cp_combines_with_multiple_preselected_coupons(self):
        """เมื่อมีทั้ง Seller Voucher และ Default CP ให้รวมทั้งหมด 'SV_CODE CP_DEFAULT CP_NEW'"""
        self.reconciler.last_scanned_smco_coupon_details = [
            {"code": "SV_260901_100", "discount": 100.0, "desc": "Seller Voucher 100", "is_selected": True},
            {"code": "CP2608280058", "discount": 200.0, "desc": "Default Promo", "is_selected": True},
            {"code": "CP2608310072", "discount": 400.0, "desc": "Add-on Promo", "is_selected": False},
        ]
        self.reconciler.last_preselected_smco_coupons = ["SV_260901_100", "CP2608280058"]

        res = self.reconciler.find_suggested_cp_for_discount(400.0)
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "SV_260901_100 CP2608280058 CP2608310072")
        self.assertEqual(res["preselected_codes"], ["SV_260901_100", "CP2608280058"])
        self.assertEqual(res["new_code"], "CP2608310072")

    def test_find_suggested_cp_avoids_duplicate_preselected_tokens(self):
        """ไม่ใส่รหัสซ้ำหากคูปองใหม่ตรงกับคูปองเริ่มต้น"""
        self.reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP2608310072", "discount": 500.0, "desc": "Promo 500", "is_selected": True},
        ]
        self.reconciler.last_preselected_smco_coupons = ["CP2608310072"]

        res = self.reconciler.find_suggested_cp_for_discount(500.0)
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "CP2608310072")
        self.assertEqual(res["preselected_codes"], [])

    def test_require_seller_voucher_also_prepends_preselected(self):
        """เมื่อค้นหา Seller Voucher หากมีคูปองเริ่มต้น (เช่น CP_DEFAULT หรือ DC...) ให้พ่วงรหัสเริ่มต้นด้วยเสมอ"""
        self.reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP_DEFAULT", "discount": 100.0, "desc": "Default Promo", "is_selected": True},
            {"code": "SV_200", "discount": 200.0, "desc": "Seller Voucher 200.-", "is_selected": False},
        ]
        self.reconciler.last_preselected_smco_coupons = ["CP_DEFAULT"]

        res = self.reconciler.find_suggested_cp_for_discount(200.0, require_seller_voucher=True)
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "CP_DEFAULT SV_200")
        self.assertEqual(res["preselected_codes"], ["CP_DEFAULT"])

    def test_scan_matching_cp_candidates_detects_btn_primary(self):
        """จำลองหน้าเว็บ SMCO ว่าปุ่ม btn-primary ถูกตรวจจับเป็น is_selected=True และลง last_preselected_smco_coupons"""
        mock_driver = MagicMock()
        self.reconciler.driver = mock_driver

        # จำลอง 2 แถวใน modal
        # แถว 1: CP2608280058 (มีปุ่ม btn-primary)
        item1 = MagicMock()
        span_name1 = MagicMock()
        span_name1.text = "CP2608280058"
        item1.find_elements.side_effect = lambda by, xp: (
            [span_name1] if "price-sku-h1" in xp else
            [MagicMock()] if "btn-primary" in xp else
            []
        )
        item1.text = "CP2608280058\nDefault Promo\n200.-"

        # แถว 2: CP2608310072 (มีปุ่ม btn-default ไม่มี btn-primary)
        item2 = MagicMock()
        span_name2 = MagicMock()
        span_name2.text = "CP2608310072"
        item2.find_elements.side_effect = lambda by, xp: (
            [span_name2] if "price-sku-h1" in xp else
            []  # ไม่มี btn-primary
        )
        item2.text = "CP2608310072\nAddon Promo\n300.-"

        mock_driver.execute_script.return_value = ["MNL-002281"]
        cp_btn = MagicMock()
        mock_driver.find_elements.side_effect = lambda by, xp: (
            [cp_btn] if "btn-coupon" in xp else
            [item1, item2] if "list-group-item" in xp else
            [span_name1, span_name2] if "price-sku-h1" in xp else
            []
        )

        with patch.object(self.reconciler, "cp_sonic_blow_process"):
            self.reconciler.scan_matching_cp_candidates_on_smco(item_no=1, cp_candidates=[])

        self.assertEqual(len(self.reconciler.last_scanned_smco_coupon_details), 2)
        self.assertTrue(self.reconciler.last_scanned_smco_coupon_details[0]["is_selected"])
        self.assertFalse(self.reconciler.last_scanned_smco_coupon_details[1]["is_selected"])
        self.assertEqual(self.reconciler.last_preselected_smco_coupons, ["CP2608280058"])

    def test_raise_missing_cp_guide_formats_preselected_message(self):
        """ทดสอบว่า _raise_missing_cp_guide แสดงข้อความแยกคูปองเริ่มต้นและคูปองที่ต้องเลือกเพิ่มอย่างชัดเจน"""
        item = {"ชื่อสินค้า": "Monitor Lenovo", "ราคาขายสุทธิ": "20,555", "ส่วนลดจาก Shopee": "0", "จำนวน": 1}
        suggested_info = {
            "suggested_code": "CP2608280058 CP2608310072",
            "preselected_codes": ["CP2608280058"],
            "new_code": "CP2608310072",
            "discount": 300.0,
            "type": "single"
        }

        logged_messages = []
        self.app.update_log.side_effect = lambda msg: logged_messages.append(msg)

        with self.assertRaises(ValueError):
            self.reconciler._raise_missing_cp_guide(
                item=item,
                sku_key="MNL-002281",
                actual_price=20855.0,
                expected_price=20555.0,
                purchased_date="2026-09-11",
                has_entry=False,
                suggested_cp_info=suggested_info
            )

        full_log = "\n".join(logged_messages)
        self.assertIn("คูปองเริ่มต้นที่ติดมากับสินค้า: 'CP2608280058'", full_log)
        self.assertIn("คูปองที่ต้องเลือกเพิ่ม: 'CP2608310072'", full_log)
        self.assertIn("รหัสรวมที่แนะนำ: 'CP2608280058 CP2608310072'", full_log)

    def test_scan_matching_cp_candidates_detects_auto_and_selected_text(self):
        """จำลองกรณีมีทั้งคูปอง Selected (ปุ่ม) และคูปอง Auto (ไม่มีปุ่ม) บน Modal ของ SMCO"""
        mock_driver = MagicMock()
        self.reconciler.driver = mock_driver

        # แถว 1: DC2410010001 (มีปุ่มข้อความ "Selected")
        item1 = MagicMock()
        span_name1 = MagicMock()
        span_name1.text = "DC2410010001"
        btn1 = MagicMock()
        btn1.text = "Selected"
        btn1.get_attribute.return_value = "btn btn-info"
        item1.find_elements.side_effect = lambda by, xp: (
            [span_name1] if "price-sku-h1" in xp else
            [btn1] if xp == ".//button" or "btn-info" in xp else
            []
        )
        item1.text = "Selected\nDC2410010001\nTopup DC MSI Notebook 2025\n3000.-"

        # แถว 2: DC2507220036 (สถานะ Auto ไม่มีปุ่ม)
        item2 = MagicMock()
        span_name2 = MagicMock()
        span_name2.text = "DC2507220036"
        auto_span = MagicMock()
        auto_span.text = "Auto"
        auto_span.is_displayed.return_value = True
        item2.find_elements.side_effect = lambda by, xp: (
            [span_name2] if "price-sku-h1" in xp else
            [auto_span] if "Auto" in xp or "auto" in xp else
            []
        )
        item2.text = "Auto\nDC2507220036\nTopup NOTEBOOK MSI : BUNDLE MOUSE\n60.-"

        # แถว 3: CP2609100001 (ปุ่ม Un select ยังไม่เลือก)
        item3 = MagicMock()
        span_name3 = MagicMock()
        span_name3.text = "CP2609100001"
        btn3 = MagicMock()
        btn3.text = "Un select"
        btn3.get_attribute.return_value = "btn btn-default"
        item3.find_elements.side_effect = lambda by, xp: (
            [span_name3] if "price-sku-h1" in xp else
            [btn3] if xp == ".//button" or "btn-default" in xp else
            []
        )
        item3.text = "Un select\nCP2609100001\nPromotion MSI Seller Voucher\n500.-"

        mock_driver.execute_script.return_value = ["MNL-002281"]
        cp_btn = MagicMock()
        mock_driver.find_elements.side_effect = lambda by, xp: (
            [cp_btn] if "btn-coupon" in xp else
            [item1, item2, item3] if "list-group-item" in xp else
            [span_name1, span_name2, span_name3] if "price-sku-h1" in xp else
            []
        )

        with patch.object(self.reconciler, "cp_sonic_blow_process"):
            self.reconciler.scan_matching_cp_candidates_on_smco(item_no=1, cp_candidates=[])

        self.assertEqual(len(self.reconciler.last_scanned_smco_coupon_details), 3)
        self.assertTrue(self.reconciler.last_scanned_smco_coupon_details[0]["is_selected"])
        self.assertTrue(self.reconciler.last_scanned_smco_coupon_details[1]["is_selected"])
        self.assertFalse(self.reconciler.last_scanned_smco_coupon_details[2]["is_selected"])
        self.assertEqual(self.reconciler.last_preselected_smco_coupons, ["DC2410010001", "DC2507220036"])

        # เมื่อนำไปคำนวณแนะนำสำหรับ 500 บาท คูปองรวมจะต้องผสมทั้ง DC2410010001 DC2507220036 และ CP2609100001
        res = self.reconciler.find_suggested_cp_for_discount(500.0)
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "DC2410010001 DC2507220036 CP2609100001")
        self.assertEqual(res["preselected_codes"], ["DC2410010001", "DC2507220036"])
        self.assertEqual(res["new_code"], "CP2609100001")

    def test_stale_preselected_coupon_not_in_sku_details_is_ignored(self):
        """ทดสอบว่าคูปองตกค้างจาก SKU อื่น (เช่น CP2609290081) ที่ไม่มีอยู่ใน details ของ SKU ปัจจุบัน จะถูกตัดทิ้ง ไม่ถูกนำมาแนะนำเป็น preselected"""
        # มีคูปองตกค้างใน state
        self.reconciler.last_preselected_smco_coupons = ["CP2609290081"]

        # แต่ SKU ปัจจุบัน (SP2-001748) มีเฉพาะ 4 DC
        self.reconciler.last_scanned_smco_coupon_details = [
            {"code": "DC2609140009", "discount": 100.0, "desc": "Promo 1", "is_selected": False},
            {"code": "DC2609170011", "discount": 150.0, "desc": "Promo 2", "is_selected": False},
            {"code": "DC2609220003", "discount": 200.0, "desc": "Promo 3", "is_selected": False},
            {"code": "DC2609290042", "discount": 250.0, "desc": "Promo 4", "is_selected": False},
        ]

        # ต้องการส่วนลด 250 บาท -> ต้องเลือก DC2609290042 ตัวเดียวเพียวๆ โดยไม่มี CP2609290081 ติดมา
        res = self.reconciler.find_suggested_cp_for_discount(250.0)
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "DC2609290042")
        self.assertEqual(res["preselected_codes"], [])
        self.assertEqual(res["new_code"], "DC2609290042")


    def test_find_suggested_cp_does_not_double_discount_when_new_coupon_matches_full_discount(self):
        """
        กรณี SKU เช่น PR3-000099:
        ราคาฐาน 12,300 บาท ราคาเป้าหมาย 10,238 บาท (ต้องการส่วนลด 2,062 บาท)
        บน SMCO มี Default/Auto CP2609300041 (ลด 1,870) ถูกติ๊กไว้
        และมี CP2610070014 (ลด 2,062) ซึ่งลดได้ครบ 2,062 พอดี
        ระบบต้องเลือก CP2610070014 ตัวเดียว ไม่พ่วง CP2609300041 เข้าไปจนกลายเป็นลด 3,932 (ราคาเหลือ 8,368)
        """
        self.reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP2609300041", "discount": 1870.0, "desc": "Default Auto Coupon", "is_selected": True},
            {"code": "CP2610070014", "discount": 2062.0, "desc": "Specific Promo 2062", "is_selected": False},
        ]
        self.reconciler.last_preselected_smco_coupons = ["CP2609300041"]

        res = self.reconciler.find_suggested_cp_for_discount(2062.0, expected_price=10238.0, sku="PR3-000099")
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "CP2610070014")
        self.assertEqual(res["new_code"], "CP2610070014")
        self.assertEqual(res["preselected_codes"], [])
        self.assertEqual(res["discount"], 2062.0)


    def test_cp_sonic_blow_process_selects_target_and_deselects_unwanted_auto_coupon(self):
        """
        ทดสอบว่า cp_sonic_blow_process:
        - ทำการคลิกปลด (Deselect) คูปอง Auto Top-up (CP2609300041) ที่กำลังเลือกอยู่ (btn-primary / selected) ออก
        - และทำการคลิกเลือก (Select) คูปองเป้าหมาย (CP2610070014) ที่ยังไม่ถูกเลือก (btn-default / unselect)
        """
        mock_driver = MagicMock()
        self.reconciler.driver = mock_driver

        # Coupon 1: CP2609300041 (Auto Top-up / is_selected = True)
        name1 = MagicMock()
        name1.text = "CP2609300041"
        btn1 = MagicMock()
        btn1.get_attribute.return_value = "btn btn-primary"
        btn1.text = "Selected"

        # Coupon 2: CP2610070014 (Target Promo / is_selected = False)
        name2 = MagicMock()
        name2.text = "CP2610070014"
        btn2 = MagicMock()
        btn2.get_attribute.return_value = "btn btn-default"
        btn2.text = "Un select"

        mock_driver.execute_script.return_value = ["MNL-002281"]
        cp_modal_btn = MagicMock()
        agree_btn = MagicMock()

        mock_driver.find_elements.side_effect = lambda by, sel: (
            [cp_modal_btn] if "btn-coupon" in sel else
            [btn1, btn2] if "selectCoupon" in sel else
            [name1, name2] if "price-sku-h1" in sel else
            [agree_btn] if "okCoupon" in sel else
            []  # backdrop empty
        )

        success = self.reconciler.cp_sonic_blow_process(item_no=1, cp_no="CP2610070014")
        self.assertTrue(success)

        # ตรวจสอบว่าทั้ง btn1 (ปลดออก) และ btn2 (เลือกเข้า) ถูกคลิก
        btn1.click.assert_called_once()
        btn2.click.assert_called_once()
        agree_btn.click.assert_called_once()

    def test_process_price_mismatches_diff_positive_applies_cp_instead_of_overcharge(self):
        """
        เมื่อราคาบน SMCO ต่ำกว่าราคาเป้าหมาย (diff > 0 เช่น expected=1128 แต่ actual=1000 เพราะติด Auto Top-up)
        และในตารางมีสูตรคูปอง CP2610000099 สำหรับราคา 1128
        ระบบต้องเลือกคูปอง CP2610000099 (เพื่อปลด Auto Top-up) และต้องไม่ทำการ Overcharge (+128) ซ้ำซ้อน
        """
        sku = "SP2-001414+SP2-001415+SP2-001416+SP2-001417"
        self.app.items = [{"เลขอ้างอิง SKU (SKU Reference No.)": sku}]
        self.mock_bot.items = self.app.items

        # จำลองผลการตรวจราคา: diff = +128.0 (expected 1128, actual 1000)
        verification_result = {
            "price": {
                sku: {
                    "ok": False,
                    "expected": 1128.0,
                    "actual": 1000.0,
                    "diff": 128.0
                }
            }
        }

        # Mock cp_candidates ให้มีสูตรคูปอง CP2610000099
        cand = {
            "sku": sku,
            "sale_price": 1128.0,
            "cp_name": "CP2610000099",
            "oc_amount": "",
            "dc_amount": ""
        }

        with patch.object(self.reconciler, "find_all_cp_candidates_from_excel", return_value=[cand]), \
             patch.object(self.reconciler, "apply_candidate_coupons_if_missing") as mock_apply_cp, \
             patch.object(self.reconciler, "smco_set_overcharge_product") as mock_oc:

            self.reconciler.process_price_mismatches(verification_result)

            # ตรวจสอบว่า apply_candidate_coupons_if_missing ถูกเรียกด้วยคูปอง CP2610000099
            mock_apply_cp.assert_called_once_with(1, sku, "CP2610000099")
            # ตรวจสอบว่าไม่มีการสั่ง Overcharge
            mock_oc.assert_not_called()


if __name__ == "__main__":
    unittest.main()




