import os
import sys
import unittest
from unittest.mock import MagicMock

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from functions.pos.pricing_engine import OrderFinancials, POSPricingReconciler, is_seller_voucher_desc
from functions.product_manager import ProductManager
import pandas as pd



class TestSellerVoucherPricing(unittest.TestCase):
    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_app = MagicMock()
        self.mock_driver = MagicMock()

        self.mock_bot.app = self.mock_app
        self.mock_bot.driver = self.mock_driver
        self.mock_app.cus_ship_cost.get.return_value = 0

    def test_order_financials_single_item_with_seller_voucher(self):
        """กรณีสินค้า 1 ชิ้น ราคา 1,000 บาท มี Seller Voucher 500 บาท -> Expected Price ต้องเป็น 500 บาท"""
        items = [
            {
                "เลขอ้างอิง SKU (SKU Reference No.)": "SKU-SELLER-01",
                "ราคาขายสุทธิ": 1000.0,
                "จำนวน": 1,
                "ส่วนลดจาก Shopee": 0.0,
                "โค้ดส่วนลดชำระโดยผู้ขาย": 500.0,
            }
        ]
        fin = OrderFinancials(
            marketplace="Shopee",
            items=items,
            shipping_cost=45.0,
            seller_voucher=500.0,
        )

        # Expected price for the SKU must be 1000 - 500 = 500
        self.assertEqual(fin.item_expected_prices["SKU-SELLER-01"], 500.0)
        # sum_price is original gross total = 1000
        self.assertEqual(fin.sum_price, 1000.0)
        # total_cart_price on POS cart is discounted item price (500) + shipping (45) = 545
        self.assertEqual(fin.total_cart_price, 545.0)
        # final_billing_price on final page = 1000 + 45 - 500 = 545
        self.assertEqual(fin.final_billing_price, 545.0)

    def test_order_financials_order_level_seller_voucher_fallback(self):
        """กรณีในแถวสินค้าไม่มีคอลัมน์ seller voucher แต่มี order-level seller_voucher = 300"""
        items = [
            {
                "เลขอ้างอิง SKU (SKU Reference No.)": "SKU-CHEAP",
                "ราคาขายสุทธิ": 200.0,
                "จำนวน": 1,
                "ส่วนลดจาก Shopee": 0.0,
            },
            {
                "เลขอ้างอิง SKU (SKU Reference No.)": "SKU-EXPENSIVE",
                "ราคาขายสุทธิ": 1200.0,
                "จำนวน": 1,
                "ส่วนลดจาก Shopee": 0.0,
            }
        ]
        fin = OrderFinancials(
            marketplace="Shopee",
            items=items,
            shipping_cost=0.0,
            seller_voucher=300.0,
        )

        # Voucher should be deducted from the most expensive SKU
        self.assertEqual(fin.item_expected_prices["SKU-CHEAP"], 200.0)
        self.assertEqual(fin.item_expected_prices["SKU-EXPENSIVE"], 900.0)
        self.assertEqual(fin.total_cart_price, 1100.0)

    def test_find_all_cp_candidates_matches_discounted_seller_voucher_price(self):
        """ทดสอบว่า POSPricingReconciler ค้นหา row ที่มี sale_price ตรงกับราคาที่หัก Seller Voucher (เช่น 500 บาท)"""
        # สร้าง mock dataframe สำหรับ cp_data.xlsx
        # มีทั้งราคาปกติ (1000) และราคาที่ผูกกับ CP ของ Seller Voucher (500)
        df_mock = pd.DataFrame([
            {
                "sku": "SKU-SELLER-01",
                "sale_price": 1000.0,
                "usage_start_date": "01/01/2026",
                "usage_end_date": "31/12/2026",
                "cp_name": "1",
                "oc_amount": 0,
                "dc_amount": 0,
            },
            {
                "sku": "SKU-SELLER-01",
                "sale_price": 500.0,
                "usage_start_date": "01/01/2026",
                "usage_end_date": "31/12/2026",
                "cp_name": "4",
                "oc_amount": 0,
                "dc_amount": 0,
            },
        ])

        self.mock_app.cp_df = df_mock
        self.mock_app.correct_sku_pattern.side_effect = lambda x: [x]
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler.reload_cp_if_modified = MagicMock()

        # ถ้าส่ง platform_price = 500.0 (หลังหัก seller voucher)
        candidates_discounted = reconciler.find_all_cp_candidates_from_excel(
            sku="SKU-SELLER-01",
            platform_price=500.0,
            purchased_date_str="15/05/2026"
        )
        self.assertTrue(len(candidates_discounted) > 0)
        self.assertEqual(candidates_discounted[0]["cp_name"], "4")

    def test_product_manager_verifies_with_seller_voucher_financials(self):
        """ทดสอบว่า ProductManager ใช้ item_expected_prices และ total_cart_price จาก OrderFinancials"""
        items = [
            {
                "เลขอ้างอิง SKU (SKU Reference No.)": "SKU-SELLER-01",
                "ราคาขายสุทธิ": 1000.0,
                "จำนวน": 1,
                "ส่วนลดจาก Shopee": 0.0,
                "โค้ดส่วนลดชำระโดยผู้ขาย": 500.0,
            }
        ]
        fin = OrderFinancials(
            marketplace="Shopee",
            items=items,
            shipping_cost=45.0,
            seller_voucher=500.0,
        )

        self.mock_app.items = items
        self.mock_app.financials = fin
        self.mock_app.correct_sku_pattern.side_effect = lambda x: [x]

        pm = ProductManager(self.mock_driver, MagicMock(), self.mock_app, self.mock_bot)

        # Mock driver elements for SKU, Price, Qty on POS
        mock_sku_el = MagicMock(text="SKU-SELLER-01")
        mock_price_el = MagicMock(text="500.00")
        mock_qty_el = MagicMock(text="1")

        def mock_find_elements(by, xpath):
            if xpath == pm.XPATH_SKU_TEXTS:
                return [mock_sku_el]
            elif xpath == pm.XPATH_UNIT_PRICE:
                return [mock_price_el]
            elif xpath == pm.XPATH_QTY_DISPLAY:
                return [mock_qty_el]
            return []

        self.mock_driver.find_elements.side_effect = mock_find_elements

        res = pm.verify_item_price()

        self.assertTrue(res["SKU-SELLER-01"]["ok"])
        self.assertEqual(res["SKU-SELLER-01"]["expected"], 500.0)
        self.assertEqual(res["SKU-SELLER-01"]["actual"], 500.0)

    def test_is_seller_voucher_desc(self):
        """ทดสอบการตรวจจับข้อความ Seller Voucher หลากหลายรูปแบบ"""
        self.assertTrue(is_seller_voucher_desc("Seller Voucher"))
        self.assertTrue(is_seller_voucher_desc("seller voucher 500 บาท"))
        self.assertTrue(is_seller_voucher_desc("คูปองร้านค้า"))
        self.assertTrue(is_seller_voucher_desc("ส่วนลดผู้ขาย (500.-)"))
        self.assertTrue(is_seller_voucher_desc("ส่วนลดร้านค้า"))
        self.assertTrue(is_seller_voucher_desc("Shop Voucher 10%"))
        self.assertTrue(is_seller_voucher_desc("coupon voucher"))
        self.assertTrue(is_seller_voucher_desc("Coupon Voucher 200.-"))

        self.assertFalse(is_seller_voucher_desc("ส่วนลด Shopee"))
        self.assertFalse(is_seller_voucher_desc("Campaign Mega Sale"))
        self.assertFalse(is_seller_voucher_desc(""))
        self.assertFalse(is_seller_voucher_desc(None))

    def test_multi_sku_guard_skips_when_seller_voucher(self):
        """ทดสอบว่าออเดอร์ที่มีหลาย SKU และมี Seller Voucher ในโหมด auto_inv จะถูกข้ามทันทีเพื่อให้ทำแบบ Manual"""
        reconciler = POSPricingReconciler(self.mock_bot)
        self.mock_app.is_auto_invoice_mode.get.return_value = True

        items = [
            {"เลขอ้างอิง SKU (SKU Reference No.)": "SKU-A", "ราคาขายสุทธิ": 500.0, "จำนวน": 1},
            {"เลขอ้างอิง SKU (SKU Reference No.)": "SKU-B", "ราคาขายสุทธิ": 800.0, "จำนวน": 1},
        ]
        fin = OrderFinancials(marketplace="Shopee", items=items, seller_voucher=200.0)
        self.mock_app.items = items
        self.mock_app.financials = fin

        verification_result = {
            "price": {
                "SKU-B": {"ok": False, "diff": -200.0, "expected": 600.0, "actual": 800.0}
            }
        }

        with self.assertRaises(ValueError) as ctx:
            reconciler.process_price_mismatches(verification_result)

        self.assertIn("ออเดอร์มีหลาย SKU", str(ctx.exception))
        self.assertIn("Manual", str(ctx.exception))

    def test_single_sku_seller_voucher_missing_in_cp_data_scans_and_records_suggested_cp(self):
        """ทดสอบว่า Single SKU ที่มี Seller Voucher และยังไม่มีใน cp_data.xlsx จะสแกน SMCO เพื่อบันทึก suggested_cp ลงใน cp_data และหยุดขอวิธีปรับราคา"""
        reconciler = POSPricingReconciler(self.mock_bot)
        self.mock_app.is_auto_invoice_mode.get.return_value = True

        items = [
            {"เลขอ้างอิง SKU (SKU Reference No.)": "SKU-SELLER-SINGLE", "ราคาขายสุทธิ": 1000.0, "จำนวน": 1}
        ]
        fin = OrderFinancials(marketplace="Shopee", items=items, seller_voucher=500.0)
        self.mock_app.items = items
        self.mock_app.financials = fin
        self.mock_app.cus_purchase_time.get.return_value = "01/09/2026"

        # Mock cp_candidates ให้ว่างเปล่า (ไม่พบใน cp_data.xlsx)
        reconciler.find_all_cp_candidates_from_excel = MagicMock(return_value=[])
        reconciler.add_missing_cp_to_excel = MagicMock()
        reconciler.scan_matching_cp_candidates_on_smco = MagicMock()
        reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP_DEFAULT", "discount": 100.0, "desc": "Default Promo", "is_selected": True},
            {"code": "CP2609100001", "discount": 500.0, "desc": "Promotion MSI Seller Voucher 10-30 Sep 2026", "is_selected": False},
        ]
        reconciler.last_preselected_smco_coupons = ["CP_DEFAULT"]

        verification_result = {
            "price": {
                "SKU-SELLER-SINGLE": {"ok": False, "diff": -500.0, "expected": 500.0, "actual": 1000.0}
            }
        }

        with self.assertRaises(ValueError) as ctx:
            reconciler.process_price_mismatches(verification_result)

        self.assertIn("ขอวิธีปรับราคาครับ", str(ctx.exception))
        # บันทึก suggested_cp ที่รวมทั้งคูปองเริ่มต้น และคูปอง Seller Voucher
        reconciler.add_missing_cp_to_excel.assert_called_once_with(
            "SKU-SELLER-SINGLE", 500.0, suggested_cp="CP_DEFAULT CP2609100001"
        )

    def test_scan_matching_cp_candidates_filters_seller_voucher(self):
        """ทดสอบว่า scan_matching_cp_candidates_on_smco กรองเฉพาะ candidate ที่มีคูปอง Seller Voucher ตรงมูลค่า"""
        reconciler = POSPricingReconciler(self.mock_bot)

        # Mock items and correct_sku_pattern
        self.mock_app.items = [{"เลขอ้างอิง SKU (SKU Reference No.)": "SKU-SELLER-01"}]
        self.mock_app.correct_sku_pattern.return_value = ["SKU-SELLER-01"]
        self.mock_bot.merged_dict = {'SMCO :: เปิดการขาย': 'WINDOW_SMCO'}

        # Mock elements on POS panel and Modal
        mock_panel = MagicMock(text="SKU-SELLER-01")
        self.mock_driver.execute_script.return_value = ["SKU-SELLER-01"]

        mock_cp_btn = MagicMock()
        self.mock_driver.find_elements.side_effect = lambda by, selector: (
            [mock_cp_btn] if "btn-coupon" in selector else []
        )

        # จำลอง scanned details จาก SMCO Modal
        # 1. คูปอง CP-CAMPAIGN: ส่วนลด 100 แต่เป็นแคมเปญทั่วไป
        # 2. คูปอง CP-SELLER-500: ส่วนลด 500 เป็น Seller Voucher (ตรงเป้า)
        # 3. คูปอง CP-SELLER-200: ส่วนลด 200 เป็น Seller Voucher (มูลค่าไม่ตรง)
        scanned_details = [
            {"code": "CP-CAMPAIGN", "discount": 100.0, "desc": "แคมเปญ 9.9"},
            {"code": "CP-SELLER-500", "discount": 500.0, "desc": "Seller Voucher 500 บาท"},
            {"code": "CP-SELLER-200", "discount": 200.0, "desc": "Seller Voucher 200 บาท"},
        ]

        cp_candidates = [
            {"cp_name": "CP-CAMPAIGN", "oc_amount": 0, "dc_amount": 0},
            {"cp_name": "CP-SELLER-500", "oc_amount": 0, "dc_amount": 0},
            {"cp_name": "CP-SELLER-200", "oc_amount": 0, "dc_amount": 0},
        ]

        mock_header_names = []
        mock_item_els = []
        for d in scanned_details:
            h_el = MagicMock(text=d["code"])
            h_el.is_displayed.return_value = True
            mock_header_names.append(h_el)

            item_mock = MagicMock()
            n_mock = MagicMock(text=d["code"])
            disc_mock = MagicMock(text=f"{d['discount']:.2f} บาท")
            desc_mock = MagicMock(text=d["desc"])

            def make_item_finder(n, disc, desc):
                def item_find_elements(by, selector):
                    if "price-sku-h1" in selector:
                        return [n]
                    elif "couponDesc" in selector:
                        return [desc]
                    elif "col-xs-12" in selector:
                        return [disc]
                    return []
                return item_find_elements

            item_mock.find_elements.side_effect = make_item_finder(n_mock, disc_mock, desc_mock)
            mock_item_els.append(item_mock)

        def custom_find_elements(by, selector):
            if "btn-coupon" in selector:
                return [mock_cp_btn]
            elif "posbook.data.cnFormPaymentId" in selector and "price-sku-h1" in selector:
                return mock_header_names
            elif "list-group-item" in selector:
                return mock_item_els
            return []

        self.mock_driver.find_elements.side_effect = custom_find_elements

        matched = reconciler.scan_matching_cp_candidates_on_smco(
            item_no=1, cp_candidates=cp_candidates, required_seller_voucher=500.0
        )

        # ต้องเหลือเฉพาะ CP-SELLER-500 เท่านั้น!
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["cp_name"], "CP-SELLER-500")

    def test_seller_voucher_priority_when_initial_diff_positive(self):
        """ทดสอบว่าเมื่อ diff > 0 เริ่มต้น (ราคา POS ต่ำกว่า expected) แต่มี Seller Voucher
        ระบบต้องให้ความสำคัญกับการใส่คูปอง Seller Voucher ก่อน แล้วจึงค่อยพิจารณา Overcharge"""
        reconciler = POSPricingReconciler(self.mock_bot)

        # Mock app financials & auto_inv
        self.mock_app.is_auto_invoice_mode.get.return_value = True
        self.mock_app.cus_seller_voucher.get.return_value = 200.0
        self.mock_app.items = [{
            'เลขอ้างอิง SKU (SKU Reference No.)': 'SKU-PRIORITY-01',
            'ราคาขายสุทธิ': '1000.0',
            'ส่วนลดจาก Shopee': '0',
            'จำนวน': '1'
        }]

        sku_key = 'SKU-PRIORITY-01'
        expected_price = 800.0  # 1000 - 200
        actual_price = 750.0    # POS ต่ำกว่า expected -> diff = +50 > 0

        verification_result = {
            "price": {
                sku_key: {
                    "expected": expected_price,
                    "actual": actual_price,
                    "diff": 50.0,
                    "ok": False
                }
            }
        }

        # Candidate ใน Excel
        reconciler.find_all_cp_candidates_from_excel = MagicMock(return_value=[
            {"cp_name": "CP-SELLER-200", "oc_amount": "250.0", "dc_amount": ""}
        ])

        # Mock find_and_apply_seller_voucher_on_smco ให้ใส่ Seller Voucher สำเร็จ
        reconciler.find_and_apply_seller_voucher_on_smco = MagicMock(return_value=(
            True, "APPLIED", {"code": "CP-SELLER-200", "discount": 200.0}
        ))

        # Mock ProductManager.verify_item_price หลังใส่คูปอง (Phase 2)
        # สมมุติว่าหลังใส่คูปอง ราคา actual กลายเป็น 550.0 -> diff ยังเหลือ +250.0
        self.mock_bot.ProductManager.verify_item_price.return_value = {
            sku_key: {
                "expected": expected_price,
                "actual": 550.0,
                "diff": 250.0,
                "ok": False
            }
        }

        # Mock Overcharge
        reconciler.smco_set_overcharge_product = MagicMock()

        reconciler.process_price_mismatches(verification_result)

        # ตรวจสอบว่า เรื่องที่ 1: มีการเรียกใส่คูปอง Seller Voucher ก่อนเสมอ!
        reconciler.find_and_apply_seller_voucher_on_smco.assert_called_once_with(
            1, 200.0, cp_candidates=[{'cp_name': 'CP-SELLER-200', 'oc_amount': '250.0', 'dc_amount': ''}], require_candidate_match=True
        )

        # ตรวจสอบว่า เรื่องที่ 2: มีการ Overcharge ส่วนต่างที่เหลือ (250 บาท) หลังใส่คูปอง
        reconciler.smco_set_overcharge_product.assert_called_once_with(sku_key, "250.0")

    def test_seller_voucher_priority_followed_by_campaign_cp(self):
        """ทดสอบกรณีแยก 2 เรื่อง: ใส่ Seller Voucher ในเรื่องที่ 1 ก่อน
        แล้วเรื่องที่ 2 (ราคายังสูงกว่า expected) เข้าสู่กระบวนการเลือก Campaign CP เดิมจาก cp_data.xlsx"""
        reconciler = POSPricingReconciler(self.mock_bot)

        self.mock_app.is_auto_invoice_mode.get.return_value = True
        self.mock_app.cus_seller_voucher.get.return_value = 100.0
        self.mock_app.items = [{
            'เลขอ้างอิง SKU (SKU Reference No.)': 'SKU-TWO-STEP-01',
            'ราคาขายสุทธิ': '1000.0',
            'ส่วนลดจาก Shopee': '0',
            'จำนวน': '1'
        }]

        sku_key = 'SKU-TWO-STEP-01'
        expected_price = 700.0  # 1000 - 100 (voucher) - 200 (campaign cp) = 700
        actual_price = 1000.0

        verification_result = {
            "price": {
                sku_key: {
                    "expected": expected_price,
                    "actual": actual_price,
                    "diff": -300.0,
                    "ok": False
                }
            }
        }

        # Candidate แคมเปญใน cp_data.xlsx
        reconciler.find_all_cp_candidates_from_excel = MagicMock(return_value=[
            {"cp_name": "CP-CAMPAIGN-200", "oc_amount": "", "dc_amount": ""}
        ])

        # เรื่องที่ 1: ใส่ Seller Voucher
        reconciler.find_and_apply_seller_voucher_on_smco = MagicMock(return_value=(
            True, "APPLIED", {"code": "CP-SELLER-100", "discount": 100.0}
        ))

        # หลังใส่ Seller Voucher ราคาลดลงเหลือ 900 -> diff = 700 - 900 = -200 (ยังสูงกว่า expected)
        self.mock_bot.ProductManager.verify_item_price.return_value = {
            sku_key: {
                "expected": expected_price,
                "actual": 900.0,
                "diff": -200.0,
                "ok": False
            }
        }

        # เรื่องที่ 2: สแกน Campaign CP บน SMCO เจอ 1 ชุด
        reconciler.scan_matching_cp_candidates_on_smco = MagicMock(return_value=[
            {"cp_name": "CP-CAMPAIGN-200", "oc_amount": "", "dc_amount": ""}
        ])

        reconciler.cp_sonic_blow_process = MagicMock(return_value=True)

        reconciler.process_price_mismatches(verification_result)

        # ตรวจสอบว่า เรื่องที่ 1 ถูกเรียก
        reconciler.find_and_apply_seller_voucher_on_smco.assert_called_once_with(
            1, 100.0, cp_candidates=[{"cp_name": "CP-CAMPAIGN-200", "oc_amount": "", "dc_amount": ""}], require_candidate_match=True
        )

        # ตรวจสอบว่า เรื่องที่ 2 เลือก Campaign CP ต่อ
        reconciler.scan_matching_cp_candidates_on_smco.assert_called_once_with(
            1, [{"cp_name": "CP-CAMPAIGN-200", "oc_amount": "", "dc_amount": ""}], required_seller_voucher=0.0
        )
        reconciler.cp_sonic_blow_process.assert_called_once_with(1, "CP-CAMPAIGN-200")

    def test_raise_missing_cp_guide_shows_price_before_seller_voucher(self):
        """ทดสอบว่าข้อความใน pattern ขอวิธีปรับราคา แสดงราคาขายก่อนหัก Seller Voucher"""
        reconciler = POSPricingReconciler(self.mock_bot)

        # จำลอง OrderFinancials ที่มีราคาขาย 1,200 และมี Seller Voucher 200
        fin = OrderFinancials(
            items=[{
                'เลขอ้างอิง SKU (SKU Reference No.)': 'SKU-GUIDE-01',
                'ราคาขายสุทธิ': '1200.0',
                'ส่วนลดจาก Shopee': '0',
                'จำนวน': '1'
            }],
            seller_voucher=200.0
        )
        self.mock_app.financials = fin
        self.mock_app.marketplace_target.get.return_value = "SHOPEE"
        self.mock_app.cus_purchase_time.get.return_value = "11-09-2026 12:00"

        item = {
            'เลขอ้างอิง SKU (SKU Reference No.)': 'SKU-GUIDE-01',
            'ชื่อสินค้า': 'Test Item Guide',
            'ราคาขายสุทธิ': '1200.0'
        }

        logs = []
        self.mock_app.update_log.side_effect = lambda msg: logs.append(msg)

        with self.assertRaises(ValueError):
            reconciler._raise_missing_cp_guide(
                item=item,
                sku_key='SKU-GUIDE-01',
                actual_price=1000.0,
                expected_price=1000.0,  # 1200 - 200 = 1000 (ราคาหลังหัก voucher)
                purchased_date="11-09-2026",
                has_entry=False
            )

        # ใน logs ต้องมีข้อความ pattern ที่แสดงราคา "ลูกค้าซื้อราคา 1,200.00 บาท" (ก่อนหัก voucher)
        pattern_found = False
        for msg in logs:
            if "ลูกค้าซื้อราคา 1,200.00 บาท" in msg:
                pattern_found = True
                break
        self.assertTrue(pattern_found, f"ไม่พบข้อความ 'ลูกค้าซื้อราคา 1,200.00 บาท' ใน logs: {logs}")

    def test_scan_matching_cp_fallback_to_coupon_detail_remark(self):
        """ทดสอบว่าเมื่อไม่พบข้อความใน couponDesc จะค้นหา fallback จาก couponDetailRemark XPath แทน"""
        reconciler = POSPricingReconciler(self.mock_bot)

        # Mock items, pattern, window dict, and execute_script for panel SKU match
        self.mock_app.items = [{"เลขอ้างอิง SKU (SKU Reference No.)": "SKU-REMARK-01"}]
        self.mock_app.correct_sku_pattern.return_value = ["SKU-REMARK-01"]
        self.mock_bot.merged_dict = {'SMCO :: เปิดการขาย': 'WINDOW_SMCO'}
        self.mock_driver.execute_script.return_value = ["SKU-REMARK-01"]

        mock_cp_btn = MagicMock()
        mock_cp_btn.is_displayed.return_value = True

        cp_candidates = [
            {"cp_name": "CP-REMARK-500", "oc_amount": "", "dc_amount": ""}
        ]

        h_el = MagicMock(text="CP-REMARK-500")
        h_el.is_displayed.return_value = True

        item_mock = MagicMock()
        n_mock = MagicMock(text="CP-REMARK-500")
        disc_mock = MagicMock(text="500.00 บาท")
        remark_mock = MagicMock(text="coupon voucher 500.-")
        general_promo_mock = MagicMock(text="General Campaign Promo")

        def item_find_elements(by, selector):
            if "price-sku-h1" in selector:
                return [n_mock]
            elif "couponDesc" in selector:
                return [general_promo_mock]  # มีข้อความ แต่ไม่ใช่ seller voucher
            elif "couponDetailRemark" in selector:
                return [remark_mock]  # เจอใน fallback couponDetailRemark ว่าเป็น coupon voucher
            elif "col-xs-12" in selector:
                return [disc_mock]
            return []

        item_mock.find_elements.side_effect = item_find_elements

        def custom_find_elements(by, selector):
            if "btn-coupon" in selector:
                return [mock_cp_btn]
            elif "posbook.data.cnFormPaymentId" in selector and "price-sku-h1" in selector:
                return [h_el]
            elif "list-group-item" in selector:
                return [item_mock]
            return []

        self.mock_driver.find_elements.side_effect = custom_find_elements

        matched = reconciler.scan_matching_cp_candidates_on_smco(
            item_no=1, cp_candidates=cp_candidates, required_seller_voucher=500.0
        )

        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["cp_name"], "CP-REMARK-500")
        details = getattr(reconciler, 'last_scanned_smco_coupon_details', [])
        self.assertEqual(len(details), 1)
        self.assertEqual(details[0]["desc"], "coupon voucher 500.-")

    def test_find_suggested_cp_for_discount_selects_latest_coupon(self):
        """ทดสอบว่า find_suggested_cp_for_discount แนะนำคูปองที่มีรหัส/วันที่ใหม่ล่าสุดเสมอเมื่อมีหลายตัวที่ลดได้ตรงกัน"""
        reconciler = POSPricingReconciler(self.mock_bot)

        # จำลองรายละเอียดคูปองที่สแกนได้บน SMCO โดยคูปองเก่า (CP2609070026) อยู่ก่อนคูปองใหม่ (CP2609100001)
        reconciler.last_scanned_smco_coupon_details = [
            {"code": "DC2410010001", "discount": 3000.0, "desc": "DC MSI Notebook 2025"},
            {"code": "DC2507220036", "discount": 60.0, "desc": "BUNDLE MOUSE WISE MT-202"},
            {"code": "CP2609070008", "discount": 500.0, "desc": "Promotion MSI Claw 07 Sep"},
            {"code": "CP2609070026", "discount": 500.0, "desc": "Promotion MSI Seller Voucher 08-15 Sep 2026"},
            {"code": "CP2609100001", "discount": 500.0, "desc": "Promotion MSI Seller Voucher 10-30 Sep 2026"},
        ]

        # ค้นหาคูปองแนะนำสำหรับส่วนลด 500 บาท
        res = reconciler.find_suggested_cp_for_discount(500.0, require_seller_voucher=False)
        self.assertIsNotNone(res)
        # ต้องเลือก CP2609100001 ที่ใหม่กว่า ไม่ใช่ CP2609070026 หรือ CP2609070008 ที่เก่ากว่า
        self.assertEqual(res["suggested_code"], "CP2609100001")
        self.assertEqual(res["discount"], 500.0)

        # หากต้องการเฉพาะ Seller Voucher
        res_sv = reconciler.find_suggested_cp_for_discount(500.0, require_seller_voucher=True)
        self.assertIsNotNone(res_sv)
        self.assertEqual(res_sv["suggested_code"], "CP2609100001")

    def test_find_and_apply_seller_voucher_multi_selects_candidate_match(self):
        """ทดสอบกรณีบน SMCO มี Seller Voucher 500 บาท 2 ตัว แต่ใน cp_candidates ระบุ CP2609100001 -> ต้องเลือก CP2609100001"""
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP2609070026", "discount": 500.0, "desc": "Promotion MSI Seller Voucher 08-15 Sep 2026"},
            {"code": "CP2609100001", "discount": 500.0, "desc": "Promotion MSI Seller Voucher 10-30 Sep 2026"},
        ]
        reconciler.cp_sonic_blow_process = MagicMock(return_value=True)

        candidates = [{"cp_name": "CP2609070007 CP2609070008 CP2609100001", "oc_amount": "2590.0", "dc_amount": ""}]
        ok, status, chosen = reconciler.find_and_apply_seller_voucher_on_smco(1, 500.0, cp_candidates=candidates)

        self.assertTrue(ok)
        self.assertEqual(status, "APPLIED")
        self.assertEqual(chosen["code"], "CP2609100001")
        reconciler.cp_sonic_blow_process.assert_called_once_with(1, "CP2609100001")

    def test_find_and_apply_seller_voucher_multi_falls_back_to_latest(self):
        """ทดสอบกรณีบน SMCO มี Seller Voucher 500 บาท 2 ตัว แต่ใน cp_candidates ไม่ได้ระบุตัวใดเลย -> เลือกรหัสที่ใหม่กว่าเมื่อ require_candidate_match=False"""
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP2609070026", "discount": 500.0, "desc": "Promotion MSI Seller Voucher 08-15 Sep 2026"},
            {"code": "CP2609100001", "discount": 500.0, "desc": "Promotion MSI Seller Voucher 10-30 Sep 2026"},
        ]
        reconciler.cp_sonic_blow_process = MagicMock(return_value=True)

        ok, status, chosen = reconciler.find_and_apply_seller_voucher_on_smco(1, 500.0, cp_candidates=None, require_candidate_match=False)

        self.assertTrue(ok)
        self.assertEqual(status, "APPLIED")
        self.assertEqual(chosen["code"], "CP2609100001")
        reconciler.cp_sonic_blow_process.assert_called_once_with(1, "CP2609100001")

    def test_find_and_apply_seller_voucher_unconfigured_requires_verification(self):
        """ทดสอบว่าเมื่อพบคูปอง Seller Voucher บน SMCO แต่ใน cp_candidates ไม่ได้ระบุไว้ (และ require_candidate_match=True) จะต้องไม่เลือกสุ่มสี่สุ่มห้าและส่งคืน UNCONFIGURED"""
        reconciler = POSPricingReconciler(self.mock_bot)
        reconciler.last_scanned_smco_coupon_details = [
            {"code": "CP2609100001", "discount": 500.0, "desc": "Promotion MSI Seller Voucher 10-30 Sep 2026"},
        ]
        reconciler.cp_sonic_blow_process = MagicMock(return_value=True)

        ok, status, chosen = reconciler.find_and_apply_seller_voucher_on_smco(1, 500.0, cp_candidates=[], require_candidate_match=True)

        self.assertFalse(ok)
        self.assertEqual(status, "UNCONFIGURED")
        self.assertEqual(chosen["code"], "CP2609100001")
        reconciler.cp_sonic_blow_process.assert_not_called()

    def test_overcharge_with_cp_candidate_applies_both_oc_and_cp(self):
        """ทดสอบกรณี diff > 0 (Overcharge) และใน candidate มีทั้ง oc_amount และ cp_name -> ใส่ทั้ง Overcharge และ Campaign CP"""
        reconciler = POSPricingReconciler(self.mock_bot)

        self.mock_app.is_auto_invoice_mode.get.return_value = True
        self.mock_app.cus_seller_voucher.get.return_value = 500.0
        sku_key = 'CO6-011018'
        self.mock_app.items = [{
            'เลขอ้างอิง SKU (SKU Reference No.)': sku_key,
            'ราคาขายสุทธิ': '29020.0',
            'ส่วนลดจาก Shopee': '0',
            'จำนวน': '1'
        }]

        # Expected bill price = 28520.0, POS base = 26430.0
        # Initial verification (before SV applied)
        verification_result = {
            "price": {
                sku_key: {
                    "expected": 28520.0,
                    "actual": 26430.0,
                    "diff": 2090.0,
                    "ok": False
                }
            }
        }

        # Candidates in cp_data.xlsx
        reconciler.find_all_cp_candidates_from_excel = MagicMock(return_value=[
            {"cp_name": "CP2609070007 CP2609070008 CP2609100001", "oc_amount": "2590.0", "dc_amount": ""}
        ])

        # SV step applies CP2609100001 (500 discount)
        # Note: In reality, after SV is applied to POS base 26430, or if OC is 2590: 26430 + 2590 - 500 = 28520.
        reconciler.find_and_apply_seller_voucher_on_smco = MagicMock(return_value=(
            True, "APPLIED", {"code": "CP2609100001", "discount": 500.0}
        ))

        # After SV applied, diff is verified: expected=28520, actual=25930 -> diff = +2590
        self.mock_bot.ProductManager.verify_item_price.side_effect = [
            # 1st call after SV applied
            {sku_key: {"expected": 28520.0, "actual": 25930.0, "diff": 2590.0, "ok": False}},
            # 2nd call after OC and CP applied
            {sku_key: {"expected": 28520.0, "actual": 28520.0, "diff": 0.0, "ok": True}}
        ]

        reconciler.smco_set_overcharge_product = MagicMock()
        reconciler.apply_candidate_coupons_if_missing = MagicMock(return_value=True)

        reconciler.process_price_mismatches(verification_result)

        # Verified that SV was searched and applied with cp_candidates passed
        reconciler.find_and_apply_seller_voucher_on_smco.assert_called_once()
        # Verified that Overcharge 2590.0 was set
        reconciler.smco_set_overcharge_product.assert_called_once_with(sku_key, "2590.0")
        # Verified that apply_candidate_coupons_if_missing was called for the remaining campaign coupons
        reconciler.apply_candidate_coupons_if_missing.assert_called_once_with(
            1, sku_key, "CP2609070007 CP2609070008 CP2609100001"
        )


if __name__ == "__main__":
    unittest.main()




