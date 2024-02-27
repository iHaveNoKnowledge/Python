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
    def __init__(self):
        try:
            self.setup_chrome()
        except:
            print('หยุดการทำงาน ณ บัดนี้')
            return
        self.get_tabs()

    def setup_chrome(self):
        self.opt = Options()
        # * ใช้เพื่อเก็บที่อยู่ของไฟล์ที่ถูก execute ด้วย Python ผ่าน command line arguments ในตัวแปร exepath ซึ่ง sys.argv[0] คือชื่อของไฟล์ Python script ที่ถูกเรียกใช้งาน
        exepath = sys.argv[0]
        # * abspath() ใช้เพื่อแปลงที่อยู่ของไฟล์หรือ directory path เป็นที่อยู่แบบ absolute โดยรวมชื่อ root directory ด้วย ซึ่งจะช่วยให้เราสามารถระบุที่อยู่อย่างแน่นอนในระบบไฟล์ได้โดยไม่ขึ้นอยู่กับ working directory ปัจจุบัน เช่นถ้าไฟล์อยู่ใน "/home/user/documents" และเราใช้ abspath() กับไฟล์นั้น ผลลัพธ์ที่ได้จะเป็น "/home/user/documents/file.txt" โดยที่ไม่ว่า working directory จะอยู่ที่ไหนก็ตาม
        # * dirname() ใช้สำหรับดึงชื่อ directory จากที่อยู่ของไฟล์หรือ directory path ที่ให้มา และส่งคืนเป็นชื่อ directory เท่านั้นโดยไม่รวมชื่อไฟล์หรือส่วนท้ายของ path ถ้า path ที่ให้มาเป็น directory path จะคืนค่าเป็นชื่อ directory ตรงไปด้วย เช่นถ้า path เป็น "/home/user/documents/file.txt" ซึ่งเป็นที่อยู่ของไฟล์ ฟังก์ชัน dirname() จะคืนค่า "/home/user/documents" โดยที่ไม่รวมชื่อไฟล์ "file.txt" ด้วย
        Dir_path = os.path.dirname(os.path.abspath(exepath))
        self.custom_path = r'C:\\bin\\'
        Download_dir = Dir_path+self.custom_path

        os.environ["WDM_LOCAL"] = self.custom_path
        # print("มีไรบ้างใน obj Options:", dir(self.opt))
        self.opt.add_experimental_option("debuggerAddress", "localhost:8989")
        # self.opt.add_argument("--disable-popup-blocking")
        # self.opt.add_experimental_option("prefs",{
        #     "download.default_directory" : Download_dir,
        #     "directory_upgrade": True
        # })
        try:
            self.driver = webdriver.Chrome(
                service=Service(r'C:\bin\chromedriver.exe'),
                options=self.opt
            )
        except:
            traceback_str = traceback.format_exc()
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


try:
    chromeDriver_browser = ChromeDriver()
except Exception as e:
    traceback_str = traceback.format_exc()
    print(f"An error occirred: {e}")
    print(traceback_str)
    # logger.debug('This is a debug message')
    # logger.info('This is an info message')
    logger.warning(f"'from class ChromeDriver()', {traceback_str}")
    # logger.error('This is an error message')
    # logger.critical('This is a critical message')
