import re
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TrackingManager:
    """
    Class to manage fetching tracking numbers from marketplace page and 
    pasting them onto the final step page.
    """

    def __init__(self, driver, bot, marketplace):
        self.driver = driver
        self.bot = bot
        self.marketplace = marketplace
        self.urls = {
            'SHOPEE': "https://seller.shopee.co.th/portal/sale/order",
            'LAZADA': "https://sellercenter.lazada.co.th/apps/order/list?status=all"
        }
        self.marketplace_url = self.urls[self.marketplace]
        self.trackings = []
        # You can define timeout here
        self.wait10 = WebDriverWait(self.driver, 10)

    def _wait_for_element(self, by, value):
        while not self.bot.operation_thread.is_set():
            try:
                self.driver.find_element(by, value).is_displayed()  # Check if element is visible
                break
            except Exception as e:
                # print(f"Waiting for element {value} failed: {e}")
                time.sleep(1)  # Wait a bit before retrying
                continue

    def collect_tracking(self, current_order, expected_count: int = None) -> None:
        self.merged_dict = self.bot.merged_dict
        """
        1. เก็บค่า tracking จาก marketplace
        """
        # * clear ค่า trackings list
        self.trackings.clear()

        # คำนวณ expected_count อัตโนมัติหากไม่ได้ส่งเข้ามา
        if expected_count is None:
            if hasattr(self.bot, 'app') and hasattr(self.bot.app, 'filter_data') and self.bot.app.filter_data is not None:
                try:
                    if not self.bot.app.filter_data.empty:
                        expected_count = len(self.bot.app.filter_data)
                except Exception:
                    pass
            if expected_count is None and hasattr(self.bot, 'items') and self.bot.items:
                expected_count = len(self.bot.items)

        # * driver สลับ tab ไป marketplace (Assuming marketplace is tab index 1 or using window handles)
        try:
            if self.marketplace == 'SHOPEE':
                try:
                    self.driver.switch_to.window(self.merged_dict['Seller Centre'])
                except:
                    self.driver.execute_script(
                        "window.open('https://seller.shopee.co.th/portal/sale/order', '_blank', 'noopener,noreferrer');"
                    )
                    self.driver.switch_to.window(self.driver.window_handles[-1])

            elif self.marketplace == 'LAZADA':
                try:
                    self.driver.switch_to.window(self.merged_dict['การจัดการคำสั่งซื้อ - Lazada Seller Center'])
                except:
                    self.driver.switch_to.window(self.merged_dict['การจัดการคำสั่งซื้อ - Seller Center'])
            pass
        except Exception as e:
            print(f"Error switching tab: {e}")

        # * marketplace หน้าแรกไหม
        is_homepage = self._check_is_marketplace_homepage()

        if not is_homepage:
            # * redicrect กลับไปหน้าแรก
            self._redirect_to_marketplace_homepage()

        # * Reenter current_order
        self._reenter_current_order(current_order)

        # ตรวจสอบและดึงข้อมูล Tracking ตาม Marketplace
        shopee_incomplete_err = None
        if self.marketplace == 'SHOPEE':
            shopee_result = self._collect_shopee_trackings(expected_count=expected_count)
            self.trackings = shopee_result.get('trackings', [])
            if not shopee_result.get('is_complete', True):
                shopee_incomplete_err = shopee_result.get('error_message', "เลข Tracking บน Shopee ไม่ครบถ้วน")
        else:
            # เก็บ tracking elements
            elements = self._get_tracking_elements()
            # สกัด trackings จาก elements as list
            self.trackings = self._extract_trackings_from_elements(elements)

        print(f"Collected trackings: {self.trackings} (Expected: {expected_count})")

        # driver สลับ tab กลับไป SMCO (เปิดการขาย) เสมอ ก่อนจะตัดสินใจต่อ
        try:
            self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
            pass
        except Exception as e:
            print(f"Error switching returning tab: {e}")

        # หากข้อมูล Tracking ไม่สมบูรณ์ ให้ raise Exception เพื่อให้ auto_inv ตัดเป็น Failed Order ทันที
        if shopee_incomplete_err:
            raise ValueError(shopee_incomplete_err)

        if expected_count is not None and expected_count > 0:
            if len(self.trackings) < expected_count:
                raise ValueError(
                    f"เลข Tracking บน {self.marketplace} ไม่ครบ: พบ {len(self.trackings)} จากที่ต้องมี {expected_count} รายการ (อาจยังเป็นสถานะนัดรับ หรือยังไม่ออกเลข)"
                )

    def apply_tracking_to_final_page(self, order_no: str = "") -> None:
        """
        นำข้อมูล Order No และ Tracking Numbers ไปใส่ใน Modal หมายเหตุหน้าท้าย:
        1. เปิด Modal หมายเหตุ (AddRemarkRef)
        2. ใส่ Order No ลงใน //textarea[@ng-model='posPaymentHead.data.ref1RemarkTemp']
        3. กระจาย Tracking Numbers ลงใน:
           - //textarea[@ng-model='posPaymentHead.data.ref2RemarkTemp'] (ความยาวไม่เกิน 255 ตัวอักษร)
           - //textarea[@ng-model='posPaymentHead.data.ref3RemarkTemp'] (ส่วนที่เหลือ ความยาวไม่เกิน 255 ตัวอักษร)
           * โดยต้องใส่ให้ครบ pattern ของแต่ละ tracking หากตัวถัดไปใส่แล้วเกิน 255 จะย้ายไปใส่ใน ref3
        4. กดปุ่มยืนยัน //button[@ng-click='okAddRemarkRef()']
        """
        order_val = order_no if order_no else str(getattr(self.bot, 'cus_order', ''))

        # แบ่ง tracking ใส่ ref2 และ ref3 (ไม่เกิน 255 ตัวอักษรต่อช่อง และไม่ตัด pattern)
        ref2_text, ref3_text = self._split_trackings_into_chunks(self.trackings, max_len=255)

        try:
            # 1. เปิด Modal หมายเหตุ ถ้ายังไม่ได้เปิด
            modal_open_selectors = [
                "//button[@ng-click='addRemarkRef()']",
                "//a[@ng-click='addRemarkRef()']",
                "//button[contains(@ng-click, 'RemarkRef') or contains(@ng-click, 'addRemark')]",
                "//a[contains(@ng-click, 'RemarkRef') or contains(@ng-click, 'addRemark')]",
                "//div[@class='col-sm-4 nopadding']//button",
                "//div[@class='col-sm-4 nopadding']//a"
            ]
            for xpath in modal_open_selectors:
                try:
                    btns = self.driver.find_elements(By.XPATH, xpath)
                    for btn in btns:
                        if btn.is_displayed():
                            self.driver.execute_script("arguments[0].click();", btn)
                            time.sleep(0.3)
                            break
                except Exception:
                    pass

            # 2. ฟังก์ชันช่วยกรอกค่าลง Textarea และ Dispatch Event
            def _set_ref_textarea_value(xpath: str, value: str):
                try:
                    el = self.driver.find_element(By.XPATH, xpath)
                    self.driver.execute_script("""
                        var el = arguments[0];
                        var val = arguments[1] || '';
                        el.style.display = 'block';
                        el.style.visibility = 'visible';
                        el.style.opacity = '1';
                        el.setAttribute('title', val);
                        el.value = val;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    """, el, value)
                    print(f"Applied {xpath} -> '{value}' (len={len(value)})")
                except Exception as ex:
                    print(f"Error setting {xpath}: {ex}")

            # ref1: ใส่เลขออเดอร์ (Order No)
            _set_ref_textarea_value("//textarea[@ng-model='posPaymentHead.data.ref1RemarkTemp']", order_val)

            # ref2: ใส่เลข Tracking ชุดแรก (สูงสุด 255 ตัวอักษร)
            _set_ref_textarea_value("//textarea[@ng-model='posPaymentHead.data.ref2RemarkTemp']", ref2_text)

            # ref3: ใส่เลข Tracking ชุดที่สอง (ถ้ามี ส่วนที่เหลือ สูงสุด 255 ตัวอักษร)
            _set_ref_textarea_value("//textarea[@ng-model='posPaymentHead.data.ref3RemarkTemp']", ref3_text)

            # 3. กดปุ่ม OK เพื่อบันทึกและปิด Modal
            time.sleep(0.3)
            try:
                ok_button = self.driver.find_element(By.XPATH, "//button[@ng-click='okAddRemarkRef()']")
                self.driver.execute_script("arguments[0].click();", ok_button)
                time.sleep(0.3)
            except Exception as ok_err:
                print(f"Error clicking okAddRemarkRef button: {ok_err}")

        except Exception as e:
            print(f"Error applying order and trackings to remark modal: {e}")

    def _split_trackings_into_chunks(self, trackings: list, max_len: int = 255) -> tuple:
        """
        แบ่งรายการ tracking ออกเป็น 2 ชุด (ref2 และ ref3)
        โดยแต่ละชุดมีความยาวไม่เกิน max_len (255 ตัวอักษร)
        และคง pattern ของ tracking แต่ละตัวให้สมบูรณ์ (ไม่ตัดคำกลาง tracking)
        """
        ref2_items = []
        ref3_items = []
        target_list = ref2_items

        for t in trackings:
            t_str = str(t).strip()
            if not t_str:
                continue

            test_items = target_list + [t_str]
            test_text = ", ".join(test_items)

            if len(test_text) <= max_len:
                target_list.append(t_str)
            else:
                if target_list is ref2_items:
                    # ย้ายไปเติมใน ref3
                    target_list = ref3_items
                    test_items_ref3 = target_list + [t_str]
                    test_text_ref3 = ", ".join(test_items_ref3)
                    if len(test_text_ref3) <= max_len:
                        target_list.append(t_str)
                    else:
                        print(f"⚠️ Tracking '{t_str}' เกินความจุของ ref3 (Max 255 chars)")
                else:
                    print(f"⚠️ Tracking '{t_str}' เกินความจุของ ref3 (Max 255 chars)")

        ref2_text = ", ".join(ref2_items)
        ref3_text = ", ".join(ref3_items)
        return ref2_text, ref3_text

    # --- Private Helper Methods ---

    def _collect_shopee_trackings(self, expected_count: int = None) -> dict:
        """
        ตรวจสอบหน้า Shopee Order ราย Package Card:
        1. ตรวจ element //div[@class='package-of-package-level-order-card']
        2. นับจำนวนว่าตรงกับ expected_count ไหม
        3. ตรวจว่าแต่ละ Card มี //div[@class='tracking-number'] หรือไม่ และตรงกับ SKU ไหนจาก //div[@class='item-description']
        """
        time.sleep(1.5)  # รอ element โหลดให้สมบูรณ์

        package_card_xpath = "//div[contains(@class, 'package-of-package-level-order-card')]"
        package_cards = self.driver.find_elements(By.XPATH, package_card_xpath)

        collected_trackings = []
        package_details = []
        missing_skus = []

        if package_cards:
            print(f"Shopee package cards found: {len(package_cards)} cards")
            for idx, card in enumerate(package_cards):
                # ดึง item description / SKU
                item_desc_text = f"Package #{idx+1}"
                try:
                    desc_el = card.find_element(By.XPATH, ".//div[contains(@class, 'item-description')]")
                    if desc_el and desc_el.text.strip():
                        item_desc_text = desc_el.text.strip().replace("\n", " ")
                except Exception:
                    pass

                # ดึง tracking number ใน card นี้
                tracking_no = None
                try:
                    track_el = card.find_element(By.XPATH, ".//div[contains(@class, 'tracking-number')]")
                    if track_el and track_el.text.strip():
                        tracking_no = track_el.text.strip()
                except Exception:
                    pass

                package_details.append({
                    "card_index": idx + 1,
                    "item_description": item_desc_text,
                    "tracking_number": tracking_no
                })

                if tracking_no:
                    collected_trackings.append(tracking_no)
                else:
                    missing_skus.append(f"[{item_desc_text}]")

            # ตรวจสอบความครบถ้วน
            is_complete = True
            error_message = None

            if expected_count is not None and expected_count > 0:
                if len(package_cards) != expected_count:
                    is_complete = False
                    error_message = (
                        f"จำนวน Package บน Shopee ({len(package_cards)}) ไม่ตรงกับรายการใน Order ({expected_count}) "
                        f"Tracking ที่พบ: {len(collected_trackings)}"
                    )
                elif missing_skus or len(collected_trackings) < expected_count:
                    is_complete = False
                    missing_str = ", ".join(missing_skus) if missing_skus else "บางรายการไม่มี tracking"
                    error_message = (
                        f"เลข Tracking บน Shopee ไม่ครบ: ได้ {len(collected_trackings)}/{expected_count} รายการ "
                        f"(รายการที่ขาดเลข Tracking หรือติดนัดรับ: {missing_str})"
                    )
            elif missing_skus:
                is_complete = False
                error_message = f"พบ Package บน Shopee ที่ยังไม่มีเลข Tracking: {', '.join(missing_skus)}"

            return {
                "is_complete": is_complete,
                "error_message": error_message,
                "trackings": collected_trackings,
                "package_details": package_details
            }
        else:
            # Fallback หาก Shopee ไม่ได้แสดงเป็น package-of-package-level-order-card
            print("No package-of-package-level-order-card found, falling back to tracking-number elements")
            elements = self._get_tracking_elements()
            collected_trackings = self._extract_trackings_from_elements(elements)
            
            is_complete = True
            error_message = None
            if expected_count is not None and expected_count > 0 and len(collected_trackings) < expected_count:
                is_complete = False
                error_message = (
                    f"เลข Tracking บน Shopee ไม่ครบ: ได้ {len(collected_trackings)}/{expected_count} รายการ (โหมด fallback)"
                )

            return {
                "is_complete": is_complete,
                "error_message": error_message,
                "trackings": collected_trackings,
                "package_details": []
            }

    def _check_is_marketplace_homepage(self):
        # Placeholder: logic to verify if current page is marketplace home page.
        if self.marketplace == 'SHOPEE':
            url = self.driver.current_url
            splited_url = url.split('/')
            is_home = splited_url[-1] == 'order'
            return is_home
        elif self.marketplace == 'LAZADA':
            url = self.driver.current_url
            splited_url = url.split('=')
            is_home = splited_url[-1] == 'all'
            return is_home
        raise ValueError("Invalid marketplace")

    def _redirect_to_marketplace_homepage(self):
        # Placeholder: logic to click home button or redirect driver.get(url)
        self.driver.get(self.marketplace_url)

    def _reenter_current_order(self, current_order):
        # Placeholder: logic to search for the current_order
        if self.marketplace == 'SHOPEE':
            self._wait_for_element(By.CSS_SELECTOR, 'div.eds-input__inner.eds-input__inner--normal input')
            self.driver.find_element(By.CSS_SELECTOR, 'div.eds-input__inner.eds-input__inner--normal input').clear()
            self.driver.find_element(
                By.CSS_SELECTOR, 'div.eds-input__inner.eds-input__inner--normal input').send_keys(current_order)
            self.driver.find_element(
                By.CSS_SELECTOR, 'div.eds-input__inner.eds-input__inner--normal input').send_keys(Keys.ENTER)
        elif self.marketplace == 'LAZADA':
            laz_order_input_path = "//span[@class='next-select-trigger-search']/input[@role='combobox' and @name='orderNumbers']"
            self.search_elmt = self.wait10.until(EC.visibility_of_element_located((By.XPATH, laz_order_input_path)))
            self.driver.find_element(By.XPATH, laz_order_input_path).clear()
            self.input_count = []

            try:
                laz_close_btn_path = "//div[@class='next-tag next-tag-closable next-tag-small next-tag-level-primary next-tag-closable']/span[@class='next-tag-close-btn']"
                close_btn = self.driver.find_element(By.XPATH, laz_close_btn_path)

                try:
                    laz_order_input_amount_path = '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/div[2]/span/span'
                    self.input_count = self.driver.find_element(By.XPATH, laz_order_input_amount_path)
                except:
                    print("Have only one input")
            except:
                print("Input is empty")

            try:
                if self.input_count.is_displayed() and close_btn.is_displayed():
                    clicks = re.sub(r'\W', "", self.input_count.text)
                    print("จำนวนครั้งของการกด x ", clicks)
                    print(f"{clicks} times click")
                    for click in range(int(clicks)):
                        close_btn = self.driver.find_element(
                            By.XPATH,
                            '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/div[1]/span[2]')
                        print("click", click)
                        close_btn.click()
                else:
                    print("1 times click")
                    close_btn.click()

            except Exception as err:
                print(f"Error handling close button: {err}")
                try:
                    close_btn.click()
                    print('1 Button closed ')
                except:
                    print('No close Button')
                    pass

            self.search_elmt.clear()
            self.search_elmt.send_keys(current_order)

            # * กด Search เพื่อ เก็บ Status
            self.searchBtn = self.driver.find_element(
                By.XPATH,
                '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/div[1]')
            self.searchBtn.click()
            time.sleep(0.75)

    def _get_tracking_elements(self) -> list:
        # Placeholder: return a list of selenium WebElements representing trackings
        # return self.driver.find_elements(By.XPATH, "TRACKING_ELEMENTS_XPATH")
        time.sleep(1)  # * ใช้ได้จริง ถ้าไม่ใช้ มันจะโหลดไม่ทันทำให้ได้ list เปล่าๆมา
        if self.marketplace == 'SHOPEE':
            shopee_tracking_xpath = "//div[@class='tracking-number']"
            tracking_elements = self.driver.find_elements(By.XPATH, shopee_tracking_xpath)
            print("tracking_elements: ", tracking_elements)
            return tracking_elements

        elif self.marketplace == 'LAZADA':
            lazada_tracking_xpath = "//div[@class='order-field order-field-tracking-number']//span[@class='show-text copy-text-item hover-show-edit break-all']"
            tracking_elements = self.driver.find_elements(By.XPATH, lazada_tracking_xpath)
            print("tracking_elements: ", tracking_elements)
            return tracking_elements

    def _extract_trackings_from_elements(self, elements):
        # Placeholder: get text or attribute from the elements
        print("extracted_elements: ", elements)
        return [el.text for el in elements if el.text]
