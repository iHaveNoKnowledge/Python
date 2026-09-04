import os
import sys
import unittest
import importlib.util
from unittest.mock import MagicMock, patch

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

MODULE_PATH = os.path.join(PROJECT_DIR, "autopage_MKII_ver5.x.x.py")
spec = importlib.util.spec_from_file_location("autopage_v5", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["autopage_v5"] = mod
spec.loader.exec_module(mod)

Bot_POS = mod.Bot_POS


class TestCustomerEditInfo(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_driver = MagicMock()
        self.mock_browser = MagicMock()
        self.mock_browser.driver = self.mock_driver
        self.mock_operation_thread = MagicMock()
        self.mock_operation_thread.is_set.return_value = False

        self.mock_app.tax_num.get.return_value = "0105555000000"
        self.mock_app.cus_order = "240904TEST001"

    def test_edit_cus_info_selects_customer_class_when_missing(self):
        """เมื่อ customerClass ยังไม่มี title (ลูกค้าเก่า) ต้องคลิกเปิด dropdown แล้วเลือก CM1 - Domestic Customer"""
        bot = Bot_POS.__new__(Bot_POS)
        bot.app = self.mock_app
        bot.browser = self.mock_browser
        bot.operation_thread = self.mock_operation_thread
        bot.js_input_value = MagicMock()

        edit_btn = MagicMock()
        edit_btn.is_displayed.return_value = True

        class_container = MagicMock()
        titles = {"value": ""}

        def get_attr(attr):
            if attr == "title":
                return titles["value"]
            return ""

        class_container.get_attribute.side_effect = get_attr

        li1 = MagicMock()
        li1.text = "Other Class"
        li2 = MagicMock()
        li2.text = "CM1 - Domestic Customer"

        def on_li2_click():
            titles["value"] = "CM1 - Domestic Customer"

        li2.click.side_effect = on_li2_click

        tax_input = MagicMock()

        mock_wait_inst = MagicMock()
        mock_wait_inst.until.side_effect = [
            class_container,  # presence of class_container
            tax_input         # element_to_be_clickable tax input
        ]

        self.mock_driver.find_element.side_effect = lambda by, val: (
            edit_btn if "btn-default" in str(val)
            else (class_container if "select2-customerClass-container" in str(val) else tax_input)
        )
        self.mock_driver.find_elements.side_effect = lambda by, val: (
            [li1, li2] if "treeitem" in str(val) else []
        )

        with patch.object(mod, "WebDriverWait", return_value=mock_wait_inst), \
             patch.object(mod.time, "sleep"):
            bot.edit_cus_info(incoming_cus_code=12345)

        self.assertEqual(
            bot.current_checkpoint,
            "ปรับแต่งข้อมูลลูกค้า (แก้ไขข้อมูลลูกค้าเดิมที่ชื่อซ้ำใน SMCO)"
        )
        class_container.click.assert_called_once()
        li2.click.assert_called_once()
        bot.js_input_value.assert_called_once_with(tax_input, "0105555000000")

    def test_edit_cus_info_skips_when_customer_class_already_set(self):
        """เมื่อ customerClass มี title เป็น CM1 อยู่แล้ว ต้องไม่กดกาง dropdown ซ้ำ"""
        bot = Bot_POS.__new__(Bot_POS)
        bot.app = self.mock_app
        bot.browser = self.mock_browser
        bot.operation_thread = self.mock_operation_thread
        bot.js_input_value = MagicMock()

        edit_btn = MagicMock()
        edit_btn.is_displayed.return_value = True

        class_container = MagicMock()
        class_container.get_attribute.return_value = "CM1 - Domestic Customer"

        tax_input = MagicMock()

        mock_wait_inst = MagicMock()
        mock_wait_inst.until.side_effect = [
            class_container,
            tax_input
        ]

        self.mock_driver.find_element.side_effect = lambda by, val: (
            edit_btn if "btn-default" in str(val)
            else (class_container if "select2-customerClass-container" in str(val) else tax_input)
        )

        with patch.object(mod, "WebDriverWait", return_value=mock_wait_inst), \
             patch.object(mod.time, "sleep"):
            bot.edit_cus_info(incoming_cus_code=12345)

        class_container.click.assert_not_called()
        bot.js_input_value.assert_called_once_with(tax_input, "0105555000000")

    def test_duplicated_cus_name_resolver_flow_and_save_btn_js_fallback(self):
        """ทดสอบ duplicated_cus_name_resolver เมื่อกดปุ่มบันทึกโดน intercept ให้ fallback ด้วย javascript click"""
        bot = Bot_POS.__new__(Bot_POS)
        bot.app = self.mock_app
        bot.browser = self.mock_browser
        self.mock_browser.merged_dict = {"SMCO :: ลูกค้า": "handle_123"}
        bot.cus_order = "240904TEST001"
        bot.get_tabs = MagicMock()
        bot.direct_to_customer_info = MagicMock()
        bot.edit_cus_info = MagicMock()
        bot.get_cookies_from_driver = MagicMock(return_value={})

        popup_el = MagicMock()
        popup_el.text = "C12345 customer duplicate"

        self.mock_driver.current_url = "https://smco.pos.com/Customer/Index"

        api_res = MagicMock()
        api_res.json.return_value = [{"nameTh": "ชื่อเดิม", "taxId": ""}]
        self.mock_app.smco_api.get_cus_data.return_value = api_res

        save_btn = MagicMock()
        save_btn.click.side_effect = Exception("element click intercepted: Element is not clickable")

        mock_wait_inst = MagicMock()
        mock_wait_inst.until.return_value = save_btn

        with patch.object(mod, "WebDriverWait", return_value=mock_wait_inst), \
             patch.object(mod.time, "sleep"):
            bot.duplicated_cus_name_resolver(popup_el)

        self.assertEqual(
            bot.current_checkpoint,
            "ปรับแต่งข้อมูลลูกค้า (บันทึกข้อมูลลูกค้าที่แก้ไขแล้ว)"
        )
        self.mock_driver.execute_script.assert_any_call("arguments[0].scrollIntoView(true);", save_btn)
        self.mock_driver.execute_script.assert_any_call("arguments[0].click();", save_btn)


if __name__ == "__main__":
    unittest.main()
