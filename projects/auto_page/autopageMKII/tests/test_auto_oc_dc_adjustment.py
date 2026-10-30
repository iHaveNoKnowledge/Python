import os
import sys

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from functions.pos.pricing_engine import (
    POSPricingReconciler,
    is_valid_adjustment,
    is_auto_adjustment,
)


class TestAutoOCDCAdjustment(unittest.TestCase):
    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_app = MagicMock()
        self.mock_bot.app = self.mock_app
        self.mock_bot.ProductManager = MagicMock()
        self.reconciler = POSPricingReconciler(self.mock_bot)
        self.reconciler.app = self.mock_app

        # Mock driver
        self.mock_driver = MagicMock()
        self.reconciler.driver = self.mock_driver

    def test_adjustment_helpers(self):
        self.assertTrue(is_auto_adjustment("auto"))
        self.assertTrue(is_auto_adjustment("AUTO"))
        self.assertTrue(is_auto_adjustment("  Auto  "))
        self.assertFalse(is_auto_adjustment("100"))
        self.assertFalse(is_auto_adjustment(""))
        self.assertFalse(is_auto_adjustment(None))

        # "auto" should NOT be treated as a static numeric adjustment
        self.assertFalse(is_valid_adjustment("auto"))
        self.assertFalse(is_valid_adjustment("AUTO"))
        self.assertTrue(is_valid_adjustment("100"))
        self.assertTrue(is_valid_adjustment("50.5"))

    def test_find_all_cp_candidates_retains_auto_adjustment_rows(self):
        # cp_df with SKU, price, cp_name and dc_amount='auto'
        df = pd.DataFrame([{
            'sku': 'MNL-002358',
            'sale_price': 2199.0,
            'cp_name': 'CP2609290086',
            'usage_start_date': '01/10/2026',
            'usage_end_date': '31/10/2026',
            'oc_amount': '',
            'dc_amount': 'auto'
        }])
        self.mock_app.cp_df = df
        self.mock_app.correct_sku_pattern.return_value = ['MNL-002358']

        cands = self.reconciler.find_all_cp_candidates_from_excel('MNL-002358', 2199.0, '15/10/2026')
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]['cp_name'], 'CP2609290086')
        self.assertEqual(cands[0]['dc_amount'], 'auto')

    def test_auto_dc_calculation_per_unit_with_multi_qty(self):
        """
        MNL-002358 expected = 2199.0
        Item Qty = 3
        After coupon, POS actual unit price = 2300.0
        Difference per unit (Qty=1) = 2300 - 2199 = 101.0
        smco_set_discount_product should be called with ('MNL-002358', '101', qty=3)
        cp_data should overwrite 'auto' with '101'
        """
        sku = 'MNL-002358'
        expected_price = 2199.0
        item = {
            'เลขอ้างอิง SKU (SKU Reference No.)': sku,
            'จำนวน': 3
        }
        chosen_cand = {
            'cp_name': 'CP2609290086',
            'oc_amount': '',
            'dc_amount': 'auto'
        }

        # Mock cp_df
        df = pd.DataFrame([{
            'sku': sku,
            'sale_price': expected_price,
            'cp_name': 'CP2609290086',
            'oc_amount': '',
            'dc_amount': 'auto',
            'last_updated': '2026-10-01 00:00:00'
        }])
        self.mock_app.cp_df = df

        # Mock POS verify_item_price returning unit actual = 2300.0
        self.mock_bot.ProductManager.verify_item_price.return_value = {
            sku: {'actual': 2300.0, 'expected': 2199.0, 'diff': -101.0, 'ok': False}
        }
        self.reconciler.apply_candidate_coupons_if_missing = MagicMock(return_value=True)
        self.reconciler.smco_set_discount_product = MagicMock()
        self.reconciler.update_auto_adjustment_in_cp_data = MagicMock(wraps=self.reconciler.update_auto_adjustment_in_cp_data)

        # Execute candidate
        result = self.reconciler.apply_chosen_pricing_candidate(
            item=item,
            sku_key=sku,
            item_no_1indexed=1,
            chosen_cand=chosen_cand,
            expected_price=expected_price,
            purchased_date='15/10/2026'
        )
        self.assertTrue(result)

        # Verify coupon applied
        self.reconciler.apply_candidate_coupons_if_missing.assert_called_once_with(1, sku, 'CP2609290086')

        # Verify DC was set with per-unit amount '101' and qty=3
        self.reconciler.smco_set_discount_product.assert_called_once_with(sku, '101', qty=3)

        # Verify cp_df in-memory updated from 'auto' to '101'
        self.assertEqual(self.mock_app.cp_df.loc[0, 'dc_amount'], '101')
        self.assertEqual(chosen_cand['dc_amount'], '101')

    def test_auto_dc_raises_error_when_pos_lower_than_expected(self):
        """
        If POS price after coupon is 2100.0, which is LOWER than expected 2199.0,
        it cannot apply discount and must raise ValueError without modifying cp_df.
        """
        sku = 'MNL-002358'
        expected_price = 2199.0
        item = {'เลขอ้างอิง SKU (SKU Reference No.)': sku, 'จำนวน': 1}
        chosen_cand = {'cp_name': 'CP2609290086', 'oc_amount': '', 'dc_amount': 'auto'}

        df = pd.DataFrame([{
            'sku': sku,
            'sale_price': expected_price,
            'cp_name': 'CP2609290086',
            'oc_amount': '',
            'dc_amount': 'auto'
        }])
        self.mock_app.cp_df = df

        # POS actual is 2100.0 (lower than 2199.0)
        self.mock_bot.ProductManager.verify_item_price.return_value = {
            sku: {'actual': 2100.0, 'expected': 2199.0, 'diff': 99.0, 'ok': False}
        }
        self.reconciler.apply_candidate_coupons_if_missing = MagicMock(return_value=True)
        self.reconciler.smco_set_discount_product = MagicMock()

        with self.assertRaises(ValueError) as ctx:
            self.reconciler.apply_chosen_pricing_candidate(
                item=item,
                sku_key=sku,
                item_no_1indexed=1,
                chosen_cand=chosen_cand,
                expected_price=expected_price,
                purchased_date='15/10/2026'
            )

        self.assertIn("คูปองลดเกิน", str(ctx.exception))
        # Ensure discount was NOT called
        self.reconciler.smco_set_discount_product.assert_not_called()
        # Ensure 'auto' was NOT overwritten
        self.assertEqual(self.mock_app.cp_df.loc[0, 'dc_amount'], 'auto')

    def test_auto_oc_calculation_per_unit(self):
        """
        MNL-002358 expected = 2199.0
        POS actual unit price = 2100.0
        Candidate has oc_amount='auto'
        Difference = 2199 - 2100 = 99.0
        smco_set_overcharge_product should be called with ('MNL-002358', '99')
        cp_data should overwrite 'auto' with '99'
        """
        sku = 'MNL-002358'
        expected_price = 2199.0
        item = {'เลขอ้างอิง SKU (SKU Reference No.)': sku, 'จำนวน': 2}
        chosen_cand = {'cp_name': '', 'oc_amount': 'auto', 'dc_amount': ''}

        df = pd.DataFrame([{
            'sku': sku,
            'sale_price': expected_price,
            'cp_name': '',
            'oc_amount': 'auto',
            'dc_amount': ''
        }])
        self.mock_app.cp_df = df

        self.mock_bot.ProductManager.verify_item_price.return_value = {
            sku: {'actual': 2100.0, 'expected': 2199.0, 'diff': 99.0, 'ok': False}
        }
        self.reconciler.smco_set_overcharge_product = MagicMock()

        result = self.reconciler.apply_chosen_pricing_candidate(
            item=item,
            sku_key=sku,
            item_no_1indexed=1,
            chosen_cand=chosen_cand,
            expected_price=expected_price,
            purchased_date='15/10/2026'
        )
        self.assertTrue(result)
        self.reconciler.smco_set_overcharge_product.assert_called_once_with(sku, '99')
        self.assertEqual(self.mock_app.cp_df.loc[0, 'oc_amount'], '99')

    def test_auto_oc_raises_error_when_pos_higher_than_expected(self):
        """
        If POS price is 2300.0, which is HIGHER than expected 2199.0,
        it cannot apply overcharge and must raise ValueError.
        """
        sku = 'MNL-002358'
        expected_price = 2199.0
        item = {'เลขอ้างอิง SKU (SKU Reference No.)': sku, 'จำนวน': 1}
        chosen_cand = {'cp_name': '', 'oc_amount': 'auto', 'dc_amount': ''}

        df = pd.DataFrame([{
            'sku': sku,
            'sale_price': expected_price,
            'cp_name': '',
            'oc_amount': 'auto',
            'dc_amount': ''
        }])
        self.mock_app.cp_df = df

        self.mock_bot.ProductManager.verify_item_price.return_value = {
            sku: {'actual': 2300.0, 'expected': 2199.0, 'diff': -101.0, 'ok': False}
        }
        self.reconciler.smco_set_overcharge_product = MagicMock()

        with self.assertRaises(ValueError) as ctx:
            self.reconciler.apply_chosen_pricing_candidate(
                item=item,
                sku_key=sku,
                item_no_1indexed=1,
                chosen_cand=chosen_cand,
                expected_price=expected_price,
                purchased_date='15/10/2026'
            )

        self.assertIn("ไม่สามารถปรับราคาขึ้นได้", str(ctx.exception))
        self.reconciler.smco_set_overcharge_product.assert_not_called()
        self.assertEqual(self.mock_app.cp_df.loc[0, 'oc_amount'], 'auto')


if __name__ == "__main__":
    unittest.main()
