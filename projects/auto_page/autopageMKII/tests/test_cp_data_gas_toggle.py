import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from tkinter import Tk, BooleanVar

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from functions.pos.cp_data_loader import DualSourceCPLoader


class TestCPDataGASToggle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize Tk instance for BooleanVar if needed
        try:
            cls.tk = Tk()
            cls.tk.withdraw()
        except Exception:
            cls.tk = None

    @classmethod
    def tearDownClass(cls):
        if cls.tk is not None:
            try:
                cls.tk.destroy()
            except Exception:
                pass

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.excel_path = os.path.join(self.tmp_dir.name, "test_cp.xlsx")
        
        # Create a sample local Excel file
        df = pd.DataFrame([
            {
                'sku': 'TEST-SKU-001',
                'marketplace': 'SHOPEE',
                'sale_price': 1000.0,
                'cp_name': 'CP100',
                'suggested_cp': '',
                'oc_amount': '',
                'dc_amount': ''
            }
        ])
        df.to_excel(self.excel_path, index=False)

    def tearDown(self):
        self.tmp_dir.cleanup()

    @patch('requests.get')
    @patch('requests.post')
    def test_default_local_only_mode(self, mock_post, mock_get):
        """When enable_gas_sync=False (default), no network calls to GAS should occur"""
        loader = DualSourceCPLoader(
            gas_url="https://mock-gas.script/exec",
            local_excel_path=self.excel_path,
            enable_gas_sync=False
        )

        self.assertFalse(loader.enable_gas_sync)

        # 1. fetch_from_gas should immediately return empty DataFrame without calling requests.get
        df_gas = loader.fetch_from_gas()
        self.assertTrue(df_gas.empty)
        mock_get.assert_not_called()

        # 2. push_record_to_gas should immediately return False without calling requests.post
        res_push = loader.push_record_to_gas({'sku': 'TEST-SKU-001', 'sale_price': 1000.0})
        self.assertFalse(res_push)
        mock_post.assert_not_called()

        # 3. fetch_conflict_resolver_gas should immediately return empty DataFrame without calling requests.get
        df_conf = loader.fetch_conflict_resolver_gas()
        self.assertTrue(df_conf.empty)
        mock_get.assert_not_called()

        # 4. push_conflict_record should immediately return False without calling requests.post
        res_conf = loader.push_conflict_record({'sku': 'TEST-SKU-001', 'sale_price': 1000.0})
        self.assertFalse(res_conf)
        mock_post.assert_not_called()

        # 5. load_cp_df should read strictly from local excel without calling requests.get
        df_loaded = loader.load_cp_df()
        self.assertEqual(len(df_loaded), 1)
        self.assertEqual(df_loaded.iloc[0]['sku'], 'TEST-SKU-001')
        mock_get.assert_not_called()

    @patch('requests.get')
    @patch('requests.post')
    def test_toggle_to_gas_sync_enabled(self, mock_post, mock_get):
        """When enable_gas_sync is switched to True, network calls to GAS should be permitted"""
        mock_resp_get = MagicMock()
        mock_resp_get.status_code = 200
        mock_resp_get.json.return_value = [
            {'sku': 'CLOUD-SKU-002', 'sale_price': 2000.0, 'cp_name': 'CLOUD200'}
        ]
        mock_get.return_value = mock_resp_get

        mock_resp_post = MagicMock()
        mock_resp_post.status_code = 200
        mock_resp_post.json.return_value = {'status': 'success'}
        mock_post.return_value = mock_resp_post

        loader = DualSourceCPLoader(
            gas_url="https://mock-gas.script/exec",
            local_excel_path=self.excel_path,
            enable_gas_sync=False
        )

        # Switch to True dynamically
        loader.enable_gas_sync = True
        self.assertTrue(loader.enable_gas_sync)

        # Now fetch_from_gas should execute requests.get
        df_gas = loader.fetch_from_gas()
        self.assertEqual(len(df_gas), 1)
        self.assertEqual(df_gas.iloc[0]['sku'], 'CLOUD-SKU-002')
        mock_get.assert_called_once()

        # push_record_to_gas (synchronous) should execute requests.post
        res = loader.push_record_to_gas(
            {'sku': 'NEW-SKU-999', 'sale_price': 999.0},
            is_async=False
        )
        self.assertTrue(res)
        mock_post.assert_called_once()

    def test_reconciler_sync_gas_flag(self):
        """Verify POSPricingReconciler synchronizes enable_gas_sync with app.is_gas_sync_enabled"""
        from functions.pos.pricing_engine import POSPricingReconciler

        class MockApp:
            def __init__(self, excel_path):
                self.cp_table_location = excel_path
                self.cp_gas_url = "https://mock-gas.script/exec"
                self.is_gas_sync_enabled = BooleanVar(value=False)
                self.cp_df = None
                self._cp_last_mtime = 0

        class MockBot:
            def __init__(self, app):
                self.app = app
                self.driver = None

        mock_app = MockApp(self.excel_path)
        mock_bot = MockBot(mock_app)
        reconciler = POSPricingReconciler(mock_bot)

        # Initially, enable_gas_sync should be False
        self.assertFalse(reconciler._is_gas_sync_enabled())
        self.assertFalse(reconciler._dual_cp_loader.enable_gas_sync)

        # Set app flag to True and synchronize
        mock_app.is_gas_sync_enabled.set(True)
        reconciler._sync_dual_loader_gas_flag()
        self.assertTrue(reconciler._is_gas_sync_enabled())
        self.assertTrue(reconciler._dual_cp_loader.enable_gas_sync)

        # Set app flag back to False and synchronize
        mock_app.is_gas_sync_enabled.set(False)
        reconciler._sync_dual_loader_gas_flag()
        self.assertFalse(reconciler._is_gas_sync_enabled())
        self.assertFalse(reconciler._dual_cp_loader.enable_gas_sync)


if __name__ == '__main__':
    unittest.main()
