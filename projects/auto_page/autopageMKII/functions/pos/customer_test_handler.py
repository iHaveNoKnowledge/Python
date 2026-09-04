import os
import re
import time
from typing import Any, Dict, Optional, Tuple
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class CustomerModalTestHandler:
    """
    โมดูลสำหรับทดสอบและตรวจสอบการทำงานของ Modal เพิ่มลูกค้า (Add Customer / saveNewMember)
    บนระบบ SMCO POS:
    1. ตรวจสอบการเปิด Modal และสถานะเริ่มต้นของปุ่มบันทึก (//button[@ng-click='saveNewMember()']) ว่า disabled หรือไม่
    2. กรอกข้อมูล:
       - memNameTh และ memNameEn ด้วยข้อความเดียวกันเสมอ
       - identity (Tax ID)
       - addressCustomer (ที่อยู่ลูกค้า)
       - Dropdowns ที่อยู่: ประเทศ, จังหวัด, อำเภอ/เขต, ตำบล/แขวง, รหัสไปรษณีย์
       - Dropdown ประเภทลูกค้า (Customer Class)
    3. ตรวจสอบค่าหลังกรอก:
       - ตรวจสอบค่าที่ใส่ใน input และ textarea
       - ตรวจสอบ attribute 'title' ของ dropdown ทั้ง 4 ตัวเทียบกับข้อมูลต้นทาง (รองรับ TH / EN)
    4. ตรวจสอบปุ่มบันทึก:
       - ถ้า attribute disabled หายไป และข้อมูลตรงทั้งหมด -> PASS
       - ถ้า disabled ยังอยู่ หรือข้อมูลไม่ตรง -> FAIL พร้อมระบุรายละเอียดข้อผิดพลาด
    5. บันทึกผลการทดสอบลงใน TestReportManager และ export ไฟล์ Excel
    """

    # XPath constants ตามที่ระบุในข้อกำหนด
    SAVE_BTN_XPATH = "//button[@ng-click='saveNewMember()']"
    CANCEL_BTN_XPATH = "/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[1]/div[4]/button[2]"
    NAME_TH_XPATH = "//input[@id='memNameTh']"
    NAME_EN_XPATH = "//input[@id='memNameEn']"
    ADDRESS_XPATH = "//textarea[@id='addressCustomer']"
    IDENTITY_XPATH = "//input[@id='identity']"

    PROVINCE_CONTAINER_XPATH = "//span[@id='select2-province-container']"
    DISTRICT_CONTAINER_XPATH = "//span[@id='select2-district-container']"
    SUBDISTRICT_CONTAINER_XPATH = "//span[@id='select2-subDistrict-container']"
    ZIP_CONTAINER_XPATH = "//span[@id='select2-zipCodeSel-container']"

    def __init__(self, bot: Any):
        self.bot = bot
        self.app = bot.app
        self.driver = bot.driver
        self.wait50 = bot.wait50

    def clean_place_name(self, text: str) -> str:
        """ตัดคำนำหน้าภาษาไทย เช่น จังหวัด, อำเภอ, เขต, ตำบล, แขวง, อ., ต. ออกเพื่อให้เทียบได้แม่นยำ"""
        if not text:
            return ""
        cleaned = text.strip()
        cleaned = cleaned.replace("จังหวัด", "")
        cleaned = cleaned.replace("อำเภอ", "").replace("เขต", "").replace("อ.", "")
        cleaned = cleaned.replace("ตำบล", "").replace("แขวง", "").replace("ต.", "")
        return cleaned.strip()

    def match_place_value(self, actual_title: str, expected_value: str, place_type: str = "") -> bool:
        """
        ตรวจสอบว่าค่าที่อ่านได้จาก dropdown (actual_title) ตรงกับค่าที่คาดหวัง (expected_value) หรือไม่
        รองรับทั้งภาษาไทยและภาษาอังกฤษ
        """
        if not actual_title or not expected_value:
            return False

        act = self.clean_place_name(actual_title).lower()
        exp = self.clean_place_name(expected_value).lower()

        # 1. เทียบตรงๆ แบบไม่สน case และไม่สนคำนำหน้า
        if act == exp or exp in act or act in exp:
            return True

        # 2. ถ้าใน bot มีตารางแปลสถานที่ (translate_eng_to_thai_place) ให้ลองแปลเพื่อเทียบ
        if hasattr(self.bot, 'translate_eng_to_thai_place') and place_type:
            try:
                # ลองแปลง exp เป็นภาษาไทยถ้าเป็นอังกฤษ
                translated_exp = self.bot.translate_eng_to_thai_place(exp, place_type)
                clean_trans_exp = self.clean_place_name(translated_exp).lower()
                if act == clean_trans_exp or clean_trans_exp in act or act in clean_trans_exp:
                    return True

                # ลองแปลง act เป็นภาษาไทยถ้า act เป็นอังกฤษ
                translated_act = self.bot.translate_eng_to_thai_place(act, place_type)
                clean_trans_act = self.clean_place_name(translated_act).lower()
                if exp == clean_trans_act or clean_trans_act in exp or exp in clean_trans_act:
                    return True
            except Exception as e:
                logger.debug(f"[CustomerModalTestHandler] translation error during match: {e}")

        return False

    def is_save_button_disabled(self) -> Tuple[bool, str]:
        """
        ตรวจสอบปุ่ม saveNewMember ว่ามี attribute disabled หรือไม่
        Returns: (is_disabled, disabled_attr_value)
        """
        try:
            save_btn = self.driver.find_element(By.XPATH, self.SAVE_BTN_XPATH)
            disabled_attr = save_btn.get_attribute("disabled")
            is_enabled = save_btn.is_enabled()
            # ถ้ามี attribute disabled (เช่น "disabled" หรือ "true") หรือ is_enabled() == False
            if disabled_attr is not None or not is_enabled:
                return True, str(disabled_attr)
            return False, ""
        except Exception as e:
            logger.warning(f"[CustomerModalTestHandler] ไม่พบปุ่ม saveNewMember หรือ error: {e}")
            return True, f"Error finding save button: {e}"

    def get_form_field_value(self, xpath: str) -> str:
        """อ่านค่า value จาก input หรือ textarea"""
        try:
            el = self.driver.find_element(By.XPATH, xpath)
            val = el.get_attribute("value")
            return val.strip() if val else ""
        except Exception:
            return ""

    def get_dropdown_title(self, xpath: str) -> str:
        """อ่านค่า attribute title หรือ text จาก span container ของ dropdown"""
        try:
            el = self.driver.find_element(By.XPATH, xpath)
            title = el.get_attribute("title")
            if title:
                return title.strip()
            # fallback เป็น inner text
            return el.text.strip()
        except Exception:
            return ""

    def close_modal(self):
        """ปิดหน้าต่าง modal เพิ่มลูกค้า คืนสถานะหน้าจอเดิม"""
        try:
            # 1. กดปุ่ม Cancel
            cancel_btn = self.driver.find_element(By.XPATH, self.CANCEL_BTN_XPATH)
            cancel_btn.click()
            time.sleep(0.5)
            return
        except Exception:
            pass

        try:
            # 2. ปิดด้วยปุ่ม Cancel แบบ ng-click
            self.driver.execute_script("document.querySelector('button[ng-click=\"cancel()\"]').click();")
            time.sleep(0.5)
            return
        except Exception:
            pass

        try:
            # 3. ส่งปุ่ม Escape
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.5)
        except Exception:
            pass

    def run_test(
        self,
        customer_data: Optional[Dict[str, Any]] = None,
        close_modal_after_test: bool = True
    ) -> Dict[str, Any]:
        """
        รันการทดสอบ Add Customer Modal ตาม Flow ที่ระบุ:
        1. เปิด Customer Form
        2. เช็ค initial state ของปุ่ม saveNewMember (ต้องมี disabled="disabled")
        3. กรอกค่าลงในฟอร์ม:
           - memNameTh และ memNameEn ต้องเป็นค่าเดียวกันเสมอ
           - identity (Tax ID)
           - addressCustomer (ที่อยู่ลูกค้า)
           - dropdowns จังหวัด, อำเภอ, ตำบล, รหัสไปรษณีย์
        4. เช็คค่าหลังกรอกเทียบกับข้อมูลต้นทาง
        5. เช็คว่า disabled="disabled" หลุดหายไปหรือไม่
        6. สรุปผล PASS / FAIL และบันทึกลงใน report

        Returns: Dict สรุปผลการทดสอบ
        """
        # 1. ดึงข้อมูลลูกค้าหากไม่ได้ส่งเข้ามาตรงๆ
        if not customer_data:
            customer_data = self._gather_customer_data_from_app()

        order_id = (
            (customer_data.get("order_id") if customer_data else None)
            or getattr(self.bot, 'cus_order', "")
            or (self.app.cus_order.get() if hasattr(self.app, 'cus_order') else "")
            or "TEST_ORDER_MODAL"
        )
        logger.info(f"[CustomerModalTestHandler] เริ่มต้นการทดสอบ Add Customer Modal สำหรับ Order: {order_id}")

        test_result = {
            "order_id": str(order_id),
            "initial_disabled_check": False,
            "name_th_match": False,
            "name_en_match": False,
            "names_identical": False,
            "identity_match": False,
            "address_match": False,
            "province_match": False,
            "district_match": False,
            "subdistrict_match": False,
            "zip_match": False,
            "save_btn_disabled_removed": False,
            "passed": False,
            "fail_reasons": [],
            "details": {}
        }

        name = customer_data.get("name", "").strip()
        tax_id = customer_data.get("tax_id", "").strip()
        address = customer_data.get("address", "").strip()
        province = customer_data.get("province", "").strip()
        district = customer_data.get("district", "").strip()
        sub_district = customer_data.get("sub_district", "").strip()
        postcode = customer_data.get("postcode", "").strip()

        logger.info(
            f"[CustomerModalTestHandler] ข้อมูลทดสอบ -> ชื่อ: '{name}', Tax ID: '{tax_id}', "
            f"ที่อยู่: '{address}', {province} / {district} / {sub_district} / {postcode}"
        )

        try:
            # 2. ตรวจสอบว่าแท็บเปิดการขายพร้อมหรือไม่ และเปิด Customer Form
            is_functionworking = True
            if hasattr(self.bot, 'open_customer_form'):
                self.bot.open_customer_form(is_functionworking)
            else:
                # Fallback: ค้นหาและกดปุ่มสร้างลูกค้า
                btn = self.driver.find_element(By.CSS_SELECTOR, getattr(self.app, 'cusCreateBtn', 'button#newMember'))
                btn.click()
                time.sleep(1)

            time.sleep(0.5)

            # 3. ตรวจสอบสถานะเริ่มต้นของปุ่ม saveNewMember ว่ามี disabled อยู่จริง
            init_disabled, init_attr = self.is_save_button_disabled()
            test_result["initial_disabled_check"] = init_disabled
            test_result["details"]["initial_save_button_disabled"] = init_attr or "disabled"
            if not init_disabled:
                test_result["fail_reasons"].append(
                    "เมื่อเปิดหน้าต่างสร้างลูกค้า ปุ่ม saveNewMember ไม่มี attribute disabled='disabled' ตามที่คาดหวัง"
                )

            # 4. กรอกชื่อภาษาไทยและอังกฤษ (ต้องใช้ค่าเดียวกันเสมอ)
            name_th_el = self.driver.find_element(By.XPATH, self.NAME_TH_XPATH)
            self.bot.js_input_value(name_th_el, name)

            name_en_el = self.driver.find_element(By.XPATH, self.NAME_EN_XPATH)
            self.bot.js_input_value(name_en_el, name)

            # 5. กรอก Tax ID (identity)
            if tax_id:
                tax_el = self.driver.find_element(By.XPATH, self.IDENTITY_XPATH)
                self.bot.js_input_value(tax_el, tax_id)

            # 6. กรอกที่อยู่ (addressCustomer)
            if address:
                addr_el = self.driver.find_element(By.XPATH, self.ADDRESS_XPATH)
                self.bot.js_input_value(addr_el, address)

            # 7. ดำเนินการเลือก Dropdowns ผ่านกลไกของบอท
            # เลือก Country (Thailand)
            try:
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[10]/div[1]/div/span/span[1]/span'
                ).click()
                if hasattr(self.bot, 'dropdown_handler'):
                    self.bot.dropdown_handler()
                try:
                    self.driver.find_element(By.XPATH, "//li[text()='Thailand' or text()='ไทย']").click()
                except Exception:
                    self.driver.find_element(By.XPATH, "/html/body/div[2]/div[3]/div[13]/span/span/span[2]/ul/li[2]").click()
            except Exception as c_err:
                logger.debug(f"[CustomerModalTestHandler] Country dropdown select note: {c_err}")

            # Province
            if province and hasattr(self.bot, '_select_dropdown_or_fail_in_auto_inv'):
                try:
                    prov_btn = self.driver.find_element(By.CSS_SELECTOR, 'span #select2-province-container')
                    prov_btn.click()
                    prov_input = self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input')
                    self.bot._select_dropdown_or_fail_in_auto_inv(
                        source="test add customer modal",
                        input_element=prov_input,
                        search_value=self.clean_place_name(province),
                        th_field='provinceNameTh',
                        en_field='provinceNameEn',
                        place_type='province'
                    )
                except Exception as p_err:
                    test_result["fail_reasons"].append(f"เลือก Dropdown จังหวัด ({province}) ไม่สำเร็จ: {p_err}")

            # District
            if district and hasattr(self.bot, '_select_dropdown_or_fail_in_auto_inv'):
                try:
                    dist_btn = self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[12]/div[1]/div/span/span[1]/span/span[1]'
                    )
                    dist_btn.click()
                    dist_input = self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input')
                    self.bot._select_dropdown_or_fail_in_auto_inv(
                        source="test add customer modal",
                        input_element=dist_input,
                        search_value=self.clean_place_name(district),
                        th_field='districtNameTh',
                        en_field='districtNameEn',
                        place_type='district'
                    )
                except Exception as d_err:
                    test_result["fail_reasons"].append(f"เลือก Dropdown อำเภอ/เขต ({district}) ไม่สำเร็จ: {d_err}")

            # SubDistrict
            if sub_district and hasattr(self.bot, '_select_dropdown_or_fail_in_auto_inv'):
                try:
                    sub_btn = self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[12]/div[3]/div/span/span[1]/span/span[1]'
                    )
                    sub_btn.click()
                    sub_btn.click()
                    sub_btn.click()
                    sub_input = self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input')
                    self.bot._select_dropdown_or_fail_in_auto_inv(
                        source="test add customer modal",
                        input_element=sub_input,
                        search_value=self.clean_place_name(sub_district),
                        th_field='subdistrictNameTh',
                        en_field='subdistrictNameEn',
                        place_type='subdistrict'
                    )
                except Exception as sd_err:
                    test_result["fail_reasons"].append(f"เลือก Dropdown ตำบล/แขวง ({sub_district}) ไม่สำเร็จ: {sd_err}")

            # Zip code
            if postcode:
                try:
                    zip_container = self.driver.find_element(By.XPATH, self.ZIP_CONTAINER_XPATH)
                    curr_zip_title = zip_container.get_attribute("title")
                    if str(postcode) not in str(curr_zip_title):
                        zip_container.click()
                        if hasattr(self.bot, 'dropdown_handler'):
                            self.bot.dropdown_handler()
                        self.driver.find_element(By.XPATH, f"//li[@role='treeitem' and text()='{postcode}']").click()
                except Exception as z_err:
                    logger.debug(f"[CustomerModalTestHandler] Postal code selection note: {z_err}")

            # Customer Class
            if hasattr(self.bot, 'customer_class_selector'):
                try:
                    self.bot.customer_class_selector(is_functionworking)
                except Exception as cc_err:
                    logger.debug(f"[CustomerModalTestHandler] Customer class selection note: {cc_err}")

            time.sleep(0.5)

            # 8. ตรวจสอบความถูกต้องของข้อมูลหลังกรอก
            # 8.1 ตรวจสอบชื่อ TH / EN
            actual_name_th = self.get_form_field_value(self.NAME_TH_XPATH)
            actual_name_en = self.get_form_field_value(self.NAME_EN_XPATH)
            test_result["details"]["name_th_actual"] = actual_name_th
            test_result["details"]["name_en_actual"] = actual_name_en
            test_result["details"]["name_expected"] = name

            if actual_name_th == name:
                test_result["name_th_match"] = True
            else:
                test_result["fail_reasons"].append(f"ชื่อภาษาไทย (memNameTh) ไม่ตรง: พบ '{actual_name_th}' แต่คาดหวัง '{name}'")

            if actual_name_en == name:
                test_result["name_en_match"] = True
            else:
                test_result["fail_reasons"].append(f"ชื่อภาษาอังกฤษ (memNameEn) ไม่ตรง: พบ '{actual_name_en}' แต่คาดหวัง '{name}'")

            if actual_name_th == actual_name_en and actual_name_th != "":
                test_result["names_identical"] = True
            else:
                test_result["fail_reasons"].append(f"ชื่อ memNameTh และ memNameEn ต้องเป็นค่าเดียวกันเสมอ แต่ค่าไม่ตรงกัน")

            # 8.2 ตรวจสอบ Tax ID (identity)
            if tax_id:
                actual_tax = self.get_form_field_value(self.IDENTITY_XPATH)
                test_result["details"]["tax_actual"] = actual_tax
                test_result["details"]["tax_expected"] = tax_id
                if actual_tax == tax_id:
                    test_result["identity_match"] = True
                else:
                    test_result["fail_reasons"].append(f"Tax ID (identity) ไม่ตรง: พบ '{actual_tax}' แต่คาดหวัง '{tax_id}'")
            else:
                test_result["identity_match"] = True  # ไม่จำเป็นต้องตรวจถ้าไม่มี tax_id

            # 8.3 ตรวจสอบ Address
            if address:
                actual_address = self.get_form_field_value(self.ADDRESS_XPATH)
                test_result["details"]["address_actual"] = actual_address
                test_result["details"]["address_expected"] = address
                if actual_address == address:
                    test_result["address_match"] = True
                else:
                    test_result["fail_reasons"].append(f"ที่อยู่ (addressCustomer) ไม่ตรง: พบ '{actual_address}' แต่คาดหวัง '{address}'")
            else:
                test_result["address_match"] = True

            # 8.4 ตรวจสอบ Dropdown Titles (Province, District, SubDistrict, Zip)
            actual_prov = self.get_dropdown_title(self.PROVINCE_CONTAINER_XPATH)
            actual_dist = self.get_dropdown_title(self.DISTRICT_CONTAINER_XPATH)
            actual_subdist = self.get_dropdown_title(self.SUBDISTRICT_CONTAINER_XPATH)
            actual_zip = self.get_dropdown_title(self.ZIP_CONTAINER_XPATH)

            test_result["details"]["province_title"] = actual_prov
            test_result["details"]["district_title"] = actual_dist
            test_result["details"]["subdistrict_title"] = actual_subdist
            test_result["details"]["zip_title"] = actual_zip

            if province:
                if self.match_place_value(actual_prov, province, "province"):
                    test_result["province_match"] = True
                else:
                    test_result["fail_reasons"].append(f"Dropdown จังหวัด title ไม่ตรง: พบ '{actual_prov}' แต่คาดหวัง '{province}'")
            else:
                test_result["province_match"] = True

            if district:
                if self.match_place_value(actual_dist, district, "district"):
                    test_result["district_match"] = True
                else:
                    test_result["fail_reasons"].append(f"Dropdown อำเภอ/เขต title ไม่ตรง: พบ '{actual_dist}' แต่คาดหวัง '{district}'")
            else:
                test_result["district_match"] = True

            if sub_district:
                if self.match_place_value(actual_subdist, sub_district, "subdistrict"):
                    test_result["subdistrict_match"] = True
                else:
                    test_result["fail_reasons"].append(f"Dropdown ตำบล/แขวง title ไม่ตรง: พบ '{actual_subdist}' แต่คาดหวัง '{sub_district}'")
            else:
                test_result["subdistrict_match"] = True

            if postcode:
                if str(postcode) in actual_zip or actual_zip == str(postcode):
                    test_result["zip_match"] = True
                else:
                    test_result["fail_reasons"].append(f"Dropdown รหัสไปรษณีย์ title ไม่ตรง: พบ '{actual_zip}' แต่คาดหวัง '{postcode}'")
            else:
                test_result["zip_match"] = True

            # 9. ตรวจสอบสถานะปุ่ม saveNewMember ว่า disabled หายไปหรือไม่
            is_still_disabled, dis_val = self.is_save_button_disabled()
            test_result["details"]["final_save_button_disabled"] = dis_val
            if not is_still_disabled:
                test_result["save_btn_disabled_removed"] = True
            else:
                test_result["save_btn_disabled_removed"] = False
                test_result["fail_reasons"].append(
                    f"ปุ่มบันทึก saveNewMember ยังคงมี attribute disabled='{dis_val}' "
                    f"(แสดงว่าข้อความสร้างชื่อลูกค้าไม่ถูกต้อง หรือเลือก dropdown ผิด)"
                )

            # 10. คำนวณผลการทดสอบ PASS / FAIL
            if len(test_result["fail_reasons"]) == 0 and test_result["save_btn_disabled_removed"]:
                test_result["passed"] = True
            else:
                test_result["passed"] = False

        except Exception as ex:
            err_msg = f"เกิดข้อผิดพลาดระหว่างรันการทดสอบ Add Customer: {ex}"
            logger.error(err_msg)
            test_result["fail_reasons"].append(err_msg)
            test_result["passed"] = False

        finally:
            if close_modal_after_test:
                self.close_modal()

        # 11. บันทึกผลการทดสอบลงใน TestReportManager และ export ไฟล์รายงาน
        self._record_to_report_manager(test_result, customer_data)

        # 12. อัปเดต Log บนหน้าจอ UI ของบอท
        status_text = "✅ PASS (ผ่านการทดสอบสมบูรณ์)" if test_result["passed"] else "❌ FAIL (ไม่ผ่านการทดสอบ)"
        log_msg = f"🔬 [Test Shortcut] Add Customer Modal -> {status_text}"
        if not test_result["passed"]:
            log_msg += f" | ปัญหา: {', '.join(test_result['fail_reasons'])}"
        if hasattr(self.app, 'update_log'):
            self.app.update_log(log_msg)

        return test_result

    def _gather_customer_data_from_app(self) -> Dict[str, Any]:
        """รวบรวมข้อมูลลูกค้าจากสถานะปัจจุบันของแอปพลิเคชัน"""
        order_id = ""
        name = ""
        tax_id = ""
        address = ""
        province = ""
        district = ""
        sub_district = ""
        postcode = ""

        try:
            if hasattr(self.app, 'cus_order'):
                order_id = str(self.app.cus_order.get()).strip()
            if not order_id and hasattr(self.app, 'entered_order'):
                order_id = str(self.app.entered_order.get()).strip()

            if hasattr(self.app, 'cus_name'):
                name = self.app.cus_name.get()
            if hasattr(self.app, 'tax_num'):
                tax_id = self.app.tax_num.get()

            # Clean name trailing branches
            if name:
                name = re.sub(r'\s*\(?(?:สำนักงานใหญ่|สํานักงานใหญ่|สนญ\.?|00000)\)?\s*$', '', name)
                name = re.sub(r'\s*\(?สาขา[^)]*\)?\s*$', '', name).strip()
                if hasattr(self.app, 'branch_type'):
                    if self.app.branch_type == 'สำนักงานใหญ่':
                        name = f"{name} ({self.app.branch_type})"
                    elif self.app.branch_type == "สาขาย่อย" and hasattr(self.app, 'tax_branch_num'):
                        name = f"{name} (สาขา{self.app.tax_branch_num.get()})"

            if hasattr(self.app, 'address'):
                address = self.app.address
            if hasattr(self.app, 'cus_province'):
                province = self.app.cus_province.get()
            if hasattr(self.app, 'cus_district'):
                district = self.app.cus_district.get()
            if hasattr(self.app, 'cus_sub_district'):
                sub_district = self.app.cus_sub_district.get()
            if hasattr(self.app, 'cus_postcode'):
                postcode = self.app.cus_postcode.get()

            # Fallback to nondistortedData if province/district/subdistrict/address was not set in StringVar
            if hasattr(self.app, 'nondistortedData') and isinstance(self.app.nondistortedData, dict):
                nd = self.app.nondistortedData
                if not province:
                    province = str(nd.get('จังหวัด.1') or nd.get('จังหวัด') or "").strip()
                if not district:
                    district = str(nd.get('เขต/อำเภอ.1') or nd.get('เขต/อำเภอ') or "").strip()
                if not sub_district:
                    sub_district = str(nd.get('แขวง/ตำบล') or "").strip()
                if not postcode:
                    postcode = str(nd.get('รหัสไปรษณีย์.1') or nd.get('รหัสไปรษณีย์') or "").strip()
                if not address:
                    address = str(nd.get('รายละเอียดที่อยู่') or nd.get('ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป') or "").strip()

            # Sanitize 'nan' strings from pandas
            if province.lower() == 'nan':
                province = ""
            if district.lower() == 'nan':
                district = ""
            if sub_district.lower() == 'nan':
                sub_district = ""
            if postcode.lower() == 'nan':
                postcode = ""
            if address.lower() == 'nan':
                address = ""

        except Exception as e:
            logger.warning(f"[CustomerModalTestHandler] รวบรวมข้อมูลจากแอปพบข้อผิดพลาด: {e}")

        # Fallback values สำหรับกรณีที่แอปยังไม่ได้โหลดออเดอร์ใดๆ เพื่อให้ทดสอบได้
        is_order_loaded = bool(name or address or province)
        if not is_order_loaded:
            if not name:
                name = "บริษัท ทดสอบระบบ จำกัด (สำนักงานใหญ่)"
            if not tax_id:
                tax_id = "0105555000000"
            if not address:
                address = "99/99 อาคารทดสอบ ชั้น 9"
            if not province:
                province = "กรุงเทพมหานคร"
            if not district:
                district = "วัฒนา"
            if not sub_district:
                sub_district = "คลองเตยเหนือ"
            if not postcode:
                postcode = "10110"

        return {
            "order_id": order_id,
            "name": name,
            "tax_id": tax_id,
            "address": address,
            "province": province,
            "district": district,
            "sub_district": sub_district,
            "postcode": postcode,
        }

    def _record_to_report_manager(self, test_result: Dict[str, Any], customer_data: Dict[str, Any]):
        """บันทึกข้อมูลและส่งออกรายงาน Excel ผ่าน TestReportManager"""
        try:
            report_mgr = getattr(self.bot, 'report_manager', None) or getattr(self.app, 'report_manager', None)
            if not report_mgr:
                from functions.utils.report_manager import TestReportManager
                report_mgr = TestReportManager()
                self.bot.report_manager = report_mgr

            order_id = test_result["order_id"]
            passed = test_result["passed"]
            err_summary = "; ".join(test_result["fail_reasons"]) if test_result["fail_reasons"] else ""

            # เตรียม record ใน report manager
            report_mgr.start_order(
                order_id=order_id,
                marketplace=getattr(self.app, 'marketplace_target', None).get() if hasattr(self.app, 'marketplace_target') else "TEST",
                customer_name=customer_data.get("name", ""),
                tax_id=customer_data.get("tax_id", "")
            )

            report_mgr.record_customer_modal_test(
                order_id=order_id,
                passed=passed,
                details=test_result["details"],
                error=err_summary
            )

            # Export ออกเป็นไฟล์ Excel อัตโนมัติในโฟลเดอร์ reports/
            excel_path = report_mgr.export_to_excel()
            if excel_path:
                logger.info(f"[CustomerModalTestHandler] บันทึกรายงานผลการทดสอบลงไฟล์: {excel_path}")
                test_result["report_path"] = excel_path

        except Exception as e:
            logger.error(f"[CustomerModalTestHandler] เกิดข้อผิดพลาดในการบันทึกรายงาน: {e}")
