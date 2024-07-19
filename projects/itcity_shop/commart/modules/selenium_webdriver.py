from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.abstract_event_listener import AbstractEventListener
from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium import webdriver
from webdriver_auto_update.chrome_app_utils import ChromeAppUtils
from webdriver_auto_update.webdriver_manager import WebDriverManager

import sys
import os
import subprocess
import shutil
import re
import time

import traceback
import logging
from logging.handlers import RotatingFileHandler

# * Configure logging to write to a rotating log file
handler = RotatingFileHandler(
    filename='chromedriver.log', maxBytes=1000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# * Create a logger and attach the handler
logger = logging.getLogger()
logger.addHandler(handler)

# * MainClass


class ChromeDriver:
    def __init__(self, *args, **kwargs):
        try:
            self.update_bot_status = kwargs['update_bot_stat_fn']
            self.app = kwargs['app']
            # if 'update_bot_stat_fn' in kwargs:
            #     self.update_bot_status = kwargs['update_bot_stat_fn']
            #     self.app = kwargs['app']
            self.setup_chrome()
        except Exception as e:
            tb_str = traceback.print_exc()
            print('Classs ChromeDriver has stopped working')
            raise ValueError('Traceback: ', tb_str)

        self.wait1 = WebDriverWait(self.driver, 50)
        self.get_tabs()

    def setup_chrome(self):
        print("setup_chrome")
        self.opt = Options()
        # * ใช้เพื่อเก็บที่อยู่ของไฟล์ที่ถูก execute ด้วย Python ผ่าน command line arguments ในตัวแปร exepath ซึ่ง sys.argv[0] คือชื่อของไฟล์ Python script ที่ถูกเรียกใช้งาน
        exepath = sys.argv[0]

        Dir_path = os.path.dirname(os.path.abspath(exepath))
        self.custom_path = r'D:\\bin\\'

        os.environ["WDM_LOCAL"] = self.custom_path
        # print("มีไรบ้างใน obj Options:", dir(self.opt))
        self.opt.add_experimental_option("debuggerAddress", "localhost:8989")
        # self.opt.add_argument("--disable-popup-blocking")
        # self.opt.add_experimental_option("prefs",{
        #     "download.default_directory" : Download_dir,
        #     "directory_upgrade": True
        # })

        #! อันเก่า
        # self.driver = webdriver.Chrome(
        #     service=Service(r'C:\bin\chromedriver.exe'),
        #     options=self.opt
        # )

        # ?? อันใหม่ทดลอง
        try:
            print("create driver")
            # * error มันจะเกิดแถวนี้
            self.driver = webdriver.Chrome(
                service=Service(r'C:\bin\chromedriver.exe'),
                options=self.opt
            )

            print("driver created")

        except:
            traceback_str = traceback.format_exc()
            print("Cannot Create Driver")
            print(traceback_str)
            chrome_app_utils = ChromeAppUtils()
            chrome_app_version = chrome_app_utils.get_chrome_version()
            print("Chrome version: ", chrome_app_version)

            # * Target directory to store chromedriver
            driver_directory = 'C:/bin'

            # * Create an inst of WebDriverManager
            driver_manager = WebDriverManager(driver_directory)

            # * Call the main method to manage chromdriver
            try:
                driver_manager.main()
                # * check_driver() ใช้ปุ๊บมันจะทำการตรวจและโหลดเลย
                driver_manager.check_driver()
            except Exception as err:

                print('error from driver_manager.main()')
                print(err)
                raise

            self.driver = webdriver.Chrome(
                service=Service(r'C:\bin\chromedriver.exe'),
                options=self.opt
            )

    def get_tabs(self):
        try:
            # if self.parent.winfo_exists():
            if True:
                print("รายงานจำนวนtabs")

                # * เก็บชื่อ title และ value ของ tab ที่เปิดอยู่
                self.title_list = []
                # self.title_list_Idx = [] #!เหมือนจะไม่ได้ใช้
                self.value_list = []
                # self.title_dict = {} #!เหมือนจะไม่ได้ใช้
                for idx, handle in enumerate(self.driver.window_handles):
                    self.driver.switch_to.window(handle)
                    # self.title_list_Idx.append(
                    #     self.driver.title + "["+str(idx)+"]") #!เหมือนจะไม่ได้ใช้
                    self.title_list.append(self.driver.title)

                    self.value_list.append(self.driver.current_window_handle)
                    # self.title_dict.update(
                    #     {self.driver.title: self.driver.current_window_handle}) #!เหมือนจะไม่ได้ใช้

                # * เอาtitle มาทำให้ unique เพราะ title จะสามารถที่จะซ้ำกันได้
                self.unique_titles = []
                self.counter = {}
                for item in self.title_list:
                    if item in self.counter:
                        self.counter[item] += 1
                        print("counter[item] คือไร: ", self.counter[item])
                        self.unique_titles.append(
                            f"{item}{self.counter[item]-1}")
                    else:
                        self.counter[item] = 1
                        self.unique_titles.append(item)

                # * เอาList มารวมกัน
                self.merged_dict = dict(
                    zip(self.unique_titles, self.value_list))
                print("มี tabs ไรบ้าง", self.merged_dict)
                self.operation_start()
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(f"An error occirred: {e}")
            print(traceback_str)
            # logger.debug('This is a debug message')
            # logger.info('This is an info message')
            logger.warning(f"'method get_tabs()', {traceback_str}")
            # logger.error('This is an error message')
            # logger.critical('This is a critical message')

    def enter_cus_name(self, cus_search):
        # * จับตาดูว่า ul เปิดอยู่ไหม
        self.is_ul_not_open = False if self.driver.find_elements(
            By.XPATH, '/html/body/span/span/span[2]/ul') else True
        # * กรณีไม่ได้เปิดไว้ จะเปิดให้
        if self.is_ul_not_open:
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[2]').click()

            self.wait1.until(EC.visibility_of_element_located(
                (By.XPATH, '/html/body/span/span/span[1]/input')))
        # * เคลียและกรอกชื่อลูกค้า
        self.driver.find_element(
            By.XPATH, '/html/body/span/span/span[1]/input').clear()
        self.driver.find_element(
            By.XPATH, '/html/body/span/span/span[1]/input').send_keys(cus_search)

    def find_and_enter_cus_name(self):
        ### * SMCO PART ############################################################################
        # * เปลี่ยนไปtab SMCO0 เพื่อเช็ค ชื่อลูกค้า
        self.driver.switch_to.window(
            self.merged_dict['SMCO :: เปิดการขาย'])

        # * ดูก่อนว่าเคลียชื่อลูกค้าแล้วเหรอยัง
        self.cus_name_span_elmt = self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]/span')
        self.cus_name_span_text = self.cus_name_span_elmt.text
        if self.cus_name_span_text == 'Please select':
            self.is_reset = False
        elif self.cus_name_span_text == 'กรุณาเลือก':
            self.is_reset = False
        else:
            self.is_reset = True
            print("มีชื่อลูกค้าอยู่แล้ว")

        try:
            print("เช็คว่าต้องรีไหม", self.is_reset)
            if self.is_reset:
                print("รีนี่หว่า, กดรีเลย")
                self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]/span').click()
                try:
                    # คลิกเพื่อให้ปิด droprdown
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]').click()
                except:
                    # * ถ้ามีสินค้าจะ error คลิกไม่ได้จะกลายเป็น except
                    try:
                        print("wait for pop-up(try)")
                        # ระบุปุ่ม ok
                        if self.driver.find_element(By.XPATH, '/html/body/div[16]/div[2]/button[1]'):
                            print("has pop-up(try)")
                            self.driver.find_element(
                                By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()
                            print("Click OK(try)")

                    except:
                        print("wait for pop-up(except)")
                        time.sleep(1)
                        # * ระบุปุ่ม ok
                        if self.driver.find_element(By.XPATH, '/html/body/div[16]/div[2]/button[1]'):
                            print("has pop-up(except)")
                            self.driver.find_element(
                                By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()
                            print("Click OK(except)")
                    # * ถ้ามีสินค้าแล้วกดลบชื่อ มันจะมีชื่อค้างอยู่แต่สินค้าหายต้องกดอีกรอบ
                    try:
                        self.driver.find_element(
                            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]/span').click()
                        print("Cusname still appear the btn 'x' is available.")
                    except:
                        print("Cusname has disappeared no 'x' to press.")

                print("หน้าใหม่พร้อมแล้ว")
            elif self.is_reset == False:
                print("ไม่ต้องรี")
        except Exception as err:
            print("Error From SMCO phase1 Resetting", err)
            while True:
                print("รอ")
                time.sleep(1)
                if self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[1]/label/div/button'):
                    print("เจอแล้ว")
                    break
                else:
                    continue

        print("ผ่านเคลียชื่อลูกค้า, รอ element โผล่")

        self.wait1.until(EC.element_to_be_clickable(
            (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/button')))

        time.sleep(1)
        # * เปลี่ยน auto เป็น name ไม่ก็ email โดยขึ้นอยู่กับว่าขอใบกำกับหรือไม่
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/button').click()
        print("self.app.cus_is_fulltax: ", self.app.cus_is_fulltax.get())

        # * จากปัญหาข้อที่ 39 // รอให้ตัวเลือกภายใน click ได้ก่อน แล้วค่อย เลือก วิธีการ search
        self.wait1.until(EC.element_to_be_clickable(
            (By.XPATH, r'''/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/div/a[contains(@ng-click, "st='E'")]''')))
        if self.app.cus_is_fulltax.get() == True:
            print("ขำใบกำกับใช้ T:")
            self.driver.find_element(
                By.XPATH, r'''/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/div/a[contains(@ng-click, "st='T'")]''').click()

        elif self.app.cus_is_fulltax.get() == False:
            # ไม่ขอใบกำกับ
            print("ไม่ขอใบกำกับใช้ N:")
            self.driver.find_element(
                By.XPATH, r'''/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/div/a[contains(@ng-click,"st='N'")]''').click()

        self.cus_search_input = self.app.cus_tax_num.get() if self.app.cus_is_fulltax.get(
        ) else f"""{self.app.cus_fname.get()} {self.app.cus_lname.get()} {self.app.cus_tel.get()}"""

        # * ถ้าเปิดแล้วจะข้ามมานี่
        self.enter_cus_name(self.cus_search_input)
        print("กรอกชื่อเสร็จ")
        # * wait_situation มันจะเจอ cusNameLi1 ที่ containค่า "Searching..."
        self.wait_situation = self.driver.find_element(
            By.XPATH, '/html/body/span/span/span[2]/ul/li')
        # * มันจะได้ Searching...
        print("มันทำไม", self.wait_situation.text)

        # * ตาม Stepแล้วนั้น ขั้นตอนด้านบนจะทำให้ Dropdown UL มันโผล่ และมี li อย่างน้อย 1 อัน => li[1] โดย li[1] จะบอกสถานะของการ search ตั้งแต่ "Searching...", "No results found", ไม่แน่ใจมีอีกไหม และบอก ผลลัพธ์ที่เจอลำดับแรก
        self.customer_added_times = 0
        self.customer_name_search_count = 0
        while True:
            if self.driver.find_element(By.XPATH, '/html/body/span/span/span[2]/ul'):
                time.sleep(0.7)
                # self.wait1.until(EC.visibility_of_element_located(
                #     (By.XPATH, '/html/body/span/span/span[2]/ul/li')))

                # * li[1] เป็นตัวที่แสดงผลแบบ dynamic เราจะตรวจจับ พฤติกรรมของ element นี้
                self.wait_situation = self.driver.find_element(
                    By.XPATH, '/html/body/span/span/span[2]/ul/li')

                # * ช่วงรอ ผลลัพของ Searching...
                try:
                    if self.wait_situation.text == "Searching...":
                        continue
                    elif self.wait_situation.text:
                        print("text element disappeared")
                        pass
                except:
                    pass

                # * หลังจาก Searching... หายไป ๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑
                self.wait1.until(EC.visibility_of_element_located(
                    (By.XPATH, '/html/body/span/span/span[2]/ul/li')))
                self.wait_situation = self.driver.find_element(
                    By.XPATH, '/html/body/span/span/span[2]/ul/li')

                # * กรณี ไม่เจอผลลัพธ์ ทำการ Add ใหม่
                if self.wait_situation.text == "No results found" and self.customer_added_times == 0:
                    print("No results found and NeverAdd")

                    # * ใช้ function เพิ่มลูกค้าใหม่
                    self.add_new_cusname()

                    # * ตรวจสอบว่ามันเป็นการเพิ่มลูกค้าหรือไม่
                    self.is_continue_progress = False
                    try:
                        if self.is_cus_name_submitted:
                            print("เติม Products ลงไป")
                            self.is_continue_progress = True
                        else:
                            print("มันเปนการยกเลิกไม่ใช่การเพิ่มลูกค้า")
                            self.is_continue_progress = False
                    except:
                        self.is_continue_progress = True
                        print("ชื่อลูกค้ามีอยู่แล้ว แอดของได้เลย")

                    # * มีชื่อลูกค้าแล้วลองกรอกใหม่อีกรอบหลัง add_new_cusname
                    # * เพิ่มจำนวนครั้งที่ add
                    if self.is_continue_progress:
                        self.customer_added_times += 1
                        self.driver.switch_to.window(
                            self.merged_dict['SMCO :: เปิดการขาย'])
                        print("ก่อนRe Enter ชื่อลูกค้า")
                        self.enter_cus_name(self.cus_search_input)
                        print(f"Re enter name after add")
                        continue
                    else:
                        break

                # * หลังจาก Add ไปแล้วรอบนึง แล้วมาเสิชใหม่แล้วยังไม่เจอ ถึงจะเข้าเงื่อนไขนี้ เป็นการ search ให้อีกรอบนึง
                elif self.wait_situation.text == "No results found" and self.customer_name_search_count < 1:
                    self.enter_cus_name(self.cus_search_input)
                    self.customer_name_search_count += 1
                    print(
                        f"Re enter name after add extra times{self.customer_name_search_count}")
                    continue

                # * Add แล้ว รีเสิชให้สองรอบแล้ว ก็ยังไม่เจอ ลองแอดด้วยตัวเองดู
                elif self.wait_situation.text == "No results found" and self.customer_added_times == 1:
                    print(
                        "I've already add it, but the element still shows 'No results found', you have to add by yourself")
                    break
                else:
                    print("The cusname has been added already")
                    self.is_continue_progress = True
                    self.driver.switch_to.window(
                        self.merged_dict['SMCO :: เปิดการขาย'])
                    break
            print("addcustomer and select While end!")
            break

        if self.is_continue_progress:
            # !66 WIP เปลี่ยนวิธีเลือกชื่อลูกค้า เดิมทีคือเลือก
            while True:
                try:
                    customer_name_input_ul = self.driver.find_element(
                        By.XPATH, '/html/body/span/span/span[2]/ul')
                    customer_name_dropdown_lis = customer_name_input_ul.find_elements(
                        By.CSS_SELECTOR, '.select2-results__option')
                    print(f"""หาจำนวน li ชื่อลูกค้าเท่ากับ: {
                          len(customer_name_dropdown_lis)} {customer_name_dropdown_lis}""")
                    break

                except:
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[2]').click()
                    continue

            if len(customer_name_dropdown_lis) > 1:
                print("มากกว่า 1")
                li_names = [
                    element.text for element in customer_name_dropdown_lis]
                self.select_cus_name_from_lis(
                    li_names, self.select_cus_name_from_lis)
                print("click แล้ว")
            else:
                self.driver.find_element(
                    By.XPATH, '/html/body/span/span/span[2]/ul/li').click()
                print("Click the cusname li result")

            # * กรณีมีสินค้ายิงไปแล้ว แล้วมีการเปลี่ยนชื่อลูกค้า มันจะมี alert // path นี้คือ element นอกของ alert /html/body/div[16]/div[2]
            if self.driver.find_element(By.XPATH, "/html/body/div[16]/div[2]").is_displayed():
                try:
                    self.driver.find_element(
                        By.XPATH, "/html/body/div[16]/div[2]/button[1]").click()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[2]').click()
                    self.wait1.until(EC.visibility_of_element_located(
                        (By.XPATH, '/html/body/span/span/span[1]/input')))
                except:
                    print("Skip, Alert Element is appear but can not perform actions.")
            else:
                print("Skip, Alert Element is Not appear")
                pass

            print("search หายไปแล้ว")
            self.wait1.until(EC.invisibility_of_element_located(
                (By.XPATH, '/html/body/span/span/span[1]/input')))

    def add_new_cusname(self):
        # * ตัวแปรที่เกี่ยวข้อง
        self.is_cus_name_submitted = False

        # * จับตาดูว่า ul เปิดอยู่ไหม
        self.is_ul_open = True if self.driver.find_elements(
            By.XPATH, '/html/body/span/span/span[2]/ul') else False
        # * กรณีไม่ได้เปิดไว้ จะเปิดให้
        if self.is_ul_open:
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[2]').click()

        if self.app.cus_is_fulltax.get():
            print("มีใบกำกับ")
            self.add_tax_customer()
        else:
            print("ไม่มีใบกำกับ")
            self.add_normal_customer()

        # * รอผู้ใช้กดยืนยัน เพิ่มชื่อลูกค้า
        self.update_bot_status(is_bot_working=False,
                               display_text="รอผู้ใช้เพิ่มชื่อลูกค้า")
        print("Now in add_new_cusname form")
        while True:
            # print("ใน while loop")
            time.sleep(0.75)
            try:
                self.is_add_form_displayed = self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').is_displayed()
                # print("self.is_add_form_displayed: ",
                #       self.is_add_form_displayed)
            except:
                print("self.is_add_form_displayed error")
                continue

            if self.is_add_form_displayed:
                print("cus_add_form_display")
                while True:
                    try:
                        self.popup_after_adding = self.driver.find_element(
                            By.XPATH, '/html/body/div[16]/div[2]/button[1]')
                        self.is_submitted_popup_displayed = self.popup_after_adding.is_displayed()
                        if self.is_submitted_popup_displayed:
                            self.update_bot_status(is_bot_working=True)
                            self.is_cus_name_submitted = True
                            self.popup_after_adding.click()
                        else:
                            break
                    except:
                        continue

            else:
                print("ปิดแล้ว")
                break
        self.update_bot_status(is_bot_working=True)
        print("เลย while มาแล้ว")

    def add_skus(self):
        if self.is_continue_progress:
            self.fill_items(self.app.cus_purchased_products)
            self.fill_items(self.app.cus_purchased_premiums)
        else:
            print("add_skus: No progress")

    def fill_items(self, array_items=[]):
        print("array_items: ", array_items)
        self.sku_input_xpath = '/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input'

        for item in array_items:
            print("item: ", item)
            self.driver.find_element(By.XPATH, self.sku_input_xpath).clear()
            self.driver.find_element(
                By.XPATH, self.sku_input_xpath).send_keys(item['code_Itcity'])
            self.driver.find_element(
                By.XPATH, self.sku_input_xpath).send_keys(Keys.ENTER)

    def add_normal_customer(self):
        name = f"""{self.app.cus_fname.get()} {self.app.cus_lname.get()} {
            self.app.cus_tel.get()}"""

        self.driver.switch_to.window(
            self.merged_dict['SMCO :: เปิดการขาย'])

        # * กดปุ่มแว่นขยาย
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[7]/a').click()
        time.sleep(0.75)

        # * กดปุ่มสร้าง//Create
        while True:
            try:
                is_btn_found = self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[1]/div[2]/button[1]').is_displayed()
                if is_btn_found:
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[1]/div[2]/button[1]').click()
                    break
                else:
                    print("element is not displayed")
                    continue
            except:
                traceback_str = traceback.format_exc()
                print("พังตอนหาปุ่ม create: ", traceback_str)
                continue
        # self.btnElement = self.wait1.until(
        #     EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[1]/div[2]/button[1]')))
        # time.sleep(0.65)
        # self.btnElement.click()  # create

        # * > เลือกหมวดลูกค้า  เพิ่มมาตอน 6.3.1 24/04/2024
        try:
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[1]/div[3]/div/span/span[1]/span/span[1]').click()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()
            time.sleep(0.75)
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[2]/ul/li').click()
        except:
            print("No customer category, Pass")

        # * > nameTH clear
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').clear()
        # # * >nameTH fill input better style ปิดการใช้งาน
        # self.driver.find_element( By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(f'{name} Tax ID: {self.app.cus_tax_num.get()}')
        # * >nameTH SMCO style
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(f'{name}')

        # * >nameEN clear
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').clear()
        # * >nameEN fill input better style ปิดการใช้งาน
        # self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(f'{name} Tax ID: {self.app.cus_tax_num.get()}')
        # * >nameEN SMCO style
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(f'{name}')

        # * กรอก Address
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').clear()
        # ! > การกรอก address แบบโกง bypass เขตแขวง SMCO แต่กลัวว่า สรรพากรจะกำหมัด
        # self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(self.app.cus_address)
        # ! > การกรอก address แบบทำตามกฎเลือก เขตแขวง ตามระบบ SMCO แต่กลัวว่า สรรพากรจะกำหมัด
        address = self.app.cus_address
        print("ข้างใน addressมีค่าไหม: ", self.app.cus_address)
        # if self.app.cus_is_fulltax.get():
        #     address = self.app.get_pure_address(self.app.cus_address)
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(address)

        # * tel.
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').clear()
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(self.app.cus_tel.get())

        # * ปุ่มบันทึกเขียวๆ
        self.save_button_location = "/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]"

        # # * กด Save
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()

        # * รอมันหายก่อนแล้วค่อยจบ function เพื่อไม่ให้ขั้นตอนต่อไปทำงานเร็วเกินไป
        # self.wait1.until(EC.invisibility_of_element_located(
        #     (By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]')))

        # while True:
        #     try:
        #         is_add_page_present = self.driver.find_element(
        #             By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').is_displayed()
        #     except:
        #         continue

        #     if is_add_page_present:
        #         continue
        #     else:
        #         break

        # *  24/04/2023: กลับมาอีกแล้วทำให้เป็น try except ละกัน// 09/11/2023: partนี้ ทาง SMCO ลบออกไปแล้ว
        # self.wait1.until(EC.visibility_of_element_located(
        #     (By.XPATH, '/html/body/div[16]/div[2]/button[1]')))
        # * สำหรับกดปิด pop-up ไอนี่จะเด้งทีหลัง
        # try:
        #     self.driver.find_element(
        #         By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()
        # except:
        #     pass

    def add_tax_customer(self):
        if self.app.cus_tax_type.get() != "Individual":
            name = self.app.cus_tax_name.get()
        else:
            name = self.app.cus_fname.get() + " " + self.app.cus_lname.get()

        self.driver.switch_to.window(
            self.merged_dict['SMCO :: เปิดการขาย'])

        # * กดปุ่มแว่นขยาย
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[7]/a').click()
        time.sleep(0.75)

        # * กดปุ่มสร้าง//Create
        while True:
            try:
                is_btn_found = self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[1]/div[2]/button[1]').is_displayed()
                if is_btn_found:
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[1]/div[2]/button[1]').click()
                    break
                else:
                    print("element is not displayed")
                    continue
            except:
                traceback_str = traceback.format_exc()
                print("พังตอนหาปุ่ม create: ", traceback_str)
                continue
        # self.btnElement = self.wait1.until(
        #     EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[1]/div[2]/button[1]')))
        # time.sleep(0.65)
        # self.btnElement.click()  # create

        # * > เลือกหมวดลูกค้า  เพิ่มมาตอน 6.3.1 24/04/2024
        try:
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[1]/div[3]/div/span/span[1]/span/span[1]').click()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()
            time.sleep(0.75)
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[2]/ul/li').click()
        except:
            print("No customer category, Pass")

        # * > nameTH clear
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').clear()

        # * >nameTH SMCO style
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(f'{name}')

        # * >nameEN clear
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').clear()
        # * >nameEN fill input better style ปิดการใช้งาน
        # self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(f'{name} Tax ID: {self.app.cus_tax_num.get()}')
        # * >nameEN SMCO style
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(f'{name}')

        # ! เปิดใช้การออกใบกำกับ ตาม SMCO style (ถ้าไม่เปิดจะถือว่าเป็นการใช้ Better style)
        # * clear Identity ID
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[3]/input').clear()
        # * Identity ID
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[3]/input').send_keys(self.app.cus_tax_num.get())

        # * tel.
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').clear()
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(self.app.cus_tel.get())

        # * ปุ่มบันทึกเขียวๆ
        self.save_button_location = "/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]"

        # # * กด Save
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()

        # * รอมันหายก่อนแล้วค่อยจบ function เพื่อไม่ให้ขั้นตอนต่อไปทำงานเร็วเกินไป
        # self.wait1.until(EC.invisibility_of_element_located(
        #     (By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]')))
        # while True:
        #     try:
        #         is_add_page_present = self.driver.find_element(
        #             By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').is_displayed()
        #     except:
        #         continue

        #     if is_add_page_present:
        #         continue
        #     else:
        #         break

        # *  24/04/2023: กลับมาอีกแล้วทำให้เป็น try except ละกัน// 09/11/2023: partนี้ ทาง SMCO ลบออกไปแล้ว
        # self.wait1.until(EC.visibility_of_element_located(
        #     (By.XPATH, '/html/body/div[16]/div[2]/button[1]')))
        # * สำหรับกดปิด pop-up ไอนี่จะเด้งทีหลัง
        # try:
        #     self.driver.find_element(
        #         By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()
        # except:
        #     pass

    def select_cus_name_from_lis(self, names, cb=""):
        cus_desire_name = self.app.cus_display_name.get().replace(" ", "")
        branch = self.app.cus_tax_branch.get().replace(" ", "")
        if branch == '00000':
            branch = 'สำนักงานใหญ่'

        # * ทำการคัดเอาเฉพาะชื่อลูกค้า ลง array ไม่เอารหัส
        names_no_code = names.copy()
        for i in range(len(names)):
            prog = re.search(r'[^-]-(.*)', names_no_code[i])
            names_no_code[i] = prog.group(1).replace(" ", "")

        for i, name in enumerate(names_no_code):
            print("if ", cus_desire_name, " In ", name)
            if cus_desire_name in name and branch in name:
                print("ชื่อที่ต้องการ อยู่ใน li")
                while True:
                    try:
                        print(f"""เลือกชื่อลูกค้าลำดับที่ {i+1} {names[i]}""")
                        # * 1st way error
                        # self.driver.find_element(
                        #     By.XPATH, f"//*[text()='{names[i]}']").click()

                        # * 2nd way error
                        # target = self.driver.find_element(By.XPATH, f"//*[text()='{names[i]}']")
                        # target.click()

                        # * 3rd way trying
                        self.driver.find_element(
                            By.XPATH, f"/html/body/span/span/span[2]/ul/li[{i+1}]").click()

                        break
                    except:

                        continue
                return
            # * ถ้ามันเจอก็จะ break ไม่เจอค่อย cb
        try:
            if cb:
                print("use callback")
                cb(names)

            # * cb ให้รอบนึงแล้วก็ไม่เจอ แอดใหม่ให้
            # print('ไม่เจอ แอดใหม่ เปลี่ยนชื่อให้ด้วย')
            # self.cus_search_input = self.app.cus_name.get()
            # self.add_new_cusname()
        except:
            print("cb doesn't works")

        # * มันจะมีกรณีที่ถ้าเลือกลูกค้าได้ในครั้งแรก cb จะไม่ทำงานในส่วนนี้
        try:
            if cb:
                cb(names)
        except:
            print("cb doesn't works")

        # * มันจะมีกรณีที่ถ้าเลือกลูกค้าได้ในครั้งแรก cb จะไม่ทำงานในส่วนนี้

    def operation_start(self):
        print("chrome started!!")
        print("self.app.cus_is_hq.get(): ", self.app.cus_is_fulltax.get())

        try:
            self.find_and_enter_cus_name()
            self.add_skus()
        except Exception as e:
            # * ถ้าพังให้ข้าม
            traceback_str = traceback.format_exc()
            print("พัง: ", traceback_str)

        print("chrome finished!!")
        self.update_bot_status(is_bot_working=False)
