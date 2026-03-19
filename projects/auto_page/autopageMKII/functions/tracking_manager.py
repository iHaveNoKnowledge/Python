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

    def collect_tracking(self, current_order) -> None:
        self.merged_dict = self.bot.merged_dict
        """
        1. เก็บค่า
        """
        # * clear ค่า trackings list
        self.trackings.clear()

        # * driver สลับ tab ไป marketplace (Assuming marketplace is tab index 1 or using window handles)
        try:
            # * Placeholder: switchTo the marketplace tab
            # * e.g., self.driver.switch_to.window(self.driver.window_handles[1])
            if self.marketplace == 'SHOPEE':
                self.driver.switch_to.window(self.merged_dict['Seller Centre'])
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
            # * Followed by re-enter? The diagram has a loop back.
            pass

        # * Reenter current_order
        self._reenter_current_order(current_order)

        # เก็บ tracking elements
        elements = self._get_tracking_elements()

        # สกัด trackings จาก elements as list
        self.trackings = self._extract_trackings_from_elements(elements)
        print(f"Collected trackings: {self.trackings}")

        # driver สลับ tab ไป เปิดการขาย0 (Assuming it's the first tab)
        try:
            # Placeholder: switch back to the main POS tab
            # e.g., self.driver.switch_to.window(self.driver.window_handles[0])
            self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
            pass
        except Exception as e:
            print(f"Error switching returning tab: {e}")

        # return self.trackings

    def apply_tracking_to_final_page(self) -> None:
        """
        2. เอาไปใส่ในหน้าท้าย
        """
        ref_element_xpath = "//textarea[@ng-model='posPaymentHead.data.ref1RemarkTemp']"
        if not self.trackings:
            print("No trackings to apply.")
            return

        # Placeholder: logic to insert trackings into the specific element in the final page
        # Example:
        # try:
        #     tracking_input = self.wait10.until(EC.presence_of_element_located((By.XPATH, "YOUR_XPATH_HERE")))
        #     tracking_text = ", ".join(self.trackings)
        #     tracking_input.send_keys(tracking_text)
        # except Exception as e:
        #     print(f"Error applying trackings: {e}")

        try:
            tracking_input = self.driver.find_element(By.XPATH, ref_element_xpath)
            tracking_text = ", ".join(self.trackings)
            self.bot.js_input_value(tracking_input, tracking_text)
        except Exception as e:
            print(f"Error applying trackings: {e}")
        pass

    # --- Private Helper Methods (To be implemented by the user) ---

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
            self.search_elmt.send_keys(self.cus_order)

            # * กด Search เพื่อ เก็บ Status
            self.searchBtn = self.driver.find_element(
                By.XPATH,
                '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/div[1]')
            self.searchBtn.click()
            time.sleep(0.75)

    def _get_tracking_elements(self) -> list:
        # Placeholder: return a list of selenium WebElements representing trackings
        # return self.driver.find_elements(By.XPATH, "TRACKING_ELEMENTS_XPATH")
        if self.marketplace == 'SHOPEE':
            tracking_elements = self.driver.find_elements(By.XPATH, "//div[@class='tracking-number']")
            print("tracking_elements: ", tracking_elements)
            return tracking_elements

        elif self.marketplace == 'LAZADA':
            print("ยังไม่ได้ทำ")
            return []

    def _extract_trackings_from_elements(self, elements):
        # Placeholder: get text or attribute from the elements
        print("extracted elements: ", elements)
        return [el.text for el in elements if el.text]
