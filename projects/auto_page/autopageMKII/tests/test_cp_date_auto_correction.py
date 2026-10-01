import os
import sys
import pytest
import datetime
import pandas as pd
from unittest.mock import patch, MagicMock

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from functions.pos.pricing_engine import parse_smart_date, parse_smart_datetime, swap_day_month, correct_cp_date_range
from functions.pos.cp_data_loader import DualSourceCPLoader

class TestCPDateAutoCorrection:
    def test_swap_day_month(self):
        # 10th of September (day=10, month=9) -> 9th of October (day=9, month=10)
        d = datetime.date(2026, 9, 10)
        swapped = swap_day_month(d)
        assert swapped == datetime.date(2026, 10, 9)

        # 23rd of September (day=23 > 12) -> None (cannot swap)
        d2 = datetime.date(2026, 9, 23)
        assert swap_day_month(d2) is None

    def test_correct_cp_date_range_iso_utc(self):
        # Case from Google Sheets via GAS: start=23/09/2026, end="2026-09-10T16:59:59.000Z"
        start, end = correct_cp_date_range("23/09/2026 00:00:01", "2026-09-10T16:59:59.000Z")
        assert start == datetime.date(2026, 9, 23)
        assert end == datetime.date(2026, 10, 9)

    def test_correct_cp_date_range_thai_slash(self):
        # start=23/09/2026, end=10/09/2026 (where user entered 09/10/2026)
        start, end = correct_cp_date_range("23/09/2026", "10/09/2026")
        assert start == datetime.date(2026, 9, 23)
        assert end == datetime.date(2026, 10, 9)

    def test_correct_cp_date_range_normal_valid_dates_untouched(self):
        # Normal range 01/09/2026 - 30/09/2026
        start, end = correct_cp_date_range("01/09/2026", "30/09/2026")
        assert start == datetime.date(2026, 9, 1)
        assert end == datetime.date(2026, 9, 30)

    def test_dual_source_cp_loader_cleans_and_swaps(self):
        loader = DualSourceCPLoader(gas_url="", local_excel_path=None)
        raw_df = pd.DataFrame([
            {
                "sku": "SP2-001792+SP2-001793+SP2-001794+SP2-001795",
                "sale_price": "1449",
                "cp_name": "CP2609220007",
                "usage_start_date": "23/09/2026 00:00:01",
                "usage_end_date": "2026-09-10T16:59:59.000Z",
                "suggested_usage_start_date": "23/09/2026 00:00:01",
                "suggested_usage_end_date": "2026-09-10T16:59:59.000Z",
            }
        ])
        cleaned_df = loader._clean_dataframe(raw_df)
        assert len(cleaned_df) == 1
        row = cleaned_df.iloc[0]
        
        # Verify usage_start_date is Sept 23, 2026
        assert row["usage_start_date"].date() == datetime.date(2026, 9, 23)
        # Verify usage_end_date is auto-corrected to Oct 9, 2026
        assert row["usage_end_date"].date() == datetime.date(2026, 10, 9)
        assert row["suggested_usage_end_date"].date() == datetime.date(2026, 10, 9)

    def test_pricing_engine_find_all_cp_candidates_with_string_sale_price(self):
        from functions.pos.pricing_engine import POSPricingReconciler
        mock_app = MagicMock()
        mock_app.cp_gas_url = ""
        mock_app.cp_table_location = ""
        mock_app.correct_sku_pattern.return_value = ["SP2-001792+SP2-001793+SP2-001794+SP2-001795"]
        # DataFrame where sale_price is string '1449' (from API/Excel)
        mock_app.cp_df = pd.DataFrame([
            {
                "sku": "SP2-001792+SP2-001793+SP2-001794+SP2-001795",
                "sale_price": "1449",
                "cp_name": "CP2609220007",
                "usage_start_date": "23/09/2026 00:00:01",
                "usage_end_date": "2026-09-10T16:59:59.000Z",
            }
        ])
        mock_bot = MagicMock()
        mock_bot.app = mock_app
        reconciler = POSPricingReconciler(mock_bot)
        reconciler.reload_cp_if_modified = MagicMock()

        # Should match without TypeError ('str' and 'float') and auto-correct the date
        candidates = reconciler.find_all_cp_candidates_from_excel(
            sku="SP2-001792+SP2-001793+SP2-001794+SP2-001795",
            platform_price=1449.0,
            purchased_date_str="2026-09-28 08:48"
        )
        assert len(candidates) == 1
        assert candidates[0]["cp_name"] == "CP2609220007"

    def test_deduct_accel_file_data_empty_dict_safe(self):
        from functions.accel_mode import AccelMode
        mock_app = MagicMock()
        accel = AccelMode(mock_app)
        accel.accel_df_state = {}  # Empty dict when no file selected
        accel.accel_file_dir = ""

        # Should not throw AttributeError: 'dict' object has no attribute 'columns'
        accel.deduct_accel_file_data("2609287HFYKV3U")

