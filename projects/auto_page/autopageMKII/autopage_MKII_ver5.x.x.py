import base64
import datetime
import gc
import json
import locale
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import winreg
from tkinter import *
from tkinter import filedialog, font, messagebox

import customtkinter as ctk
import httpcore
import pandas as pd
import pdfplumber
import pytz
import requests
import win32api
import win32com.client as comclt
import win32print
from bs4 import BeautifulSoup
from customtkinter import *
from dotenv import load_dotenv
from functions.accel_mode import AccelMode
from functions.auto_add_product import AutoAddProduct
from functions.BaseUrlFinder.BaseUrlFinder import BaseUrlFinder
from functions.browser_manager import BrowserManager
from functions.pos.frontpage.smcoformhandler import SMCOFormHandler
from functions.product_manager import ProductManager
from functions.tracking_manager import TrackingManager
from functions.utils.crypto import AccountManager
from googletrans import Translator
from loguru import logger
from openpyxl import load_workbook
from order_display_manager import OrderDisplayManager
from PIL import Image, ImageTk
from selenium import webdriver
from selenium.common.exceptions import (InvalidSessionIdException,
                                        NoSuchElementException,
                                        StaleElementReferenceException,
                                        TimeoutException, WebDriverException)
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class RefreshRequiredException(BaseException):
    """Raised when a session collision popup is detected, requiring a page refresh and order restart."""
    pass


class SmcoApiClient:
    """
    จัดการ HTTP requests ทั้งหมดสำหรับ SMCO API
    ใช้ requests.Session() เดียวเพื่อ reuse connection และ cookie จาก login
    """

    _BASE_HEADERS = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }

    def __init__(self):
        self._session = requests.Session()

    def login(self, origin: str, user_id: str, password: str) -> dict:
        """
        POST login ไปที่ SMCO แล้ว return response.json()

        Args:
            origin: base URL เช่น 'http://192.168.0.11:8080'
            user_id: รหัสพนักงาน
            password: รหัสผ่าน

        Returns:
            dict จาก response.json()

        Raises:
            requests.exceptions.RequestException: ถ้า request ล้มเหลว
        """
        url = f'{origin}/smartcore/loginssoauthen.htm'
        cookies = {
            'JSESSIONID': 'EA2AD7582A59949D14642F01ADF23832',
            'locale': 'en_US',
        }
        headers = {**self._BASE_HEADERS, 'Origin': origin}
        data = {
            'locale': 'en_US',
            'redirect': f'{origin}/smartcore/',
            'username': [user_id],
            'password': [password],
            'branch': ['', ''],
            'storeId': ['', ''],
        }
        response = self._session.post(url, cookies=cookies, headers=headers, data=data, verify=False)
        return response.json()

    def post(self, url: str, data: dict, cookies: dict = None, origin: str = '') -> requests.Response:
        """
        Generic POST สำหรับ SMCO API endpoints

        Args:
            url: URL เต็ม
            data: form data ที่จะส่ง
            cookies: browser cookies (จากSelenium driver)
            origin: Origin header value

        Returns:
            requests.Response object
        """
        headers = {**self._BASE_HEADERS, 'Origin': origin}
        return self._session.post(url, cookies=cookies, headers=headers, data=data, verify=False)

    def get_vatinfo(self, json_data: dict, extra_headers: dict = None) -> requests.Response:
        """
        POST ไปยัง RD VAT API (vsinter.rd.go.th) เพื่อค้นหาข้อมูลภาษี
        ใช้ session เดียวกับ SMCO เพื่อ reuse connection

        Args:
            json_data: JSON payload เช่น {'nid': ..., 'brano': ..., 'searchType': '1', ...}
            extra_headers: headers เพิ่มเติม (optional)

        Returns:
            requests.Response object
        """
        url = 'https://vsinter.rd.go.th/rd-commoninter-service/subother/vatsbtsearch/getVatInfo'
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Origin': 'https://vsinter.rd.go.th',
            'Pragma': 'no-cache',
            'Referer': 'https://vsinter.rd.go.th/rd-webcontent-web/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': self._BASE_HEADERS['User-Agent'],
        }
        if extra_headers:
            headers.update(extra_headers)
        return self._session.post(url, headers=headers, json=json_data)

    def get_product_info(self, origin: str, sku: str, cookies: dict,) -> requests.Response:
        """
        ค้นหาข้อมูลสินค้า (product master) จาก SKU — ใช้เพื่อได้ product id
        สำหรับ combo กับ get_serial_list()

        Args:
            origin: base URL เช่น 'http://192.168.0.142:9099'
            sku: รหัสสินค้า เช่น 'PR2-000495'
            cookies: browser cookies (จาก get_cookies_from_driver)
            source_id: รหัสสาขา/source (default '40010012')

        Returns:
            requests.Response — .json() จะมี list ของ product records
        """
        url = f'{origin}/smartcore/smartpos/pointofsales/posmainv3/getProductMasterInfoPOSV3.htm'
        payload = {
            'activeFlag': 'true',
            'requestText': sku,
            'start': '1',
            'length': '1',
            'order[0][column]': '0',
            'order[0][dir]': 'asc',
            'modeScan': 'Y',
            'isIgnoreQty': 'false',
            'onlyProduct': 'false',

        }
        return self.post(url, data=payload, cookies=cookies, origin=origin)

    def get_serial_list(self, origin: str, product_id: str, master_id: int,
                        parent_id: int, cookies: dict,
                        timestamp: str = '0') -> requests.Response:
        """
        ค้นหา Serial Number list ใน stock จาก product id
        ใช้ต่อจาก get_product_info() เพื่อดูว่ายังมี SN ใดอยู่ใน stock

        Args:
            origin: base URL เช่น 'http://192.168.0.142:9099'
            product_id: id ของสินค้าที่ได้จาก get_product_info()
            master_id: branchId (เช่น 180)
            parent_id: parentId ของสินค้า (เช่น 441)
            cookies: browser cookies (จาก get_cookies_from_driver)
            timestamp: _ param สำหรับ cache busting (ใส่ int timestamp หรือ '0')

        Returns:
            requests.Response — .json()['data'] จะมี list ของ serial records
        """
        url = f'{origin}/smartcore/inventory/stock/v2/getSerialInfoList.htm'
        search_value = json.dumps({
            'byId': str(product_id),
            'byMasterId': master_id,
            'byParentId': parent_id,
        }, separators=(',', ':'))

        # * DataTables column definitions boilerplate (17 columns)
        _col_names = [
            '', 'serialNo', 'imeiNo1', 'imeiNo2', 'age', 'WhAge', 'telNo',
            'reservedQty', 'reservedByEn', 'reservedDate', 'reservedPaymentNo',
            'reservedSo', 'remark', 'receiveDate', 'refDocNo', 'vendorNameen',
            'status', 'source', 'creator', 'createDate',
        ]
        payload: dict = {
            'draw': '2',
            'order[0][column]': '0',
            'order[0][dir]': 'asc',
            'start': '0',
            'length': '1000',
            'search[value]': search_value,
            'search[regex]': 'false',
            '_': str(timestamp),
        }
        for i, name in enumerate(_col_names):
            payload[f'columns[{i}][data]'] = name
            payload[f'columns[{i}][name]'] = ''
            payload[f'columns[{i}][searchable]'] = 'true'
            payload[f'columns[{i}][orderable]'] = 'false' if i == 0 else 'true'
            payload[f'columns[{i}][search][value]'] = ''
            payload[f'columns[{i}][search][regex]'] = 'false'

        return self.post(url, data=payload, cookies=cookies, origin=origin)

    def get_cus_data(self, origin: str, req_text: str, search_type: str, cookies: dict) -> requests.Response:
        """
        ค้นหาชื่อผู้ซื้อจาก API โดยใช้คำค้นหาและ ประเภทการค้นหา (เช่น by name, by tax id, by customercode, etc.)
        ใช้สำหรับ autocomplete ชื่อผู้ซื้อในหน้า POS

        Args:
            origin: base URL เช่น 'http://
            search_type: N = by name, T = by tax id, C = by customer code
        Returns:
            requests.Response — .json()['data'] จะมี list ของ customer records
        """
        url = f'{origin}/smartcore/uilts/oper/pos/getCustomerSearchPOS/selectoption.htm'
        payload = {
            'requestText': req_text,
            'target': search_type,
        }
        response = self.post(url, data=payload, cookies=cookies, origin=origin)
        if response.status_code != 200:
            logger.error(f"{self.cus_order}: get_cus_data(): API call failed with status code {response.status_code}")
            return None
        return response


# * images
icon_path = os.path.join(os.path.dirname(__file__), 'imgs', 'kheedluang.ico')
arrow_icon = os.path.join(os.path.dirname(__file__), 'imgs', 'Arrow.gif')
stop_icon = os.path.join(os.path.dirname(__file__), 'imgs', 'stop.jpg')

# * initial settings
locale.setlocale(locale.LC_ALL, 'en_us')
current_directory = os.getcwd()
print("current_directory:", current_directory)
address_file = r"tables\Addresscleaner_TambonData.xlsx"
file_path = os.path.join(current_directory, address_file)
directory_of_file = os.path.dirname(file_path)
print("file located:", directory_of_file)
load_dotenv()

# * ปรับ https ให้ตัว translate
setattr(httpcore, 'SyncHTTPTransport', 'AsyncHTTPProxy')

# * splash screen
if getattr(sys, 'frozen', False):
    import pyi_splash


class MyApp:
    def __init__(self, root):
        # * For testing purposes only
        self.is_testing = False
        # * instance of utility classes
        self.account_manager = AccountManager("AutoSamaticMKII")
        # * general Variables (mostly for gui)------------------------------------------------------------------------------------
        self.root = root
        self.dev_account = ["62078", "61651", "62302"]
        self.is_bot_running = BooleanVar(value=False)
        # self.validate_input_variable = self.root.register(self.validate_input)
        self.user_id = StringVar(value=self.account_manager.get_last_username())
        self.user_pw = StringVar(value="")
        self.result = ""
        self.is_accel_mode = BooleanVar()
        self.is_accel_mode_activated = BooleanVar(value=False)
        self.is_seller_voucher_popup = BooleanVar(value=False)
        self.is_auto_invoice_mode = BooleanVar(value=False)
        self.table_location = ""
        self.cp_table_location = ""
        self.cp_df = None

        # * Initialize AccelMode instance
        self.accel_mode = AccelMode(self)
        self.marketplace_target = StringVar(value="MarketPlace")
        self.bg_by_market_place = {'SHOPEE': '#ee4d2d', 'LAZADA': '#201adb', '': '#747474'}
        self.cus_order = StringVar(value="")
        self.is_tax_required = BooleanVar(value=False)
        self.tax_num = StringVar(value="")
        self.cus_tax_status = StringVar(value="")
        self.tax_branch_num = StringVar(value="")
        self.cus_name = StringVar(value="")
        self.cus_account_name = StringVar(value="")
        self.cus_address = ""
        self.cus_remark = ""
        self.order_note = ""
        self.cus_province = StringVar(value="")
        self.cus_district = StringVar(value="")
        self.cus_sub_district = StringVar(value="")
        self.cus_tel = StringVar(value="")
        self.cus_email = StringVar(value="")
        self.cus_postcode = StringVar(value="")
        self.cus_cur_status = StringVar(value="")
        self.cus_tax_name_lazada = StringVar(value="")
        self.is_forbid = False
        self.cus_ship_cost = DoubleVar(value=0)
        self.cus_seller_voucher = DoubleVar(value=0)
        self.cus_purchase_time = StringVar(value="")
        self.cus_arrow_btn = '//form[@id="divMember"]//span[@class="select2-selection__arrow" and @role="presentation"]'
        # self.cusNameInput = '/html/body/span/span/span[1]/input' อันเก่าจริงๆมันใช้ได้แหละแต่กันไว้ก่อน
        self.cusNameInput = '//span[@class="select2-search select2-search--dropdown"]/input'
        self.cusCreateBtn = 'button#newMember'
        self.cusNameLi1 = '/html/body/span/span/span[2]/ul/li'
        self.cus_name_dropdown_ul = '//ul[@id="select2-memberSearch-results"]'
        # self.bot_state = BooleanVar(value=False)
        self.cookies = {
            'vatinfo': {
                'JSESSIONID': '',
            }
        }
        self.is_bot_browser_busy = BooleanVar(value=False)
        self.is_finish_order_triggered = BooleanVar(value=False)
        self.mimic_list_item_states = []
        self.POP_UP = PopUp(self.root)

        # * เราจะใช้สอง obj หลักๆ UI กับ BOT WEBDRIVER ###################################################################
        # * 1)Create UI ---------------------------------------------------------------------------------------------
        self.scale_factor = self.adjust_scale(self.root, 1000, 900)
        self.create_main_window()
        self.scale_widget(self.root, self.scale_factor)
        #! self.get_dataframe() สร้างไว้ไมวะ
        current_dir = os.path.dirname(os.path.abspath(__file__))
        time_name = datetime.datetime.now()
        log_path = os.path.join(current_dir, f"""logs\\autopageMKII_log_{time_name.strftime('%Y_%m_%d')}.log""")
        logger.add(log_path, format="{time} {level} {message}", level="INFO")

        # * 2)Start HTTP API client (shared ระหว่าง MyApp และ Bot_POS) --------------------------------------------------------
        self.smco_api = SmcoApiClient()

        # * 3)Start a POS BOT WEBDRIVER instance ------------------------------------------------------------------------
        self.bot = Bot_POS(self.root, self)

        # * 4)Create caches
        cache_dir = os.path.join(current_dir, f"""caches.json""")
        self.subdistrict_cache = {}
        self.load_subdistrict_cache()

    def load_subdistrict_cache(self):
        self.subdistrict_cache = {}
        cache_path = "output_test.xlsx"
        if os.path.exists(cache_path):
            try:
                # Read only 'หมายเลขคำสั่งซื้อ' and 'แขวง/ตำบล' columns to be fast
                cache_df = pd.read_excel(cache_path, usecols=['หมายเลขคำสั่งซื้อ', 'แขวง/ตำบล'], dtype=str)
                cache_df.dropna(subset=['หมายเลขคำสั่งซื้อ', 'แขวง/ตำบล'], inplace=True)
                for _, row in cache_df.iterrows():
                    order_num = str(row['หมายเลขคำสั่งซื้อ']).strip()
                    subdist = str(row['แขวง/ตำบล']).strip()
                    if order_num and subdist and subdist.lower() != 'nan':
                        self.subdistrict_cache[order_num] = subdist
                print(f"Loaded {len(self.subdistrict_cache)} subdistrict entries from cache (output_test.xlsx).")
            except Exception as cache_err:
                print(f"Warning: Could not load subdistrict cache: {cache_err}")

    def finish_order(self):
        """กดปุ่ม Finish เพื่อ click controlKeyF2 บนเว็บ"""
        try:
            if hasattr(self, 'bot') and hasattr(self.bot, 'driver'):
                self.is_finish_order_triggered.set(True)
                self.bot.driver.find_element(
                    By.XPATH, "//div/a[@id='controlKeyF2']").click()
                print("Finish: Clicked controlKeyF2")
            else:
                print("Finish: Bot or driver not available")
        except Exception as e:
            print(f"Finish: Error clicking controlKeyF2: {e}")

    def cp_sonic_blow_handler(self):
        self.bot.cp_sonic_blow_process(self.demonicCp_itemNo.get(), self.demonicCp_cpNo.get())

    def reset_browser_memory(self):
        """Callback สำหรับปุ่ม 'Reset Memory' Button"""
        try:
            if hasattr(self, 'bot') and hasattr(self.bot, 'driver'):
                self.bot.browser.reset_all_tabs_memory()
                print("Browser memory reset completed")
            else:
                print("Browser not initialized yet")
        except Exception as e:
            print(f"Error resetting browser memory: {e}")

    def check_browser_memory(self):
        """Callback สำหรับปุ่ม 'Check Memory' Button"""
        try:
            if hasattr(self, 'bot') and hasattr(self.bot, 'driver'):
                current_handle = self.bot.driver.current_window_handle
                all_handles = self.bot.driver.window_handles

                print(f"\n=== Browser Memory Report ===")
                print(f"Total tabs: {len(all_handles)}")

                total_memory = 0
                for i, handle in enumerate(all_handles):
                    try:
                        self.bot.driver.switch_to.window(handle)
                        tab_title = self.bot.driver.title[:30]
                        memory_usage = self.bot.browser.get_current_tab_memory_usage()
                        total_memory += memory_usage
                        print(f"Tab {i+1}: {tab_title} - {memory_usage:.1f}MB")
                    except Exception as e:
                        print(f"Tab {i+1}: Error checking - {e}")

                print(f"Total memory usage: {total_memory:.1f}MB")
                print(f"Operations completed: {self.bot.operation_count}")
                print("="*30)

                # กลับไป tab เดิม
                self.bot.driver.switch_to.window(current_handle)
            else:
                print("Browser not initialized yet")
        except Exception as e:
            print(f"Error checking browser memory: {e}")

    def validate_input(self, value):
        pattern = r'[A-z]'
        if re.fullmatch(pattern, value) is None:
            return False

        return True

    def on_canvas_configure(self, event):
        self.canvas_width = event.width
        self.canvas_height = event.height
        self.root_frame.config(width=self.canvas_width, height=self.canvas_height)

    def adjust_scale(self, root, base_width, base_height):
        # Get current screen resolution
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # Calculate scale factors - ใช้ขนาดหน้าต่างที่ต้องการเป็นตัวตั้ง
        width_scale = base_width / screen_width
        height_scale = base_height / screen_height

        # ใช้ scale factor ที่มากกว่าเพื่อให้แน่ใจว่า UI จะพอดีกับหน้าจอ
        scale_factor = max(width_scale, height_scale)

        # กลับค่า scale เพื่อให้ UI เล็กลงเมื่อหน้าจอเล็กกว่าขนาดที่ต้องการ
        return 1 / scale_factor

    def scale_widget(self, widget, scale_factor):
        if isinstance(widget, (CTkLabel, CTkButton, CTkEntry, CTkFrame)):
            current_width = widget.cget("width")
            current_height = widget.cget("height")
            new_width = int(current_width * scale_factor)
            new_height = int(current_height * scale_factor)
            widget.configure(width=new_width, height=new_height)

        if isinstance(widget, CTk):
            for child in widget.winfo_children():
                self.scale_widget(child, scale_factor)

    def create_main_window(self):
        bg_color = "#37629e" if getattr(self, "is_testing", False) else "#444"
        # คำนวณ scale factor จากขนาดหน้าจอ
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        base_width = 1920
        base_height = 1080

        # คำนวณ scaling factor
        scaling_factor = min(screen_width / base_width, screen_height / base_height)

        # ตั้งค่า scaling สำหรับ window และ widgets
        set_window_scaling(scaling_factor)
        set_widget_scaling(scaling_factor)

        if screen_height <= 768:
            base_font_size = 10
        elif screen_height <= 1080:
            base_font_size = 10
        else:
            base_font_size = 12

        # สร้าง font objects ที่ใช้บ่อย
        self.normal_font = CTkFont(
            family="Arial",
            size=int(base_font_size * scaling_factor)
        )

        self.bold_font = CTkFont(
            family="Arial",
            size=int(base_font_size * scaling_factor),
            weight="bold"
        )

        self.header_font = CTkFont(
            family="Arial",
            size=int((base_font_size + 2) * scaling_factor),
            weight="bold"
        )

        # * ตั้งค่าขนาดและตำแหน่งหน้าต่าง
        window_width = min(int(975 * scaling_factor), screen_width - 100)
        window_height = min(int(750 * scaling_factor), screen_height - 100)
        x_position = max(0, min(
            (screen_width - window_width) // 2,
            screen_width - window_width - 20
        ))
        y_position = max(0, min(
            (screen_height - window_height) // 2,
            screen_height - window_height - 40
        ))

        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.root.title("Autosamatic ver5.x.xLITE")
        self.root.configure(fg_color=bg_color)

        # กำหนด minimum size
        min_width = min(int(800 * scaling_factor), screen_width - 100)
        min_height = min(int(600 * scaling_factor), screen_height - 100)
        self.root.minsize(min_width, min_height)

        # กำหนด base font size ตาม resolution
        if screen_height <= 768:
            base_font_size = 12
        else:
            base_font_size = 10

        # สร้าง Main Canvas
        self.canvas = Canvas(self.root, bg=bg_color, width=800, height=600)

        # สร้าง Scrollbar แนวตั้ง
        self.scrollbar_y = CTkScrollbar(
            self.root,
            orientation="vertical",
            command=self.canvas.yview
        )
        self.scrollbar_y.pack(side="right", fill="y")

        # สร้าง Scrollbar แนวนอน
        self.scrollbar_x = CTkScrollbar(
            self.root,
            orientation="horizontal",
            command=self.canvas.xview
        )
        self.scrollbar_x.pack(side="bottom", fill="x")

        # กำหนด scrollcommand ให้ canvas
        self.canvas.configure(
            yscrollcommand=self.scrollbar_y.set,
            xscrollcommand=self.scrollbar_x.set
        )

        # สร้าง main frame ที่จะอยู่ใน canvas
        self.main_frame = CTkFrame(self.canvas, fg_color=bg_color)

        # สร้าง window ใน canvas เพื่อใส่ main_frame
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.main_frame,
            anchor="nw"
        )

        # Pack canvas
        self.canvas.pack(side="left", fill="both", expand=True)

        # Bind events สำหรับการ scroll
        self.main_frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # #* FRAMES #####################################################################################################
        # self.root_frame = CTkFrame(self.canvas,  fg_color="pink") ใช้ได้แต่รอก่อน
        # self.canvas.create_window((0, 0), window=self.root_frame, anchor="nw") ใช้ได้แต่รอก่อน

        # > Frame1 Order Entry
        self.entry_frame = CTkFrame(
            self.main_frame,
            fg_color="#ccc",  # แทน bg
            # border_width=10,   # แทน borderwidth
            # border_color="#ccc",  # แทน highlightbackground
        )
        self.entry_frame.pack(side='top', anchor=W, pady=10, padx=5)

        # > Frame new: Checkbox Frame
        self.checkbox_frame = CTkFrame(
            self.main_frame,
            fg_color="#ccc",
        )
        self.checkbox_frame.pack(side='top', anchor=W, pady=5, padx=5)

        # > Frame3 ImportFile Status and Bot Status
        self.import_file_frame = CTkFrame(
            self.main_frame,
            fg_color="#ccc",
        )
        self.import_file_frame.pack(side='top', anchor=W, padx=10, pady=(5, 0))

        # > Frame3.5 CP File Frame
        self.cp_file_frame = CTkFrame(
            self.main_frame,
            fg_color="#ccc",
        )
        self.cp_file_frame.pack(side='top', anchor=W, padx=10, pady=(5, 0))

        # > Frame4 Customer Details
        self.order_details_frame = CTkFrame(
            self.main_frame,
            fg_color="#ccc"
        )
        self.order_details_frame.pack(side='top', anchor=W, padx=5, pady=(5, 0))

        # > Frame7 For Customer's Invoice Details
        self.invoice_details_frame = CTkFrame(
            self.main_frame,
            fg_color="#445"
        )
        self.invoice_details_frame.pack(side='top', anchor=W, padx=5, pady=(5, 0))

        #! ปรับ ui ใหม่ ทำให้ตรงนี้ไม่ได้ใช้
        # > Frame5 Products Lists
        # self.products_list_frame = CTkFrame(
        #     self.main_frame,
        #     fg_color="#445"
        # )
        # self.products_list_frame.pack(side='top', padx=5, pady=5, fill=X)

        # > Frame6 Marketplace(MP) Products Lists
        self.mp_products_list_frame = CTkFrame(
            self.main_frame,
            fg_color=bg_color
        )
        self.mp_products_list_frame.pack(side='top', padx=5, pady=5, fill="x")

        # > Frame7 The Upper Log Frame Demonic Frame
        self.demonic_frame = CTkFrame(
            self.main_frame,
            fg_color=bg_color
        )
        self.demonic_frame.pack(side='top', pady=(0, 2))

        # > Frame2 Log Frame
        self.log_frame = CTkFrame(
            self.main_frame,
            fg_color=bg_color
        )
        self.log_frame.pack(side='top', pady=20, fill="both")

        # * Create widgets in the main window
        self.create_widgets()

        # * Setup smart mouse wheel scrolling
        self._setup_smart_scroll()

    def on_frame_configure(self, event=None):
        """อัพเดท scroll region เมื่อ frame มีการเปลี่ยนแปลงขนาด"""
        # อัพเดท scroll region ให้ตรงกับขนาดของ main_frame
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        """ปรับขนาด canvas window เมื่อ canvas มีการ resize"""
        # อัพเดท scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _setup_smart_scroll(self):
        """
        ตั้งค่า smart scroll ที่จะตรวจสอบว่า mouse อยู่ที่ widget ไหน
        แล้วให้ widget นั้นรับ scroll event แทน
        """
        # Bind mouse wheel event to root window
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        """
        Handler สำหรับ mouse wheel event ที่จะตรวจสอบว่า mouse hover อยู่ที่ไหน
        แล้วส่ง scroll event ไปให้ widget ที่เหมาะสม

        - Scroll ปกติ: เลื่อนแนวตั้ง (vertical)
        - Shift + Scroll: เลื่อนแนวนอน (horizontal)
        """
        # หา widget ที่ mouse กำลัง hover อยู่
        widget = event.widget

        # ตรวจสอบว่ากด Shift หรือไม่
        is_shift_pressed = (event.state & 0x0001) != 0

        # คำนวณทิศทางการ scroll
        scroll_amount = int(-1 * (event.delta / 120))

        # ตรวจสอบว่า widget ที่ hover อยู่มี scrollbar ของตัวเองหรือไม่
        # โดยการเช็คว่ามันเป็น Text widget, Listbox, หรือ widget อื่นที่มี scroll ได้
        if self._widget_has_scrollbar(widget):
            # ถ้า widget มี scrollbar ของตัวเอง ให้ส่ง event ไปให้มัน
            try:
                if is_shift_pressed:
                    # Shift + Scroll = เลื่อนแนวนอน
                    if self._can_scroll(widget, 'x', scroll_amount):
                        widget.xview_scroll(scroll_amount, "units")
                else:
                    # Scroll ปกติ = เลื่อนแนวตั้ง
                    if self._can_scroll(widget, 'y', scroll_amount):
                        widget.yview_scroll(scroll_amount, "units")
            except:
                # ถ้า widget ไม่รองรับ xview_scroll/yview_scroll ก็ไม่ทำอะไร
                pass
        else:
            # ถ้าไม่มี scrollbar ให้ scroll main canvas แทน
            if is_shift_pressed:
                # Shift + Scroll = เลื่อนแนวนอน
                if self._can_scroll(self.canvas, 'x', scroll_amount):
                    self.canvas.xview_scroll(scroll_amount, "units")
            else:
                # Scroll ปกติ = เลื่อนแนวตั้ง
                if self._can_scroll(self.canvas, 'y', scroll_amount):
                    self.canvas.yview_scroll(scroll_amount, "units")

    def _can_scroll(self, widget, direction, amount):
        """
        ตรวจสอบว่าสามารถ scroll ได้หรือไม่โดยไม่เกินจุดเริ่มต้น (origin)

        Args:
            widget: widget ที่จะ scroll
            direction: 'x' สำหรับแนวนอน, 'y' สำหรับแนวตั้ง
            amount: จำนวนที่จะ scroll (บวก = scroll ลง/ขวา, ลบ = scroll ขึ้น/ซ้าย)

        Returns:
            True ถ้าสามารถ scroll ได้, False ถ้าจะเกินจุดเริ่มต้น
        """
        try:
            if direction == 'y':
                # ตรวจสอบแนวตั้ง
                view = widget.yview()
                # view[0] = ตำแหน่งบนสุดที่แสดง (0.0 = บนสุด)
                # view[1] = ตำแหน่งล่างสุดที่แสดง (1.0 = ล่างสุด)

                if amount < 0:  # scroll ขึ้น
                    # ป้องกันการ scroll ขึ้นเกินจุดบนสุด (origin)
                    return view[0] > 0.0
                else:  # scroll ลง
                    # อนุญาตให้ scroll ลงได้เสมอ (เพื่อดู content ที่อยู่ล่าง viewport)
                    return view[1] < 1.0
            else:  # direction == 'x'
                # ตรวจสอบแนวนอน
                view = widget.xview()
                # view[0] = ตำแหน่งซ้ายสุดที่แสดง (0.0 = ซ้ายสุด)
                # view[1] = ตำแหน่งขวาสุดที่แสดง (1.0 = ขวาสุด)

                if amount < 0:  # scroll ซ้าย
                    # ป้องกันการ scroll ซ้ายเกินจุดซ้ายสุด (origin)
                    return view[0] > 0.0
                else:  # scroll ขวา
                    # อนุญาตให้ scroll ขวาได้เสมอ (เพื่อดู content ที่อยู่ขวา viewport)
                    return view[1] < 1.0
        except:
            # ถ้าเกิด error ให้อนุญาต scroll (เผื่อ widget ไม่รองรับ)
            return True

    def _widget_has_scrollbar(self, widget):
        """
        ตรวจสอบว่า widget มี scrollbar ของตัวเองหรือไม่
        Returns True ถ้ามี scrollbar, False ถ้าไม่มี
        """
        # เช็คว่าเป็น widget ประเภทที่มี scroll ได้หรือไม่
        scrollable_types = ('Text', 'Listbox', 'Canvas', 'CTkTextbox', 'CTkScrollableFrame')

        # ตรวจสอบชื่อ class ของ widget
        widget_class = widget.__class__.__name__

        # ถ้าเป็น Text widget หรือ Listbox ให้เช็คว่ามี scrollbar หรือไม่
        if widget_class in scrollable_types:
            # ตรวจสอบว่า widget มีความสูงเกินกว่าที่แสดงได้หรือไม่
            try:
                # สำหรับ Text widget
                if hasattr(widget, 'yview'):
                    yview = widget.yview()
                    # ถ้า yview[1] < 1.0 แสดงว่ามีเนื้อหาที่ scroll ได้
                    if yview[1] < 1.0:
                        return True
            except:
                pass

        return False

    def measure_text(self, text):
        return font.Font().measure(str(text).strip())

    # * Mimic Shopee - REMOVED: row_header_maker and row_table_data_maker
    # * These methods have been moved to OrderDisplayManager class

    # * เป็นส่วนของ GUI ช่อง input ที่รับ order sn ในรูปแบบ file excel
    def accelmode_toggle(self):
        # * ระบุสถานะการแสดงผลของ GUI ที่ใช้สำหรับการ Input order แบบธรรมดา เพื่อทำการ remove มันแล้วแทนที่ ด้วย GUI ของ Accel mode
        order_label = self.inp1_label_order.winfo_ismapped()
        order_input = self.inp1_order_input.winfo_ismapped()
        order_btn = self.inp1_search_btn.winfo_ismapped()

        # * ถ้า Accel mode ทำงาน
        if self.is_accel_mode.get():
            # * gui โหมดธรรมดาทุกตัวทำงานอยู่
            if order_label and order_input and order_btn:
                # * ลบ gui โหมดธรรมดา ทิ้งรายตัว
                self.inp1_label_order.grid_remove()
                self.inp1_order_input.grid_remove()

            # Remove normal mode buttons from entry_frame
            self.inp1_search_btn.grid_remove()
            self.accel_stop_btn.grid_remove()
            self.display_acc_btn.grid_remove()

            # * เอา gui ของ accel mode มาแปะแทน (บน top frame)
            self.accl_dir_label.grid(row=0, column=1, padx=5)
            self.accl_dir_namedisplay_on_btn.grid(row=0, column=2, padx=5)
            self.add_trans_to_accel_file_btn.grid(row=0, column=3, padx=5)

            # Grid accel mode buttons on entry_frame
            self.accl_start_btn.grid(row=0, column=4, padx=5)
            self.accel_skip_btn.grid(row=0, column=5, padx=5)
            self.accel_del_btn.grid(row=0, column=6, padx=5)
            self.accel_stop_all_btn.grid(row=0, column=7, padx=5)
            self.display_acc_btn.grid(row=0, column=8, padx=5)

        # * ถ้า Accel mode ไม่ทำงาน
        else:
            # * ลบ gui ของ accel mode ทิ้งรายตัว (บน top frame)
            self.accl_dir_label.grid_remove()
            self.accl_dir_namedisplay_on_btn.grid_remove()
            self.add_trans_to_accel_file_btn.grid_remove()

            # Remove accel mode buttons from entry_frame
            self.accl_start_btn.grid_remove()
            self.accel_skip_btn.grid_remove()
            self.accel_del_btn.grid_remove()
            self.accel_stop_all_btn.grid_remove()
            self.display_acc_btn.grid_remove()

            # * เอา gui ของ โหมดธรรมดา มาแปะแทน (บน top frame)
            self.inp1_label_order.grid(row=0, column=1, padx=5)
            self.inp1_order_input.grid(row=0, column=2, padx=5)

            # Grid normal mode buttons on entry_frame
            self.inp1_search_btn.grid(row=0, column=3, padx=5)
            self.accel_stop_btn.grid(row=0, column=4, padx=5)
            self.display_acc_btn.grid(row=0, column=5, padx=5)

    def accel_confirm_skip(self):
        self.stop_operation()

    def accel_confirm_delete(self):
        try:
            # Delete order from accel file without deducting SN
            self.accel_mode.deduct_accel_file_data(self.cus_order, remove_order=True)
            self.update_log(f"🗑️ ลบออร์เดอร์ {self.cus_order.get()} ออกจากไฟล์ Accel เรียบร้อยแล้ว")
        except Exception as e:
            logger.error(f"Error deleting order from accel file: {e}")
            self.update_log(f"🛑 Error: ลบออร์เดอร์ไม่สำเร็จ: {e}")

        self.stop_operation()

    def seller_voucher_popup_checkbox_toggle(self):
        if self.is_seller_voucher_popup.get():
            self.seller_voucher_popup_checkbox.configure(bg='#21ff29', fg='#000')
        else:
            self.seller_voucher_popup_checkbox.configure(
                bg="#BF2D2A",
                fg="#FFF"
            )

    def auto_invoice_mode_toggle(self):
        if self.is_auto_invoice_mode.get():
            self.auto_inv_mode_checkbox.configure(bg='#21ff29', fg='#000')
        else:
            self.auto_inv_mode_checkbox.configure(
                bg="#BF2D2A",
                fg="#FFF"
            )

    #! น่าจะไม่ได้ใช้ deprecated
    # def seller_voucher_popup_toggle(self):
    #     self.is_seller_voucher_popup.set(not self.is_seller_voucher_popup.get())

    def create_widgets(self):
        # * entry_frame !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # * > MarketPlace
        # * >> Label
        self.marketplace_label = CTkLabel(
            self.entry_frame,
            textvariable=self.marketplace_target,
            fg_color="#747474",
            text_color="#FFF",
            font=CTkFont(family="bazooka", size=10, weight="bold"),
            padx=6
        )
        self.marketplace_label.grid(row=0, column=0, padx=5)

        # * > search order component
        # * >> Labels
        self.inp1_label_order = CTkLabel(self.entry_frame, text="Order: ", fg_color="#FFF", width=10)
        self.inp1_label_order.grid(row=0, column=1, padx=5)
        # * >> Inputs
        self.entered_order = StringVar()
        self.inp1_order_input = Entry(self.entry_frame, textvariable=self.entered_order, width=40)
        self.inp1_order_input.grid(row=0, column=3)
        # * >> Buttons
        self.font = CTkFont(family='fixedsys', size=10, weight="bold")
        self.inp1_search_btn = CTkButton(
            self.entry_frame,
            font=self.font,
            text="Start",
            fg_color="#f5a91d",
            text_color="#1E1E1E",
            border_width=1.5,
            border_color="#7d4b19",
            command=self.search_order,
            width=10,
            height=25
        )

        # * > search order Accel mode component
        # * พวกนี้มันต้อง add แบบ toggle เพราะมันต้องสลับกับโหมดปกติ
        # * >> Labels
        self.accl_dir_label = CTkLabel(self.entry_frame, text=f"Accel File Dir ")

        # * >> FileName Display on Button
        self.accl_dir_namedisplay_on_btn = CTkButton(
            self.entry_frame,
            text=f"ยังไม่เลือก Accel File",
            command=self.accel_mode.select_accel_file,
            fg_color="#969696"
        )

        # * >> Buttons
        self.start_image = Image.open(arrow_icon)
        self.start_photo = ImageTk.PhotoImage(
            self.start_image.resize((30, 20)))
        # * fonts
        # self.font = CTkFont(family='fixedsys', size=10, weight="bold")
        self.accl_start_btn = CTkButton(
            self.entry_frame,
            font=self.font,
            text=f"Start",
            # image=self.start_photo,
            command=self.accel_mode.accel_search,
            fg_color="#81ed55",
            text_color="#1E1E1E",
            border_color="#2d8a37",
            border_width=1.5,
            width=30,
            height=25
        )

        # * >> search order Stop Button (Stop button in normal mode)
        self.accel_stop_btn = CTkButton(
            self.entry_frame,
            font=self.font,
            text=f"Stop",
            command=self.stop_operation,
            fg_color="#bf2d2a",  # Red for Stop
            text_color="#ffffff",
            border_width=1.5,
            border_color="#732844",
            width=28,
            height=25
        )

        # * >> search order Skip Button (Accel mode)
        self.accel_skip_btn = CTkButton(
            self.entry_frame,
            font=self.font,
            text=f"Skip",
            command=self.accel_confirm_skip,
            fg_color="#f0ad4e",  # Orange for Skip
            text_color="#ffffff",
            border_width=1.5,
            border_color="#eea236",
            width=28,
            height=25
        )

        # * >> search order Del Button (Accel mode)
        self.accel_del_btn = CTkButton(
            self.entry_frame,
            font=self.font,
            text=f"Del",
            command=self.accel_confirm_delete,
            fg_color="#bf2d2a",  # Red for Del
            text_color="#ffffff",
            border_width=1.5,
            border_color="#732844",
            width=28,
            height=25
        )

        # * >> search order Stop All Button (To fully stop Accel mode)
        self.accel_stop_all_btn = CTkButton(
            self.entry_frame,
            font=self.font,
            text=f"Stop All",
            command=self.stop_accel_mode,
            fg_color="#bf2d2a",  # Red for Stop All
            text_color="#ffffff",
            border_width=1.5,
            border_color="#732844",
            width=28,
            height=25
        )

        # * > add transfers to accel mode component
        # * พวกนี้มันต้อง add แบบ toggle เพราะมันต้องสลับกับโหมดปกติ
        # * >> add transfer Button
        self.add_trans_to_accel_file_btn = CTkButton(
            self.entry_frame,
            text=f"เลือกใส่ Transfer",
            command=lambda: self.accel_mode.extract_sn_btn(
                self.accel_mode.accel_file_dir
            ),
            fg_color="#969696",
            text_color="#000",
        )

        # * > Log in button component
        # * >> A BTN to display the User_account
        self.btn_display = f"ID:{self.user_id.get()}" if self.user_id.get() and self.user_pw.get() else "Login"
        self.display_acc_btn = CTkButton(
            self.entry_frame,
            text=self.btn_display,
            command=lambda: UserAccount(self.root, self),
            width=28,
            height=25,
            font=self.font
        )

        # * > Accel mode
        # * >> Checkbox for activation toggle (Built-in label)
        self.accel_mode_checkbox = Checkbutton(
            self.checkbox_frame,
            text="Accel Mode",
            variable=self.is_accel_mode,
            command=self.accelmode_toggle
        )

        # ! __wip not ready
        # * > Auto Invoice Mode
        # * >> Checkbox for activation toggle (Built-in label)
        self.auto_inv_mode_checkbox = Checkbutton(
            self.checkbox_frame,
            text="Auto Inv",
            variable=self.is_auto_invoice_mode,
            command=self.auto_invoice_mode_toggle,
            bg="#BF2D2A",
            fg="#FFF"
        )
        self.auto_inv_mode_checkbox.grid(row=0, column=1, padx=5)

        # * > Seller voucher Pop-up Checkbox
        # * >> Checkbox for activation toggle (Built-in label)
        self.seller_voucher_popup_checkbox = Checkbutton(
            self.checkbox_frame,
            text="S.V.Notice",
            variable=self.is_seller_voucher_popup,
            command=self.seller_voucher_popup_checkbox_toggle,
            bg="#BF2D2A",
            fg="#FFF"
        )
        self.seller_voucher_popup_checkbox.grid(row=0, column=2, padx=5)

        # * import_file_frame !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # * > Export File and Bot status location display component
        self.display_location_label = CTkLabel(self.import_file_frame, text=f"File located: ")
        self.display_location_label.grid(row=0, column=0, padx=(5, 0))

        self.display_location_result = CTkLabel(
            self.import_file_frame, text=f"ยังไม่เลือก Import File", fg_color="#FFF", corner_radius=10)
        self.display_location_result.grid(row=0, column=1, padx=1)

        self.display_location_result_btn = CTkButton(
            self.import_file_frame, text=f"ใส่ Import File", command=self.select_excel, fg_color="#969696")
        self.display_location_result_btn.grid(row=0, column=2, padx=(0, 5))

        # >> bot status
        self.display_bot_status_label = CTkLabel(
            self.import_file_frame, text=f"Bot Status: ไม่มีการทำงาน (⸝⸝ᴗ﹏ᴗ⸝⸝) ᶻ 𝗓 𐰁", fg_color="#1f242e",
            text_color="#ffec1f", padx=5)
        self.display_bot_status_label.grid(row=0, column=3, padx=(5, 0))

        # >> Memory management buttons
        self.memory_reset_btn = CTkButton(
            self.import_file_frame, text="Reset Memory", command=self.reset_browser_memory, fg_color="#ff6b35",
            text_color="white", width=100, height=28)
        self.memory_reset_btn.grid(row=0, column=4, padx=(5, 0))

        self.memory_check_btn = CTkButton(
            self.import_file_frame, text="Check Memory", command=self.check_browser_memory, fg_color="#4a90e2",
            text_color="white", width=100, height=28)
        self.memory_check_btn.grid(row=0, column=5, padx=(5, 0))

        # * >> Finishing up button
        self.finishing_up_btn = CTkButton(
            self.import_file_frame, text="Finish!", command=self.finish_order, fg_color="#77579e",
            hover_color="#563871", text_color="#FFF", width=50, height=28, border_color="#FFF", border_width=1.5)
        self.finishing_up_btn.grid(row=0, column=6, padx=(5, 5))

        # * cp_file_frame !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # * > CP Data File location display component
        self.display_cp_location_label = CTkLabel(self.cp_file_frame, text=f"CP Data: ")
        self.display_cp_location_label.grid(row=0, column=0, padx=(5, 0))

        self.display_cp_location_btn = CTkButton(
            self.cp_file_frame, text=f"ยังไม่เลือก CP Data File", command=self.select_cp_excel, fg_color="#969696")
        self.display_cp_location_btn.grid(row=0, column=1, padx=(0, 5))

        # * Order_details_frame !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # * > Current Order display component
        # >> Labels
        self.label_current_order = CTkLabel(
            self.order_details_frame, text="Current Order: ", fg_color="#FFF",  corner_radius=4)
        self.label_current_order.grid(row=1, column=0, padx=(5, 0), pady=(2, 2), sticky=EW)
        # >> Value display
        self.display_current_order = CTkEntry(
            self.order_details_frame, state="readonly", width=210, height=25, border_width=0,
            textvariable=self.cus_order, corner_radius=4)
        self.display_current_order.grid(row=1, column=1, padx=(1, 0), sticky=EW, columnspan=1)

        # * > Current Status display component
        # * >> Labels
        self.label_current_status = CTkLabel(
            self.order_details_frame,
            text="Status: ",
            fg_color="#FFF",
            corner_radius=4
        )
        self.label_current_status.grid(row=1, column=2, padx=(5, 0), columnspan=1)
        # * >> Value display
        self.display_current_status = CTkLabel(
            self.order_details_frame,
            textvariable=self.cus_cur_status,
            text_color="#000000",
            fg_color="#8fd4ff",
            corner_radius=4
        )
        self.display_current_status.grid(row=1, column=3, padx=(1, 0), sticky=EW)

        # * > Lazada Customer Alternate Name (Tax Name)
        # * >> Labels
        self.label_lazada_tax_name = CTkLabel(
            self.order_details_frame,
            text="ชื่อผู้เสียภาษี (Lazada): ",
            fg_color=f"{self.bg_by_market_place['LAZADA']}",
            text_color="#FFF",
            corner_radius=4
        )
        # self.label_lazada_tax_name.grid(row=1, column=4, padx=(5, 0), pady=(2, 2), sticky='ew')
        # * >> Value display
        self.display_lazada_tax_name = CTkEntry(
            self.order_details_frame,
            height=25,
            border_width=0,
            textvariable=self.cus_tax_name_lazada,
            state="readonly",
            corner_radius=4
        )
        # self.display_lazada_tax_name.grid(row=1, column=5, padx=(1, 0), sticky='ew')

        # * > Customer Name display component
        # * >> Labels
        self.label_cus_name = CTkLabel(
            self.order_details_frame, text="ชื่อ", fg_color="#FFF", corner_radius=4)
        self.label_cus_name.grid(row=2, column=0, padx=(5, 0), pady=(2, 2), sticky='ew')
        # * >> Value display
        self.display_cus_name = CTkEntry(
            self.order_details_frame, height=25, border_width=0,  textvariable=self.cus_name,  state="readonly")
        self.display_cus_name.grid(row=2, column=1, padx=(1, 0), sticky='ew')

        # * > Is Tax?? display component
        # * >> Labels
        self.label_is_tax = CTkLabel(self.order_details_frame, text="ใบกำกับ", fg_color="#FFF", corner_radius=4)
        self.label_is_tax.grid(row=2, column=2, padx=(5, 0), sticky='ew', columnspan=1)
        # * >> Value display
        self.display_is_tax = CTkLabel(
            self.order_details_frame,
            textvariable=self.cus_tax_status,
            fg_color="#fff",
            corner_radius=4
        )
        self.display_is_tax.grid(row=2, column=3, padx=(1, 0), sticky=EW, columnspan=1)

        # * > Tax Number display component
        # >> Labels
        self.label_tax_number = CTkLabel(
            self.order_details_frame, text="เลขผู้เสียภาษี", fg_color="#FFF", corner_radius=4)
        self.label_tax_number.grid(row=2, column=4, padx=(5, 0), sticky='ew')
        # >> Value display
        self.display_tax_number = CTkEntry(
            self.order_details_frame,
            width=105,
            height=25,
            border_width=0,
            textvariable=self.tax_num,
            state="readonly",
            corner_radius=4
        )
        self.display_tax_number.grid(row=2, column=5, padx=(1, 0), sticky='ew')

        # * > Customer Email display component
        # >> Labels
        self.label_cus_email = CTkLabel(self.order_details_frame, text="Email", fg_color="#FFF", corner_radius=4)
        self.label_cus_email.grid(row=2, column=6, padx=(5, 0), sticky='ew')
        # >> Value display
        self.display_cus_email = CTkEntry(
            self.order_details_frame, height=25, border_width=0, width=180, textvariable=self.cus_email,
            state="readonly", corner_radius=4)
        self.display_cus_email.grid(row=2, column=7, padx=(1, 4), sticky='ew')

        # * > Customer Address display component ส่วนแสดงผลที่อยู่ลูกค้า
        # * >>Address
        # >>> Labels
        self.label_cus_address = CTkLabel(self.invoice_details_frame, text="ที่อยู่: ", fg_color="#FFF")
        self.label_cus_address.grid(row=3, column=0, padx=(5, 0), pady=(2, 2), sticky="nsew")
        # >>> Value display
        self.display_cus_address = CTkTextbox(
            self.invoice_details_frame, width=350, height=90, border_width=0, text_color="#000000", fg_color="#fff",
            state="disabled"
        )
        self.display_cus_address.grid(row=3, column=1, padx=(1, 0), columnspan=2, sticky=W)
        self.display_cus_address.tag_add("left", "1.0", "1.end")

        # * >> Customer remark display component ส่วนแสดงผลหมายเหตุลูกค้า col 4-5
        # >>> Labels
        self.label_cus_remark = CTkLabel(
            self.invoice_details_frame,
            text="หมายเหตุจากผู้ซื้อ: ",
            fg_color="#FFF",
            height=1,
        )
        self.label_cus_remark.grid(row=3, column=4, padx=(5, 0), pady=(2, 2), sticky="nsew")
        # >>> Value display
        self.display_cus_remark = CTkTextbox(
            self.invoice_details_frame, width=160, height=90, border_width=0, text_color="#000000", fg_color="#fff",
            state="disabled")
        self.display_cus_remark.grid(
            row=3, column=5, padx=(1, 0), columnspan=1, sticky=W)
        self.display_cus_remark.tag_add("left", "1.0", "1.end")

        # * >> Order Note display component ส่วนแสดงผลหมายเหตุลูกค้า col 6-7
        # >>> Labels
        self.label_order_note = CTkLabel(
            self.invoice_details_frame, text="บันทึก: ", fg_color="#FFF", height=1,)
        self.label_order_note.grid(row=3, column=6, padx=(5, 0), pady=(2, 2), sticky="nsew")
        # >>> Value display
        self.display_order_note = CTkTextbox(
            self.invoice_details_frame, width=160, height=90, border_width=0, text_color="#000000", fg_color="#fff",
            state="disabled")
        self.display_order_note.grid(row=3, column=7, padx=(1, 0), columnspan=1, sticky=W)
        self.display_order_note.tag_add("left", "1.0", "1.end")

        #! ปรับ ui ใหม่ ทำให้ตรงนี้ไม่ได้ใช้
        # * > Customter Products List
        # self.label_cus_products = CTkLabel(self.products_list_frame, text="รายการสินค้า: ", fg_color="#FFF", height=1)
        # self.label_cus_products.pack()

        #! ปรับ ui ใหม่ ทำให้ตรงนี้ไม่ได้ใช้
        # * >> สร้าง Treeview widget
        # self.tree = ttk.Treeview(self.products_list_frame, columns=(
        #     "Productname", "Price", "QTY"), show="headings", height=8)
        # self.tree.column("Productname", anchor=W, width=350)
        # self.tree.column("Price", width=self.measure_text("Price")+10)
        # self.tree.column("QTY", width=self.measure_text("QTY")+10)
        # self.tree.heading("Productname", text="Product")
        # self.tree.heading("Price", text="Price")
        # self.tree.heading("QTY", text="QTY")

        # self.y_scrollbar = ttk.Scrollbar(self.products_list_frame, command=self.tree.yview)
        # self.y_scrollbar.pack(side="right", fill="y")

        # self.tree.pack(side='bottom', fill=X)
        # self.tree.config(yscrollcommand=self.y_scrollbar.set)

        # * > Margetplace Products display Header purchased products list header
        # * Initialize OrderDisplayManager
        self.order_display_manager = OrderDisplayManager(self.mp_products_list_frame, self)

        self.mimic_column_headers = ['No.', 'สินค้าทั้งหมด',
                                     'ราคาต่อชิ้น', 'QTY', 'ราคาขายสุทธิ', 'ราคา+รีเบท', 'ปรับราคา']
        self.order_display_manager.create_header(self.mimic_column_headers)

        # * > demonic cp segment
        # * >> Label
        self.demonicCp_label = CTkLabel(
            self.demonic_frame, text="CP Adder", fg_color="#FFF", height=4, padx=2, pady=2)
        self.demonicCp_label.grid(row=0, column=0, padx=(0, 1))
        # * >> Inputs1
        self.demonicCp_itemNo = StringVar()
        self.demonicCp_itemNo_input = Entry(
            self.demonic_frame, textvariable=self.demonicCp_itemNo, width=10)
        self.demonicCp_itemNo_input.grid(row=0, column=3, padx=(0, 2))
        # * >> Inputs2
        self.demonicCp_cpNo = StringVar()
        self.demonicCp_cpNo_input = Entry(
            self.demonic_frame, textvariable=self.demonicCp_cpNo, width=10)
        self.demonicCp_cpNo_input.grid(row=0, column=4)
        # * >> Buttons Auto add CP
        self.demonicCp_btn = CTkButton(
            self.demonic_frame,
            text="SonicBlow!",
            command=self.cp_sonic_blow_handler,
            width=60,
            height=4
        )
        self.demonicCp_btn.grid(row=0, column=5, padx=(1, 0))

        # * > Log windows component
        self.report_log = CTkTextbox(self.log_frame, state=DISABLED, height=208)
        self.report_log.pack(side="left", fill="both", expand=True)

        ## * Create DataSourceSelector instance ###########
        self.data_source_selector = DataSourceSelector(self.root, self)
        self.user_account = UserAccount(self.root, self)
        self.accelmode_toggle()

    def reset_all_display(self):
        self.result = ""
        self.table_location = ""
        self.cus_order.set("")
        self.is_tax_required.set(False)
        self.tax_num.set("")
        self.cus_email.set("")
        self.cus_tax_status.set("")
        self.cus_name.set("")
        self.cus_address = ""
        self.cus_remark = ""
        self.order_note = ""
        self.update_gui('', self.display_cus_address)
        self.cus_province.set("")
        self.cus_district.set("")
        self.cus_sub_district.set("")
        self.cus_tel.set("")
        self.cus_cur_status.set("")
        self.cus_account_name.set("")
        self.display_is_tax.configure(font=("Chiller", 10, "normal"))
        self.cus_tax_name_lazada.set("")

    def update_log(self, update_txt):
        self.update_txt = update_txt
        self.report_log.configure(state=NORMAL)
        self.report_log.insert(END, self.update_txt + "\n")
        self.report_log.configure(state=DISABLED)

    def update_mp_frame(self, data_list):
        data_list
        self.report_log.configure(state=NORMAL)
        self.report_log.insert(END, self.update_txt + "\n")
        self.report_log.configure(state=DISABLED)

    def define_marketplace(self):
        file_input = self.table_location
        df = pd.read_excel(file_input)
        search_words = ['shopee', 'lazada']
        matches = [
            word for col in df.columns for word in search_words if word.lower() in col.lower()]

        # # เอา Dataframe มา groupby
        # if matches[0].lower() == 'lazada':
        #     self.group_by_order(file_input)

        if all(item == matches[0] for item in matches):
            return matches[0].upper()
        else:
            raise ValueError(
                "Error: Cannot varify the marketplace from this file, check the file you've imported")

    def select_excel(self):
        self.result = "Excel"
        print("Select Excel")
        self.table_location = filedialog.askopenfilename(title="Select Shopee order toship file")

        # * ตัดเอาเฉพาะ ชื่อไฟล์
        self.display_location_result.configure(text=f"{self.table_location.split('/')[-1]}")

        # * target should come before get dataframe
        self.marketplace_target.set(self.define_marketplace())
        result = self.marketplace_target.get()
        print("ต้องตีเว็บไหน", result)
        # self.canvas.config(fg_color=f'{self.bg_by_market_place[self.marketplace_target.get()]')
        self.entry_frame.configure(fg_color=f'{self.bg_by_market_place[str(result)]}')
        self.marketplace_label.configure(
            fg_color=f'{self.bg_by_market_place[str(result)]}',
            width=1000 if self.marketplace_target.get() == "" else 0
        )

        print("myapp:self.label_lazada_tax_name: ", self.label_lazada_tax_name)
        if result == "LAZADA":
            self.label_lazada_tax_name.grid(row=1, column=4, padx=(5, 0), pady=(2, 2), sticky='ew')
            self.display_lazada_tax_name.grid(row=1, column=5, columnspan=1, padx=(1, 0), sticky='ew')
        else:
            self.label_lazada_tax_name.grid_remove()
            self.display_lazada_tax_name.grid_remove()

        # * หลังจากได้ไฟล์เข้ามาแล้ว (self.table_location) เราจะทำการสร้างเป็น dataframe ด้วย function get_data_frame()
        self.get_data_frame()
        print("Table Location:", self.table_location)
        self.update_log("แอดไฟล์")

    def select_cp_excel(self):
        self.cp_table_location = filedialog.askopenfilename(title="Select CP Data file")
        if self.cp_table_location:
            self.display_cp_location_btn.configure(text=f"{self.cp_table_location.split('/')[-1]}")
            try:
                self.cp_df = pd.read_excel(self.cp_table_location)
                if 'usage_start_date' in self.cp_df.columns:
                    self.cp_df['usage_start_date'] = pd.to_datetime(self.cp_df['usage_start_date'], errors='coerce')
                if 'usage_end_date' in self.cp_df.columns:
                    self.cp_df['usage_end_date'] = pd.to_datetime(self.cp_df['usage_end_date'], errors='coerce')
                self.update_log(f"โหลดไฟล์ CP Data สำเร็จ: {len(self.cp_df)} รายการ")
            except Exception as e:
                self.update_log(f"โหลดไฟล์ CP Data ล้มเหลว: {e}")
                self.cp_df = None

    def group_by_order(self, file_input, dtype):
        df = pd.read_excel(file_input, dtype=dtype)
        #! สำคัญมาก ถ้าอยากให้ nan หาย เอา dfมาใช้ method fillna('', inplace=True) "//การใช้ Inplace ทำให้แก้ ที่ df โดยตรงโดยไม่ต้องเก็บค่าใหม่
        # df.fillna('', inplace=True)

        # เพิ่มส่วนที่ไม่มี และหาไม่ได้
        df['ส่วนลดจาก Shopee'], df['ประเภทใบกำกับภาษี'], df['โค้ดส่วนลดชำระโดย Shopee (เช่น โค้ดจากโปรแกรม ร้านโค้ดคุ้ม, โค้ดส่วนลด Shopee, โค้ดส่วนลด Shopee Mall)'], df[
            'ประเภทสาขา'], df['หมายเหตุจากผู้ซื้อ'], df['บันทึก'] = 0.00, "", 0, "", "", ""

        # กำหนด Datatype
        data_types = {
            'orderNumber': str, 'ส่วนลดจาก Shopee': float, 'ประเภทใบกำกับภาษี': str,
            'โค้ดส่วนลดชำระโดย Shopee (เช่น โค้ดจากโปรแกรม ร้านโค้ดคุ้ม, โค้ดส่วนลด Shopee, โค้ดส่วนลด Shopee Mall)':
            float, 'ประเภทสาขา': str, 'หมายเหตุจากผู้ซื้อ': str, 'บันทึก': str, 'paidPrice': float, 'variation': str,
            'billingAddr': str, 'createTime': str, 'branchNumber': str, 'billingAddr2': str, 'customerEmail': str,
            'taxCode': str, 'billingAddr3': str, 'billingAddr4': str, 'billingAddr5': str, 'billingName': str,
            'billingPhone': str, 'customerName': str, 'shippingFee': float, 'sellerDiscountTotal': float,
            'unitPrice': float}
        df = df.astype(data_types)

        # อุดค่าว่างก่อนไม่งั้น จะใช้ size() ไม่ได้ (vectorized แทน loop)
        float_cols = df.select_dtypes(include=['float']).columns
        str_cols = df.select_dtypes(include=['object']).columns
        df[float_cols] = df[float_cols].fillna(0)
        df[str_cols] = df[str_cols].replace('nan', '').fillna('')

        # เพิ่มส่วนที่ไม่มี แต่สามารถหาคำนวณเพิ่มเองได้
        result_count = df.groupby(['orderNumber', 'sellerSku', 'itemName',
                                  'unitPrice', 'variation']).size().reset_index(name='จำนวน')

        result_with_additional_columns_df = df.groupby('orderNumber').agg({
            'status': 'first',
            'ส่วนลดจาก Shopee': 'first',
            'ประเภทใบกำกับภาษี': 'first',
            'customerEmail': 'first',
            'โค้ดส่วนลดชำระโดย Shopee (เช่น โค้ดจากโปรแกรม ร้านโค้ดคุ้ม, โค้ดส่วนลด Shopee, โค้ดส่วนลด Shopee Mall)': 'first',
            'ประเภทสาขา': 'first',
            'หมายเหตุจากผู้ซื้อ': 'first',
            'บันทึก': 'first',
            'billingName': 'first',
            'billingAddr': 'first',
            'billingAddr2': 'first',
            'billingAddr4': 'first',
            'billingAddr3': 'first',
            'billingAddr5': 'first',
            'taxCode': 'first',
            'billingPhone': 'first',
            'customerName': 'first',
            'paidPrice': 'sum',
            'createTime': 'first',
            'branchNumber': 'first'
        })
        result_with_additional_columns_df = result_with_additional_columns_df.astype(
            {'billingAddr5': str, 'billingPhone': str})

        # ** ปรับแต่ง Column สำหรับ LAZADA--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # * สร้าง sum_column  ขึ้นมาใหม่ --------------------------------------------------------
        # *> 'ราคาขายสุทธิ'
        result_count.loc[:, 'ราคาขายสุทธิ'] = result_count["จำนวน"] * result_count["unitPrice"]

        # *> 'ชื่อผู้รับ' AND 'หมายเลขโทรศัพท์' - REMOVED BUGGY ASSIGNMENT
        # These were assigned by index which caused mismatch.
        # They will be assigned correctly after merge from result_with_additional_columns_df

        # *> 'โค้ดส่วนลดชำระโดยผู้ขาย'
        seller_discount_df = df.groupby('orderNumber')['sellerDiscountTotal'].sum(
        ).reset_index(name='โค้ดส่วนลดชำระโดยผู้ขาย')
        seller_discount_df.loc[:, 'โค้ดส่วนลดชำระโดยผู้ขาย'] *= -1

        # *> 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ'
        shipping_fee_df = df.groupby('orderNumber')['shippingFee'].sum(
        ).reset_index(name='ค่าจัดส่งที่ชำระโดยผู้ซื้อ')

        # * ปรับแต่งค่าใน Column
        # result_with_additional_columns_df = result_with_additional_columns_df['branchNumber'].map(lambda x: )

        # *  รวม dataframe เป็น dataframe ใหม่
        result_df = (
            result_count
            .merge(seller_discount_df, on='orderNumber', how='left')
            .merge(result_with_additional_columns_df, on='orderNumber', how='left')
            .merge(shipping_fee_df, on='orderNumber', how='left')
        ).copy()

        # * เราต้องการ column ที่มีชื่อต่างกัน แต่ข้อมูลเหมือนกัน เลยต้อง copy column เพิ่ม
        result_df.loc[:, 'รายละเอียดที่อยู่'] = result_df['billingAddr'].copy()

        # * Fix: Assign 'ชื่อผู้รับ' and 'หมายเลขโทรศัพท์' correctly from merged data
        result_df.loc[:, 'ชื่อผู้รับ'] = result_df['billingName'].copy()
        result_df.loc[:, 'หมายเลขโทรศัพท์'] = result_df['billingPhone'].copy()

        # / Clean ที่อยู่: แยก address โดย U+00B7 (·) และลบชื่อบริษัท/สาขา เป็นการจัดการค่าใน export file ของ lazada เท่านั้น ไม่มีการเอาค่าจากแหล่งอื่นมาเกี่ยวข้อง
        address_split_result = result_df.apply(self._split_lazada_address, axis=1, result_type='expand')
        result_df.loc[:, 'รายละเอียดที่อยู่'] = address_split_result[0]
        result_df.loc[:, 'billingAddr2'] = address_split_result[1]

        # * Fill missing sub-district (แขวง/ตำบล) data is now deferred to order_search() on-demand.

        # ลบ keywords ซ้ำซ้อนจากที่อยู่ (ตำบล, อำเภอ, จังหวัด, etc.)
        result_df['รายละเอียดที่อยู่'] = result_df.apply(self._remove_redundant_keywords, axis=1)

        result_df.loc[:, 'ประเภทสาขา'] = result_df['branchNumber'].copy()

        # * สกัดและหาเลขสาขา จากข้อมูลที่กรอกมั่วๆไร้ซึ่ง pattern จาก lazada exportfile และเก็บไว้ในตัวแปร extracted_branch_df สาขาจะแสดงเป็นเลข 5 หลักแทนช่องว่างด้วย 0 แต่สาขา 00000 จะแสดงเป็น "สำนักงานใหญ่"
        extracted_branch_df = result_df['ประเภทสาขา'].apply(self.find_branch)

        # * เปลี่ยน ค่าใน col branchNumber ให้กลายเป็นบอกเฉพาะเลขสาขาถ้าเป็นสาขาย่อย และ เป็นค่าว่างถ้าเป็นสำนักงานใหญ่
        result_df.loc[:, 'branchNumber'] = extracted_branch_df.copy()
        result_df.loc[:, 'branchNumber'] = result_df['branchNumber'].map(
            lambda row: "" if row == "สำนักงานใหญ่" else row)

        # * นำค่าที่สกัดและแปลงจากตัวแปร extracted_branch_df มาหาประเภทสาขา หาก ค่าใน cell เป็น"สำนักงานใหญ่" จะ return "สำนักงานใหญ่" ถ้าไม่ใช่ จะแสดงเป็น "สาขาย่อย" (มีค่าเป็นเลขสาขา จะ return เป็น สาขาย่อย)
        # * ใช้ผลลัพธ์จาก find_branch เพื่อกำหนดประเภทสาขา
        result_df['ประเภทสาขา'] = extracted_branch_df.map(
            lambda row: "สำนักงานใหญ่" if row == "สำนักงานใหญ่" else "สาขาย่อย")

        # * เปลี่ยนค่าใน Col billingAddrs ตัดภาษาอังกฤษออก เนื่องจาก ที่อยู่ที่ได้จาก exportfile laz จะมี pattern เป็น ไทย/ อังกิก เช่น "บางปะกง/ Bang Pakong"
        # >> addr4 = เขต/อำเภอ, addr3 = จังหวัด
        address_divs = ['billingAddr4', 'billingAddr3']
        for address_div in address_divs:
            result_df.loc[:, f'{address_div}'] = result_df[f'{address_div}'].map(lambda row: row.split('/')[0].strip())

        # * เปลี่ยน Dtype ของ Column ['createTime'] (วันที่ทำการสั่งซื้อ) จาก Series ให้เป็นobjวันที่ เนื่องจากอันเดิมมันเอาไป Sort ไม่ได้ เวลาออกเป็นตาราง
        result_df['createTime'] = pd.to_datetime(result_df['createTime'], format='mixed', dayfirst=True)
        # * >  แปลง objวันที่ ให้กลายเป็น number ใน excel เพื่อให้แสดงผลใน cel เหมือนกับ exported file ของ shopee
        result_df.loc[:, 'createTime'] = result_df['createTime'].dt.strftime('%Y-%m-%d %H:%M')

        # * ตรวจสอบผลลัพธ์
        # print(f"""qty ใน lazada""")
        # print(result_count)

        # print("ราคาขายสุทธิ")
        # print(total_per_order_df)

        # * เปลี่ยนชื่อ column // เปลี่ยนชื่อ column // เปลี่ยนชื่อ column // เปลี่ยนชื่อ column // เปลี่ยนชื่อ column // เปลี่ยนชื่อ column // เปลี่ยนชื่อ column
        result_df.rename(columns={
            'orderNumber': 'หมายเลขคำสั่งซื้อ',
            'sellerSku': 'เลขอ้างอิง SKU (SKU Reference No.)',
            'itemName': 'ชื่อสินค้า',
            'unitPrice': 'ราคาขาย',
            'status': 'สถานะการสั่งซื้อ',
            'billingName': 'ชื่อ',
            'billingAddr': 'ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป',
            'billingAddr2': 'แขวง/ตำบล',
            'billingAddr4': 'เขต/อำเภอ.1',
            'billingAddr3': 'จังหวัด.1',
            'billingAddr5': 'รหัสไปรษณีย์.1',
            'taxCode': 'หมายเลขประจำตัวผู้เสียภาษี',
            'billingPhone': 'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี',
            'customerName': 'ชื่อผู้ใช้ (ผู้ซื้อ)',
            'paidPrice': 'จำนวนเงินทั้งหมด',
            'createTime': 'วันที่ทำการสั่งซื้อ',
            'branchNumber': 'รหัสประจำสาขา',
            'variation': 'ชื่อตัวเลือก',
            'customerEmail': 'อีเมลสำหรับรับใบกำกับภาษี'
        },
            inplace=True
        )
        result_df.loc[:, 'หมายเลขคำสั่งซื้อ'] = result_df['หมายเลขคำสั่งซื้อ'].astype(str)

        print("ตารางใหม่")
        print(result_df)
        excel_file_path = "output_test.xlsx"
        result_df.to_excel(excel_file_path, index=False, na_rep="", engine="openpyxl")
        return result_df

    @staticmethod
    def _split_lazada_address(row):
        """แยก address โดย U+00B7 (·) และลบชื่อบริษัท/สาขาออก"""
        addr = str(row['รายละเอียดที่อยู่'])
        extracted_sub_district = row['billingAddr']

        if '\u00B7' in addr:
            parts = addr.split('\u00B7')
            if len(parts) >= 2:
                addr = parts[0].strip()
                sub_part = parts[1].strip()
                if '/' in sub_part:
                    sub_part = sub_part.split('/')[0].strip()
                extracted_sub_district = sub_part
            else:
                addr = parts[0].strip()

        # ลบชื่อบริษัท
        company_patterns = [
            r'บริษัท\s+[^\s]+(?:\s+[^\s]+){0,5}?\s+จำกัด\s*(?:\(มหาชน\))?\s*',
            r'บริษัท[\u0E00-\u0E7Fa-zA-Z0-9\.]+จำกัด\s*(?:\(มหาชน\))?\s*',
            r'บจก\.?\s*[\u0E00-\u0E7Fa-zA-Z0-9\.]+\s*',
            r'บมจ\.?\s*[\u0E00-\u0E7Fa-zA-Z0-9\.]+\s*',
            r'\b(?:Company|Co\.?,?\s*Ltd\.?|Corporation|Corp\.?|Inc\.?)\b\s*',
        ]
        for pattern in company_patterns:
            addr = re.sub(pattern, '', addr, flags=re.IGNORECASE)
        addr = re.sub(r'^\s*บริษัท\s*', '', addr)
        addr = re.sub(r'^\s*บ\.\s*', '', addr)

        # ลบ branch indicators
        branch_patterns = [
            r'\(?\s*สำนักงานใหญ่\s*\)?',
            r'\(?\s*สนง\.?\s*ใหญ่\s*\)?',
            r'\(?\s*สนญ\.?\s*\)?',
            r'\(?\s*Head\s+Office\s*\)?',
            r'\(?\s*HQ\s*\)?',
            r'\(?\s*สาขา\s*\d+\s*\)?',
            r'\(?\s*Branch\s*\d+\s*\)?',
            r'\(?\s*สาขาที่\s*\d+\s*\)?',
            r'\bสาขา\d+\b',
        ]
        for pattern in branch_patterns:
            addr = re.sub(pattern, '', addr, flags=re.IGNORECASE)

        # Clean up
        addr = re.sub(r'\(\s*\)', '', addr)
        addr = re.sub(r'\s+', ' ', addr).strip()
        return addr, extracted_sub_district

    def _fill_missing_subdistrict(self, row, address_df):
        """หาตำบล/แขวงที่ขาดหายไปจากข้อมูล Excel หรือ Google"""
        district_key = 'billingAddr4' if 'billingAddr4' in row else 'เขต/อำเภอ.1'
        province_key = 'billingAddr3' if 'billingAddr3' in row else 'จังหวัด.1'
        zipcode_key = 'billingAddr5' if 'billingAddr5' in row else 'รหัสไปรษณีย์.1'
        full_address_key = 'billingAddr' if 'billingAddr' in row else 'ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป'
        subdistrict_key = 'billingAddr2' if 'billingAddr2' in row else 'แขวง/ตำบล'
        details_key = 'รายละเอียดที่อยู่'

        district = str(row[district_key]).split('/')[0].strip() if pd.notna(row[district_key]) else ''
        province = str(row[province_key]).split('/')[0].strip() if pd.notna(row[province_key]) else ''
        zipcode = str(row[zipcode_key]).strip() if pd.notna(row[zipcode_key]) else ''
        full_address = str(row[full_address_key]) if pd.notna(row[full_address_key]) else ''

        district = re.sub(r'^(?:อำเภอ|อ\.|เขต)\s*', '', district)
        province = re.sub(r'^(?:จังหวัด|จ\.)\s*', '', province)

        candidates = pd.DataFrame()
        if district and province:
            candidates = address_df[
                (address_df['DistrictThaiShort'].str.strip() == district) &
                (address_df['ProvinceThai'].str.strip() == province)
            ]
            if candidates.empty and district.startswith('เมือง'):
                short_district = district[len('เมือง'):]
                candidates = address_df[
                    (address_df['DistrictThaiShort'].str.strip() == short_district) &
                    (address_df['ProvinceThai'].str.strip() == province)
                ]

        if candidates.empty and zipcode:
            candidates = address_df[address_df['PostCodeMain'].str.strip() == zipcode]

        possible_tambons = []
        if not candidates.empty:
            possible_tambons = candidates['TambonThaiShort'].unique().tolist()
            possible_tambons.sort(key=len, reverse=True)

            candidates_not_district = [t for t in possible_tambons if t != district]
            candidates_is_district = [t for t in possible_tambons if t == district]

            for tambon in candidates_not_district:
                if pd.isna(tambon):
                    continue
                if tambon in full_address:
                    return tambon

            for tambon in candidates_is_district:
                if pd.isna(tambon):
                    continue
                if re.search(r'(?:ต\.|ตำบล|แขวง)\s*' + re.escape(tambon), full_address):
                    return tambon
                if full_address.count(tambon) >= 2:
                    return tambon

        # Fallback: Google Search
        if possible_tambons:
            try:
                address_dict = {
                    "cleaned_address": row[details_key],
                    "amphoe": district, "province": province, "postal": zipcode
                }
                google_result = self.bot.google_for_tambon(address_dict, possible_tambons)
                if google_result:
                    return google_result
            except Exception as e:
                print(f"Google search error: {e}")

        return row[subdistrict_key]

    @staticmethod
    def _remove_redundant_keywords(row):
        """ลบ keywords ซ้ำซ้อนจากที่อยู่ เช่น ตำบล, อำเภอ, เขต, จังหวัด"""
        addr = str(row['รายละเอียดที่อยู่'])
        redundant_patterns = [
            r'\bตำบล[^\s]*', r'\bต\.[^\s]*',
            r'\bอำเภอ[^\s]*', r'\bอ\.[^\s]*',
            r'\bแขวง[^\s]*', r'\bเขต[^\s]*',
            r'\bจังหวัด[^\s]*', r'\bจ\.[^\s]*',
        ]
        for pattern in redundant_patterns:
            addr = re.sub(pattern, '', addr)
        addr = re.sub(r'\s+', ' ', addr).strip()
        addr = re.sub(r'\s*-\s*$', '', addr)
        return addr

    def f(self, d):
        return '{0:n}'.format(d)

    def get_data_frame(self):
        target = self.marketplace_target.get()
        self.file_path = self.table_location
        if target == 'LAZADA':
            self.load_subdistrict_cache()

        # * dtype preset สำหรับการโหลดข้อมูล เพื่อป้องกัน error จากการที่บาง column มีค่า missing หรือมีค่าไม่ตรงกับ type ที่ควรจะเป็น ซึ่งจะทำให้เกิด error ตอนโหลดข้อมูลเข้ามาเป็น DataFrame
        base_dtypes = {
            'หมายเลขประจำตัวผู้เสียภาษี': str, 'รหัสไปรษณีย์.1': str,
            'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี': str, 'จำนวน': int,
            'ค่าจัดส่งที่ชำระโดยผู้ซื้อ': float, 'โค้ดส่วนลดชำระโดยผู้ขาย': float,
            'แขวง/ตำบล': str, 'ประเภทสาขา': str, 'สาขาย่อย': str,
            'รหัสประจำสาขา': str, 'หมายเหตุจากผู้ซื้อ': str, 'บันทึก': str,
            'orderNumber': str
        }
        # * เฉพาะ Lazada ที่มี column 'taxCode' ซึ่งมีค่าเป็นเลขประจำตัวผู้เสียภาษีที่บางครั้งอาจจะมีค่า missing หรือไม่ตรงกับ type ที่ควรจะเป็น จึงต้องเพิ่ม dtype preset สำหรับ column นี้โดยเฉพาะ เพื่อป้องกัน error ตอนโหลดข้อมูลเข้ามาเป็น DataFrame
        if target == 'LAZADA':
            base_dtypes['taxCode'] = str

        self.columns_dtype_preset = base_dtypes

        try:
            # * แยก Logic การโหลดข้อมูล
            if target == 'SHOPEE':
                print("Loading Shopee data...")
                self.data_frame = pd.read_excel(self.file_path, dtype=self.columns_dtype_preset)
            elif target == 'LAZADA':
                print("Loading Lazada data...")
                self.data_frame = self.group_by_order(self.file_path, self.columns_dtype_preset)
            else:
                print("Unknown Marketplace")
                return

            # * ตรวจสอบ Data
            if not self.data_frame.empty:
                print(f"มี Data Frame (Type: {type(self.data_frame)})")
            else:
                print("Data Frame ว่างเปล่า")

        except FileNotFoundError:
            print(f"ไม่พบไฟล์ที่: {self.file_path}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"เกิดข้อผิดพลาด: {e}")
            # พยายามกำหนด self.data_frame เป็น DataFrame เปล่าๆ เพื่อไม่ให้เกิด AttributeError ภายหลัง
            self.data_frame = pd.DataFrame()

    def update_gui(self, address, widget):
        if address != "":
            input = address.strip()
        else:
            input = "-"

        self.cus_address = input
        widget.configure(state=NORMAL)
        widget.delete(1.0, END)
        widget.insert(END, input)
        widget.configure(state=DISABLED)

    def update_gui_remark(self):
        if self.cus_remark == "" or self.cus_remark == "nan":
            self.display_cus_remark.configure(state=NORMAL)
            self.display_cus_remark.delete(1.0, END)
            self.display_cus_remark.insert(END, 'ไม่มี')
            self.display_cus_remark.configure(state=DISABLED)

        else:
            self.display_cus_remark.configure(state=NORMAL)
            self.display_cus_remark.delete(1.0, END)
            self.display_cus_remark.insert(END, self.cus_remark)
            self.display_cus_remark.configure(state=DISABLED)

    def update_gui_note(self):
        if self.order_note == "" or self.order_note == "nan":
            self.display_order_note.configure(state=NORMAL)
            self.display_order_note.delete(1.0, END)
            self.display_order_note.insert(END, 'ไม่มี')
            self.display_order_note.configure(state=DISABLED)

        else:
            self.display_order_note.configure(state=NORMAL)
            self.display_order_note.delete(1.0, END)
            self.display_order_note.insert(END, self.order_note)
            self.display_order_note.configure(state=DISABLED)

    # * widget รายการสินค้า ///////////////////////////////////////////////
    def show_products(self, products_list):
        # for i in self.tree.get_children():
        #     self.tree.delete(i)
        self.total_price = 0
        for product in products_list:
            product_name = product["เลขอ้างอิง SKU (SKU Reference No.)"]
            price = product["ราคาขายสุทธิ"]
            shopee_rebate = product['ส่วนลดจาก Shopee']
            price_plusrebate = price+shopee_rebate
            QTY = product['จำนวน']
            self.total_price += price_plusrebate
            # self.tree.insert("", "end", values=(
            #     product_name, self.f(price_plusrebate), QTY))

        # * แสดง summary (ค่าขนส่ง, voucher, ราคารวม) ใต้ตาราง order แทนที่จะแสดงใน Treeview
        self.order_display_manager.create_summary_section(
            self.marketplace_target.get(),
            products_list,
            self.nondistortedData
        )

    def get_pure_address(self, cus_address):
        """
            •นำคีเวิร์ดไปหาใน string cus_address ว่าเจอไหม ถ้าเจอให้เก็บตำแหน่งที่เจอมา
            \n•แล้วเลือกเอาตำแหน่งตัวอักษรใน string cus_address ตั้งแต่แรก[0, found_keyword]จนสิ้นสุดที่ตำแหน่งที่เจอค่า keyword
            \n•!ปัญหาคือใช้ได้กับเฉพาะภาษาไทย
        """
        # สร้างรายชื่อของตำแหน่งที่พบคำใน customer_address
        keywords = ["เขต", "แขวง", "ต.", "ตำบล",
                    "อ.", "อำเภอ", "จ.", "จังหวัด"]
        positions = []

        for keyword in keywords:
            if keyword in cus_address:
                keyword_position = cus_address.find(keyword)
                positions.append(keyword_position)

        # หาตำแหน่งสูงสุดและตำแหน่งต่ำสุดในรายชื่อตำแหน่ง
        if positions:
            min_position = min(positions)
            max_position = max(positions)
        else:
            min_position = -1
            max_position = -1

        # ลบตั้งแต่ตำแหน่งที่พบคำไปจนสุดลงท้ายของ customer_address
        if min_position >= 0:
            truncated_address = cus_address[:min_position]
        else:
            truncated_address = cus_address

        print("get_pure_address result: ", truncated_address.strip())
        return truncated_address.strip().replace('\u200b', '')

    def clean_duplicate_parts(self, address):
        # ใช้ regex เพื่อค้นหาและลบคำย่อที่มีส่วนที่มากกว่าคำเต็ม
        pattern = r'(ต\..+?)\s+?(ตำบล|อ\..+?)\s+?(อำเภอ|จ\..+?)\s+?(จังหวัด)'

        matches = re.findall(pattern, address)
        if matches:
            cleaned_address = address
            for match in matches:
                full_word, abbr_word1, abbr_word2, abbr_word3 = match
                if len(full_word) > len(abbr_word1):
                    cleaned_address = cleaned_address.replace(
                        abbr_word1, full_word)
                if len(full_word) > len(abbr_word2):
                    cleaned_address = cleaned_address.replace(
                        abbr_word2, full_word)
                if len(full_word) > len(abbr_word3):
                    cleaned_address = cleaned_address.replace(
                        abbr_word3, full_word)
        else:
            cleaned_address = address
        print("After_Clean_dup: ", cleaned_address)
        return cleaned_address

    def deduplicate_address_halves(self, addr_str):
        addr_str = addr_str.strip()
        length = len(addr_str)
        # Check duplicate halves by sliding window of words
        words = addr_str.split()
        n = len(words)
        for i in range(1, n // 2 + 1):
            if words[0:i] == words[i:2*i]:
                return " ".join(words[0:i]) + " " + " ".join(words[2*i:])

        # Substring check for exact duplicate text sequences (e.g. part 2 has extra administrative suffixes)
        mid = length // 2
        for i in range(10, mid):
            part1 = addr_str[:i].strip()
            part2 = addr_str[i:].strip()
            if part2.startswith(part1):
                return part2
        return addr_str

    def clean_address(self, address):
        # ลบความซ้ำซ้อนระดับประโยคที่ซ้ำกัน (เช่น ก๊อปปี้แปะที่อยู่ซ้ำกันสองรอบ)
        address = self.deduplicate_address_halves(address)

        keywords = ["เขต", "แขวง", "ต.", "ตำบล",
                    "อ.", "อำเภอ", "จ.", "จังหวัด"]

        # ตรวจสอบว่าสตริงมีคำ "จังหวัด" และ ("เขต" หรือ "แขวง") หรือไม่
        if "จังหวัด" in address and any(keyword in address for keyword in ["เขต", "แขวง"]):
            # ลบคำ "จังหวัด" ออกจากสตริง
            address = address.replace("จังหวัด", "")

        if "\n" in address:
            address = address.replace('\n', " ")

        # เริ่มต้นโดยการแยกคำด้วยช่องว่าง
        parts = address.split()

        # สร้าง list เพื่อเก็บคำที่ไม่ใช่คำย่อ
        cleaned_parts = []

        for part in parts:
            # ตรวจสอบว่าคำนี้เป็นคำย่อหรือไม่
            is_abbreviation = any(part.startswith(keyword) for keyword in ["ต.", "อ.", "จ."])
            if not is_abbreviation:
                cleaned_parts.append(part)

        # นำคำที่ไม่ใช่คำย่อมาเชื่อมกลับเป็นสตริงใหม่
        cleaned_address = ' '.join(cleaned_parts)

        # ลบคำที่มีส่วนที่เหมือนกันออก
        cleaned_address = self.clean_duplicate_parts(cleaned_address)

        # แก้ไขเครื่องหมายช่องว่างที่เหลือหลังการลบคำ
        cleaned_address = cleaned_address.replace("  ", " ")

        return cleaned_address

    # ? WIP note_extractor ยังไม่ค่อยสมบูรณ์ เพราะ case ตัวอย่างมันนานๆเจอที
    def note_extractor(self):
        if self.order_note != 'nan':
            try:
                self.name_match = re.search(r'ชื่อ\s*:?\s*(.*)', self.order_note)
            except:
                self.name_match = re.search(r'บริษัท.*', self.order_note)

            # * ถ้ากลับมาดูไม่ต้องสงสัยว่าแยกทำไม พอเขียนติดกันแล้วมันดูสับสน เลยแยกเฉยๆไม่มีไร (A1/2)
            if "บริษัท" in self.name_match.group():
                self.branch_match = re.search(r'สาขา\s*:?\s*(.*)', self.order_note)
                self.tax_id_match = re.search(r'Tax id\s*:?\s*(.*)', self.order_note)
                self.email_match = re.search(r'email\s*:?\s*(.*)', self.order_note.lower())
                self.tel_match = re.search(r'tel\s*:?\s*,?(.*)', self.order_note.lower())

            self.address_match = re.search(r'ที่อยู่\s*:?\s*(.*)', self.order_note)

            print("try: regexบันทึก: ", self.name_match)
            print("try: ใช้ group กับ regexบันทึก: ", self.name_match.group(1))

            # * เก็บค่าเข้าตัวแปร //#* ถ้ากลับมาดูไม่ต้องสงสัยว่าแยกทำไม พอเขียนติดกันแล้วมันดูสับสน เลยแยกเฉยๆไม่มีไรจะรวมกันก็ได้ (A2/2)
            if "บริษัท" in self.name_match.group():
                self.tax_branch_num.set(
                    self.branch_match.group(1)) if self.branch_match else self.tax_branch_num.set(
                    self.tax_branch_num.get())
                self.tax_num.set(
                    self.tax_id_match.group(1)) if self.tax_id_match else self.tax_num.set(
                    self.tax_num.get())
                self.cus_email.set(
                    self.email_match.group(1)) if self.email_match else self.cus_email.set(
                    self.cus_email.get())
                self.cus_tel.set(self.tel_match.group(1)) if self.tel_match else self.cus_tel.set(self.cus_tel.get())

            self.cus_name.set(self.name_match.group(1)) if self.name_match else self.cus_name.set(self.cus_name.get())
            self.note_extracted_address = self.address_match.group(1) if self.address_match else "-"
            self.cus_address = self.note_extracted_address
        else:
            print("no note to be extracted, note_extractor was not used")

    def translator(self, text):
        # ตรวจสอบว่าชื่อไม่ใช่ภาษาไทย, อังกฤษ, หรือตัวเลข
        #! Patterns เก่าๆ
        #! pattern = re.compile(r'^[a-zA-Z0-9ก-๙\s\W\_]+$')
        #! pattern = re.compile(r'^[a-zA-Z0-9ก-๙\s\W_!@#$%^&*()\-_=+/[\]{}|;:\'",<.>/?]+$') ต่างกันตรงที่มี "     กับไม่มี " ตอน testใน regex101 มันใส่ " แล้ววมันไม่ทำงาน ซึ่งพอลบออกมาก็ใช้งานได้ปกติ

        # * สำหรับแก้ปัญหาข้อที่ 38 // pattern ใหม่
        pattern = re.compile(
            r'^[a-zA-Z0-9ก-๙\s\W_!@#$%^&*()\-_=+/[\]{}|;:\',<.>/?]+$')
        is_usable = bool(re.match(pattern, text))
        if is_usable:
            return text
        else:

            try:
                translator = Translator()
                lang_src = translator.detect(text).lang
                print("Whare are you from: ", lang_src)
                translation = translator.translate(
                    text, src=lang_src, dest='en')
                print("Translated name", translation.text)
                return translation.text
            except:
                print("google ก็แปลให้ไม่ได้เอาชื่อ", text, "ไปแทนนะ")
                return text

    def cus_tel_fixer(self, tel):
        if len(tel) == 10:
            print("เบอร์มือถือ")
            return tel
        elif len(tel) == 9:
            print("ดูก่อนว่าเบอร์บ้านไหม")
            if tel[0] == "0":
                print('โอเคเบอร์บ้าน')
                return tel
            else:
                print("ลืมใส่เลข 0 แหละ")
                print("เติม 0 ให้", "0"+tel)
                return tel
        elif len(tel) > 10:
            if len(tel) == 11:
                tel_no_code = tel[-8:]
                print('เบอร์บ้านแต่ติดรหัสประเทศ')
            elif len(tel) == 12:
                tel_no_code = tel[-9:]
                print('เบอร์มือถือแต่ติดรหัสประเทศ')

            if tel_no_code[0] != 0:
                print("ตัดรหัสประเทศและเพิ่มเลข 0")
                fixed_tel = "0" + str(tel_no_code)
                print('')
                return fixed_tel
            else:
                print('holy shetttttttttttt+')

    def find_branch(self, input):
        """ method นี้ จะ return ไม่ "สำนักงานใหญ่" ก็ เลขสาขาที่เป็นเลข 5 หลัก เท่านั้น """
        # ตัวแปร branch
        input = re.sub(r'\s+', '', str(input))
        branch = str(input).strip()

        pattern = re.compile(r"สำนักงานใหญ่|ใหญ่|สนงใหญ่|สนง\.ใหญ่|สนง|Head|สนญ|^0+$")
        match = pattern.findall(branch)

        # * ตรวจสอบค่าของตัวแปร branch
        if match:
            return 'สำนักงานใหญ่'
          # เมื่อไม่มีสำนักงานใหญ่ ให้ดูว่ามีเลขไหม
        elif re.findall(r'[0-9]+', branch):
            #   เมื่อมีเลขให้ดูว่ามีคำว่าสาขากับเลขหรือไม่
            # print("2nd condition", branch)
            if re.search(r'สาขา.*[0-9]', branch):
                matches = re.search(r'[0-9]+', branch)
                match = matches[0]
                match = match.strip()
                if len(match) == 5 and match[0] == "0":
                    # print("ตัดสาขาออกแล้วมีเลขครบ 5 หลักพอดี", match)
                    return match

                elif len(match) < 5:
                    txt = "{:0>5}"
                    # print("เลขที่ได้หลังตัดสาขาออก มีหลักไม่ครบ เติมหลัก แล้ว Return")
                    # print("ปรับ Format เป็น 5 หลัก")
                    # print("return", txt.format(match))
                    match = txt.format(match)
                    return match

            elif re.search(r'0[0-9]{0,4}', branch) and (branch[0] == "0" and len(branch) <= 5):
                branch = re.search(r'0[0-9]{0,4}', branch)[0]
                # print(branch)
                # print("เลขสาขาตรงๆ ครบบ้างไม่ครบบ้าง")
                if len(branch) == 5:
                    # print("Return แค่ 5 ตัวท้าย")
                    # print("return", branch[-5:])
                    branch = branch[-5:]
                    return branch

                elif len(branch) < 5:
                    txt = "{:0>5}"
                    # print("ปรับผลลัพธ์ ให้ Return เป็น Format 5 หลัก")
                    # print("return", txt.format(branch))
                    return txt.format(branch)
                else:
                    # print("บิดเบี้ยว", branch)
                    # print("return สำนักงานใหญ่")
                    return "สำนักงานใหญ่"
            else:
                # print("not match any subcondition in the 2nd condition")
                # print("return สำนักงานใหญ่")
                return "สำนักงานใหญ่"

        else:
            # print("ไม่มีบอกสำนักงาน")
            # print("return ค่า สำนักงานใหญ่ แล้วกัน")
            return "สำนักงานใหญ่"

    def branch_to_branch_type(self, branch):
        if 'สำนักงานใหญ่' in branch:
            return 'สำนักงานใหญ่'
        else:
            return ''

    def cus_name_simplifyer(self, name):
        if name:
            self.cus_name.set(self.translator(re.sub(r'\s{2,}', " ", name.strip().replace('\u200b', ''))))

            # *  ตัดพวก non-ASCII values // ref https://stackoverflow.com/questions/20889996/how-do-i-remove-all-non-ascii-characters-with-regex-and-notepad
            self.cus_name.set(re.sub(r'[^\x00-\x25\x27-\x7F\wA-Zก-๙|/]+', '', self.cus_name.get().strip()))

            # * ปรับคำบอกประเภทการจดทะเบียนของใบกำกับ
            # print("name.get()ก่อนทำการ format", self.cus_name.get())
            self.cus_name.set(self.tax_name_formatter(self.cus_name.get()))
            # print("name.get()หลังจากทำการ format", self.cus_name.get())
        else:
            # print("Customer Name is empty")
            pass

    def order_search(self, order, on_complete):
        try:
            self._order_search_internal(order, on_complete)
        except Exception as e:
            logger.error(f"Error in order_search: {e}")
            traceback.print_exc()
            self.update_log("🛑 Error: ข้อมูลในไฟล์ Excel ไม่ครบถ้วน (มีคอลัมน์/ข้อมูลไม่มีค่า)")
            self.root.after(0, lambda: messagebox.showerror(
                "ข้อมูลไม่ครบถ้วน",
                "มีค่าใน Import File ไม่ครบ หรือรูปแบบข้อมูลไม่ถูกต้อง"
            ))
            if on_complete is not None:
                on_complete.set()
            if hasattr(self, 'operation_thread') and self.operation_thread is not None:
                self.operation_thread.set()

    def _order_search_internal(self, order,  on_complete):
        self.on_complete = on_complete
        self.on_complete.clear()
        print(f"order: {order} - order_search  ทำงาน, is_order_search_set: {self.order_Search_thread.is_set()}")
        self.reset_all_display()
        self.order = order.strip()
        is_laz_len_not_correct = self.marketplace_target.get() == 'LAZADA' and len(self.order) != 16
        is_shopee_len_not_correct = self.marketplace_target.get() == 'SHOPEE' and len(self.order) != 14
        if is_shopee_len_not_correct or is_laz_len_not_correct:
            self.on_complete.set()
            self.operation_thread.set()
            raise ValueError("The Order length is not correct")
        self.cus_order.set(self.order)
        # # * Memory management - ตรวจสอบและจัดการ memory ก่อนเริ่มงาน
        # if hasattr(self, 'bot') and hasattr(self.bot, 'pre_operation_memory_cleanup'):
        #     self.bot.pre_operation_memory_cleanup("search_order")

        differential_col_data = [
            'เลขอ้างอิง SKU (SKU Reference No.)',
            'ชื่อสินค้า',
            'ราคาขาย',
            'จำนวน',
            'ราคาขายสุทธิ',
            'ส่วนลดจาก Shopee',
            'ชื่อตัวเลือก',
        ]
        non_differential_col_data = [
            'หมายเลขคำสั่งซื้อ',
            'สถานะการสั่งซื้อ',
            'โค้ดส่วนลดชำระโดยผู้ขาย',
            'ค่าจัดส่งที่ชำระโดยผู้ซื้อ',
            'ประเภทใบกำกับภาษี',
            'ชื่อ',
            'ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป',
            'แขวง/ตำบล',
            'เขต/อำเภอ.1',
            'จังหวัด.1',
            'รหัสไปรษณีย์.1',
            'หมายเลขประจำตัวผู้เสียภาษี',
            'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี',
            'อีเมลสำหรับรับใบกำกับภาษี',
            'ชื่อผู้ใช้ (ผู้ซื้อ)',
            'จำนวนเงินทั้งหมด',
            'วันที่ทำการสั่งซื้อ',
            'โค้ดส่วนลดชำระโดย Shopee (เช่น โค้ดจากโปรแกรม ร้านโค้ดคุ้ม, โค้ดส่วนลด Shopee, โค้ดส่วนลด Shopee Mall)',
            'รายละเอียดที่อยู่',
            'ประเภทสาขา',
            'รหัสประจำสาขา',
            'หมายเหตุจากผู้ซื้อ',
            'บันทึก',
            'ชื่อผู้รับ',
            'หมายเลขโทรศัพท์'
        ]

        if self.order != "":

            print("self.order err?: ", self.order, type(self.order))

            if getattr(self, 'data_frame', None) is None or self.data_frame.empty:
                print("Error: data_frame is missing or empty. Please load an Excel file.")
                self.update_log("Error: ไม่พบข้อมูลตาราง กรุณาเลือกไฟล์ Excel และรอโหลดข้อมูลก่อนค้นหาออเดอร์")

            if not self.data_frame[(self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order)].empty:
                # ? self.filter_data จะเป็นการทำComparisionให้เรียบร้อยแล้วคืน DataFrame ที่กรองแล้วทันที --------------------ไวกว่า
                self.filter_data = self.data_frame[(self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order)]
                # ? self.target_row เป็น การหา เอาคอล "หมายเลขคำสั่งซื้อ" ทั้งหมดมาตรวจแล้วคืนค่าเป็น Boolean เท่านั้น ---------ช้ากว่า
                self.target_row = self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order
                self.cus_masked_name = self.data_frame[self.target_row]['ชื่อผู้รับ'].iloc[0]
                self.cus_masked_tel = self.data_frame[self.target_row]['หมายเลขโทรศัพท์'].iloc[0]
                self.order_status = self.data_frame[self.target_row]['สถานะการสั่งซื้อ'].iloc[0]

                # *  ของมีอะไรบ้าง dtypeหลังใช้ .to_dict('records') จะเป็น list of dict ฉันั้น self.items = [{}, {}, ...]
                raw_items = self.data_frame[differential_col_data][self.target_row].to_dict('records')
                # * ตัดช่องว่าง
                for row in raw_items:
                    row['เลขอ้างอิง SKU (SKU Reference No.)'] = row['เลขอ้างอิง SKU (SKU Reference No.)'].replace(
                        ' ', '')

                # Group items by SKU and Option (if they are the same, combine them)
                grouped = {}
                for row in raw_items:
                    sku = row['เลขอ้างอิง SKU (SKU Reference No.)']
                    option = str(row['ชื่อตัวเลือก'])
                    
                    key = (sku, option)
                    if key not in grouped:
                        grouped[key] = row.copy()
                    else:
                        grouped[key]['จำนวน'] = int(grouped[key]['จำนวน']) + int(row['จำนวน'])
                        grouped[key]['ราคาขายสุทธิ'] = float(grouped[key]['ราคาขายสุทธิ']) + float(row['ราคาขายสุทธิ'])
                        grouped[key]['ส่วนลดจาก Shopee'] = float(grouped[key]['ส่วนลดจาก Shopee']) + float(row['ส่วนลดจาก Shopee'])
                
                self.items = list(grouped.values())

                self.nondistortedData = self.data_frame[self.target_row][non_differential_col_data].iloc[0].to_dict()
                print('self.nondistortedData', self.nondistortedData)
                self.update_log(f"สินค้าที่มี")

                for row in self.items:
                    print("ตัวเลือก", str(row['ชื่อตัวเลือก']))
                    option = ""
                    if str(row['ชื่อตัวเลือก']) != "nan":
                        option = str(row['ชื่อตัวเลือก'])
                    self.update_log(
                        f"SKU: {str(row['เลขอ้างอิง SKU (SKU Reference No.)'])} ชื่อสินค้า: {option} {str(row['ชื่อสินค้า'])} ")
                    self.update_log(
                        f"ราคาขาย: {float(row['ราคาขาย']):,.2f} จำนวน: {int(row['จำนวน'])} ราคาขายสุทธิ: {float(row['ราคาขายสุทธิ']):,.2f} ส่วนลดจาก Shopee: {float(row['ส่วนลดจาก Shopee']):,.2f}")

                # * update list รายการสินค้า ช่องที่เลียนแบบ mimic list item like an orange theme app ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////
                with self.bot.driver_lock:
                    self.order_display_manager.create_data_rows(self.items)
                    pass

                # * ชื่อที่ต้องออกใบกำกับ
                try:
                    # * ต้องใช้ translator เพราะ ในระบบ รับได้แค่ ภาษา "ไทย" กับ "อังกฤษเท่านั้น" ใช่แล้วฉันเคยเจอ เกาหลี ญี่ปุ่น แม้แต่ อิโมจิก็เคยเจอมาแล้ว พวกนี้ web ที่รับ input รับภาษาเหล่านี้ไม่ได้เลย
                    self.cus_name.set(self.translator(
                        re.sub(
                            r'\s{2,}', " ", self.nondistortedData['ชื่อ'].strip().replace(
                                '\u200b', ''))))
                except:
                    # * ถ้าชื่อมันว่างมันจะ strip()
                    self.cus_name.set(
                        re.sub(
                            r"[\(\)]", "", self.nondistortedData['ชื่อผู้ใช้ (ผู้ซื้อ)'] + " " + self.cus_masked_name +
                            " " + self.cus_masked_tel))

                self.cus_name_simplifyer(self.cus_name.get())

                # * ประเภทใบกำกับภาษี
                # * เราดูว่าขอใบกำกับหรือไม่ จากที่ว่า 1)มีเลขผู้เสียภาษี 2)มี branch_type
                # * เลือก Column และ row ที่เฉพาะเจาะจง มาแสดงผล โดยการใช้ ['ชื่อคอลั่ม'].iloc[0]
                self.branch_type = str(self.nondistortedData['ประเภทสาขา'])
                print("self.branch_type: ", self.branch_type, type(self.branch_type), len(self.branch_type))
                print("รหัสประจำสาขา= ", self.data_frame[self.target_row]['รหัสประจำสาขา'].iloc[0])
                branch = self.find_branch(str(self.nondistortedData['รหัสประจำสาขา']))
                self.tax_branch_num.set(branch)

                print("self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'] กลายเป็น boolจริงเหรอ",
                      self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'])
                print("self.nondistortedData['หมายเลขประจำตัวผู้เสียภาษี'] พัง")
                print(bool(pd.isna(self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0])))
                print(pd.isna(self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0]))
                print(pd.isna(self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี']))
                print("raw data from DF: ", self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0])
                print("type checking: ", type(self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0]))

                # * ถ้า col ['หมายเลขประจำตัวผู้เสียภาษี'] ไม่ใช่ nan จะเก็บค่าลงใน tax_num_only
                if self.marketplace_target.get() == 'SHOPEE':
                    if not pd.isna(self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0]):
                        tax_num_only = re.sub(r'\D', '', str(self.nondistortedData['หมายเลขประจำตัวผู้เสียภาษี']))
                    else:
                        tax_num_only = "ไม่มีเลข"

                elif self.marketplace_target.get() == 'LAZADA':
                    if self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0] != "":
                        tax_num_only = re.sub(r'\D', '', str(self.nondistortedData['หมายเลขประจำตัวผู้เสียภาษี']))
                    else:
                        tax_num_only = "ไม่มีเลข"

                # ถ้าเลขใบกำกับเป็น nan หรือ tax_num_only ไม่มีค่า
                if tax_num_only == "ไม่มีเลข":
                    self.is_tax_required.set(False)
                    self.cus_tax_status.set("ไม่ขอใบกำกับ")
                    self.root.after(0, lambda: self.display_is_tax.configure(
                        fg_color="#6ec7ff", text_color="#000", font=("Chiller", 10, "normal")))
                    self.tax_num.set("")
                elif tax_num_only != "ไม่มีเลข" and len(tax_num_only) != 13:
                    if len(tax_num_only) > 13:
                        self.is_tax_required.set(False)
                        self.cus_tax_status.set("ขอ//เลขเกิน")
                    elif len(tax_num_only) < 13:
                        self.is_tax_required.set(False)
                        self.cus_tax_status.set("ขอ//เลขไม่ครบ")

                    self.root.after(0, lambda: self.display_is_tax.configure(
                        fg_color="#8502d1", text_color="#FFF", font=("Chiller", 10, "normal")))
                    self.tax_num.set(tax_num_only)

                else:
                    if "สำนักงานใหญ่" in self.branch_type:
                        self.is_tax_required.set(True)
                        self.cus_tax_status.set("ขอใบกำกับ สนงใหญ่")
                        self.root.after(0, lambda: self.display_is_tax.configure(
                            fg_color="#ff0000",
                            text_color="#FFF",
                            font=("Chiller", 10, "bold")
                        ))
                        self.tax_num.set(tax_num_only)
                    elif self.branch_type == "สาขาย่อย" and (not pd.isna(self.data_frame[self.target_row]['รหัสประจำสาขา'].iloc[0])):
                        self.is_tax_required.set(True)
                        self.cus_tax_status.set(f"ใบกำกับ สาขา{branch}")
                        self.root.after(0, lambda: self.display_is_tax.configure(fg_color="#ff0055", text_color="#FFF",
                                                                                 font=("Chiller", 10, "bold")))
                        self.tax_num.set(tax_num_only)
                    else:
                        self.is_tax_required.set(True)
                        self.cus_tax_status.set("ไม่ขอแต่มีเลข")
                        self.root.after(0, lambda: self.display_is_tax.configure(fg_color="#ff9e36", text_color="#FFF",
                                                                                 font=("Chiller", 12, "bold")))
                        self.tax_num.set(tax_num_only)

                if self.is_tax_required.get() == True and len(tax_num_only) == 13:
                    pass

                # * ส่วนสำหรับการแสดงผล UI ------------------------------------------------------
                # self.address = self.filter_data.iat[0, 59]
                self.address = self.nondistortedData['รายละเอียดที่อยู่']
                self.cus_remark: str = str(self.nondistortedData['หมายเหตุจากผู้ซื้อ'])
                self.order_note: str = str(self.nondistortedData['บันทึก'])
                self.cus_email.set(str(self.nondistortedData['อีเมลสำหรับรับใบกำกับภาษี']))

                print("ตรวจหมายเหตุ: ", self.cus_remark)
                print("ตรวจบันทึก: ", self.order_note, "type: ", type(self.order_note))

                # * ดึงบันทึกลูกค้า SHOPEE
                if self.marketplace_target.get() == 'SHOPEE':
                    try:
                        self.note_extractor()
                    except Exception as err:
                        print("Cannot Extract Note: ", err)
                    # self.cus_name.set()
                    # self.cus_name_simplifyer(self.name_match.group())

                    # กรองอักษรพิเศษสำหรับลูกค้า Shopee ปกติ (ไม่ขอใบกำกับภาษี)
                    if not self.is_tax_required.get():
                        cleaned_name = re.sub(r'[^\x20-\x7E\u0e00-\u0e7f]+', '', self.cus_name.get())
                        cleaned_name = re.sub(r'\s{2,}', " ", cleaned_name.strip())
                        self.cus_name.set(cleaned_name)
                elif self.marketplace_target.get() == 'LAZADA':
                    pass

                # * เอาที่อยู่มาโชว์ ใน UI
                # ? แบบที่1 แบ่ง Channel
                # if self.marketplace_target.get() == "SHOPEE":
                #     self.cleaned_address = f"""{self.get_pure_address(self.clean_address(self.address))} {self.nondistortedData['แขวง/ตำบล']} {
                #     self.nondistortedData['เขต/อำเภอ.1']} {self.nondistortedData['จังหวัด.1']} {self.nondistortedData['รหัสไปรษณีย์.1']}"""
                # else:
                #     self.cleaned_address = f"""{self.get_pure_address(self.clean_address(self.address))}"""

                # ? แบบที่2 ไม่แบ่ง Channel
                if self.marketplace_target.get() == 'LAZADA':
                    # ตรวจสอบและเติมตำบลเฉพาะออเดอร์ที่ยังไม่มี (Lazy & On-Demand)
                    current_subdist = str(self.nondistortedData.get('แขวง/ตำบล', '')).strip()
                    if not current_subdist or current_subdist.lower() == 'nan':
                        order_num_str = str(self.order).strip()
                        cached_subdist = self.subdistrict_cache.get(order_num_str)
                        if cached_subdist:
                            print(f"Subdistrict for order {self.order} found in cache: {cached_subdist}")
                            self.nondistortedData['แขวง/ตำบล'] = cached_subdist
                            self.data_frame.loc[self.target_row, 'แขวง/ตำบล'] = cached_subdist
                        else:
                            print(f"Subdistrict for order {self.order} is missing. Filling...")
                            if not hasattr(self, 'address_df') or self.address_df is None:
                                try:
                                    address_data_path = os.path.join(
                                        os.path.dirname(__file__),
                                        'tables', 'Addresscleaner_TambonData.xlsx')
                                    self.address_df = pd.read_excel(address_data_path, dtype=str)
                                    print("Lazy-loaded TambonData successfully.")
                                except Exception as e:
                                    print(f"Error loading TambonData: {e}")
                                    self.address_df = pd.DataFrame()

                            filled_subdist = self._fill_missing_subdistrict(self.nondistortedData, self.address_df)
                            if filled_subdist:
                                print(f"Computed subdistrict for order {self.order}: {filled_subdist}")
                                self.nondistortedData['แขวง/ตำบล'] = filled_subdist
                                self.data_frame.loc[self.target_row, 'แขวง/ตำบล'] = filled_subdist
                                self.subdistrict_cache[order_num_str] = filled_subdist
                                # บันทึกความเปลี่ยนแปลงลงในไฟล์ cache (output_test.xlsx)
                                try:
                                    excel_file_path = "output_test.xlsx"
                                    self.data_frame.to_excel(excel_file_path, index=False, na_rep="", engine="openpyxl")
                                    print(f"Saved updated dataframe with filled subdistrict to {excel_file_path}")
                                except Exception as write_err:
                                    print(f"Warning: Could not save updated dataframe to excel: {write_err}")

                    self.cleaned_address = f"""{self.get_pure_address(self.clean_address(self.address))} {self.nondistortedData['แขวง/ตำบล']} {
                        self.nondistortedData['เขต/อำเภอ.1']} {self.nondistortedData['จังหวัด.1']} {self.nondistortedData['รหัสไปรษณีย์.1']}"""

                    if "กรุงเทพ" in self.cleaned_address:
                        self.cleaned_address = self.cleaned_address.replace("จังหวัด", '')
                    self.search_result = {
                        "status": self.order_status,
                        "is_tax": self.is_tax_required.get(),
                        "address": self.cleaned_address,
                        "details": self.nondistortedData,
                        "items": self.items
                    }

                if self.marketplace_target.get() == 'SHOPEE':
                    self.cleaned_address = ""
                    # * ถ้าขอใบกำกับค่อยใส่ ถ้าไม่ ก็ "" ไป
                    if self.is_tax_required.get():
                        self.cleaned_address = f"""{
                            self.get_pure_address(self.clean_address(self.address))}  {
                            self.nondistortedData['แขวง/ตำบล']}  {
                            self.nondistortedData['เขต/อำเภอ.1']}  {
                            self.nondistortedData['จังหวัด.1']}  {
                            self.nondistortedData['รหัสไปรษณีย์.1']} """

                    if "กรุงเทพ" in self.cleaned_address:
                        self.cleaned_address = self.cleaned_address.replace("จังหวัด", '')
                    self.search_result = {
                        "status": self.order_status,
                        "is_tax": self.is_tax_required.get(),
                        "address": self.cleaned_address,
                        "details": self.nondistortedData,
                        "items": self.items,
                    }

                # * สร้างสูตรสำหรับสร้าง input gui
                print("มีไอเทมไรบ้าง", self.search_result['items'])
                self.input_formula = []
                for item in self.search_result['items']:
                    amount = int(item['จำนวน'])
                    sku = str(item['เลขอ้างอิง SKU (SKU Reference No.)'])
                    result = {'sku': sku, 'qty': amount}
                    self.input_formula.append(result)
                    print("จำนวน", int(item['จำนวน']), type(int(item['จำนวน'])))
                print("สูตรสร้าง input", self.input_formula)
                for item_idx, item in enumerate(self.input_formula):
                    print("รายการที่ ", item_idx+1, item['sku'])
                    for item_idx in range(item['qty']):
                        print("สร้างinputอันที่ ", item_idx+1)

                self.cus_account_name.set(re.sub(r'[^\x00-\x25\x27-\x7F\wA-Zก-๙|/]+',
                                          '', self.nondistortedData['ชื่อผู้ใช้ (ผู้ซื้อ)']))
                self.cus_account_name.set(self.cus_account_name.get().strip())
                print("self.cus_account_name: ", self.cus_account_name.get())

                # * update display text ใน gui
                # * เลือกว่าจะใช้ที่อยู่ แบบรายcol หรือ แบบสำเร็จ ไปอัพเดทและแสดงผลที่อยู่ใน gui โดยอัพเดท the gui ด้วย method update_gui_address
                # * การจะเลือกรายcol ได้ต้องชัวร์ว่า col แขวง/ตำบลต้องไม่ใช่ค่าว่าง หรือต้องไม่ Return เป็น "nan"
                try:
                    if not str(self.nondistortedData['แขวง/ตำบล']) == "nan":
                        print("แขวง/ตำบล ไม่เท่ากับ nan: ", self.nondistortedData['แขวง/ตำบล'])
                        # * Lazada กับ shopee มันแสดงผล address ไม่เหมือนกันเพราะ ตาราง Excel ที่มันให้มา
                        if self.marketplace_target.get() == "LAZADA":
                            self.update_gui(
                                re.sub(
                                    r'\s{2,}', " ", f"""{self.address}  {self.nondistortedData['แขวง/ตำบล']}
                                    {self.nondistortedData['เขต/อำเภอ.1']}  {self.nondistortedData['จังหวัด.1']}
                                    {self.nondistortedData['รหัสไปรษณีย์.1']} """.replace('\u200b', '')).strip(),
                                self.display_cus_address)
                        else:
                            print("update gui address else")
                            self.update_gui(re.sub(r'\s{2,}', " ", self.cleaned_address.replace(
                                '\u200b', '')).strip(), self.display_cus_address)
                    else:
                        print("ถ้ามี nan")
                        self.update_gui(re.sub(
                            r'\s{2,}', " ", self.nondistortedData
                            ['ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป'].strip().replace('\u200b', '')),
                            self.display_cus_address)

                except Exception as err:
                    print("Cannot Update Address", err)
                    self.update_gui('-', self.display_cus_address)

                self.update_gui_remark()
                self.update_gui_note()

                # * เก็บค่ารายละเอียดที่อยู่
                if self.is_tax_required.get():
                    self.cus_province.set(self.nondistortedData['จังหวัด.1'].strip())
                    self.cus_district.set(self.nondistortedData['เขต/อำเภอ.1'].strip())
                if self.cus_sub_district != "":
                    self.cus_sub_district.set(self.nondistortedData['แขวง/ตำบล'])
                else:
                    self.cus_sub_district.set('')
                #! wip lazada ไม่รู้จะมีลูกเล่นไรไหม แต่คิดว่าน่าจะ add ไม่ติด เพราะอาจะขาด column นี้ ใน dataframe
                try:
                    self.cus_postcode.set(self.nondistortedData['รหัสไปรษณีย์.1'])
                except:
                    self.cus_postcode.set('')
                print("self.nondistortedData['หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี']: ",
                      self.nondistortedData['หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี'])
                print("self.nondistortedData['หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี'] bool?: ",
                      pd.isna(self.nondistortedData['หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี']))

                if not str(self.nondistortedData['หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี']) == "nan":
                    print("มีเบอร์โทร")
                    tel_for_set = self.cus_tel_fixer(self.nondistortedData['หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี'])
                    self.cus_tel.set(tel_for_set)
                else:
                    print("ไม่มีเบอร์โทร")
                    self.cus_tel.set("1")

                self.cus_ship_cost.set(self.nondistortedData['ค่าจัดส่งที่ชำระโดยผู้ซื้อ'])
                self.cus_seller_voucher.set(abs(float(self.nondistortedData['โค้ดส่วนลดชำระโดยผู้ขาย'])))
                self.cus_purchase_time.set(self.nondistortedData['วันที่ทำการสั่งซื้อ'])

                self.net_prices_list = []
                for item in self.items:
                    net_price = item['ราคาขายสุทธิ'] + item['ส่วนลดจาก Shopee']
                    self.net_prices_list.append(net_price)

                self.sum_price = sum(self.net_prices_list)
                self.show_products(self.items)
                print("จำนวนเงิน", self.f(self.nondistortedData['จำนวนเงินทั้งหมด']))
                print(
                    'สินค้ารวมค่าส่ง: ', self.f(
                        self.nondistortedData['จำนวนเงินทั้งหมด'] + float(self.cus_ship_cost.get())))
                self.update_log(f"เวลาที่สั่ง: {self.cus_purchase_time.get()}")
                self.update_log(f"ค่าขนส่ง: {self.f(self.cus_ship_cost.get())}")
                self.update_log(
                    f"ราคาที่ต้องยิงทั้งหมด+ค่าส่ง: {self.f(float(self.sum_price) + float(self.cus_ship_cost.get()))}")

                self.update_log(f" ")
                self.update_log(f"-↓↓↓↓↓↓-หน้าสุดท้าย-↓↓↓↓↓↓-")
                self.update_log(f"seller voucher: -{self.f(self.cus_seller_voucher.get())}")

                # * จากปัญหาข้อที่ 37 // การอัพเดท LOG เนื่องจาก LAZ กับ Shopee มีเงื่อนไข การใส่ค่าขนส่งในการออกบิลไม่เหมือนกัน SHOPEE ใส่หมด แต่ LAZ ใส่เป็นบาง ORDER ขึ้นอยู่กับว่า ลูกค้า จะ inbox มาขอให้ใส่หรือไม่
                if self.marketplace_target.get() == "SHOPEE":
                    self.update_log(
                        f"สินค้ารวมค่าส่ง หักseller: {self.f((self.sum_price+self.cus_ship_cost.get())-self.cus_seller_voucher.get())}")
                elif self.marketplace_target.get() == "LAZADA":
                    self.update_log(f"สินค้าเฉยๆ หักseller: {self.f((self.sum_price)-self.cus_seller_voucher.get())}")
                    self.update_log(f"---------------------------------")
                    self.update_log(
                        f"สินค้ารวมค่าส่ง หักseller: {self.f((self.sum_price+self.cus_ship_cost.get())-self.cus_seller_voucher.get())}")

            else:
                print(f"Order ที่ยิงมา {self.cus_order.get()} ไม่สามารถหาใน Export File ได้")
                print("อาจเกิดจาก เลข Order ที่กรอกเข้ามาผิดพลาด หรือไม่ก็ ไฟล์เก่าเกินไป")
                print("ถ้าไฟล์เก่าแนะนำให้ไป Export File มาใหม่ จาก Link ที่ให้ด้านล่าง")
                print("https://seller.shopee.co.th/portal/sale/shipment?type=toship")

                self.update_log(f"Order ที่ยิงมา {self.cus_order.get()} ไม่สามารถหาใน Export File ได้")
                self.update_log("อาจเกิดจาก เลข Order ที่กรอกเข้ามาผิดพลาด หรือถ้า Order ไม่ผิด ก็แปลว่าไฟล์ไม่มีข้อมูล")
                self.update_log("ถ้าไฟล์เก่าแนะนำให้ไป Export File มาใหม่ จาก Link ที่ให้ด้านล่าง")
                self.update_log("https://seller.shopee.co.th/portal/sale/shipment?type=toship")
                # self.reset_all_display()
                logger.info(f"Order: {self.search_query} Not found in the shopee's Export File")

        else:
            self.reset_all_display()

        print("ก่อน seller voucher popup")
        if self.is_seller_voucher_popup.get() and self.cus_seller_voucher.get() > 0:
            txtsize = self.cal_adjusted_font_size(1920, 24)
            self.root.after(0, lambda t=txtsize, m=self.cus_seller_voucher.get(): self.POP_UP.show(
                "Seller Voucher Notification",
                f"มี Seller Voucher {m} บาท",
                "alert",
                txtsize=t
            ))
            print("seller voucher popup ต้องเด้งละ")

        self.on_complete.set()
        print(f"order: {order} - order_search  ทำงาน, is_order_search_set: {self.order_Search_thread.is_set()}")
        print("order_search ทำงานจบ")

    def cal_adjusted_font_size(self, base_width, base_font_size):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.base_width = base_width
        self.base_font_size = base_font_size

        scale_factor = screen_width / self.base_width
        adjusted_font_size = int(self.base_font_size * scale_factor)
        return adjusted_font_size

    def cus_name_cleaner(self, name, account_name=":"):
        is_found = re.search(r"\[.*\]|\(.*\)|\{.*\}", name)
        name = re.sub(r"\[.*\]|\(.*\)|\{.*\}", '', name).strip() if is_found else name.strip()
        # เช็คว่าถ้ามองชื่อเป็น list มันจะแบ่งได้กี่ส่วน
        name += " "+account_name if len(name.split()) == 1 else ""
        print("name:", name)
        return name

    def tax_name_formatter(self, name: str) -> str:
        # ลบ zero-width space และ trim
        name_edited = name.replace('\u200b', '').strip()

        # --- ลบ text ทีไม่ต้องการก่อนเริ่มจัด format ---
        name_edited = re.sub(r'เลขประจำตัวผู้เสียภาษี\s*[\d-]*', '', name_edited).strip()
        name_edited = re.sub(r'TAX\s*ID:?\s*[\d-]*', '', name_edited, flags=re.IGNORECASE).strip()

        # --- patterns สำหรับสำนักงานใหญ่ ---
        head_office_patterns = [
            r'\(\s*สำนักงานใหญ่\s*\)?', r'สำนักงานใหญ่',
            r'\(\s*สํานักงานใหญ่\s*\)?', r'สํานักงานใหญ่',
            r'\(\s*สนญ\.?\s*\)?', r'สนญ\.?',
            r'\(\s*00000\s*\)?',
        ]

        # --- patterns สำหรับสาขา ---
        branch_patterns = [
            r'\(\s*สาขา[^)]*\)?',
            r'สาขา\s*\d+'
        ]

        # --- แยก suffix สาขา/สำนักงานใหญ่ออกมาก่อน ---
        extracted_suffix = ""
        for pattern in head_office_patterns + branch_patterns:
            match = re.search(pattern, name_edited)
            if match:
                extracted_suffix = match.group()
                # แปลง สนญ. เป็น สำนักงานใหญ่ ให้เป็นมาตรฐานเดียวกัน
                if re.match(r'\(?สนญ\.?\)?|\(?00000\)?', extracted_suffix):
                    extracted_suffix = "สำนักงานใหญ่"
                name_edited = re.sub(pattern, '', name_edited).strip()
                break  # ดึงมาแค่อันเดียวพอ

        # --- ลบคำซ้ำกันแบบเป๊ะๆ (Duplicate substrings) ที่มักเกิดจากระบบเบิ้ลชื่อ ---
        # เช่น "ร้านเอ็มแอนด์เอ...ร้านเอ็มแอนด์เอ..." -> ให้เหลือคำเดียว
        # จำกัดความยาวอย่างน้อย 8 ตัวอักษร เพื่อป้องกันการหั่นชื่อจริงๆ เช่น "ชาบูชาบู" (4 อักษร)
        name_edited = re.sub(r'(.{8,}?)\s*\1+', r'\1', name_edited)

        # --- ปรับรูปแบบประเภทบริษัท ---

        # 1. กรณี บมจ. (บริษัท มหาชน จำกัด)
        if name_edited.startswith(("บมจ", "บริษัท มหาชน จำกัด", "บมจ.")) or "มหาชน" in name_edited:
            # ลบคำนำหน้า/คำลงท้ายเดิมออกก่อนเพื่อจัด format ใหม่
            name_edited = re.sub(r'^(บมจ\.?|บริษัท มหาชน จำกัด|บริษัท|บ\.)', '', name_edited).strip()
            name_edited = re.sub(r'(จำกัด\(มหาชน\)|มหาชน จำกัด|จำกัด)$', '', name_edited).strip()

            if not name_edited.startswith("บริษัท"):
                name_edited = f"บริษัท {name_edited}"
            if not name_edited.endswith("จำกัด (มหาชน)"):
                name_edited = f"{name_edited} จำกัด (มหาชน)"

        # 2. กรณี หจก.
        elif name_edited.startswith(("หจก", "ห้างหุ้นส่วนจำกัด", "ห.")):
            name_edited = re.sub(r'^(หจก\.?|ห้างหุ้นส่วนจำกัด|ห\.)', '', name_edited).strip()
            if not name_edited.startswith("ห้างหุ้นส่วนจำกัด"):
                name_edited = f"ห้างหุ้นส่วนจำกัด {name_edited}"

        # 3. กรณี บจก. (บริษัท จำกัด)
        elif name_edited.startswith(("บจก", "บริษัท", "บ.", "บจ.")):
            name_edited = re.sub(r'^(บจก\.?|บริษัท|บ\.|จก\.|บจ\.?)', '', name_edited).strip()
            # ลบคำว่า "จำกัด" ท้ายประโยคเดิมออกก่อน
            name_edited = re.sub(r'จำกัด\s*[A-Za-z0-9]*$', '', name_edited).strip()

            if not name_edited.startswith("บริษัท"):
                name_edited = f"บริษัท {name_edited}"
            if not name_edited.endswith("จำกัด"):
                name_edited = f"{name_edited} จำกัด"

        # --- ต่อ suffix คืน ---
        if extracted_suffix:
            # ถ้ามีวงเล็บเปิดแต่ไม่มีวงเล็บปิด ให้เติมวงเล็บปิดให้ถูกต้อง
            if extracted_suffix.startswith('(') and not extracted_suffix.endswith(')'):
                extracted_suffix = extracted_suffix + ')'
            name_edited = f"{name_edited} {extracted_suffix}"

        # --- ลบช่องว่างเกิน ---
        name_edited = re.sub(r"\s{2,}", ' ', name_edited).strip()

        return name_edited

    def on_thread_done(self):
        print("on_thread_done start")
        self.get_tabs_stat = self.get_tabs_thread.is_alive()
        self.search_thread_stat = self.search_thread.is_alive()
        print("ก่อนifเช็คตัวรัน tab", self.get_tabs_stat)
        print("ก่อนifเช็คตัวรัน excel", self.search_thread_stat)
        if self.get_tabs_thread.is_alive():
            print("self.get_tabs_thread.is_alive()")
            # self.operation_thread.set()
            self.get_tabs_thread.join()

        print("Thread is done คงเหงาแย่")

        self.get_tabs_stat = self.get_tabs_thread.is_alive()
        self.search_thread_stat = self.search_thread.is_alive()
        print("หลังifเช็คตัวรัน tab", self.get_tabs_stat)
        print("หลังifเช็คตัวรัน excel", self.search_thread_stat)

        print("Thread is done")
        if self.get_tabs_stat == False and self.search_thread_stat == False:
            self.display_bot_status_label.configure(
                text=f"Bot Status: ˶ᵔ ᵕ ᵔ˶ จบการทำงาน", fg_color="#d9f2ff", text_color="#000")
            print("Bot Status: ˶ᵔ ᵕ ᵔ˶ จบการทำงาน (ตัวบน)")

        if self.get_tabs_thread.is_alive():
            print("มีthreadใหม่มาต่อ")
            self.display_bot_status_label.configure(
                text=f"Bot Status: ᕦʕ •ᴥ•ʔᕤ กำลังทำงาน", fg_color="#cf1313", text_color="#ffffff")

    def check_threads(self, longer_thread_cycle, shorter_thread_cycle, callback=None):
        # * Check if these are still the current threads
        is_current = (longer_thread_cycle == self.longer_thread_cycle and shorter_thread_cycle ==
                      self.shorter_thread_cycle)

        if is_current:
            # print(
            #     f"check_threads: is_current={is_current}, shorter={shorter_thread_cycle.is_alive()}, longer={longer_thread_cycle.is_alive()}")
            pass

        # * เป็นการเช็ค thread ไปเรื่อยๆจนกว่า thread ทั้งคู่จะดับไป หาก Thread ใด Thread หนึ่ง ทำงานอยู่ ให้เช็คตัวเองอีกรอบ ภายในเวลา 100 millisec
        if (shorter_thread_cycle.is_alive() or longer_thread_cycle.is_alive()):
            # * after(เวลาmillisec, callbackfunction)
            self.root.after(750, lambda: self.check_threads(shorter_thread_cycle, longer_thread_cycle, callback))

            # * เอาไว้แสดงสถานะของ bot gui ว่าทำงานอยู่หรือไม่
            if is_current:
                if self.is_bot_browser_busy.get() == True:
                    self.display_bot_status_label.configure(
                        text=f"Bot Status: ᕦʕ •ᴥ•ʔᕤ กำลังทำงาน", fg_color="#cf1313", text_color="#ffffff")
                elif self.is_bot_browser_busy.get() == False:
                    self.display_bot_status_label.configure(
                        text=f"Bot Status: Your Turn", fg_color="#21ff29", text_color="#000")
        else:
            # * เมื่อ Thread ทั้งสองไม่ alive จะทำการรวม thread ย่อย เข้ากับ thread หลัก แล้วเรียกใช้ callback ถ้าหากมี callback มาด้วยน่ะนะ callbackนี้จะรับ operation_startเข้ามาให้ทำงานอีกรอบ
            print("check_threads: Threads dead. Joining...")
            shorter_thread_cycle.join()
            longer_thread_cycle.join()
            print("check_threads: Joined.")

            if is_current:
                print("check_threads: Updating GUI to Done")
                self.display_bot_status_label.configure(
                    text=f"Bot Status: ˶ᵔ ᵕ ᵔ˶ จบการทำงาน", fg_color="#d9f2ff", text_color="#000")
                print("Bot Status: ˶ᵔ ᵕ ᵔ˶ จบการทำงาน (ตัวล่าง)")
            else:
                print("check_threads: Not current, skipping GUI update")
                self.display_bot_status_label.configure(
                    text=f"Bot Status: ˶ᵔ ᵕ ᵔ˶ จบการทำงาน", fg_color="#d9f2ff", text_color="#000")

            if callback:
                callback()

    def search_order(self, accel_order=None, callback=None):
        self.is_bot_running.set(False)
        # self.is_bot_running.set(True)
        self.autofinal = False

        # * ลบ result products list เก่า
        # * len(self.mimic_column_headers) เพราะ เวลาเพิ่มลด header มันจะได้ไม่พัง ตอนแรก header แม่งหาย งงเลย
        for widget in self.mp_products_list_frame.winfo_children()[len(self.mimic_column_headers):]:
            widget.destroy()

        if self.is_accel_mode.get():
            self.search_query = accel_order
        else:
            self.search_query = self.entered_order.get()

        print("search() ทำงานและได้ผลลัพธ์: ", self.search_query)

        self.entered_order.set("")
        if self.search_query != "":
            self.report_log.configure(state=NORMAL)
            self.report_log.delete("1.0", "end")
            # self.report_log.insert(END, self.search_query + "\n")
            self.report_log.configure(state=DISABLED)
        else:
            self.report_log.configure(state=NORMAL)
            self.report_log.delete("1.0", "end")
            self.report_log.configure(state=DISABLED)

        # * Stop previous threads if they exist
        if hasattr(self, 'operation_thread') and self.operation_thread is not None:
            print("Stopping previous threads...")
            self.operation_thread.set()
            self.stop_operation()
            # รอให้ old threads ตายจริงก่อนสร้าง thread ใหม่ (แก้ race condition บน self.operation_thread)
            if hasattr(self, 'longer_thread_cycle') and self.longer_thread_cycle.is_alive():
                print("Waiting for longer_thread_cycle to die...")
                self.longer_thread_cycle.join(timeout=5)
                if self.longer_thread_cycle.is_alive():
                    print("⚠️ longer_thread_cycle didn't die in time!")
            if hasattr(self, 'shorter_thread_cycle') and self.shorter_thread_cycle.is_alive():
                print("Waiting for shorter_thread_cycle to die...")
                self.shorter_thread_cycle.join(timeout=5)
                if self.shorter_thread_cycle.is_alive():
                    print("⚠️ shorter_thread_cycle didn't die in time!")

        self.operation_thread = threading.Event()
        self.order_Search_thread = threading.Event()
        # print("self.operation_thread.set()2157: ")
        # self.operation_thread.set()
        self.order_Search_thread.set()
        self.operation_thread.clear()

        # * สร้าง Thread
        self.bot.get_tabs()
        self.longer_thread_cycle = threading.Thread(
            target=lambda: self.bot.operation_task_thread(self.operation_thread))
        self.shorter_thread_cycle = threading.Thread(target=lambda: self.order_search(
            self.search_query, self.order_Search_thread))
        print("Thread Name: ", self.longer_thread_cycle.name)

        # * สั่ง Thread ให้เริ่มทำงาน
        self.is_data_ready = False
        self.shorter_thread_cycle.start()
        self.longer_thread_cycle.start()

        # * ตรวจสอบว่า Thread ทั้งสองยังทำงานอยู่หรือไม่
        self.check_threads(self.longer_thread_cycle, self.shorter_thread_cycle, callback)
        self.display_bot_status_label.configure(
            text=f"Bot Status: ᕦʕ •ᴥ•ʔᕤ กำลังทำงาน", fg_color="#cf1313", text_color="#ffffff")

    def stop_operation(self):
        # self.is_accel_mode_activated.set(False) ตัวแปรนี้การการhandleที่ทำให้บัค แต่มันทำงานดี
        self.is_bot_running.set(False)
        print("self.operation_thread.set()2182: ")
        self.operation_thread.set()
        logger.info(f"""Order: {self.order} stop operation
                    """)

    def stop_accel_mode(self):
        self.is_accel_mode_activated.set(False)
        self.stop_operation()
        self.update_log("🛑 หยุดการทำงาน Accel Mode ทั้งหมดเรียบร้อยแล้ว")

    # * ส่งไปแปะไว้ที่ order_display_manager.py
    def auto_add_product_threaded(self, skus, qty, **kwargs):
        """
        Wrapper method สำหรับเรียก auto_add_product ใน thread แยก
        เพื่อไม่ให้รบกวน threading cycle หลัก (longer_thread_cycle และ shorter_thread_cycle)

        Parameters:
            skus: list of SKU codes
            qty: quantity
            **kwargs: additional arguments to pass to auto_add_product
        """

        try:
            self.bot.driver.switch_to.window(self.bot.merged_dict['SMCO :: เปิดการขาย'])
        except:
            self.bot.get_tabs()
            self.bot.driver.switch_to.window(self.bot.merged_dict['SMCO :: เปิดการขาย'])

        def run_auto_add():
            try:
                self.bot.AutoAddProduct.auto_add_product(skus, qty, **kwargs)
            except Exception as e:
                print(f"Error in auto_add_product_threaded: {e}")

        # สร้าง daemon thread เพื่อไม่ให้รบกวน main threads
        auto_add_thread = threading.Thread(target=run_auto_add, daemon=True, name="AutoAddProductThread")
        auto_add_thread.start()
        print(f"Started auto_add_product in separate thread: {auto_add_thread.name}")

    #! ตัวกากกว่า sku_formater,  sku_formaterเทพกว่า
    def correct_sku_pattern(self, text: str) -> list:
        result = []
        text = text.replace(" ", "")
        elements = text.split("+")

        for element in elements:
            prefix, code = element.split("-")
            code = code.zfill(6)
            result.append(prefix + "-" + code)

        return result

    def open_subwindow(self):
        self.data_source_selector.create_subwindow()

    #! สร้างไว้ไมวะ
    # def get_dataframe(self):
    #     print("เรียกหา dataframe")


# สำหรับเลือกที่มาของแหล่งข้อมูล
class DataSourceSelector:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.create_subwindow()

    def create_subwindow(self):
        self.subwindow = CTkToplevel(self.parent)
        self.subwindow.transient(self.parent)
        self.subwindow.geometry("250x75+650+400")
        self.subwindow.title("Data Source")
        self.subwindow.grab_set()
        self.subwindow.resizable(False, False)

        self.api_btn = CTkButton(self.subwindow, text="API", command=self.select_api)
        self.api_btn.pack(side='left', expand=TRUE, fill="both")
        self.excel_btn = CTkButton(self.subwindow, text="Excel", command=self.select_excel)
        self.excel_btn.pack(side='left', expand=TRUE, fill="both")

        self.subwindow.protocol("WM_DELETE_WINDOW", self.on_close)

    def select_api(self):
        self.app.result = "API"
        print("Select API")
        self.subwindow.destroy()

    def select_excel(self):
        self.app.result = "Excel"
        print("Select Excel")
        self.app.table_location = filedialog.askopenfilename(title="Select Shopee order toship file")
        self.app.display_location_result.configure(text=f"{self.app.table_location.split('/')[-1]}")
        # target should come before getting dataframe
        self.app.marketplace_target.set(self.app.define_marketplace())
        result = self.app.marketplace_target.get()
        self.app.entry_frame.configure(fg_color=f'{self.app.bg_by_market_place[str(result)]}')
        self.app.marketplace_label.configure(
            fg_color=f'{self.app.bg_by_market_place[str(result)]}',
            width=1000 if self.app.marketplace_target.get() == "" else 0
        )

        if result == "LAZADA":
            self.app.label_lazada_tax_name.grid(row=1, column=4, padx=(5, 0), pady=(2, 2), sticky='ew')
            self.app.display_lazada_tax_name.grid(row=1, column=5, padx=(1, 0), sticky='ew')
        else:
            self.app.label_lazada_tax_name.grid_remove()
            self.app.display_lazada_tax_name.grid_remove()

        self.app.get_data_frame()
        print("Table Location:", self.app.table_location)
        self.subwindow.destroy()
        self.app.update_log("เพิ่มไฟล์แล้ว")

    def on_close(self):
        self.app.marketplace_target.set("")
        self.app.marketplace_label.configure(width=70 if self.app.marketplace_target.get() == "" else 0)
        self.subwindow.destroy()


class PopUp:
    """
    Class PopUp use for create a reusable pop-up for THE BOT GUI
    Parameters:
        - parent (obj): class parent obj. อยากให้ใครอุ้มส่งไปให้คนนั้น

    Usage:
        # สร้างครั้งเดียวตอน init
        popup = PopUp(parent_window)

        # เรียกใช้ได้เรื่อยๆ
        popup.show(title="Error", message="Something wrong", mode="alert")
        popup.show(title="Confirm", message="Submit data?", mode="form")
    """

    _instances = {}  # เก็บ instance แยกตาม parent

    def __new__(cls, parent):
        # Singleton pattern - ถ้ามี parent นี้แล้ว ให้ return instance เดิม
        if parent not in cls._instances:
            cls._instances[parent] = super().__new__(cls)
        return cls._instances[parent]

    def __init__(self, parent):
        # ป้องกัน re-init ถ้า instance มีอยู่แล้ว
        if hasattr(self, '_initialized'):
            return

        self.parent = parent
        self.mode_opt = {"form": "Submit", "alert": "Close"}
        self.subwindow = None
        self._initialized = True

        # ผูก cleanup กับการปิด parent window
        self.parent.bind("<Destroy>", self._cleanup, add="+")

    def show(self, title, message, mode="alert", **kwargs):
        """
        แสดง popup ใหม่ หรือ update popup ที่มีอยู่

        Parameters:
            - title (str): Title name of the pop-up
            - message (str): For display a message in the pop-up
            - mode (str): "form" สำหรับ submit, "alert" สำหรับ alert
            - **kwargs: txtsize สำหรับขนาดตัวอักษร
        """
        # ถ้ามี popup เปิดอยู่แล้ว ให้ destroy ก่อน
        if self.subwindow and self.subwindow.winfo_exists():
            self.subwindow.destroy()

        self.mode = mode
        self.title = title
        self.message = message
        self._create_subwindow(**kwargs)

    def hide(self):
        """ซ่อน popup (ไม่ destroy)"""
        if self.subwindow and self.subwindow.winfo_exists():
            self.subwindow.withdraw()

    def delete(self):
        """ปิด popup"""
        if self.subwindow and self.subwindow.winfo_exists():
            self.subwindow.destroy()
            self.subwindow = None

    def _create_subwindow(self, **kwargs):
        """สร้าง popup window (internal method)"""
        self.subwindow = CTkToplevel(self.parent)
        self.subwindow.transient(self.parent)
        self.subwindow.geometry("400x140+650+400")
        self.subwindow.title(f"{self.title}")
        self.subwindow.grab_set()
        self.subwindow.resizable(True, False)

        # สร้างเฟรม
        self.subwin_frame = CTkFrame(self.subwindow)
        self.subwin_frame.pack(padx=10, pady=10, fill='x', expand=True)

        # สร้าง Textbox widget
        self.fontSize = kwargs.get('txtsize') or 9
        self.id_label = CTkTextbox(self.subwin_frame, font=("bazooka", self.fontSize))
        self.id_label.insert(END, f'{self.message}')
        self.id_label.pack(fill=BOTH, expand=True)
        self.id_label.configure(state=DISABLED)

        # Submit/Close Button
        self.submit_btn = CTkButton(
            self.subwin_frame,
            text=f"{self.mode_opt[self.mode]}",
            command=self.delete
        )
        self.submit_btn.pack(fill='x', expand=True)

        # ยก widget นี้ขึ้นมาหน้าสุด
        self.subwindow.attributes('-topmost', 1)
        self.subwindow.lift()

    def _cleanup(self, event=None):
        """ทำลาย instance เมื่อ parent window ถูกปิด"""
        if self.subwindow and self.subwindow.winfo_exists():
            self.subwindow.destroy()

        # ลบ instance ออกจาก dict
        if self.parent in PopUp._instances:
            del PopUp._instances[self.parent]

    @classmethod
    def destroy_all(cls):
        """ทำลาย popup ทั้งหมด (ใช้ตอน cleanup แอพ)"""
        for instance in list(cls._instances.values()):
            if instance.subwindow and instance.subwindow.winfo_exists():
                instance.subwindow.destroy()
        cls._instances.clear()

# * class สำหรับรับ ID PASS


class UserAccount:
    def __init__(self, parent, app={}):
        self.parent = parent
        self.app = app
        self.create_subwindow("Loginปลอม")
        self.POP_UP = app.POP_UP

    def create_subwindow(self, title: str = "Untitled"):
        self.subwindow = CTkToplevel(self.parent)
        self.subwindow.transient(self.parent)
        self.subwindow.geometry("250x180+650+400")
        self.subwindow.title(title)
        self.subwindow.grab_set()
        self.subwindow.resizable(False, False)

        # * Event Enter
        self.subwindow.bind("<Return>", lambda event=None: self.submit_btn.invoke())
        self.subwindow.bind("<Key>", _onKeyRelease)

        # * สร้างเฟรม
        self.subwin_frame = CTkFrame(self.subwindow)
        self.subwin_frame.pack(padx=10, pady=10, fill='x', expand=True)

        # * สร้าง widget
        self.id_label = CTkLabel(self.subwin_frame, text="SMCO ID", font=CTkFont(family="bazooka", size=9), anchor="w")
        self.id_label.pack(fill='x', expand=True)
        # self.id_input = Entry(self.subwin_frame, textvariable=self.app.user_id,
        #                       validate="key", validatecommand=(self.app.validate_input_variable, '%P'))
        self.id_input = CTkEntry(
            self.subwin_frame,
            textvariable=self.app.user_id
        )
        self.id_input.pack(fill='x', expand=True)
        self.id_input.focus()

        self.pass_label = CTkLabel(self.subwin_frame, text="SMCO Password",
                                   font=CTkFont(family="bazooka", size=9), anchor="w")
        self.pass_label.pack(fill='x', expand=True)
        # self.pass_input = Entry(
        #     self.subwin_frame, textvariable=self.app.user_pw, show="*", validate="key", validatecommand=(self.app.validate_input_variable, '%P'))
        self.pass_input = CTkEntry(
            self.subwin_frame,
            textvariable=self.app.user_pw,
            show="*"
        )
        self.pass_input.pack(fill='x', expand=True)

        # * checkBox
        self.chk_bx_show_pw = CTkCheckBox(
            self.subwin_frame, text="Show Pass", font=('bazooka', 9),
            command=self.show_and_hide)
        self.chk_bx_show_pw.pack()

        # * Submit Button
        self.submit_btn = CTkButton(self.subwin_frame, text="Submit", command=self.update_btn)
        self.submit_btn.pack(fill='x', expand=True)

    def login(self):
        # * ใช้ SmcoApiClient แทน global session โดยตรง
        origin = 'http://192.168.0.11:8080'
        try:
            result = self.app.smco_api.login(
                origin=origin,
                user_id=self.app.user_id.get(),
                password=self.app.user_pw.get(),
            )
            print("ได้ result ไรมา: ", result)
            # * ตรวจสอบ response จากการ login
            if result['status'] == "MORE_BRANCH":
                print("Logged in")
                return True
            else:
                print("Incorrect username or password")
                self.login_alert = self.POP_UP.show(
                    "Login Fail!!",
                    "พาสเวิร์ดผิดหรือป่าว~\nถ้าถูกแล้วก็อาจจะเป็นที่ SMCO\nลองเช็ค SMCO ดู",
                    "alert",
                )
                return False
        except requests.exceptions.RequestException as e:
            print(f"Login request failed: {e}")
            self.login_alert = self.POP_UP.show(
                "Login Error",
                f"ติดต่อ SMCO ไม่ได้\n{e}",
                "alert",
            )
            return False

    def update_btn(self):
        user_input = self.app.user_pw.get()
        user_input_th_included = bool(re.search(r'[\u0E00-\u0E7F]', user_input))
        if self.app.user_id.get() and self.app.user_pw.get():
            if user_input_th_included:
                self.login_alert = self.POP_UP.show(
                    title="Login Fail!!", message="พาสเวิร์ดมีภาษาไทย ไม่สามารถ login ได้", mode="alert")
            # is_closable = self.login()
            else:
                is_closable = True
                print("ปิดได้ไหม ", is_closable)
                if is_closable:
                    self.display_btn_txt = f"""Logged in !! ID : {self.app.user_id.get()}"""
                    self.app.display_acc_btn.configure(text=self.display_btn_txt,
                                                       font=CTkFont(family="bazooka", size=9))
                    self.subwindow.destroy()

                else:
                    print("ไม่ติด")
                    self.display_btn_txt = "Login"
                    # self.subwindow.destroy()
                    # return self.display_btn_txt

                if self.app.user_id.get() in self.app.dev_account:
                    print("Accel mode approachable")
                    if self.app.accel_mode_checkbox.winfo_ismapped():
                        pass
                    else:
                        self.app.accel_mode_checkbox.grid(row=0, column=0, padx=5)
                else:
                    print("Normal mode", self.app.user_id.get() in self.app.dev_account)
                    self.app.accel_mode_checkbox.grid_remove()
                    print(self.app.user_id.get())
                    # print(self.app.dev_account)

                self.app.account_manager.set_last_username(self.app.user_id.get())

                return self.display_btn_txt

    def show_and_hide(self):
        # สำหรับ CTkEntry ใช้ .configure(show="") หรือ .configure(show="*")
        if self.chk_bx_show_pw.get():  # ถ้า checkbox ถูกติ๊ก
            self.pass_input.configure(show="")  # แสดงรหัสผ่าน
        else:
            self.pass_input.configure(show="*")  # ซ่อนรหัสผ่าน


class StopEvent:
    """Wrapper ที่ proxy threading.Event แต่เพิ่ม generation check
    เมื่อ thread ใหม่เริ่ม (generation เปลี่ยน), is_set() จะ return True อัตโนมัติ
    ทำให้ old thread หยุดโดยไม่ต้องแก้ 40+ จุดที่เช็ค self.operation_thread.is_set()"""

    def __init__(self, event, bot, generation):
        self._event = event
        self._bot = bot  # เอาไว้ดู ว่า generation ปัจจุบันของ bot เป็นเท่าไหร่
        self._generation = generation  # gen ของ thread นี้

    def is_set(self):
        return self._event.is_set() or self._bot._active_generation != self._generation

    def set(self):
        self._event.set()

    def clear(self):
        self._event.clear()


class Bot_POS:
    def __init__(self, parent, app):
        # super().__init__(parent)
        self.parent = parent
        self.app = app
        self.wsh = comclt.Dispatch("WScript.Shell")
        self.driver_lock = threading.Lock()
        self.auto_add_product_stop_flag = threading.Event()  # Flag สำหรับควบคุมการหยุด auto_add_product แยกจาก operation_thread
        self.browser = BrowserManager(app=self.app, bot_instance=self, logger_instance=logger)
        self.channel_options = {
            'shp_itcitymobile_master': 'SHP ITCITY Mobile',
            'itcity': 'SHOPEE',
            'shp_wisegadget_master': 'SHOPEE Wise Gadget',
            'lenovoofficialstorebyitcity': 'SHP ITCITY LENOVO',
        }
        self.sumatra_path = ""

        # * Initialize Sumatra PDF cache file path
        self.sumatra_cache_file = os.path.join(os.path.dirname(__file__), "sumatra_pdf_cache.txt")
        # * Load cached Sumatra PDF path or search for it
        if not self.load_sumatra_cache():
            # If cache is empty or invalid, search for Sumatra PDF
            self.find_sumatra_from_registry()

        # ? BaseUrlFinder() มันทำงานโดยหาค่าจาก env แต่ตอนออก exe ยังใช้ไม่ได้ ตอนนี้เลยตั้งค่า origin ตายตัวไปก่อน
        # self.origin = BaseUrlFinder().check_available_ip()
        # self.origin = "http://115.31.167.19:9099"
        self.origin = "http://115.31.167.28:8080"
        self.smco_handler = SMCOFormHandler(self, logger)  # * ใส่ logger ไปด้วยเพราะมันมี setting
        self.AutoAddProduct = AutoAddProduct(self.driver, self.wait50, self.app, self)
        self.ProductManager = ProductManager(self.driver, self.wait50, self.app, self)

        # Network capture is now managed by BrowserManager

        # * Load address translation data from Excel
        try:
            import pandas as pd

            # ใช้ absolute path โดยอิงจาก directory ของไฟล์นี้
            current_dir = os.path.dirname(os.path.abspath(__file__))
            excel_path = os.path.join(current_dir, 'tables', 'Addresscleaner_TambonData.xlsx')
            self.address_data = pd.read_excel(excel_path, dtype=str)
            print(f"Loaded address data from: {excel_path}")
            print(f"Total rows: {len(self.address_data)}")
        except Exception as e:
            print(f"Warning: Could not load address data: {e}")
            self.address_data = None

        # / Memory management tracking
        self.operation_count = 0
        self.memory_check_interval = 10  # ตรวจสอบทุก 10 operations (ปรับได้ตามต้องการ)
        self.max_memory_mb = 70  # ถ้า tab ใช้เกิน 800MB ให้ reset (ปรับได้ 500-1500MB)
        self.is_memory_checking = False

        # คำอธิบาย:
        # - memory_check_interval: ยิ่งน้อยยิ่งตรวจบ่อย แต่จะช้าลง (แนะนำ 5-20)
        # - max_memory_mb: ขึ้นกับสเปคคอม และความต้องการ (แนะนำ 500-1000MB)

        # / utils variables
        self.is_random_subdistrict_used = False  # ใช้ใน address cleaner
        # * share SmcoApiClient instance จาก MyApp เพื่อใช้ session เดียวกัน
        self.smco_api = self.app.smco_api

    @property
    def driver(self):
        return self.browser.driver

    @property
    def wait5(self):
        return self.browser.wait5

    @property
    def wait50(self):
        return self.browser.wait50

    @property
    def merged_dict(self):
        return self.browser.merged_dict

    @property
    def network_capture(self):
        return self.browser.network_capture

    def setup_chrome(self, *args, **kwargs):
        return self.browser.setup_chrome(*args, **kwargs)

    def reconnect_driver(self, *args, **kwargs):
        return self.browser.reconnect_driver(*args, **kwargs)

    def is_driver_alive(self, *args, **kwargs):
        return self.browser.is_driver_alive(*args, **kwargs)

    def get_tabs(self, *args, **kwargs):
        return self.browser.get_tabs(*args, **kwargs)

    def retry_on_stale_element(self, *args, **kwargs):
        return self.browser.retry_on_stale_element(*args, **kwargs)

    def manage_browser_memory(self, *args, **kwargs):
        return self.browser.manage_browser_memory(*args, **kwargs)

    def check_for_refresh_popup(self, element):
        """
        Helper to check if a popup element's text contains the word 'refresh' (case-insensitive).
        If it does, raises RefreshRequiredException.
        """
        try:
            text = element.text
            if "refresh" in text.lower():
                logger.warning(f"Detect 'refresh' popup: '{text}'. Raising RefreshRequiredException...")
                self.click_popup_confirm_button(timeout=2)
                raise RefreshRequiredException("ตรวจพบการ Login ซ้ำซ้อน")
        except StaleElementReferenceException:
            try:
                el = self.driver.find_element(By.XPATH, "//div[@class = 'swal2-content']")
                text = el.text
                if "refresh" in text.lower():
                    logger.warning(f"Detect 'refresh' popup: '{text}'. Raising RefreshRequiredException...")
                    self.click_popup_confirm_button(timeout=2)
                    raise RefreshRequiredException("ตรวจพบการ Login ซ้ำซ้อน")
            except Exception:
                pass
        except RefreshRequiredException:
            raise
        except Exception as e:
            print(f"Error checking refresh popup: {e}")

    def wait_and_get_popup(self, timeout=5):
        """
        Wait for a popup with xpath //div[@class = 'swal2-content'] to be visible.
        If it contains 'refresh', handles it and raises RefreshRequiredException.
        Otherwise, returns the popup element.
        """
        try:
            popup = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.XPATH, "//div[@class = 'swal2-content']"))
            )
            time.sleep(0.3)
            self.check_for_refresh_popup(popup)
            return popup
        except RefreshRequiredException:
            raise
        except Exception:
            return None

    def click_popup_confirm_button(self, timeout=5):
        """
        Attempts to click the popup confirm button (OK / ตกลง) using selenium's click
        or falls back to javascript executor if needed.
        """
        try:
            btn = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]")))
            btn.click()
            print("Successfully clicked swal confirm button via Selenium")
            return True
        except Exception:
            try:
                # Fallback to javascript click if standard click fails
                btn = self.driver.find_element(
                    By.XPATH, "//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]")
                self.driver.execute_script("arguments[0].click();", btn)
                print("Successfully clicked swal confirm button via JS fallback")
                return True
            except Exception:
                pass
        return False

    def refresh_all_smco_tabs(self):
        """
        Refreshes all tabs where the title indicates it's an SMCO page.
        """
        try:
            original_handle = self.driver.current_window_handle
        except Exception:
            original_handle = None

        try:
            self.get_tabs()
        except Exception as e:
            logger.error(f"Failed to refresh tabs list: {e}")

        # Iterate over all window handles and refresh if title contains "SMCO"
        for handle in self.driver.window_handles:
            try:
                self.driver.switch_to.window(handle)
                title = self.driver.title
                if "SMCO" in title:
                    logger.info(f"Refreshing SMCO tab: '{title}' (handle: {handle})")
                    self.driver.refresh()
                    time.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to refresh tab (handle: {handle}): {e}")

        if original_handle and original_handle in self.driver.window_handles:
            try:
                self.driver.switch_to.window(original_handle)
            except Exception:
                pass

    def cp_sonic_blow_process(self, item_no: int, cp_no: str):
        """
        เลือก coupon สำหรับสินค้าที่ระบุ รองรับการเลือกหลาย coupon ในครั้งเดียว
        รองรับทั้งการระบุเป็นลำดับตัวเลข (Index เช่น "1 5") หรือระบุเป็นชื่อ/รหัสคูปองโดยตรง (เช่น "CP2605220025, DC2605220017")

        Args:
            item_no (int): เลขลำดับสินค้า (1-indexed)
            cp_no (str): ลำดับคูปอง (ตัวเลข) หรือ รหัสคูปอง (ข้อความ) แยกด้วยเว้นวรรคหรือเครื่องหมายจุลภาค
        """
        item_idx = int(item_no) - 1

        # * แยกข้อมูล cp_no ให้รองรับทั้งแบบ Space, Comma หรือผสมกัน (เช่น "1 5", "CP2605220025, DC2605220017")
        raw_tokens = []
        for part in str(cp_no).split(','):
            for token in part.split():
                if token.strip():
                    raw_tokens.append(token.strip())

        # * เก็บชื่อ coupon ที่เลือกแต่ละตัว
        cp_target_names = []

        cp_name_loc = "//div[@ng-show='posbook.data.cnFormPaymentId===undefined']//span[@class='text-primary price-sku-h1 ng-binding']"
        selected_cp_btn_loc = f'''
                            //div[@ng-show='posbook.data.cnFormPaymentId===undefined']//button[@ng-click='selectCoupon(oms.currentProductByProcessCoupon,pmt)']
                            '''
        cp_name_elements_list = self.driver.find_elements(By.XPATH, cp_name_loc)
        print("ตอนแรกเปนงี้", self.app.items[item_idx]['เลขอ้างอิง SKU (SKU Reference No.)'])
        self.demonic_ordered_items_list = self.app.correct_sku_pattern(
            self.app.items[item_idx]['เลขอ้างอิง SKU (SKU Reference No.)'])
        print(f"self.demonic_ordered_items_list: {self.demonic_ordered_items_list}")
        print(f"raw_tokens: {raw_tokens}")

        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
        # *>  element location
        # * >> ปุ่มคูปองด้านนอก ที่ตำแหน่ง [-4] จะเป็นตัวแยก element หรือ ตัวบอกตำแหน่งของ element ว่าเป็นลำดับที่เท่าไหร่ อย่างตัวอย่างนี้เป็น อันที่1
        # cp_btn_xpath = '/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[1]/a' # ! >> old fashion way
        # green_agree_btn_xpath = '/html/body/div[2]/div[3]/div[11]/div/div[1]/span/div[2]/button[1]'   # ! >> old fashion way ปุ่มยืนยันสีเขียว
        green_agree_btn_xpath = 'button[ng-click="okCoupon()"]'

        try:
            # * ก่อน SMCOver 6.3.3
            cp_list = self.driver.find_elements(By.XPATH, '/html/body/div[1]/div[2]/div[9]/div/div[2]/div[3]')
        except:
            # * ตั้งแต่ SMCOver 6.3.3
            cp_list = self.driver.find_elements(By.XPATH, '/html/body/div[1]/div[2]/div[9]/div/div[2]/div[2]')

        # * Loop ผ่านแต่ละ item ในรายการสินค้า
        for idx, item in enumerate(self.demonic_ordered_items_list):
            item_position = idx+1
            print("item จาก demonic_ordered_items_list", item)

            # ดึงข้อมูลรายการสินค้าบนหน้าเว็บใหม่ทุกรอบของแต่ละสินค้า เพื่อรองรับความเปลี่ยนแปลงของหน้าเว็บและตำแหน่งที่อาจสลับได้เสมอ!
            try:
                item_texts = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('.col-sm-12.panel.panel-default.ng-scope')).map(el => el.innerText);
                """)
            except Exception as e:
                print("ไม่สามารถดึงข้อมูลรายการสินค้าจากหน้าเว็บได้:", e)
                item_texts = []

            # สร้าง dict mapping ระหว่าง SKU -> Index สำหรับรอบนั้นๆ
            sku_to_index = {}
            for pos_idx, text in enumerate(item_texts):
                if item in text:
                    sku_to_index[item] = pos_idx
                    break

            if item not in sku_to_index:
                print(f"ไม่พบ SKU: {item} ในรายการขายหน้าเว็บ (ข้าม)")
                continue

            target_idx = sku_to_index[item]
            print(f"เจอสินค้า {item} ที่ตำแหน่ง Index: {target_idx}")

            try:
                # ดึงรายการปุ่ม Coupon ล่าสุดสดๆ เสมอเพื่อเลี่ยง Stale Element
                item_list_cp_btn_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, 'div.col-sm-4.nopadding button.btn-coupon.btn.btn-sm')
                if target_idx >= len(item_list_cp_btn_elements):
                    print(f"ดึงปุ่ม coupon ของ {item} ไม่สำเร็จ (index เกินรายการ)")
                    continue

                # * คลิกปุ่ม coupon เพื่อเปิดหน้ารายการ coupon (เปิดครั้งเดียว)
                cp_btn_xpath = item_list_cp_btn_elements[target_idx]
                cp_btn_xpath.click()
                time.sleep(0.1)  # * รอให้หน้า coupon list โหลด

                # * Loop ผ่านแต่ละ coupon token ที่ต้องการเลือก
                for cp_idx, token in enumerate(raw_tokens):
                    print(f"กำลังเลือก coupon: {token} สำหรับ item: {item}")

                    # ค้นหาปุ่มคูปองเป้าหมาย
                    target_btn_idx = -1

                    # ดึงข้อมูลชื่อคูปองและปุ่มบนหน้าจอสดๆ เสมอ
                    cp_name_elements = self.driver.find_elements(By.XPATH, cp_name_loc)
                    cp_btn_elements = self.driver.find_elements(By.XPATH, selected_cp_btn_loc)

                    if not cp_name_elements or not cp_btn_elements:
                        print("ไม่พบรายการคูปองหรือปุ่มคูปองบนหน้าจอ")
                        continue

                    # กรณีที่ 1: token เป็นรหัสคูปอง/ชื่อคูปองโดยตรง (มีตัวอักษรปน เช่น CPxxxx, DCxxxx)
                    if not token.isdigit():
                        for idx3, element in enumerate(cp_name_elements):
                            element_text_cleaned = element.text.replace(" ", "")
                            if token in element_text_cleaned:
                                target_btn_idx = idx3
                                break
                        if target_btn_idx == -1:
                            print(f"ไม่พบคูปองที่มีชื่อ/รหัส: {token} ในรายการ")
                            continue

                    # กรณีที่ 2: token เป็นลำดับตัวเลข (Index เช่น "1", "2")
                    else:
                        original_idx = int(token) - 1

                        # รักษาความสามารถเดิม: ถ้ามี cp_target_name จากรอบก่อน ให้ใช้ชื่อนั้นค้นหาแทนเพื่อกันตำแหน่งสลับ
                        if cp_idx < len(cp_target_names) and cp_target_names[cp_idx] != "":
                            for idx3, element in enumerate(cp_name_elements):
                                element_text_cleaned = element.text.replace(" ", "")
                                if cp_target_names[cp_idx] in element_text_cleaned:
                                    target_btn_idx = idx3
                                    break
                            if target_btn_idx == -1:
                                target_btn_idx = original_idx
                        else:
                            target_btn_idx = original_idx

                    # คลิกเลือกคูปองที่ต้องการ
                    if 0 <= target_btn_idx < len(cp_btn_elements):
                        cp_btn_elements[target_btn_idx].click()
                        time.sleep(0.2)  # * รอให้ UI อัพเดท

                        # ดึงชื่อคูปองล่าสุดอีกรอบในกรณีที่มีการ update เพื่อความปลอดภัย
                        latest_cp_name_elements = self.driver.find_elements(By.XPATH, cp_name_loc)
                        if target_btn_idx < len(latest_cp_name_elements):
                            selected_cp_name = latest_cp_name_elements[target_btn_idx].text.replace(" ", "")
                        else:
                            selected_cp_name = ""

                        # * เก็บหรืออัพเดทชื่อ CP ที่เลือกเพื่อใช้ในสินค้าตัวถัดไป
                        if cp_idx >= len(cp_target_names):
                            cp_target_names.append(selected_cp_name)
                            print(f"cp_target_name[{cp_idx}] now is: {selected_cp_name}")
                        else:
                            cp_target_names[cp_idx] = selected_cp_name
                    else:
                        print(
                            f"ตำแหน่ง Index {target_btn_idx} นอกขอบเขตของรายการปุ่มคูปองที่มีอยู่ ({len(cp_btn_elements)})")

                # * กดยืนยัน (ครั้งเดียวหลังจากเลือกครบทุก coupon แล้ว)
                print(f"click OK ในรอบของ: {item}, เลือก coupon ทั้งหมด: {raw_tokens}")
                self.driver.find_element(By.CSS_SELECTOR, green_agree_btn_xpath).click()

            except Exception as err:
                print("Demonic CP Bot inner Exception Error:", err)
                pass

        # * ล้างค่า cp_target_names เมื่อเสร็จสิ้น
        print(f"เลือก coupon เสร็จสิ้น: {cp_target_names}")

    def cp_bringer(self):
        #! wth is this function for?
        pass

    def find_cp_no_placeholder(self, item_index: int, sku: str, diff) -> str:
        """
        ฟังก์ชัน Placeholder สำหรับหาหมายเลขคูปอง (cp_no) ของ SKU ที่มีส่วนต่างราคา

        Args:
            item_index (int): ลำดับสินค้า (1-indexed)
            sku (str): รหัส SKU อ้างอิง
            diff: จำนวนส่วนต่างราคา (expected - actual) หรือ "NOT_FOUND"

        Returns:
            str: ลำดับ coupon ที่ต้องการเลือก (เช่น "1" หรือ "1 5")
        """
        print(f"[Placeholder] Finding cp_no for SKU: {sku}, diff: {diff}, item_index: {item_index}")
        return "1"

    def find_cp_from_excel(self, sku: str, platform_price: float, purchased_date_str: str) -> dict:
        """
        ค้นหา CP จากไฟล์ CP_data.xlsx (self.app.cp_df) และส่งกลับ dict ข้อมูลคูปอง ปรับเพิ่ม และปรับลด
        """
        if self.app.cp_df is None or self.app.cp_df.empty:
            print("[CP Lookup] No CP data loaded")
            return None

        # 1. Parse purchased date
        try:
            purchased_dt = pd.to_datetime(purchased_date_str)
            if pd.isna(purchased_dt):
                return None
        except Exception as e:
            print(f"[CP Lookup] Date parsing error for '{purchased_date_str}': {e}")
            return None

        # 2. Filter by SKU
        sku_clean = str(sku).strip().upper()  # / แบบย่อ เช่น SP2-1703
        formatted_skus = [s.strip().upper() for s in self.app.correct_sku_pattern(sku)]  # / แบเต็ม SP2-001703

        def sku_match(row_sku):
            row_sku_str = str(row_sku).strip().upper()
            # / เทียบสองแบบเพราะ sku ที่ input มาใน CP_data.xlsx อาจจะเป็นแบบย่อ หรือเต็มก็ได้ //แบบย่อ เช่น SP2-1703 //#/ แบบเต็ม SP2-001703
            return (row_sku_str == sku_clean) or (row_sku_str in formatted_skus)

        sku_mask = self.app.cp_df['sku'].apply(sku_match)
        df_filtered = self.app.cp_df[sku_mask]

        if df_filtered.empty:
            print(f"[CP Lookup] No matching SKU found in CP Data for: {sku}")
            return None

        # 3. Filter by Date Range
        valid_rows = []
        for idx, row in df_filtered.iterrows():
            try:
                start_date = pd.to_datetime(row.get('usage_start_date'))
                end_date = pd.to_datetime(row.get('usage_end_date'))

                # Check date range
                if pd.notna(start_date) and pd.notna(end_date):
                    if start_date.date() <= purchased_dt.date() <= end_date.date():
                        valid_rows.append(row)
                elif pd.notna(start_date):
                    if start_date.date() <= purchased_dt.date():
                        valid_rows.append(row)
                elif pd.notna(end_date):
                    if purchased_dt.date() <= end_date.date():
                        valid_rows.append(row)
                else:
                    valid_rows.append(row)
            except Exception as date_err:
                print(f"[CP Lookup] Row date validation error at index {idx}: {date_err}")

        if not valid_rows:
            print(f"[CP Lookup] SKU {sku} found, but date {purchased_dt.date()} is not within any CP usage range.")
            return None

        df_valid = pd.DataFrame(valid_rows)

        # 4. Filter by Price (sale_price == platform_price)
        price_tolerance = 0.05
        df_price_matched = df_valid[
            (df_valid['sale_price'] - platform_price).abs() <= price_tolerance
        ]

        if df_price_matched.empty:
            print(
                f"[CP Lookup] SKU {sku} and date matched, but no matching sale_price for platform_price={platform_price}. Available prices: {df_valid['sale_price'].tolist()}")
            return None

        # ดึงค่า cp_name, oc_amount, dc_amount จากแถวแรกที่เจอ
        matched_row = df_price_matched.iloc[0]
        cp_name = matched_row.get('cp_name')
        oc_amount = matched_row.get('oc_amount')
        dc_amount = matched_row.get('dc_amount')

        return {
            "cp_name": str(cp_name).strip() if pd.notna(cp_name) else "",
            "oc_amount": str(oc_amount).strip() if pd.notna(oc_amount) else "",
            "dc_amount": str(dc_amount).strip() if pd.notna(dc_amount) else ""
        }

    def process_price_mismatches(self, verification_result: dict) -> None:
        """
        ตรวจสอบความแตกต่างของราคาสินค้าแต่ละ SKU และเรียกใช้คูปองหรือปรับราคาหากมีส่วนต่าง
        ตามขั้นตอนใน cp_adding2.drawio
        """
        price_result = verification_result.get("price", {})

        def is_valid_adjustment(amount_str):
            if not amount_str or str(amount_str).strip() == "" or str(amount_str).strip().upper() == "NONE":
                return False
            tokens = str(amount_str).split()
            for token in tokens:
                clean = token.replace('-', '').replace('+', '').split('.')[0].strip()
                if clean.isdigit() and int(clean) > 0:
                    return True
            return False

        # วนลูปตามรายการสินค้าใน order
        processed_skus = set()
        for i, item in enumerate(self.app.items):
            sku_key = item.get('เลขอ้างอิง SKU (SKU Reference No.)')
            if not sku_key:
                continue
            if sku_key in processed_skus:
                continue
            processed_skus.add(sku_key)

            if sku_key in price_result:
                item_price_info = price_result[sku_key]
                if not item_price_info.get("ok", True):
                    diff_val = item_price_info.get("diff", 0)  # expected - actual
                    expected_price = item_price_info.get("expected", 0)
                    actual_price = item_price_info.get("actual", 0)
                    item_no_1indexed = i + 1
                    purchased_date = self.app.cus_purchase_time.get()

                    if actual_price == "NOT_FOUND":
                        error_msg = f"ไม่มีสินค้าให้ตรวจสอบและปรับราคา สำหรับ SKU: {sku_key} (วันที่: {purchased_date}, ราคาที่ต้องออกบิล: {expected_price})"
                        self.app.update_log(f"❌ {error_msg}")
                        raise ValueError(error_msg)

                    print(
                        f"[Verification] SKU: {sku_key} expected={expected_price}, actual={actual_price}, diff={diff_val}")

                    #/ ดึงข้อมูลแคมเปญจาก Excel เสมอก่อนเพื่อตรวจสอบแนวทางการปรับราคาของสินค้าเซ็ต
                    cp_info = self.find_cp_from_excel(sku_key, expected_price, purchased_date)

                    if not isinstance(diff_val, (int, float)):
                        print(
                            f"[Verification] SKU: {sku_key} price difference is not numeric (diff={diff_val}). Skipping price mismatch adjustment.")
                        continue

                    # กรณีที่ 1: marketplace_item_price > smco_item_price? (diff > 0)
                    if diff_val > 0:
                        # ตรวจสอบว่าใน Excel มีการระบุ oc_amount สำหรับสินค้าเซ็ตเพื่อความถูกต้องหรือไม่
                        if cp_info and is_valid_adjustment(cp_info.get("oc_amount", "")):
                            oc_amount_str = cp_info.get("oc_amount", "")
                            print(
                                f"[Verification] Applying Overcharge (OC) from CP Data: {oc_amount_str} for SKU: {sku_key}")
                            self.app.update_log(f"⚡ ปรับราคาขึ้น (Overcharge) จากข้อมูลแคมเปญ: {oc_amount_str} บาท")
                            self.smco_set_overcharge_product(sku_key, str(oc_amount_str))
                        else:
                            # ปรับตาม diff_val ปกติ (สำหรับสินค้าเดี่ยวปกติ)
                            print(
                                f"[Verification] Marketplace price is higher. Applying Overcharge (OC) for SKU: {sku_key} with amount: {diff_val}")
                            self.app.update_log(
                                f"⚡ ปรับราคาขึ้น (Overcharge) สำหรับ SKU: {sku_key} จำนวน {diff_val} บาท")
                            self.smco_set_overcharge_product(sku_key, str(diff_val))

                    # กรณีที่ 2: marketplace_item_price < smco_item_price? (diff < 0)
                    elif diff_val < 0:
                        print(f"[Verification] Marketplace price is lower. Searching coupon (CP) for SKU: {sku_key}")
                        self.app.update_log(f"🔍 กำลังหาคูปองลดราคาสำหรับ SKU: {sku_key}")

                        if cp_info:
                            cp_name = cp_info.get("cp_name", "")
                            oc_amount_str = cp_info.get("oc_amount", "")
                            dc_amount_str = cp_info.get("dc_amount", "")

                            # 1. แอดคูปอง (ถ้ามีระบุ cp_name)
                            if cp_name and cp_name.upper() != "NONE" and cp_name.strip() != "":
                                print(
                                    f"[Verification] Found matching coupon: {cp_name}. Checking for missing ones...")
                                self.app.update_log(
                                    f"🔍 ตรวจสอบว่าคูปอง: {cp_name} สำหรับ SKU: {sku_key} ถูกเลือกไว้แล้วหรือยัง...")

                                try:
                                    sku_variants = [sku_key]
                                    try:
                                        sku_variants = self.app.correct_sku_pattern(sku_key)
                                    except Exception:
                                        pass

                                    panels = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
                                    target_panel = None
                                    for panel in panels:
                                        panel_text = panel.text
                                        if any(variant in panel_text for variant in sku_variants):
                                            target_panel = panel
                                            break

                                    existing_cps = []
                                    if target_panel:
                                        tooltip_elements = target_panel.find_elements(By.XPATH, ".//a[@data-toggle='tooltip']")
                                        for el in tooltip_elements:
                                            text = el.text or ""
                                            title = el.get_attribute("title") or ""
                                            combined = (text + " " + title).replace(" ", "").upper()
                                            existing_cps.append(combined)

                                    target_tokens = []
                                    for part in str(cp_name).split(','):
                                        for token in part.split():
                                            tok = token.strip().upper()
                                            if tok:
                                                target_tokens.append(tok)

                                    missing_tokens = []
                                    for token in target_tokens:
                                        matched = False
                                        for existing in existing_cps:
                                            if token in existing:
                                                matched = True
                                                break
                                        if not matched:
                                            missing_tokens.append(token)

                                    if not missing_tokens:
                                        self.app.update_log(
                                            f"✨ คูปอง {cp_name} สำหรับ SKU: {sku_key} ถูกเลือกไว้ครบก่อนแล้ว ข้ามการเลือกซ้ำ")
                                    else:
                                        missing_cp_str = " ".join(missing_tokens)
                                        self.app.update_log(
                                            f"✅ คูปองที่ยังไม่ถูกเลือกคือ: {missing_cp_str} กำลังดำเนินการแอดคูปอง...")
                                        self.cp_sonic_blow_process(item_no_1indexed, missing_cp_str)
                                        time.sleep(0.5)
                                except Exception as check_err:
                                    print(f"Error checking and filtering cp/dc tooltips: {check_err}")
                                    # Fallback to applying original cp_name
                                    self.cp_sonic_blow_process(item_no_1indexed, cp_name)
                                    time.sleep(0.5)

                            # 2. ปรับราคาเพิ่ม Overcharge (ถ้ามีระบุ oc_amount)
                            if is_valid_adjustment(oc_amount_str):
                                print(
                                    f"[Verification] Applying Overcharge (OC) from CP Data: {oc_amount_str} for SKU: {sku_key}")
                                self.app.update_log(f"⚡ ปรับราคาขึ้น (Overcharge) จากข้อมูลแคมเปญ: {oc_amount_str} บาท")
                                self.smco_set_overcharge_product(sku_key, str(oc_amount_str))
                                time.sleep(0.5)

                            # 3. ปรับราคาลด Discount (ถ้ามีระบุ dc_amount)
                            if is_valid_adjustment(dc_amount_str):
                                print(
                                    f"[Verification] Applying Discount (DC) from CP Data: {dc_amount_str} for SKU: {sku_key}")
                                self.app.update_log(f"📉 ปรับราคาลด (Discount) จากข้อมูลแคมเปญ: {dc_amount_str} บาท")
                                self.smco_set_discount_product(sku_key, str(dc_amount_str), qty=1)
                                time.sleep(0.5)
                        else:
                            # บันทึกข้อมูล SKU และราคาออกบิลที่ไม่พบ CP ลงไฟล์ CP_data.xlsx
                            self.add_missing_cp_to_excel(sku_key, expected_price)

                            error_msg = f"Order skipped, CP/DC not found for SKU: {sku_key} (วันที่: {purchased_date}, ราคาที่ต้องออกบิล: {expected_price})"
                            self.app.update_log(f"❌ {error_msg}")
                            raise ValueError(error_msg)

    def add_missing_cp_to_excel(self, sku_key: str, expected_price: float):
        """
        บันทึกเฉพาะข้อมูล SKU และ expected_price (sale_price) ลงในไฟล์ CP_data.xlsx (self.app.cp_table_location)
        เพื่อให้ผู้ใช้งานสามารถเข้าไปจัดการเงื่อนไขการปรับราคาต่อในภายหลัง
        """
        try:
            excel_path = getattr(self.app, 'cp_table_location', '')
            if not excel_path or str(excel_path).strip() == "":
                print("[add_missing_cp_to_excel] No cp_table_location set. Skipping.")
                return

            import os
            if not os.path.exists(excel_path):
                print(f"[add_missing_cp_to_excel] File not found: {excel_path}. Skipping.")
                return

            # อ่านข้อมูลเก่า
            try:
                df = pd.read_excel(excel_path)
            except Exception as read_err:
                print(f"[add_missing_cp_to_excel] Error reading excel: {read_err}")
                return

            # สร้างข้อมูลแถวใหม่ (บันทึกเฉพาะ sku และ sale_price ตามความต้องการของผู้ใช้)
            new_row = {
                'sku': sku_key,
                'sale_price': expected_price
            }

            # เพื่อไม่ให้เกิดปัญหากับคอลัมน์อื่นๆ ในไฟล์จริง เราจะแปลงเป็น DataFrame แล้ว concat
            new_df = pd.DataFrame([new_row])
            
            # รักษาโครงสร้างคอลัมน์ของไฟล์ Excel เดิมไว้
            for col in df.columns:
                if col not in new_df.columns:
                    new_df[col] = ""
            
            # เรียงลำดับคอลัมน์ให้ตรงกัน
            new_df = new_df[df.columns]

            # รวมและบันทึก
            df_combined = pd.concat([df, new_df], ignore_index=True)
            df_combined.to_excel(excel_path, index=False)

            self.app.update_log(f"💾 บันทึก SKU: {sku_key} (ราคาเป้าหมาย: {expected_price}) ลงใน CP Data เรียบร้อยแล้ว (เว้นค่าการปรับราคาให้กรอกเพิ่มในภายหลัง)")
            
            # อัปเดต DataFrame ในหน่วยความจำ (self.app.cp_df) เพื่อให้สามารถใช้งานได้ทันที
            if self.app.cp_df is not None:
                if 'usage_start_date' in new_df.columns:
                    new_df['usage_start_date'] = pd.to_datetime(new_df['usage_start_date'], errors='coerce')
                if 'usage_end_date' in new_df.columns:
                    new_df['usage_end_date'] = pd.to_datetime(new_df['usage_end_date'], errors='coerce')
                self.app.cp_df = pd.concat([self.app.cp_df, new_df], ignore_index=True)

        except Exception as err:
            print(f"[add_missing_cp_to_excel] Error appending row: {err}")

    def smco_pos_item_list_srp_bringer(self, sku: str):
        """return srp โดยดึงจากหน้า pos (ฉะนั้นในposต้องมี sku อยู่ก่อนนะ)ตาม sku ที่เราใส่เข้ามาใน fn นี้"""
        srp = 0

        return srp

    def sku_formater(self, sku_input: str):
        """รับ string ที่มี sku หลายๆตัวมา แล้วจัด format ให้ถูกต้อง เช่น sp2-1703  -> SP2-001703 แล้ว return string ที่จัด format แล้วเฉยๆ ต้องไปแยกเป็น list เอง"""
        prog = re.findall(r'[A-Za-z]{2,}[A-Za-z0-9]?-?\d{1,6}', sku_input)
        result = ""
        for item in prog:
            prefix, number = item.split('-')  # แยกส่วนหน้า-หลัง
            uppered_prefix = prefix.upper()  # เปลี่ยน prefix เป็นตัวพิมพ์ใหญ่
            number_padded = number.zfill(6)   # เติมศูนย์จนเลขยาว 6 ตัว
            result += f"{uppered_prefix}-{number_padded} "
        return result.strip()

    def oc_amounts_calculator(self, entered_data):
        result = 0
        entered_data = str(entered_data).replace(',', '')

        if "+" in entered_data:
            entered_data = entered_data.split("+")
            for operand in entered_data:
                result += float(operand.strip())
            return int(result)

        elif "-" in entered_data:
            operands = [float(x.strip()) for x in entered_data.split("-")]
            result = operands[0]  # ตัวแรกเป็นตัวตั้ง
            for operand in operands[1:]:
                result -= operand  # ลบแต่ตัวหลัง
            return int(result)

        try:
            return int(float(entered_data.strip()))
        except ValueError:
            return entered_data

    # / fcuntion overcharge product
    def smco_set_overcharge_product(self, items_user_input: str = None, oc_amounts_input: str = None):
        """อันนี้ based มาจาก smco_set_overcharge_product_v2จาก test_each_py_functions.ipynb แต่ปรับให้มันรับ user_id กับ user_pw มาเอง"""
        print("items_target: ", items_user_input)
        print("oc_amounts_input: ", oc_amounts_input, "Type: ", type(oc_amounts_input))
        if items_user_input is None or oc_amounts_input is None:
            print("เลขลำดับสินค้า หรือ จำนวนเงินที่ต้องการ ยังไม่ถูกกำหนด")
            return

        formatted_items_to_oc: list = self.sku_formater(items_user_input).split(" ")
        oc_amounts_list_prog = str(oc_amounts_input).split()
        oc_amounts_list = [int(self.oc_amounts_calculator(oc_amount)) for oc_amount in oc_amounts_list_prog]
        items_list_element = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')

        for idx, item in enumerate(formatted_items_to_oc):
            print(f"item {idx+1} : {item}")
            oc_amount = oc_amounts_list[0]
            print("before: round:", idx+1, "oc_amount: ", oc_amount)
            if len(oc_amounts_list) > 1:
                oc_amount = oc_amounts_list[idx]
            print("after: round:", idx+1, "oc_amount: ", oc_amount)
            if oc_amount > 0:
                for idx2, div in enumerate(items_list_element):
                    try:
                        is_found = div.text.find(item)
                        li_loc = idx2+1

                        if is_found != -1:
                            print("found at li no: ", li_loc)
                            print("is_found: ", is_found)

                            css_sel_loc = {
                                'product_code': f'.col-sm-12.panel.panel-default.ng-scope:nth-child({li_loc}) div:nth-child(2) span:nth-child(1) a',
                                'srp_btn': f'.col-sm-12.panel.panel-default.ng-scope:nth-child({li_loc}) div.panel-body:nth-child(1) div.row.col-sm-6:nth-child(2) > div:nth-child(1) div:nth-child(1) div a:nth-child(1)'
                            }

                            self.driver.find_element(By.CSS_SELECTOR, css_sel_loc['srp_btn']).click()
                            # todo ถ้าไม่รอตรงนี้ code มันจะรันไปอย่างไว element มันยังไม่ทันขึ้น code รันเสร็จละ
                            time.sleep(0.5)
                            # changePriceInput = self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[1]/input')
                            changePriceInput = self.driver.find_element(By.XPATH, "//input[@ng-keyup='onPistive(oms)']")
                            based_price = self.driver.execute_script(
                                "return angular.element(arguments[0]).val();", changePriceInput)
                            print("based_price extracted from form: ", based_price)
                            new_price = float(based_price.replace(",", "")) + float(oc_amount)
                            print("new_price calculated: ", new_price)
                            self.driver.execute_script(
                                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                                changePriceInput, 0)
                            self.driver.execute_script(
                                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                                changePriceInput, new_price)

                            # / ใส่ พนักงาน
                            user_id_input = self.driver.find_element(
                                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[2]/input')
                            self.js_input_value(user_id_input, self.app.user_id.get())

                            # / ใส่ รหัสพนักงาน
                            user_pw_input = self.driver.find_element(
                                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[3]/input')
                            self.js_input_value(user_pw_input, self.app.user_pw.get())

                            # / ใส่ หมายเหตุ
                            note_textarea = self.driver.find_element(
                                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[5]/div/textarea')
                            self.js_input_value(note_textarea, "Online")

                            # / กด บันทึก button สีเขียว
                            green_submit_btn = self.driver.find_element(
                                By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[6]/a[1]')
                            self.driver.execute_script("arguments[0].click();", green_submit_btn)

                            # รอให้หน้าต่างแก้ไขราคาปิดตัวลงอย่างสมบูรณ์
                            try:
                                self.wait50.until(EC.invisibility_of_element_located(
                                    (By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[6]/a[1]')))
                                print("ปิดหน้าต่าง Overcharge สำเร็จ")
                            except Exception as wait_err:
                                print(f"Warning waiting for overcharge modal: {wait_err}")
                                time.sleep(1)

                            break
                        else:
                            # print("ไม่เจอ", item, "นะ")
                            pass
                    except Exception as err:
                        print("smco_set_overcharge_product_v2_Error occurred: ", err)
                        logger.error(f"order: {self.cus_order}: smco_set_overcharge_product_v2_Error: {err}")
                        pass

        # Todo
        #! ดูท่าทางว่าเลือกจาก bot gui จะใช้ไม่ได้
        pass

    def smco_set_discount_product(
            self, items_user_input: str = None, dc_amounts_input: str = None, qty: str = ["1"]):
        print("items_dc_target: ", items_user_input)
        print("dc_amounts_input: ", dc_amounts_input)
        if items_user_input is None or dc_amounts_input is None:
            print("เลขลำดับสินค้า หรือ จำนวนเงินที่ต้องการ ยังไม่ถูกกำหนด")
            return

        formatted_items_to_dc: list = self.sku_formater(items_user_input).split(" ")
        dc_amounts_list_prog = dc_amounts_input.split()  # * เอาไว้แยกทำลดพวกสินค้าที่สั่งมา 1 รายการแต่มีหลาย sku เช่น หมึก 4 สี
        dc_amounts_list = [float(self.oc_amounts_calculator(dc_amount)) for dc_amount in dc_amounts_list_prog]
        # * เอาไว้เก็บ element ของ item ทั้งหมดในหน้ายิงขาย
        item_elements = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')

        for idx, item in enumerate(formatted_items_to_dc):  # * loop ไล่ itemที่ลูกค้าสั่งมา
            print(f"item {idx+1} : {item}", )
            dc_amount = dc_amounts_list[0]
            print("before: round:", idx+1, "dc_amount: ", dc_amount)
            if len(dc_amounts_list) > 1:
                dc_amount = dc_amounts_list[idx]
                # try:
                # * เนื่องจาก พวกสินค้ามีหลายตัวใน 1 รายการ แต่มันอาจจะลดแค่บางตัว ตัวที่ไม่ลดฉันจะให้ใส่ตัวที่แปลงค่าเป็น int ไม่ได้ เช่น "-" หรือ "x" มาแทน เช่น (sp2-1703 sp2-1704 ลด 100 บาท) ///แต่ (sp2-1705 sp2-1706 ไม่ลด) เราก็จะใส่ qty เป็น ["1","1","-","-"] แบบนี้
                # qty = int(qtys[idx])
                # except:
                #     break

            # Convert qty to float safely
            qty_val = 1.0
            if qty is not None:
                try:
                    if isinstance(qty, list):
                        raw_qty = qty[idx] if idx < len(qty) else qty[0]
                        qty_val = float(raw_qty)
                    else:
                        qty_val = float(qty)
                except Exception:
                    qty_val = 1.0

            print("after: round:", idx+1, "dc_amount: ", dc_amount,
                  "qty: ", qty, "dc_amount * qty_val: ", dc_amount * qty_val)
            if dc_amount > 0:
                for idx2, div in enumerate(item_elements):  # * loop ไล่ element บนหน้ายิงขาย
                    try:
                        is_found = div.text.find(item)
                        li_loc = idx2+1

                        if is_found != -1:
                            print("found at li no: ", li_loc)
                            print("is_found: ", is_found)

                            css_sel_loc = {
                                'product_code': f'.col-sm-12.panel.panel-default.ng-scope:nth-child({li_loc}) div:nth-child(2) span:nth-child(1) a',
                                'total_net_btn': f'#bodyOfSku > div:nth-child({li_loc}) > div > div:nth-child(2) > div:nth-child(1) > div:nth-child(9) > a:nth-child(3)'
                            }

                            self.driver.find_element(By.CSS_SELECTOR, css_sel_loc['total_net_btn']).click()
                            # todo ถ้าไม่รอตรงนี้ code มันจะรันไปอย่างไว element มันยังไม่ทันขึ้น code รันเสร็จละ
                            time.sleep(0.5)

                            manual_dc_Input = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '#mdseScroll > div.panel.panel-default > div.panel-body > div:nth-child(1) > div > div:nth-child(1) > input')
                            self.driver.execute_script(
                                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                                manual_dc_Input, 0)
                            sum_dc_amount = dc_amount * qty_val
                            self.driver.execute_script(
                                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                                manual_dc_Input, sum_dc_amount)

                            note_textarea = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '#mdseScroll > div.panel.panel-default > div.panel-body > div:nth-child(2) > div > div > textarea')
                            self.driver.execute_script("""
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input'));
                                arguments[0].dispatchEvent(new Event('change'));
                            """, note_textarea, "Online")

                            user_id_input = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '#mdseScroll > div.panel.panel-default > div.panel-body > div:nth-child(3) > div > div:nth-child(1) > input')
                            self.driver.execute_script("""
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input'));
                                arguments[0].dispatchEvent(new Event('change'));
                            """, user_id_input, self.app.user_id.get())

                            user_pw_input = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '#mdseScroll > div.panel.panel-default > div.panel-body > div:nth-child(3) > div > div:nth-child(2) > input')
                            self.driver.execute_script("""
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input'));
                                arguments[0].dispatchEvent(new Event('change'));
                            """, user_pw_input, self.app.user_pw.get())

                            green_btn_summit = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '.row.row-space div.text-center  a.btn.btn-success.text-center#saveCustomerBtn[ng-click="okChagePrice()"]')
                            self.driver.execute_script("arguments[0].click();", green_btn_summit)

                            # รอให้หน้าต่างแก้ไขราคาส่วนลดปิดตัวลงอย่างสมบูรณ์
                            try:
                                self.wait50.until(
                                    EC.invisibility_of_element_located(
                                        (By.CSS_SELECTOR,
                                         '.row.row-space div.text-center  a.btn.btn-success.text-center#saveCustomerBtn[ng-click="okChagePrice()"]')))
                                print("ปิดหน้าต่าง Discount สำเร็จ")
                            except Exception as wait_err:
                                print(f"Warning waiting for discount modal: {wait_err}")
                                time.sleep(1)

                            break
                        else:
                            # print("ไม่เจอ", item, "นะ")
                            pass
                    except Exception as err:
                        print("smco_set_discount_product_Error occurred: ", err)
                        pass
            print("smco_set_discount_product: for loop ended!")

        # Todo
        #! ดูท่าทางว่าเลือกจาก bot gui จะใช้ไม่ได้
        pass

    def record_failed_with_checkpoint(self, reason):
        checkpoint = getattr(self, 'current_checkpoint', 'เริ่มรัน')
        full_reason = f"{reason} (ด่านที่ติด: {checkpoint})"
        if hasattr(self.app, 'accel_mode') and hasattr(self.app.accel_mode, 'record_failed_order'):
            self.app.accel_mode.record_failed_order(self.app.cus_order, full_reason)

    def is_connection_error(self, err):
        err_str = str(err).lower()
        connection_keywords = [
            "connection refused",
            "target machine actively refused it",
            "max retries exceeded",
            "winerror 10061",
            "invalid session id",
            "chrome not reachable",
            "no such window",
            "failed to check if window was closed",
            "disconnected",
            "broken pipe"
        ]
        is_conn = (
            isinstance(err, (ConnectionError, InvalidSessionIdException)) or
            any(k in err_str for k in connection_keywords)
        )
        return is_conn

    def operation_task_thread(self, event=None):
        # ใช้ generation counter เพื่อให้ old thread หยุดอัตโนมัติเมื่อ thread ใหม่เริ่ม
        self._active_generation = getattr(self, '_active_generation', 0) + 1
        my_generation = self._active_generation
        self.operation_thread = StopEvent(event, self, my_generation)

        while not self.operation_thread.is_set() and not self.app.order_Search_thread.is_set():
            print("Waiting for order search thread to finish before starting operation task...")
            time.sleep(0.5)

        if not self.operation_thread.is_set():
            while not self.operation_thread.is_set():
                try:
                    # * เริ่มการทำงาน Operation Start
                    if self.app.order != "" and not self.operation_thread.is_set():
                        logger.info(f"Order: {self.app.order} Start!!")
                        self.current_checkpoint = "เริ่มรัน"
                        self.operation_start()
                        break  # รันสำเร็จ ออกจากลูปเพื่อไปทำออเดอร์ถัดไป
                    else:
                        self.app.update_log("กรุณากรอก Order ก่อน")
                        break

                except RefreshRequiredException as err:
                    print(f"operation_task_thread, Refresh Required: {err}")
                    logger.warning(f"Order: {self.app.order} - Refresh Required: {err}")
                    msg = str(err) if str(err) else "มีการ Login ที่หน้าจออื่น"
                    self.app.update_log(f"⚠️ {msg} กำลัง Refresh ทุกแท็บของ SMCO และเริ่มงานใหม่...")
                    try:
                        self.refresh_all_smco_tabs()
                    except Exception as e:
                        print(f"Failed to refresh SMCO tabs: {e}")
                    time.sleep(2)
                    continue  # วนกลับไปรันออเดอร์เดิมใหม่

                except Exception as err:
                    if self.is_connection_error(err):
                        print(f"operation_task_thread, Connection Error: {err}")
                        logger.error(f"Order: {self.app.order} - WebDriver connection lost: {err}")
                        self.app.update_log("⚠️ การเชื่อมต่อเบราว์เซอร์หลุด กำลังพยายาม Reconnect...")

                        # ลอง reconnect
                        if self.reconnect_driver():
                            self.app.update_log("⚠️ Reconnected สำเร็จ! กำลังเริ่มทำงานออเดอร์เดิมใหม่อีกครั้ง...")
                            time.sleep(1)
                            continue  # วนกลับไปรันออเดอร์เดิมใหม่
                        else:
                            self.app.update_log("❌ ไม่สามารถ Reconnect ได้ จะลองใหม่อีกครั้งใน 5 วินาที...")
                            self.app.display_bot_status_label.configure(
                                text="Bot Status: ❌ Connection Lost", fg_color="#ff2b2b", text_color="#FFF")
                            time.sleep(5)
                            continue  # วนกลับไปพยายาม reconnect และรันใหม่เรื่อยๆ จนกว่าจะได้ หรือกดหยุด
                    else:
                        # Error จริงจากการทำออเดอร์ (เช่น ValueError หรือข้อมูลผิดพลาด) -> ข้ามออเดอร์
                        traceback_str = traceback.format_exc()
                        print(f"operation_task_thread, An error occurred: {err}")
                        print(traceback_str)
                        logger.info(f"Order: {self.app.order} operation_task_thread_outer_Exception_Error!! {err}")
                        self.record_failed_with_checkpoint(str(err))
                        break  # ออกจากลูปเพื่อข้ามไปทำออเดอร์ถัดไป
        else:
            print("Operation thread is already set, skipping operation task")
            self.app.update_log("หยุดการทำงานของ Bot บน Browser แล้ว")

    def set_cus_name_search_type(self):
        # * 1. คลิกเปิด Dropdown ก่อน
        cus_type_locator = (
            By.XPATH,
            r"//div[contains(@ng-show, 'abbCustomerFlag')]//div[contains(@class, 'input-group-prepend')]/button")
        self.driver.find_element(*cus_type_locator).click()

        is_tax = self.app.is_tax_required.get()
        marketplace = self.app.marketplace_target.get()
        print(f"Tax Required: {is_tax}, Marketplace: {marketplace}")

        # * 2. กำหนด Logic การเลือกประเภทการค้นหา (st)
        st_value = 'N'  # Default คือไม่ขอใบกำกับ

        if is_tax:
            if marketplace == "SHOPEE":
                # * ถ้ามี cus_code ใช้ 'C' ถ้าไม่มีใช้ 'T'
                st_value = 'C' if getattr(self, 'cus_code', False) else 'T'
            elif marketplace == "LAZADA":
                st_value = 'C' if getattr(self, 'cus_code', False) else 'T'

        # 3. สร้าง XPath จาก st_value ที่เลือกมา
        # ใช้ f-string เพื่อใส่ค่า st เข้าไปใน XPath ตรงๆ
        target_xpath = f"//div[contains(@ng-show, 'abbCustomerFlag')]//a[contains(@ng-click, \"st='{st_value}'\")]"

        # 4. รอให้ Element พร้อมแล้วค่อยคลิก
        print(f"Selecting search type (st='{st_value}')")
        target_element = self.wait50.until(EC.element_to_be_clickable((By.XPATH, target_xpath)))
        target_element.click()

        # * สำหรับ SMCO 8.0.0
        # print("ไม่ขอใบกำกับใช้ C:")
        # self.driver.find_element(
        #     By.XPATH, r'''//div[contains(@ng-show, "abbCustomerFlag")]//a[contains(@ng-click,"st='C'")]''').click()

    def set_cus_name_search_type_last_page(self):
        cus_type_btn = self.driver.find_element(
            By.XPATH,
            r"""//div[@ng-show='posPaymentHead.data.taxinvTypeId == 93003002 && posPaymentHead.data.taxInvFtPermission == true']//button[@class='btn btn-outline-secondary dropdown-toggle ng-binding']""")
        current_search_type = self.driver.execute_script("return arguments[0].innerText;", cus_type_btn)
        if not 'T' in current_search_type:
            self.driver.execute_script("arguments[0].click();", cus_type_btn)
            self.wait50.until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     r'''//div[contains(@id, "convertFullTaxModal")]//a[contains(@ng-click, "st='N'")]''')))
            if self.app.is_tax_required.get() == True:
                # ขอใบกำกับ **Trick** สามารถใส่single qoute สามตัวได้ หากด้านในมีการใช้ qoute และ bouble qoute ไปแล้ว แต่ทั้งหมดต้องเป็น string อีกที >>  ('''function("vbvb, x='แมว'")''')
                if self.app.marketplace_target.get() == "SHOPEE":
                    print("ขอใบกำกับSHOPEE ใช้ T:")
                    self.driver.find_element(
                        By.XPATH, r'''//div[contains(@id, "convertFullTaxModal")]//a[contains(@ng-click, "st='T'")]''').click()
                elif self.app.marketplace_target.get() == "LAZADA":
                    print("ขอใบกำกับLazada ใช้ T:")
                    self.driver.find_element(
                        By.XPATH, r'''//div[contains(@id, "convertFullTaxModal")]//a[contains(@ng-click, "st='T'")]''').click()
            elif self.app.is_tax_required.get() == False:
                # ไม่ขอใบกำกับ
                print("ไม่ขอใบกำกับใช้ N:")
                self.driver.find_element(
                    By.XPATH, r'''//div[contains(@id, "convertFullTaxModal")]//a[contains(@ng-click,"st='N'")]''').click()

        print("set_cus_name_search_type_last_page ends.")

    def dropdown_handler(self):
        print("dropdown_handler starts")
        while not self.operation_thread.is_set():
            try:
                li_locators = self.driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
                # print("li_locators.text: ", li_locators[0].text)
                if not "Searching" in li_locators[0].text:
                    break
                time.sleep(0.3)

            except:
                time.sleep(0.45)
                continue

    def select_cusname_address_last_page(self):
        is_last_page = True
        if self.app.marketplace_target.get() == "SHOPEE":
            self.cus_search_input = self.app.tax_num.get() if self.app.is_tax_required.get(
            ) else self.app.cus_name_cleaner(self.app.cus_name.get())
        elif self.app.marketplace_target.get() == "LAZADA":
            self.cus_search_input = self.app.tax_num.get() if self.app.is_tax_required.get(
            ) else self.app.cus_name_cleaner(self.app.cus_name.get(), self.app.cus_account_name.get())

        # * เริ่มกระบวนการหาชื่อลูกค้าสำหรับออกบิล invoice
        self.get_customer_name_ready(self.cus_search_input, is_last_page)

        # * ใส่ตัวเช็คที่อยู่ลูกค้า
        if self.app.is_tax_required.get():
            print("tax required, start address check and correct")
            self.cus_name_span = self.driver.find_element(
                By.XPATH, "//span[@id='select2-invAddressSelectFt-container']")
            # * ที่กล้าเก็บค่า attribute มาใช้ตรงๆแบบนี้เพราะต่อให้ไม่มี attribute มันก็ return ค่าว่างอยู่ดี ซึ่งปกติ element นี้จะแสดง attribute title ด้วยถ้ามีการเลือกที่อยู่ลูกค้าแล้ว ถ้าไม่เลือก attribute title จะไม่แสดงใน html
            self.text_from_name_span = self.cus_name_span.get_attribute("title")
            self.tax_address_corrector(self.text_from_name_span)

        else:
            print("no tax required, skip address check")
        pass

    def get_customer_name_ready(self, cus_search_input, is_last_page: bool = False):
        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
        print(f"Order: {self.cus_order} : get_customer_name_ready starts")
        self.set_cus_name_search_type()
        #! ใช้ getarrt('cus_code') ไรประมาณนี้ เพราะ cus_code มันยังไม่ถูกสร้างมันจะถูกสร้างทีหลังหากมีการเคส duplicated customer

        # * start Enter customer name here +++++++++++==================================================
        while not self.operation_thread.is_set():
            if getattr(self, 'cus_code', False):
                self.enter_cus_name(self.cus_code)
            else:
                self.enter_cus_name(cus_search_input)
            print("กรอกชื่อเสร็จ")
            # * wait_condition มันจะเจอ cusNameLi1 ที่ containค่า "Searching..."
            self.searching_condition = self.driver.find_element(By.XPATH, self.app.cusNameLi1)
            # * มันจะได้ Searching...
            print("มันทำไม", self.searching_condition.text)

            # ? WIP แก้ละรอดูว่าพังไหม //pop-up เด้งแทรกตอนกรอกชื่อลูกค้าในช่อง search
            # pop-up อันนึงเด้งมาหลังจาก กรอกชื่อ  xpath : "/html/body/div[16]/div[2]/div[6]" text: "Reload data not complete,reload page verify data again." button:"//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]"
            try:
                # * มี pop-upไหม
                if self.driver.find_element(By.XPATH, "/html/body/div[16]/div[2]/div[6]").is_displayed():
                    # * ถ้ามี ปิด แล้วเริ่มไปกรอกชื่อใหม่
                    self.driver.find_element(
                        By.XPATH,
                        "//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]").click()
                    continue
                # * ไม่มี pop-up ให้ break
                break
            except:
                break

        # * ตาม Stepแล้วนั้น ขั้นตอนด้านบนจะทำให้ Dropdown UL มันโผล่ และมี li อย่างน้อย 1 อัน นั่นคือ li[0] โดย li[0] จะบอกสถานะของการ search ตั้งแต่ "Searching...", "No results found", ไม่แน่ใจมีอีกไหม และแสดง ผลลัพธ์ที่เจอลำดับแรก
        self.ensure_li_shown_cus_name()  # *เนื่องจาก li แสดง สถานะและชื่อลูกค้า ซึ่งต้อง handle ให้แน่ใจว่าเป็นชื่อลูกค้าจริงๆก่อน

        # * is_name_list_selectable จะมีการตรวจสอบว่าเลือกได้เหรือไม่ ถ้าเลือกได้ก็เลือกเลย----------------------------
        while not self.operation_thread.is_set():
            time.sleep(0.5)
            try:
                #! มีแววว่าจะ deprecated? # * รอให้ dropdown ul โผล่มาก่อน แทนที่จะใช้ find_element ตรงๆ
                # self.wait50.until(EC.presence_of_element_located((By.XPATH, self.app.cus_name_dropdown_ul))) #! มันมีตั้งแต่ขั้นตอน ที่แล้วแล้ว จาก fn ensure_li_shown_cus_name()
                # * หา li ไปตรวจสอบว่ามี len เท่าไหร่ (re-fetch เพื่อหลีกเลี่ยง stale element)
                customer_name_input_ul_from_dropdown = self.driver.find_element(By.XPATH, self.app.cus_name_dropdown_ul)
                customer_name_lis_from_dropdown = customer_name_input_ul_from_dropdown.find_elements(
                    By.CSS_SELECTOR, '.select2-results__option')

                cus_found_names_list = [element.text for element in customer_name_lis_from_dropdown]
                self.select_cus_name_from_lis(
                    self.app.cus_name.get(),
                    cus_found_names_list,
                    self.select_cus_name_from_lis
                )
                print("click แล้ว")
                break

            except ValueError as ve:
                print(f"Aborting customer selection due to ValueError: {ve}")
                raise ve
            except Exception as err:
                print("ยังเลือกชื่อลูกค้าไม่ได้เลย:", err)
                time.sleep(0.5)
                try:
                    self.driver.find_element(By.XPATH, self.app.cus_arrow_btn).click()
                except Exception:
                    pass
                continue

        # * กรณีมีสินค้ายิงไปแล้ว แล้วมีการเปลี่ยนชื่อลูกค้า มันจะมี alert // path นี้คือ element นอกของ alert /html/body/div[16]/div[2]
        while not self.operation_thread.is_set():
            try:
                if self.driver.find_element(By.XPATH, "/html/body/div[16]/div[2]").is_displayed():
                    try:
                        self.driver.find_element(
                            By.XPATH, "//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]").click()
                        self.driver.find_element(By.XPATH, self.app.cus_arrow_btn).click()
                        self.wait50.until(EC.visibility_of_element_located((By.XPATH, self.app.cusNameInput)))
                        break
                    except:
                        print("Skip, Alert Element is appear but can not perform actions.")
                        break
                else:
                    print("Skip, Alert Element is Not appear")
                    break

            except:
                continue

        print(f"Order: {self.cus_order} : search หายไปแล้ว: get_customer_name_ready() ends")
        self.wait50.until(EC.invisibility_of_element_located((By.XPATH, self.app.cusNameInput)))

    def enter_cus_name(self, cus_search):
        # * ย้ายไปหน้าหลัก
        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])

        # * clear ชื่อ เก่า
        self.driver.find_element(By.XPATH, self.cus_name_dropdown_elmt_loc).click()

        # * จับตาดูว่า ul เปิดอยู่ไหม
        self.is_ul_open = True if self.driver.find_elements(By.XPATH, self.app.cus_name_dropdown_ul) else False

        # * กรณีไม่ได้เปิดไว้ จะเปิดให้
        if not self.is_ul_open:
            self.driver.find_element(By.XPATH, self.app.cus_arrow_btn).click()
            self.wait50.until(EC.visibility_of_element_located((By.XPATH, self.app.cusNameInput)))

        # * เคลียและกรอกชื่อลูกค้า
        self.driver.find_element(By.XPATH, self.app.cusNameInput).clear()
        self.driver.find_element(By.XPATH, self.app.cusNameInput).send_keys(cus_search)

    def add_new_customer(self, cb=None):
        # * ขอใบกำกับป่าว
        if self.app.is_tax_required.get():
            print("Tax_needed")
            if self.app.marketplace_target.get() == 'SHOPEE':
                self.addCustomer("tax")

            # * กำลังทำ กำลังปรับปรุง ยังไม่เสร็จ การหาลูกค้าของ laz มันมีกรณี excel และ api
            elif self.app.marketplace_target.get() == 'LAZADA':
                self.addCustomer("tax_laz")

        else:
            print("no_Tax_needed")
            self.addCustomer("normal", self.cus_search_input)

        try:
            cus_code_element = self.wait_and_get_popup(5)
            if cus_code_element:
                # * เคส duplicate cus name จะเกิดโดยชื่อซ้ำ มักจะเกิดกับกรณีที่ ชื่อลูกค้าที่ชื่อเก่าไม่มีเลขผู้เสียภาษี แต่ถัดมาลูกค้าขอด้วยชื่อเดิมเพิ่มเติมคือมีเลขผู้เสียถาษีbotจะเสิชด้วยเลขผู้เสียภาษีแล้วจะทำให้หาไม่เจอทำให้เกิดการadd customer ใหม่ ทำให้ชื่อแบบที่ไม่มีเลขผู้เสียภาษี ซ้ำกับชื่อที่แอดใหม่(มีเลขผู้เสียภาษี)-
                # *-duplicate_cus_name_resolver จึงแก้ไขโดยการเพิ่มเลขผู้เสียภาษีให้กับชื่อลูกค้าอันเดิมทำให้ไม่มีการซ้ำเกิดขึ้น
                # * กรณี add แล้ว มี popup-duplicate customer
                print("Check Duplicated customer!!")
                if self.app.is_tax_required.get():
                    self.duplicated_cus_name_resolver(cus_code_element)
            else:
                raise ValueError("Popup not found after adding customer.")

        except RefreshRequiredException:
            raise
        except Exception as err:
            if self.app.is_auto_invoice_mode.get():
                logger.error(
                    f"Order: {self.cus_order} - Auto Invoice Mode is ON, but failed to add customer. Error: {err}")
                print("Auto Invoice Mode is ON, but failed to add customer, correct the unfinished order number and note the reason to the main loop input file")
                raise ValueError(f"Auto Invoice Mode is ON, but failed to add customer. Error: {err}")

            print("No duplicate!", err)

        if self.click_popup_confirm_button():
            print("add_new_customer() end, swal confirm button is clicked after add customer")
        else:
            print("add_new_customer() end, but No swal confirm button to click after add customer")

    def ensure_li_shown_cus_name(self):
        """
        li ที่จะแสดงใน ul นั้นมันไม่ได้มีแค่ชื่อลูกค้า แต่มันมี สถานะเช่น "กำลังหา" หรือ "หาไม่เจอ" ซึ่งทำให้กดเลือกชื่อลูกค้าจาก li ไม่ได้ทันที จึงต้อง handle ส่วนนี้โดยทำให้ค่าที่โผล่ใน li นั้นเป็น ชื่อลูกค้าแล้วจริงๆแล้วไปยังขั้นตอนต่อไป (functionนี้ยังไม่มีการเลือกliนะ)
        มันเปนการกรอกชื่อและดูผลลัพของ li ต่างๆว่า แสดงผลอย่างไร มันจะมีกรณีแสดง li เดียวแล่้วถูก,  แสดง li เดียวแต่เปนการบอกว่าไม่มีชื่อ, แสดง li จำนวนมาก แต่มีตัวถูก, แสดง li จำนวนมาก แต่ไม่มีตัวถูก
        """
        self.customer_added_times = 0
        self.customer_name_search_count = 0
        print(f"""order: {self.cus_order}: ensure_li_shown_cus_name starts""")
        while not self.operation_thread.is_set():
            try:
                self.wait50.until(EC.presence_of_element_located((By.XPATH, self.app.cus_name_dropdown_ul)))
            except Exception:
                time.sleep(0.5)
                continue
            if self.driver.find_elements(By.XPATH, self.app.cus_name_dropdown_ul):
                time.sleep(0.7)
                # * li[1] เป็นตัวที่แสดงผลแบบ dynamic เราจะตรวจจับ พฤติกรรมของ element นี้
                self.searching_condition = self.driver.find_element(By.XPATH, self.app.cusNameLi1)

                # * ช่วงรอ ผลลัพของ Searching...
                try:
                    if self.searching_condition.text == "Searching...":
                        continue
                    elif self.searching_condition.text:
                        print("text element not display Searching...")
                        pass
                except:
                    pass

                # * หลังจาก Searching... หายไป ๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑๑
                self.wait50.until(EC.visibility_of_element_located((By.XPATH, self.app.cusNameLi1)))
                self.searching_condition = self.driver.find_element(By.XPATH, self.app.cusNameLi1)

                # * กรณี ไม่เจอผลลัพธ์ ทำการ Add ใหม่
                if self.searching_condition.text == "No results found" and self.customer_added_times == 0:
                    print("No results found and NeverAdd")
                    self.add_new_customer()

                    # * เพิ่มจำนวนครั้งที่ add
                    self.customer_added_times += 1
                    print("ก่อนRe Enter ชื่อลูกค้า")
                    self.enter_cus_name(self.cus_search_input)
                    self.customer_name_search_count += 1
                    print(f"Re enter name after add")
                    continue
                # * หลังจาก Add ไปแล้วรอบนึง แล้วมาเสิชใหม่แล้วยังไม่เจอ ถึงจะเข้าเงื่อนไขนี้ เป็นการ search ให้อีกรอบนึง
                elif self.searching_condition.text == "No results found" and self.customer_name_search_count < 2:
                    time.sleep(1)
                    self.enter_cus_name(self.cus_search_input)
                    self.customer_name_search_count += 1
                    print(f"Re enter name after add extra times {self.customer_name_search_count}")
                    continue
                # * Add แล้ว รีเสิชให้สองรอบแล้ว ก็ยังไม่เจอ ลองแอดด้วยตัวเองดู
                elif self.searching_condition.text == "No results found" and self.customer_added_times == 1:
                    print("I've already add it, but the element still shows 'No results found', you have to add by yourself")
                    self.enter_cus_name(self.cus_search_input)
                    self.customer_name_search_count += 1
                    time.sleep(1)
                    continue
                else:
                    print("Found a customer name:", self.searching_condition.text)
                    print("Cusname lis are shown and ready to select")
                    self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
                    break
            print("addcustomer and select While end!")
            print(f"""order: {self.cus_order}: ensure_li_shown_cus_name ends""")
            break

    # !66 WIP เปลี่ยนวิธีเลือกชื่อลูกค้า เดิมทีคือเลือก // ชิพหายมันเลือกค่าจาก i
    def select_cus_name_from_lis(self, cus_desire_name, cus_name_list, cb=""):
        print(f"""order: {self.cus_order} : select_cus_name_from_lis starts """)
        tax_num = str(self.app.tax_num.get())
        print('tax_num: ', tax_num)

        if self.app.marketplace_target.get() == "LAZADA" and self.app.is_tax_required.get():
            print("A Lazada customer with tax number, get desired name from vatinfo data API")
            # * ล้างคำที่ไม่เกี่ยวกับชื่อลูกค้า (คำเสริมยศต่างๆที่ไม่สำคัญกับการแยกแยะว่าใครเป็นใคร)
            if self.tax_info.get(tax_num):
                # / self.tax_info เป็น dict ที่ยิง api มาเก็บไว้แล้ว ถ้ามี tax_num นี้อยู่ใน dict แล้วก็ใช้เลย ไม่ต้องยิง api ใหม่
                cus_desire_name = self.tax_info[tax_num]['name']
            else:
                # / ถ้าไม่มีใน dict ก็ยิง api ใหม่แล้วเก็บไว้ใน dict มาใช้ต่อ (ทำไมถึง else ไว้นะ มันก็น่าจะมีตั้งแต่แรกนี่หว่าจำที่มาไม่ได้)
                vatinfo_data = self.get_vatinfo_data(tax_num, self.app.tax_branch_num.get())
                self.tax_info[tax_num] = vatinfo_data if vatinfo_data else {}
                cus_desire_name = self.tax_info[tax_num]['name']

            self.app.cus_tax_name_lazada.set(cus_desire_name)

        print("incoming cus_desire_name: ", cus_desire_name)
        # ลบคำนำหน้า
        pattern_prefix = r'^(บริษัท|บจก\.?|หจก\.?|หสม\.?|บมจ.\.?|ห้างหุ้นส่วนจำกัด|ห้างหุ้นส่วนสามัญ|บจ\.?|บ\.)\s*'

        # ลบคำลงท้ายพวกสาขาก่อน
        pattern_branch = r'(สำนักงานใหญ่|สํานักงานใหญ่|สนญ\.?|\(สำนักงานใหญ่\)|\(สํานักงานใหญ่\)|\(สนญ\.?\)|\(00000\)|\s*\(?สาขา.*)$'

        # ลบคำว่าจำกัดที่อาจจะอยู่ท้ายสุดหลังจากลบสาขาแล้ว
        pattern_suffix = r'จำกัด(\s*มหาชน)?\s*[A-Za-z0-9]*$'

        current_cus_name: str = self.cus_name_span_elmt.text if self.cus_name_span_elmt else ""

        cus_desire_name = cus_desire_name.strip()
        cus_desire_name = re.sub(pattern_prefix, '', cus_desire_name)
        cus_desire_name = re.sub(pattern_branch, '', cus_desire_name).strip()
        cus_desire_name = re.sub(pattern_suffix, '', cus_desire_name).strip()

        cus_desire_name = cus_desire_name.replace(" ", "")
        cus_desire_name = cus_desire_name.replace("\n", "")
        cus_desire_name = cus_desire_name.replace("(", "")
        cus_desire_name = cus_desire_name.replace(")", "")

        is_branched: bool = self.app.branch_type == "สาขาย่อย"

        print(f"[select_cus_name_from_lis]cus_desire_name: {cus_desire_name} /// current_cus_name: {current_cus_name}")
        current_cus_name_cleaned = current_cus_name.replace(" ", "").replace("(", "").replace(")", "")
        if cus_desire_name in current_cus_name_cleaned and self.app.tax_branch_num.get() in current_cus_name_cleaned:
            while not self.operation_thread.is_set():
                try:
                    self.driver.find_element(By.XPATH, self.app.cus_name_dropdown_ul)
                    self.driver.find_element(By.CSS_SELECTOR, "#select2-memberSearch-container").click()
                    break
                except:
                    time.sleep(0.5)
                    continue

            print(f"cus_desire_name has already in current_cus_name")
            return

        # * ทำการคัดเอาเฉพาะชื่อลูกค้าไม่เอารหัส ลง array
        names_no_code = cus_name_list.copy()
        for i in range(len(cus_name_list)):
            prog = re.search(r'[^-]-(.*)', names_no_code[i])
            names_no_code[i] = prog.group(1).replace(" ", "")
        self.has_branch_code_in_df = not pd.isna(self.app.data_frame[self.app.target_row]['รหัสประจำสาขา'].iloc[0])
        # * เอา array มาหาดูว่าจะต้องเลือกชื่อไหน เอา idx ที่ได้ไช้ระบุ locator ที่ต้อง click
        for i, name in enumerate(names_no_code):
            name = name.replace(")", "")
            name = name.replace("(", "")

            print("if ", cus_desire_name, " In ", name)
            print("จริงทั้งคู่ไหม: ", is_branched, "และ ", self.app.tax_branch_num.get() in name)
            print(f"""is_branched: {is_branched} 
                  tax_branch_num in name: {self.app.tax_branch_num.get()} in {name} {self.app.tax_branch_num.get() in name} 
                  has_branch_code_in_df: {self.has_branch_code_in_df}""")
            if cus_desire_name in name:
                if is_branched:
                    # * สาขาย่อยจริง (เพราะ column "ประเภทสาขา" ใน df มันจะ เป็น ประเภท "สาขาย่อย" แล้วมีเลข)
                    if self.has_branch_code_in_df:
                        if not self.app.tax_branch_num.get() in name:
                            print("เจอชื่อ แต่ชื่อที่เจอไม่ใช่สาขาย่อยที่ถูกต้องตามที่ลูกค้าต้องการ ข้าม")
                            continue
                        print("ชื่อสาขาย่อยที่ต้องการ อยู่ใน li")
                        while not self.operation_thread.is_set():
                            try:
                                print("เลือกชื่อลูกค้าสาขาย่อย", cus_name_list[i])
                                # * ต้อง +1 เพราะว่า xpath รับค่าเป็นจำนวนเต็ม+ ไม่ใช่ index
                                self.driver.find_element(By.XPATH, f"/html/body/span/span/span[2]/ul/li[{i+1}]").click()
                                return

                            except:
                                print("No customer found")
                                time.sleep(0.5)
                    else:  # * personal (เพราะ column "ประเภทสาขา" ใน df มันจะ เป็น ประเภท "สาขาย่อย" แต่ไม่มีเลข)
                        while not self.operation_thread.is_set():
                            try:
                                print("เลือกชื่อลูกค้าใบกำกับแบบบุคคล", cus_name_list[i])
                                # * ต้อง +1 เพราะว่า xpath รับค่าเป็นจำนวนเต็ม+ ไม่ใช่ index
                                self.driver.find_element(By.XPATH, f"/html/body/span/span/span[2]/ul/li[{i+1}]").click()
                                return

                            except:
                                print("No customer found")
                                time.sleep(0.5)

                elif not re.search(r"สาขา.*?\d{5}", name):
                    print("ชื่อที่ไม่มีสาขา อยู่ใน li")
                    while not self.operation_thread.is_set():
                        try:
                            print("เลือกชื่อลูกค้าธรรมดา|ใบกำกับสนงใหญ่", cus_name_list[i])
                            # * ต้อง +1 เพราะว่า xpath รับค่าเป็นจำนวนเต็ม+ ไม่ใช่ index
                            self.driver.find_element(By.XPATH, f"/html/body/span/span/span[2]/ul/li[{i+1}]").click()
                            return

                        except:
                            print("No customer found")
                            time.sleep(0.5)
                continue

            # * ถ้ามันเจอก็จะ จบ function แต่ถ้าไม่เจอจะไปใช้ cb ต่อ

        print(f"order: {self.cus_order} : select_cus_name_from_lis: ไม่มีชื่อที่ใช้ได้ Add ใหม่")
        self.add_new_customer(lambda: self.get_customer_name_ready(self.cus_search_input))
        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
        try:
            customer_current_input_name = self.cus_name_dropdown_elmt_loc.text
            print(
                f"Order: {self.cus_order} : select_cus_name_from_lis(): customer_current_input_name: {customer_current_input_name}")
            prog = re.search(r'[^-]-(.*)', customer_current_input_name)
            customer_current_input_name = prog.group(1).replace(" ", "")
            print(f"customer_current_input_name: {customer_current_input_name} and cus_desire_name: {cus_desire_name}")
        except:
            customer_current_input_name = self.cus_search_input
            print(
                f"Order: {self.cus_order} : select_cus_name_from_lis(): customer_current_input_name: {customer_current_input_name}")
        self.get_customer_name_ready(customer_current_input_name)
        return
        try:
            if cb:
                print("use callback layer1: เพื่อ make sure ว่า li มันใช้ไม่ได้")
                cb(cus_desire_name, cus_name_list)

            # * cb ให้รอบนึงแล้วก็ไม่เจอ แอดใหม่ให้
            # print('ไม่เจอ แอดใหม่ เปลี่ยนชื่อให้ด้วย')
            # self.cus_search_input = self.app.cus_name.get()
            # self.add_new_customer()
        except:
            print("cb doesn't works")

        # print("ก่อนRe Enter ชื่อลูกค้า")
        # self.enter_cus_name(self.cus_search_input)
        # print(f"Re enter name after add")
        # * มันจะมีกรณีที่ถ้าเลือกลูกค้าได้ในครั้งแรก cb จะไม่ทำงานในส่วนนี้
        try:
            if cb:
                print("use callback layer2: for what?")
                cb(cus_name_list)
        except:
            print("cb doesn't works")

        # * มันจะมีกรณีที่ถ้าเลือกลูกค้าได้ในครั้งแรก cb จะไม่ทำงานในส่วนนี้

    def has_sale_type_selected(self) -> bool:
        """
        elements บางส่วนจะมีการโชว์หรือซ่อนขึ้นอยู่กับค่าของ Sale Type ด้วย ฉะนั้นต้องชัวร์ก่อนว่าได้เลือก Sale Type แล้ว
        """
        # ? wip เช็คตรงนี้ก่อน
        # ? //span[(contains(., "AR Online") or contains(., "Online Sale")) and not(contains(., "Deposite -"))and(@id="select2-divSaletype2-container")]
        # ? ว่ามี element ใหม่ ถ้ามี แปลว่าเลือกแล้ว ถ้าไม่มีค่อยลงมาทำข้างล่าง
        try:
            self.driver.find_element(
                By.XPATH,
                """//span[(contains(., "AR Online") or contains(., "Online Sale")) and not(contains(., "Deposite -"))and(@id="select2-divSaletype2-container")]""")
            return True
        except:
            print("Sale Type ยังไม่ได้เลือก")
            return False

    def select_sale_type(self):
        while not self.operation_thread.is_set():
            try:
                self.driver.find_element(
                    By.CSS_SELECTOR, '#contentZen > div.ng-scope > div:nth-child(2) > div.panel-body > div.col-sm-3 > div.col-sm-12.nopadding > div.panel-body > div > div > div:nth-child(2) span.select2-selection__arrow').click()
                break
            except:
                time.sleep(0.5)
                continue
        time.sleep(0.25)
        self.dropdown_handler()
        while not self.operation_thread.is_set():
            try:
                #! ยังไม่สมบูร 100%
                self.driver.find_element(
                    By.XPATH, '//*[@id="select2-divSaletype2-results"]/li[(starts-with(., "AR Online") or starts-with(., "Online Sale")) or starts-with(., "Sale exhibition") and not(contains(., "Deposite -"))]').click()
                print("เจอ saletype li")
                return
            except Exception as err:
                print("ยังไม่เจอ li ให้เลือก")
                print("select_sale_type Error: ", err)
                time.sleep(0.5)
                continue
        raise ValueError(f'Thread has been terminated during select_sale_type')

    def insert_emp(self):
        self.smco_current_emp = self.driver.find_element(
            By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]').text
        if not self.app.user_id.get() in self.smco_current_emp:
            while not self.operation_thread.is_set():  # * รอโหลดหลังเลือก AR บางครั้งมันจะเclick ไม่ได้เพราะมันมีการเอา background fading มาบัง
                try:
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]').click()
                    self.driver.find_element(
                        By.XPATH, '/html/body/span/span/span[1]/input').send_keys(self.app.user_id.get())
                    break
                except:
                    time.sleep(0.25)
                    continue

            while not self.operation_thread.is_set():
                time.sleep(0.25)
                try:
                    if self.app.user_id.get() in self.driver.find_element(
                            By.XPATH, '/html/body/span/span/span[2]/ul/li').text:
                        self.driver.find_element(By.XPATH, '/html/body/span/span/span[2]/ul/li').click()
                        print("Found emp and select")
                        break

                except:
                    continue

    def open_old_tax_form(self):
        try:
            self.driver.find_element(
                By.XPATH, "//button[@class='btn btn-primary' and @ng-click='abbCustomerFlag = false;']").click()
        except:
            print("Cannot click 'ค้นหาลูกค้า'")

    def add_shipping_cost(self):
        shipping_cost = int(self.app.cus_ship_cost.get())
        has_shpping_cost = False
        print("มี item ใน listไหม")
        item_elements = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
        if len(item_elements) > 0:
            print("มี item ใน list", len(item_elements))
            for idx, item_element in enumerate(item_elements):
                item_sku_name = ''
                item_sku_name_element = item_element.find_element(By.CSS_SELECTOR, "u.ng-binding")
                item_sku_name = self.driver.execute_script("return arguments[0].textContent;", item_sku_name_element)
                print(f"""sku name: {item_sku_name}""")

                item_srp = 0
                item_srp_element = item_element.find_element(By.XPATH, ".//span[@class='font-color-base ng-binding']")
                item_srp = self.driver.execute_script("return arguments[0].textContent;", item_srp_element)
                before_decimal = item_srp.split('.')[0]
                cleaned_item_srp = int(re.sub(r'[^0-9]', '', before_decimal))
                print(f"""srp: {cleaned_item_srp}""")

                if item_sku_name != 'SV0-000101':
                    continue
                elif item_sku_name == 'SV0-000101' and cleaned_item_srp == shipping_cost:
                    print("shpping cost has been corrected")
                    has_shpping_cost = True
                    return
                elif item_sku_name == 'SV0-000101' and cleaned_item_srp != shipping_cost:
                    print(
                        f"shpping cost has not been corrected: {item_sku_name}:  {cleaned_item_srp}  != {shipping_cost}: {cleaned_item_srp != shipping_cost}")
                    # ! item_elements ต้องอ่านค่าใหม่เพราะ ทันทีที่กดลบ element นี้มันจะไม่เหมือนเดิมเพราะมันลบ chirldren node ออก
                    item_elements = self.driver.find_elements(
                        By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
                    item_delete_btn_element = item_element.find_element(
                        By.XPATH, ".//button[@class='btn btn-danger btn-sm ng-scope']")
                    item_delete_btn_element.click()
                    # while not self.operation_thread.is_set():
                    #     try:
                    #         item_element.is_enabled()
                    #         continue
                    #     except:
                    #         time.sleep(2)
                    #         break
                    has_shpping_cost = False
                    pass
                else:
                    has_shpping_cost = False
        else:
            print("ไม่เคยมี item ใน list มาก่อน")
            has_shpping_cost = False

        if int(shipping_cost) != int(0) and not has_shpping_cost:
            try:
                self.sku_input_element = self.driver.find_element(
                    By.XPATH, "//span[contains(@class, 'arFilterBox-')]//input[@name='svalue' and contains(@class, 'arFilterBox-search ')]")
                self.js_input_value(self.sku_input_element, 'SV0-000101')
                self.sku_input_element.send_keys("\ue007")
                print("กรอก Code ขนส่งสำเร็จ")
                # response_data = self.network_capture.capture_response('getProductMasterInfoPOSV3.htm')
                # if response_data:
                # * ถ้าไม่มีรู้สึกว่า element li จะโหลดไม่ทันทำให้ funciton ปรับราคานี้ไม่ทำงาน
                while not self.operation_thread.is_set():
                    try:
                        self.driver.find_element(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
                        print("item li found")
                        self.smco_set_overcharge_product('SV0-000101', shipping_cost)
                        print("กด Enter ที่ช่อง SKU Input สำเร็จ")
                        break
                    except:
                        time.sleep(0.75)
                        continue

                # self.skuAddBtn = self.wait50.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')))
                # skuAddBtn = self.driver.find_element(By().XPATH,'/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')
                # self.skuAddBtn.send_keys("\ue007")  # กด Enter

                #! WIP ทดสอบ 1/2 หยุดเพื่อให้จบ if ก่อน แล้ว2/2 จะเป็นชั้นที่จบ scope จริงๆ รู้สึก return ตรนี้ใช้แล้วจะจบเลย ไม่ได้จบแค่ if งั้นเหรอ
                # logger.info(f"Order: {self.app.order} 1/2Finished!!")
                # return

            except Exception as err:
                err_str = str(err).lower()
                if "connection refused" in err_str or "target machine actively refused it" in err_str or "max retries exceeded" in err_str or "winerror 10061" in err_str:
                    print(f"Connection lost during add_shipping_cost: {err}")
                    logger.error(f"Connection lost during add_shipping_cost: {err}")
                    self.app.update_log("⚠️ Session lost while adding shipping cost. Attempting to reconnect...")
                    self.reconnect_driver()
                    self.app.update_log("⚠️ Reconnected. Please check the shipping cost manually.")
                else:
                    print("Shipment cost skipped: ", err)
        else:
            print("No shipment cost")

    def printtingPage(self):
        time.sleep(1)
        self.printing_page = self.driver.find_element(By().XPATH, '/html/body')
        self.action01 = ActionChains(self.driver).context_click(self.printing_page)
        self.action01.perform()

    #! deprecated?
    def just_press_p(self):
        time.sleep(1)
        self.wsh.SendKeys("P")
        time.sleep(1.55)
        self.wsh.SendKeys("{Enter}")
        print("print แล้ว")
        time.sleep(2)
        # * กดข้างนอกแล้วส่ง event ปุ่ม  ESC จาก KB
        # self.driver.find_element(By.XPATH, '/html/body/div[3]/div/div/div').click()
        # self.wsh.SendKeys("{ESC}")

        # * ใช้ selenium กดปุ่มแดงโดยตรง ปุ่มแดงหน้า print ไม่เหมือน ปุ่มแดงหน้าแรก เพราะห้นปริ้นจะเป็น tag a ส่วนหน้าปกติมันเป็น button ใช้คนละ element แต่อยู๋ตำแหน่งเดียวกัน โคตรปั่น
        self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[8]/div/div[1]/div/a').click()

        print("กด ปุ่มแดง ออก แล้ว")
        # ถ้าเขียนเป็น cb แล้วมันจะพัง

    def etax_reprint(self, inv_number):
        try:
            # * เก็บหน้าเก่าเพื่อ กลับไปหน้าเดิมก่อน reprint
            prev_window = self.driver.current_window_handle
            # * สลับหน้าไป reprint
            self.driver.switch_to.window(self.merged_dict['SMCO :: พิมพ์ใบเสร็จซ้ำ'])
            print("สลับไปหน้าพิม์ใบเสร็จซ้ำ")

        except:
            # * สลับไม่ได้เปิด reprint ใหม่
            print("ไม่มีหน้าให้สลับ เปิดใหม่")
            self.driver.get(f"{self.origin}/smartcore/smartpos/payment/reprint_invoice.htm?mc=POS2050")
            all_window_handles = self.driver.window_handles
            latest_window_handle = all_window_handles[-1]
            self.driver.switch_to.window(latest_window_handle)
            print("ไม่มีเปิดใหม่")

        # * เริ่มทำการกรอกบิลล่าสุดในหน้า reprint หน้า พิมพ์ใบเสร็จซ้ำ
        try:
            print("Start reprint")
            time.sleep(0.75)
            # * > เปิด dropdownก่อน ไม่งั้นใช้ input ไม่ได้
            self.driver.find_element(
                By().XPATH, '/html/body/div[1]/div[2]/div[1]/div[2]/div/div[1]/div[1]/div/span/span[1]/span/span[1]').click()
            self.driver.find_element(By().XPATH, '/html/body/span/span/span[1]/input').clear()
            self.driver.find_element(By().XPATH, '/html/body/span/span/span[1]/input').send_keys(inv_number)
            self.driver.find_element(
                By().XPATH, '/html/body/div[1]/div[2]/div[1]/div[2]/div/div[2]/div[2]/div/textarea').clear()
            self.driver.find_element(
                By().XPATH, '/html/body/div[1]/div[2]/div[1]/div[2]/div/div[2]/div[2]/div/textarea').send_keys("Etax")
            # while not self.operation_thread.is_set():
            #     # if self.driver.find_element(By.XPATH, '/html/body/span/span/span[2]/ul/li').text == "Searching...":
            #     #     continue
            #     time.sleep(0.75)
            #     if self.driver.find_element(By.XPATH, '/html/body/span/span/span[2]/ul/li').text == inv_number:
            #         self.driver.find_element(By.XPATH, '/html/body/span/span/span[2]/ul/li').click()
            #         self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[1]/div[1]/span/button[2]').click()
            #         break

        except Exception as err:
            print("reprint พัง: ", err)

        # * กลับหน้าเดิม
        self.driver.switch_to.window(prev_window)

    def get_pdf_src_and_print(self, inv_number, retry_count=0, max_retries=3):
        # * Get the current time in UTC
        self.utc_time = datetime.datetime.now()
        # * Specify the timezone
        self.tz = pytz.timezone('Asia/Bangkok')
        # * Convert the current time to Bangkok time and format it
        self.th_time = self.utc_time.astimezone(self.tz).strftime("%d_%m_%Y-%I_%M_%S_%p")
        # * use inv_number from pop-up and time to create file name
        self.pdf_path = f"{inv_number}_{self.th_time}.pdf"

        # * get base64_str
        self.base64_pdf_data = self.get_base64_from_ui()

        # * แปลง base64 back to binary data and write down to pdf
        self.base64_to_pdf(self.base64_pdf_data, self.pdf_path)
        self.bin_pdf_data = base64.b64decode(self.base64_pdf_data)  # ! ทำไรวะ

        # * collect txt from pdf
        self.extracted_txt = self.pdf_to_txt(self.pdf_path)

        # * is inv correct?
        if inv_number in self.extracted_txt:
            print(f"""inv_number:\ncorrect inv!!\n{inv_number}""")
            # * print
            try:
                print("Print via sumatra printer")
                self.print_pdf_silence_sumatra(self.pdf_path)
            except:
                print("Print via default printer")
                self.print_pdf_silence(self.pdf_path)

        else:
            print(f"""inv_number:\nwrong inv!!\nget src again""")
            if retry_count < max_retries:
                print("retry count:", retry_count+1)
                self.get_pdf_src_and_print(inv_number, retry_count+1)

        # * กดปุ่มแดงปิดหน้า print
        try:
            cancel_btn_element = self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[3]/div[10]/div/div[1]/div[2]/a')
            self.driver.execute_script("arguments[0].click();", cancel_btn_element)
        except Exception as e:
            print(f"Error closing print window: {e}")

    def get_base64_from_ui(self):
        try:
            pdf_src = self.driver.find_element(
                By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div[2]/div[2]/div/embed").get_attribute('src')  # *ของ reprint
        except:
            pdf_src = self.driver.find_element(
                By.XPATH, "/html/body/div[2]/div[3]/div[10]/div/div[2]/div[2]/div/embed").get_attribute('src')  # * ของ smco
        proc = re.search("(?<=,).*", pdf_src)
        base64_str = proc.group(0)
        return base64_str

    def base64_to_pdf(self, base64_string, pdf_path):
        pdf_bytes = base64.b64decode(base64_string)
        with open(f"{pdf_path}", "wb") as pdf_file:
            pdf_file.write(pdf_bytes)

    def pdf_to_txt(self, pdf_path):
        result = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                result += page.extract_text()
        return result

    def print_pdf(self, pdf_path):
        try:
            os.startfile(f"{pdf_path}", "print")
            print("Printing complete.")
        except OSError as err:
            print(f"No PDF Reader found: {err}")

    def print_pdf_silence(self, pdf_path):
        try:
            win32api.ShellExecute(
                0,
                "print",
                f"{pdf_path}",
                '/d:"%s"' % win32print.GetDefaultPrinter(),
                ".",
                0
            )
            print("Printing via pdf readers silently complete.")
        except OSError as err:
            print(f"(silence_mode)No PDF Reader found: {err}")

    def load_sumatra_cache(self):
        """Load Sumatra PDF path from cache file if it exists and is valid"""
        try:
            if os.path.exists(self.sumatra_cache_file):
                with open(self.sumatra_cache_file, 'r', encoding='utf-8') as f:
                    cached_path = f.read().strip()

                # Verify the cached path still exists
                if cached_path and os.path.isfile(cached_path):
                    self.sumatra_path = cached_path
                    print(f"Loaded Sumatra PDF path from cache: {cached_path}")
                    return True
                else:
                    print("Cached Sumatra PDF path is invalid, will search again")
                    # Delete invalid cache
                    os.remove(self.sumatra_cache_file)
        except Exception as e:
            print(f"Error loading Sumatra PDF cache: {e}")

        return False

    def save_sumatra_cache(self):
        """Save Sumatra PDF path to cache file"""
        try:
            if self.sumatra_path:
                with open(self.sumatra_cache_file, 'w', encoding='utf-8') as f:
                    f.write(self.sumatra_path)
                print(f"Saved Sumatra PDF path to cache: {self.sumatra_path}")
        except Exception as e:
            print(f"Error saving Sumatra PDF cache: {e}")

    def find_sumatra_from_registry(self):
        reg_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ]
        if self.sumatra_path != "":
            return self.sumatra_path

        for reg_root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            for reg_path in reg_paths:
                try:
                    # *เอา path ที่ต่อกันของreg_rootและreg_path มาเปิด แล้วเอาค่าที่เปิดมาเก็บเป็น object เข้า ตัวแปร key ภาษา ui คือ เปิด folder uninstall แต่ใน regedit uninstall เรียกว่า key เพราะมันถูกเก็บเป็น key-value pair
                    with winreg.OpenKey(reg_root, reg_path) as key:
                        # * winreg.QueryInfoKey(key) มันจะ return tuple ที่มีสมาชิก 3 อัน โดยบอกรายละเอียดของkey โดย idx0จะบอก จำนวน subkey(ในui คือfolder ย่อย), idx1บอกว่าkeyนี้มีvalue ไรบ้าง, idx2บอกเวลาที่เปลี่ยนแปลงล่าสุด
                        for i in range(0, winreg.QueryInfoKey(key)[0]):
                            try:
                                # * Enumkey ทำการ return "ชื่อsub_key" ของ key(param1) ที่อยู่ลำดับที่ i(param2)
                                subkey_name = winreg.EnumKey(key, i)
                                # * เหมือน double click ที่ folderที่ชื่อ subkey_name(param2) ที่อยู่ภายใต้ key(param1), as subkey เหมือนหน้าจอใหม่ที่กำลังแสดงค่าภายใน subkey_name(param2)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    # * เป็นการขอเอาค่าออกมจาก sub_keyที่openแล้ว(subkey(param1)), โดยค่าที่เอาออกมานั้นเราจะใส่ค่า value_name ลงไปใน param2 เพื่อที่จะ query เอา value ออกมา ในที่นี้ value_name คือ DisplayName ฉะนั้นมันจะ return value ของ value_name "DisplayName" ภายใต้ subkey ที่กำลังเปิด
                                    display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                    if "SumatraPDF" in display_name:  # * เทียบดิวะรอไร
                                        install_location, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                        exe_path = os.path.join(install_location, "SumatraPDF.exe")
                                        print("smt path: ", exe_path)
                                        if os.path.isfile(exe_path):
                                            self.sumatra_path = exe_path
                                            self.save_sumatra_cache()  # Save to cache
                                            return self.sumatra_path
                            except (FileNotFoundError, OSError, PermissionError, KeyError):
                                continue
                except FileNotFoundError:
                    continue
        print("SumatraPDF was not installed.")
        return None

    def print_pdf_silence_sumatra(self, pdf_path):
        try:
            sumatra_path = self.find_sumatra_from_registry()
            # Use subprocess.run() to wait for completion (blocking)
            result = subprocess.run([sumatra_path, '-print-to-default', pdf_path],
                                    shell=False,
                                    capture_output=True,
                                    timeout=30)  # 30 second timeout
            if result.returncode == 0:
                print("SMT Printing silently complete.")
            else:
                print(f"SMT Printing completed with return code: {result.returncode}")
        except subprocess.TimeoutExpired:
            print("SMT Printing timed out after 30 seconds")
        except Exception as e:
            print(f"sumatra Silent print failed: {e}")

            # Invalidate cache and retry
            if self.sumatra_path:
                print("Invalidating Sumatra PDF cache and searching again...")
                self.sumatra_path = ""
                if os.path.exists(self.sumatra_cache_file):
                    os.remove(self.sumatra_cache_file)

                # Retry finding Sumatra
                sumatra_path = self.find_sumatra_from_registry()
                if sumatra_path:
                    try:
                        result = subprocess.run([sumatra_path, '-print-to-default', pdf_path],
                                                shell=False,
                                                capture_output=True,
                                                timeout=30)
                        if result.returncode == 0:
                            print("SMT Printing silently complete after cache invalidation.")
                        return
                    except Exception as retry_error:
                        print(f"Retry also failed: {retry_error}")

            raise ValueError("Sumatra was not found")

    def operation_start(self):
        self.tracking_manager = TrackingManager(self.driver, self, self.app.marketplace_target.get())
        # ตรวจสอบ driver ก่อนเริ่มทำงาน
        if not self.is_driver_alive():
            error_msg = "WebDriver connection lost. Browser may have crashed or been closed."
            print(error_msg)
            logger.error(f"Order: {self.app.order} - {error_msg}")
            self.app.update_log(error_msg)
            self.app.display_bot_status_label.configure(
                text=f"Bot Status: ❌ Driver Error", fg_color="#ff2b2b", text_color="#FFF")
            raise ConnectionError("WebDriver is not alive. Cannot proceed with operation.")

        self.app.is_bot_browser_busy.set(True)
        self.is_forbid = False
        is_etax = False
        self.is_old_tax_form = False
        self.cus_code = ""
        self.cus_order = self.app.cus_order.get()
        self.tax_info = {}

        #! Memory management - ตรวจสอบและจัดการ memory ก่อนเริ่ม operation อาจจะไม่ต้องใช้ก็ได้ เพราะใช้ใน
        inv_number = ""
        self.operation_states = {"purchased_channel": None}
        if self.app.order != "" and not self.operation_thread.is_set():
            ### * MARKETPLACES Part ########################################################################################
            self.autofinal = False
            print("operation start!! ยังไม่มีไรจะใส่ใส่เป็น placeholderไว้ก่อน")

            # * เปลี่ยนไปtab MARKETPLACES เพื่อเช็ค status (เพราะไม่มี API เลยต้องทำ และเพื่อดูรูปว่ามีของแถมหรือไม่)
            #### * IF MARKETPLACE IS SHOPEE ###################################################################################################################################
            if self.app.marketplace_target.get() == 'SHOPEE':
                while self.is_memory_checking:
                    try:
                        print("Wait For memory checking.....")
                        time.sleep(0.35)
                        continue
                    except:
                        print("Memory checking done.")
                        break
                self.driver.switch_to.window(self.merged_dict['Seller Centre'])
                print("switch to 'Seller Centre'")
                time.sleep(1)
                # self.wait5.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.subaccount-info span.subaccount-name')))
                shopee_sub_account_name_element = self.driver.find_element(
                    By.CSS_SELECTOR, 'div.subaccount-info span.subaccount-name')
                self.operation_states['purchased_channel'] = self.driver.execute_script(
                    "return arguments[0].innerText;", shopee_sub_account_name_element)
                # self.operation_states['purchased_channel'] = self.driver.find_element(By.CSS_SELECTOR, 'div.subaccount-info span.subaccount-name').text
                print(f"self.operation_states['purchased_channel']: {self.operation_states['purchased_channel']}")
                cur_url = self.driver.current_url

                # * เปลี่ยนไปใช้หน้า "ทั้งหมด" เพราะ ในที่หน้าต่างกัน add_new_customer, elements มันต่างกัน บังคับให้มันใช้อันที่ถูก
                if cur_url != "https://seller.shopee.co.th/portal/sale/order":
                    # self.driver.get("https://seller.shopee.co.th/portal/sale/order")
                    # self.driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[4]/div[1]/div/div/div/div[1]/div/div[1]/div[1]/div').click() //ใช้ได้แต่กันไว้ก่อน 25/11/2024 15:11

                    # * ใช้ retry logic เพื่อป้องกัน NoSuchElementException เมื่อ auto_add_product กำลังทำงาน
                    def click_tab():
                        return self.driver.find_element(
                            By.CSS_SELECTOR, 'div.eds-tabs__nav div.eds-tabs__nav-warp div div div.tab-label').click()

                    self.retry_on_stale_element(click_tab)

                else:
                    print("อยู๋ในหน้าทั้งหมดอยู่แล้ว ไม่ต้องเปลี่ยน")

                try:
                    # * กรอก order ลงในช่อง search - ใช้ retry logic เพื่อป้องกัน error จาก auto_add_product
                    def find_search_element():
                        return self.wait50.until(EC.visibility_of_element_located(
                            # (By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[2]/div/div/div[1]/div[1]/div[2]/div[1]/span[2]/div/div[1]/div/div/input'))) เก่า ไม่น่าจะกลับมาใช้แล้ว
                            # (By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div/div[2]/div[1]/div[1]/div[1]/div/span[2]/div/div[1]/div/div/input')))
                            # (By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div/div[2]/div[1]/div/div[1]/div[1]/div/div/span[2]/div/div[1]/div/div/input'))) พัง 28/08/2024 12:00 PM
                            # (By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[4]/div/div/div[2]/div[1]/div/div/div[1]/div[1]/div/div/span[2]/div/div[1]/div/div/input') พัง 19/09/2024 17:00
                            # (By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[5]/div/div/div[2]/div/div[1]/div/div/div[1]/div[1]/div/div/span[2]/div/div[1]/div/div/input') พัง 25/11/2024 15:11
                            (By.CSS_SELECTOR, 'div.eds-input__inner.eds-input__inner--normal input')

                        ))

                    self.search_elmt = self.retry_on_stale_element(find_search_element)

                    self.search_elmt.clear()
                    self.search_elmt.send_keys(self.cus_order)

                    # * กด Search เพื่อ เก็บ Status
                    self.searchBtn = self.driver.find_element(
                        # By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/button[1]') เก่า ไม่น่าจะกลับมาใช้แล้ว
                        # By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div/div[2]/div[1]/div[1]/div[2]/button[1]' พัง 28/08/2024 12:00
                        # By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div/div[2]/div[1]/div/div/div[2]/button[1]' พัง 18/09/2024 14:00
                        # By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[4]/div/div/div[2]/div[1]/div/div/div[2]/button[1]' พัง 19/09/2024 17:00
                        # By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[5]/div/div/div[2]/div/div[1]/div/div/div[2]/button[1]' ใช้ได้อยู่ แต่กันไว้ก่อน พัง 25/11/2024 15:11
                        By.CSS_SELECTOR, 'div.order-search-buttons button.search-btn.eds-button.eds-button--primary.eds-button--normal.eds-button--outline'
                    )
                    self.driver.execute_script("arguments[0].click();", self.searchBtn)
                except:
                    print("cannot search order")
                    tb_str = traceback.format_exc()
                    if "NewConnectionError" in tb_str or "MaxRetryError" in tb_str or "ConnectionRefusedError" in tb_str:
                        print("WebDriver connection lost during search")
                        logger.error(f"Order: {self.app.order} - WebDriver connection lost during search")
                        self.app.update_log("❌ Browser connection lost. Please restart the browser.")
                        raise ConnectionError(f"WebDriver connection lost during operation_start: {tb_str}") from None
                    raise ValueError(f"method operation_start Error : {tb_str}")

                # * ตรวจสอบ Status และ update ของ MARKETPLACE
                time.sleep(1)

                found_order = False
                search_timeout = 10.0
                start_time = time.time()
                while not self.operation_thread.is_set():
                    try:
                        status_el = self.driver.find_elements(By.CLASS_NAME, 'status-wrapper')
                        order_sn_el = self.driver.find_elements(By.XPATH, "//div/span[@class='order-sn']")

                        if (status_el and status_el[0].is_displayed()) or (order_sn_el and order_sn_el[0].is_displayed()):
                            found_order = True
                            print("พบออเดอร์ใน Shopee แล้ว")
                            break
                    except Exception as e:
                        print(f"Error checking Shopee elements: {e}")

                    try:
                        page_text = self.driver.page_source.lower()
                        empty_indicators = ["no data", "ไม่มีข้อมูล", "no orders", "no results"]
                        empty_el = self.driver.find_elements(
                            By.CSS_SELECTOR, ".eds-empty, .empty-wrapper, .no-orders, .no-data")

                        if (empty_el and any(el.is_displayed() for el in empty_el)) or any(ind in page_text for ind in empty_indicators):
                            print("ตรวจพบหน้าว่างเปล่า (ไม่พบออเดอร์) ใน Shopee")
                            break
                    except:
                        pass

                    if time.time() - start_time > search_timeout:
                        print("หมดเวลารอผลลัพธ์การค้นหาใน Shopee")
                        break
                    time.sleep(0.5)

                if not found_order:
                    error_msg = f"ไม่พบออเดอร์ {self.cus_order} ในระบบ Shopee หรือค้นหาไม่สำเร็จ"
                    self.app.update_log(f"❌ {error_msg}")
                    raise ValueError(error_msg)

                # *>  ต้องใช้ try except เพราะ element ของ shopee มันดันแบ่งเป็นสองแบบหากมีสถานะ order ที่ต่างกัน แทนที่จะเขียนให้เหมือนกัน ยุ่งยากกว่าเดิม
                try:
                    # * สำหรับ หาข้อความ "ที่ต้องจัดส่ง" ต่อให้มี element ที่บรรจุคำว่า "จะถูกยกเลินใน x วัน" หรือ "การจัดส่งช้า" ตราบใดที่ข้างล่างมี ที่ต้องจัดส่ง จะมี class big-text เสมอ
                    self.app.cus_cur_status.set(self.driver.find_element(By.CLASS_NAME, 'status-wrapper').text)

                except:
                    # * elementจะแสดงตาม DOM DIR นี้ ถ้าหาก ดูในหน้า ทั้งหมด สำหรับ Order ที่มีสถานะ "ส่งสินค้าแล้ว", "ยกเลิกแล้ว", "สำเร็จ"
                    self.app.cus_cur_status.set(self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[4]/div/div/div[2]/div[4]/div/div[2]/a/div[2]/div/div/div[3]/div/div[1]/span').text)

                # * จะได้ element มา
                self.app.display_current_status.configure(text_color="#000000", fg_color="#8fd4ff")
                if self.app.cus_cur_status.get() == "ส่งสินค้าแล้ว":
                    self.app.display_current_status.configure(fg_color="#00ff11", text_color="#000000")
                    self.app.POP_UP.show(
                        "Caution!!", f"Order {self.app.order} มีสถานะ '{self.app.cus_cur_status.get()}'", "alert")
                    logger.info(f"Order: {self.app.order} has status: '{self.app.cus_cur_status.get()}'")

                elif "ยกเลิก" in self.app.cus_cur_status.get():
                    self.app.display_current_status.configure(fg_color="#ff2b2b", text_color="#FFF")
                    self.is_forbid = True
                    #! WIP accel_mode[3] ถ้าเป็น accel mode อาจจะไม่ต้องใช้ popup แต่ใช้เป็นการเก็บผลลัพธ์การทำงานแทน
                    self.app.POP_UP.show(
                        "Caution!!", f"Order {self.app.order} มีสถานะ '{self.app.cus_cur_status.get()}'", "alert")
                    logger.info(f"Order: {self.app.order} has status: '{self.app.cus_cur_status.get()}'")

                self.is_status_true = self.app.order_status == self.app.cus_cur_status.get()
                if self.is_status_true:
                    print(self.app.order_status == self.app.cus_cur_status.get())
                    print("Status in the file is reliable")
                else:
                    print(self.app.order_status == self.app.cus_cur_status.get())
                    print("Status in the file is unreliable, suggest downloading a new Export File from the link below")
                    print("https://seller.shopee.co.th/portal/sale/shipment?type=toship")

                # * สำหรับโหมด auto_invoice_mode ให้กรองเฉพาะออเดอร์สถานะ "ที่ต้องจัดส่ง"
                if hasattr(self.app, 'is_auto_invoice_mode') and self.app.is_auto_invoice_mode.get():
                    shopee_status = self.app.cus_cur_status.get().strip()
                    if not shopee_status:
                        raise ValueError("ไม่สามารถระบุสถานะออเดอร์ Shopee ได้ (ค่าสถานะเป็นค่าว่าง)")

                    if shopee_status != "ที่ต้องจัดส่ง":
                        if "ยังไม่ชำระ" in shopee_status:
                            error_msg = f"ออเดอร์มีสถานะ '{shopee_status}' (ถือว่า Failed ตามเงื่อนไข)"
                            self.app.update_log(f"❌ {error_msg}")
                            raise ValueError(error_msg)
                        else:
                            success_msg = f"ข้ามออเดอร์ (สถานะ: {shopee_status}) ถือว่า Complete ตามเงื่อนไข"
                            self.app.update_log(f"✅ {success_msg}")
                            if hasattr(self.app, 'accel_mode'):
                                if hasattr(self.app.accel_mode, 'deduct_accel_file_data'):
                                    try:
                                        self.app.accel_mode.deduct_accel_file_data(self.app.cus_order, remove_order=True)
                                    except Exception as xl_err:
                                        logger.warning(f"ไม่สามารถ deduct order จาก Sheet1 ได้: {xl_err}")
                                if hasattr(self.app.accel_mode, 'record_completed_order'):
                                    self.app.accel_mode.record_completed_order(
                                        self.app.cus_order, status=f"ข้าม (สถานะ: {shopee_status})")
                            return

            #### * IF MARKETPLACE IS LAZADA ###########################################################################################################################
            elif self.app.marketplace_target.get() == 'LAZADA':
                try:
                    self.driver.switch_to.window(self.merged_dict['การจัดการคำสั่งซื้อ - Lazada Seller Center'])
                except:
                    self.driver.switch_to.window(self.merged_dict['การจัดการคำสั่งซื้อ - Seller Center'])

                cur_url = self.driver.current_url

                # * เปลี่ยนไปใช้หน้า "ทั้งหมด" เพราะ ในที่หน้าต่างกัน css, elements มันต่างกัน บังคับให้มันใช้อันที่ถูก
                if cur_url != "https://sellercenter.lazada.co.th/apps/order/list?oldVersion=1&spm=a1zawg.23708326.navi_left_sidebar.droot_normal_ordersreviews_ordersnewui.3fa34edfUCdGFY&status=all":
                    self.driver.find_element(
                        By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/div[2]/div/div[1]/div/div/div/ul/li[1]/div').click()
                    time.sleep(0.75)
                    self.wait50.until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             '/html/body/div/section/div[2]/div/div[1]/div/div/div[3]/div/div[3]/div[1]/div[1]/div[2]/div[2]/span[1]/span[2]/span/a'
                             )))

                # * กรอก order ลงในช่อง search
                laz_order_input_path = "//span[@class='next-select-trigger-search']/input[@role='combobox' and @name='orderNumbers']"
                self.search_elmt = self.wait50.until(EC.visibility_of_element_located((By.XPATH, laz_order_input_path)))
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

                # * ตรวจสอบ Status และ update
                found_order = False
                search_timeout = 10.0
                start_time = time.time()
                status_btn_xpath = '/html/body/div/section/div[2]/div/div[1]/div/div/div[3]/div/div[3]/div/div[2]/div/div/div[5]/div[1]/button'

                while not self.operation_thread.is_set():
                    try:
                        status_el = self.driver.find_elements(By.XPATH, status_btn_xpath)
                        if status_el and status_el[0].is_displayed():
                            found_order = True
                            print("พบออเดอร์ใน Lazada แล้ว")
                            break
                    except Exception as e:
                        print(f"Error checking Lazada elements: {e}")

                    try:
                        page_text = self.driver.page_source.lower()
                        empty_el = self.driver.find_elements(By.CSS_SELECTOR, ".next-table-empty, .empty, .no-data")

                        if (empty_el and any(el.is_displayed() for el in empty_el)) or "ไม่มีข้อมูล" in page_text or "no data" in page_text:
                            print("ตรวจพบหน้าว่างเปล่า (ไม่พบออเดอร์) ใน Lazada")
                            break
                    except:
                        pass

                    if time.time() - start_time > search_timeout:
                        print("หมดเวลารอผลลัพธ์การค้นหาใน Lazada")
                        break
                    time.sleep(0.5)

                if not found_order:
                    error_msg = f"ไม่พบออเดอร์ {self.cus_order} ในระบบ Lazada หรือค้นหาไม่สำเร็จ"
                    self.app.update_log(f"❌ {error_msg}")
                    raise ValueError(error_msg)

                # เก็บ status order เข้าตัวแปรไปแสดงผลใน GUI
                self.app.cus_cur_status.set(self.driver.find_element(
                    By.XPATH, status_btn_xpath + '/span').text)

                # จะได้ element มา
                print("realtime_status_text", self.app.cus_cur_status.get())
                self.app.display_current_status.configure(text_color="#000000", fg_color="#8fd4ff")
                if "พิมพ์ใบแจ้งหนี้" in self.app.cus_cur_status.get() or "ยกเลิก" in self.app.cus_cur_status.get():
                    self.app.display_current_status.configure(fg_color="#ff2b2b", text_color="#FFF")
                    self.is_forbid = True
                elif self.app.cus_cur_status.get() == "สถานะการจัดส่ง":
                    self.app.display_current_status.configure(fg_color="#00ff11", text_color="#000000")

            #### * IF MARKETPLACE NON OF THEM ABOVE ###################################################################################################################
            else:
                self.driver.switch_to.window(self.merged_dict[''])
                print('Cannot Define What marketplace you are working with')

            # * ถ้าสถานะยกเลิก ก็หยุดเลย
            if self.is_forbid:
                print("This order was forbidden.")
                if hasattr(self.app, 'accel_mode') and self.app.is_accel_mode_activated.get():
                    try:
                        self.app.accel_mode.deduct_accel_file_data(self.app.cus_order, remove_order=True)
                        self.app.accel_mode.record_failed_order(
                            self.app.cus_order, f"ยกเลิก (สถานะ: {self.app.cus_cur_status.get()})")
                    except Exception as xl_err:
                        print("Accel mode delete/log order failed:", xl_err)
                        logger.error(f"Accel mode delete/log order failed: {xl_err}")
                self.app.display_bot_status_label.configure(
                    text=f"Bot Status: ˶ᵔ ᵕ ᵔ˶ จบการทำงาน", fg_color="#d9f2ff", text_color="#000")
                return

            ### * SMCO PART ############################################################################
            # * เปลี่ยนไปtab SMCO0 เพื่อเช็ค ชื่อลูกค้า
            try:
                self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
                current_url = self.driver.current_url
                matched_str = re.search(r'\/[A-z].*', current_url).group()
                self.origin = current_url.replace(matched_str, '')
                print("SMCO :: เปิดการขาย ไม่หาย ไปต่อ")
                logger.info(f"{self.cus_order}: SMCO :: เปิดการขาย ไม่หาย ไปต่อ")
            except:  # * กรณีหน้าเปิดการขายมันหายไป
                print("SMCO :: เปิดการขาย หายไป เปิดใหม่")
                logger.info(f"{self.cus_order}: SMCO :: เปิดการขาย หายไป เปิดใหม่")
                self.driver.execute_script("window.open('');")
                all_handles = self.driver.window_handles
                new_handle = all_handles[-1]  # tab ใหม่ล่าสุด
                self.driver.switch_to.window(new_handle)
                self.driver.get(f"{self.origin}/smartcore/smartpos/pointofsales/posmainv3.htm")
                self.get_tabs()
                self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])

            # self.smco_handler.insert_emp()
            # self.smco_handler.select_sale_type()

            # * เลือก ประเภทการขาย ==========================================================================
            self.select_sale_type()

            # * มันจะมี pop-up เด้งระหว่างนี้
            try:
                self.driver.find_element(
                    By.XPATH,
                    "//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]").click()
            except:
                print("no sale type pop-up")

            # * ใส่ รหัสพนักงาน ===============================================================================
            self.insert_emp()

            # * ดูก่อนว่าเคลียชื่อลูกค้าแล้วเหรอยัง
            # self.cus_name_dropdown_elmt_loc = '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/div[2]/form/div/span/span[1]/span/span[1]'
            self.cus_name_dropdown_elmt_loc = '//span[@id="select2-memberSearch-container"]'
            self.cus_name_span_x_btn_text = ""
            self.is_reset = False

            # Todo ทดสอบก่อน
            # * เปิด form ใส่ชื่อลูกค้าแบบเก่า
            # self.open_old_tax_form()
            while not self.operation_thread.is_set():
                try:
                    self.cus_name_span_elmt = self.driver.find_element(By.XPATH, self.cus_name_dropdown_elmt_loc)
                    self.cus_name_span_x_btn_text = self.cus_name_span_elmt.text
                    print("found element cus_name_span_elmt ")
                    break
                except:
                    print("finding element cus_name_span_elmt")
                    time.sleep(0.5)
                    continue

            # * เพราะวิธีออกใบกำกับมันยังไม่แน่นอนมีทั้งแบบเก่าและแบบใหม่ แบบเก่ามันจะทำโดยขั้นตอนด้านล่างนี่ แต่ถ้าเป็นแบบใหม่มันจะย้ายไปทำหน้าท้าย ซึ่งไม่รู้จะย้ายไปไม
            self.is_old_tax_form = False
            if self.driver.find_element(By.XPATH, self.cus_name_dropdown_elmt_loc).is_displayed():
                self.is_old_tax_form = True
                print("element cus_name_span_elmt is displayed")

                if self.cus_name_span_x_btn_text == 'Please select':
                    self.is_reset = False
                elif self.cus_name_span_x_btn_text == 'กรุณาเลือก':
                    self.is_reset = False
                else:
                    self.is_reset = True
                    print("มีชื่อลูกค้าอยู่แล้ว")
                    #! แบบใหม่ยังไม่ต้องรีบใช้
                    # self.cus_name_span = self.driver.find_element(
                    #     By.XPATH, "//span[@id='select2-memberSearch-container']")
                    # if not self.app.is_tax_required.get() and "CWI99" in self.cus_name_span.get_attribute("title"):
                    #     self.is_reset = False
                    #     print("มีชื่อลูกค้าที่เหมาะสมอยู่แล้วไม่ต้องรี")
                    # else:
                    #     self.is_reset = True
                    #     print("มีชื่อลูกค้าอยู่แล้ว")

                try:
                    print("เช็คว่าต้องรีไหม", self.is_reset)
                    if self.is_reset:
                        print("รีนี่หว่า, กดรีเลย")
                        self.driver.find_element(By.XPATH, self.cus_name_dropdown_elmt_loc).click()
                        items_list = self.driver.find_elements(
                            By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
                        if len(items_list) == 0:
                            # * คลิกเพื่อให้ปิด droprdown
                            self.driver.find_element(By.XPATH, self.cus_name_dropdown_elmt_loc).click()
                            print("ปิด dropwdown กรณีไม่มีสินค้า")
                        else:
                            # * ถ้ามีสินค้าจะ error คลิกไม่ได้จะกลายเป็น except
                            print("กรณีมีสินค้า")
                            self.driver.find_element(
                                By.XPATH, '//span[@id="select2-memberSearch-container"]/span').click()
                            try:
                                print("wait for pop-up(try)")
                                # ระบุปุ่ม ok
                                if self.driver.find_element(
                                        By.XPATH,
                                        """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]"""):
                                    print("has pop-up(try)")
                                    self.driver.find_element(
                                        By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]""").click()
                                    print("Click OK(try)")
                            except:
                                print("wait for pop-up(except)")
                                time.sleep(1)
                                # * ระบุปุ่ม ok
                                if self.driver.find_element(
                                        By.XPATH,
                                        """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]"""):
                                    print("has pop-up(except)")
                                    self.driver.find_element(
                                        By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]""").click()
                                    print("Click OK(except)")
                            # * ถ้ามีสินค้าแล้วกดลบชื่อ มันจะมีชื่อค้างอยู่แต่สินค้าหายต้องกดอีกรอบ
                            try:
                                self.driver.find_element(By.XPATH, self.cus_name_dropdown_elmt_loc).click()
                                print("Cusname still appear, the btn 'x' is available.")
                            except:
                                print("Cusname has disappeared, no 'x' to press.")

                        print("หน้าใหม่พร้อมแล้ว")
                    elif self.is_reset == False:
                        print("ไม่ต้องรี")
                except Exception as err:
                    # * กดปุ่ม Reset มุมขวาบนเพื่อ Reset หน้าเว็บใหม่
                    print("Error From SMCO phase1 Resetting", err)
                    logger.info("Error From SMCO phase1 Resetting", err)
                    while not self.operation_thread.is_set():
                        print("รอ")
                        time.sleep(1)
                        if self.driver.find_element(
                                By.XPATH, '//div[@class="btn-outline pull-right"]//button[@id="create"]'):
                            print("เจอแล้ว")
                            break
                        else:
                            continue

                print("ผ่านเคลียชื่อลูกค้า, รอ element โผล่")

                # * เลือก filter การ query ลูกค้า ==========================================================================
                # * /html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/div[1]/div/div/button
                # self.wait50.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/button')))
                self.wait50.until(EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@ng-show, 'abbCustomerFlag')]//div[contains(@class, 'input-group-prepend')]/button")))

                time.sleep(1)

                # * จากปัญหาข้อที่ 39 // รอให้ตัวเลือกภายใน click ได้ก่อน แล้วค่อย เลือก วิธีการ searchs
                self.set_cus_name_search_type()

                # * ดูว่า self.cus_search_input จะต้องถูกกำหนดค่าเป็นเลขใบกำกับหรือชื่อ อิงจาก tax_bool choosing by ternary like conditional
                # 09/11/2023 ใช้เลขใบกำกับเสิชไม่ได้แล้ว ฉะนั้นไม่ต้องเลือกแล้ว เอาชื่อเสิชให้หมดเลย

                # if self.app.marketplace_target.get() == "SHOPEE":
                #     self.cus_search_input = self.app.cus_email.get() if self.app.is_tax_required.get(
                #     ) else self.app.cus_name_cleaner(self.app.cus_name.get(), self.app.cus_account_name.get())
                # elif self.app.marketplace_target.get() == "LAZADA":
                #     self.cus_search_input = self.app.tax_num.get() if self.app.is_tax_required.get(
                #     ) else self.app.cus_name_cleaner(self.app.cus_name.get(), self.app.cus_account_name.get())

                # * 05/07/2024 Shopeeนั้นได้ลบ ชื่อลูกค้าแบบ ธรรมดา ออกไปอย่างถาวร จึงต้องปรับวิธีออกบิลให้กับแบบธรรมดาโดยการใช้ "account"+" ชื่อที่เป็นดอกจัน"+" หมายเลขโทรศัพท์"
                # self.cus_search_input = self.app.tax_num.get() if self.app.is_tax_required.get(
                # ) else self.app.cus_name_cleaner(self.app.cus_name.get(), self.app.cus_account_name.get())

                if self.app.marketplace_target.get() == "SHOPEE":
                    #! ver ต่ำกว่า 8.0.0
                    self.cus_search_input = self.app.tax_num.get() if self.app.is_tax_required.get(
                    ) else self.app.cus_name_cleaner(self.app.cus_name.get())
                    # / ver 8.0.0 ขึ้นไป
                    # self.cus_search_input = self.app.tax_num.get() if self.app.is_tax_required.get() else "CWI99"
                elif self.app.marketplace_target.get() == "LAZADA":
                    self.cus_search_input = self.app.tax_num.get() if self.app.is_tax_required.get(
                    ) else self.app.cus_name_cleaner(self.app.cus_name.get(), self.app.cus_account_name.get())
                    # self.cus_search_input = self.app.tax_num.get() if self.app.is_tax_required.get() else "CWI99"

                # * เริ่มกระบวนการหาชื่อลูกค้าสำหรับออกบิล invoice
                if not self.cus_search_input in self.driver.find_element(
                        By.CSS_SELECTOR, "#select2-memberSearch-container").get_attribute("title"):
                    self.get_customer_name_ready(self.cus_search_input)
                self.current_checkpoint = "ใส่ชื่อลูกค้าสำเร็จ"

                # * ใส่ตัวเช็คที่อยู่ลูกค้า
                if self.app.is_tax_required.get():
                    print("tax required, start address check and correct")
                    self.cus_name_span = self.driver.find_element(
                        By.XPATH, "//span[@id='select2-memberSearch-container']")
                    # * ที่กล้าเก็บค่า attribute มาใช้ตรงๆแบบนี้เพราะต่อให้ไม่มี attribute มันก็ return ค่าว่างอยู่ดี ซึ่งปกติ element นี้จะแสดง attribute title ด้วยถ้ามีการเลือกที่อยู่ลูกค้าแล้ว ถ้าไม่เลือก attribute title จะไม่แสดงใน html
                    self.text_from_name_span = self.cus_name_span.get_attribute("title")
                    self.tax_address_corrector(self.text_from_name_span)
                    self.current_checkpoint = "ตรวจสอบ/แก้ไขที่อยู่สำเร็จ"

                else:
                    print("no tax required, skip address check")
                    self.current_checkpoint = "ข้ามการตรวจที่อยู่ (ไม่ต้องใช้ภาษี)"

            # เคลียร์ข้อมูลสินค้าเดิมที่อาจค้างอยู่ในหน้ารถเข็น POS ก่อนแอดของและค่าขนส่งใหม่
            if self.app.is_auto_invoice_mode.get():
                try:
                    print("Checking for existing items in cart to clear before adding new items...")
                    while not self.operation_thread.is_set():
                        delete_buttons = self.driver.find_elements(
                            By.XPATH, "//div[contains(@class, 'panel')]//button[@class='btn btn-danger btn-sm ng-scope']"
                        )
                        if not delete_buttons:
                            break
                        print("Clearing an existing item from POS cart...")
                        self.driver.execute_script("arguments[0].click();", delete_buttons[0])
                        time.sleep(0.8)  # รอให้รายการนั้นหายไปและ DOM โหลดเสร็จ
                    self.current_checkpoint = "เคลียร์สินค้าค้างตะกร้าสำเร็จ"
                except Exception as e:
                    print(f"Error during cart clearing: {e}")

            # / ใส่ค่าขนส่ง ================================================================================
            # / ค่าขนส่งเราจะใส่ให้ SHOPEE เท่านั้น
            if self.app.marketplace_target.get() == "SHOPEE":
                self.add_shipping_cost()
                self.current_checkpoint = "ใส่ค่าขนส่งสำเร็จ"

            ### PHASE2 After Add Product###############################################################################################################
            # # #เช็คของเติม CP อัตโนมัติ กำลังทำ ถ้าเอาไปใส่ใน while loop ข้างล่างมันจะบัค ไม่สามารถแปลงเป็น float ได้
            # while not self.operation_thread.is_set():
            #     self.phase1_net_price = self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[2]/div/div/div/div/span[1]')
            #     self.phase1_net_price = float(self.phase1_net_price.text)
            #     if self.app.phase1_sum_price != self.phase1_net_price:
            #         print("ราคาไม่ตรง", self.app.phase1_sum_price,  " = ",self.phase1_net_price)
            #         continue
            #     else:
            #         print("ราคาตรงแล้ว")
            #         break

            #! WIP ทดสอบ 2/2
            # logger.info(f"Order: {self.app.order} 2/2Finished!!")
            # self.app.search_complete.set()
            # return

            # * Add SKU จากไฟล์ Accel mode
            # if self.app.is_accel_mode_activated.get():
            if len(self.app.accel_mode.accel_df_state) > 0:
                self.app.accel_mode.accel_fill_sku(self.driver, self.operation_thread)
                self.current_checkpoint = "กรอกสินค้า Accel สำเร็จ"

            if self.app.is_auto_invoice_mode.get():
                try:
                    self.ProductManager.auto_add_all_items()
                    self.current_checkpoint = "กรอกสินค้าลง POS สำเร็จ"

                    verification_result = self.ProductManager.verify_all()
                    print("verification_result: ", verification_result)
                    self.current_checkpoint = "ตรวจสอบราคาและจำนวนสำเร็จ"

                    # * ตรวจสอบความแตกต่างของราคาสินค้าแต่ละ SKU และเรียกใช้คูปองหากมีส่วนต่าง
                    self.process_price_mismatches(verification_result)
                    self.current_checkpoint = "ปรับราคา/ใส่คูปองสำเร็จ (จบ process ปรับราคา)"

                    # * ตรวจสอบราคาอีกครั้งหลังปรับราคา
                    self.app.update_log("🔍 กำลังตรวจสอบราคาและจำนวนสินค้าอีกครั้งหลังปรับราคา...")
                    post_verification = self.ProductManager.verify_all()
                    print("post_verification_result: ", post_verification)

                    if post_verification.get("all_ok"):
                        self.app.update_log("✅ ตรวจสอบราคาสำเร็จและถูกต้อง (All OK). กำลังดำเนินการออกบิล...")
                        self.app.finish_order()
                        self.current_checkpoint = "ออกบิลเรียบร้อย"

                        # * ตรวจสอบ popup แจ้งเตือน (กรณีสินค้ายังไม่มี serial) สำหรับ accelmode + auto_inv
                        if self.app.is_accel_mode.get() and self.app.is_auto_invoice_mode.get():
                            time.sleep(1.5)  # รอให้ popup โชว์
                            warning_popups = self.driver.find_elements(
                                By.XPATH, "//div[contains(@class, 'swal2-icon') and contains(@class, 'swal2-warning') and contains(@class, 'pulse-warning')]"
                            )
                            has_warning = False
                            for popup in warning_popups:
                                try:
                                    style_attr = popup.get_attribute("style") or ""
                                    if "display: block" in style_attr or "display:block" in style_attr:
                                        has_warning = True
                                        break
                                except:
                                    pass

                            if has_warning:
                                err_msg = "พบป๊อปอัปแจ้งเตือน แต่ไม่พบข้อความผิดพลาด"
                                content_elems = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'swal2-content')]")
                                for content in content_elems:
                                    try:
                                        content_style = content.get_attribute("style") or ""
                                        if "display: block" in content_style or "display:block" in content_style:
                                            err_msg = content.text
                                            break
                                    except:
                                        pass

                                # ปิด Swal popup เพื่อไม่ให้กีดขวางขั้นตอนถัดไป
                                try:
                                    swal_ok = self.driver.find_element(
                                        By.XPATH,
                                        "//button[contains(@class, 'swal2-confirm') and (text()='OK' or text()='ตกลง')]"
                                    )
                                    if swal_ok.is_displayed():
                                        self.driver.execute_script("arguments[0].click();", swal_ok)
                                        print("ปิด Swal popup สำเร็จ")
                                except:
                                    pass

                                self.app.update_log(f"❌ พบข้อผิดพลาดจากป๊อปอัป: {err_msg}")
                                raise ValueError(err_msg)
                    else:
                        qty_errors = []
                        qty_res = post_verification.get("qty", {})
                        for sku, info in qty_res.items():
                            if not info.get("ok", True):
                                qty_errors.append(f"SKU Qty mismatch: {sku} (expected {info.get('expected')}, actual {info.get('actual')})")

                        price_errors = []
                        price_res = post_verification.get("price", {})
                        for sku, info in price_res.items():
                            if not info.get("ok", True):
                                price_errors.append(
                                    f"SKU Price mismatch: {sku} (expected {info.get('expected')}, actual {info.get('actual')}, diff {info.get('diff')})"
                                )

                        total_errors = []
                        total_res = post_verification.get("total", {})
                        if not total_res.get("ok", True):
                            total_errors.append(f"Total Price mismatch (expected {total_res.get('expected')}, actual {total_res.get('actual')})")

                        all_errors = qty_errors + price_errors + total_errors
                        error_msg = f"ราคา/จำนวนไม่ตรงหลังปรับราคา: " + " | ".join(all_errors)
                        self.app.update_log(f"❌ {error_msg}")
                        raise ValueError(error_msg)
                except Exception as err:
                    err_str = str(err).lower()
                    if "connection refused" in err_str or "target machine actively refused it" in err_str or "max retries exceeded" in err_str or "winerror 10061" in err_str:
                        print(f"Connection lost during adding items: {err}")
                        logger.error(f"Connection lost during adding items: {err}")
                        self.app.update_log("⚠️ Session lost while adding items. Attempting to reconnect...")
                        self.reconnect_driver()
                        self.app.update_log("⚠️ Reconnected. Please check the items manually.")
                    else:
                        print(f"Error occurred while verifying items: {err}")
                        logger.error(f"Error occurred while verifying items: {err}")
                        self.record_failed_with_checkpoint(str(err))
                        raise err

            self.app.update_log("Autoหน้าแรก มันจบแค่นี้ ยิงของ, ใส่คูปอง, กดไปหน้าถัดไปได้เลย")
            self.app.display_bot_status_label.configure(
                text=f"Bot Status: Your Turn", fg_color="#21ff29", text_color="#000")

            # todo for testing
            # * Update Accel file //////////////////////
            if self.app.is_testing:
                logger.info(
                    f"Order: {self.cus_order} Testing mode is ON. Attempting to update Accel file with order data.")
                try:
                    self.app.accel_mode.deduct_accel_file_data(
                        self.app.cus_order, getattr(self.app.accel_mode, "used_serials", []))
                    self.app.accel_mode.record_completed_order(
                        self.app.cus_order, status="TEST_SUCCESS (จบ process ปรับราคา)")

                except Exception as err:
                    logger.info(f"test: cannot excute: self.app.accel_mode.deduct_accel_file_data(): {err}")

                logger.info(f"""Order: {self.cus_order} Testing End!!""")
                return

            self.current_checkpoint = "เข้าสู่หน้าจอสรุปออเดอร์แล้ว"

            # with self.driver_lock:
            #! use decorator get_tabs() ก่อนแล้วค่อยให้ thread ทำงาน
            # / หน้าท้าย ================================================================================
            self.autofinal = True
            while self.autofinal and not self.operation_thread.is_set():
                self.app.is_bot_browser_busy.set(False)
                print("Enter final loop")
                print("Waiting for element to appear")
                while self.parent.winfo_exists() and not self.operation_thread.is_set():
                    time.sleep(0.55)
                    while not self.operation_thread.is_set():
                        # * รอ elementก่อน ถ้ามีค่อยออกจาก loop
                        try:
                            self.saler_name_input_element = self.driver.find_element(
                                By.CSS_SELECTOR, '#select2-salePersonSearch-container'
                            )
                            title_attribute = self.saler_name_input_element.get_attribute("title")

                            # * ตรวจสอบว่าหน้าสุดท้ายหรือยัง
                            some_last_page_text_element_xpath = "//*[contains(text(),' Payment: ') or  contains(text(), 'ชำระเงิน:') or contains(text(), 'CN Reason')]"
                            is_final_page_displayed = self.driver.find_element(
                                By.XPATH, some_last_page_text_element_xpath).is_displayed()
                            break
                        except InvalidSessionIdException:
                            print("Invalid session ID. Attempting to relaunch driver.")
                            self.app.update_log("❌ Browser session lost. Attempting to relaunch the browser...")
                            logger.error(f"Order: {self.cus_order} - Browser session lost during final page wait loop.")
                            self.reconnect_driver()
                            try:
                                self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
                            except Exception as sw_err:
                                print(f"Cannot switch to SMCO window after reconnect: {sw_err}")
                            time.sleep(1)
                            continue  # Retry finding the element after relaunching the driver

                        except Exception as err:
                            err_str = str(err).lower()
                            if "target window already closed" in err_str or "no such window" in err_str:
                                print("Browser window is closed. Exiting wait loop.")
                                self.autofinal = False  # Stop the outer loop too
                                break  # Exit the element search loop
                            else:
                                print(
                                    f"cannot see elements from final page, waiting... Error details: {type(err).__name__}")
                                # * ไม่มี element ให้วนเรื่อยๆ
                                time.sleep(1)
                                continue

                    # *ดึงตัวอักษรออกมา
                    #! matched_obj = re.search("^C[0-9]+", title_attribute) เลิกใช้ เพราะบางชื่อมันไม่ขึ้นต้นด้วย C
                    matched_obj = re.search(r"^[A-Z0-9?]+", title_attribute)
                    try:
                        self.emp_name_from_element = matched_obj.group()
                    except:
                        self.emp_name_from_element = ""

                    # * หน้ารายการยิงของ (หน้าแรก)
                    # ! Deprecated
                    # * /update/ แต่สมัยนี้มันไม่มีหน้า SN แล้วนี่หว่า มันย้ายไปเปนหน้าใหม่เลย popup-sn เลยหายไปละ /ปัญหา/แก้ bot ดับจาก alert หน้ารายการยิงของ (หน้าแรก)
                    # while not self.operation_thread.is_set():
                    #     time.sleep(0.55)
                    #     try:
                    #         sn_window = self.driver.find_element(
                    #             By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[7]/div/div/div[1]')  # * ส่วนลด pop up
                    #         # print("SN_window is still there")
                    #         if sn_window.is_displayed():
                    #             # print("หน้า SN กำลังโชว์")
                    #             # if self.driver.find_element(By.XPATH, self.cus_name_dropdown_elmt_loc).is_displayed():
                    #             continue

                    #         else:
                    #             # print("หน้า SN ไม่ได้โชว์")
                    #             break
                    #     except Exception as err:
                    #         # self.alert_text = self.driver.switch_to.alert.text ใช้ไม่ได้
                    #         # print("alertทั้งหมดคือไร", err)
                    #         print("Show only the part of obj err", err)
                    #         # self.app.POP_UP.show("SN Duplicate", f'{err}', "alert")
                    #         # self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
                    #         # WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                    #         # print("Popupโผล่")
                    #         continue

                    # * เอาไว้ใช้เพื่อจบการทำงาน เมื่ออกบืล เดิมทีค่าที่เป็นชื่อลูกค้ามันจะหายไป แต่ปัจจุบันไม่มีชื่อลูกค้าแล้ว เลยไปใช้ชื่อพนักงาน แต่ชื่อพนักงานมันจะหายไหมนะ?
                    if self.emp_name_from_element == "" and is_final_page_displayed == False:
                        print("Emp name disappeared")
                        break
                    elif (not "Select " in self.saler_name_input_element.get_attribute("title") or not "กรุณาเลือก" in self.saler_name_input_element.get_attribute("title")) and is_final_page_displayed == False:
                        continue
                    elif (not "Select " in self.saler_name_input_element.get_attribute("title") or not "กรุณาเลือก" in self.saler_name_input_element.get_attribute("title")) and is_final_page_displayed == True:
                        self.app.is_bot_browser_busy.set(True)
                        time.sleep(0.55)
                        print("Page Payment")

                        # ? ลองของใหม่
                        if not hasattr(self, "last_page") or not isinstance(self.last_page, WebElement):
                            print("ไม่เคยตเข้า last_page มาก่อน")
                            reload = True
                        else:
                            try:
                                _ = self.last_page.text
                                print("มี last_page อยู่แล้ว")
                                reload = False
                            except Exception as err:
                                print("last_page เก่า ใช้ไม่ได้  ต้องโหลดใหม่")
                                print(err)
                                reload = True

                        if reload:
                            print("โหลด last_page ใหม่")
                            while not self.operation_thread.is_set():
                                try:
                                    self.last_page = self.driver.find_element(
                                        By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[1]/span[1]'
                                    )
                                    print("โหลด last_page สำเร็จ")
                                    break
                                except Exception as e:
                                    print("Cannot reload last_page element:", e)
                                    continue

                        if (self.last_page.text == "Payment:") or (self.last_page.text == "ชำระเงิน:"):
                            # Auto หน้าท้าย ทำได้ครั้งเดียว

                            # is_final_page = self.wait50.until(EC.visibility_of_element_located(
                            #     (By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[1]/div[5]/div[1]/textarea')))
                            try:
                                #! deprecated
                                # * กรอก seller voucher
                                # if self.app.cus_seller_voucher.get():
                                #     # ถ้ามี เซลเลอร์ให้ ให้กรอกให้ด้วย
                                #     self.driver.find_element(
                                #         By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[1]/div[5]/div[3]/div[1]/div[2]/input').clear()
                                #     self.driver.find_element(
                                #         By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[1]/div[5]/div[3]/div[1]/div[2]/input').send_keys(self.app.cus_seller_voucher.get())

                                # * /กรอก remark
                                time.sleep(0.75)
                                remark_text = self.cus_order
                                textarea_element = self.driver.find_element(
                                    By.XPATH, "//div[@class='col-sm-4 nopadding']/textarea[@ng-model='posPaymentHead.data.cnRemark']")

                                self.tracking_manager.collect_tracking(remark_text)
                                self.tracking_manager.apply_tracking_to_final_page()

                                # / Final way ใช้ function ที่เขียนแยกไว้
                                self.js_input_value(textarea_element, remark_text)

                                # / เลือกประเภทชำระเงิน และ กำหนด final price (โดยดูตาม marketplace ว่าเป็น shopee หรือ lazada เพราะค่าที่ต้องใส่จะต่างกัน)
                                time.sleep(0.75)
                                final_price = 0
                                if self.app.marketplace_target.get() == 'SHOPEE':
                                    final_price = (self.app.sum_price + self.app.cus_ship_cost.get()
                                                   ) - self.app.cus_seller_voucher.get()
                                    try:
                                        channel = self.channel_options[f'{self.operation_states['purchased_channel']}']
                                        print("channel: ", channel)
                                        # / เลือก shopee
                                        payment_type_btn_element = self.driver.find_element(
                                            # By.XPATH, f"//a[contains(., '{channel}')]")
                                            By.XPATH, f"//a//label[text()='{channel}']")
                                        self.driver.execute_script("arguments[0].click();", payment_type_btn_element)
                                    except Exception as e:
                                        payment_type_btn_element = self.driver.find_element(
                                            By.XPATH, "//a[contains(., 'Transfer') and @ng-click='addPaymentType(btnsubList)']")
                                        self.driver.execute_script("arguments[0].click();", payment_type_btn_element)
                                elif self.app.marketplace_target.get() == 'LAZADA':
                                    final_price = (self.app.sum_price) - self.app.cus_seller_voucher.get()
                                    # / เลือก lazada
                                    payment_type_btn_element = self.driver.find_element(
                                        By.XPATH, "//a[contains(., 'LAZ')]")
                                    self.driver.execute_script("arguments[0].click();", payment_type_btn_element)

                                # / PO No:
                                try:
                                    po_no_input_element = self.driver.find_element(
                                        By.XPATH, "//input[@id='textbox81037000102']")
                                    value_to_input = self.cus_order
                                    #! classic way
                                    # po_no_input_element.clear()
                                    # po_no_input_element.send_keys(value_to_input)

                                    #! CAUTION หากไม่ใช้ trgigger event input and change มันเปลี่ยนค่าที่แสดงผลบน html เฉยๆ แต่ state มันไม่เปลี่ยน มันเลยดูเหมือนใส่แล้วแต่ไม่ได้ใส่
                                    # * Final way ใช้ function ที่เขียนแยกไว้
                                    self.js_input_value(po_no_input_element, value_to_input)
                                except Exception as e:
                                    print("Cannot fill PO No:", e)

                                # Todo migrate this section to 3.2.1 : update 3.1.5 auto toggle the sn toggle to "false" because default was set to "true"
                                # / ผมใช้เอง หรือ กรณีใช้ปุ่ม Finish
                                if self.app.user_id.get() == "62078" or self.app.is_finish_order_triggered.get():
                                    cn_flag_element = self.driver.find_element(By.CSS_SELECTOR, '#cnRefFlag')
                                    self.driver.execute_script("""arguments[0].click();""", cn_flag_element)

                                try:
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[3]/div[1]/div[1]/div/div/div/div/div[2]/center/button[2]').click()
                                except:
                                    print("ปุ่ม Brows() ไม่โผล่")

                                # / input 'Name:'
                                # / ลูกค้ามีชื่อไหม ถ้าไม่มี ใส่ order แทน
                                if self.app.cus_name.get():
                                    value_to_input = self.app.cus_name.get()
                                else:
                                    value_to_input = self.cus_order

                                #! classic way
                                # self.driver.find_element(
                                #     By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[2]/div/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').clear()
                                # self.driver.find_element(
                                #     By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[2]/div/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').send_keys(value_to_input)

                                # * Final way ใช้ function ที่เขียนแยกไว้
                                final_cus_name_input_element = self.driver.find_element(
                                    By.XPATH, "//input[@id='textbox81037000101']")
                                self.js_input_value(final_cus_name_input_element, value_to_input)

                            except Exception as err:
                                print("Final page failed, skip to waiting for price")
                                print("err: ", err)
                                break

                            # / Auto Enter final Price
                            try:
                                print("Auto enter price")
                                print("final_price: ", final_price)
                                final_price_element = self.driver.find_element(By.XPATH, "//input[@id='ripCash00']")
                                # final_price_element.clear()
                                self.js_input_value(final_price_element, final_price)
                                # final_price_element.send_keys(final_price)

                            except Exception as e:
                                print("auto_final_price broken", e)

                            # / Check wrimagecard value (เฉพาะเมื่อกดปุ่ม Finish เท่านั้น)
                            if self.app.is_finish_order_triggered.get():
                                try:
                                    value_element = self.driver.find_element(
                                        By.XPATH,
                                        "//div[@class='col-sm-12    wrimagecard-lightGray wrimagecard-topimage ng-binding']")
                                    value_text = value_element.text.strip()
                                    print(f"wrimagecard value: '{value_text}'")
                                    if value_text == "0.00":
                                        print("Value is 0.00, clicking btnPayment")
                                        btn_payment = self.driver.find_element(
                                            By.XPATH,
                                            "//div[@class='wrimagecard wrimagecard-green wrimagecard-topimage']/a[@id='btnPayment' and @ng-click='savebeforePayment()']")
                                        # self.driver.execute_script("arguments[0].click();", btn_payment) # ! ใช้ click ธรรมดาแทนเพราะบางทีถ้าใช้ js click มันจะไม่ trigger event ที่จำเป็นบางอย่างทำให้เกิด error ในขั้นตอนต่อไป
                                        btn_payment.click()  # * ตรงนี้จะ trigger event blur ที่จะทำให้ระบบมันไปคำนวณราคาต่อและถ้าใช้ js click มันจะไม่ trigger event blur ทำให้ราคามันไม่ update และเกิด error ในขั้นตอนต่อไปเพราะราคามันยังเป็นราคาเก่าอยู่
                                except Exception as e:
                                    print(f"wrimagecard check failed: {e}")
                                finally:
                                    self.app.is_finish_order_triggered.set(False)

                            # *Auto price มันมีสองอันได้ไง
                            # print("Auto enter price")
                            # print((self.app.sum_price + self.app.cus_ship_cost.get()) - self.app.cus_seller_voucher.get())
                            # final_price = (self.app.sum_price + self.app.cus_ship_cost.get()) - self.app.cus_seller_voucher.get()
                            # if self.app.user_id.get() in self.app.dev_account:
                            #     self.driver.find_element(By.XPATH, "//input[@id='ripCash00']").clear()
                            #     self.driver.find_element(By.XPATH, "//input[@id='ripCash00']").send_keys(final_price)

                            #! deprecated มันเหมือนมีไรสักอย่างที่มันจะแสดงชื่อลูกค้า แต่ตอนนี้เหมือนจะไม่มีละ
                            # # * ค้นหา element โดยใช้ XPath
                            # self.is_input_on = self.driver.find_element(By.XPATH,'/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]')

                            # # * ดึงข้อความจาก element ที่ค้นหาได้
                            # text_value = self.is_input_on.get_attribute("title")

                            # # * พิมพ์ผลลัพธ์
                            # print("Check customer name self.is_input_on:", text_value)

                            # # * สำหรับ prefinal  pop-up (optional by ETAX)
                            # # * > แบบเลือกให้ตาม ข้อมูลลูกค้า
                            # while not self.operation_thread.is_set():

                            #     try:
                            #         self.etax_radio_printout = self.driver.find_element(
                            #             By.XPATH, '/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[1]/label/input')
                            #         self.etax_radio_sendmail = self.driver.find_element(
                            #             By.XPATH, '/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[2]/label/input')

                            #         if self.etax_radio_printout.is_displayed():
                            #             print("Click Print Out Radio")
                            #             self.etax_radio_printout.click()
                            #             print("Press Print, and break the loop")
                            #             break
                            #         elif self.etax_radio_sendmail.is_displayed():
                            #             print("Click Send Email Radio")
                            #             self.etax_radio_sendmail.click()
                            #             print(
                            #                 "Press Send Email, and break the loop")
                            #             break
                            #     except:
                            #         print("radio has Disappeared")
                            #         continue

                            # # * > แบบเลือกemail เป็น default
                            # ใช้ได้หรือป่าวไม่แน่ใจ
                            # while not self.operation_thread.is_set():
                            #     final_popup = self.driver.find_element(By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]""")

                            #     print("Radio while loop")
                            #     if final_popup.is_displayed() == True and self.etax_radio_sendmail.is_displayed() == False:
                            #         print("Radio ยังไม่โผล่")
                            #         continue
                            #     elif final_popup.is_displayed() == False:
                            #         print("หน้า final หายไป")
                            #         break
                            #     else:
                            #         try:
                            #             self.etax_radio_sendmail = self.driver.find_element(
                            #                 By.XPATH, '/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[2]/label/input')
                            #             print("Radio appeared")
                            #             if self.etax_radio_sendmail.is_displayed():
                            #                 is_etax = True
                            #                 print("Click Send Email Radio")
                            #                 self.etax_radio_sendmail.click()
                            #                 print(
                            #                     "Press Send Email, and break the loop")
                            #                 break
                            #             elif not self.etax_radio_sendmail.is_displayed():
                            #                 print("ไม่โชว์ก็ออก")
                            #                 break
                            #         except:
                            #             print("radio has Disappeared")
                            #             break

                            # * สำหรับรอ final pop-up after click the green btn
                            self.final_popup_after_green_btn_handler(is_etax, self)
                            continue

                        else:
                            print("จบสูตร")
                        self.autofinal = False
                        break

                    print("Whileหลัก ถ้ามาถึงนี่แปลว่าต้องเริ่มใหม่")
                    continue
                break

                print("จบ auto_last_page")
                self.autofinal = False
                # print("self.operation_thread.set()4357: ")
                # self.operation_thread.set()
                # self.driver.quit()

            print("operation_thread is set or autofinal is false, exit final loop")

        else:
            print("ไม่มีOrder ไม่รู้จะทำอะไร")

        # # * จงใจให้ Error จงใจ Error // มันจะได้จบๆไป
        # if self.app.accel_search_thread:
        #     self.app.accel_timer = threading.Timer(
        #         0.2, self.app.on_accel_thread_done)
        #     self.app.accel_timer.start()
        # else:
        #     print("'MyApp' object has no attribute 'accel_search_thread'")
        #     pass

    def open_customer_form(self, is_functionworking):
        if not self.has_sale_type_selected():
            print("No sale type selected, selecting now")
            self.select_sale_type()
        print("opening customer form initializing")

        time.sleep(0.55)

        # * มันมีปุ่มบางอย่างที่มันอาจจะทำให้มีปัญหาในการจัดการชื่อลูกค้าได้ มันจะแสดงผลในหน้าใหม่เท่านั้น หน้าเก่าไม่แสดง เลยต้อง try-except ไว้ เพราะมันอาจจะมีหรือไม่มีก็ได้
        try:
            self.driver.execute_script(
                """ document.querySelector("button[ng-click='abbCustomerFlag = false;']").click(); """)
        except Exception as err:
            print("There's no the new abbCustomerFlag btn")
            print("abbCustomerFlag-err: ", err)

        customer_form_dialog_element = False
        # todo เช็ค dialog form โหลดเสร็จยัง
        while is_functionworking and not self.operation_thread.is_set():
            try:
                # * ไม่เจอ faded backdrop แปลว่ายังไม่เปิดnew cus form มันเลยจะไปเปิดใน except แล้วกลับมา
                customer_form_dialog_element = self.driver.find_element(
                    By.CSS_SELECTOR, 'body > div.modal-backdrop.fade.in')
                customer_class_input = self.driver.find_element(
                    By.XPATH, '//*[contains(@class, "select2-selection__rendered") and @id="select2-memberClass-container"]')
                if customer_form_dialog_element.is_displayed() and customer_class_input.is_displayed():
                    print(f"customer_form_dialog_element: {customer_form_dialog_element.is_displayed()}")
                    time.sleep(0.25)
                    # * element นี้มันมาไม่ทัน จึงทำให้ต้องเขียน except และมี try except ซ้อนข้างล่างอีกชั้น
                    print(f"customer_class_input: {customer_class_input.is_displayed()}")
                    break
            except Exception as err:
                # print(f"customer_class_selector error: {err}") #* handle ได้ละ
                try:
                    print(f"No create customer form, click 'create customer' button")
                    self.driver.find_element(By.CSS_SELECTOR, self.app.cusCreateBtn).click()  # * กดปุ่ม create customer
                    print(f"'create customer' button clicked")
                except:
                    time.sleep(0.25)
                    continue

    def customer_class_selector(self, is_functionworking):
        print("finding customer class dropdown initializing")
        # * มีตัว Customer Class ให้กรอกไหม
        while is_functionworking and not self.operation_thread.is_set():
            print("start finding customer class dropdown")
            # * > เลือกหมวดลูกค้า  เพิ่มมาตอน 6.3.1 24/04/2024
            try:
                # self.driver.find_element(By.XPATH, '//*[@class="select2-selection__rendered" and @id="select2-memberClass-container"]').click()
                while True:
                    print("customer class handler while start")
                    time.sleep(0.25)
                    try:
                        self.driver.find_element(By.CSS_SELECTOR, "#select2-memberClass-results > li").is_displayed()
                        print(f"dropdown target has been already displaying")
                        break
                    except:
                        try:
                            self.driver.find_element(By.CSS_SELECTOR,
                                                     "#select2-memberClass-results > li").is_displayed()
                            print(f"dropdown target choice is now displaying")
                            continue
                        except:
                            #! ไอ้ตัวนี้ไม่รู้เปนไร คลิกไม่ได้หลายรอบละเจ๊กแม่ ทั้งๆที่ข้างบนตรวจการมีอยู๋ของมันจนหมดแล้วแท้ๆ
                            try:
                                dropdown_input = self.driver.find_element(
                                    By.CSS_SELECTOR, '#select2-memberClass-container')
                                dropdown_input.click()
                                print(f"dropdown clicked {dropdown_input.text}")
                                # ! ต้องเช็ค ul ที่โผล่มาหลังจาก click ก่อน บางที click แล้วหาย
                                time.sleep(0.25)
                                continue
                            except:
                                print(f"driver cannot see the element")
                                continue

                # * บางจังหวะ มันไม่ขึ้น "CM1-Domestic Customer" แล้วมันข้ามไปใส่ชื่อเลย แล้วมันจะไปต่อไม่ได้เพราะ CM1-Domestic Customer ไม่ได้ถูกใส่
                while True:
                    print("let's click the target li")
                    time.sleep(0.25)
                    try:
                        print("click choice li")
                        choice_found = self.driver.find_element(
                            By.CSS_SELECTOR, "#select2-memberClass-results > li").text
                        print("choice_found: ", choice_found)
                        if self.driver.find_element(
                                By.CSS_SELECTOR, "#select2-memberClass-results > li").text == "CM1-Domestic Customer":
                            print("the corrected choice is found")
                            self.driver.find_element(
                                By.CSS_SELECTOR, '#customerNewModal > span > span > span.select2-search.select2-search--dropdown > input').clear()
                            time.sleep(0.25)
                            self.driver.find_element(By.CSS_SELECTOR, "#select2-memberClass-results > li").click()
                            print(f"Click the choice")
                            break
                    except Exception as err:
                        time.sleep(1)
                        print("except cannot click li: ", err)  # for develop inspection
                        break
                try:
                    if self.driver.find_element(By.CSS_SELECTOR, "#select2-memberClass-container").get_attribute(
                            'title') == "CM1-Domestic Customer":
                        print("li name selection complete")
                        break
                except:
                    print("back to call li again")
                    continue

            except Exception as err:
                print("No Customer Class input")
                time.sleep(1)
                print("except: ", err)  # for develop inspection

    def addCustomer(self, customer_type="normal", cusname_fixed=None):
        """
        Unified method to add customers to SMCO system
        Args:
            customer_type: "normal", "tax", or "tax_laz"
            cusname_fixed: For normal customers, the fixed customer name
        """
        is_functionworking = True
        try:
            self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย1'])
            print("SMCO :: เปิดการขาย1 ไม่หาย ไปต่อ")
            logger.info(f"{self.cus_order}: SMCO :: เปิดการขาย1 ไม่หาย ไปต่อ")
        except Exception as err:
            print("SMCO :: เปิดการขาย1 หายไป เปิดใหม่ {err}")
            logger.info(f"{self.cus_order}: SMCO :: เปิดการขาย1 หายไป เปิดใหม่ {err}")
            self.driver.execute_script("window.open('');")
            all_handles = self.driver.window_handles
            new_handle = all_handles[-1]  # tab ใหม่ล่าสุด
            self.driver.switch_to.window(new_handle)
            self.driver.get(f"{self.origin}/smartcore/smartpos/pointofsales/posmainv3.htm")
            self.get_tabs()
            try:
                self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย1'])
                print(f"หลังจาก reopen และตรวจดูด้วย get_tabs, หน้า 'SMCO :: เปิดการขาย1' มีอยู่จริง ")
            except Exception as err:
                print(f"หลังจาก reopen และตรวจดูด้วย get_tabs, หน้า 'SMCO :: เปิดการขาย1' ไม่มีอยู่จริง {err}")
                logger.error(
                    f"{self.cus_order}: หลังจาก reopen และตรวจดูด้วย get_tabs, หน้า 'SMCO :: เปิดการขาย1' ไม่มีอยู่จริง {err}")
                self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])

        try:
            self.driver.find_element(
                By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]""").click()
            logger.info(f"{self.cus_order}: there is a 'Close' button in SMCO :: เปิดการขาย1")
            print(f"{self.cus_order}: there is a 'Close' button in SMCO :: เปิดการขาย1")
        except:
            print(f"{self.cus_order}: there is no any 'Close' button in SMCO :: เปิดการขาย1")

        self.open_customer_form(is_functionworking)

        # Prepare customer data based on type
        if customer_type == "normal":
            name = cusname_fixed
            tax_num = None
            address = self.app.cus_address
            email = ""
            phone = "1"
            use_dropdown_address = False

        elif customer_type == "tax":
            name = self.app.cus_name.get()
            # Remove any trailing branch info to standardize format
            name = re.sub(r'\s*\(?(?:สำนักงานใหญ่|สํานักงานใหญ่|สนญ\.?|00000)\)?\s*$', '', name)
            name = re.sub(r'\s*\(?สาขา[^)]*\)?\s*$', '', name)
            name = name.strip()

            # Add branch info for tax customers
            if self.app.branch_type == 'สำนักงานใหญ่':
                name = f"{name} ({self.app.branch_type})"
            elif self.app.branch_type == "สาขาย่อย" and not pd.isna(self.app.data_frame[self.app.target_row]['รหัสประจำสาขา'].iloc[0]):
                name = f"{name} (สาขา{self.app.tax_branch_num.get()})"

            tax_num = self.app.tax_num.get()
            address = self.app.get_pure_address(self.app.clean_address(
                self.app.address)) if self.app.is_tax_required.get() else self.app.address
            email = self.app.cus_email.get()
            phone = self.app.cus_tel.get()
            use_dropdown_address = True
            province = self.app.cus_province.get().replace("จังหวัด", "")
            district = self.app.cus_district.get().replace("อำเภอ", "").replace("เขต", "").replace("อ.", "")
            sub_district = self.app.cus_sub_district.get().replace("ตำบล", "").replace("แขวง", "").replace("ต.", "")
            postcode = self.app.cus_postcode.get()

        elif customer_type == "tax_laz":
            # * value of self.app.tax_branch_num.get() can be "สำนักงานใหญ่" or ตัวเลขสาขา 5 หลัก
            if self.tax_info.get(self.app.tax_num.get()):
                tax_info = self.tax_info[self.app.tax_num.get()]
            else:
                tax_info = self.get_vatinfo_data(self.app.tax_num.get(), self.app.tax_branch_num.get())
                self.tax_info[self.app.tax_num.get()] = tax_info
            name = tax_info['name']
            self.app.cus_tax_name_lazada.set(name)

            # Remove any trailing branch info to standardize format
            name = re.sub(r'\s*\(?(?:สำนักงานใหญ่|สํานักงานใหญ่|สนญ\.?|00000)\)?\s*$', '', name)
            name = re.sub(r'\s*\(?สาขา[^)]*\)?\s*$', '', name)
            name = name.strip()

            # * Add branch info for lazada tax customers
            if self.app.branch_type == 'สำนักงานใหญ่':
                self.app.tax_branch_num.set(self.app.nondistortedData['ประเภทสาขา'])
                if name.startswith("บริษัท") or "จำกัด" in name:
                    name += f" (สำนักงานใหญ่)"
            elif self.app.branch_type == "สาขาย่อย" and not pd.isna(self.app.data_frame[self.app.target_row]['รหัสประจำสาขา'].iloc[0]):
                name = f"{name} (สาขา{self.app.tax_branch_num.get()})"

            tax_num = tax_info['tax_num']
            address = tax_info['address_shortened']
            email = self.app.cus_email.get()
            phone = self.app.cus_tel.get()
            use_dropdown_address = True
            province = tax_info['province'].replace("จังหวัด", "")
            district = tax_info['district'].replace("อำเภอ", "").replace("เขต", "").replace("ต.", "")
            sub_district = tax_info['sub_district'].replace("ตำบล", "").replace("แขวง", "").replace("ต.", "")
            postcode = tax_info['postal_code']

        # Fill customer form
        while is_functionworking and not self.operation_thread.is_set():
            try:
                # * Name TH
                name_th_element = self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[1]/input')
                self.js_input_value(name_th_element, name)
                # self.driver.find_element(
                #     By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[1]/input').clear()
                # self.driver.find_element(
                #     By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[1]/input').send_keys(name)

                # * Name ENG
                name_eng_element = self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[2]/input')
                self.js_input_value(name_eng_element, name)

                # * Tax ID (only for tax customers)
                if tax_num:
                    tax_num_element = self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[3]/input')
                    self.js_input_value(tax_num_element, tax_num)

                # * Address
                address_element = self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[8]/div/textarea')
                self.js_input_value(address_element, address)

                # * Email (if provided)
                if email:
                    email_element = self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[14]/div[3]/input')
                    self.js_input_value(email_element, email)

                # * Phone
                phone_element = self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[15]/div[3]/input')
                self.js_input_value(phone_element, phone)

                # * Address dropdowns (only for tax customers)
                if use_dropdown_address:
                    # * Country dropdown
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[10]/div[1]/div/span/span[1]/span').click()
                    self.dropdown_handler()

                    if customer_type == "tax":
                        self.driver.find_element(
                            By.XPATH, "/html/body/div[2]/div[3]/div[13]/span/span/span[2]/ul/li[2]").click()
                    else:  # tax_laz
                        self.driver.find_element(By.XPATH, "//li[text()='Thailand' or text()='ไทย']").click()

                    # * Province dropdown
                    province_dropdown_btn = self.driver.find_element(
                        By.CSS_SELECTOR, 'span #select2-province-container')
                    province_dropdown_btn.click()
                    province_input = self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input')

                    # ใช้ helper method เพื่อเลือกจาก API response
                    self.select_li_from_dropdown(
                        input_element=province_input,
                        search_value=province,
                        th_field='provinceNameTh',
                        en_field='provinceNameEn',
                        place_type='province'
                    )

                    # * District dropdown
                    district_dropdown_btn = self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[12]/div[1]/div/span/span[1]/span/span[1]')
                    district_dropdown_btn.click()
                    district_input = self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input')

                    # ใช้ helper method เพื่อเลือกจาก API response
                    self.select_li_from_dropdown(
                        input_element=district_input,
                        search_value=district,
                        th_field='districtNameTh',
                        en_field='districtNameEn',
                        place_type='district'
                    )

                    # * SubDistrict dropdown
                    subdistrict_dropdown_btn = self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[12]/div[3]/div/span/span[1]/span/span[1]')
                    # คลิก 3 ครั้งเพื่อให้แน่ใจว่า dropdown เปิด
                    subdistrict_dropdown_btn.click()
                    subdistrict_dropdown_btn.click()
                    subdistrict_dropdown_btn.click()
                    subdistrict_input = self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input')

                    # ใช้ helper method เพื่อเลือกจาก API response
                    self.select_li_from_dropdown(
                        input_element=subdistrict_input,
                        search_value=sub_district,
                        th_field='subdistrictNameTh',
                        en_field='subdistrictNameEn',
                        place_type='subdistrict'
                    )

                    # * Postal code
                    zip_code_btn_xpath = "//span[@id='select2-zipCodeSel-container']"
                    zip_code_btn_element = self.driver.find_element(By.XPATH, zip_code_btn_xpath)
                    try:
                        # * ถ้าหาไม่เจอมันจะ เข้า Except ไปเอง
                        self.driver.find_element(By.XPATH, f"""//span[@title='{postcode}']""")
                    except:
                        try:
                            zip_code_btn_element.click()
                            self.dropdown_handler()
                            self.driver.find_element(
                                By.XPATH, f"""//li[@role='treeitem' and text()='{postcode}']""").click()
                        except (NoSuchElementException, TimeoutException) as err:

                            print(f"Postal code {postcode} cannot be found in dropdown, skip postal code selection")
                            if hasattr(self.app, 'is_auto_invoice_mode') and self.app.is_auto_invoice_mode.get():
                                logger.error(
                                    f"order {self.cus_order}: auto invoice mode requires postal code selection but postal code {postcode} cannot be found in dropdown, stopping the process. Error details: {err}")
                                raise ValueError(
                                    f"Postal code {postcode} cannot be found in dropdown, auto invoice mode requires postal code selection, stopping the process. Error details: {err}")

                print(f"customer_class_selector() initializing: is_functionworking {is_functionworking}")
                self.customer_class_selector(is_functionworking)

                # * CLick Save Button (commented out but kept for completeness)
                if customer_type == "normal" or self.app.is_auto_invoice_mode.get():
                    save_btn = self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[1]/div[4]/button[1]')
                    is_disabled = save_btn.get_attribute("disabled")
                    if is_disabled is not None or not save_btn.is_enabled():
                        logger.warning(
                            f"Order: {self.cus_order} - Save button is disabled (disabled={is_disabled}). Refreshing page and restarting...")
                        try:
                            self.driver.refresh()
                        except Exception as e:
                            logger.error(f"Failed to refresh browser: {e}")
                        time.sleep(2)
                        raise RefreshRequiredException("ปุ่มบันทึกถูกปิดใช้งาน (disabled)")

                    save_btn.click()

                # * Wait for saving process to complete
                while is_functionworking and not self.operation_thread.is_set():
                    try:
                        self.wait50.until(EC.invisibility_of_element_located(
                            (By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[1]/div[4]/button[1]')))
                        is_functionworking = False
                        break
                    except RefreshRequiredException:
                        raise
                    except:
                        print("[metthod]addCustomer: Save button still appear")

                break

            except (InvalidSessionIdException, WebDriverException) as err:
                print(f"addCustomer(): WebDriver connection error, raising to trigger reconnect. Error: {err}")
                raise err
            except ValueError as ve:
                print(f"addCustomer(): Stopped by ValueError: {ve}")
                # ปิดหน้าต่างสร้างลูกค้า เพื่อไม่ให้ค้าง
                try:
                    # 1. ลองกดปุ่มยกเลิก (ปุ่มถัดจาก Save)
                    cancel_btn_xpath = '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[1]/div[4]/button[2]'
                    self.driver.find_element(By.XPATH, cancel_btn_xpath).click()
                except:
                    pass

                try:
                    # 2. ลองส่งปุ่ม ESC เพื่อปิด Modal
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except:
                    pass

                try:
                    # 3. ลองกดปุ่มปิดแบบทั่วไป
                    self.driver.execute_script("document.querySelector('button[ng-click=\"cancel()\"]').click();")
                except:
                    pass
                time.sleep(0.5)
                raise ve
            except Exception as err:
                print(f"addCustomer(): Elements cannot be found, retry filling customer form. Error: {err}")
                if customer_type != "normal":
                    continue
                else:
                    break

        print(f"add {customer_type} Customer end")

    def addressExtractor(self, cusAddress):
        self.splited = cusAddress.split(",")
        return (self.splited)

    def js_input_value(self, element, value):
        """
        ฟังก์ชันสำหรับกรอกค่าลงใน Element โดยใช้ JavaScript
        พร้อมสั่ง Trigger Event เพื่อให้ Framework ของหน้าเว็บรับรู้
        """
        script = """
            var el = arguments[0];
            var val = arguments[1];
            
            el.focus();
            el.dispatchEvent(new Event('focus', { bubbles: true }));
            
            
            el.value = val;
            
            
            el.dispatchEvent(new Event('input', { bubbles: true }));
            
            
            el.dispatchEvent(new Event('change', { bubbles: true }));
            
            
            
        """
        self.driver.execute_script(script, element, value)


# el.dispatchEvent(new Event('blur', { bubbles: true })); ถ้าจะใช้ให้ใส่ล่างสุดนะ


# *Customer Tax Address Correction--------------------------------------------------------------------------------------------------

    def get_cookies_from_driver(self):
        cookies = self.driver.get_cookies()
        cookies_from_webdriver = {}
        for i in cookies:
            cookies_from_webdriver[i['name']] = i['value']
            # print(f"{i['name']} : {i['value']}")
        return cookies_from_webdriver

    def address_api_request_smco(self, payload: dict = {}):
        cookies = self.get_cookies_from_driver()
        current_url = self.driver.current_url
        matched_str = re.search(r'\/[A-z].*', current_url).group()
        self.origin = current_url.replace(matched_str, '')

        url = f'{self.origin}/smartcore/uilts/oper/pos/getCustomerSearchPOS/selectoption.htm'
        response = self.smco_api.post(url, data=payload, cookies=cookies, origin=self.origin)

        # print('get_address_smco response status: ', response.json())
        # print('response.json(): ', response.json())
        return response

    def smco_req_find_customer_id(self, cus_code: str = ""):
        print("find_customer_id excuted by code: ", cus_code)
        payload = {
            'requestText': f'{cus_code}',
            'target': 'C',
        }
        response = self.address_api_request_smco(payload)
        response_data: list = response.json()
        cus_data: dict = {}
        for i in response_data:
            if i['custCode'] == cus_code:
                cus_data = i
                break
            else:
                print(f'ไม่มี {cus_code} นี้จาก response_data')
                raise ValueError(f'ไม่มี {cus_code} นี้จาก response_data')

        customer_id = cus_data['id'] or False
        # print("customer_id: ", cus_data['id'])
        return customer_id

    def is_english(self, text):
        """
        ตรวจสอบว่าข้อความเป็นภาษาอังกฤษหรือไม่

        Args:
            text: ข้อความที่ต้องการตรวจสอบ

        Returns:
            bool: True ถ้าเป็นภาษาอังกฤษ, False ถ้าเป็นภาษาไทย
        """
        import re
        if not text:
            return False
        # นับตัวอักษร a-z
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        # ถ้ามีตัวอักษรอังกฤษมากกว่า 50% = ภาษาอังกฤษ
        return english_chars > len(text) * 0.5

    def translate_eng_to_thai_place(self, eng_name, place_type='district'):
        """
        แปลงชื่อสถานที่จากภาษาอังกฤษเป็นภาษาไทย
        โดยค้นหาจาก Addresscleaner_TambonData.xlsx

        Args:
            eng_name: ชื่อภาษาอังกฤษ (เช่น "Watthana")
            place_type: ประเภท ('province', 'district', 'subdistrict')

        Returns:
            str: ชื่อภาษาไทย หรือ eng_name เดิมถ้าหาไม่เจอ
        """
        if self.address_data is None:
            print("Address data not loaded, returning original name")
            return eng_name

        try:
            # กำหนด column names ตาม place_type
            column_mapping = {
                'province': ('ProvinceEng', 'ProvinceThai'),
                'district': ('DistrictEngShort', 'DistrictThaiShort'),
                'subdistrict': ('TambonEngShort', 'TambonThaiShort')
            }

            # ลองหลาย pattern ของ column names
            possible_en_cols = [
                column_mapping.get(place_type, ('', ''))[0],
                f'{place_type}_en',
                f'{place_type}NameEn',
                f'{place_type.capitalize()}_EN'
            ]

            possible_th_cols = [
                column_mapping.get(place_type, ('', ''))[1],
                f'{place_type}_th',
                f'{place_type}NameTh',
                f'{place_type.capitalize()}_TH'
            ]

            # หา column ที่มีอยู่จริง
            en_col = None
            th_col = None

            for col in possible_en_cols:
                print("col: ", col)
                if col in self.address_data.columns:
                    en_col = col
                    break

            for col in possible_th_cols:
                print("col: ", col)
                if col in self.address_data.columns:
                    th_col = col
                    break

            if not en_col or not th_col:
                print(f"Columns not found for {place_type}")
                print(f"en_col: {en_col}, th_col: {th_col}")
                print(f"Available columns: {self.address_data.columns.tolist()}")
                return eng_name

            # ค้นหาชื่อภาษาอังกฤษ (case-insensitive)
            mask = self.address_data[en_col].str.lower() == eng_name.lower()
            matches = self.address_data[mask]

            if not matches.empty:
                thai_name = matches.iloc[0][th_col]
                print(f"Translated '{eng_name}' → '{thai_name}'")
                return thai_name
            else:
                print(f"No translation found for '{eng_name}', using original")
                return eng_name

        except Exception as e:
            print(f"Error in translation: {e}")
            return eng_name

    def select_li_from_dropdown(self, input_element, search_value, th_field, en_field, place_type='district'):
        """
        เลือก dropdown โดยใช้ข้อมูลจาก API response
        แก้ปัญหาการเลือกผิดเมื่อเว็บเป็น EN version แต่ลูกค้ากรอกภาษาไทย
        รองรับการกรอกภาษาอังกฤษโดยแปลงเป็นภาษาไทยก่อน

        Args:
            input_element: Input element ของ dropdown
            search_value: ค่าที่ต้องการค้นหา (ภาษาไทยหรืออังกฤษ)
            th_field: ชื่อ field ภาษาไทยใน response (เช่น 'provinceNameTh')
            en_field: ชื่อ field ภาษาอังกฤษใน response (เช่น 'provinceNameEn')
            place_type: ประเภทสถานที่ ('province', 'district', 'subdistrict')

        Returns:
            bool: True ถ้าเลือกสำเร็จ, False ถ้าไม่พบ
        """

        try:
            # * ตรวจสอบว่าเป็นภาษาอังกฤษหรือไม่
            if self.is_english(search_value):
                print(f"Detected English input: '{search_value}'")
                # แปลงเป็นภาษาไทยก่อน
                thai_value = self.translate_eng_to_thai_place(search_value, place_type)
                search_value = thai_value
                print(f"Will search with Thai name: '{search_value}'")
            # * Clear logs ก่อนส่ง request
            self.network_capture.clear_logs()

            # * Clear และ type ค่าเพื่อ trigger API call
            input_element.clear()
            input_element.send_keys(search_value)
            print(f"Typed '{search_value}' to trigger API")

            # รอ dropdown พร้อม
            self.dropdown_handler()

            # จับ response จาก API
            api_url_part = "/getCountryInfomation.htm"
            response_data = self.network_capture.capture_response(api_url_part)

            li_dropdowns = self.driver.find_elements(By.XPATH, "//li[@role='treeitem']")

            if response_data:
                print(f"Got {len(response_data)} items from API")

                # * หาค่าที่ตรงกับ search_value
                matched_item = None
                for idx, item in enumerate(response_data):
                    if item.get(th_field) == search_value:
                        matched_item = item
                        matched_item_idx = idx
                        print(f"Matched: {item.get(th_field)} ({item.get(en_field)})")
                        break

                if matched_item:
                    # เลือกโดยกด Enter (dropdown จะเลือกตัวแรกที่ตรง)
                    # input_element.send_keys(Keys.ENTER)
                    li_dropdowns[matched_item_idx].click()
                    print(f"Selected '{search_value}', item idx {matched_item_idx} successfully")

                    # Clear logs หลังใช้งาน
                    self.network_capture.clear_logs()
                    return True
                else:
                    print(f"No match found for '{search_value}'")
            else:
                print("No response from API, using fallback")

            # Fallback: กด Enter ตามปกติ
            input_element.send_keys(Keys.ENTER)
            self.network_capture.clear_logs()
            return False

        except Exception as e:
            print(f"Error in select_li_from_dropdown: {e}")
            # Fallback: กด Enter
            try:
                input_element.send_keys(Keys.ENTER)
            except:
                pass
            self.network_capture.clear_logs()
            return False

    def smco_req_find_cus_address(self, cus_id: int = None, **kwargs):
        print(f"order: {self.cus_order}: smco_req_find_cus_address() called with cus_id: {cus_id} and kwargs: {kwargs}")
        max_retries = 3
        retry_count = 0
        suffix = kwargs
        while retry_count < max_retries:
            try:
                payload = {
                    'target': '1',
                    'parentId': f'{cus_id}',
                }
                response = self.address_api_request_smco(payload)

                # ตรวจสอบ response status
                if response.status_code in [400, 500]:
                    print(
                        f"Request failed with status {response.status_code}, retrying... ({retry_count + 1}/{max_retries})")
                    retry_count += 1
                    time.sleep(1)  # รอ 1 วินาทีก่อนลองใหม่
                    continue

                response.raise_for_status()  # จะ raise ValueError ถ้า status code เป็น 4xx หรือ 5xx

                response_data: dict = response.json()
                extracted_address: dict = {}

                for address in response_data['addressOfMember']:
                    if address['defaultFlag']:
                        # ดึงข้อมูลจาก dictionary หลักแบบปลอดภัย
                        sub_dist_data = address.get('subDustricId') or {}
                        dist_data = address.get('districtId') or {}
                        prov_data = address.get('provinceId') or {}

                        extracted_address['address'] = address.get('custAddress') or ''
                        extracted_address['subdistrict'] = sub_dist_data.get(
                            f"""subdistrictName{suffix["subdistrict"]}""".strip()) or ''
                        extracted_address['district'] = dist_data.get(f'districtName{suffix["district"]}') or ''
                        extracted_address['provice'] = prov_data.get(f'provinceName{suffix["province"]}') or ''
                        extracted_address['zip_code'] = address.get('zipCode') or ''
                        print('subdistrict from req: ', extracted_address['subdistrict'])

                return extracted_address

            except requests.exceptions.RequestException as e:
                print(f"Request error: {e}")
                retry_count += 1
                if retry_count == max_retries:
                    print("Max retries reached, returning empty address")
                    return {
                        'address': '',
                        'subdistrict': '',
                        'district': '',
                        'provice': '',
                        'zip_code': ''
                    }
                time.sleep(1)

            except Exception as e:
                print(f"Unexpected error: {e}")
                return {
                    'address': '',
                    'subdistrict': '',
                    'district': '',
                    'provice': '',
                    'zip_code': ''
                }

    def direct_to_customer_info(self, incoming_cus_code: int = None):
        # * เนื่องจาก หน้าลูกค้ามันมีสองชั้น ตรวจสอบว่า หน้าที่กำลังแสดงผลเป็นหน้าในหรือนอก ถ้าในต้องปรับเป็นนอกก่อน
        while not self.operation_thread.is_set():
            is_outer_page_on = False
            is_inner_page_on = False
            is_inner_info_page_on = False
            self.driver.switch_to.window(self.merged_dict['SMCO :: ลูกค้า'])
            try:
                'SMCO :: ลูกค้า' in self.merged_dict
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/button')
                is_outer_page_on = True

            except:
                if self.driver.find_element(By.CSS_SELECTOR, '#vendorFormReal div:nth-child(1) > div:nth-child(2) > div > input').is_displayed():
                    is_inner_info_page_on = True

                self.driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[1]/div')
                is_inner_page_on = True

            finally:
                if is_inner_page_on and is_inner_info_page_on:
                    break
                elif is_inner_page_on:
                    self.driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div[1]/div[1]/div[1]/a').click()
                    continue
                elif is_outer_page_on:
                    break
                else:
                    time.sleep(0.25)

        is_already_in_info_edit_page = False
        is_correct_cus_code = False
        is_already_in_edit_page = False
        # * รอดูว่าelement โผล่ยัง
        while not self.operation_thread.is_set():
            print("ก่อนเข้า try")
            time.sleep(0.25)
            # self.driver.switch_to.window(self.merged_dict['SMCO :: ลูกค้า'])
            try:
                'SMCO :: ลูกค้า' in self.merged_dict
                print("เข้ามาใน try")
                # * มมันถูกซ่อนไว้เฉยๆ webDriverสามารถเข้าถึงได้ แต่ว่ามันจะมี attribute display = false
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/button')
                print(
                    "ปุ่มหน้า SMCO :: ลูกค้า ไม่โดนดักได้ไง: ", self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/button'),
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/button').is_displayed())
                print("we are in the outer page, kinda customer searching page")
                break
            except:
                try:
                    print("we are already in the deepest part")
                    is_already_in_info_edit_page = self.driver.find_element(
                        By.CSS_SELECTOR, '#vendorFormReal div:nth-child(1) > div:nth-child(2) > div > input').is_displayed()
                    current_cus_code = self.driver.find_element(
                        By.CSS_SELECTOR, f"#vendorFormReal div:nth-child(1) > div:nth-child(2) > div > input").get_attribute('title')
                    is_correct_cus_code = incoming_cus_code == current_cus_code
                    break

                except:
                    print("we are in some selected customer edit page")
                    is_already_in_edit_page = self.driver.find_element(
                        By.CSS_SELECTOR, 'div#editBtnDiv > div.btn-group:nth-child(2) > a#editBtn').is_displayed()
                continue

        if is_already_in_info_edit_page and is_correct_cus_code:
            print("อยู่หน้าในอยู๋ละ")
            return

        # * ปุ่มลูกค้า
        customer_code_btn = self.driver.find_element(
            By.XPATH, '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/button')
        if not customer_code_btn.is_displayed():
            adavance_button = self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[2]/div/div[2]/div/div[1]/div/div[2]/label')
            adavance_button.click()
            # adavance_button_text = adavance_button.text
            # print("adavance_button: ", adavance_button , "clicked")
            pass
        customer_code_btn.click()

        # * customer code search popup
        self.wait_element(
            '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[2]/div/div/div[2]/div/div/span/span[1]/span/ul/li/input')
        customer_popup_input = self.driver.find_element(
            By.XPATH,
            '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[2]/div/div/div[2]/div/div/span/span[1]/span/ul/li/input')
        try:
            customer_popup_clear_btn = self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[2]/div/div/div[2]/div/div/span/span[1]/span/ul/span')
            customer_popup_clear_btn.click()
        except:
            pass

        customer_popup_input.send_keys(self.cus_code)

        # * หา li
        while not self.operation_thread.is_set():
            time.sleep(0.25)
            # self.driver.switch_to.window(self.merged_dict['SMCO :: ลูกค้า'])
            try:
                'SMCO :: ลูกค้า' in self.merged_dict
                self.wait_element(
                    '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[2]/span/span/span/ul/li', self.cus_code)
                break
            except:
                continue
        customer_li_item_target = self.driver.find_element(
            By.XPATH, '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[2]/span/span/span/ul/li')
        customer_li_item_target.click()

        # * Close pop up
        exit_popup_btn = self.driver.find_element(
            By.XPATH, '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[2]/div/div/div[1]/span')
        exit_popup_btn.click()
        # * wait until pop up disappear
        while not self.operation_thread.is_set():
            time.sleep(0.25)
            # self.driver.switch_to.window(self.merged_dict['SMCO :: ลูกค้า'])
            try:
                'SMCO :: ลูกค้า' in self.merged_dict
                customer_popup_input = self.driver.find_element(
                    By.XPATH,
                    '/html/body/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/div[2]/div/div/div[2]/div/div/span/span[1]/span/ul/li/input')
                if not customer_popup_input.is_displayed():
                    break
                else:
                    continue
            except:
                continue

        find_customer_btn = self.driver.find_element(
            By.XPATH, '/html/body/div[2]/div[2]/div/div[2]/div/div[3]/center/button[1]')
        find_customer_btn.click()

        while not self.operation_thread.is_set():
            time.sleep(0.25)
            # self.driver.switch_to.window(self.merged_dict['SMCO :: ลูกค้า'])
            try:
                'SMCO :: ลูกค้า' in self.merged_dict
                customer_code_target = self.driver.find_element(By.XPATH, f"//*[text()='{self.cus_code}']")
                customer_code_target.click()
                break
            except:
                continue

    def open_customer_edit_page(self):
        try:
            self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
            self.cur_url = self.driver.current_url
            matched_str = re.search(r'\/[A-z].*', self.cur_url).group()
            based_url = self.cur_url.replace(matched_str, '')
            print("based URL:", based_url)
            customer_edit_url = based_url+'/smartcore/customers/customers_search_new.htm?mc=POS1010'
            print("customer edit URL:", customer_edit_url)
            self.driver.execute_script(f"window.open('{customer_edit_url}', '_blank');")
            time.sleep(0.75)
            self.get_tabs()
        except:
            print("try error: cannot open SMCO :: ลูกค้า")
            pass

        self.driver.switch_to.window(self.merged_dict['SMCO :: ลูกค้า'])

        # * รอดูว่า element โผล่ยัง
        while not self.operation_thread.is_set():
            time.sleep(0.25)
            # self.driver.switch_to.window(self.merged_dict['SMCO :: ลูกค้า'])
            try:
                'SMCO :: ลูกค้า' in self.merged_dict
                self.driver.find_element(By.CLASS_NAME, 'container-fluid')
                break

            except:
                continue

    def wait_element(self, xpath: str, text: str = None):
        while not self.operation_thread.is_set():
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                pass
            except:
                continue

            if element.is_displayed():
                if not text:
                    break
                elif text in element.text:
                    break
                else:
                    time.sleep(0.75)
            else:
                time.sleep(0.75)

    def should_skip_address_correction(self):
        if self.is_random_subdistrict_used:
            self.is_random_subdistrict_used = False
            return True
        return False

    def _normalize_address_for_comparison(self, address):
        """Normalize Thai address variations and strip whitespace for fair comparison."""
        # Normalize 'Moo' (หมู่ที่/ม. → หมู่) — avoid matching "หมู่บ้าน"
        address = re.sub(r'(?:หมู่ที่|หมู่|ม\.)\s*(\d+)', r'หมู่\1', address)
        # Normalize 'Soi' (ซ. → ซอย)
        address = re.sub(r'(?:ซอย|ซ\.)\s*([^ตอจ\s]+)', r'ซอย\1', address)
        # Normalize 'Road' (ถ. → ถนน)
        address = re.sub(r'(?:ถนน|ถ\.)\s*([^ตอจ\s]+)', r'ถนน\1', address)
        # Normalize 'ตำบล/แขวง' to ค่าว่าง
        address = re.sub(r'(?:ตำบล|ต\.|แขวง)\s*', '', address)
        # Normalize 'อำเภอ/เขต' to ค่าว่าง
        address = re.sub(r'(?:อำเภอ|เขต|อ\.)\s*', '', address)
        # Normalize 'จังหวัด' to ค่าว่าง
        address = re.sub(r'(?:จังหวัด|จ\.)\s*', '', address)
        return address.replace(' ', '').replace('เลขที่', '')

    def _build_desired_addresses(self):
        """Build and clean the desired address strings from app data for comparison."""
        self.desired_address = re.sub(
            r'\n', " ", f"""{self.app.get_pure_address(self.app.address)}""".replace('\u200b', ''))
        self.desired_address = re.sub(r'\s{2,}', ' ', self.desired_address)

        self.desired_full_address = re.sub(
            r'\n', " ", f"""{self.app.get_pure_address(self.app.address)}  {self.app.nondistortedData['แขวง/ตำบล']}
            {self.app.nondistortedData['เขต/อำเภอ.1']}  {self.app.nondistortedData['จังหวัด.1']}
            {self.app.nondistortedData['รหัสไปรษณีย์.1']} """.replace('\u200b', ''))

        for prefix in ["อำเภอ", "เขต", "อ.", "ตำบล", "แขวง", "ต.", "จังหวัด", "จ.", "เลขที่"]:
            self.desired_full_address = self.desired_full_address.replace(prefix, "")

    def _fill_address_revision_form(self):
        """Open the SMCO customer edit page and fill in the corrected address fields."""
        self.get_tabs()
        if 'SMCO :: ลูกค้า' not in self.merged_dict:
            self.open_customer_edit_page()

        self.direct_to_customer_info()

        address_revise_btn = self.driver.find_element(
            By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[2]/div[1]/div/div[6]/a')
        address_revise_btn.click()

        addr_textarea_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[1]/div[2]/textarea'
        self.wait_element(addr_textarea_xpath)
        address_revise_input = self.driver.find_element(By.XPATH, addr_textarea_xpath)

        tel_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[13]/div[4]/input'
        country_dropdown_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[2]/div/span/span[1]/span/span[1]'
        country_li_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[2]/ul/li[2]'
        province_dropdown_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[4]/div/span/span[1]/span/span[1]'
        dropdown_input_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input'
        district_dropdown_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[6]/div/span/span[1]/span/span[1]'
        subdistrict_dropdown_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[8]/div/span/span[1]/span/span[1]'

        while True:
            try:
                # * กรอก Address
                address_revise_input.clear()
                self.desired_address = self.app.get_pure_address(self.desired_address)
                address_revise_input.send_keys(self.desired_address)

                # * Telephone
                self.driver.find_element(By.XPATH, tel_xpath).clear()
                self.driver.find_element(By.XPATH, tel_xpath).send_keys(self.app.cus_tel.get())

                # * Country → Thailand
                self.driver.find_element(By.XPATH, country_dropdown_xpath).click()
                self.dropdown_handler()
                self.driver.find_element(By.XPATH, country_li_xpath).click()

                # * Province
                self.driver.find_element(By.XPATH, province_dropdown_xpath).click()
                self.driver.find_element(By.XPATH, dropdown_input_xpath).clear()
                self.driver.find_element(By.XPATH, dropdown_input_xpath).send_keys(
                    self.app.cus_province.get().replace("จังหวัด", ""))
                time.sleep(1.75)
                self.driver.find_element(By.XPATH, dropdown_input_xpath).send_keys(Keys.ENTER)

                # * District
                self.driver.find_element(By.XPATH, district_dropdown_xpath).click()
                district_input = self.driver.find_element(By.XPATH, dropdown_input_xpath)
                self.select_li_from_dropdown(
                    input_element=district_input,
                    search_value=self.app.cus_district.get().replace("อำเภอ", "").replace("เขต", "").replace("ต.", ""),
                    th_field='districtNameTh',
                    en_field='districtNameEn',
                    place_type='district'
                )

                # * SubDistrict (click 3 ครั้งเพื่อให้แน่ใจว่า dropdown เปิด)
                subdistrict_btn = self.driver.find_element(By.XPATH, subdistrict_dropdown_xpath)
                subdistrict_btn.click()
                subdistrict_btn.click()
                subdistrict_btn.click()
                subdistrict_input = self.driver.find_element(By.XPATH, dropdown_input_xpath)
                self.select_li_from_dropdown(
                    input_element=subdistrict_input,
                    search_value=self.app.cus_sub_district.get().replace("ตำบล", "").replace("แขวง", "").replace("ต.", ""),
                    th_field='subdistrictNameTh',
                    en_field='subdistrictNameEn',
                    place_type='subdistrict'
                )

                # * Postal code
                zip_code_btn_xpath = "//span[@id='select2-zipCodeSel-container']"
                zip_code_btn_element = self.driver.find_element(By.XPATH, zip_code_btn_xpath)
                postcode = self.app.cus_postcode.get()
                try:
                    # * ถ้าหาไม่เจอมันจะ เข้า Except ไปเอง
                    self.driver.find_element(By.XPATH, f"""//span[@title='{postcode}']""")
                except:
                    try:
                        zip_code_btn_element.click()
                        self.dropdown_handler()
                        self.driver.find_element(
                            By.XPATH, f"""//li[@role='treeitem' and text()='{postcode}']""").click()
                    except Exception as err:
                        print(f"Postal code {postcode} cannot be found in dropdown, skip postal code selection")
                        if self.app.is_auto_invoice_mode.get():
                            logger.error(
                                f"order {self.cus_order}: auto invoice mode requires postal code selection but postal code {postcode} cannot be found in dropdown, stopping the process. Error details: {err}")
                            raise ValueError(
                                f"Postal code {postcode} cannot be found in dropdown, auto invoice mode requires postal code selection, stopping the process. Error details: {err}")

                print(f"""{self.cus_order}: Address Revise Complete""")
                break
            except ValueError as ve:
                print(f"Address Revise Error: Stopped by ValueError: {ve}")
                # ปิดหน้าต่างแก้ไขที่อยู่ เพื่อไม่ให้ค้าง
                try:
                    self.driver.execute_script("""
                        let m = document.querySelector('.modal.in, .modal.show');
                        if(m){
                            let b = m.querySelector('button.close, button[data-dismiss="modal"], button[ng-click*="cancel"], button[ng-click*="close"]');
                            if(b) b.click();
                            else { m.style.display='none'; m.classList.remove('in','show'); document.querySelectorAll('.modal-backdrop').forEach(bd=>bd.style.display='none'); }
                        }
                    """)
                except:
                    pass
                time.sleep(0.5)
                # กลับไปหน้าการขายให้ถูกต้องก่อน Throw Error
                try:
                    if 'SMCO :: เปิดการขาย' in self.merged_dict:
                        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
                except:
                    pass
                raise ve
            except Exception as err:
                # * Address Revise Error1 ละเอียดกว่าบอกต่ำแหน่งแบบเชื่อม parent child Traceback แบบเต็ม (Full Stack Trace)
                print(f"Address Revise Error1 : {traceback.format_exc()}")
                # print(f"Address Revise Error2 : {err}") #* Message (เฉพาะข้อความ Error) ไม่ละเอียด
                # logger.info(f"""{self.cus_order}: Address Revise Error1 : {traceback.format_exc()}""")
                # logger.info(f"""{self.cus_order}: Address Revise Error2 : {err}""")
                continue
         # * CLick Save Button (commented out but kept for completeness)
        if self.app.is_auto_invoice_mode.get():
            self.driver.find_element(By.XPATH, "//button[@ng-click='saveAddress()']").click()

        # * Wait for success popup
        self.app.is_bot_browser_busy.set(False)
        while not self.operation_thread.is_set():
            time.sleep(0.55)
            try:
                success_popup = self.driver.find_element(By.CSS_SELECTOR, '.swal2-icon.swal2-success')
                if success_popup.is_displayed():
                    self.app.is_bot_browser_busy.set(True)
                    break
            except:
                continue

        # * กลับไปหน้าการขาย
        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])

    def check_language(self, text: str):
        # ตรวจสอบว่ามีตัวอักษรภาษาอังกฤษหรือไม่
        if re.search(r'[a-zA-Z]', text):
            return 'En'
        # ตรวจสอบว่ามีตัวอักษรภาษาไทยหรือไม่
        elif re.search(r'[ก-๙]', text):
            return 'Th'
        else:
            return 'unknown'

    def tax_address_corrector(self, cus_name):
        print("cus_name: ", cus_name)
        if self.app.marketplace_target.get() == "LAZADA" and self.tax_info[self.app.tax_num.get()]:
            tax_data = self.tax_info[self.app.tax_num.get()]
            suffixes = {
                'subdistrict': self.check_language(
                    tax_data['sub_district'].replace("ตำบล", "").replace("แขวง", "").replace("ต.", "")),
                'district': self.check_language(
                    tax_data['district'].replace("อำเภอ", "").replace("เขต", "").replace("ต.", "")),
                'province': self.check_language(tax_data['province'].replace("จังหวัด", ""))}
        else:
            suffixes = {
                'subdistrict': self.check_language(self.app.nondistortedData['แขวง/ตำบล']),
                'district': self.check_language(self.app.nondistortedData['เขต/อำเภอ.1']),
                'province': self.check_language(self.app.nondistortedData['จังหวัด.1'])
            }
        # random จะเป็นการที่ user เลือกเองฉะนั้นไม่ต้องตรวจซ้ำ
        if self.should_skip_address_correction():
            print("Random subdistrict used, skipping address correction")
            return

        match = re.search(r'^C\d{1,}(?=-)', cus_name)  # * for customer code
        self.cus_code = match.group()

        customer_id = self.smco_req_find_customer_id(self.cus_code)
        if customer_id:
            cus_address = self.smco_req_find_cus_address(customer_id, **suffixes)
            # print("cus_address: ", cus_address)
        else:
            cus_address = {
                'address': '',
                'subdistrict': '',
                'district': '',
                'provice': '',
                'zip_code': ''
            }

        if not any(cus_address.values()):
            print("Address not matched")

        self.current_address = "".join(cus_address.values())
        self.current_address = re.sub(r'\s+', '', self.current_address)
        self._build_desired_addresses()

        print("compare self.current_address & self.desired_full_address")
        print(self.current_address.replace(' ', ''))

        print(self.desired_full_address.replace(' ', ''))

        current_normalized = self._normalize_address_for_comparison(self.current_address)
        desired_normalized = self._normalize_address_for_comparison(self.desired_full_address)
        logger.info(f"{self.cus_order}: compare current_normalized & desired_normalized")
        logger.info(current_normalized.replace(' ', ''))
        logger.info(desired_normalized.replace(' ', ''))

        if current_normalized != desired_normalized:
            # logger.info(f"{self.cus_order}: compare self.current_address & self.desired_full_address")
            # logger.info(self.current_address.replace(' ', ''))
            # logger.info(self.desired_full_address.replace(' ', ''))
            print("Customer Address is not correct")

            self._fill_address_revision_form()
        else:
            print("Customer address has already corrected")

        print("tax_address_corrector done!")

    def edit_cus_info(self, incoming_cus_code: int = None):
        while not self.operation_thread.is_set():
            try:
                if self.driver.find_element(
                        By.CSS_SELECTOR, f"div.btn-group.pull-right a.btn.btn-default").is_displayed():
                    self.driver.find_element(By.CSS_SELECTOR, f"div.btn-group.pull-right a.btn.btn-default").click()
                    break
                elif self.driver.find_element(By.CSS_SELECTOR, f"#vendorFormReal div:nth-child(1) > div:nth-child(2) > div > input").is_displayed():
                    current_cus_code = self.driver.find_element(
                        By.CSS_SELECTOR, f"#vendorFormReal div:nth-child(1) > div:nth-child(2) > div > input").get_attribute('title')
                    if current_cus_code == incoming_cus_code:
                        break
                    else:
                        raise ValueError("current_cus_code != incoming_cus_code, u r going to edit a wrong customer")
            except:
                time.sleep(1)
                continue
        # WebDriverWait(driver, 12).until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"div.col-xs-3 div.col-sm-7 input.form-control.input-height.ng-valid.ng-valid-maxlength.ng-touched")))
        # self.driver.find_element(By.CSS_SELECTOR, f"div.col-xs-3 div.col-sm-7 input.form-control.input-height.ng-valid.ng-valid-maxlength.ng-touched").send_keys(self.app.tax_num.get())
        WebDriverWait(
            self.driver, 12).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"/html/body/div[2]/div[2]/div/div[3]/div[1]/div[1]/div[1]/form/div[8]/div[2]/div/input")))
        self.driver.find_element(
            By.XPATH, f"/html/body/div[2]/div[2]/div/div[3]/div[1]/div[1]/div[1]/form/div[8]/div[2]/div/input").clear()
        self.driver.find_element(
            By.XPATH, f"/html/body/div[2]/div[2]/div/div[3]/div[1]/div[1]/div[1]/form/div[8]/div[2]/div/input").send_keys(self.app.tax_num.get())

    def duplicated_cus_name_resolver(self, popup_dup_element):
        # * ระบุตัวตนของ pop-up
        self.cus_code_element = popup_dup_element
        self.dup_popup_content = self.cus_code_element.text
        self.driver.find_element(
            By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]""").click()

        if ("Save Successfully." in self.dup_popup_content) or ("บันทึกข้อมูลสำเร็จ" in self.dup_popup_content):
            print("Not Duplicate, return")
            logger.info(f"{self.cus_order}: duplicated_cus_name_resolver():After adding cusname, the cusname is Not Duplicated")
            return
        print("close dup popup = ", self.dup_popup_content)

        # * เก็บรหัสเพื่อไปเสิชหาว่าdupที่ใคร
        matched_obj = re.search(r'^C.\d*', self.dup_popup_content, re.MULTILINE)
        print("matched_obj:", matched_obj)
        self.cus_code = matched_obj.group()
        current_url = self.driver.current_url
        matched_str = re.search(r'\/[A-z].*', current_url).group()
        self.origin = current_url.replace(matched_str, '')

        print("cus_code: ", self.cus_code)
        res_cus_data = self.app.smco_api.get_cus_data(
            origin=self.origin,
            req_text=self.cus_code, search_type='C',
            cookies=self.get_cookies_from_driver(),
        )
        cus_data_list = res_cus_data.json()
        cus_name = [cus_data.get('nameTh') for cus_data in cus_data_list
                    if cus_data.get('taxId') == self.app.tax_num.get()]
        if cus_name and cus_name[0]:
            print(
                f"order: {self.cus_order}: duplicated_cus_name_resolver: no need to update tax number because the tax number {self.app.tax_num.get()} is already associated with customer name {cus_name[0]} in SMCO")
            return

        self.get_tabs()
        if not 'SMCO :: ลูกค้า' in self.merged_dict:
            self.open_customer_edit_page()
        self.direct_to_customer_info(self.cus_code)
        self.edit_cus_info(self.cus_code)

        # * press the upper right conor save btn
        self.driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div[1]/div[2]/div[2]/a').click()

        # * press to close complete popup

        try:
            self.wait5.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     'body div.swal2-container div.swal2-modal.show-swal2.visible button.swal2-confirm.styled')))
            #! ซ้ำ กับช่วงท้ายของ add_new_customer()
            # self.driver.find_element(
            #     By.CSS_SELECTOR,
            #     'body div.swal2-container div.swal2-modal.show-swal2.visible button.swal2-confirm.styled').click()
        except:
            pass

#! Deprecated: data ที่ดึงมาโดยตรงมันแยก part ที่อยู่สวยงามอยู่ละ ไม่ต้องตัดแต่ง มั้ง
# * function แยก address:str ที่ได้จาก vatinfo ให้เป็น part ย่อย (เขต, แขวง, จังหวัด, ปณ.)-------------------------------------
    def classify_vatinfo_address(self, input):
        try:
            # Create a copy of the output dictionary
            result = input
            print("resultสำหรับ classify คือไร :", result)

            # Remove the "ตำบล" and everything after it from the address
            # address_only = re.compile(r'(?:ตำบล|ต\.).*')
            # result['address_shortened'] = address_only.sub('', result['address']).strip()

            # Define the regular expression pattern
            pattern = re.compile(r'ตำบล/แขวง\s+(\S+).*?เขต\s+(\S+).*?จังหวัด\s+(\S+)')

            # Use the pattern to find matches in the address
            matches = pattern.search(result['address'])

            # Extract the matched groups
            if matches:
                result['sub_district'] = matches.group(1)
                result['district'] = matches.group(2)
                result['province'] = matches.group(3)
            else:
                result['sub_district'] = None
                result['district'] = None
                result['province'] = None

            # Add a space after the word "บริษัท" in the company name
            result['name'] = re.sub(r'(บริษัท)\s*', r'\1 ', result['name'])

            return result
        except:
            print("Input is empty. Cannot be classify, result = ", result)
            return result

    def get_res_vatinfo(self, tax_num, tax_branch_number):
        tax_input = str(tax_num)
        branch = str(tax_branch_number)
        jsession_id = ''

        # เราจะไม่ใช้ cookies แต่จะใช้ค่าจาก class แรกสุด เพราะ
        # cookies = self.app.cookies['vatinfo']
        # print("cookies for reqtaxinfo: ", self.app.cookies['vatinfo'])

        params = ''

        json_data = {
            'nid': f'{tax_input}',
            'brano': f'{tax_branch_number}',
            'searchType': '1',
            'firNam': '',
            'midNam': '',
            'lasNam': '',
        }

        times = 1

        data2 = {
            'operation': 'GotoPage_Click',
            'goto_page': f'{times}',
            'tin': 'on',
            'txtTin': tax_input,
            'branotxt': '',
            'fname': 'null',
            'lname': 'null',
        }

        while not self.operation_thread.is_set():
            print("times = 1")
            response = self.smco_api.get_vatinfo(json_data)

            try:
                response.raise_for_status()
                # * Parse JSON response directly
                json_response = response.json()
                print("JSON response from VAT API:", json_response)

                # * Extract data from response (handle both dict and list formats)
                data_list = None
                if isinstance(json_response, dict):
                    # * API returns dict with 'data' key
                    data_list = json_response.get('data', [])
                    status = json_response.get('status', '')
                    print(f"API Status: {status}")
                elif isinstance(json_response, list):
                    # * API returns list directly
                    data_list = json_response

                # * Check if we have data
                if data_list and isinstance(data_list, list) and len(data_list) > 0 and status == '000':
                    # * Find the matching branch or use the first one
                    output_item = None
                    for item in data_list:
                        if item.get('brano', '') == tax_branch_number:
                            output_item = item
                            break

                    # * If no exact match, use first item
                    if not output_item:
                        output_item = data_list[0]

                    # * Normalize the data structure
                    output = self.normalize_vat_api_data(output_item, tax_branch_number)
                    print("Normalized output:", output)
                    break
                else:
                    print("No VAT info found from API")
                    output = {}
                    break

            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error occurred: {e}")
                output = {}
                break
            except Exception as e:
                print(f"An error occured: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                output = {}
                break

        return output

    def normalize_vat_api_data(self, api_item, requested_branch):
        """
        Transform VAT API JSON response to standardized dictionary format.

        Args:
            api_item (dict): Single item from VAT API response list
            requested_branch (str): The branch number that was requested

        Returns:
            dict: Standardized dictionary with keys:
                tax_num, branch, name, address, address_shortened,
                province, district, sub_district, postal_code
        """
        try:
            # * Extract เลขผู้เสียภาษี
            tax_num = api_item.get('nid', '') or api_item.get('pin', '')

            # * Extract สาขา and map to Thai
            branch_num = api_item.get('brano', '00000')
            if branch_num == '00000':
                branch = '(สำนักงานใหญ่)'
            else:
                branch = f'(สาขา{branch_num})'

            # * Extract ชื่อ
            name_title = api_item.get('bratitle', '') or api_item.get('title', '')
            name_body = api_item.get('branam', '') or api_item.get('firnam', '')
            name = f"{name_title}{name_body}".strip()

            # * Build full address from components
            address_parts = []

            # *  Building name
            bldgnam = api_item.get('bldgnam', '')
            if bldgnam and bldgnam != '-':
                address_parts.append(bldgnam)

            # *  Room and floor
            roomno = api_item.get('roomno', '')
            floorno = api_item.get('floorno', '')
            if roomno and roomno != '-':
                address_parts.append(f"ห้อง {roomno}")
            if floorno and floorno != '-':
                address_parts.append(f"ชั้น {floorno}")

            # Address number
            addno = api_item.get('addno', '')
            if addno:
                address_parts.append(addno)

            # Moo
            moono = api_item.get('moono', '')
            if moono and moono != '-':
                address_parts.append(f"หมู่ {moono}")

            # Village
            village = api_item.get('village', '')
            if village and village != '-':
                address_parts.append(village)

            # Soi
            soinam = api_item.get('soinam', '')
            if soinam and soinam != '-':
                address_parts.append(f"ซอย{soinam}")

            # Yaek
            yaek = api_item.get('yaek', '')
            if yaek and yaek != '-':
                address_parts.append(f"แยก{yaek}")

            # Road
            thnnam = api_item.get('thnnam', '')
            if thnnam and thnnam != '-':
                address_parts.append(f"ถนน{thnnam}")

            # Province, district, subdistrict components
            tamnam = api_item.get('tamnam', '')  # Sub-district
            ampnam = api_item.get('ampnam', '')  # District
            provnam = api_item.get('provnam', '')  # Province
            poscod = api_item.get('poscod', '')  # Postal code

            # * Build address_shortened (without tambon/district/province)
            address_shortened = ' '.join(address_parts)

            # * Build full address (with tambon/district/province)
            full_address_parts = address_parts.copy()
            if tamnam:
                full_address_parts.append(f"ตำบล/แขวง {tamnam}")
            if ampnam:
                full_address_parts.append(f"เขต {ampnam}")
            if provnam:
                full_address_parts.append(f"จังหวัด {provnam}")
            if poscod:
                full_address_parts.append(poscod)

            full_address = ' '.join(full_address_parts)

            # * Return standardized structure
            result = {
                'tax_num': tax_num,
                'branch': branch,
                'name': name,
                'address': full_address,
                'address_shortened': address_shortened,
                'province': provnam,
                'district': ampnam,
                'sub_district': tamnam,
                'postal_code': poscod,
            }

            print(f"Normalized VAT data: {result}")
            return result

        except Exception as e:
            print(f"Error normalizing VAT API data: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return {}

    def google_for_tambon(self, address, possible_tambons):
        # Todo address รับค่าเป็น dict
        # Todo possible_tambons รับค่าเป็น list

        input = f"{address['cleaned_address']} {address['amphoe']} {
            address['province']} {address['postal']}"

        session = requests.Session()

        params = {
            'q': f'{input}',
            'oq': f'{input}',
        }
        response = session.get('https://www.google.com/search', params=params)
        soup = BeautifulSoup(response.content, 'html.parser')
        # print("soup type:", type(soup))
        # print("soupหน้าตาเปนไง: ", soup)

        found_tambon = {}
        # * การหาแบบ alltag มาจาก https://www.skytowner.com/explore/finding_elements_that_contain_a_specific_text_in_beautiful_soup#:~:text=To%20find%20elements%20that%20contain,together%20with%20a%20lambda%20function.
        try:
            for possible_tambon in possible_tambons:
                found_tambon[f'{possible_tambon}'] = 0
                matched_tags = soup.find_all(lambda tag: len(
                    tag.find_all()) == 0 and possible_tambon in tag.text)
                for matched_tag in matched_tags:
                    # print("found_the_possible_tambon", possible_tambon,"matched_tag: ", matched_tag)
                    found_tambon[f'{possible_tambon}'] += 1
                # print(found_tambon)
                most_tambon = max(found_tambon, key=found_tambon.get)
            # print("คนที่คะแนนเยอะสุด", most_tambon)
            print("Loading Tambon...............")
            return most_tambon
        except:
            print('ไม่มี element')
            return possible_tambons[0]

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            # Use the directory where the script is located instead of current working directory
            base_path = os.path.dirname(os.path.abspath(__file__))
        result = os.path.join(base_path, relative_path)
        print("resource_path: ", result)
        return result

    def address_seperator(self, df, order):
        # * function ใช้สำหรับลูกค้าขอใบกำกับ เพราะมันต้องย้ายค่าตำบล ออกไปใส่ใบกำกับ
        print("assign_address order:", order)
        # เตรียมข้อมูล Pattern ที่อยู่คนไทย
        df.loc[:, 'ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป'] = df['ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป'].astype(str)
        df.loc[:, 'หมายเลขคำสั่งซื้อ'] = df['หมายเลขคำสั่งซื้อ'].astype(str)

        # * หาตำบลจากไฟล์
        target_row_index = df['หมายเลขคำสั่งซื้อ'] == order
        if any(target_row_index) == True:
            print("เจอ Order ใน ไฟล์")
            cus_address = df[target_row_index]['รายละเอียดที่อยู่'].iloc[0]
            print("cus_address", cus_address)
            full_cus_address = df[target_row_index]['ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป'].iloc[0]
            amphoe = str(df[target_row_index]['เขต/อำเภอ.1'].iloc[0])
            amphoe_short = amphoe.replace("อำเภอ", "").replace("เขต", "")
            province = str(df[target_row_index]['จังหวัด.1'].iloc[0])
            print("amphoe", amphoe)
            print("amphoe_short", amphoe_short)
            postal_code = str(df[target_row_index]['รหัสไปรษณีย์.1'].iloc[0])
            is_alert = False

            # เอาข้อมูลลูกค้ามาเทียบกับตาราง Pattern ที่อยู่คนไทย
            # จัวนี้ต้องผูกกับ exe
            # tambon_data_address = r'test\tkinter_test\Addresscleaner_TambonData.xlsx'

            tambon_data_address = self.resource_path(r"tables\Addresscleaner_TambonData.xlsx")
            df_thai_addr = pd.read_excel(tambon_data_address)
            allfiltered_df = df_thai_addr[(df_thai_addr['PostCodeMain'].astype(
                str) == postal_code) & (df_thai_addr['DistrictThaiShort'] == amphoe_short)]
            possible_tambons = list(allfiltered_df['TambonThaiShort'])
            possible_tambons.sort(key=len, reverse=True)

            print("ตำบลที่เป็นไปได้: ", possible_tambons)

            ##
            decent_tambon = []
            for tambon in possible_tambons:
                # * เขต แขวง อ ต ไรก็ตามเอาออกให้หมด

                if "ตำบล" in tambon:
                    tambon = re.sub(r'\bตำบล\b', '', tambon)
                elif "ต." in tambon:
                    tambon = re.sub(r'\bต.\b', '', tambon)
                elif "แขวง" in tambon:
                    tambon = re.sub(r'แขวง', '', tambon)
                # * ช่องว่างตั้งแต่ 1 อันขึ้นไป จะกลายเป็น โดนลบทั้งหมด
                tambon = re.sub(r'\s{1,}', '', tambon)

                # decent_tambon.append(tambon) เลิกใช้ list แล้ว เก็บค่าตรงๆไปเลย
                if tambon in full_cus_address:
                    decent_tambon = tambon
                    break

            # *ลบตำบลออก
            cleaned_address = self.app.get_pure_address(cus_address)

            # * หาค่าตัวแปรที่เหมาะสมลงใน decent_tambon
            if decent_tambon:
                # * เจอตำบลในไฟล์
                print("เลือกตำบลที่เหมาะสมมาแล้ว", decent_tambon)

            else:
                # * ตำบลในไฟล์ไม่มีต้อง Google เอา
                print("ไม่มีตำบลมาให้ต้อง search google")
                address_dict = {"cleaned_address": cleaned_address, "decent_tambon": decent_tambon,
                                "amphoe": amphoe_short, "province": province, "postal": postal_code}
                googled_tambon = self.google_for_tambon(address_dict, possible_tambons)
                decent_tambon = googled_tambon
                is_alert = True
                self.app.POP_UP.show("Caution!!", f""""ตำบล/แขวง"อันนี้มั่วมาโปรดตรวจสอบก่อนออกบิล""", "alert")
                self.is_random_subdistrict_used = True

            # * บางคนไม่ใส่ ตำบล ต แขวง ต้องรู้ ชื่อตำบลก่อนค่อยลบ
            print("ก่อนลบ", cleaned_address)
            #! ตรงนี้ผิด ลบทำไม
            # prog = re.compile(fr'{re.escape(decent_tambon)}.*')
            # cleaned_address = prog.sub('', cleaned_address)
            # print("ลบไม่ได้", cleaned_address)

            # * เลือกว่าจะ ตำบล หรหือ แขวง
            if decent_tambon in cus_address and ("กรุงเทพ" in cus_address or "กทม" in cus_address):
                decent_tambon = "แขวง" + tambon
            elif decent_tambon in cus_address:
                decent_tambon = "ตำบล" + tambon

            return {"cleaned_address": cleaned_address, "decent_tambon": decent_tambon, "amphoe": amphoe_short, "province": province, "postal": postal_code, "alert": is_alert}

        # * หาตำบลจากไฟล์ไม่เจอ
        elif any(target_row_index) == False:
            print("ไม่เจอOrder")

    def get_vatinfo_data(self, tax_num, branch="สำนักงานใหญ่"):
        # * value of branch can be "สำนักงานใหญ่" or ตัวเลขสาขา 5 หลัก
        print(f'ใช้ vatinfo_req และส่ง data body ด้วย : {str(tax_num)}, สาขา {str(branch)}')
        branch_for_search_from_res = branch
        if branch == "สำนักงานใหญ่":
            branch_for_search_from_res = "00000"

        # * หาชื่อใบกำกับจาก vatinfo
        result = self.get_res_vatinfo(str(tax_num), str(branch_for_search_from_res))

        # * กรณีหาจาก taxinfo ไม่มี ทำให้ต้อง หาจาก Excel ที่ import เข้ามา
        if bool(result) == False:
            print("no data from vatinfo, use manual data from excel instead")
            # * หาตำบล จาก address ที่ลูกค้าให้มา
            cus_address_from_table = self.address_seperator(self.app.data_frame, self.cus_order)

            manual_result_strcuture = {
                'tax_num': f'{self.app.tax_num.get()}',
                'branch': f'{self.app.branch_type}',
                'name': f'{self.app.cus_name.get()}',
                'address_shortened': f"{cus_address_from_table['cleaned_address']}",
                'province': f'{self.app.cus_province.get()}',
                'district': f'{self.app.cus_district.get()}',
                'sub_district': f"{cus_address_from_table['decent_tambon']}",
                'province': f'{self.app.cus_province.get()}',
                'address': f'{self.app.cus_address}',
                'postal_code': f"{self.app.nondistortedData['รหัสไปรษณีย์.1']}",
            }
            result = manual_result_strcuture
        else:
            result['name']
            # * ตรวจสอบดูว่า ค่าที่ response กลับมา มีช่องว่างตามเงื่อนไขหรือไม่
            x = re.search(r"^ห้างหุ้นส่วนจำกัด\s|^บริษัท\s", result['name'])

            if x:
                # * มีช่องว่าง แปลว่าดี
                print("เจอช่องว่าง response ไม่ต้องทำอะไร return ได้เลย", result['name'])
            else:
                # * ไม่มีช่องว่าง แปลว่าผิด Format
                result['name'] = result['name'].replace(
                    "บริษัท", "บริษัท ").replace(
                    "ห้างหุ้นส่วนจำกัด", "ห้างหุ้นส่วนจำกัด ")
                print("ไม่เจอช่องว่างจาก response แต่เพิ่มให้แล้ว", result['name'])

        return result

    def save_order_details(self, order_no, tracking_no, bill_no):
        """
        บันทึกข้อมูล Order Number, Tracking Number และ เลขบิลใบเสร็จ
        หลังจากเสร็จสิ้นหรือก่อนพิมพ์ โดยบันทึกเก็บไว้ใน logs/completed_orders.json
        และไฟล์ logs/completed_orders.csv โดยจัดเรียงคอลัมน์เป็น: เวลา, tracking, order, inv
        รวมถึงเตรียมความพร้อมในการส่ง API ไปเก็บยัง Server ในอนาคต
        """
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"[SaveOrderDetails] Order No: {order_no} | Tracking No: {tracking_no} | Bill No: {bill_no}")
            print(f"\n--- [SaveOrderDetails] ---")
            print(f"Time: {timestamp}")
            print(f"Tracking: {tracking_no}")
            print(f"Order: {order_no}")
            print(f"Bill/Receipt: {bill_no}")
            print(f"--------------------------\n")

            current_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.join(current_dir, "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 1. บันทึกลงในไฟล์ CSV (คอลัมน์เรียงตาม: time, tracking, order, inv)
            csv_path = os.path.join(log_dir, "completed_orders.csv")
            csv_file_exists = os.path.exists(csv_path)

            import csv
            try:
                with open(csv_path, mode='a', newline='', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file)
                    if not csv_file_exists:
                        writer.writerow(["time", "tracking", "order", "inv"])
                    writer.writerow([timestamp, str(tracking_no), str(order_no), str(bill_no)])
                logger.info(f"[SaveOrderDetails] บันทึกลง CSV สำเร็จ: {csv_path}")
            except Exception as csv_err:
                logger.error(f"[SaveOrderDetails] ไม่สามารถเขียนลง CSV ได้: {csv_err}")

            # 2. บันทึกลงในไฟล์ JSON ประวัติ
            json_path = os.path.join(log_dir, "completed_orders.json")
            order_data = {
                "timestamp": timestamp,
                "tracking_number": str(tracking_no),
                "order_number": str(order_no),
                "bill_number": str(bill_no)
            }

            orders_history = []
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        orders_history = json.load(f)
                except Exception as json_load_err:
                    logger.warning(f"ไม่สามารถโหลด completed_orders.json เดิมได้: {json_load_err}")

            orders_history.append(order_data)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(orders_history, f, indent=4, ensure_ascii=False)

            logger.info(f"[SaveOrderDetails] บันทึกลง JSON สำเร็จ: {json_path}")

            # 3. บันทึกเพิ่มเติมไปยัง Excel (ถ้าใช้งาน Accel mode)
            if hasattr(self.app, 'accel_mode') and hasattr(self.app.accel_mode, 'record_completed_order'):
                try:
                    self.app.accel_mode.record_completed_order(
                        order_no, tracking=tracking_no, bill_no=bill_no, status="Completed (จบกระบวนการ flow เต็ม)")
                    self.current_checkpoint = "บันทึกประวัติออเดอร์สำเร็จ (จบกระบวนการ flow เต็ม)"
                    logger.info(f"[SaveOrderDetails] บันทึกลง Excel ใน Sheet 'Completed_Orders' สำเร็จ")
                except Exception as xl_err:
                    logger.warning(f"ไม่สามารถบันทึกลง Excel ได้: {xl_err}")

            # 4. ส่งข้อมูลไปยัง API Server (เผื่อไว้สำหรับส่งข้อมูลเข้า Server ในอนาคต - Commented out)
            # api_url = "http://your-server-api-endpoint/api/orders"
            # headers = {"Content-Type": "application/json"}
            # payload = {
            #     "timestamp": timestamp,
            #     "tracking": str(tracking_no),
            #     "order_no": str(order_no),
            #     "inv_no": str(bill_no)
            # }
            # try:
            #     # response = requests.post(api_url, json=payload, headers=headers, timeout=5)
            #     # if response.status_code == 200:
            #     #     logger.info("[SaveOrderDetails] ส่งข้อมูลไป API Server สำเร็จ")
            #     # else:
            #     #     logger.warning(f"[SaveOrderDetails] ส่งข้อมูลไป API Server ล้มเหลว (Status Code: {response.status_code})")
            #     pass
            # except Exception as api_err:
            #     logger.error(f"[SaveOrderDetails] เกิดข้อผิดพลาดในการส่ง API: {api_err}")

        except Exception as e:
            logger.error(f"เกิดข้อผิดพลาดในการรัน save_order_details: {e}")

    def final_popup_after_green_btn_handler(self, is_etax, operation_obj):
        self.app.is_bot_browser_busy.set(False)
        auto_radio_times = 0
        loop_counter = 0  # * Counter for GC
        while not self.operation_thread.is_set():
            time.sleep(1)
            loop_counter += 1

            # * Periodic Garbage Collection (every ~60 seconds)
            if loop_counter % 60 == 0:
                print(f"Performing garbage collection... (Loop count: {loop_counter})")
                gc.collect()

            try:
                final_popup = self.driver.find_element(By.XPATH, """//div[@class = 'swal2-content']""")
                self.check_for_refresh_popup(final_popup)
                convert_full_tax_modal_element = self.driver.execute_script(
                    """ return document.querySelector("div[id='convertFullTaxModal']"); """
                )
                is_final_page = self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[1]/span[1]')
                #!พัง self.etax_radio_sendmail = self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[2]/label/input') element etax อยู่ไหนไม่รู้
                # print("is_final_page= ", is_final_page)
            except RefreshRequiredException:
                print("Refresh required")
                raise
            except:
                print("Element not found, continuing loop...")
                continue

            if final_popup.is_displayed():
                print("final_popup is displayed")
                try:
                    self.driver.find_element(
                        By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]""").click()
                    print('Click space behind final popup')
                except:
                    print('Cannot click space behind final popup')
                pass
            #! etax พังใช้ไม่ได้
            # elif is_final_page.is_displayed() == True and self.etax_radio_sendmail.is_displayed() == False:
            #     print("Radio ยังไม่โผล่")
            #     continue
            elif is_final_page.is_displayed() == False:
                print("หน้า final หายไป")
                pass
            # Todo ทำไม่ทัน UAT โดนปรับไปใช้คอมมาทก่อน
            elif convert_full_tax_modal_element.is_displayed():
                # while not self.operation_thread.is_set():
                #     print("convertFullTaxModal displayed")
                #     if not self.is_old_tax_form and self.app.is_tax_required.get():
                #         try:
                #             # * ต้องการใบกำกับ
                #             self.driver.execute_script(
                #                 """document.querySelector("input[ng-click='changeDataFtRadio(93003002)']").click();""")
                #             break
                #         except:
                #             continue
                #     else:
                #         try:
                #             # * ไม่ต้องการต้องการใบกำกับ
                #             self.driver.execute_script(
                #                 """document.querySelector("input[ng-click='changeDataFtRadio(93003001)']").click();""")
                #             self.driver.find_element(
                #                 By.XPATH, "//button[@ng-click='savePayment()' and @class='btn btn-success']").click()
                #             break
                #         except:
                #             continue
                while not self.operation_thread.is_set() and convert_full_tax_modal_element.is_displayed():
                    print("หน้าเลือกแบบย่อแบบเต็มยังแสดงผลอยู่")
                    if self.app.is_tax_required.get():
                        try:
                            # * ต้องการใบกำกับ
                            el = self.driver.find_element(
                                By.CSS_SELECTOR, "input[name='radioConvertFullTaxModal'][ng-value='93003002']")
                            self.driver.execute_script("arguments[0].click();", el)
                            cus_name_element = self.driver.find_element(
                                By.XPATH, "//span[@id='select2-memberSearchft-container']")
                            convert_tax_cus_name = None
                            convert_tax_cus_name = self.driver.execute_script(
                                "return arguments[0].getAttribute('title');", cus_name_element)
                            print("convert_tax_cus_name: ", convert_tax_cus_name)
                            if convert_tax_cus_name == None:  # ! ตรงนี้แม่ง err จริงๆด้วย แต่ก่อนหน้านี้แม่งใช้ได้นะ งงจัด
                                print("ยังไม่ได้เลือกใบกำกับ")
                                self.set_cus_name_search_type_last_page()
                                self.select_cusname_address_last_page()
                            break
                        except Exception as err:
                            print("radioConvertFulltallModalErr: ", err)
                            time.sleep(0.5)
                            continue
                    else:
                        print("ไม่เอาใบกำกับ กด submit ไปเลย แต่ไม่กล้ากดตอนนี้")
                    time.sleep(1)
                pass
            else:
                try:
                    # ? พังหมด
                    # print("Radio appeared")
                    if self.etax_radio_sendmail.is_displayed():
                        is_etax = True
                        print("Click Send Email Radio")
                        if auto_radio_times < 1:
                            self.etax_radio_sendmail.click()
                            print(
                                "Press Send Email, and break the loop")
                            auto_radio_times += 1
                        else:
                            print("เคยเลือกไปแล้ว")

                    elif not self.etax_radio_sendmail.is_displayed():
                        print("ไม่โชว์ก็ออก")

                except:
                    # print("radio has Disappeared")
                    pass

            if final_popup.is_displayed() == True:
                self.app.is_bot_browser_busy.set(True)
                print("final pop-up has finally displayed!")
                try:
                    final_popup_btn = self.wait50.until(EC.element_to_be_clickable(
                        # (By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]"""))) #! ปุ่มนี้น่าจะหายไปละ
                        (By.XPATH, """//div[@class = 'swal2-content']""")))
                    self.check_for_refresh_popup(final_popup_btn)
                    # *> ให้เวลาดูเลขบิล 1 วิ
                    time.sleep(1)

                    alert_text = self.driver.find_element(
                        By().XPATH, """//div[@class = 'swal2-content']""").text  # * ตำแหน่งแสดงเลขบิล

                    match = re.search(r'(?:ABB-)?B\d+-\w.*\d+-\d+', alert_text)
                    print("match: ", match)
                    # * ถ้าไม่มีบิล, match จะ = none ทำให้ .group() ไม่ได้ แล้ว return error ห
                    inv_number = match.group()
                    print("inv_number: ", inv_number)
                    self.app.update_log(f'เลขบิล: {inv_number}')
                    self.current_checkpoint = f"สร้างใบเสร็จสำเร็จ (เลขบิล: {inv_number})"

                    # # * เรียกใช้งานฟังก์ชันบันทึกข้อมูล Order Details (Commented out per user request)
                    # try:
                    #     order_no = self.app.cus_order.get()
                    #     tracking_no = ", ".join(self.tracking_manager.trackings) if hasattr(self, 'tracking_manager') and self.tracking_manager.trackings else ""
                    #     self.save_order_details(order_no, tracking_no, inv_number)
                    # except Exception as save_err:
                    #     print(f"Error calling save_order_details: {save_err}")

                    # * สลับไปreprintก่อนแล้วค่อยกลับมากด เพราะมันช้ากรอกรอไว้เลย
                    # * ไปหน้า Reprint ##########################################################################################
                    if is_etax and inv_number != "":
                        print("has etax")
                        try:
                            self.etax_reprint(inv_number)
                        except Exception as e:
                            print(f"etax_reprint error: {e}")
                            logger.error(f"etax_reprint error: {e}")
                        # * Update Accel file //////////////////////
                        if hasattr(self.app, 'accel_mode') and self.app.is_accel_mode_activated.get():
                            try:
                                tracking_no = ", ".join(self.tracking_manager.trackings) if hasattr(self, 'tracking_manager') and self.tracking_manager.trackings else ""
                                self.app.accel_mode.deduct_accel_file_data(
                                    self.app.cus_order,
                                    getattr(self.app.accel_mode, "used_serials", []))
                                self.app.accel_mode.record_completed_order(
                                    self.app.cus_order, tracking=tracking_no, bill_no=inv_number, status="Completed (etax)")
                            except Exception as xl_err:
                                print("Accel mode update failed:", xl_err)
                                logger.error(f"Accel mode update failed: {xl_err}")
                        # * ถ้ามี etax ก็ print แล้วจบไป
                        time.sleep(0.75)
                        # final_popup_btn.click() #! ปุ่มนี้น่าจะหายไปละ
                        break

                    # self.wait50.until(EC.invisibility_of_element_located((By.XPATH, """//div[@class = 'swal2-content']""")))
                    # time.sleep(1)
                    # final_popup_btn.click() #! ปุ่มนี้น่าจะหายไปละ

                    # * ลอง click container ดู ใช้ได้แล้ว
                    print("click container!")
                    self.driver.execute_script("document.querySelector('.swal2-overlay').click();")  # * อันนี้ดีย์

                    # * > printing
                    # * >> รอหน้า canvas โผล่ก่อน
                    self.wait50.until(EC.visibility_of_element_located(
                        (By.XPATH, '/html/body/div[2]/div[3]/div[10]/div/div[2]/div[2]/div/embed')))
                    time.sleep(1)

                    #! วิธี print แบบเก่า
                    # self.printtingPage()
                    # self.just_press_p()
                    # ! วิธี print แบบใหม่ // 2/2/2026 พัง มันจะมี thread ใหม่ทำงานชนกับ thread เก่า ทำให้ ปิดหน้า print ไม่ได้ ตอใช้ accel mode
                    # self.printing_thread = threading.Thread(
                    #     target=self.get_pdf_src_and_print, args=(inv_number,))
                    # self.printing_thread.start()
                    try:
                        self.get_pdf_src_and_print(inv_number)
                        self.current_checkpoint = "พิมพ์เอกสารใบเสร็จสำเร็จ"
                    except Exception as e:
                        print(f"get_pdf_src_and_print error: {e}")
                        logger.error(f"get_pdf_src_and_print error: {e}")

                    # * Update Accel file //////////////////////
                    if hasattr(self.app, 'accel_mode') and self.app.is_accel_mode_activated.get():
                        try:
                            tracking_no = ", ".join(self.tracking_manager.trackings) if hasattr(self, 'tracking_manager') and self.tracking_manager.trackings else ""
                            self.app.accel_mode.deduct_accel_file_data(
                                self.app.cus_order, getattr(self.app.accel_mode, "used_serials", []))
                            self.app.accel_mode.record_completed_order(
                                self.app.cus_order, tracking=tracking_no, bill_no=inv_number, status="Completed")
                        except Exception as xl_err:
                            print("Accel mode update failed:", xl_err)
                            logger.error(f"Accel mode update failed: {xl_err}")

                except RefreshRequiredException:
                    raise
                except Exception as err:
                    # time.sleep(1)
                    # print("ไม่ได้เลขบิล")
                    # final_popup.click()
                    try:
                        final_popup_btn.click()  # ! ปุ่มนี้น่าจะหายไปละ
                    except:
                        pass
                    print("พัง ข้ามไปเลยละกัน", err)
                    if hasattr(self.app, 'accel_mode') and self.app.is_accel_mode_activated.get():
                        try:
                            self.app.accel_mode.record_failed_order(self.app.cus_order, f"พังระหว่างยืนยันบิล: {err}")
                        except Exception as xl_err:
                            logger.error(f"Accel mode record failed order error: {xl_err}")

                break

                # * > รอหน้า canvas โผล่ก่อน
                # * >> แบบไม่มีระบบ ETAX มันจะ Process ไปหน้า print มันเลย wait element ของ canvas ได้ แล้วมันจะจบ แค่นี้

                #! WIP ต้องเปลี่ยนเป็น while loop แทน เพราะถ้าหาก ขั้นตอนด้านบนเป็น except มันจะรอนาน เพราะใช้ self.wait50
                #! ย้ายไปข้างบนแล้ว ถ้าข้างบนใช้ได้ข้างล่างลบทิ้งได้เลย
                # self.wait50.until(EC.visibility_of_element_located(
                #     (By.XPATH, '/html/body/div[2]/div[3]/div[10]/div/div[2]/div[2]/div/embed')))
                # time.sleep(1)
                # self.driver.find_element(
                #     By.XPATH, '/html/body/div[2]/div[3]/div[10]/div/div[2]/div[2]/div/embed')
                # self.printtingPage()
                # self.just_press_p()
                # break

            # * >> แบบมี ETAX มันจะ redirect กลับไปหน้าเดิม
            elif is_final_page.is_displayed() == False:
                print("End or back")
                if bool(
                    re.search(
                        r"\w{5}\-\w{3}-\w{10}", self.driver.find_element(
                            By.XPATH, "//div[@id='printZone']//div[@class='panel-title ng-binding']").text)):
                    print("ไปหน้าสุดท้าย จบ loop")
                    break
                elif self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/form/label') and self.emp_name_from_element == "":
                    print("มันจบละ")
                    break
                elif self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/form/label'):
                    print(f"กลับมาหน้าเดิม : {operation_obj.autofinal}")
                    operation_obj.autofinal = True  # * ถ้าอันนี้ยัง true แปลว่าหน้าท้ายยัง loop อยู่น่าจะทำให้กลับหน้าเก่าได้
                    break

            else:
                continue

                # try:
                #     print('จุดจบ')
                #     # * กดปุ่มใน pop-up สุดท้าย
                #     self.driver.find_element(
                #         By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]""")
                #     self.wait50.until(EC.visibility_of_element_located(
                #         (By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]""")))
                #     self.wait50.until(EC.element_to_be_clickable(
                #         (By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]"""))).click()
                #     # > รอหน้า canvas โผล่ก่อน
                #     self.wait50.until(EC.visibility_of_element_located(
                #         (By.XPATH, '/html/body/div[2]/div[3]/div[10]/div/div[2]/div[2]/div/embed')))
                #     self.printtingPage()
                #     break
                # except Exception as err:
                #     print('ไม่ใช่จุดจบ', err)
                #     pass

        # * ต้องใช้จริงๆเหรอ?
        # if self.app.accel_search_thread:
        #     self.app.accel_timer = threading.Timer(
        #         0.2, self.app.on_accel_thread_done)
        #     self.app.accel_timer.start()
        # else:
        #     print("'MyApp' object has no attribute 'accel_search_thread'")
        #     pass

    #! จำเป็นเหรอวะ
    # def last_page_tax_dialog_handler(self):
    #     while not self.operation_thread.is_set():
    #         try:


if __name__ == "__main__":
    def on_closing():
        """Properly cleanup all resources before closing the application"""
        print("Tkinter window is closing")

        try:
            # Stop all operation threads
            if hasattr(app, 'bot') and hasattr(app.bot, 'operation_thread'):
                print("Stopping operation threads...")
                app.bot.operation_thread.set()

            # Wait for printing thread to complete if it exists
            if hasattr(app, 'bot') and hasattr(app.bot, 'printing_thread'):
                if app.bot.printing_thread and app.bot.printing_thread.is_alive():
                    print("Waiting for printing thread to complete...")
                    app.bot.printing_thread.join(timeout=2.0)

            # Properly quit Selenium WebDriver
            if hasattr(app, 'bot') and hasattr(app.bot, 'driver'):
                try:
                    print("Closing WebDriver...")
                    app.bot.driver.quit()
                    print("WebDriver closed successfully")
                except Exception as e:
                    print(f"Error closing WebDriver: {e}")

            # Give threads time to finish cleanup
            time.sleep(0.5)

        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            # Destroy all popup windows
            PopUp.destroy_all()
            # Destroy the main window
            root.destroy()

    # def ctrl_saraea_copy(event):
    #     ctrl_state = event.state & 0x4 != 0  # 0x4 คือ flag สำหรับ Control key
    #     # 67 คือรหัสสำหรับสระแอในภาษาไทย (อาจแตกต่างบนระบบอื่นๆ)
    #     if ctrl_state and event.keycode == 67:
    #         event.widget.event_generate("<<Copy>>")

    # * เทคนิคคือ เช็คว่า ascii คือไร แล้วดูด้วยว่า นอกจากรับแบบ ascii แล้วรับแบบ keysym(ตัวอักษรจริง)ว่าตรงกับ ascii ไหม ถ้าไม่ตรงแปลว่าคนละภาษาแน่นอน เพราะ มันจะได้ ??
    # / มีไว้รองรับภาษาอื่นๆ ที่ไม่ใช่ภาษาอังกฤษโดยเฉพาะ เช่น ภาษาไทย
    def _onKeyRelease(event):
        # print("press :", event.keysym)
        ctrl = (event.state & 0x4) != 0
        if event.keycode == 88 and ctrl and event.keysym.lower() != "x":
            event.widget.event_generate("<<Cut>>")

        if event.keycode == 86 and ctrl and event.keysym.lower() != "v":
            event.widget.event_generate("<<Paste>>")

        if event.keycode == 67 and ctrl and event.keysym.lower() != "c":
            event.widget.event_generate("<<Copy>>")

        if event.keycode == 65 and ctrl and event.keysym.lower() != "a":
            event.widget.event_generate("<<SelectAll>>")

    root = CTk()
    # * options
    ctk.set_appearance_mode("Light")

    # * change icon
    root.iconbitmap(icon_path)

    # * > ทำลาย root tkInter เมื่อguiถูกปิด เพื่อไม่ให้มีการทำงานตกค้าง
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # * > ลืมไปละ น่าจะเกี่ยวกับช่องไฟ
    root.columnconfigure(0, weight=1)

    # * > ปรับขนาดจอ
    # root.resizable(False, False)

    # * > ทำให้กด copy, paste, cut จากภาษาอะไรก็ได้
    root.bind('<Key>', _onKeyRelease)

    # * > ทำให้กด F12 เพื่อกดปุ่ม Finish
    root.bind('<F12>', lambda event: app.finish_order())

    # * Create Instance
    app = MyApp(root)

    if getattr(sys, 'frozen', False):
        pyi_splash.close()
    root.mainloop()
    Print("Program closed")
