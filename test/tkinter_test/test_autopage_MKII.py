import unittest
import autopage_MKII_ver3_1_1

class TestFunction(unittest.TestCase):
    def test_1(self):
        self.assertFalse(autopage_MKII_ver3_1_1.MyApp().sn_extractor("C:\Users\BCP_27\Documents\GitHub\Python\test\tkinter_test\Accel_mode.xlsx", "C:\Users\BCP_27\Downloads\TRB018324080800011-Tranfer.pdf"), '3.1.1')