import unittest
import autopage_MKII_ver3_1_1

class TestFunction(unittest.TestCase:
    def test_1(self):
        self.assertEqual(autopage_MKII_ver3_1_1.get_version(), '3.1.1')