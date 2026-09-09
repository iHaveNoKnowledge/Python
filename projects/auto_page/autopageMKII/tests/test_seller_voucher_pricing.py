import os
import sys
import unittest
from unittest.mock import MagicMock

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from functions.pos.pricing_engine import OrderFinancials, POSPricingReconciler
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


if __name__ == "__main__":
    unittest.main()
