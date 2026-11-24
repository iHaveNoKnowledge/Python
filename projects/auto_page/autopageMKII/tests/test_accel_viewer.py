import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openpyxl import Workbook

from functions import accel_viewer as av


_HEADER = list(av.COLUMNS)


def _make_accel(path, rows, sheet=av.SHEET_NAME):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(_HEADER)
    for r in rows:
        ws.append(r)
    wb.save(path)


class LoadProcessedLogsTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="accel_view_")
        self.path = os.path.join(self.tmpdir, "accel.xlsx")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_loads_rows_in_column_order_and_blank_cells_are_empty_strings(self):
        _make_accel(self.path, [
            ["2026-11-11 10:00", "TRK-1", "ORD-1", "B001", "100", "SN1,SN2", "Completed", None, "ok"],
            ["2026-11-11 10:01", "TRK-2", "ORD-2", "B002", "250", "SN3", "Failed", "PRICE_MISMATCH", None],
        ])
        rows = av.load_processed_logs(self.path)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][av.COLUMNS.index("sn")], "SN1,SN2")
        self.assertEqual(rows[0][av.COLUMNS.index("error_category")], "")
        self.assertEqual(rows[1][av.COLUMNS.index("remark")], "")
        self.assertNotIn("nan", [c for r in rows for c in r])

    def test_keeps_leading_zeros_as_text(self):
        _make_accel(self.path, [["t", "TRK", "ORD", "000123", "10", "", "", "", ""]])
        rows = av.load_processed_logs(self.path)
        self.assertEqual(rows[0][av.COLUMNS.index("bill_no")], "000123")

    def test_missing_sheet_raises(self):
        _make_accel(self.path, [], sheet="Other")
        with self.assertRaises(Exception):
            av.load_processed_logs(self.path)


class FilterSortTest(unittest.TestCase):
    ROWS = [
        ["2026-01-02", "TRK-B", "ORD-2", "B002", "300", "SN-X", "Completed", "", "b"],
        ["2026-01-01", "TRK-A", "ORD-1", "B010", "50", "SN-Y", "Failed", "OTHER", "a"],
        ["", "TRK-C", "ORD-3", "", "1000", "", "Completed", "", ""],
    ]

    def test_empty_query_returns_all(self):
        self.assertEqual(len(av.filter_rows(self.ROWS, "")), 3)
        self.assertEqual(len(av.filter_rows(self.ROWS, "   ")), 3)

    def test_query_matches_any_column_case_insensitive(self):
        out = av.filter_rows(self.ROWS, "sn-y")
        self.assertEqual([r[av.COLUMNS.index("orders")] for r in out], ["ORD-1"])

    def test_query_no_match(self):
        self.assertEqual(av.filter_rows(self.ROWS, "zzz"), [])

    def test_numeric_sort_ascending_and_descending(self):
        price = av.COLUMNS.index("price")
        asc = [r[price] for r in av.sort_rows(self.ROWS, price, True)]
        desc = [r[price] for r in av.sort_rows(self.ROWS, price, False)]
        self.assertEqual(asc, ["50", "300", "1000"])
        self.assertEqual(desc, ["1000", "300", "50"])

    def test_empty_values_always_last(self):
        bill = av.COLUMNS.index("bill_no")
        asc = av.sort_rows(self.ROWS, bill, True)
        desc = av.sort_rows(self.ROWS, bill, False)
        self.assertEqual(asc[-1][bill], "")
        self.assertEqual(desc[-1][bill], "")

    def test_text_sort_is_case_insensitive(self):
        status = av.COLUMNS.index("status")
        out = [r[status] for r in av.sort_rows(self.ROWS, status, True)]
        self.assertEqual(out, ["Completed", "Completed", "Failed"])


class CopyTsvTest(unittest.TestCase):
    ROWS = [
        ["a", "b", "c"],
        ["d\te", "f", "g\nh"],
        ["i", "j", "k"],
    ]

    def test_rectangle_is_tab_and_newline_separated(self):
        self.assertEqual(av.cells_to_tsv(self.ROWS, 0, 1, 0, 1), "a\tb\nd e\tf")

    def test_single_cell(self):
        self.assertEqual(av.cells_to_tsv(self.ROWS, 2, 2, 2, 2), "k")

    def test_full_values_are_copied_not_display_truncated(self):
        long_value = "SN" + ",SN" * 60
        rows = [[long_value]]
        self.assertEqual(av.cells_to_tsv(rows, 0, 0, 0, 0), long_value)

    def test_sn_commas_stay_in_one_cell(self):
        rows = [["SN1,SN2,SN3", "next"]]
        tsv = av.cells_to_tsv(rows, 0, 0, 0, 1)
        self.assertEqual(tsv, "SN1,SN2,SN3\tnext")
        self.assertEqual(len(tsv.split("\t")), 2)


class DisplayTest(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(av._display("abc", 10), "abc")

    def test_long_text_truncated_to_fit_column(self):
        out = av._display("x" * 50, 10)
        self.assertLessEqual(len(out), 8)
        self.assertTrue(out.endswith("…"))

    def test_display_strips_tabs_and_newlines(self):
        self.assertEqual(av._display("a\tb\nc", 10), "a b c")


if __name__ == "__main__":
    unittest.main()
