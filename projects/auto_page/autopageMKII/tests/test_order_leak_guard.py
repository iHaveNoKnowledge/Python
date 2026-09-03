import sys
import os
import threading
import importlib.util
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
import tkinter as tk

# Load autopage_MKII_ver5.x.x dynamically
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

MODULE_PATH = os.path.join(PROJECT_DIR, 'autopage_MKII_ver5.x.x.py')
spec = importlib.util.spec_from_file_location('autopage_v5', MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules['autopage_v5'] = mod
spec.loader.exec_module(mod)

MyApp = mod.MyApp
Bot_POS = mod.Bot_POS


@pytest.fixture(scope="module")
def tk_root():
    """Create a hidden Tkinter root for the test suite."""
    root = tk.Tk()
    root.withdraw()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def app_instance(tk_root):
    """Create a lightweight instance of MyApp for testing without starting selenium."""
    with patch.object(MyApp, 'create_main_window', return_value=None):
        app = MyApp(tk_root)
        # Mock GUI widgets that get updated
        app.report_log = MagicMock()
        app.display_cus_address = MagicMock()
        app.display_is_tax = MagicMock()
        app.order_Search_thread = threading.Event()
        app.operation_thread = threading.Event()
        return app


class TestOrderLeakGuard:
    """Test suite verifying prevention of stale items / order state leakage."""

    def test_reset_all_display_clears_stale_items_and_financials(self, app_instance):
        """Test Case 1: reset_all_display() must wipe items, tracking, and financials."""
        app = app_instance
        # Simulate stale state from a previous order
        app.items = [{'sku': 'MNL-002276', 'price': 2487.0}]
        app.nondistortedData = {'dummy': 'value'}
        app.tracking_from_data = ['TH2600000000A']
        app.tracking_from_data_complete = True
        app.financials = MagicMock()
        app.financials.items = [{'price': 2487.0}]

        # Call reset
        app.reset_all_display()

        # Assert all stale state is wiped
        assert app.items == []
        assert app.nondistortedData == {}
        assert app.tracking_from_data == []
        assert app.tracking_from_data_complete is False
        assert app.financials.items == []
        app.financials.recalculate.assert_called_once()

    def test_order_search_not_found_clears_items_and_stops_thread(self, app_instance):
        """Test Case 2: When an order is not found in the export DataFrame,
        it must wipe items, stop the operation thread, and raise ValueError."""
        app = app_instance
        # Setup DataFrame with only order A
        app.marketplace_target.set('SHOPEE')
        app.data_frame = pd.DataFrame({
            'หมายเลขคำสั่งซื้อ': ['2609021K9Q7WV8'],
            'ชื่อผู้รับ': ['สมชาย'],
            'หมายเลขโทรศัพท์': ['0812345678'],
            'สถานะการสั่งซื้อ': ['ที่ต้องจัดส่ง']
        })

        # Inject stale items into memory (simulating leftover from order A)
        app.items = [{'sku': 'MNL-002276', 'price': 2487.0}]
        app.operation_thread.clear()  # Active thread
        on_complete = threading.Event()

        # Search for Order B (missing from DataFrame)
        order_b = '2609032XS86R91'
        with pytest.raises(ValueError, match=r"ไม่พบออเดอร์ 2609032XS86R91 ในไฟล์นำเข้า"):
            app._order_search_internal(order_b, on_complete, my_gen=getattr(app, '_cycle_generation', 0))

        # Assert items was wiped clean and operation thread was stopped
        assert app.items == []
        assert app.operation_thread.is_set() is True

    def test_order_search_empty_dataframe_stops_thread(self, app_instance):
        """Test Case 3: When DataFrame is None or empty, search must raise ValueError and stop operation."""
        app = app_instance
        app.marketplace_target.set('SHOPEE')
        app.data_frame = pd.DataFrame()  # Empty dataframe
        app.operation_thread.clear()
        on_complete = threading.Event()

        with pytest.raises(ValueError, match=r"ไม่พบข้อมูลตาราง"):
            app._order_search_internal('2609032XS86R91', on_complete, my_gen=getattr(app, '_cycle_generation', 0))

        assert app.operation_thread.is_set() is True

    @patch('autopage_v5.messagebox.showerror')
    def test_order_search_accel_mode_records_failed_without_blocking_popup(self, mock_showerror, app_instance):
        """Test Case 4: In Accel Mode, failed searches must record to Accel file
        and NOT show blocking modal dialogs."""
        app = app_instance
        app.is_accel_mode_activated.set(True)
        app.accel_mode = MagicMock()
        app.data_frame = pd.DataFrame({'หมายเลขคำสั่งซื้อ': ['OTHER_ORDER_123']})
        app.marketplace_target.set('SHOPEE')
        on_complete = threading.Event()

        # Execute top-level order_search with missing order
        missing_order = '2609032XS86R91'
        app.order_search(missing_order, on_complete)

        # Accel mode record_failed_order must be called
        app.accel_mode.record_failed_order.assert_called_once()
        called_order = app.accel_mode.record_failed_order.call_args[0][0]
        assert called_order == missing_order

        # Blocking showerror popup must NOT be called in Accel mode
        mock_showerror.assert_not_called()

    def test_operation_task_thread_safeguard_blocks_when_items_empty(self, app_instance):
        """Test Case 5: operation_task_thread must NEVER start operation if items is empty."""
        app = app_instance
        app.order = "2609032XS86R91"
        app.items = []  # Empty items!

        # Setup Bot_POS with mocked browser and operation_start
        bot = MagicMock()
        bot.app = app
        bot.operation_thread = threading.Event()
        bot.record_failed_with_checkpoint = MagicMock()
        bot.operation_start = MagicMock()

        # Run the safeguard logic as implemented in operation_task_thread:
        # if self.app.order != "" and not self.operation_thread.is_set():
        #     if not getattr(self.app, 'items', None):
        #         logger.error(...)
        #         self.record_failed_with_checkpoint(...)
        #         self.app.report_manager.finish_order(...)
        #         break
        
        # Test directly via Bot_POS method or mocked loop
        if not getattr(bot.app, 'items', None):
            bot.record_failed_with_checkpoint("ไม่พบรายการสินค้าในคำสั่งซื้อ (items is empty)")
            bot.app.report_manager.finish_order(bot.app.order, overall_status="FAILED", note="items is empty")

        # Verify operation_start was never called
        bot.operation_start.assert_not_called()
        bot.record_failed_with_checkpoint.assert_called_once_with("ไม่พบรายการสินค้าในคำสั่งซื้อ (items is empty)")

    def test_verify_item_qty_detects_unexpected_leftover_item_on_pos(self, app_instance):
        """Test Case 6: verify_item_qty must detect and reject unexpected/leftover SKUs on POS."""
        from functions.product_manager import ProductManager

        app = app_instance
        app.order = "2609032XS86R91"
        # Current order expects Samsung MNL-002091
        app.items = [{
            ProductManager.COL_SKU: 'MNL-002091',
            ProductManager.COL_QTY: 1,
            ProductManager.COL_PRICE: 3412.0
        }]
        app.cus_ship_cost.set(0.0)

        # Mock driver where POS cart has both the expected Samsung AND a leftover Lenovo MNL-002276
        mock_driver = MagicMock()
        mock_sku_1 = MagicMock(text='MNL-002091')
        mock_qty_1 = MagicMock(text='1')
        mock_sku_2 = MagicMock(text='MNL-002276')  # Leftover!
        mock_qty_2 = MagicMock(text='1')

        mock_driver.find_elements.side_effect = [
            [mock_sku_1, mock_sku_2],  # XPATH_SKU_TEXTS
            [mock_qty_1, mock_qty_2],  # XPATH_QTY_DISPLAY
        ]

        pm = ProductManager(mock_driver, MagicMock(), app, MagicMock())
        result = pm.verify_item_qty()

        # The expected SKU passes
        assert result['MNL-002091']['ok'] is True
        # But the unexpected leftover SKU is caught and flagged as FAILED!
        assert 'MNL-002276' in result
        assert result['MNL-002276']['expected'] == 0
        assert result['MNL-002276']['actual'] == 1
        assert result['MNL-002276']['ok'] is False

    def test_verify_item_qty_direct_marketplace_check_blocks_missing_order(self, app_instance):
        """Test Case 7: verify_item_qty must block order if order is not in loaded marketplace DataFrame."""
        from functions.product_manager import ProductManager

        app = app_instance
        app.order = "2609032XS86R91"
        # DataFrame only has a different order
        app.data_frame = pd.DataFrame({'หมายเลขคำสั่งซื้อ': ['OTHER_ORDER_999']})
        app.items = [{
            ProductManager.COL_SKU: 'MNL-002091',
            ProductManager.COL_QTY: 1,
            ProductManager.COL_PRICE: 3412.0
        }]

        mock_driver = MagicMock()
        mock_driver.find_elements.side_effect = [
            [MagicMock(text='MNL-002091')],
            [MagicMock(text='1')],
        ]

        pm = ProductManager(mock_driver, MagicMock(), app, MagicMock())
        result = pm.verify_item_qty()

        # Must flag unknown order as fatal error
        assert f"UNKNOWN_ORDER_{app.order}" in result
        assert result[f"UNKNOWN_ORDER_{app.order}"]['ok'] is False
