import json
import math
import time

from functions.network_response_utils import NetworkResponseCapture
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC


class AutoAddProduct:
    def __init__(self, driver, wait50, app, parent):
        self.driver = driver
        self.wait50 = wait50
        self.app = app
        self.bot = parent
        self.driver_lock = parent.driver_lock
        self.network_capture = NetworkResponseCapture(driver)

    # * Utils
    def idx_of_target_element(self, sku: str):
        print("incoming sku: ", sku)
        smco_sku_code_elements = self.driver.find_elements(
            By.XPATH, "//span[(contains(@ng-click, 'productNameChangeChk(x)'))and not(contains(@class, 'ng-hide'))]//u")

        sku_target_idx: int = None
        for idx, sku_element in enumerate(smco_sku_code_elements):
            print(f"No. {idx+1} เจอ sku: {sku_element.text}")
            if sku_element.text == sku:
                sku_target_idx = idx
                print(f"เจอ sku ตรงกับที่ต้องการที่ลำดับที่ {sku_target_idx + 1} ")
                return sku_target_idx

        return None

    # * main fxs/helpers
    def item_qty_setter(self, item_identifier: str | int, qty: int = 1):
        print("item_qty_setter called item_identifier: ", item_identifier, " qty: ", qty)
        try:
            if isinstance(item_identifier, str):  # * แปลงเป็น idx ก่อน
                print("Converting")
                item_identifier = self.idx_of_target_element(item_identifier)
                print("item_identifier: ", item_identifier)
                print("Converted")

            target_idx = item_identifier

            if target_idx is None:
                print(f"Error, Could not find element index for identifier:  '{item_identifier}'")
                return

            # * Wait for DOM to settle
            time.sleep(0.5)

            # * Update XPath to exclude hidden elements
            current_qty_elements = self.driver.find_elements(
                By.XPATH, "//span[@class='col-sm-4 ng-binding' and not(contains(@class, 'ng-hide'))]")

            if target_idx >= len(current_qty_elements):
                print(
                    f"Error: target_idx {target_idx} out of range for current_qty_elements (len={len(current_qty_elements)})")
                return

            target_current_qty = current_qty_elements[target_idx].text
            print("current_qty_elements count: ", len(current_qty_elements))
            print(f"target_current_qty at idx {target_idx}: '{target_current_qty}'")
            print("qty needed: ", qty)

            if target_idx >= 0:
                print("Start qty setter check")
                try:
                    # * Update XPath to exclude hidden elements for buttons too, just in case
                    item_qty_elements = self.driver.find_elements(
                        By.XPATH, "//button[@ng-click='incrementMainQty(true, x)' and not(contains(@class, 'ng-hide'))]")

                    # * Check if we really need to loop
                    if int(target_current_qty) < int(qty):
                        print(
                            f"Quantity mismatch: current {target_current_qty} < needed {qty}. Starting increment loop.")
                        while not self.bot.auto_add_product_stop_flag.is_set() and int(target_current_qty) < int(qty):
                            print(f"target_current_qty and qty: {target_current_qty} and {qty}")
                            try:
                                print("click increase button")
                                if target_idx < len(item_qty_elements):
                                    item_qty_elements[target_idx].click()
                                else:
                                    print(
                                        f"Error: Button index {target_idx} out of range (buttons={len(item_qty_elements)})")
                                    break

                                # * Re-read quantity
                                target_current_qty = current_qty_elements[target_idx].text
                                if int(target_current_qty) >= int(qty):
                                    break
                            except Exception as e:
                                # * กรณียัง click ไม่ได้/มีปัญหากับการ click จะลงมาที่นี
                                print(f"Cannot click increase button: {e}")
                                time.sleep(0.25)
                                continue
                    else:
                        print(
                            f"Quantity match or exceed: current {target_current_qty} >= needed {qty}. No action needed.")

                except Exception as e:
                    print(f"Error in item_qty_setter loop: {e}")
        except Exception as e:
            print(f"Critical error in item_qty_setter: {e}")

    def price_setter(self,  sku: str,  srp: int = None):
        # Todo //span[(contains(@ng-click, 'productNameChangeChk(x)'))and not(contains(@class, 'ng-hide'))]//u[text()=ตัวแปรsku]
        if srp:
            sku_target_idx = self.idx_of_target_element(sku)

            # * Dynamic click on price element base on sku_target_idx
            smco_price_elements = self.driver.find_elements(
                By.XPATH, "//div[@class='row']//div//a[@class='col-sm-6 text-right font-color-base ng-binding']")
            smco_price_elements[sku_target_idx].click()

            time.sleep(1)
            # ค่าขนส่งโดนข้า230208FX99FUGGมหลังจากตรงนี้
            print("Successfully clicked on SKU ELEMENT 1")

            changePriceInput = self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[1]/input')
            changePriceInput.clear()
            # changePriceInput.send_keys(69)
            # changePriceInput.send_keys(int(app.cus_ship_cost.get()))
            self.driver.execute_script(
                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')", changePriceInput, srp)
            self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[2]/input').clear()
            self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[2]/input').send_keys(self.app.user_id.get())

            self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[3]/input').clear()
            self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[3]/input').send_keys(self.app.user_pw.get())

            self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[5]/div/textarea').clear()
            self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[5]/div/textarea').send_keys("Online")

            self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[6]/a[1]').click()
            try:
                print("Waiting for element to disappear")
                self.wait50.until(EC.invisibility_of_element_located(
                    (By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[6]/a[1]')))
            except:
                print("No need to wait")

    # * Main Process
    def auto_add_product(self, skus: list[str], qty: int = 1, srp: int = None, **kwargs):
        with self.driver_lock:
            # * Clear stop flag ก่อนเริ่มทำงาน
            self.bot.auto_add_product_stop_flag.clear()

            print(f"incoming skus: {skus}")
            self.bot.get_tabs()
            merged_dict = self.bot.merged_dict
            self.driver.switch_to.window(merged_dict['SMCO :: เปิดการขาย'])

            try:
                # * SKU input location
                sku_input_element = self.wait50.until(EC.visibility_of_element_located(
                    (By.XPATH, "//span[contains(@class, 'arFilterBox-')]//input[@name='svalue' and contains(@class, 'arFilterBox-search ')]")))
                sku_qty_element = self.driver.find_element(
                    By.XPATH, "//input[@style='text-align:center;' and @ng-model='modelAddOn.productQty']")

                for sku in skus:
                    while not self.bot.auto_add_product_stop_flag.is_set():
                        try:
                            print("Processing SKU: ", sku, " with qty: ", qty)
                            self.driver.execute_script(
                                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                                sku_qty_element,
                                qty
                            )
                            result = self.driver.execute_script(
                                "return angular.element(arguments[0]).val()", sku_qty_element)
                            print("result: ", result)
                            if int(result) == int(qty):
                                break

                        except Exception as err:
                            print("auto_add_product - set qty error: ", err)
                            continue

                    # * ใช้ NetworkResponseCapture utility แทนโค้ดเดิม
                    target_url_part = "/smartcore/smartpos/pointofsales/posmainv3/getProductMasterInfoPOSV3.htm"

                    # * Clear logs ก่อนส่ง request
                    self.network_capture.clear_logs()

                    # * เตรียม SKU input
                    sku_input_element.clear()
                    sku_input_element.send_keys(sku)
                    print(f"Placing SKU Input with {sku} success")

                    # * ส่ง request
                    sku_input_element.send_keys(Keys().ENTER)
                    print("Pressed Enter to submit SKU")
                    time.sleep(0.2)

                    # * ดึง response ด้วย utility
                    response_data = self.network_capture.capture_response(target_url_part, max_attempts=20)

                    product_from_response = None
                    if response_data:
                        try:
                            product_from_response = response_data[0]['productCode']
                            print(f"Got product: {product_from_response}")
                        except Exception as err:
                            print(f"Cannot parse product: {err}")
                            product_from_response = None
                    else:
                        print("No response received")

                    # * Clear logs หลังใช้งาน
                    self.network_capture.clear_logs()

                    self.price_setter(sku=product_from_response, srp=srp)
                    self.item_qty_setter(product_from_response, qty)

            except Exception as err:
                print("Shipment cost skipped")
                print(err)
