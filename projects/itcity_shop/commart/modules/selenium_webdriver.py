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

            if 'update_bot_stat_fn' in kwargs:
                self.update_bot_status = kwargs['update_bot_stat_fn']
                self.app = kwargs['app']
            self.setup_chrome()
        except Exception as e:
            tb_str = traceback.print_exc()
            print('Classs ChromeDriver has stopped working')
            raise ValueError('Traceback: ', tb_str)
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

    def add_customer(self):
        print("ชื่อลูกค้าเป็นไง SHOP: ", self.app.cus_name.get())
        name = self.app.cus_name.get()

        self.driver.switch_to.window(
            self.merged_dict['SMCO :: เปิดการขาย'])
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[7]/a').click()
        time.sleep(0.75)
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[1]/div[2]/button[1]').click()

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
        # self.driver.find_element( By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(f'{name} Tax ID: {self.app.tax_num.get()}')
        # * >nameTH SMCO style
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(f'{name}')

        # * >nameEN clear
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').clear()
        # * >nameEN fill input better style ปิดการใช้งาน
        # self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(f'{name} Tax ID: {self.app.tax_num.get()}')
        # * >nameEN SMCO style
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(f'{name}')

        # ! เปิดใช้การออกใบกำกับ ตาม SMCO style (ถ้าไม่เปิดจะถือว่าเป็นการใช้ Better style)
        if len(self.app.cus_tax_num.get()) > 0:
            # * clear Identity ID
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[3]/input').clear()
            # * Identity ID
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[3]/input').send_keys(self.app.cus_tax_num.get())

        # * กรอก Address
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').clear()
        # ! > การกรอก address แบบโกง bypass เขตแขวง SMCO แต่กลัวว่า สรรพากรจะกำหมัด
        # self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(self.app.cus_address)
        # ! > การกรอก address แบบทำตามกฎเลือก เขตแขวง ตามระบบ SMCO แต่กลัวว่า สรรพากรจะกำหมัด
        address = self.app.cus_address
        print("ข้างใน addressมีค่าไหม: ", self.app.cus_address)
        # if self.app.tax_bool.get():
        #     address = self.app.get_pure_address(self.app.cus_address)
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(address)

        # * กรอก email
        # self.email_input = self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[13]/div[2]/input')
        # self.email_input.clear()
        # self.email_input.send_keys(self.app.cus_email.get())

        # * tel.
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').clear()
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(self.app.cus_tel.get())

        if len(self.app.cus_tax_num.get()) > 0:
            ### * เป็นแบบกรอกแบบ DropDown ##########################################################################################################
            # dropdown Country
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[9]/div[1]/div/span/span[1]/span/span[1]').click()
            time.sleep(1)
            # select thailand in dropdown
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[2]/ul/li[2]').click()

            # province dropdown
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[9]/div[2]/div/span/span[1]/span/span[1]').click()
            self.driver.find_element(
                # province input
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()
            self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
                self.app.cus_province.get().replace("จังหวัด", ""))  # province input
            time.sleep(1.75)
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

            self.driver.find_element(
                # District drop
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[1]/div/span/span[1]/span/span[1]').click()
            self.driver.find_element(
                # District
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()
            self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
                self.app.cus_district.get().replace("อำเภอ", "").replace("เขต", "").replace("ต.", ""))  # District
            time.sleep(1.75)
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

            # SubDistrict drop
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[3]/div/span/span[1]/span/span[1]').click()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[3]/div/span/span[1]/span/span[1]').click()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[3]/div/span/span[1]/span/span[1]').click()
            # SubDistrict
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()
            self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
                self.app.cus_sub_district.get().replace("ตำบล", "").replace("แขวง", "").replace("ต.", ""))  # SubDistrict
            time.sleep(1.75)
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

        # # * กด Save
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()

        # * รอมันหายก่อนแล้วค่อยจบ function เพื่อไม่ให้ขั้นตอนต่อไปทำงานเร็วเกินไป
        # self.wait1.until(EC.invisibility_of_element_located(
        #     (By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]')))
        while True:
            try:
                is_add_page_present = self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').is_displayed()
            except:
                continue

            if is_add_page_present:
                continue
            else:
                break

        # *  24/04/2023: กลับมาอีกแล้วทำให้เป็น try except ละกัน// 09/11/2023: partนี้ ทาง SMCO ลบออกไปแล้ว
        # self.wait1.until(EC.visibility_of_element_located(
        #     (By.XPATH, '/html/body/div[16]/div[2]/button[1]')))
        try:
            self.driver.find_element(
                By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()
        except:
            pass

    def operation_start(self):
        print("chrome started!!")

        try:
            self.add_customer()
        except Exception as e:
            traceback_str = traceback.format_exc()
            print("พัง: ", traceback_str)
        print("chrome finished!!")
        self.update_bot_status(is_bot_working=False)

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


# try:
#     chromeDriver_browser = ChromeDriver()
# except Exception as e:
#     traceback_str = traceback.format_exc()
#     print(f"An error occirred: {e}")
#     print(traceback_str)
#     # logger.debug('This is a debug message')
#     # logger.info('This is an info message')
#     logger.warning(f"'from class ChromeDriver()', {traceback_str}")
#     # logger.error('This is an error message')
#     # logger.critical('This is a critical message')
