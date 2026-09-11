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

    def test_require_seller_voucher_does_not_prepend_preselected(self):
        """เมื่อค้นหา Seller Voucher สำหรับเรื่องที่ 1 ไม่นำ preselected มาพ่วงหน้า"""
        self.reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP_DEFAULT", "discount": 100.0, "desc": "Default Promo", "is_selected": True},
            {"code": "SV_200", "discount": 200.0, "desc": "Seller Voucher 200.-", "is_selected": False},
        ]
        self.reconciler.last_preselected_smco_coupons = ["CP_DEFAULT"]

        res = self.reconciler.find_suggested_cp_for_discount(200.0, require_seller_voucher=True)
        self.assertIsNotNone(res)
        self.assertEqual(res["suggested_code"], "SV_200")
        self.assertEqual(res["preselected_codes"], [])

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


if __name__ == "__main__":
    unittest.main()
