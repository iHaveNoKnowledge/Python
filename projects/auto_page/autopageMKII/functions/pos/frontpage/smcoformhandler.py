import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class SMCOFormHandler:
    def __init__(self, bot, logger):
        self.bot = bot
        self.driver = bot.driver
        self.logger = logger
        self.wait50 = WebDriverWait(self.driver, 50)
        self.payment_type_dict = {
            "SITO1": "Online Sale",
            "SITL1": "AR Online LAZ",
            "SITS1": "AR Online SHP",
            "SXTO1": "ไม่รู้ มีทั้ง AR Online และ Online sale",
            "STIKTO": "AR Online TIK",
            "SOULIT": "Online Sale",
            "SWGIT": "AR Online SHP - Wise Gadget ",
            "SITLE": "AR Online SHP - IT CITY LENOVO ",
            "SAMAIT-AMAZEITCITY": "AR Online AMAZE ITCITY ",
        }

    def __getattr__(self, name):
        return getattr(self.bot, name)

    @property
    def app(self):
        return self.bot.app

    @property
    def user_id(self):
        return self.bot.app.user_id.get()

    def ensure_customer_name(self):
        # * ดูก่อนว่าเคลียชื่อลูกค้าแล้วเหรอยัง
        self.cus_name_span_elmt_dir = '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]'
        self.cus_name_span_x_btn_text = ""
        self.is_reset = False
        while not self.operation_thread.is_set():
            try:
                self.cus_name_span_elmt = self.driver.find_element(By.XPATH, self.cus_name_span_elmt_dir)
                self.cus_name_span_x_btn_text = self.cus_name_span_elmt.text
                print("เจอ element cus_name_span_elmt")
                break
            except:
                print("ยังไม่เจอ element cus_name_span_elmt")
                time.sleep(0.5)
                continue

        if self.cus_name_span_x_btn_text == 'Please select':
            self.is_reset = False
        elif self.cus_name_span_x_btn_text == 'กรุณาเลือก':
            self.is_reset = False
        else:
            self.is_reset = True
            print("มีชื่อลูกค้าอยู่แล้ว")

        try:
            print("เช็คว่าต้องรีไหม", self.is_reset)
            if self.is_reset:
                print("รีนี่หว่า, กดรีเลย")
                self.driver.find_element(By.XPATH, self.cus_name_span_elmt_dir).click()
                items_list = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
                if len(items_list) == 0:
                    # * คลิกเพื่อให้ปิด droprdown
                    self.driver.find_element(By.XPATH, self.cus_name_span_elmt_dir).click()
                    print("ปิด dropwdown กรณีไม่มีสินค้า")
                else:
                    # * ถ้ามีสินค้าจะ error คลิกไม่ได้จะกลายเป็น except
                    print("กรณีมีสินค้า")
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]/span').click()
                    try:
                        print("wait for pop-up(try)")
                        # ระบุปุ่ม ok
                        if self.driver.find_element(By.XPATH, '/html/body/div[24]/div[2]/button[1]'):
                            print("has pop-up(try)")
                            self.driver.find_element(By.XPATH, '/html/body/div[24]/div[2]/button[1]').click()
                            print("Click OK(try)")
                    except:
                        print("wait for pop-up(except)")
                        time.sleep(1)
                        # * ระบุปุ่ม ok
                        if self.driver.find_element(By.XPATH, '/html/body/div[24]/div[2]/button[1]'):
                            print("has pop-up(except)")
                            self.driver.find_element(By.XPATH, '/html/body/div[24]/div[2]/button[1]').click()
                            print("Click OK(except)")
                    # * ถ้ามีสินค้าแล้วกดลบชื่อ มันจะมีชื่อค้างอยู่แต่สินค้าหายต้องกดอีกรอบ
                    try:
                        self.driver.find_element(By.XPATH, self.cus_name_span_elmt_dir).click()
                        print("Cusname still appear the btn 'x' is available.")
                    except:
                        print("Cusname has disappeared no 'x' to press.")

                print("หน้าใหม่พร้อมแล้ว")
            elif self.is_reset == False:
                print("ไม่ต้องรี")
        except Exception as err:
            print("Error From SMCO phase1 Resetting", err)
            self.logger.info("Error From SMCO phase1 Resetting", err)
            while not self.operation_thread.is_set():
                print("รอ")
                time.sleep(1)
                if self.driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div[2]/div[1]/label/div/button'):
                    print("เจอแล้ว")
                    break
                else:
                    continue

        print("ผ่านเคลียชื่อลูกค้า, รอ element โผล่")

        self.wait50.until(EC.element_to_be_clickable(
            (By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/button')))
        time.sleep(1)

        # * เปลี่ยน auto เป็น name ไม่ก็ email โดยขึ้นอยู่กับว่าขอใบกำกับหรือไม่
        self.driver.find_element(
            By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/button').click()
        print("self.app.tax_bool: ", self.app.tax_bool.get())

        # * จากปัญหาข้อที่ 39 // รอให้ตัวเลือกภายใน click ได้ก่อน แล้วค่อย เลือก วิธีการ search
        self.set_cus_name_search_type()

        # * ดูว่า self.cus_search_input จะต้องถูกกำหนดค่าเป็นเลขใบกำกับหรือชื่อ อิงจาก tax_bool choosing by ternary like conditional
        # 09/11/2023 ใช้เลขใบกำกับเสิชไม่ได้แล้ว ฉะนั้นไม่ต้องเลือกแล้ว เอาชื่อเสิชให้หมดเลย

        # if self.app.marketplace_target.get() == "SHOPEE":
        #     self.cus_search_input = self.app.cus_email.get() if self.app.tax_bool.get(
        #     ) else self.app.cusNameFixer5(self.app.cus_name.get(), self.app.cus_account_name.get())
        # elif self.app.marketplace_target.get() == "LAZADA":
        #     self.cus_search_input = self.app.tax_num.get() if self.app.tax_bool.get(
        #     ) else self.app.cusNameFixer5(self.app.cus_name.get(), self.app.cus_account_name.get())

        # * 05/07/2024 Shopeeนั้นได้ลบ ชื่อลูกค้าแบบ ธรรมดา ออกไปอย่างถาวร จึงต้องปรับวิธีออกบิลให้กับแบบธรรมดาโดยการใช้ "account"+" ชื่อที่เป็นดอกจัน"+" หมายเลขโทรศัพท์"
        # self.cus_search_input = self.app.tax_num.get() if self.app.tax_bool.get(
        # ) else self.app.cusNameFixer5(self.app.cus_name.get(), self.app.cus_account_name.get())

        if self.app.marketplace_target.get() == "SHOPEE":
            self.cus_search_input = self.app.tax_num.get() if self.app.tax_bool.get() else self.app.cusNameFixer5(self.app.cus_name.get())
        elif self.app.marketplace_target.get() == "LAZADA":
            self.cus_search_input = self.app.tax_num.get() if self.app.tax_bool.get(
            ) else self.app.cusNameFixer5(self.app.cus_name.get(), self.app.cus_account_name.get())

        # * เริ่มกระบวนการหาชื่อลูกค้าสำหรับออกบิล invoice
        self.get_customer_name_ready(self.cus_search_input)

        # * ใส่ตัวเช็คที่อยู่ลูกค้า
        if self.app.tax_bool.get():
            print("tax required, start address check and correct")
            self.smco_cus_address_element = self.driver.find_element(
                By.XPATH,
                '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[14]/div[2]/div[1]/span/span[1]/span/span[1]')
            self.cus_name_span = self.driver.find_element(
                By.XPATH,
                '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]')
            # * ที่กล้าเก็บค่า attribute มาใช้ตรงๆแบบนี้เพราะต่อให้ไม่มี attribute มันก็ return ค่าว่างอยู่ดี
            self.text_from_name_span = self.cus_name_span.get_attribute("title")
            self.tax_address_corrector(self.text_from_name_span)

        else:
            print("no tax required, skip address check")

    def dropdown_handler(self):
        while not self.operation_thread.is_set():
            try:
                li_locators = self.driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
                print("li_locators.text: ", li_locators[0].text)
                if not "Searching" in li_locators[0].text:
                    break
                time.sleep(0.30)

            except:
                time.sleep(0.30)
                continue
        return "dropdown is ready!"

    def insert_emp(self):
        self.smco_current_emp = self.driver.find_element(
            By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]').text
        if not self.user_id in self.smco_current_emp:
            self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]').click()
            self.driver.find_element(By.XPATH, '/html/body/span/span/span[1]/input').send_keys(self.user_id)
            while not self.operation_thread.is_set():
                time.sleep(0.25)
                try:
                    if self.user_id in self.driver.find_element(
                            By.XPATH, '/html/body/span/span/span[2]/ul/li').text:
                        self.driver.find_element(By.XPATH, '/html/body/span/span/span[2]/ul/li').click()
                        print("Found and select")
                        break

                except:
                    continue

    def select_sale_type(self):
        self.driver.find_element(
            By.CSS_SELECTOR, '#contentZen > div.ng-scope > div:nth-child(2) > div.panel-body > div.col-sm-3 > div.col-sm-12.nopadding > div.panel-body > div > div > div:nth-child(2) span.select2-selection__arrow').click()
        time.sleep(0.25)
        self.dropdown_handler()
        while not self.operation_thread.is_set():
            try:
                self.driver.find_element(
                    By.XPATH, '//*[@id="select2-divSaletype2-results"]/li[text()="AR Online SHP"]').click()
                print("เจอ element cus_name_span_elmt")
                break
            except Exception as err:
                print("ยังไม่เจอ li ให้เลือก")
                print("select_sale_type Error: ", err)
                time.sleep(0.5)
                continue
