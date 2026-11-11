import os
import sys
import unittest

import pandas as pd

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from functions.cp_pattern_viewer import _canonical_cp, _row_complete

DATES = {"usage_start_date": "2026-11-01", "usage_end_date": "2026-11-30"}


class TestCPPatternComplete(unittest.TestCase):
    def test_cp_name_with_dates_is_complete(self):
        self.assertTrue(_row_complete({"cp_name": "CP2610280012", **DATES}))

    def test_none_cp_name_counts_as_a_discount_method(self):
        self.assertTrue(_row_complete({"cp_name": "NONE", **DATES}))

    def test_oc_amount_without_cp_name_is_complete(self):
        self.assertTrue(_row_complete({"cp_name": None, "oc_amount": 19, **DATES}))

    def test_dc_amount_without_cp_name_is_complete(self):
        self.assertTrue(_row_complete({"cp_name": None, "dc_amount": 12, **DATES}))

    def test_none_cp_name_without_dates_is_incomplete(self):
        self.assertFalse(_row_complete({"cp_name": "NONE"}))

    def test_missing_end_date_is_incomplete(self):
        self.assertFalse(_row_complete({"cp_name": "CP2610280012", "usage_start_date": "2026-11-01"}))

    def test_no_discount_method_is_incomplete(self):
        self.assertFalse(_row_complete({"cp_name": None, "oc_amount": None, "dc_amount": None, **DATES}))

    def test_pandas_missing_values_are_incomplete(self):
        self.assertFalse(_row_complete({"cp_name": pd.NA, "usage_start_date": pd.NaT, "usage_end_date": pd.NaT}))
        self.assertFalse(_row_complete({"cp_name": float("nan"), "oc_amount": float("nan"), **DATES}))

    def test_canonical_none_is_kept_distinct_from_empty(self):
        self.assertEqual(_canonical_cp("NONE"), "NONE")
        self.assertEqual(_canonical_cp(None), "")


if __name__ == "__main__":
    unittest.main()
