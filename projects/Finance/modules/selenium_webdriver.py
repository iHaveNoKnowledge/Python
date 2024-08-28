from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from webdriver_auto_update.chrome_app_utils import ChromeAppUtils
from webdriver_auto_update.webdriver_manager import WebDriverManager
from selenium.webdriver.support.ui import WebDriverWait

import sys
import os
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
            pass
            # self.update_bot_status = kwargs['update_bot_stat_fn']
            # self.app = kwargs['app']
            
        except Exception as e:
            tb_str = traceback.print_exc()
            print('Classs ChromeDriver has stopped working')
            raise ValueError('Traceback: ', tb_str)
        
        self.setup_chrome()
        self.wait1 = WebDriverWait(self.driver, 50)
        self.get_tabs()


    def setup_chrome(self):
        print("setup_chrome")
        self.opt = Options()
        # * exepath จะมีค่าเป็น relativepath
        exepath = sys.argv[0]
        # * abspath() ใช้เพื่อแปลงที่อยู่ของไฟล์ที่เป็น relative path ให้เป็น absolute path เช่นถ้าไฟล์อยู่ใน "/home/user/documents" และเราใช้ abspath() กับไฟล์นั้น ผลลัพธ์ที่ได้จะเป็น "c:/bla_bla/xxx/home/user/documents/file.txt" โดยที่ไม่ว่า working directory จะอยู่ที่ไหนก็ตาม
        # * dirname() ใช้สำหรับดึงชื่อ directory จากที่อยู่ของไฟล์หรือ directory path ที่ให้มา และส่งคืนเป็นชื่อ directory เท่านั้นโดยไม่รวมชื่อไฟล์หรือส่วนท้ายของ path ถ้า path ที่ให้มาเป็น directory path จะคืนค่าเป็นชื่อ directory ตรงไปด้วย เช่นถ้า path เป็น "c:/bla_bla/xxx/home/user/documents/file.txt" ซึ่งเป็นที่อยู่ของไฟล์ ฟังก์ชัน dirname() จะคืนค่า "c:/bla_bla/xxx/home/user/documents" โดยที่ไม่รวมชื่อไฟล์ "file.txt" ด้วย
        Dir_path = os.path.dirname(os.path.abspath(exepath))
        self.custom_path = r'C:\\bin\\'

        os.environ["WDM_LOCAL"] = self.custom_path
        self.opt.add_experimental_option("debuggerAddress", "localhost:8989")
        self.opt.add_argument("--user-data-dir=C:/bin/chromeProfile")

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

                # เอาList มารวมกัน
                self.merged_dict = dict(
                    zip(self.unique_titles, self.value_list))
                print("มี tabs ไรบ้าง", self.merged_dict)
                # self.operation_start()
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(f"An error occirred: {e}")
            print(traceback_str)
            # logger.debug('This is a debug message')
            # logger.info('This is an info message')
            logger.warning(f"'method get_tabs()', {traceback_str}")
            # logger.error('This is an error message')
            # logger.critical('This is a critical message')

    def operation_start(self, kit_sku, target_data):
        print("sku: ", kit_sku)
        print("target_data: ", target_data)
        self.get_tabs()
        # * switch to the right page
        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])

        # * check ก่อนว่าใส่ชื่อลูกค้ายัง
        self.cus_name_input_element = self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]')
        self.cus_name_title_attribute = self.cus_name_input_element.get_attribute(
            "title")
        self.prog = re.search("^C[0-9]+", self.cus_name_title_attribute)
        try:
            self.is_name_empty = self.prog.group()
        except:
            print("ไม่มีชื่อลูกค้า")
            return

        if self.is_name_empty:
            # * arguments
            self.kit_sku = kit_sku
            self.target_data = target_data

            # * sku input zone
            self.sku_input = self.driver.find_element(
                By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input")
            self.sku_input.clear()
            self.sku_input.send_keys(self.kit_sku)
            self.sku_input.send_keys(Keys.ENTER)

            # * Make sure if an sn btn element appear

            while True:
                # * ต้องรอ ถ้าไม่รอ แล้ว เปิด element ทันที หน้า sn มันจะหด แล้วก็ error เพราะหา element ไม่เจอ
                time.sleep(2)
                try:
                    self.driver.find_element(
                        By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/div[2]/div[1]/div[1]/a").is_displayed()
                    break
                except:
                    continue

            # * sn fill
            self.sn_sequence_list = self.create_sn_fill_sequence(self.kit_sku)
            # * SN Button Pattern Dir
            # * /html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/div[2]/div[1]/div[{dom_idx}]/a
            # * Example ref
            # * /html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/div[2]/div[1]/div[1]/a ปุ่ม sn 1
            # * /html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/div[2]/div[1]/div[2]/a ปุ่ม sn 2

            for i, sku in enumerate(self.sn_sequence_list):
                self.dom_idx = i+1
                self.sn_btn_dir = f"/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/div[2]/div[1]/div[{
                    self.dom_idx}]/a"
                self.sn_btn_elmt = self.driver.find_element(
                    By.XPATH, self.sn_btn_dir)
                try:
                    self.sn_btn_elmt.click()
                except:
                    continue

                # * SN input in the pop-up

                while True:
                    try:
                        self.driver.find_element(
                            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[7]/div/div/div[2]/form/div/div[1]/div/input').is_displayed()
                        self.driver.find_element(
                            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[7]/div/div/div[2]/form/div/div[1]/div/input').clear()
                        break
                    except:
                        continue

                self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[7]/div/div/div[2]/form/div/div[1]/div/input').send_keys(self.target_data[sku])

                # *submit
                self.submit_btn = self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[7]/div/div/div[2]/div[2]/a[1]')
                # * ปุ่มมันกระพริบมันมีช่วงที่ click ได้และไม่ได้ ต้องใช้ while มารัวให้มัน
                for i in range(2):
                    while True:
                        try:
                            self.submit_btn.click()
                            break
                        except:
                            continue
        else:
            error_message = "ไม่มีชื่อลูกค้า"
            print(error_message)
            return error_message

    def create_sn_fill_sequence(self, kit_sku):
        # test case ที่ดีต้องดูหลายๆค่า เพราะแต่ละ sku มีลำดับไม่เหมือนกันฉะนั้นต้องลองเทสสองเคสนี้ KCU2-000781, KCU2-000777
        # * Argument ต้องรับ
        self.target = kit_sku
        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
        # sku_kit_list = self.driver.find_elements(By.CSS_SELECTOR, "div.col-sm-9.col-xs-8")
        print("มีเซ็ตไรบ้าง")
        try:
            self.kit_name_target = self.driver.find_element(
                By.XPATH, f"//a[contains(., '{self.target}')]")
        except:
            print(f"หา ชุดkit {self.target} ไม่เจอ")
            return
        self.kit_items_target_elmt = self.kit_name_target.find_element(
            By.XPATH, "../div[1]")
        self.kit_items_list = self.kit_items_target_elmt.find_elements(
            By.CLASS_NAME, "ng-binding")
        # print(f"element by kit name: {self.kit_name_target}, kit name: {self.kit_name_target.text}")
        # print(f"kit_items_target: {self.kit_items_target_elmt}")
        # print(f"kit_items_list: {self.kit_items_list}")

        # * ดึง text แต่ละ elemtn ย่อย เพื่อเอา sku ภายในชุด kit
        self.prog = re.compile(r"\w{2}\d\-\d{6}")

        self.sku_type_list = []
        for i, item in enumerate(self.kit_items_list):
            try:
                self.result = f"{self.prog.match(item.text).group()}"
                self.sku_type_list.append(str(self.result[0:3].lower()))
                # print(result[0:3])

            except:
                continue

        #! ส่วนนี้จะใช้ได้หาก smco เรียงของตาม step เท่านั้น หาก เรียง เป็น ts9(psu) ตามด้วย ts8(case)
        # * ดูว่ามี ts8 ซ้ำหรือไม่
        self.ts8_count = self.sku_type_list.count('ts8')

        # * หากมีซ้ำจะทำการเปลี่ยน
        if self.ts8_count > 1:
            for i in range(len(self.sku_type_list)):
                if self.sku_type_list[i] == 'ts8':
                    self.sku_type_list[i] = 'ts9'
                    break

        print("gotcha: ", self.sku_type_list)
        return self.sku_type_list


