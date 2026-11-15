import os
import sys
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from openpyxl import Workbook

from functions import cp_pattern_viewer as v
from functions.cp_pattern_viewer import (
    filter_pattern_rows,
    filter_sort_price_items,
    filter_sort_sku_items,
    sort_pattern_rows,
)


def _row(excel_row, **kw):
    r = {"_excel_row": excel_row, "sku": "X", "sale_price": 100}
    r.update(kw)
    return r


class TestSortSearchSku(unittest.TestCase):
    SUMMARY = [
        {"sku": "ABC-2", "complete": 1, "prc_patterns": 3},
        {"sku": "ABC-1", "complete": 2, "prc_patterns": 1},
        {"sku": "XYZ-9", "complete": 1, "prc_patterns": 2},
    ]

    def test_search_by_sku_substring_case_insensitive(self):
        out = filter_sort_sku_items(self.SUMMARY, "abc", "sku", True)
        self.assertEqual([it["sku"] for it in out], ["ABC-1", "ABC-2"])

    def test_search_by_column_value(self):
        out = filter_sort_sku_items(self.SUMMARY, "3", "sku", True)
        self.assertEqual([it["sku"] for it in out], ["ABC-2"])

    def test_sort_complete_desc(self):
        out = filter_sort_sku_items(self.SUMMARY, "", "complete", False)
        self.assertEqual([it["sku"] for it in out], ["ABC-1", "ABC-2", "XYZ-9"])

    def test_sort_prc_patterns_numeric(self):
        out = filter_sort_sku_items(self.SUMMARY, "", "prc_patterns", True)
        self.assertEqual([it["prc_patterns"] for it in out], [1, 2, 3])

    def test_empty_query_returns_all_sorted_by_default(self):
        out = filter_sort_sku_items(self.SUMMARY, "  ", "sku", True)
        self.assertEqual(len(out), 3)
        self.assertEqual(out[0]["sku"], "ABC-1")


class TestSortSearchPrice(unittest.TestCase):
    ITEMS = [
        {"price": 993.0, "complete": 0, "patterns": 2},
        {"price": 3144.0, "complete": 1, "patterns": 1},
        {"price": 1056.5, "complete": 0, "patterns": 3},
    ]

    def test_search_price_without_comma(self):
        out = filter_sort_price_items(self.ITEMS, "3144", "price", True)
        self.assertEqual([it["price"] for it in out], [3144.0])

    def test_search_price_with_comma(self):
        out = filter_sort_price_items(self.ITEMS, "3,144", "price", True)
        self.assertEqual([it["price"] for it in out], [3144.0])

    def test_search_matches_complete_count(self):
        out = filter_sort_price_items(self.ITEMS, "0", "price", True)
        self.assertEqual(sorted(it["price"] for it in out), [993.0, 1056.5])

    def test_sort_price_numeric_not_lexical(self):
        out = filter_sort_price_items(self.ITEMS, "", "price", True)
        self.assertEqual([it["price"] for it in out], [993.0, 1056.5, 3144.0])
        out = filter_sort_price_items(self.ITEMS, "", "price", False)
        self.assertEqual([it["price"] for it in out], [3144.0, 1056.5, 993.0])

    def test_sort_patterns_desc(self):
        out = filter_sort_price_items(self.ITEMS, "", "patterns", False)
        self.assertEqual([it["patterns"] for it in out], [3, 2, 1])


class TestSortSearchPatternRows(unittest.TestCase):
    ROWS = [
        _row(2, cp_name="CP2610280012", usage_start_date=datetime(2026, 11, 1),
             usage_end_date=datetime(2026, 11, 30), oc_amount=19, dc_amount=None,
             suggested_remark="ส่วนลด 19"),
        _row(3, cp_name="NONE", usage_start_date=datetime(2026, 10, 1),
             usage_end_date=datetime(2026, 10, 31), oc_amount=None, dc_amount=None,
             suggested_remark="auto"),
        _row(4, cp_name=None, usage_start_date=None, usage_end_date=None,
             oc_amount=None, dc_amount=12, suggested_remark=None),
    ]

    def test_search_matches_cp_and_remark_and_ddmmyyyy(self):
        self.assertEqual([r["_excel_row"] for r in filter_pattern_rows(self.ROWS, "cp2610")], [2])
        self.assertEqual([r["_excel_row"] for r in filter_pattern_rows(self.ROWS, "ส่วนลด")], [2])
        self.assertEqual([r["_excel_row"] for r in filter_pattern_rows(self.ROWS, "01/11/2026")], [2])

    def test_empty_query_returns_all(self):
        self.assertEqual(len(filter_pattern_rows(self.ROWS, "")), 3)

    def test_sort_no_defaults_to_file_order(self):
        out = sort_pattern_rows(list(reversed(self.ROWS)), "no.", True)
        self.assertEqual([r["_excel_row"] for r in out], [2, 3, 4])
        out = sort_pattern_rows(list(self.ROWS), "no.", False)
        self.assertEqual([r["_excel_row"] for r in out], [4, 3, 2])

    def test_sort_cp_asc_empty_last(self):
        out = sort_pattern_rows(list(self.ROWS), "cp", True)
        self.assertEqual([r["_excel_row"] for r in out], [2, 3, 4])

    def test_sort_start_desc_empty_last(self):
        out = sort_pattern_rows(list(self.ROWS), "start", False)
        self.assertEqual([r["_excel_row"] for r in out], [2, 3, 4])

    def test_sort_oc_numeric_desc_empty_last(self):
        out = sort_pattern_rows(list(self.ROWS), "oc", False)
        self.assertEqual([r["_excel_row"] for r in out], [2, 3, 4])

    def test_sort_dc_numeric_asc_empty_last(self):
        out = sort_pattern_rows(list(self.ROWS), "dc", True)
        self.assertEqual([r["_excel_row"] for r in out], [4, 2, 3])


