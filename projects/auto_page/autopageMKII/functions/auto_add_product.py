import json
import math
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


class AutoAddProduct:
    def __init__(self, driver, wait50, app):
        self.driver = driver
        self.wait50 = wait50
        self.app = app

    def price_setter(self,  sku: str,  srp: int = None):
        # Todo WIP ใช้ได้ละ รอ implement ใน flow จริง ใช้คู่กับ auto_add_product
        # Todo มึงจะต้องหา element ของ item ทั้งหมดก่อน แล้วก็ดูว่า response ข้างบน มันส่งคืน item ไรมา บ้าง แล้วก็ loop เพื่อหา element ที่ตรงกับ item ที่ response ส่งมา เราก็จะรู้ว่า response ที่ส่งกลับมาไปอยู่ลำดับที่เท่าไหร่ของ element ในหน้ายิงขาย
        # Todo //span[(contains(@ng-click, 'productNameChangeChk(x)'))and not(contains(@class, 'ng-hide'))]//u[text()=ตัวแปรsku]
        if srp:
            smco_sku_code_elements = self.driver.find_elements(By.XPATH, "//span[(contains(@ng-click, 'productNameChangeChk(x)'))and not(contains(@class, 'ng-hide'))]//u")
            sku_target_idx: int = None
            for idx, sku_element in enumerate(smco_sku_code_elements):
                print(f"No. {idx+1} เจอ sku: {sku_element.text}")
                if sku_element.text == sku:
                    sku_target_idx = idx
                    print(f"เจอ sku ตรงกับที่ต้องการที่ลำดับที่ {sku_target_idx + 1} ")
                    break

            # * Dynamic click on price element base on sku_target_idx
            smco_price_elements = self.driver.find_elements(
                By.XPATH, "//div[@class='row']//div//a[@class='col-sm-6 text-right font-color-base ng-binding']")
            smco_price_elements[sku_target_idx].click()

            time.sleep(1)
            # ค่าขนส่งโดนข้า230208FX99FUGGมหลังจากตรงนี้
            print("Successfully clicked on SKU ELEMENT 1")

            changePriceInput = self.driver.find_element(
                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[1]/input')
            changePriceInput.clear()
            # changePriceInput.send_keys(69)
            # changePriceInput.send_keys(int(app.cus_ship_cost.get()))
            self.driver.execute_script(
                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')", changePriceInput, srp)
            self.driver.find_element(
                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[2]/input').clear()
            self.driver.find_element(
                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[2]/input').send_keys(self.app.user_id.get())

            self.driver.find_element(
                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[3]/input').clear()
            self.driver.find_element(
                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[3]/input').send_keys(self.app.user_pw.get())

            self.driver.find_element(
                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[5]/div/textarea').clear()
            self.driver.find_element(
                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[5]/div/textarea').send_keys("Online")

            self.driver.find_element(
                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[6]/a[1]').click()
            try:
                print("Waiting for element to disappear")
                self.wait50.until(EC.invisibility_of_element_located(
                    (By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[6]/a[1]')))
            except:
                print("No need to wait")

    def auto_add_product(self, skus: list[str], srp: int = None):
        print(f"incoming skus: {skus}")
        try:
            skuInput_element = self.wait50.until(EC.visibility_of_element_located(
                (By.XPATH, "//span[contains(@class, 'arFilterBox-')]//input[@name='svalue' and contains(@class, 'arFilterBox-search ')]")))
            # skuInput = self.driver.find_element(By.CSS_SELECTOR,'input.arFilterBox-search.ng-valid.ng-dirty.ng-empty.ng-touched')
            for sku in skus:
                skuInput_element.clear()
                skuInput_element.send_keys(sku)
                print(f"Placing SKU Input with {sku} success")

                skuInput_element.send_keys(Keys().ENTER)
                print("Pressed Enter to submit SKU")

            request_ids = []
            target_url_part = "/smartcore/smartpos/pointofsales/posmainv3/getProductMasterInfoPOSV3.htm"
            n = 0
            # * จับ requestId หลัง submit form: โดยเราจะดูว่า request ที่ browser ส่งออกไป มี url ตรงกับ request url ที่เราตั้งใจส่งและรอดูผลลัพหรือไม่ ซึ่งในที่นี้คือ target_url_part
            for _ in range(50):  # poll 5 วิ
                logs = self.driver.get_log("performance")
                for entry in logs:
                    print("entry: ", entry)
                    msg = json.loads(entry["message"])["message"]
                    if msg["method"] == "Network.requestWillBeSent":  # * ตรวจดู เมื่อ browser กำลังจะส่ง request ออกไป
                        url = msg["params"]["request"]["url"]
                        if target_url_part in url:
                            request_ids.append(msg["params"]["requestId"])
                            print("msg from target url req:", msg)
                            break

                # * ถ้าใช้ตรงนี้มันจะเร็วเกินไป ทำให้ response ยังไม่มา รอ 5 วิ พอเป็นพิธี
                if len(request_ids) > 0:
                    print("request_ids: ", request_ids)
                    break

                time.sleep(0.1)
                n += 1
                if n % 10 == 0 and n >= 10:
                    print("time: ", math.floor(n/10), "วินาที")

            product_from_response = None
            # * ดึง response จาก requestId: เป็นการดูว่า request ที่เราสนใจ มี response กลับมาแล้วหรือยัง มันจะส่งกลับมา 200 เสมอ ถ้ามีของกลับมา
            for _ in range(50):  # poll 10 วิ
                res = None
                for req_id in request_ids:
                    try:
                        res = self.driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": req_id})
                        print(f"Response for {req_id} = {res}")
                        try:
                            product_from_response = json.loads(res['body'])[0]['productCode']
                        except:
                            product_from_response = None

                        break
                    except Exception as e:
                        # print(f"Request {req_id} ยังไม่มี response: {e}")
                        continue

                print("resp: ", res)
                print("sku from res: ", product_from_response)
                if res:
                    print("ได้ response แล้ว")
                    break
                time.sleep(0.1)

            self.price_setter(sku=product_from_response, srp=srp)

        except Exception as err:
            print("Shipment cost skipped")
            print(err)
