import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock

import pandas as pd

from functions import accel_mode as am
from functions.accel_mode import AccelMode, is_valid_xlsx


def _rows(tag, count=2):
    return [
        {
            "timestamp": f"2026-11-11 10:{i:02d}:00",
            "tracking": f"TRK-{tag}-{i}",
            "orders": f"ORD-{tag}-{i}",
            "bill_no": "B1",
            "price": "100",
            "sn": "SN1",
            "status": "Completed",
            "error_category": "",
            "remark": "ok",
        }
        for i in range(count)
    ]


_LOG_COLS = ["timestamp", "tracking", "orders", "bill_no", "price",
             "sn", "status", "error_category", "remark"]
_FAILED_COLS = ["timestamp", "failed_category", "orders", "failed_reason"]


class AccelSaveAtomicTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="accel_test_")
        self.path = os.path.join(self.tmpdir, "accel.xlsx")
        with pd.ExcelWriter(self.path, engine="openpyxl") as writer:
            pd.DataFrame({"orders": ["ORD-OLD"], "cp": ["NONE"]}).to_excel(
                writer, sheet_name="Sheet1", index=False)
            pd.DataFrame({col: [] for col in _LOG_COLS}).to_excel(
                writer, sheet_name="Processed_Logs", index=False)
        self.obj = AccelMode(None)
        self.obj.accel_file_dir = self.path
        self.obj.main_sheet_name = "Sheet1"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _sheet_names(self):
        with pd.ExcelFile(self.path) as excel:
            return list(excel.sheet_names)

    def test_save_returns_true_and_keeps_other_sheets(self):
        before = self._sheet_names()
        saved = self.obj._save_df_to_excel(pd.DataFrame(_rows("A")), "Processed_Logs")
        self.assertTrue(saved)
        self.assertFalse(self.obj.excel_save_failed)
        self.assertEqual(self._sheet_names(), before)
        self.assertEqual(len(pd.read_excel(self.path, sheet_name="Processed_Logs")), 2)

    def test_no_temp_files_are_left_behind(self):
        self.obj._save_df_to_excel(pd.DataFrame(_rows("B")), "Processed_Logs")
        leftovers = [f for f in os.listdir(self.tmpdir) if f.startswith(".~accel_")]
        self.assertEqual(leftovers, [])

    def test_new_sheet_keeps_position(self):
        self.obj._save_df_to_excel(pd.DataFrame({col: [] for col in _FAILED_COLS}),
                                   "Failed_Orders")
        self.assertEqual(self._sheet_names(),
                         ["Sheet1", "Processed_Logs", "Failed_Orders"])

    def test_corrupt_file_is_not_destroyed(self):
        broken = os.path.join(self.tmpdir, "broken.xlsx")
        with open(broken, "wb") as handle:
            handle.write(b"not a zip")
        self.obj.accel_file_dir = broken

        saved = self.obj._save_df_to_excel(pd.DataFrame(_rows("C")), "Processed_Logs")

        self.assertFalse(saved)
        self.assertTrue(self.obj.excel_save_failed)
        with open(broken, "rb") as handle:
            self.assertEqual(handle.read(), b"not a zip")

    def test_rename_blocked_falls_back_to_direct_write(self):
        with mock.patch.object(AccelMode, "_replace_with_retry",
                               side_effect=PermissionError(32, "in use")):
            saved = self.obj._save_df_to_excel(pd.DataFrame(_rows("R", 3)), "Processed_Logs")

        self.assertTrue(saved)
        self.assertFalse(self.obj.excel_save_failed)
        self.assertTrue(is_valid_xlsx(self.path))
        self.assertEqual(len(pd.read_excel(self.path, sheet_name="Processed_Logs")), 3)

    def test_fully_locked_file_keeps_original_intact(self):
        with open(self.path, "rb") as handle:
            original = handle.read()
        with mock.patch.object(AccelMode, "_commit_temp_file",
                               side_effect=PermissionError(32, "in use")):
            saved = self.obj._save_df_to_excel(pd.DataFrame(_rows("D")), "Processed_Logs")

        self.assertFalse(saved)
        self.assertTrue(self.obj.excel_save_failed)
        with open(self.path, "rb") as handle:
            self.assertEqual(handle.read(), original)
        self.assertTrue(is_valid_xlsx(self.path))

    def test_openpyxl_fallback_used_when_excel_writer_fails(self):
        class BrokenWriter:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("simulated writer failure")

        with mock.patch.object(am.pd, "ExcelWriter", BrokenWriter):
            saved = self.obj._save_df_to_excel(pd.DataFrame(_rows("E", 3)), "Processed_Logs")

        self.assertTrue(saved)
        self.assertTrue(is_valid_xlsx(self.path))
        self.assertEqual(len(pd.read_excel(self.path, sheet_name="Processed_Logs")), 3)

    def test_concurrent_records_do_not_lose_rows(self):
        tags = "WXYZ"
        rounds = 4
        errors = []
        stop = threading.Event()

        def writer(tag):
            for i in range(rounds):
                row = _rows(tag, 1)[0]
                row["orders"] = f"ORD-{tag}-{i}"
                row["tracking"] = f"TRK-{tag}-{i}"
                try:
                    self.obj._record_to_processed_logs([row], f"ORD-{tag}-{i}")
                except Exception as exc:
                    errors.append(f"{tag}{i}: {exc}")

        def reader():
            while not stop.is_set():
                try:
                    with am._ACCEL_FILE_LOCK:
                        pd.read_excel(self.path, sheet_name="Processed_Logs", dtype=str)
                except Exception as exc:
                    errors.append(f"reader: {exc}")

        reader_thread = threading.Thread(target=reader, daemon=True)
        reader_thread.start()
        writers = [threading.Thread(target=writer, args=(tag,)) for tag in tags]
        for thread in writers:
            thread.start()
        for thread in writers:
            thread.join()
        stop.set()
        reader_thread.join(timeout=5)

        self.assertEqual(errors, [])
        written = set(pd.read_excel(self.path, sheet_name="Processed_Logs")["orders"].astype(str))
        expected = {f"ORD-{tag}-{i}" for tag in tags for i in range(rounds)}
        self.assertTrue(expected.issubset(written))
        self.assertTrue(is_valid_xlsx(self.path))


if __name__ == "__main__":
    unittest.main()
