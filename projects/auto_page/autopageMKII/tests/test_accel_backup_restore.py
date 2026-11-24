import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openpyxl import Workbook

from functions import accel_mode as am
from functions.accel_mode import AccelMode, is_valid_xlsx


def _write_xlsx(path, marker):
    wb = Workbook()
    ws = wb.active
    ws.title = "Processed_Logs"
    ws["A1"] = marker
    wb.save(path)


def _read_marker(path):
    # openpyxl ปฏิเสธนามสกุล .bak จึงอ่านผ่าน file object
    import io
    from openpyxl import load_workbook
    with open(path, "rb") as f:
        wb = load_workbook(io.BytesIO(f.read()))
    try:
        return wb.active["A1"].value
    finally:
        wb.close()


class BackupRestoreTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="accel_bak_")
        self.path = os.path.join(self.tmpdir, "accel.xlsx")
        self.bak = am.accel_backup_path(self.path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_backup_path_naming(self):
        self.assertEqual(self.bak, self.path + ".bak")

    def test_commit_keeps_previous_version_as_bak(self):
        _write_xlsx(self.path, "OLD")
        tmp = os.path.join(self.tmpdir, ".~accel_tmp.xlsx")
        _write_xlsx(tmp, "NEW")
        AccelMode(None)._commit_with_backup(tmp, self.path)
        self.assertEqual(_read_marker(self.path), "NEW")
        self.assertTrue(is_valid_xlsx(self.bak))
        self.assertEqual(_read_marker(self.bak), "OLD")

    def test_commit_restores_from_bak_when_result_is_invalid(self):
        _write_xlsx(self.path, "OLD")
        tmp = os.path.join(self.tmpdir, ".~accel_tmp.xlsx")
        with open(tmp, "wb") as f:
            f.write(b"not a zip at all")  # จำลองไฟล์ที่เขียนขาดกลางทาง
        with self.assertRaises(OSError):
            AccelMode(None)._commit_with_backup(tmp, self.path)
        self.assertTrue(is_valid_xlsx(self.path))
        self.assertEqual(_read_marker(self.path), "OLD")

    def test_commit_without_existing_file_creates_no_bak(self):
        tmp = os.path.join(self.tmpdir, ".~accel_tmp.xlsx")
        _write_xlsx(tmp, "FIRST")
        AccelMode(None)._commit_with_backup(tmp, self.path)
        self.assertEqual(_read_marker(self.path), "FIRST")
        self.assertFalse(os.path.exists(self.bak))

    def test_restore_when_main_file_corrupt_and_bak_valid(self):
        _write_xlsx(self.bak, "BACKUP")
        with open(self.path, "wb") as f:
            f.write(b"truncated")
        self.assertTrue(am.restore_accel_backup_if_corrupt(self.path))
        self.assertEqual(_read_marker(self.path), "BACKUP")

    def test_no_restore_when_main_file_valid(self):
        _write_xlsx(self.path, "GOOD")
        _write_xlsx(self.bak, "BACKUP")
        self.assertFalse(am.restore_accel_backup_if_corrupt(self.path))
        self.assertEqual(_read_marker(self.path), "GOOD")

    def test_no_restore_when_bak_missing_or_invalid(self):
        with open(self.path, "wb") as f:
            f.write(b"broken")
        self.assertFalse(am.restore_accel_backup_if_corrupt(self.path))
        with open(self.bak, "wb") as f:
            f.write(b"also broken")
        self.assertFalse(am.restore_accel_backup_if_corrupt(self.path))

    def test_no_restore_when_main_file_absent(self):
        _write_xlsx(self.bak, "BACKUP")
        self.assertFalse(am.restore_accel_backup_if_corrupt(self.path))
        self.assertFalse(os.path.exists(self.path))


class SaveFailedNotifyTest(unittest.TestCase):
    def test_callback_fires_once_per_failure_episode(self):
        calls = []
        m = AccelMode(None)
        m.on_save_failed = calls.append
        m._notify_save_failed("p1")
        m._notify_save_failed("p1")
        self.assertEqual(calls, ["p1"])

    def test_callback_error_does_not_propagate(self):
        m = AccelMode(None)

        def boom(_path):
            raise RuntimeError("ui gone")

        m.on_save_failed = boom
        m._notify_save_failed("p")  # ต้องไม่ raise
        self.assertTrue(m._save_fail_notified)

    def test_no_callback_is_safe(self):
        m = AccelMode(None)
        m._notify_save_failed("p")
        self.assertTrue(m._save_fail_notified)


if __name__ == "__main__":
    unittest.main()
