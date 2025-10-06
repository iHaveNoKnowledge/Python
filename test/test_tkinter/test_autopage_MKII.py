import unittest
import tempfile
import os
import tkinter as tk
from autopage_MKII_ver3_1_1 import MyApp
from openpyxl import Workbook, load_workbook


class DummyRoot:
    pass


class TestSNExtractor(unittest.TestCase):
    def setUp(self):
        # สร้าง Tk root แต่ไม่โชว์หน้าต่าง
        self.root = tk.Tk()
        self.root.withdraw()  # ซ่อน GUI

        # สร้าง temp Excel file
        tmp_file = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        self.tmp_excel_path = tmp_file.name
        tmp_file.close()

        # Dummy PDF path
        self.dummy_pdf_path = r"C:\Users\BCP_27\Downloads\TRB018324080800011-Tranfer.pdf"

        # สร้าง MyApp instance
        self.app = MyApp(self.root)

    def tearDown(self):
        # ลบ temp Excel file หลัง test
        if os.path.exists(self.tmp_excel_path):
            os.remove(self.tmp_excel_path)

    def test_sn_extractor_runs(self):
        # เรียก sn_extractor
        try:
            self.app.sn_extractor(self.tmp_excel_path, self.dummy_pdf_path)
        except Exception as e:
            self.fail(f"sn_extractor raised an exception: {e}")

        # ตรวจสอบว่าไฟล์ Excel ถูกสร้าง/เขียน (size > 0)
        self.assertTrue(os.path.exists(self.tmp_excel_path))
        self.assertGreater(os.path.getsize(self.tmp_excel_path), 0)


if __name__ == "__main__":
    unittest.main()
    # self.assertFalse(MyApp().sn_extractor("C:\Users\BCP_27\Documents\GitHub\Python\test\tkinter_test\Accel_mode.xlsx", "C:\Users\BCP_27\Downloads\TRB018324080800011-Tranfer.pdf"), '3.1.1')
