import os
import sys
import unittest
import importlib.util

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(PROJECT_DIR, "autopage_MKII_ver5.x.x.py")
spec = importlib.util.spec_from_file_location("autopage_v5", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["autopage_v5"] = mod
spec.loader.exec_module(mod)


class TestTaxNameFormatting(unittest.TestCase):
    def setUp(self):
        self.app = mod.MyApp.__new__(mod.MyApp)

    def test_typo_jamgud_inversion(self):
        """ทดสอบคำผิดยอดฮิต 'จำกดั' (พิมพ์ ด ก่อน ั) ให้ถูกแปลงเป็น 'จำกัด' และไม่เกิด 'จำกดั จำกัด' เบิ้ลซ้ำ"""
        raw = " บริษัท เวซุน เทคโนโลยี (ประเทศไทย) จำกดั"
        result = self.app.tax_name_formatter(raw)
        self.assertEqual(result, "บริษัท เวซุน เทคโนโลยี (ประเทศไทย) จำกัด")

    def test_already_has_duplicate_jamgud(self):
        """ทดสอบกรณีที่มีทั้งคำผิดและคำถูกเบิ้ลซ้ำ เช่น 'จำกดั จำกัด' ให้ยุบเหลือ 'จำกัด' เดียว"""
        raw = "บริษัท เวซุน เทคโนโลยี (ประเทศไทย) จำกดั จำกัด"
        result = self.app.tax_name_formatter(raw)
        self.assertEqual(result, "บริษัท เวซุน เทคโนโลยี (ประเทศไทย) จำกัด")

    def test_corporate_with_head_office_suffix(self):
        """ทดสอบกรณี บจก. มีคำผิดและมี (สำนักงานใหญ่) พ่วงมาด้วย"""
        raw = "บจก. เวซุน เทคโนโลยี (ประเทศไทย) จำกดั (สำนักงานใหญ่)"
        result = self.app.tax_name_formatter(raw)
        self.assertEqual(result, "บริษัท เวซุน เทคโนโลยี (ประเทศไทย) จำกัด (สำนักงานใหญ่)")

    def test_partnership_typo(self):
        """ทดสอบกรณี หจก. ที่พิมพ์ 'จำกดั'"""
        raw = "หจก. รุ่งเรืองการค้า จำกดั"
        result = self.app.tax_name_formatter(raw)
        self.assertEqual(result, "ห้างหุ้นส่วนจำกัด รุ่งเรืองการค้า")

    def test_public_company_typo(self):
        """ทดสอบกรณี บมจ. ที่พิมพ์ 'จำกดั'"""
        raw = "บมจ. พลังงานไทย จำกดั"
        result = self.app.tax_name_formatter(raw)
        self.assertEqual(result, "บริษัท พลังงานไทย จำกัด (มหาชน)")

    def test_company_typo_prefixes(self):
        """ทดสอบกรณีพิมพ์ 'บริษัท' ผิด เช่น บรัษัท, บรืษัท"""
        raw = "บรัษัท เอสซีจี เทรดดิ้ง จำกัด"
        result = self.app.tax_name_formatter(raw)
        self.assertEqual(result, "บริษัท เอสซีจี เทรดดิ้ง จำกัด")


if __name__ == "__main__":
    unittest.main()