class TestRowsCache(unittest.TestCase):
    HEADER = ["sku", "sale_price", "cp_name", "usage_start_date", "usage_end_date",
              "oc_amount", "dc_amount", "suggested_cp", "suggested_usage_start_date",
              "suggested_usage_end_date", "suggested_oc_amount", "suggested_dc_amount",
              "suggested_remark"]

    def setUp(self):
        v._ROWS_CACHE.clear()

    def tearDown(self):
        v._ROWS_CACHE.clear()

    @staticmethod
    def _write_xlsx(path, data_rows):
        wb = Workbook()
        ws = wb.active
        if ws is None:
            ws = wb.create_sheet()
        ws.title = "Sheet1"
        ws.append(TestRowsCache.HEADER)
        for r in data_rows:
            ws.append(r)
        wb.save(path)

    @staticmethod
    def _row(sku, price):
        return [sku, price, None, None, None, None, None,
                None, None, None, None, None, None]

    def test_read_once_until_file_changes(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "cp.xlsx")
            self._write_xlsx(path, [self._row("SKU-1", 100)])
            app = SimpleNamespace(cp_table_location=path)
            with mock.patch.object(v, "read_cp_rows", wraps=v.read_cp_rows) as spy:
                rows1 = v._sku_price_rows(app, "SKU-1")
                rows2 = v._sku_price_rows(app, "SKU-1")
                self.assertEqual(spy.call_count, 1)
                self.assertEqual(len(rows1), 1)
                self.assertEqual(len(rows2), 1)

                self._write_xlsx(path, [self._row("SKU-1", 100), self._row("SKU-1", 200)])
                st = os.stat(path)
                os.utime(path, (st.st_atime, st.st_mtime + 5))
                rows3 = v._sku_price_rows(app, "SKU-1")
                self.assertEqual(spy.call_count, 2)
                self.assertEqual(len(rows3), 2)

    def test_cached_rows_are_not_polluted_by_price_tag(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "cp.xlsx")
            self._write_xlsx(path, [self._row("SKU-1", 100)])
            app = SimpleNamespace(cp_table_location=path)
            rows1 = v._sku_price_rows(app, "SKU-1")
            self.assertEqual(rows1[0]["_price"], 100.0)
            cached = v._ROWS_CACHE[path]["rows"][0]
            self.assertNotIn("_price", cached)
            rows2 = v._sku_price_rows(app, "SKU-1")
            self.assertEqual(rows2[0]["_price"], 100.0)
            self.assertIsNot(rows2[0], cached)

    def test_force_reload_clears_cache(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "cp.xlsx")
            self._write_xlsx(path, [self._row("SKU-1", 100)])
            app = SimpleNamespace(cp_table_location=path, cp_df=None,
                                  _cp_last_mtime=0,
                                  reload_cp_df_if_modified=lambda: None)
            v._sku_price_rows(app, "SKU-1")
            self.assertIn(path, v._ROWS_CACHE)
            v._force_reload_cp(app)
            self.assertEqual(v._ROWS_CACHE, {})
            self.assertIsNone(v._SUMMARY_CACHE["df"])

    def test_summary_cache_reuses_until_df_or_mtime_changes(self):
        import pandas as pd
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "cp.xlsx")
            self._write_xlsx(path, [])
            df = pd.DataFrame({"sku": ["A", "A"], "sale_price": [100, 200]})
            s1 = v._summarize_cached(df, path)
            s2 = v._summarize_cached(df, path)
            self.assertIs(s1, s2)
            self.assertEqual(len(s1), 1)

            s3 = v._summarize_cached(df.copy(), path)
            self.assertIsNot(s1, s3)

            st = os.stat(path)
            os.utime(path, (st.st_atime, st.st_mtime + 5))
            s4 = v._summarize_cached(df, path)
            self.assertIsNot(s2, s4)

            self.assertEqual(v._summarize_cached(None, path), [])


if __name__ == "__main__":
    unittest.main()
