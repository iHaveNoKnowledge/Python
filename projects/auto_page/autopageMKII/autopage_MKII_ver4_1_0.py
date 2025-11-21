import base64
import datetime
import locale
import os
import random
import re
import subprocess
import sys
import threading
import time
import traceback
import winreg
from tkinter import *
from tkinter import filedialog, font, ttk

import customtkinter as ctk
import httpcore
import numpy as np
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
from functions.pos.frontpage.smcoformhandler import SMCOFormHandler
from googletrans import Translator
from loguru import logger
from openpyxl import load_workbook
from PIL import Image, ImageTk
from pypdf import PdfReader
from selenium import webdriver
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_auto_update.chrome_app_utils import ChromeAppUtils
from webdriver_auto_update.webdriver_manager import WebDriverManager

session = requests.Session()


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
        # * Variables------------------------------------------------------------------------------------
        self.root = root
        self.dev_account = ["62078", "61651", "62302"]
        self.is_bot_running = BooleanVar(value=False)
        # self.validate_input_variable = self.root.register(self.validate_input)
        self.user_id = StringVar(value="")
        self.user_pw = StringVar(value="")
        self.result = ""
        self.is_accel_mode = BooleanVar()
        self.is_accel_mode_activated = BooleanVar(value=False)
        self.is_seller_voucher_popup = BooleanVar(value=False)
        self.is_auto_invoice_mode = BooleanVar(value=False)
        self.table_location = ""

        # * Initialize AccelMode instance
        self.accel_mode = AccelMode(self)
        self.marketplace_target = StringVar(value="MarketPlace")
        self.bg_by_market_place = {'SHOPEE': '#ee4d2d', 'LAZADA': '#201adb', '': '#747474'}
        self.cus_order = StringVar(value="")
        self.tax_bool = BooleanVar(value=False)
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
        self.cus_cur_status = StringVar(value="")
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

        # * 2)Start a POS BOT WEBDRIVER instance ------------------------------------------------------------------------
        self.bot = Bot_POS(self.root, self)

    def demonic_cp_selection(self):
        self.bot.demonic_cp_bot(self.demonicCp_itemNo.get(), self.demonicCp_cpNo.get())

    def reset_browser_memory(self):
        """Callback สำหรับปุ่ม 'Reset Memory' Button"""
        try:
            if hasattr(self, 'bot') and hasattr(self.bot, 'driver'):
                self.bot.reset_all_tabs_memory()
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
                        memory_usage = self.bot.get_current_tab_memory_usage()
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

        # ตั้งค่าขนาดและตำแหน่งหน้าต่าง
        window_width = min(int(1000 * scaling_factor), screen_width - 100)
        window_height = min(int(900 * scaling_factor), screen_height - 100)
        x_position = max(0, min(
            (screen_width - window_width) // 2,
            screen_width - window_width - 20
        ))
        y_position = max(0, min(
            (screen_height - window_height) // 2,
            screen_height - window_height - 40
        ))

        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.root.title("Autosamatic ver4.1.0")
        self.root.configure(fg_color="#444")

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
        self.canvas = Canvas(self.root, bg="#444", width=800, height=600)

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
        self.main_frame = CTkFrame(self.canvas, fg_color="#444")

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

        # > Frame3 ImportFile Status and Bot Status
        self.import_file_frame = CTkFrame(
            self.main_frame,
            fg_color="#ccc",
        )
        self.import_file_frame.pack(side='top', anchor=W, padx=10, pady=(5, 0))

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

        # > Frame5 Products Lists
        self.products_list_frame = CTkFrame(
            self.main_frame,
            fg_color="#445"
        )
        self.products_list_frame.pack(side='top', padx=5, pady=5, fill=X)

        # > Frame6 Margetplace(MP) Products Lists
        self.mp_products_list_frame = CTkFrame(
            self.main_frame,
            fg_color="#444"
        )
        self.mp_products_list_frame.pack(side='top', padx=5, pady=5, fill="x")

        # > Frame7 The Upper Log Frame Demonic Frame
        self.demonic_frame = CTkFrame(
            self.main_frame,
            fg_color="#444"
        )
        self.demonic_frame.pack(side='top', pady=(0, 2))

        # > Frame2 Log Frame
        self.log_frame = CTkFrame(
            self.main_frame,
            fg_color="#444"
        )
        self.log_frame.pack(side='top', pady=20, fill="both")

        # * Create widgets in the main window
        self.create_widgets()

        # * start the scrollbar
        # self.canvas.update_idletasks()
        # self.canvas.config(scrollregion=self.canvas.bbox("all"))
        # self.canvas.bind_all("<MouseWheel>", lambda event: self.canvas.yview_scroll(int(-1*(event.delta/120)), "units"))
        # # self.canvas.bind("<Configure>", self.on_canvas_configure)

    def on_frame_configure(self, event=None):
        # """อัพเดท scroll region เมื่อ frame มีการเปลี่ยนแปลงขนาด"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        # """ปรับขนาด canvas window เมื่อ canvas มีการ resize"""
        # ปรับความกว้างของ window ใน canvas ให้เท่ากับความกว้างของ canvas
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def measure_text(self, text):
        return font.Font().measure(str(text).strip())

    def row_header_maker(self, list_of_cols):
        # * สร้าง header
        self.list_of_cols = list_of_cols
        self.colspan_amount = [1, 19, 2, 2, 2, 2]
        self.cols_location = [0, 1, 21, 23, 25, 27]
        # self.cols_width = [5, 100, 10, 10, 10, 10]
        # self.cols_width = [1, 22, 2, 2, 2, 2]
        self.cols_width = [40, 550, 80, 50, 80, 80]
        self.entry_list = []
        i = 0
        for header in self.list_of_cols:
            self.mp_products_header = CTkEntry(self.mp_products_list_frame, text_color="#000000",
                                               fg_color="#fff", width=int(self.cols_width[i]), height=14)
            self.mp_products_header.insert(0, header)
            self.entry_list.append(self.mp_products_header)
            i += 1

        for idx, entry in enumerate(self.entry_list):
            entry.grid(row=0, column=self.cols_location[idx], columnspan=self.colspan_amount[idx], sticky='nsew')
            entry.configure(state="readonly")

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
                self.inp1_search_btn.grid_remove()

            # * เอา gui ของ accel mode มาแปะแทน
            self.accl_dir_label.grid(row=0, column=1, padx=5)
            self.accl_dir_namedisplay_on_btn.grid(row=0, column=3)
            self.add_trans_to_accel_file_btn.grid(row=0, column=4)
            self.accl_start_btn.grid(row=0, column=5, padx=5)

        # * ถ้า Accel mode ไม่ทำงาน
        else:
            # * ลบ gui ของ accel mode ทิ้งรายตัว
            self.accl_dir_label.grid_remove()
            self.accl_dir_namedisplay_on_btn.grid_remove()
            self.add_trans_to_accel_file_btn.grid_remove()
            self.accl_start_btn.grid_remove()

            # * เอา gui ของ โหมดธรรมดา มาแปะแทน
            self.inp1_label_order.grid(row=0, column=1, padx=5)
            self.inp1_order_input.grid(row=0, column=3)
            self.inp1_search_btn.grid(row=0, column=5, padx=5)

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
        self.inp1_search_btn.grid(row=0, column=5, padx=5)

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

        # * >> search order Stop Button
        self.accel_stop_btn = CTkButton(
            self.entry_frame,
            font=self.font,
            text=f"Stop",
            command=self.stop_operation,
            fg_color="#bf2d2a",
            text_color="#ffffff",
            border_width=1.5,
            border_color="#732844",
            width=28,
            height=25
        )
        self.accel_stop_btn.grid(row=0, column=6, padx=5)

        # * > add transfers to accel mode component
        # * พวกนี้มันต้อง add แบบ toggle เพราะมันต้องสลับกับโหมดปกติ
        # * >> add transfer Button
        self.add_trans_to_accel_file_btn = CTkButton(
            self.entry_frame,
            text=f"เลือกใส่ Transfer",
            command=lambda: self.accel_mode.extract_sn_btn(
                self.accel_mode.accel_file_dir
            ),
            fg_color="#969696"
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
        self.display_acc_btn.grid(row=0, column=7, padx=5)

        # * > Accel mode
        # * >> Checkbox for activation toggle (Built-in label)
        self.accel_mode_checkbox = Checkbutton(
            self.entry_frame,
            text="Accel Mode",
            variable=self.is_accel_mode,
            command=self.accelmode_toggle
        )

        # ! __wip not ready
        # * > Auto Invoice Mode
        # * >> Checkbox for activation toggle (Built-in label)
        # self.auto_inv_mode_checkbox = Checkbutton(
        #     self.entry_frame,
        #     text="Auto Inv",
        #     variable=self.is_auto_invoice_mode,
        #     command=self.auto_invoice_mode_toggle,
        #     bg="#BF2D2A",
        #     fg="#FFF"
        # )
        # self.auto_inv_mode_checkbox.grid(row=0, column=9, padx=5)

        # * > Seller voucher Pop-up Checkbox
        # * >> Checkbox for activation toggle (Built-in label)
        self.seller_voucher_popup_checkbox = Checkbutton(
            self.entry_frame,
            text="S.V.Notice",
            variable=self.is_seller_voucher_popup,
            command=self.seller_voucher_popup_checkbox_toggle,
            bg="#BF2D2A",
            fg="#FFF"
        )
        self.seller_voucher_popup_checkbox.grid(row=0, column=10, padx=5)

        # * import_file_frame !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # * > Export File and Bot status location display component
        self.display_location_label = CTkLabel(self.import_file_frame, text=f"File located: ")
        self.display_location_label.grid(row=0, column=0, padx=(5, 0))

        self.display_location_result = CTkLabel(
            self.import_file_frame, text=f"ยังไม่เลือก Import File", fg_color="#FFF", corner_radius=10)
        self.display_location_result.grid(row=0, column=1, padx=10)

        self.display_location_result_btn = CTkButton(
            self.import_file_frame, text=f"ใส่ Import File", command=self.select_excel, fg_color="#969696")
        self.display_location_result_btn.grid(row=0, column=2, padx=(5, 0))

        # >> bot status
        self.display_bot_status_label = CTkLabel(
            self.import_file_frame, text=f"Bot Status: ไม่มีการทำงาน (⸝⸝ᴗ﹏ᴗ⸝⸝) ᶻ 𝗓 𐰁", fg_color="#1f242e",
            text_color="#ffec1f", padx=5)
        self.display_bot_status_label.grid(row=0, column=3, padx=(5, 0), )

        # >> Memory management buttons
        self.memory_reset_btn = CTkButton(
            self.import_file_frame, text="Reset Memory", command=self.reset_browser_memory, fg_color="#ff6b35",
            text_color="white", width=100, height=28)
        self.memory_reset_btn.grid(row=0, column=4, padx=(5, 0))

        self.memory_check_btn = CTkButton(
            self.import_file_frame, text="Check Memory", command=self.check_browser_memory, fg_color="#4a90e2",
            text_color="white", width=100, height=28)
        self.memory_check_btn.grid(row=0, column=5, padx=(5, 0))

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
        # >> Labels
        self.label_current_status = CTkLabel(
            self.order_details_frame, text="Status: ", fg_color="#FFF", corner_radius=4)
        self.label_current_status.grid(row=1, column=2, padx=(5, 0), columnspan=1)
        # >> Value display
        self.display_current_status = CTkLabel(
            self.order_details_frame, textvariable=self.cus_cur_status, text_color="#000000", fg_color="#8fd4ff",
            corner_radius=4)
        self.display_current_status.grid(row=1, column=3, padx=(1, 0), sticky=EW)

        # * > Is Tax?? display component
        # >> Labels
        self.label_is_tax = CTkLabel(self.order_details_frame, text="ใบกำกับ", fg_color="#FFF", corner_radius=4)
        self.label_is_tax.grid(row=2, column=2, padx=(5, 0), sticky='ew', columnspan=1)
        # >> Value display
        self.display_is_tax = CTkLabel(self.order_details_frame,
                                       textvariable=self.cus_tax_status, fg_color="#fff", corner_radius=4)
        self.display_is_tax.grid(row=2, column=3, padx=(1, 0), sticky=EW, columnspan=1)

        # * > Tax Number display component
        # >> Labels
        self.label_tax_number = CTkLabel(
            self.order_details_frame, text="เลขผู้เสียภาษี", fg_color="#FFF", corner_radius=4)
        self.label_tax_number.grid(row=2, column=4, padx=(5, 0), sticky='ew')
        # >> Value display
        self.display_tax_number = CTkEntry(self.order_details_frame, width=105, height=25,
                                           border_width=0, textvariable=self.tax_num, state="readonly", corner_radius=4)
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

        # * > Customer Name display component
        # * >> Labels
        self.label_cus_name = CTkLabel(
            self.order_details_frame, text="ชื่อ", fg_color="#FFF", corner_radius=4)
        self.label_cus_name.grid(row=2, column=0, padx=(5, 0), pady=(2, 2), sticky='ew')
        # * >> Value display
        self.display_cus_name = CTkEntry(
            self.order_details_frame, height=25, border_width=0,  textvariable=self.cus_name,  state="readonly")
        self.display_cus_name.grid(row=2, column=1, padx=(1, 0), sticky='ew')

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

        # * > Customter Products List
        self.label_cus_products = CTkLabel(self.products_list_frame, text="รายการสินค้า: ", fg_color="#FFF", height=1)
        self.label_cus_products.pack()

        # * >> สร้าง Treeview widget
        self.tree = ttk.Treeview(self.products_list_frame, columns=(
            "Productname", "Price", "QTY"), show="headings", height=8)
        self.tree.column("Productname", anchor=W, width=350)
        self.tree.column("Price", width=self.measure_text("Price")+10)
        self.tree.column("QTY", width=self.measure_text("QTY")+10)
        self.tree.heading("Productname", text="Product")
        self.tree.heading("Price", text="Price")
        self.tree.heading("QTY", text="QTY")

        self.y_scrollbar = ttk.Scrollbar(self.products_list_frame, command=self.tree.yview)
        self.y_scrollbar.pack(side="right", fill="y")

        self.tree.pack(side='bottom', fill=X)
        self.tree.config(yscrollcommand=self.y_scrollbar.set)

        # * > Margetplace Products display Header purchased products list header
        headers = ['No.', 'สินค้าทั้งหมด', 'ราคาต่อชิ้น', 'จำนวน', 'ราคาขายสุทธิ', 'ราคารวมรีเบท']
        self.row_header_maker(headers)

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
        self.demonicCp_btn = CTkButton(self.demonic_frame, text="SonicBlow!",
                                       command=self.demonic_cp_selection, width=60,  height=4)
        self.demonicCp_btn.grid(row=0, column=5, padx=(1, 0))

        # * > Log windows component
        self.report_log = CTkTextbox(self.log_frame, state=DISABLED, height=208)
        self.report_log.pack(side="left", fill="both", expand=True)

        ## * Create DataSourceSelector instance ###########
        self.data_source_selector = DataSourceSelector(self.root, self)
        self.user_account = UserAccount(self.root, self)

    def reset_all_display(self):
        self.result = ""
        self.table_location = ""
        self.cus_order.set("")
        self.tax_bool.set(False)
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
        for i in self.tree.get_children():
            self.tree.delete(i)

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

        # self.import_file_frame.config(
        #     fg_color=f'{self.bg_by_market_place[self.marketplace_target.get()]}')

        # * หลังจากได้ไฟล์เข้ามาแล้ว (self.table_location) เราจะทำการสร้างเป็น dataframe ด้วย function get_data_frame()
        self.get_data_frame()
        print("Table Location:", self.table_location)
        self.update_log("แอดไฟล์")

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

        # อุดค่าว่างก่อนไม่งั้น จะใช้ size() ไม่ได้
        #! คำเตือน ถ้าใช้ parameter inplace= ห้ามเก็บค่าเข้าตัวแปรเดิมเด็ดขาด ไม่งั้นมันจะพัง มันจะ error nontype รัวๆ
        # df['variation'].fillna(value="-", inplace=True)
        # ตรวจสอบ columntype
        column_type = df.dtypes
        print("createTime: ", column_type['createTime'])
        print("createTimeerr?:", df['createTime'])
        print("column_type: ", column_type['variation'])
        for column in df.columns:
            # print("ทำไมคืนค่า0: ", column_type[column])
            if column_type[column] == 'float':
                df[column] = df[column].replace(np.nan, 0)
            elif column_type[column] == 'object':
                df[column] = df[column].replace('nan', '')
            elif column_type[column] == 'str':
                df[column] = df[column].replace('nan', '')
            else:
                df.fillna(np.nan, inplace=True)

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

        # เก็บไว้ก่อน['billingName', 'billingAddr', 'billingAddr2', 'billingAddr4', 'billingAddr3', 'billingAddr5', 'taxCode', 'billingPhone', 'customerName', 'paidPrice', 'createTime', 'branchNumber']

        # ** ปรับแต่ง Column สำหรับ LAZADA--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        # * สร้าง sum_column  ขึ้นมาใหม่ --------------------------------------------------------
        # *> 'ราคาขายสุทธิ'
        # total_per_order_df = df.groupby('orderNumber')[
        #     'unitPrice'].sum().reset_index(name='ราคาขายสุทธิ')
        result_count['ราคาขายสุทธิ'] = result_count["จำนวน"] * \
            result_count["unitPrice"]

        # *> 'ชื่อผู้รับ'
        result_count['ชื่อผู้รับ'] = df['billingName']

        # *> 'หมายเลขโทรศัพท์'
        result_count['หมายเลขโทรศัพท์'] = df['billingPhone']

        # *> 'โค้ดส่วนลดชำระโดยผู้ขาย'
        total_sellerDiscountTotal_df = df.groupby('orderNumber')[
            'sellerDiscountTotal'].sum().reset_index(name='โค้ดส่วนลดชำระโดยผู้ขาย')
        total_sellerDiscountTotal_df['โค้ดส่วนลดชำระโดยผู้ขาย'] *= -1

        # *> 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ'
        total_shippingfee_df = df.groupby('orderNumber')['shippingFee'].sum(
        ).reset_index(name='ค่าจัดส่งที่ชำระโดยผู้ซื้อ')

        # * ปรับแต่งค่าใน Column
        # result_with_additional_columns_df = result_with_additional_columns_df['branchNumber'].map(lambda x: )

        # *  รวม dataframe เป็น dataframe ใหม่
        # merge1_df = pd.merge(result_count, total_per_order_df,
        #                      on='orderNumber', how='left')
        merge2_df = pd.merge(result_count, total_sellerDiscountTotal_df, on='orderNumber', how='left')
        merge3_df = pd.merge(
            merge2_df, result_with_additional_columns_df, on='orderNumber', how='left')
        result_df = pd.merge(merge3_df, total_shippingfee_df, on='orderNumber', how='left')
        # result_df = pd.concat([result_count, total_per_order_df,
        #                    total_sellerDiscountTotal_df, total_shippingfee_df], ignore_index=True)

        # * เราต้องการ column ที่มีชื่อต่างกัน แต่ข้อมูลเหมือนกัน เลยต้อง copy column เพิ่ม
        result_df['รายละเอียดที่อยู่'] = result_df['billingAddr'].copy()

        result_df['ประเภทสาขา'] = result_df['branchNumber'].copy()
        print("result_df d-type", type(result_df['ประเภทสาขา']))

        # * สกัดและหาเลขสาขา จากข้อมูลที่กรอกมั่วๆไร้ซึ่ง pattern จาก lazada exportfile และเก็บไว้ในตัวแปร extracted_branch_df สาขาจะแสดงเป็นเลข 5 หลักแทนช่องว่างด้วย 0 แต่สาขา 00000 จะแสดงเป็น "สำนักงานใหญ่"
        extracted_branch_df = result_df['ประเภทสาขา'].apply(self.find_branch)

        # * เปลี่ยน ค่าใน col branchNumber ให้กลายเป็นบอกเฉพาะเลขสาขาถ้าเป็นสาขาย่อย และ เป็นค่าว่างถ้าเป็นสำนักงานใหญ่
        result_df['branchNumber'] = extracted_branch_df.copy()
        result_df['branchNumber'] = result_df['branchNumber'].map(
            lambda row: "" if row == "สำนักงานใหญ่" else row)

        # * นำค่าที่สกัดและแปลงจากตัวแปร extracted_branch_df มาหาประเภทสาขา หาก ค่าใน cell เป็น"สำนักงานใหญ่" จะ return "สำนักงานใหญ่" ถ้าไม่ใช่ จะแสดงเป็น "สาขาย่อย" (มีค่าเป็นเลขสาขา จะ return เป็น สาขาย่อย)
        result_df['ประเภทสาขา'] = extracted_branch_df.map(
            lambda row: "สำนักงานใหญ่" if row == "สำนักงานใหญ่" else "สาขาย่อย")

        # * แยกย่อยออกมาจาก บรรทัดบนเพื่อ กรองส่วนที่ไม่มีเลขให้เป็นคำว่า สาขาย่อย เพราอันบน มันจะเปนสำนักงานใหญ่หมดถ้าหากหาค่าไม่ได้
        # result_df['ประเภทสาขา'] = result_df['taxCode'].apply(
        #     lambda row: "สาขาย่อย" if len(row) == 0 else "สำนักงานใหญ่")
        result_df['ประเภทสาขา'] = result_df['taxCode'].apply(
            lambda row: "สาขาย่อย" if (isinstance(row, str) and len(row) == 0) else "สำนักงานใหญ่")
        # result_df['ประเภทสาขา'] = result_df['taxCode'].apply(
        #     lambda row: print("ทำไมไม่ได้สาขาย่อยวะ", row) if (isinstance(row, str) and len(row) == 0) else print("ทำไมไม่ได้สาขาย่อยวะ", type(row)))
        result_df['ประเภทสาขา'] = result_df['taxCode'].apply(
            lambda row: "สาขาย่อย" if (pd.notna(row) and isinstance(row, str) and len(
                row) == 0) else "สำนักงานใหญ่" if isinstance(row, str) else "สาขาย่อย"
        )

        # * เปลี่ยนค่าใน Col billingAddrs ตัดภาษาอังกฤษออก เนื่องจาก ที่อยู่ที่ได้จาก exportfile laz จะมี pattern เป็น ไทย/ อังกิก เช่น "บางปะกง/ Bang Pakong"
        # >> addr4 = เขต/อำเภอ, addr3 = จังหวัด
        address_divs = ['billingAddr4', 'billingAddr3']
        for address_div in address_divs:
            result_df[f'{address_div}'] = result_df[f'{address_div}'].map(
                lambda row: row.split('/')[0].strip())

        # * เปลี่ยน Dtype ของ Column ['createTime'] (วันที่ทำการสั่งซื้อ) จาก Series ให้เป็นobjวันที่ เนื่องจากอันเดิมมันเอาไป Sort ไม่ได้ เวลาออกเป็นตาราง
        result_df['createTime'] = pd.to_datetime(
            result_df['createTime'], format='mixed', dayfirst=True)
        # * >  แปลง objวันที่ ให้กลายเป็น number ใน excel เพื่อให้แสดงผลใน cel เหมือนกับ exported file ของ shopee
        result_df['createTime'] = result_df['createTime'].dt.strftime(
            '%Y-%m-%d %H:%M')

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
        result_df['หมายเลขคำสั่งซื้อ'] = result_df['หมายเลขคำสั่งซื้อ'].astype(
            str)

        print("ตารางใหม่")
        print(result_df)
        excel_file_path = "output_test.xlsx"
        result_df.to_excel(excel_file_path, index=False,
                           na_rep="", engine="openpyxl")
        return result_df

    def f(self, d):
        return '{0:n}'.format(d)

    def get_data_frame(self):
        print("มีป่าวหว่า", self.table_location)
        self.file_path = self.table_location
        print('self.marketplace_target.get()', self.marketplace_target.get())
        shopee = {'หมายเลขประจำตัวผู้เสียภาษี': str, 'รหัสไปรษณีย์.1': str, 'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี': str,
                  'จำนวน': int, 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ': float, 'โค้ดส่วนลดชำระโดยผู้ขาย': float, 'แขวง/ตำบล': str,
                  'ประเภทสาขา': str, 'สาขาย่อย': str, 'รหัสประจำสาขา': str, 'หมายเหตุจากผู้ซื้อ': str, 'บันทึก': str}
        lazada = {
            'หมายเลขประจำตัวผู้เสียภาษี': str, 'รหัสไปรษณีย์.1': str, 'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี': str,
            'จำนวน': int, 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ': float, 'โค้ดส่วนลดชำระโดยผู้ขาย': float, 'แขวง/ตำบล': str,
            'ประเภทสาขา': str, 'สาขาย่อย': str, 'รหัสประจำสาขา': str, 'หมายเหตุจากผู้ซื้อ': str, 'บันทึก': str,
            'taxCode': str}
        self.columns_preset = shopee if self.marketplace_target.get(
        ) == 'SHOPEE' else lazada if self.marketplace_target.get() == 'LAZADA' else ''
        try:
            if self.marketplace_target.get() == 'SHOPEE':
                print("เปลี่ยน dtype เป็น form shopee")
                self.data_frame = pd.read_excel(
                    self.file_path, dtype=self.columns_preset)
                self.data_frame['หมายเลขประจำตัวผู้เสียภาษี'].astype(str)
            elif self.marketplace_target.get() == 'LAZADA':
                self.data_frame = self.group_by_order(
                    self.file_path, self.columns_preset)

                self.data_frame['โค้ดส่วนลดชำระโดยผู้ขาย'].astype(float)
                self.data_frame['หมายเลขประจำตัวผู้เสียภาษี'].astype(str)

            print("df มี type เป็นไร", type(self.data_frame))
            # print("self.data_frame หน้าตาเปนไง: ", self.data_frame) มันยาว
            if self.data_frame.empty:
                print("ไม่มี Data Frame")
            else:
                print("มี Data Frame")
        except FileNotFoundError:
            print("File not found.")
        except NameError as e:
            print(f"ตัวแปร '{e.name}' ไม่มีอยู่จริง")
        # except Exception as e:
        #     print(f"อะไรสักอย่างพัง {e}")

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
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.total_price = 0
        for product in products_list:
            product_name = product["เลขอ้างอิง SKU (SKU Reference No.)"]
            price = product["ราคาขายสุทธิ"]
            shopee_rebate = product['ส่วนลดจาก Shopee']
            price_plusrebate = price+shopee_rebate
            QTY = product['จำนวน']
            self.total_price += price_plusrebate
            self.tree.insert("", "end", values=(
                product_name, self.f(price_plusrebate), QTY))

        # * Shopee + ค่าขนส่ง แต่ Lazada ไม่ต้อง + ค่าขนส่งในบางกรณี
        if self.marketplace_target.get() == 'SHOPEE':
            self.total_price += self.cus_ship_cost.get()
            self.phase1_sum_price = self.total_price
            self.tree.insert("", "end", value=("ค่าขนส่ง", self.f(self.cus_ship_cost.get()), 1))
            self.total_price -= self.cus_seller_voucher.get()
            self.tree.insert("", "end", value=("Seller Voucher",  "-"+self.f(self.cus_seller_voucher.get()), 1))
            self.tree.insert("", "end", values=("ราคาที่ต้องออก", self.f(self.total_price)))
            self.tree.insert("", "end", values=("Shopee Voucher", self.f(
                self.nondistortedData['โค้ดส่วนลดชำระโดย Shopee (เช่น โค้ดจากโปรแกรม ร้านโค้ดคุ้ม, โค้ดส่วนลด Shopee, โค้ดส่วนลด Shopee Mall)']*-1)))
            self.tree.insert("", "end", values=("ลูกค้าจ่ายทั้งหมด", self.f(self.nondistortedData['จำนวนเงินทั้งหมด'])))

        elif self.marketplace_target.get() == 'LAZADA':
            # * มันต้องมีทั้ง ราคาที่ต้องออกแบบ +ขนส่งกับ ไม่มีขนส่ง
            self.total_price -= self.cus_seller_voucher.get()
            self.tree.insert("", "end", value=("Seller Voucher",  "-"+self.f(self.cus_seller_voucher.get()), 1))

            # > แบบไม่มีขนส่ง
            self.total_price_no_ship_cost = self.total_price
            self.tree.insert("", "end", values=("ราคาที่ต้องออก(Noขนส่ง)", self.f(self.total_price_no_ship_cost)))

            # > แบบมีขนส่ง
            self.total_price_with_ship = self.total_price + self.cus_ship_cost.get()
            self.tree.insert("", "end", value=("ค่าขนส่ง", self.f(self.cus_ship_cost.get()), 1))
            self.tree.insert("", "end", values=("ราคาที่ต้องออก(+ขนส่ง)", self.f(self.total_price_with_ship)))

    def get_pure_address(self, cus_address):
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

    def clean_address(self, address):
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
        # * method นี้ จะ return ไม่ "สำนักงานใหญ่" ก็ เลขสาขาที่เป็นเลข 5 หลัก เท่านั้น
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
            print("name.get()ก่อนทำการ standardized", self.cus_name.get())
            self.cus_name.set(self.tax_name_standardizer(self.cus_name.get()))
            print("name.get()หลังจากทำการ standardized", self.cus_name.get())
        else:
            print("Customer Name is empty")

    def order_search(self, order,  on_complete):
        print("order_search ทำงาน")
        self.on_complete = on_complete
        self.order = order.strip()
        if len(self.order) < 14:
            raise ValueError("The Order length is not correct")
        self.cus_order.set(self.order)

        # # * Memory management - ตรวจสอบและจัดการ memory ก่อนเริ่มงาน
        # if hasattr(self, 'bot') and hasattr(self.bot, 'pre_operation_memory_cleanup'):
        #     self.bot.pre_operation_memory_cleanup("search_order")

        differential_col_data = ['เลขอ้างอิง SKU (SKU Reference No.)', 'ชื่อสินค้า',
                                 'ราคาขาย', 'จำนวน', 'ราคาขายสุทธิ', 'ส่วนลดจาก Shopee', 'ชื่อตัวเลือก']
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
            if not self.data_frame[(self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order)].empty:
                # ? self.filter_data จะเป็นการทำComparisionให้เรียบร้อยแล้วคืน DataFrame ที่กรองแล้วทันที --------------------ไวกว่า
                self.filter_data = self.data_frame[(self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order)]
                # ? self.target_row เป็น การหา เอาคอล "หมายเลขคำสั่งซื้อ" ทั้งหมดมาตรวจแล้วคืนค่าเป็น Boolean เท่านั้น ---------ช้ากว่า
                self.target_row = self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order
                self.cus_masked_name = self.data_frame[self.target_row]['ชื่อผู้รับ'].iloc[0]
                self.cus_masked_tel = self.data_frame[self.target_row]['หมายเลขโทรศัพท์'].iloc[0]
                self.order_status = self.data_frame[self.target_row]['สถานะการสั่งซื้อ'].iloc[0]

                # *  ของมีอะไรบ้าง dtypeหลังใช้ .to_dict('records') จะเป็น list of dict ฉันั้น self.items = [{}, {}, ...]
                self.items = self.data_frame[differential_col_data][self.target_row].to_dict('records')
                # * ตัดช่องว่าง
                for row in self.items:
                    row['เลขอ้างอิง SKU (SKU Reference No.)'] = row['เลขอ้างอิง SKU (SKU Reference No.)'].replace(
                        ' ', '')

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
                self.widgets_no_col_lst = []
                self.widgets_product_col_lst = []
                self.widgets_prc_unit_lst = []
                self.widgets_qty_lst = []
                self.widgets_total_prc_lst = []
                self.widgets_total_rebt_prc_lst = []
                self.widgets_demonic_cp_btn_lst = []
                self.all_cols = [
                    self.widgets_no_col_lst,
                    self.widgets_product_col_lst,
                    self.widgets_prc_unit_lst,
                    self.widgets_qty_lst,
                    self.widgets_total_prc_lst,
                    self.widgets_total_rebt_prc_lst,
                    self.widgets_demonic_cp_btn_lst
                ]
                self.idx = 0
                self.mimic_list_item_states = []
                for item_idx, row in enumerate(self.items):
                    # self.no_col_value_widget = CTkEntry(self.mp_products_list_frame,width=int(self.cols_width[0]), height=14)
                    self.no_col_value_widget = CTkButton(
                        self.mp_products_list_frame,
                        width=int(self.cols_width[0]),
                        height=14
                    )
                    # self.no_col_value_widget.insert(0, self.idx+1)
                    self.no_col_value_widget.configure(
                        text=str(self.idx + 1),
                        fg_color="#81ed55",
                        text_color="#1E1E1E",
                        border_width=2,
                        border_color="#969696",
                        command=lambda idx=item_idx: self.bot.AutoAddProduct.auto_add_product(self.correct_sku_pattern(
                            self.items[idx]['เลขอ้างอิง SKU (SKU Reference No.)']), self.items[idx]['จำนวน'])

                    )

                    self.widgets_no_col_lst.append(self.no_col_value_widget)
                    self.idx += 1

                    self.product_col_name_value_widget = CTkEntry(
                        self.mp_products_list_frame, width=int(self.cols_width[1]), height=14)
                    self.product_col_name_value_widget.insert(
                        0, f"{" ".join(self.correct_sku_pattern(str(row['เลขอ้างอิง SKU (SKU Reference No.)'])))}{' : ' + str(row['ชื่อตัวเลือก']) if not pd.isna(row['ชื่อตัวเลือก']) else ''} : {str(row['ชื่อสินค้า'])}")
                    self.widgets_product_col_lst.append(self.product_col_name_value_widget)
                    self.mimic_list_item_states.append(f"{str(row['เลขอ้างอิง SKU (SKU Reference No.)'])}")

                    self.price_unit_col_value_widget = CTkEntry(
                        self.mp_products_list_frame, width=int(self.cols_width[2]), height=14)
                    self.price_unit_col_value_widget.insert(0, f"{float(row['ราคาขาย']):,.2f}")
                    self.widgets_prc_unit_lst.append(self.price_unit_col_value_widget)

                    self.qty_col_value_widget = CTkEntry(
                        self.mp_products_list_frame, width=int(self.cols_width[3]), height=14)
                    self.qty_col_value_widget.insert(0, int(row['จำนวน']))
                    self.widgets_qty_lst.append(self.qty_col_value_widget)

                    self.total_price_col_value_widget = CTkEntry(
                        self.mp_products_list_frame, width=int(self.cols_width[4]), height=14)
                    self.total_price_col_value_widget.insert(0, f"{float(row['ราคาขายสุทธิ']):,.2f}")
                    self.widgets_total_prc_lst.append(self.total_price_col_value_widget)

                    self.total_rebate_price_col_value_widget = CTkEntry(
                        self.mp_products_list_frame, width=int(self.cols_width[5]), height=14)
                    self.total_rebate_price_col_value_widget.insert(
                        0, f"{float(row['ราคาขายสุทธิ'])+float(row['ส่วนลดจาก Shopee']):,.2f}")
                    self.widgets_total_rebt_prc_lst.append(self.total_rebate_price_col_value_widget)

                    # # * ปุ่ม CP นรกใช้ไม่ได้เก็บไว้พิจารณา
                    # self.demonic_cp_btn = CTkButton(self.mp_products_list_frame, text="xxx", fg_color="#969696", command=self.search_order, width=10)
                    # self.widgets_demonic_cp_btn_lst.append(self.demonic_cp_btn)

                for col_idx, col_list in enumerate(self.all_cols):
                    for idxrow, col in enumerate(col_list):
                        col.grid(
                            row=idxrow + 1,
                            column=self.cols_location[col_idx],
                            columnspan=self.colspan_amount[col_idx]
                        )
                        if col_idx != 1:
                            col.configure(state="readonly")

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
                    self.tax_bool.set(False)
                    self.cus_tax_status.set("ไม่ขอใบกำกับ")
                    self.display_is_tax.configure(fg_color="#6ec7ff", text_color="#000", font=("Chiller", 10, "normal"))
                    self.tax_num.set("")
                elif tax_num_only != "ไม่มีเลข" and len(tax_num_only) != 13:
                    if len(tax_num_only) > 13:
                        self.tax_bool.set(False)
                        self.cus_tax_status.set("ขอ//เลขเกิน")
                    elif len(tax_num_only) < 13:
                        self.tax_bool.set(False)
                        self.cus_tax_status.set("ขอ//เลขไม่ครบ")

                    self.display_is_tax.configure(fg_color="#8502d1", text_color="#FFF", font=("Chiller", 10, "normal"))
                    self.tax_num.set(tax_num_only)

                else:
                    if "สำนักงานใหญ่" in self.branch_type:
                        self.tax_bool.set(True)
                        self.cus_tax_status.set("ขอใบกำกับ สนงใหญ่")
                        self.display_is_tax.configure(fg_color="#ff0000", text_color="#FFF",
                                                      font=("Chiller", 10, "bold"))
                        self.tax_num.set(tax_num_only)
                    elif self.branch_type == "สาขาย่อย" and (not pd.isna(self.data_frame[self.target_row]['รหัสประจำสาขา'].iloc[0])):
                        self.tax_bool.set(True)
                        self.cus_tax_status.set("ขอใบกำกับ สาขาย่อย")
                        self.display_is_tax.configure(fg_color="#ff0055", text_color="#FFF",
                                                      font=("Chiller", 10, "bold"))
                        self.tax_num.set(tax_num_only)
                    else:
                        self.tax_bool.set(True)
                        self.cus_tax_status.set("ไม่ขอแต่มีเลข")
                        self.display_is_tax.configure(fg_color="#ff9e36", text_color="#FFF",
                                                      font=("Chiller", 12, "bold"))
                        self.tax_num.set(tax_num_only)

                if self.tax_bool.get() == True and len(tax_num_only) == 13:
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
                    self.cleaned_address = f"""{self.get_pure_address(self.clean_address(self.address))} {self.nondistortedData['แขวง/ตำบล']} {
                        self.nondistortedData['เขต/อำเภอ.1']} {self.nondistortedData['จังหวัด.1']} {self.nondistortedData['รหัสไปรษณีย์.1']}"""

                    if "กรุงเทพ" in self.cleaned_address:
                        self.cleaned_address = self.cleaned_address.replace("จังหวัด", '')
                    self.search_result = {
                        "status": self.order_status,
                        "is_tax": self.tax_bool.get(),
                        "address": self.cleaned_address,
                        "details": self.nondistortedData,
                        "items": self.items
                    }

                if self.marketplace_target.get() == 'SHOPEE':
                    self.cleaned_address = ""
                    # * ถ้าขอใบกำกับค่อยใส่ ถ้าไม่ ก็ "" ไป
                    if self.tax_bool.get():
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
                        "is_tax": self.tax_bool.get(),
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
                if self.tax_bool.get():
                    self.cus_province.set(self.nondistortedData['จังหวัด.1'].strip())
                    self.cus_district.set(self.nondistortedData['เขต/อำเภอ.1'].strip())
                if self.cus_sub_district != "":
                    self.cus_sub_district.set(self.nondistortedData['แขวง/ตำบล'])
                else:
                    self.cus_sub_district.set('')
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
                self.reset_all_display()
                logger.info(f"Order: {self.search_query} Not found in the shopee's Export File")

        else:
            self.reset_all_display()

        print("ก่อน seller voucher popup")
        if self.is_seller_voucher_popup.get() and self.cus_seller_voucher.get() > 0:
            txtsize = self.cal_adjusted_font_size(1920, 24)
            self.POP_UP.show(
                "Seller Voucher Notification",
                f"มี Seller Voucher {self.cus_seller_voucher.get()} บาท",
                "alert",
                txtsize=txtsize
            )
            print("seller voucher popup ต้องเด้งละ")

        self.on_complete.set()

    def cal_adjusted_font_size(self, base_width, base_font_size):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.base_width = base_width
        self.base_font_size = base_font_size

        scale_factor = screen_width / self.base_width
        adjusted_font_size = int(self.base_font_size * scale_factor)
        return adjusted_font_size

    def cusNameFixer5(self, name, account_name=":"):
        is_found = re.search(r"\[.*\]|\(.*\)|\{.*\}", name)
        name = re.sub(r"\[.*\]|\(.*\)|\{.*\}", '', name).strip() if is_found else name.strip()
        # เช็คว่าถ้ามองชื่อเป็น list มันจะแบ่งได้กี่ส่วน
        name += " "+account_name if len(name.split()) == 1 else ""
        print("name:", name)
        return name

    def tax_name_standardizer(self, name: str) -> str:
        # ลบ zero-width space และ trim
        name_edited = name.replace('\u200b', '').strip()

        # --- patterns สำหรับสำนักงานใหญ่ ---
        head_office_patterns = [
            r'\(สำนักงานใหญ่\)', r'สำนักงานใหญ่',
            r'\(สํานักงานใหญ่\)', r'สํานักงานใหญ่',
            r'\(สนญ\.?\)', r'สนญ\.?',
            r'\(00000\)',  # เพิ่ม case ของเลข 00000
        ]

        # --- patterns สำหรับสาขา ---
        branch_patterns = [
            r'\(สาขา.*?\)',   # (สาขาxxx)
            r'สาขา\d*'        # สาขา + ตัวเลข
        ]

        # --- ลบคำสำนักงานใหญ่ ---
        for pattern in head_office_patterns:
            name_edited = re.sub(pattern, '', name_edited).strip()

        # --- ลบคำสาขา ---
        for pattern in branch_patterns:
            name_edited = re.sub(pattern, '', name_edited).strip()

        # --- ปรับรูปแบบประเภทบริษัท ---
        if name_edited.startswith(("หจก", "ห้างหุ้นส่วนจำกัด", "ห.")):
            name_edited = re.sub(r'^(หจก\.?|ห้างหุ้นส่วนจำกัด|ห\.)', '', name_edited).strip()
            if not name_edited.startswith("ห้างหุ้นส่วนจำกัด"):
                name_edited = f"ห้างหุ้นส่วนจำกัด {name_edited}"
        elif name_edited.startswith(("บจก", "บริษัท", "บ.")) or name_edited.endswith("จำกัด"):
            name_edited = re.sub(r'^(บจก\.?|บริษัท|บ\.?|จก\.)', '', name_edited).strip()
            # ถ้าไม่มี "บริษัท" หรือ "จำกัด" อยู่แล้ว ให้เพิ่ม
            if not name_edited.startswith("บริษัท"):
                name_edited = f"บริษัท {name_edited}"
            if not name_edited.endswith("จำกัด"):
                name_edited = f"{name_edited} จำกัด"

        # --- ลบช่องว่างเกิน ---
        name_edited = re.sub(r"\s{2,}", ' ', name_edited)

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

    def check_threads(self, shorter_thread_cycle, longer_thread_cycle, callback=None):
        # print(self.is_bot_running.get())
        # * เป็นการเช็ค thread ไปเรื่อยๆจนกว่า thread ทั้งคู่จะดับไป หาก Thread ใด Thread หนึ่ง ทำงานอยู่ ให้เช็คตัวเองอีกรอบ ภายในเวลา 100 millisec
        if (shorter_thread_cycle.is_alive() or longer_thread_cycle.is_alive()):
            # * after(เวลาmillisec, callbackfunction)
            self.root.after(750, lambda: self.check_threads(shorter_thread_cycle, longer_thread_cycle, callback))

            # * เอาไว้แสดงสถานะของ bot gui ว่าทำงานอยู่หรือไม่
            if self.is_bot_browser_busy.get() == True:
                self.display_bot_status_label.configure(
                    text=f"Bot Status: ᕦʕ •ᴥ•ʔᕤ กำลังทำงาน", fg_color="#cf1313", text_color="#ffffff")
            elif self.is_bot_browser_busy.get() == False:
                self.display_bot_status_label.configure(
                    text=f"Bot Status: Your Turn", fg_color="#21ff29", text_color="#000")
        else:
            # * เมื่อ Thread ทั้งสองไม่ alive จะทำการรวม thread ย่อย เข้ากับ thread หลัก แล้วเรียกใช้ callback ถ้าหากมี callback มาด้วยน่ะนะ callbackนี้จะรับ operation_startเข้ามาให้ทำงานอีกรอบ
            shorter_thread_cycle.join()
            longer_thread_cycle.join()
            print("shorter_thread_cycle is alive?: ", shorter_thread_cycle.is_alive())
            print("longer_thread_cycle is alive?: ", longer_thread_cycle.is_alive())
            self.display_bot_status_label.configure(
                text=f"Bot Status: ˶ᵔ ᵕ ᵔ˶ จบการทำงาน", fg_color="#d9f2ff", text_color="#000")
            print("Bot Status: ˶ᵔ ᵕ ᵔ˶ จบการทำงาน (ตัวล่าง)")

            if callback:
                callback()

    def search_order(self, accel_order=None, callback=None):
        self.is_bot_running.set(False)
        self.is_bot_running.set(True)
        self.autofinal = False

        # * ลบ result products list เก่า
        for widget in self.mp_products_list_frame.winfo_children()[6:]:
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

        self.operation_thread = threading.Event()
        self.order_Search_thread = threading.Event()
        self.operation_thread.set()
        self.order_Search_thread.set()
        self.operation_thread.clear()

        # * สร้าง Thread
        self.bot.get_tabs()
        self.shorter_thread_cycle = threading.Thread(
            target=lambda: self.bot.operation_task_thread(self.operation_thread))
        self.longer_thread_cycle = threading.Thread(target=lambda: self.order_search(
            self.search_query, self.order_Search_thread))
        print("Thread Name: ", self.longer_thread_cycle.name)

        # * สั่ง Thread ให้เริ่มทำงาน
        self.longer_thread_cycle.start()
        self.shorter_thread_cycle.start()

        # * ตรวจสอบว่า Thread ทั้งสองยังทำงานอยู่หรือไม่
        self.check_threads(self.shorter_thread_cycle, self.longer_thread_cycle, callback)
        self.display_bot_status_label.configure(
            text=f"Bot Status: ᕦʕ •ᴥ•ʔᕤ กำลังทำงาน", fg_color="#cf1313", text_color="#ffffff")

    def stop_operation(self):
        # self.is_accel_mode_activated.set(False) ตัวแปรนี้การการhandleที่ทำให้บัค แต่มันทำงานดี
        self.is_bot_running.set(False)
        self.operation_thread.set()
        logger.info(f"Order: {self.order} stop operation")

    def correct_sku_pattern(self, text: str):
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
        # self.import_file_frame.config(
        #     fg_color=f'{self.bg_by_market_place[self.app.marketplace_target.get()]}')

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
        cookies = {
            'JSESSIONID': 'EA2AD7582A59949D14642F01ADF23832',
            'locale': 'en_US',
        }

        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            # 'Cookie': 'JSESSIONID=EA2AD7582A59949D14642F01ADF23832; locale=en_US',
            'Origin': 'http://192.168.0.11:8080',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }

        data = {
            'locale': 'en_US',
            'redirect': 'http://192.168.0.11:8080/smartcore/',
            'username': [
                f'{self.app.user_id.get()}',
            ],
            'password': [
                f'{self.app.user_pw.get()}',
            ],
            'branch': [
                '',
                '',
            ],
            'storeId': [
                '',
                '',
            ],
        }

        response = session.post(
            'http://192.168.0.11:8080/smartcore/loginssoauthen.htm',
            cookies=cookies,
            headers=headers,
            data=data,
            verify=False,
        )

        result = response.json()
        print("ได้ response ไรมา: ", response)
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
                        self.app.accel_mode_checkbox.grid(row=0, column=8, padx=5)
                else:
                    print("Normal mode", self.app.user_id.get() in self.app.dev_account)
                    self.app.accel_mode_checkbox.grid_remove()
                    print(self.app.user_id.get())
                    # print(self.app.dev_account)

                return self.display_btn_txt

    def show_and_hide(self):
        # สำหรับ CTkEntry ใช้ .configure(show="") หรือ .configure(show="*")
        if self.chk_bx_show_pw.get():  # ถ้า checkbox ถูกติ๊ก
            self.pass_input.configure(show="")  # แสดงรหัสผ่าน
        else:
            self.pass_input.configure(show="*")  # ซ่อนรหัสผ่าน


class Bot_POS:
    def __init__(self, parent, app):
        # super().__init__(parent)
        self.parent = parent
        self.app = app
        self.wsh = comclt.Dispatch("WScript.Shell")
        self.driver = self.setup_chrome()
        self.driver.execute_cdp_cmd("Network.enable", {})
        self.channel_options = {
            'shp_itcitymobile_master': 'SHP ITCITY Mobile',
            'itcity': 'SHOPEE',
            'shp_wisegadget_master': 'SHOPEE Wise Gadget',
        }

        self.wait50 = WebDriverWait(self.driver, 50)
        self.wait5 = WebDriverWait(self.driver, 5)
        # ? BaseUrlFinder() มันทำงานโดยหาค่าจาก env แต่ตอนออก exe ยังใช้ไม่ได้ ตอนนี้เลยตั้งค่า origin ตายตัวไปก่อน
        # self.origin = BaseUrlFinder().check_available_ip()
        # self.origin = "http://115.31.167.19:9099"
        self.origin = "http://115.31.167.28:8080"
        self.smco_handler = SMCOFormHandler(self, logger)  # * ใส่ logger ไปด้วยเพราะมันมี setting
        self.AutoAddProduct = AutoAddProduct(self.driver, self.wait50, self.app, self)

        # Memory management tracking
        self.operation_count = 0
        self.memory_check_interval = 10  # ตรวจสอบทุก 10 operations (ปรับได้ตามต้องการ)
        self.max_memory_mb = 70  # ถ้า tab ใช้เกิน 800MB ให้ reset (ปรับได้ 500-1500MB)
        self.is_memory_checking = False

        # คำอธิบาย:
        # - memory_check_interval: ยิ่งน้อยยิ่งตรวจบ่อย แต่จะช้าลง (แนะนำ 5-20)
        # - max_memory_mb: ขึ้นกับสเปคคอม และความต้องการ (แนะนำ 500-1000MB)

    def setup_chrome(self):
        self.opt = Options()
        # * ใช้เพื่อเก็บที่อยู่ของไฟล์ที่ถูก execute ด้วย Python ผ่าน command line arguments ในตัวแปร exepath ซึ่ง sys.argv[0] คือชื่อของไฟล์ Python script ที่ถูกเรียกใช้งาน
        exepath = sys.argv[0]

        # Dir_path = os.path.dirname(os.path.abspath(exepath))
        self.custom_path = r'D:\\bin\\'

        os.environ["WDM_LOCAL"] = self.custom_path
        # print("มีไรบ้างใน obj Options:", dir(self.opt))
        self.opt.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        self.opt.add_experimental_option("debuggerAddress", "localhost:8989")
        self.opt.add_argument("--disable-popup-blocking")
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
            driver = webdriver.Chrome(
                service=Service(r'C:\bin\chromedriver.exe'),
                options=self.opt
            )
            print("driver created")
            return driver

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

            driver = webdriver.Chrome(
                service=Service(r'C:\bin\chromedriver.exe'),
                options=self.opt
            )
            return driver

    def get_current_tab_memory_usage(self):
        """ตรวจสอบการใช้หน่วยความจำ !!ของ tab ปัจจุบัน!! โดยจะคืนค่า เกี่ยวกับ total heap size, used heap size และ threshold ที่ตั้งไว้"""
        try:
            # * ใช้ Chrome DevTools Protocol เพื่อดู memory usage
            memory_info = self.driver.execute_script(
                "return {'usedJSHeapSize': performance.memory.usedJSHeapSize, "
                "'totalJSHeapSize': performance.memory.totalJSHeapSize}"
            )
            used_mb = memory_info['usedJSHeapSize'] / 1024 / 1024
            total_mb = memory_info['totalJSHeapSize'] / 1024 / 1024

            print(f"Memory: {used_mb:.1f}MB used / {total_mb:.1f}MB allocated (Threshold: {self.max_memory_mb}MB)")
            print(f"  Current URL: {self.driver.current_url[:60]}...")

            if used_mb > self.max_memory_mb:
                print(f"  ⚠️  MEMORY EXCEEDED! {used_mb:.1f}MB > {self.max_memory_mb}MB")

            return used_mb
        except Exception as e:
            print(f"Error checking memory usage: {e}")
            return 0

    def close_and_reopen_tab_if_memory_high(self, tab_name=None):
        """ปิดแท็บเก่าแล้วเปิดใหม่ ถ้า memory เกิน limit"""

        try:
            # * ตรวจสอบ URL ปัจจุบัน
            try:
                current_url = self.driver.current_url
            except Exception:
                logger.warning("ไม่สามารถอ่าน current_url ได้ อาจไม่มีแท็บเปิดอยู่")
                return False

            current_handle = self.driver.current_window_handle
            memory_usage = self.get_current_tab_memory_usage()

            logger.info(
                f"{self.app.cus_order.get()}: Checking memory for '{tab_name or current_url}' ({memory_usage:.1f}MB)"
            )

            # 🔥 ถ้าใช้ memory เกิน limit → รีโหลดแท็บ
            if memory_usage > self.max_memory_mb:
                print(f"Memory usage ({memory_usage:.1f}MB) exceeds limit ({self.max_memory_mb}MB)")
                print(f"Reopening tab: {tab_name or current_url}")

                # 🧾 เก็บตำแหน่ง scroll ปัจจุบัน
                try:
                    scroll_position = self.driver.execute_script("return document.scrollingElement.scrollTop;")
                except Exception:
                    scroll_position = 0

                # 📑 เปิดแท็บใหม่อย่างปลอดภัย
                old_handles = set(self.driver.window_handles)
                self.driver.execute_script(f"window.open('{current_url}', '_blank');")

                # ✅ รอจนกว่าจะมีแท็บใหม่โผล่
                WebDriverWait(self.driver, 5).until(
                    lambda d: len(set(d.window_handles) - old_handles) > 0
                )

                new_handle = list(set(self.driver.window_handles) - old_handles)[0]
                logger.info(f"{self.app.cus_order.get()}: Opened new tab for '{tab_name or current_url}'")

                # 🪟 สลับไปแท็บใหม่ก่อน แล้วค่อยปิดแท็บเก่า
                self.driver.switch_to.window(new_handle)
                try:
                    self.driver.switch_to.window(current_handle)
                    self.driver.close()
                    logger.info(f"{self.app.cus_order.get()}: Closed old tab for '{tab_name or current_url}'")
                except Exception as e:
                    logger.warning(f"Error closing old tab: {e}")

                # 🔁 สลับกลับไปแท็บใหม่อีกครั้ง
                self.driver.switch_to.window(new_handle)

                # ⏳ รอหน้าโหลดเสร็จจริง (แทนการ sleep)
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                # 📜 กลับไป scroll ตำแหน่งเดิม
                try:
                    self.driver.execute_script(f"document.scrollingElement.scrollTop = {scroll_position};")
                except Exception:
                    pass

                # 🔍 อัปเดตข้อมูลแท็บทั้งหมด
                self.get_tabs()

                # 🔄 อัปเดต handle ใน merged_dict
                updated = False
                for key, value in list(self.merged_dict.items()):
                    if value == current_handle:
                        self.merged_dict[key] = new_handle
                        updated = True
                        print(f"Updated {key} handle → new tab")
                if not updated:
                    print("⚠️ No merged_dict entry matched old handle")

                print("✅ Tab closed and reopened successfully (memory cleaned)")
                return True

            # ถ้า memory ยังไม่เกิน limit → ไม่ต้องทำอะไร
            return False

        except Exception as e:
            print(f"❌ Error closing/reopening tab: {e}")
            logger.error(f"close_and_reopen_tab_if_memory_high failed: {e}")
            return False

    # เก็บฟังก์ชันเก่าไว้เป็น backup

    def refresh_tab_if_memory_high(self, tab_name=None):
        """Refresh tab ถ้าใช้ memory เกินกำหนด (backup method)"""
        return self.close_and_reopen_tab_if_memory_high(tab_name)

    def force_garbage_collection(self):
        """บังคับให้ browser ทำ garbage collection"""
        try:
            # ทำ garbage collection ใน JavaScript
            self.driver.execute_script(
                "if (window.gc) { window.gc(); } "
                "else if (window.CollectGarbage) { window.CollectGarbage(); }"
            )

            # ล้าง cache และ unused objects
            self.driver.execute_script(
                "if (typeof window.caches !== 'undefined') {"
                "  caches.keys().then(names => {"
                "    names.forEach(name => caches.delete(name));"
                "  });"
                "}"
            )
            print("Forced garbage collection completed")
        except Exception as e:
            print(f"Error during garbage collection: {e}")

    def pre_operation_memory_cleanup(self, operation_name="operation"):
        """ตรวจสอบและจัดการ memory ก่อนเริ่ม operation สำคัญ (เฉพาะ SMCO tabs)"""
        print(f"\n=== Pre-operation Memory Cleanup: {operation_name} ===")
        self.is_memory_checking = True
        try:
            current_handle = self.driver.current_window_handle
            all_handles = self.driver.window_handles

            print(f"Checking memory for {len(all_handles)} tabs before {operation_name}")

            # ตรวจสอบ memory ของ SMCO tabs เท่านั้น
            tabs_cleaned = 0
            smco_tabs_found = 0

            for i, handle in enumerate(all_handles):
                try:
                    self.driver.switch_to.window(handle)
                    tab_title = self.driver.title
                    print(f"handle No. {i+1}: {tab_title}")
                    # จัดการเฉพาะ tabs ที่มี "SMCO :: " ในชื่อ
                    if "SMCO :: " in tab_title:
                        smco_tabs_found += 1
                        memory_usage = self.get_current_tab_memory_usage()

                        print(f"SMCO Tab {smco_tabs_found}: {tab_title[:50]} - {memory_usage:.1f}MB")

                        # ถ้า memory เกินกำหนด ให้ปิดแล้วเปิดใหม่
                        if memory_usage > self.max_memory_mb:
                            print(f"  → Cleaning SMCO tab (memory too high)")
                            logger.info(
                                f"{self.app.cus_order.get()}: Pre-operation cleanup: Closing and reopening tab '{tab_title}' due to high memory ({memory_usage:.1f}MB)")
                            if self.close_and_reopen_tab_if_memory_high(tab_title):
                                tabs_cleaned += 1
                        else:
                            print(f"  → Memory OK")
                    else:
                        # แสดงข้อมูล tab อื่น แต่ไม่จัดการ
                        print(f"Other Tab {i+1}: {tab_title[:30]} - Skipped (not SMCO)")

                except Exception as e:
                    print(f"  → Error checking tab {i+1}: {e}")

            # กลับไป tab เดิม
            try:
                self.driver.switch_to.window(current_handle)
            except:
                # ถ้า tab เดิมถูกปิดไป ให้หา SMCO tab แรกที่เจอ
                for handle in self.driver.window_handles:
                    try:
                        self.driver.switch_to.window(handle)
                        if "SMCO :: " in self.driver.title:
                            print("Switched to first available SMCO tab")
                            break
                    except:
                        continue

            # ทำ garbage collection รวม
            self.force_garbage_collection()

            print(f"Memory cleanup completed: {tabs_cleaned}/{smco_tabs_found} SMCO tabs cleaned")
            #! กำลังทดลองยังไม่พร้อมใช้ testing ลองดูอันนี้ก่อนนะ เพราะแม่งเปิดใหม่ไม่ติดไม่รู้เปนไรเปิดข้างนอกแม่งเลยดูดิจะเจอเบาะแสไรไหม
            # print("Testing")
            # for i in enumerate(tabs_cleaned):
            #     target_url = f'{self.origin}/smartcore/smartpos/pointofsales/posmainv3.htm'
            #     # เปิด tab ใหม่
            #     self.driver.execute_script(f"window.open('{target_url}');")
            #     all_handles = self.driver.window_handles
            #     new_handle = all_handles[-1]  # tab ใหม่ล่าสุด

            #     # ย้ายไป tab ใหม่
            #     self.driver.switch_to.window(new_handle)

            #     # โหลด URL เดิม
            #     self.driver.get(target_url)

            # print("="*50)
            self.is_memory_checking = False

        except Exception as e:
            print(f"Error in pre-operation memory cleanup: {e}")
            self.is_memory_checking = False

    def manage_browser_memory(self, operation_name="operation"):
        """หลัก method สำหรับจัดการ memory ของ browser (ใช้แค่สำหรับการนับ operation)"""
        self.operation_count += 1
        print(f"Operation count: {self.operation_count} ({operation_name})")

    def reset_all_tabs_memory(self):
        """Reset memory ของทุก tabs ที่เปิดอยู่"""
        try:
            current_handle = self.driver.current_window_handle
            all_handles = self.driver.window_handles

            print(f"Resetting memory for {len(all_handles)} tabs")

            for handle in all_handles:
                try:
                    self.driver.switch_to.window(handle)
                    tab_title = self.driver.title[:50]  # แค่ 50 ตัวอักษรแรก

                    # ตรวจสอบ memory และ refresh ถ้าจำเป็น
                    self.refresh_tab_if_memory_high(tab_title)

                except Exception as e:
                    print(f"Error resetting tab {handle}: {e}")

            # กลับไป tab เดิม
            self.driver.switch_to.window(current_handle)

            # ทำ garbage collection รวม
            self.force_garbage_collection()

            print("Memory reset completed for all tabs")

        except Exception as e:
            print(f"Error in reset_all_tabs_memory: {e}")

    def demonic_cp_bot(self, item_no: int, cp_no: int):
        self.item_no = int(item_no)-1
        self.cp_no = int(cp_no)
        print("ตอนแรกเปนงี้", self.app.items[self.item_no]['เลขอ้างอิง SKU (SKU Reference No.)'])
        self.demonic_ordered_items_list = self.app.correct_sku_pattern(
            self.app.items[self.item_no]['เลขอ้างอิง SKU (SKU Reference No.)']
        )
        print(f"self.demonic_ordered_items_list: {self.demonic_ordered_items_list}")
        print(f"self.cp_no: {self.cp_no}")

        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
        # *>  element location
        # * >> ปุ่มคูปองด้านนอก ที่ตำแหน่ง [-4] จะเป็นตัวแยก element หรือ ตัวบอกตำแหน่งของ element ว่าเป็นลำดับที่เท่าไหร่ อย่างตัวอย่างนี้เป็น อันที่1
        # cp_btn_xpath = '/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[2]/div[1]/div/div[2]/div[3]/div[1]/a' # ! >> old fashion way
        # green_agree_btn_xpath = '/html/body/div[2]/div[3]/div[11]/div/div[1]/span/div[2]/button[1]'   # ! >> old fashion way ปุ่มยืนยันสีเขียว
        green_agree_btn_xpath = 'button[ng-click="okCoupon()"]'
        item_list_elements = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
        item_list_cp_btn_elements = self.driver.find_elements(
            By.CSS_SELECTOR, 'div.col-sm-4.nopadding button.btn-coupon.btn.btn-sm')

        try:
            # * ก่อน SMCOver 6.3.3
            cp_list = self.driver.find_elements(By.XPATH, '/html/body/div[1]/div[2]/div[9]/div/div[2]/div[3]')
        except:
            # * ตั้งแต่ SMCOver 6.3.3
            cp_list = self.driver.find_elements(By.XPATH, '/html/body/div[1]/div[2]/div[9]/div/div[2]/div[2]')

        for idx, item in enumerate(self.demonic_ordered_items_list):
            item_position = idx+1
            print("จำนวน skus in SMCO POS ", len(item_list_elements))
            for idx2, div in enumerate(item_list_elements):
                li_position = idx2+1
                try:
                    is_found = item in div.text  # * มันจะ error ตรงนี้หาก divตัวไหนแปรสภาพหลังเลือก cp ไปแล้ว ทำให้มันจะข้าม loop ตั้งแต่ตรงนี้ แต่ข้ามแบบ error ซึ่ง exception ข้างล่างดักไว้แล้ว อยากเห็นลองเปิดดูได้
                    # print(f"item: {item_position}, li no. {li_position}")
                    # print("is_found: ", is_found)
                    if is_found == True:
                        # cp_btn_xpath = f'''/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[2]/div[{li_position}]/div/div[2]/div[3]/div[1]/button'''
                        cp_btn_xpath = item_list_cp_btn_elements[idx2]
                        cp_btn_xpath.click()

                        # * เลือก cp เป้าหมาย
                        selected_btn = f'''/html/body/div[2]/div[3]/div[11]/div/div[2]/div[2]/div[{
                            self.cp_no}]/div[1]/button'''
                        self.driver.find_element(By.XPATH, selected_btn).click()

                        # * กดยืนยัน
                        self.driver.find_element(By.CSS_SELECTOR, green_agree_btn_xpath).click()
                        time.sleep(0.25)  # * รอให้มัน process หน่อย
                        break
                        # print(div.text)
                    else:
                        # print("ไม่เจอ", item, "นะ")
                        pass
                except Exception as err:
                    # Todo มันไม่ใช่เรื่องใหญ่อะไร exception นี้มักจะเกิดจาก elementที่เคยเลือกไปแล้วมันเปลี่ยนโครงสร้างแต่ elementใน item_list_elements ที่แกะมา ลูบทีละตัวมันเปนค่าเดิม ทำให้ loop รอบถัดไป error ที่ elementเดิมที่เคยเลือก cp ไปก่อนหน้า เช่น รับเข้ามา (<em>(1), <em>(2), <em>(3)) พอเลือก cp มันจะเป็นแบบนี้แทน (<em>(1CP), <em>(2), <em>(3)) แต่ตอน loop เราใช้ค่า <em>(1) ไปหา มันจะ error เพราะในหน้าเว็บมันกลายเปน <em>(1CP) ไปแล้ว
                    # print("Demonic CP Bot inner Exception Error:", err)
                    pass

    def get_tabs(self):
        if self.parent.winfo_exists():
            print("รายงานจำนวนtabs")
            self.title_list = []
            # self.title_list_Idx = [] #!เหมือนจะไม่ได้ใช้
            self.value_list = []
            # self.title_dict = {} #!เหมือนจะไม่ได้ใช้

            # * check ว่า self.driver เดิมยังทำงานได้ไหม
            try:
                # * เช็คก่อนว่า driver ใช้ได้ไหม หรือการเชื่อมต่อ session หลุดไหม
                self.driver.window_handles
                print("driver is still running")
            except:
                # * driver หลุดก็ออก seesion เก่า
                try:
                    print("Quit old driver, not sure if this process is auto or not")
                    self.driver.quit()
                except:
                    print("No need to quit old driver, no driver found")
                    pass

                self.driver = webdriver.Chrome(
                    service=Service(r'C:\bin\chromedriver.exe'),
                    options=self.opt
                )

            for idx, handle in enumerate(self.driver.window_handles):
                self.driver.switch_to.window(handle)
                print("self.driver.title: ", self.driver.title)
                self.title_list.append(self.driver.title)
                self.value_list.append(self.driver.current_window_handle)

            self.unique_titles = []
            self.counter = {}
            for item in self.title_list:
                if item in self.counter:
                    self.counter[item] += 1
                    print("counter[item] คือไร: ", self.counter[item])
                    self.unique_titles.append(f"{item}{self.counter[item]-1}")
                else:
                    self.counter[item] = 1
                    self.unique_titles.append(item)

            # * เอาList มารวมกัน
            self.merged_dict = dict(zip(self.unique_titles, self.value_list))
            print("มี tabs ไรบ้าง", self.merged_dict)

    def operation_task_thread(self, event=None):
        self.operation_thread = event
        if not self.operation_thread.is_set():
            try:
                # * เริ่มการทำงาน Operation Start
                if self.app.order != "" and not self.operation_thread.is_set():

                    logger.info(f"Order: {self.app.order} Start!!")
                    try:
                        self.operation_start()
                    except Exception as err:
                        logger.info(f"Order: {self.app.order} outer_Exception_Error!! {err}")
                else:
                    self.app.update_log("กรุณากรอก Order ก่อน")
                    self.app.search_complete.set()

            except Exception as err:
                traceback_str = traceback.format_exc()
                print(f"operation_task_thread, An error occirred: {err}")
                print(traceback_str)
                logger.info(f"Order: {self.app.order} operation_task_thread_outer_Exception_Error!! {err}")
        else:
            print("Operation thread is already set, skipping operation task")
            self.app.update_log("Operation thread is already set, skipping operation task")

    def set_cus_name_search_type(self):
        self.wait50.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 r'''//div[contains(@ng-show, "abbCustomerFlag")]//a[contains(@ng-click, "st='E'")]''')))
        if self.app.tax_bool.get() == True:
            # ขอใบกำกับ **Trick** สามารถใส่single qoute สามตัวได้ หากด้านในมีการใช้ qoute และ bouble qoute ไปแล้ว แต่ทั้งหมดต้องเป็น string อีกที >>  ('''function("vbvb, x='แมว'")''')
            if self.app.marketplace_target.get() == "SHOPEE":
                print("ขอใบกำกับSHOPEE ใช้ T:")
                self.driver.find_element(
                    By.XPATH, r'''//div[contains(@ng-show, "abbCustomerFlag")]//a[contains(@ng-click, "st='T'")]''').click()
            elif self.app.marketplace_target.get() == "LAZADA":
                print("ขอใบกำกับLazada ใช้ T:")
                self.driver.find_element(
                    By.XPATH, r'''//div[contains(@ng-show, "abbCustomerFlag")]//a[contains(@ng-click, "st='T'")]''').click()
        elif self.app.tax_bool.get() == False:
            # ไม่ขอใบกำกับ
            print("ไม่ขอใบกำกับใช้ N:")
            self.driver.find_element(
                By.XPATH, r'''//div[contains(@ng-show, "abbCustomerFlag")]//a[contains(@ng-click,"st='N'")]''').click()

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

    def get_customer_name_ready(self, cus_search_input):
        # * start Enter customer name here +++++++++++==================================================
        while not self.operation_thread.is_set():
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
        self.find_selectable_cus_name_li()  # *เนื่องจาก li แสดง สถานะและชื่อลูกค้า ซึ่งต้อง handle ให้แน่ใจว่าเป็นชื่อลูกค้าจริงๆก่อน

        # * is_name_list_selectable จะมีการตรวจสอบว่าเลือกได้เหรือไม่ ถ้าเลือกได้ก็เลือกเลย----------------------------
        while not self.operation_thread.is_set():
            try:
                # * หา li ไปตรวจสอบว่ามี len เท่าไหร่
                customer_name_input_ul = self.driver.find_element(By.XPATH, self.app.cus_name_dropdown_ul)
                customer_name_dropdown_lis = customer_name_input_ul.find_elements(By.CSS_SELECTOR, '.select2-results__option')
                # print("หาจำนวน li ชื่อลูกค้าเท่ากับ:", customer_name_dropdown_lis)
                # * เลือกชื่อลูกค้า มีสองกรณี คือ เลือกจาก li > 1 หรือ น้อยกว่า 2
                if len(customer_name_dropdown_lis) > 1:
                    print("มากกว่า 1")
                    cus_found_names_list = [element.text for element in customer_name_dropdown_lis]
                    self.select_cus_name_from_lis(
                        self.app.cus_name.get(),
                        cus_found_names_list, self.select_cus_name_from_lis)
                    print("click แล้ว")
                    break
                else:
                    self.driver.find_element(By.XPATH, self.app.cusNameLi1).click()
                    print("Click the cusname li result")
                    break

            except:
                self.driver.find_element(By.XPATH, self.app.cus_arrow_btn).click()
                continue

        # #* เลือกชื่อลูกค้า มีสองกรณี คือ เลือกจาก li > 1 หรือ น้อยกว่า 2 ย้ายไปไว้ใน while เพราะ customer_name_dropdown_lis มันหายได้หากไว้นอก while มันจะพัง
        # if len(customer_name_dropdown_lis) > 1:
        #     print("มากกว่า 1")
        #     cus_found_names_list = [element.text for element in customer_name_dropdown_lis]
        #     self.select_cus_name_from_lis(self.app.cus_name.get(), cus_found_names_list, self.select_cus_name_from_lis)
        #     print("click แล้ว")
        # else:
        #     self.driver.find_element(By.XPATH, self.app.cusNameLi1).click()
        #     print("Click the cusname li result")

        # * กรณีมีสินค้ายิงไปแล้ว แล้วมีการเปลี่ยนชื่อลูกค้า มันจะมี alert // path นี้คือ element นอกของ alert /html/body/div[16]/div[2]
        if self.driver.find_element(By.XPATH, "/html/body/div[16]/div[2]").is_displayed():
            try:
                self.driver.find_element(By.XPATH, "//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]").click()
                self.driver.find_element(By.XPATH, self.app.cus_arrow_btn).click()
                self.wait50.until(EC.visibility_of_element_located((By.XPATH, self.app.cusNameInput)))
            except:
                print("Skip, Alert Element is appear but can not perform actions.")
        else:
            print("Skip, Alert Element is Not appear")
            print("No customer name input found")
            pass

        print("search หายไปแล้ว")
        self.wait50.until(EC.invisibility_of_element_located((By.XPATH, self.app.cusNameInput)))

    def enter_cus_name(self, cus_search):
        # * ย้ายไปหน้าหลัก
        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])

        # * clear ชื่อ เก่า
        self.driver.find_element(By.XPATH, self.cus_name_span_elmt_loc).click()

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
        if self.app.tax_bool.get():
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
            self.wait5.until(EC.visibility_of_element_located((By.XPATH, """//div[@class = 'swal2-content']""")))
            cus_code_element = self.driver.find_element(By.XPATH, """//div[@class = 'swal2-content']""")
            # * เคส duplicate cus name จะเกิดโดยชื่อซ้ำ มักจะเกิดกับกรณีที่ ชื่อลูกค้าที่ชื่อเก่าไม่มีเลขผู้เสียภาษี แต่ถัดมาลูกค้าขอด้วยชื่อเดิมเพิ่มเติมคือมีเลขผู้เสียถาษีbotจะเสิชด้วยเลขผู้เสียภาษีแล้วจะทำให้หาไม่เจอทำให้เกิดการadd customer ใหม่ ทำให้ชื่อแบบที่ไม่มีเลขผู้เสียภาษี ซ้ำกับชื่อที่แอดใหม่(มีเลขผู้เสียภาษี)-
            # *-duplicate_cus_name_resolver จึงแก้ไขโดยการเพิ่มเลขผู้เสียภาษีให้กับชื่อลูกค้าอันเดิมทำให้ไม่มีการซ้ำเกิดขึ้น
            # * กรณี add แล้ว มี popup-duplicate customer
            print("Check Duplicated customer!!")
            self.duplicated_cus_name_resolver(cus_code_element)
            cb()

        except Exception as err:
            print("No duplicate!", err)

    def find_selectable_cus_name_li(self):
        """
        li ที่จะแสดงใน ul นั้นมันไม่ได้มีแค่ชื่อลูกค้า แต่มันมี สถานะเช่น "กำลังหา" หรือ "หาไม่เจอ" ซึ่งทำให้กดเลือกชื่อลูกค้าจาก li ไม่ได้ทันที จึงต้อง handle ส่วนนี้โดยทำให้ค่าที่โผล่ใน li นั้นเป็น ชื่อลูกค้าแล้วจริงๆแล้วไปยังขั้นตอนต่อไป (functionนี้ยังไม่มีการเลือกliนะ)
        มันเปนการกรอกชื่อและดูผลลัพของ li ต่างๆว่า แสดงผลอย่างไร มันจะมีกรณีแสดง li เดียวแล่้วถูก,  แสดง li เดียวแต่เปนการบอกว่าไม่มีชื่อ, แสดง li จำนวนมาก แต่มีตัวถูก, แสดง li จำนวนมาก แต่ไม่มีตัวถูก
        """
        self.customer_added_times = 0
        self.customer_name_search_count = 0
        while not self.operation_thread.is_set():
            if self.driver.find_element(By.XPATH, self.app.cus_name_dropdown_ul):
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
                    print(f"Re enter name after add")
                    continue
                # * หลังจาก Add ไปแล้วรอบนึง แล้วมาเสิชใหม่แล้วยังไม่เจอ ถึงจะเข้าเงื่อนไขนี้ เป็นการ search ให้อีกรอบนึง
                elif self.searching_condition.text == "No results found" and self.customer_name_search_count < 1:
                    time.sleep(1)
                    self.enter_cus_name(self.cus_search_input)
                    self.customer_name_search_count += 1
                    print(f"Re enter name after add extra times {self.customer_name_search_count}")
                    continue
                # * Add แล้ว รีเสิชให้สองรอบแล้ว ก็ยังไม่เจอ ลองแอดด้วยตัวเองดู
                elif self.searching_condition.text == "No results found" and self.customer_added_times == 1:
                    print("I've already add it, but the element still shows 'No results found', you have to add by yourself")
                    self.enter_cus_name(self.cus_search_input)
                    time.sleep(1)
                    continue
                else:
                    print("Found customer name:", self.searching_condition.text)
                    self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
                    break
            print("addcustomer and select While end!")
            break

    # !66 WIP เปลี่ยนวิธีเลือกชื่อลูกค้า เดิมทีคือเลือก // ชิพหายมันเลือกค่าจาก i
    def select_cus_name_from_lis(self, cus_desire_name, cus_name_list, cb=""):
        # * ล้างคำที่ไม่เกี่ยวกับชื่อลูกค้า (คำเสริมยศต่างๆที่ไม่สำคัญกับการแยกแยะว่าใครเป็นใคร)
        print("incoming cus_desire_name: ", cus_desire_name)
        pattern = r'^(บริษัท|บจก\.?|หจก\.?|หสม\.?|ห้างหุ้นส่วนจำกัด|ห้างหุ้นส่วนสามัญ)\s*'
        pattern2 = r'จำกัด(\s*มหาชน)?$'

        cus_desire_name = re.sub(pattern, '', cus_desire_name)
        cus_desire_name = re.sub(pattern2, '', cus_desire_name)
        cus_desire_name = cus_desire_name.strip()

        cus_desire_name = cus_desire_name.replace(" ", "")
        cus_desire_name = cus_desire_name.replace("\n", "")

        print(
            f"[select_cus_name_from_lis]cus_desire_name: {cus_desire_name} and self.cus_name_span_elmt.text: {self.cus_name_span_elmt.text}")
        if cus_desire_name in self.cus_name_span_elmt.text:
            while not self.operation_thread.is_set():
                try:
                    self.driver.find_element(By.XPATH, self.app.cus_name_dropdown_ul)
                    self.driver.find_element(By.CSS_SELECTOR, "#select2-memberSearch-container").click()
                    break
                except:
                    time.sleep(0.5)
                    continue

            print(f"cus_desire_name in self.cus_name_span_elmt.text")
            return

        # * ทำการคัดเอาเฉพาะชื่อลูกค้าไม่เอารหัส ลง array
        names_no_code = cus_name_list.copy()
        for i in range(len(cus_name_list)):
            prog = re.search(r'[^-]-(.*)', names_no_code[i])
            names_no_code[i] = prog.group(1).replace(" ", "")

        # * เอา array มาหาดูว่าจะต้องเลือกชื่อไหน เอา idx ที่ได้ไช้ระบุ locator ที่ต้อง click
        for i, name in enumerate(names_no_code):
            print("if ", cus_desire_name, " In ", name)
            if cus_desire_name in name:
                print("ชื่อที่ต้องการ อยู่ใน li")
                while not self.operation_thread.is_set():
                    try:
                        print("เลือกชื่อลูกค้า", cus_name_list[i])
                        # * ต้อง +1 เพราะว่า xpath รับค่าเป็นจำนวนเต็ม+ ไม่ใช่ index
                        self.driver.find_element(By.XPATH, f"/html/body/span/span/span[2]/ul/li[{i+1}]").click()
                        break

                    except:
                        print("No customer found")
                        continue
                return
            # * ถ้ามันเจอก็จะ จบ function แต่ถ้าไม่เจอจะไปใช้ cb ต่อ

        self.add_new_customer(lambda: self.get_customer_name_ready(self.cus_search_input))

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
                self.driver.find_element(By.CSS_SELECTOR, '#contentZen > div.ng-scope > div:nth-child(2) > div.panel-body > div.col-sm-3 > div.col-sm-12.nopadding > div.panel-body > div > div > div:nth-child(2) span.select2-selection__arrow').click()
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
                    By.XPATH, '//*[@id="select2-divSaletype2-results"]/li[(starts-with(., "AR Online") or starts-with(., "Online Sale")) and not(contains(., "Deposite -"))]').click()
                print("เจอ saletype li")
                return
            except Exception as err:
                print("ยังไม่เจอ li ให้เลือก")
                print("select_sale_type Error: ", err)
                time.sleep(0.5)
                continue
        raise Exception(f'Thread has been terminated during select_sale_type')

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

    def add_shipping_cost(self):
        if int(self.app.cus_ship_cost.get()) != int(0):
            try:
                self.skuInput_element = self.wait50.until(EC.visibility_of_element_located(
                    (By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')))
                # skuInput = driver.find_element(By().XPATH,'/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')
                self.skuInput_element.clear()

                self.skuInput_element.send_keys("SV0-000101")
                print("กรอก Code ขนส่งสำเร็จ")

                self.skuAddBtn = self.wait50.until(EC.visibility_of_element_located(
                    (By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')))
                # skuAddBtn = driver.find_element(By().XPATH,'/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')
                self.skuAddBtn.send_keys("\ue007")  # กด Enter
                print("กด Enter ที่ช่อง SKU Input สำเร็จ")

                #! WIP ทดสอบ 1/2 หยุดเพื่อให้จบ if ก่อน แล้ว2/2 จะเป็นชั้นที่จบ scope จริงๆ รู้สึก return ตรนี้ใช้แล้วจะจบเลย ไม่ได้จบแค่ if งั้นเหรอ
                # logger.info(f"Order: {self.app.order} 1/2Finished!!")
                # return
                time.sleep(2)

                # ทำไมต้องใส่วงเล็บ คลุม BY.XPATH เพราะ ถ้าไม่ใส่ ฟังชัน visibility จะมอง xpath เป็น argument ที่สอง ของ method visibility
                self.definePrice_btn_element = self.wait50.until(EC.visibility_of_element_located(
                    (By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div[1]/div/a[1]')))
                # self.definePrice_btn_element = driver.find_element(By().XPATH,'/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div[1]/div/a[1]')
                self.definePrice_btn_element.click()
                time.sleep(1)
                # ค่าขนส่งโดนข้า230208FX99FUGGมหลังจากตรงนี้
                print("Successfully clicked on SKU ELEMENT 1")

                self.changePriceInput = self.driver.find_element(
                    By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[1]/input')
                self.changePriceInput.clear()
                # self.changePriceInput.send_keys(69)
                # self.changePriceInput.send_keys(int(self.app.cus_ship_cost.get()))
                self.driver.execute_script(
                    "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                    self.changePriceInput, self.app.cus_ship_cost.get())
                self.driver.find_element(
                    By().XPATH,
                    '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[2]/input').clear()
                self.driver.find_element(
                    By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[2]/input').send_keys(self.app.user_id.get())

                self.driver.find_element(
                    By().XPATH,
                    '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[3]/input').clear()
                self.driver.find_element(
                    By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[3]/input').send_keys(self.app.user_pw.get())

                self.driver.find_element(
                    By().XPATH,
                    '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[5]/div/textarea').clear()
                self.driver.find_element(
                    By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[5]/div/textarea').send_keys("Online")

                self.driver.find_element(
                    By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[6]/a[1]').click()
                # try:
                #     print("Waiting for element to disappear")
                #     self.wait50(EC.invisibility_of_element_located((By().XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[6]/a[1]')))
                # except:
                #     print("No need to wait")
            except Exception as err:
                print("Shipment cost skipped")
                print(err)
        else:
            print("No shipment cost")

    def printtingPage(self):
        time.sleep(1)
        self.printing_page = self.driver.find_element(By().XPATH, '/html/body')
        self.action01 = ActionChains(self.driver).context_click(self.printing_page)
        self.action01.perform()

    #! deprecated?
    def justPressP(self):
        time.sleep(1)
        self.wsh.SendKeys("P")
        time.sleep(1.55)
        self.wsh.SendKeys("{Enter}")
        print("print แล้วโว้ย")
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
        self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[10]/div/div[1]/div[2]/a').click()

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

    def find_sumatra_from_registry(self):
        reg_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        ]

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
                                            return exe_path
                            except (FileNotFoundError, OSError, PermissionError, KeyError):
                                print("continue")
                                continue
                except FileNotFoundError:
                    continue
        print("SumatraPDF was not installed.")
        return None

    def print_pdf_silence_sumatra(self, pdf_path):
        try:
            sumatra_path = self.find_sumatra_from_registry()
            subprocess.Popen([sumatra_path, '-print-to-default', pdf_path], shell=False)
            print("SMT Printing silently complete.")
        except Exception as e:
            print(f"sumatra Silent print failed: {e}")
            raise ValueError("Sumatra was not found")

    def operation_start(self):
        self.app.is_bot_browser_busy.set(True)
        self.is_forbid = False
        is_etax = False
        self.is_old_tax_form = False

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
                self.wait5.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.subaccount-info span.subaccount-name')))
                self.operation_states['purchased_channel'] = self.driver.find_element(
                    By.CSS_SELECTOR, 'div.subaccount-info span.subaccount-name').text
                print(f"self.operation_states['purchased_channel']: {self.operation_states['purchased_channel']}")
                cur_url = self.driver.current_url

                # * เปลี่ยนไปใช้หน้า "ทั้งหมด" เพราะ ในที่หน้าต่างกัน add_new_customer, elements มันต่างกัน บังคับให้มันใช้อันที่ถูก
                if cur_url != "https://seller.shopee.co.th/portal/sale/order":
                    # self.driver.get("https://seller.shopee.co.th/portal/sale/order")
                    # self.driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[4]/div[1]/div/div/div/div[1]/div/div[1]/div[1]/div').click() //ใช้ได้แต่กันไว้ก่อน 25/11/2024 15:11
                    self.driver.find_element(
                        By.CSS_SELECTOR, 'div.eds-tabs__nav div.eds-tabs__nav-warp div div div.tab-label').click()
                    #! ตรงนี้มันไม่ใช้แล้ว
                    # self.wait50.until(EC.text_to_be_present_in_element(
                    #     (By.XPATH, '/html/body/div[1]/div[1]/div/div[1]/div/div[2]/div[1]/div/div[1]/div[1]/a'), 'การขายของฉัน'))
                else:
                    print("อยู๋ในหน้าทั้งหมดอยู่แล้ว ไม่ต้องเปลี่ยน")

                try:
                    # * กรอก order ลงในช่อง search
                    self.search_elmt = self.wait50.until(EC.visibility_of_element_located(
                        # (By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[2]/div/div/div[1]/div[1]/div[2]/div[1]/span[2]/div/div[1]/div/div/input'))) เก่า ไม่น่าจะกลับมาใช้แล้ว
                        # (By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div/div[2]/div[1]/div[1]/div[1]/div/span[2]/div/div[1]/div/div/input')))
                        # (By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div/div[2]/div[1]/div/div[1]/div[1]/div/div/span[2]/div/div[1]/div/div/input'))) พัง 28/08/2024 12:00 PM
                        # (By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[4]/div/div/div[2]/div[1]/div/div/div[1]/div[1]/div/div/span[2]/div/div[1]/div/div/input') พัง 19/09/2024 17:00
                        # (By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[5]/div/div/div[2]/div/div[1]/div/div/div[1]/div[1]/div/div/span[2]/div/div[1]/div/div/input') พัง 25/11/2024 15:11
                        (By.CSS_SELECTOR, 'div.eds-input__inner.eds-input__inner--normal input')

                    ))

                    self.search_elmt.clear()
                    self.search_elmt.send_keys(self.app.cus_order.get())

                    # * กด Search เพื่อ เก็บ Status
                    self.searchBtn = self.driver.find_element(
                        # By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[2]/div/div/div[1]/div[1]/div[2]/div[2]/button[1]') เก่า ไม่น่าจะกลับมาใช้แล้ว
                        # By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div/div[2]/div[1]/div[1]/div[2]/button[1]' พัง 28/08/2024 12:00
                        # By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div/div[2]/div[1]/div/div/div[2]/button[1]' พัง 18/09/2024 14:00
                        # By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[4]/div/div/div[2]/div[1]/div/div/div[2]/button[1]' พัง 19/09/2024 17:00
                        # By.XPATH, '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[5]/div/div/div[2]/div/div[1]/div/div/div[2]/button[1]' ใช้ได้อยู่ แต่กันไว้ก่อน พัง 25/11/2024 15:11
                        By.CSS_SELECTOR, 'div.order-search-buttons button.search-btn.eds-button.eds-button--primary.eds-button--normal.eds-button--outline'
                    )
                    self.searchBtn.click()
                except:
                    print("cannot search order")
                    raise ValueError(f"method operation_start Error : {traceback.format_exc()}")

                # * ตรวจสอบ Status และ update ของ MARKETPLACE
                time.sleep(1)

                while not self.operation_thread.is_set():
                    # * ใช้ while loop รอดู interface ว่า มันโผล่มายัง
                    try:
                        self.driver.find_element(By.CLASS_NAME, 'status-wrapper').is_displayed()
                        break
                    except:
                        continue
                try:
                    self.driver.find_element(By.CLASS_NAME, 'status-wrapper').is_displayed()
                    print("Found element classed big-text")
                except:
                    print("Not found element classed big-text, try to wait and click element with XPATH")
                    self.wait50.until(
                        EC.element_to_be_clickable(
                            (By.XPATH,
                             '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[3]/div/div/div[2]/div[4]/div/div[2]/a/div[2]/div/div/div')))

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
                        "Caution!!", f"Order นี้มีสถานะ '{self.app.cus_cur_status.get()}' จะทำต่อจริงอ่อ?", "alert")

                elif "ยกเลิก" in self.app.cus_cur_status.get():
                    self.app.display_current_status.configure(fg_color="#ff2b2b", text_color="#FFF")
                    self.is_forbid = True
                    #! WIP accel_mode[3] ถ้าเป็น accel mode อาจจะไม่ต้องใช้ popup แต่ใช้เป็นการเก็บผลลัพธ์การทำงานแทน
                    self.app.POP_UP.show(
                        "Caution!!", f"Order นี้มีสถานะ '{self.app.cus_cur_status.get()}' จะทำต่อจริงอ่อ?", "alert")

                self.is_status_true = self.app.order_status == self.app.cus_cur_status.get()
                if self.is_status_true:
                    print(self.app.order_status == self.app.cus_cur_status.get())
                    print("Status in the file is reliable")
                else:
                    print(self.app.order_status == self.app.cus_cur_status.get())
                    print("Status in the file is unreliable, suggest downloading a new Export File from the link below")
                    print("https://seller.shopee.co.th/portal/sale/shipment?type=toship")

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
                             '/html/body/div/section/div[2]/div/div[1]/div/div/div[3]/div/div[3]/div[1]/div[1]/div[2]/div[2]/span[1]/span[2]/span/a')))

                # * กรอก order ลงในช่อง search
                self.search_elmt = self.wait50.until(
                    EC.visibility_of_element_located(
                        (By.XPATH,
                         '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/span/input')))

                self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/span/input').clear()

                self.input_count = []

                try:
                    close_btn = self.driver.find_element(
                        By.XPATH,
                        '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/div[1]/span[2]')

                    try:
                        self.input_count = self.driver.find_element(
                            By.XPATH,
                            '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/div[2]/span/span')
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
                self.search_elmt.send_keys(self.app.cus_order.get())

                # * กด Search เพื่อ เก็บ Status
                self.searchBtn = self.driver.find_element(
                    By.XPATH,
                    '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/div[1]')
                self.searchBtn.click()
                time.sleep(0.75)

                # * ตรวจสอบ Status และ update
                # รอให้ btn element กดได้
                self.wait50.until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         '/html/body/div/section/div[2]/div/div[1]/div/div/div[3]/div/div[3]/div/div[2]/div/div/div[5]/div[1]/button')))

                # เก็บ status order เข้าตัวแปรไปแสดงผลใน GUI
                self.app.cus_cur_status.set(self.driver.find_element(
                    By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/div[3]/div/div[3]/div/div[2]/div/div/div[5]/div[1]/button/span').text)

                # จะได้ element มา
                print("realtime_status_text", self.app.cus_cur_status.get())
                self.app.display_current_status.configure(text_color="#000000", fg_color="#8fd4ff")
                if "พิมพ์ใบแจ้งหนี้" in self.app.cus_cur_status.get():
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
                self.app.display_bot_status_label.configure(
                    text=f"Bot Status: ˶ᵔ ᵕ ᵔ˶ จบการทำงาน", fg_color="#d9f2ff", text_color="#000")
                return

            ### * SMCO PART ############################################################################
            # * เปลี่ยนไปtab SMCO0 เพื่อเช็ค ชื่อลูกค้า
            try:
                self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
                print("SMCO :: เปิดการขาย ไม่หาย ไปต่อ")
                logger.info(f"{self.app.cus_order.get()}: SMCO :: เปิดการขาย ไม่หาย ไปต่อ")
            except:  # * กรณีหน้าเปิดการขายมันหายไป
                print("SMCO :: เปิดการขาย หายไป เปิดใหม่")
                logger.info(f"{self.app.cus_order.get()}: SMCO :: เปิดการขาย หายไป เปิดใหม่")
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

            # * ใส่ รหัสพนักงาน ===============================================================================
            self.insert_emp()

            # ! wip test new class
            # * ดูก่อนว่าเคลียชื่อลูกค้าแล้วเหรอยัง
            # self.cus_name_span_elmt_loc = '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/div[2]/form/div/span/span[1]/span/span[1]'
            self.cus_name_span_elmt_loc = '//span[@id="select2-memberSearch-container"]'
            self.cus_name_span_x_btn_text = ""
            self.is_reset = False
            while not self.operation_thread.is_set():
                try:
                    self.cus_name_span_elmt = self.driver.find_element(By.XPATH, self.cus_name_span_elmt_loc)
                    self.cus_name_span_x_btn_text = self.cus_name_span_elmt.text
                    print("found element cus_name_span_elmt ")
                    break
                except:
                    print("finding element cus_name_span_elmt")
                    time.sleep(0.5)
                    continue

            # * เพราะวิธีออกใบกำกับมันยังไม่แน่นอนมีทั้งแบบเก่าและแบบใหม่ แบบเก่ามันจะทำโดยขั้นตอนด้านล่างนี่ แต่ถ้าเป็นแบบใหม่มันจะย้ายไปทำหน้าท้าย ซึ่งไม่รู้จะย้ายไปไม
            self.is_old_tax_form = False
            if self.driver.find_element(By.XPATH, self.cus_name_span_elmt_loc).is_displayed():
                self.is_old_tax_form = True
                print("element cus_name_span_elmt is displayed")

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
                        self.driver.find_element(By.XPATH, self.cus_name_span_elmt_loc).click()
                        items_list = self.driver.find_elements(
                            By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
                        if len(items_list) == 0:
                            # * คลิกเพื่อให้ปิด droprdown
                            self.driver.find_element(By.XPATH, self.cus_name_span_elmt_loc).click()
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
                                self.driver.find_element(By.XPATH, self.cus_name_span_elmt_loc).click()
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

                # * เปลี่ยน auto เป็น name ไม่ก็ email โดยขึ้นอยู่กับว่าขอใบกำกับหรือไม่
                self.driver.find_element(
                    By.XPATH, "//div[contains(@ng-show, 'abbCustomerFlag')]//div[contains(@class, 'input-group-prepend')]/button").click()
                print("self.app.tax_bool: ", self.app.tax_bool.get())

                # * จากปัญหาข้อที่ 39 // รอให้ตัวเลือกภายใน click ได้ก่อน แล้วค่อย เลือก วิธีการ searchs
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
                    self.cus_name_span = self.driver.find_element(
                        By.XPATH, "//span[@id='select2-memberSearch-container']")
                    # * ที่กล้าเก็บค่า attribute มาใช้ตรงๆแบบนี้เพราะต่อให้ไม่มี attribute มันก็ return ค่าว่างอยู่ดี
                    self.text_from_name_span = self.cus_name_span.get_attribute("title")
                    self.tax_address_corrector(self.text_from_name_span)

                else:
                    print("no tax required, skip address check")

            # * ใส่ค่าขนส่ง ================================================================================
            # * ค่าขนส่งเราจะใส่ให้ SHOPEE เท่านั้น
            if self.app.marketplace_target.get() == "SHOPEE":
                self.add_shipping_cost()

            self.app.update_log("Autoหน้าแรก มันจบแค่นี้ ยิงของ, ใส่คูปอง, กดไปหน้าถัดไปได้เลย")
            self.app.display_bot_status_label.configure(
                text=f"Bot Status: Your Turn", fg_color="#21ff29", text_color="#000")

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

            # todo for testing
            # * Update Accel file //////////////////////
            # try:
            #     self.app.accel_mode.deduct_accel_file_data(
            #         self.app.cus_order, getattr(self.app.accel_mode, "used_serials", []))
            # except Exception as err:
            #     logger.info(f"test: cannot excute: self.app.accel_mode.deduct_accel_file_data(): {err}")

            # logger.info(f"Order: {self.app.cus_order.get()} Testing End!!")
            # return

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
                            self.cus_name_input_element = self.driver.find_element(
                                By.CSS_SELECTOR, '#select2-salePersonSearch-container')
                            title_attribute = self.cus_name_input_element.get_attribute("title")

                            # * ตรวจสอบว่าหน้าสุดท้ายหรือยัง
                            is_final_page_displayed = self.driver.find_element(
                                By.XPATH, "//*[contains(text(),' Payment: ') or  contains(text(), 'ชำระเงิน:') or contains(text(), 'CN Reason')]").is_displayed()
                            break
                        except:
                            # * ไม่มี element ให้วนเรื่อยๆ
                            continue

                    # *ดึงตัวอักษรออกมา
                    #! matched_obj = re.search("^C[0-9]+", title_attribute) เลิกใช้ เพราะบางชื่อมันไม่ขึ้นต้นด้วย C
                    matched_obj = re.search(r"^[0-9]+-", title_attribute)
                    try:
                        self.is_input_empty = matched_obj.group()
                    except:
                        self.is_input_empty = ""

                    # * แก้ bot ดับจาก alert
                    while not self.operation_thread.is_set():
                        time.sleep(0.55)
                        try:

                            sn_window = self.driver.find_element(
                                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[7]/div/div/div[1]')
                            # print("SN_window is still there")
                            if sn_window.is_displayed():
                                # print("หน้า SN กำลังโชว์")

                                # if self.driver.find_element(By.XPATH, self.cus_name_span_elmt_loc).is_displayed():
                                continue

                            else:
                                # print("หน้า SN ไม่ได้โ๙ว์")
                                break
                        except UnexpectedAlertPresentException as err:
                            # self.alert_text = self.driver.switch_to.alert.text ใช้ไม่ได้
                            # print("alertทั้งหมดคือไร", err)
                            print("Show only the part of obj err", err.alert_text)
                            self.app.POP_UP.show("SN Duplicate", f'{err.alert_text}', "alert")
                            # self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])
                            # WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                            # print("Popupโผล่")
                            continue

                    if self.is_input_empty == "" and is_final_page_displayed == False:
                        print("Emp name disappeared")
                        break
                    elif (self.cus_name_input_element.text != "Select Customer" or self.cus_name_input_element.text != "กรุณาเลือก") and is_final_page_displayed == False:
                        continue
                    elif (self.cus_name_input_element.text != "Select Customer" or self.cus_name_input_element.text != "กรุณาเลือก") and is_final_page_displayed == True:
                        self.app.is_bot_browser_busy.set(True)
                        time.sleep(0.55)
                        print("Page Payment")
                        is_final_page2 = self.wait50.until(EC.visibility_of_element_located(
                            (By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[1]/span[1]')))
                        self.last_page = self.driver.find_element(
                            By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[1]/span[1]')
                        if (self.last_page.text == "Payment:") or (self.last_page.text == "ชำระเงิน:"):
                            # Auto หน้าท้าย ทำได้ครั้งเดียว
                            is_final_page2 = self.wait50.until(EC.visibility_of_element_located(
                                (By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[1]/span[1]')))

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

                                # ถ้าไม่มี seller ก็ไปกรอก remark ได้เลย
                                time.sleep(0.75)
                                self.driver.find_element(
                                    By.XPATH,
                                    "/html/body/div[2]/div[3]/div[6]/div[2]/div/div[1]/div[5]/div[1]/textarea").clear()
                                self.driver.find_element(
                                    By.XPATH, "/html/body/div[2]/div[3]/div[6]/div[2]/div/div[1]/div[5]/div[1]/textarea").send_keys(self.app.cus_order.get())

                                # เลือกประเภทชำระเงิน
                                time.sleep(0.75)
                                if self.app.marketplace_target.get() == 'SHOPEE':
                                    channel = self.channel_options[f'{self.operation_states['purchased_channel']}']
                                    print("channel: ", channel)
                                    # เลือก shopee
                                    self.driver.find_element(By.XPATH, f"//a[contains(., '{channel}')]").click()
                                elif self.app.marketplace_target.get() == 'LAZADA':
                                    # เลือก lazada
                                    self.driver.find_element(By.XPATH, "//a[contains(., 'LAZ')]").click()

                                # * PO No:
                                po_no_input_element = self.driver.find_element(
                                    By.XPATH, "//input[@id='textbox81037000102']")
                                po_no_input_element.clear()
                                po_no_input_element.send_keys(self.app.cus_order.get())

                                # Todo migrate this section to 3.2.1 : update 3.1.5 auto toggle the sn toggle to "false" because default was set to "true"
                                # * ผมใช้เอง
                                self.driver.find_element(By.CSS_SELECTOR, '#cnRefFlag').click()

                                try:
                                    # จู่ๆ brows()btn มันก็ทำงานเลยต้องคลิกเพื่อปิด
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[3]/div[1]/div[1]/div/div/div/div/div[2]/center/button[2]').click()
                                except:
                                    print("ปุ่ม Brows() ไม่โผล่")

                                # * ลูกค้ามีชื่อไหม ถ้าไม่มี ใส่ a
                                if self.app.cus_name.get():
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[2]/div/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').clear()
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[2]/div/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').send_keys(self.app.cus_name.get())
                                else:
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[2]/div/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').clear()
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[2]/div/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').send_keys(self.app.cus_order.get())

                            except Exception as err:
                                print("Final page failed, skip to waiting for price")
                                print("err: ", err)
                                break

                            # *Auto Enter final Price
                            try:
                                print("Auto enter price")
                                print((self.app.sum_price + self.app.cus_ship_cost.get()) - self.app.cus_seller_voucher.get())
                                final_price = (self.app.sum_price + self.app.cus_ship_cost.get()
                                               ) - self.app.cus_seller_voucher.get()
                                self.driver.find_element(
                                    By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[2]/div/div/div[3]/div/div[2]/div[2]/div[1]/div[1]/input').clear()
                                self.driver.find_element(
                                    By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[2]/div/div/div[3]/div/div[2]/div[2]/div[1]/div[1]/input').send_keys(final_price)
                            except Exception as e:
                                print("auto_final_price broken", e)
                            # *Auto price มันมีสองอันได้ไง
                            # print("Auto enter price")
                            # print((self.app.sum_price + self.app.cus_ship_cost.get()) - self.app.cus_seller_voucher.get())
                            # final_price = (self.app.sum_price + self.app.cus_ship_cost.get()) - self.app.cus_seller_voucher.get()
                            # if self.app.user_id.get() in self.app.dev_account:
                            #     self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[2]/div/div/div[3]/div/div[2]/div[2]/div[1]/div[1]/input').clear()
                            #     self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[2]/div/div[2]/div/div/div[3]/div/div[2]/div[2]/div[1]/div[1]/input').send_keys(final_price)

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
                            self.final_popup_after_green_btn_handler()
                            # * ไม่แน่ใจ
                            continue
                        else:
                            print("จบสูตร")
                        self.autofinal = False
                        self.operation_thread.set()
                        break

                    print("Whileหลัก ถ้ามาถึงนี่แปลว่าต้องเริ่มใหม่")
                    continue
                break

            print("จบ auto_last_page")
            self.autofinal = False
            self.operation_thread.set()
            # self.driver.quit()

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
        
        #* มันมีปุ่มบางอย่างที่มันอาจจะทำให้มีปัญหาในการจัดการชื่อลูกค้าได้ มันจะแสดงผลในหน้าใหม่เท่านั้น หน้าเก่าไม่แสดง เลยต้อง try-except ไว้ เพราะมันอาจจะมีหรือไม่มีก็ได้
        try:
            self.diver.execute_script(""" return document.querySelector("button[ng-click='abbCustomerFlag = false;']").click(); """)
        except Exception as err:
            print("There's no the new abbCustomerFlag btn")
            print("abbCustomerFlag-err: ", err)
                
        customer_form_dialog_element = False
        # todo เช็ค dialog form โหลดเสร็จยัง
        while is_functionworking and not self.operation_thread.is_set():
            try:
                # * ไม่เจอ faded backdrop แปลว่ายังไม่เปิดnew cus form มันเลยจะไปเปิดใน except แล้วกลับมา
                customer_form_dialog_element = self.driver.find_element(By.CSS_SELECTOR, 'body > div.modal-backdrop.fade.in')
                customer_class_input = self.driver.find_element(By.XPATH, '//*[contains(@class, "select2-selection__rendered") and @id="select2-memberClass-container"]')
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
            logger.info(f"{self.app.cus_order.get()}: SMCO :: เปิดการขาย1 ไม่หาย ไปต่อ")
        except Exception as err:
            print("SMCO :: เปิดการขาย1 หายไป เปิดใหม่ {err}")
            logger.info(f"{self.app.cus_order.get()}: SMCO :: เปิดการขาย1 หายไป เปิดใหม่ {err}")
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
                    f"{self.app.cus_order.get()}: หลังจาก reopen และตรวจดูด้วย get_tabs, หน้า 'SMCO :: เปิดการขาย1' ไม่มีอยู่จริง {err}")
                self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])

        try:
            self.driver.find_element(
                By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]""").click()
            logger.info(f"{self.app.cus_order.get()}: there is a 'Close' button in SMCO :: เปิดการขาย1")
            print(f"{self.app.cus_order.get()}: there is a 'Close' button in SMCO :: เปิดการขาย1")
        except:
            print(f"{self.app.cus_order.get()}: there is no any 'Close' button in SMCO :: เปิดการขาย1")

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
            # Add branch info for tax customers
            if self.app.branch_type == 'สำนักงานใหญ่':
                name = f"{name} ({self.app.branch_type})"
            elif self.app.branch_type == "สาขาย่อย" and not pd.isna(self.app.data_frame[self.app.target_row]['รหัสประจำสาขา'].iloc[0]):
                name = f"{name} (สาขา{self.app.tax_branch_num.get()})"

            tax_num = self.app.tax_num.get()
            address = self.app.get_pure_address(self.app.address) if self.app.tax_bool.get() else self.app.address
            email = self.app.cus_email.get()
            phone = self.app.cus_tel.get()
            use_dropdown_address = True
            province = self.app.cus_province.get().replace("จังหวัด", "")
            district = self.app.cus_district.get().replace("อำเภอ", "").replace("เขต", "").replace("อ.", "")
            sub_district = self.app.cus_sub_district.get().replace("ตำบล", "").replace("แขวง", "").replace("ต.", "")

        elif customer_type == "tax_laz":
            tax_info = self.get_vatinfo_data(self.app.tax_num.get(), self.app.tax_branch.get())
            name = tax_info['name']

            # Add branch info for lazada tax customers
            if self.app.branch_type == 'สำนักงานใหญ่':
                self.app.tax_branch.set(self.app.nondistortedData['ประเภทสาขา'])
                if name.startswith("บริษัท") or "จำกัด" in name:
                    name += f" {tax_info['branch']}"
            elif self.app.branch_type == "สาขาย่อย" and not pd.isna(self.app.data_frame[self.app.target_row]['รหัสประจำสาขา'].iloc[0]):
                name = f"{name} (สาขา{self.app.tax_branch.get()})"

            tax_num = tax_info['tax_num']
            address = tax_info['address_shortened']
            email = self.app.cus_email.get()
            phone = self.app.cus_tel.get()
            use_dropdown_address = True
            province = tax_info['province'].replace("จังหวัด", "")
            district = tax_info['district'].replace("อำเภอ", "").replace("เขต", "").replace("ต.", "")
            sub_district = tax_info['sub_district'].replace("ตำบล", "").replace("แขวง", "").replace("ต.", "")

        # Fill customer form
        while is_functionworking and not self.operation_thread.is_set():
            try:
                # Name TH
                # self.wait50.until(EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[1]/input')))
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[1]/input').clear()
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[1]/input').send_keys(name)

                # Name ENG
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[2]/input').clear()
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[2]/input').send_keys(name)

                # Tax ID (only for tax customers)
                if tax_num:
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[3]/input').clear()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[4]/div[3]/input').send_keys(tax_num)

                # Address
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[8]/div/textarea').clear()
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[8]/div/textarea').send_keys(address)

                # Email (if provided)
                if email:
                    self.driver.find_element(
                        By.XPATH,
                        '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[14]/div[3]/input').clear()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[14]/div[3]/input').send_keys(email)

                # Phone
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[15]/div[3]/input').clear()
                self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[15]/div[3]/input').send_keys(phone)

                # Address dropdowns (only for tax customers)
                if use_dropdown_address:
                    # Country dropdown
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[10]/div[1]/div/span/span[1]/span').click()
                    self.dropdown_handler()

                    if customer_type == "tax":
                        self.driver.find_element(
                            By.XPATH, "/html/body/div[2]/div[3]/div[13]/span/span/span[2]/ul/li[2]").click()
                    else:  # tax_laz
                        self.driver.find_element(By.XPATH, "//*[text()='Thailand' or text()='ไทย']").click()

                    # * Province dropdown
                    self.driver.find_element(By.CSS_SELECTOR, 'span #select2-province-container').click()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input').clear()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input').send_keys(province)
                    self.dropdown_handler()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input').send_keys(Keys().ENTER)

                    # * District dropdown
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[12]/div[1]/div/span/span[1]/span/span[1]').click()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input').clear()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input').send_keys(district)
                    self.dropdown_handler()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input').send_keys(Keys().ENTER)

                    # * SubDistrict dropdown
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[12]/div[3]/div/span/span[1]/span/span[1]').click()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[12]/div[3]/div/span/span[1]/span/span[1]').click()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[2]/form/div[12]/div[3]/div/span/span[1]/span/span[1]').click()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input').clear()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input').send_keys(sub_district)
                    self.dropdown_handler()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/span/span/span[1]/input').send_keys(Keys().ENTER)

                print(f"customer_class_selector() initializing: is_functionworking {is_functionworking}")
                self.customer_class_selector(is_functionworking)

                # * CLick Save Button (commented out but kept for completeness)
                if customer_type == "normal":
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[1]/div[4]/button[1]').click()

                # Wait for save to complete
                while is_functionworking and not self.operation_thread.is_set():
                    try:
                        self.wait50.until(EC.invisibility_of_element_located(
                            (By.XPATH, '/html/body/div[2]/div[3]/div[13]/div/div/div[3]/div/div[1]/div[4]/button[1]')))
                        is_functionworking = False
                        break
                    except:
                        print("[metthod]addCustomer: Save button still appear")

                break

            except:
                print("addCustomer(): Elements cannot be found, retry filling customer form")
                if customer_type != "normal":
                    continue
                else:
                    break

        print(f"add {customer_type} Customer end")

    def addressExtractor(self, cusAddress):
        self.splited = cusAddress.split(",")
        return (self.splited)


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

        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': f'{self.origin}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }

        response = requests.post(
            f'{self.origin}/smartcore/uilts/oper/pos/getCustomerSearchPOS/selectoption.htm',
            cookies=cookies,
            headers=headers,
            data=payload,
            verify=False,
        )

        print('get_address_smco response status: ', response)
        print('response.json(): ', response.json())
        return response

    def smco_req_find_customer_id(self, cus_code: str = ""):
        print("find_customer_id excuted by code: ", cus_code)
        payload = {
            'requestText': f'{cus_code}',
            'target': 'C',
        }
        response = self.address_api_request_smco(payload)
        response_data: list = response.json()
        print("response_data: ", response_data)
        cus_data: dict = {}
        for i in response_data:
            if i['custCode'] == cus_code:
                cus_data = i
                break
            else:
                print(f'ไม่มี {cus_code} นี้จาก response_data')
                raise Exception(f'ไม่มี {cus_code} นี้จาก response_data')

        customer_id = cus_data['id'] or False
        # print("customer_id: ", cus_data['id'])
        return customer_id

    def smco_req_find_cus_address(self, cus_id: int = None):
        max_retries = 3
        retry_count = 0

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

                response.raise_for_status()  # จะ raise exception ถ้า status code เป็น 4xx หรือ 5xx

                response_data: dict = response.json()
                extracted_address: dict = {}

                for address in response_data['addressOfMember']:
                    if address['defaultFlag']:
                        extracted_address['address'] = address['custAddress'] or ''
                        extracted_address['subdistrict'] = address['subDustricId']['subdistrictNameTh'] or ''
                        extracted_address['district'] = address['districtId']['districtNameTh'] or ''
                        extracted_address['provice'] = address['provinceId']['provinceNameTh'] or ''
                        extracted_address['zip_code'] = address['zipCode'] or ''

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

    def wait_element(self, xpath, text=None):
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

    def tax_address_corrector(self, cus_name):
        print("cus_name: ", cus_name)
        # match = re.search(r'C\d*(?=-)', cus_name) #! อันนี้ถ้าหากมีคนตั้งชื่อเหมือนรหัสมันจะเจอสองจุดแต่ patternจริงๆแล้วนั้นรหัสมันจะต้องขึ้นต้นก่อนเสมอฉะนั้นต้องปรับ
        match = re.search(r'^C\d{1,}(?=-)', cus_name)  # * for customer code
        self.cus_code = match.group()

        customer_id = self.smco_req_find_customer_id(self.cus_code)

        if customer_id:
            cus_address = self.smco_req_find_cus_address(customer_id)
        else:
            cus_address = {
                'address': '',
                'subdistrict': '',
                'district': '',
                'provice': '',
                'zip_code': ''
            }
        # ตรวจสอบว่าได้ข้อมูลที่ถูกต้องมาหรือไม่
        if not any(cus_address.values()):
            print("Address not matched")
            # self.app.POP_UP.show(
            #     "Error",
            #     "ไม่สามารถดึงข้อมูลที่อยู่ลูกค้าได้ กรุณาลองใหม่อีกครั้ง",
            #     "alert"
            # )

        cus_address_to_compare = "".join(cus_address.values())
        # print("cus_address_to_compare: ", cus_address_to_compare)

        self.current_address = cus_address_to_compare
        self.desired_address = re.sub(
            r'\n', " ", f"""{self.app.get_pure_address(self.app.address)}  {self.app.nondistortedData['แขวง/ตำบล']}
            {self.app.nondistortedData['เขต/อำเภอ.1']}  {self.app.nondistortedData['จังหวัด.1']}
            {self.app.nondistortedData['รหัสไปรษณีย์.1']} """.replace('\u200b', ''))
        self.desired_address = re.sub(r'\s{2,}', ' ', self.desired_address)
        print("self.desired_address: ", self.desired_address.replace(' ', ''))

        self.desired_full_address = self.desired_address.replace(
            "อำเภอ", "").replace(
            "เขต", "").replace(
            "อ.", "").replace(
            "ตำบล", "").replace(
            "แขวง", "").replace(
            "ต.", "").replace(
            "จังหวัด", "").replace(
            "จ.", "")

        print("compare self.current_address & self.desired_full_address")
        print(self.current_address.replace(' ', ''))
        print(self.desired_full_address.replace(' ', ''))

        if not self.current_address.replace(
                ' ', '') == self.desired_full_address.replace(
                ' ', ''):  # * ต้อง replaceช่องว่างตอนเทียบเพื่อจะได้หาความเหมือนแค่ตัวอักษร
            # * เข้าหน้าข้อมูลลูกค้า------------------------------------------------------------------------------
            logger.info(f"{self.app.cus_order.get()}: compare self.current_address & self.desired_full_address")
            logger.info(self.current_address.replace(' ', ''))
            logger.info(self.desired_full_address.replace(' ', ''))
            print("Customer Address is not correct")

            self.get_tabs()
            if not 'SMCO :: ลูกค้า' in self.merged_dict:
                self.open_customer_edit_page()

            self.direct_to_customer_info()

            address_revise_btn = self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[2]/div[1]/div/div[6]/a')
            address_revise_btn.click()
            self.wait_element(
                '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[1]/div[2]/textarea')
            address_revise_input_popup = self.driver.find_element(
                By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[1]/div[2]/textarea')

            is_address_revice_end = False
            while not is_address_revice_end:
                try:
                    # * กรอก Address
                    address_revise_input_popup.clear()
                    self.desired_address = self.app.get_pure_address(self.desired_address)
                    address_revise_input_popup.send_keys(self.desired_address)

                    # * tel.
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[13]/div[4]/input').clear()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[13]/div[4]/input').send_keys(self.app.cus_tel.get())

                    ### * เป็นแบบกรอกแบบ DropDown ##########################################################################################################
                    # * dropdown Country
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[2]/div/span/span[1]/span/span[1]').click()
                    time.sleep(1.55)
                    # * select thailand in dropdown
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[2]/ul/li[2]').click()

                    # * province dropdown
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[4]/div/span/span[1]/span/span[1]').click()

                    # * province input
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input').clear()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input').send_keys(
                        self.app.cus_province.get().replace("จังหวัด", ""))
                    time.sleep(1.75)
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input').send_keys(Keys().ENTER)

                    # * District drop
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[6]/div/span/span[1]/span/span[1]').click()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input').clear()

                    # * District fill and enter
                    self.driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input').send_keys(
                        self.app.cus_district.get().replace("อำเภอ", "").replace("เขต", "").replace("ต.", ""))  # District
                    time.sleep(1.75)
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input').send_keys(Keys().ENTER)

                    # * SubDistrict drop
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[8]/div/span/span[1]/span/span[1]').click()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[8]/div/span/span[1]/span/span[1]').click()
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[8]/div/span/span[1]/span/span[1]').click()

                    # * SubDistrict fill and enter
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input').clear()
                    self.driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input').send_keys(
                        self.app.cus_sub_district.get().replace("ตำบล", "").replace("แขวง", "").replace("ต.", ""))  # SubDistrict
                    time.sleep(1.75)
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input').send_keys(Keys().ENTER)

                    print(f"""{self.app.cus_order.get()}: Address Revise Complete""")
                    is_address_revice_end = True
                    break
                except Exception as err:
                    print(f"Address Revise Error1 : {traceback.format_exc()}")
                    print(f"Address Revise Error2 : {err}")
                    logger.info(f"""{self.app.cus_order.get()}: Address Revise Error1 : {traceback.format_exc()}""")
                    logger.info(f"""{self.app.cus_order.get()}: Address Revise Error2 : {err}""")
                    continue

            self.app.is_bot_browser_busy.set(False)
            while not self.operation_thread.is_set():
                time.sleep(0.25)
                try:
                    'SMCO :: ลูกค้า' in self.merged_dict
                    success_popup_element = self.driver.find_element(By.CSS_SELECTOR, '.swal2-icon.swal2-success')
                    if success_popup_element.is_displayed():
                        self.app.is_bot_browser_busy.set(True)
                        break
                    continue
                except:
                    continue

            # #*  กด save เพื่อ บันทึกการเปลี่ยนที่อยู่ แล้วจะทำให้ pop-up แก้ที่อยู่หายไป
            # revised_submit = self.driver.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[1]/div/button[2]')
            # revised_submit.click()

            # ? กดปิดหน้าลูกค้า ใช้ดีไหม ปิดไว้ก่อน
            # while not self.operation_thread.is_set():
            #     try:
            #         cancel_btn = self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div/div[1]/div[1]/div[1]')
            #         cancel_btn.click()
            #         break
            #     except:
            #         continue

            # * กลับไปหน้าการขาย
            self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])

            # ? /lasted update/ปัจจุบันหากผลลัพเปนอันเดิมมันจะไม่ resetละทำให้code ส่วนนี้อาจจะไร้ประโยชน์  ปิดไว้ก่อย/todo/เพื่อ reset ค่า address ให้เป็น lasted update
            # self.driver.find_element(By.XPATH, self.cus_name_span_elmt_loc).click() #* กดล้างค่า เพื่อให้มันล้าง state ที่มาจากการ fetch ของ smco
            # self.driver.find_element(By.XPATH, '//div[contains(@ng-show, 'abbCustomerFlag')]//div[contains(@class, 'input-group-prepend')]/button').click() #* กด dropdown เพื่อดู list ประเภทของการ query data ลูกค้า
            # self.wait50.until(EC.element_to_be_clickable((By.XPATH, r'''//div[contains(@ng-show, "abbCustomerFlag")]//a[contains(@ng-click, "st='E'")]'''))) #* รอ dropdown ให้มันแสดงผลออกมา
            # self.driver.find_element(By.XPATH, r'''//div[contains(@ng-show, "abbCustomerFlag")]//a[contains(@ng-click, "st='C'")]''').click() #* กดเลือกประเภทการ query data ลูกค้า, ให้เป็น query จาก customer code
            # self.enter_cus_name(self.cus_code) #* ใส่ customer code ลง input ช่องค้นหา

            # while not self.operation_thread.is_set(): #* รอกด li อันที่1 จาก dropdown ให้มันแสดงผลออกมา
            #     time.sleep(0.25)
            #     try:
            #         if self.cus_code in self.driver.find_element(By.XPATH, self.app.cusNameLi1).text:
            #             self.driver.find_element(By.XPATH, self.app.cusNameLi1).click()
            #             break
            #         continue
            #     except:
            #         continue

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
        # driver.find_element(By.CSS_SELECTOR, f"div.col-xs-3 div.col-sm-7 input.form-control.input-height.ng-valid.ng-valid-maxlength.ng-touched").send_keys(self.app.tax_num.get())
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
            print("Not Duplicate")
            logger.info(f"{self.app.cus_order.get()}: After adding cusname, the cusname is Not Duplicated")
            return
        print("close dup popup = ", self.dup_popup_content)

        # * เก็บรหัสเพื่อไปเสิชหาว่าdupที่ใคร
        matched_obj = re.search(r'^C.\d*', self.dup_popup_content, re.MULTILINE)
        print("matched_obj:", matched_obj)
        self.cus_code = matched_obj.group()
        print("cus_code: ", self.cus_code)
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
            self.driver.find_element(
                By.CSS_SELECTOR,
                'body div.swal2-container div.swal2-modal.show-swal2.visible button.swal2-confirm.styled').click()
        except:
            pass

# * function แยก address:str ที่ได้จาก vatinfo ให้เป็น part ย่อย (เขต, แขวง, จังหวัด, ปณ.)-------------------------------------
    def classify_vatinfo_address(self, input):
        try:
            # Create a copy of the output dictionary
            result = input
            print("resultสำหรับ classify คือไร :", result)

            # Remove the "ตำบล" and everything after it from the address
            address_only = re.compile(r'(?:ตำบล|ต\.).*')
            result['address_shortened'] = address_only.sub('', result['address']).strip()

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

    def get_res_vatinfo(self, tax_num, tax_branch):
        tax_input = str(tax_num)
        branch = str(tax_branch)
        jsession_id = ''

        # เราจะไม่ใช้ cookies แต่จะใช้ค่าจาก class แรกสุด เพราะ
        # cookies = self.app.cookies['vatinfo']
        print("cookies for reqtaxinfo: ", self.app.cookies['vatinfo'])

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            # 'Cookie': 'JSESSIONID=0000afl1mgz_VGdxFmh7f5mQJqf:-1',
            'Origin': 'https://vsreg.rd.go.th',
            'Referer': 'https://vsreg.rd.go.th/VATINFOWSWeb/jsp/VATInfoWSServlet',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        params = ''

        data = {
            'operation': 'searchByTin',
            'goto_page': '',
            'tin': 'on',
            'txtTin': tax_input,
            'branotxt': '',
            'fname': 'null',
            'lname': 'null',
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
            if times == 1:
                print("times = 1")
                response = session.post('https://vsreg.rd.go.th/VATINFOWSWeb/jsp/VATInfoWSServlet',
                                        cookies=self.app.cookies['vatinfo'], params=params, headers=headers, data=data)

                # Todo มันมีการตรวจสอบ cookies ตลอดเวลา แต่ครั้งแรกreqไปมันจะตรวจสอบก่อน ถ้าไม่มีมันจะ return มาให้  ครั้งถัดไปมันจะตรวจอีกถ้ามี"แล้วยังใช้ได้" มันจะไม่ return ให้ ถ้าใช้ไม่ได้มันจะ return ตัวใหม่ให้
                try:
                    # * กรณี ที่ มี cookies returns กลับมา เพราะอันเก่ามันหมดอายุแล้ว หรือไม่เคยมีมาก่อน
                    print("response cookies ไรมา", response.cookies)
                    # * > เก็บค่า cookies จาก response เข้าไปใน cookies ที่มีอยู่แล้ว
                    jsession_id = response.cookies['JSESSIONID']
                    print("we never have usable cookies before that why the response has cookies. We'll use it like a state in app.cookies")
                    self.app.cookies['vatinfo']['JSESSIONID'] = f"""{jsession_id}"""
                except Exception as err:
                    # * กรณี ที่ ไม่มี cookies returns กลับมา เพราะอันเก่าใช้ได้อยู่ ใช้ cookies เดิมได้เลย
                    print(
                        "if the response is '<RequestCookieJar[]>', it indicates that no cookies were returned. Therefore, we already have available cookies now.",
                        response)

            elif times > 1:
                print("jsession_id", jsession_id)
                # รอบสองเราเอา cookies มาประกอบ request โดย data ที่ใช้ request รอบนี้เป็นอีกแบบนึงจะต้องมี cookie เป็นตัวยืนยันว่าเคย login มาแล้ว ถ้าไม่มี cookie จะผ่านไม่ได้ เหมือนจะเป็น authen

                data2['goto_page'] = f'{times}'
                response = session.post(
                    'https://vsreg.rd.go.th/VATINFOWSWeb/jsp/VATInfoWSServlet?', params=params,
                    cookies=self.app.cookies['vatinfo'],
                    headers=headers, data=data2)

            try:
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                # print("ได้ไรออกมา", soup)
                # หาว่า response มี <tr> หรือไม่ มีเท่าไหร่
                menu_elements = soup.select('tr[class^="trMenu"]')
                is_many_page = soup.select("""span[onclick^="gotoPage('"]""")
                print("มีหลายหน้า?: ", bool(is_many_page))
                search_result = []
                output = ""

                # * ตรวจหา element รายการข้อมูลใบกำกับ ซึ่งมันจะมี class ชื่อ trmenu
                if len(menu_elements):
                    # * มี <tr>
                    for menu_element in menu_elements:
                        result_data = {
                            "no": "",
                            "tax_num": "",
                            "branch": "",
                            "name": "",
                            "address": "",
                            "postal_code": ""
                        }

                        # print(menu_element) <<หาทั้งหมด
                        # * tr = menu_element.find('tr')
                        # * ในแต่ละ <tr> มี <td> หลายอัน
                        tds = menu_element.find_all('td')
                        for idx, key in enumerate(result_data):
                            b = tds[idx].find('b')
                            result = b.find('font').text.strip()
                            result = re.sub(r"\s{2,}", " ", result)

                            # * ช่วงใบกำกับ จะตัดเอาค่า 13 หลักจากด้านหลัง เพราะไอ 10 หลักตอนแรกมันคือไรไม่รู้
                            if idx == 1 and len(result) > 13:
                                result = result[-13:]

                            print(result)
                            result_data[key] = result
                        print(" ")
                        search_result.append(result_data)

                    # * เอา search_result มาดูว่าตรงกับสาขาที่ต้องการหรือไม่
                    for item in search_result:
                        if item['branch'] == self.app.branch_type:
                            output = item
                            print("เกบค่าลง dict result ลง output", output)
                            break
                    if bool(output) == False:
                        print("ว่างต้องวนใหม่")
                        times += 1
                        continue
                    else:
                        print("ใช้ได้", output)
                        break

                elif bool(menu_elements) == False:
                    # ไม่มี <tr>
                    print("ไม่มีใบกำกับจาก request", output)
                    break

            except session.exceptions.HTTPError as e:
                print(f"HTTP Error occurred: {e}")
            except Exception as e:
                print(f"An error occured: {e}")
            break

        output = self.classify_vatinfo_address(output)
        print("output: ", output)
        return output

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
            print("คนที่คะแนนเยอะสุด", most_tambon)
            return most_tambon
        except:
            print('ไม่มี element')
            return possible_tambons[0]

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def address_seperator(self, df, order):
        # * function ใช้สำหรับลูกค้าขอใบกำกับ เพราะมันต้องย้ายค่าตำบล ออกไปใส่ใบกำกับ
        print("assign_address order:", order)
        # เตรียมข้อมูล Pattern ที่อยู่คนไทย
        df['ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป'] = df['ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป'].astype(str)
        df['หมายเลขคำสั่งซื้อ'] = df['หมายเลขคำสั่งซื้อ'].astype(str)

        # * หาตำบลจากไฟล์
        target_row_index = df['หมายเลขคำสั่งซื้อ'] == order
        if any(target_row_index) == True:
            print("เจอ Order ใน ไฟล์")
            cus_address = df[target_row_index]['ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป'].iloc[0]
            print("cus_address", cus_address)
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
                if tambon in cus_address:
                    print("ทำไมได้ตลาดยอดวะ", tambon)
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
                googled_tambon = self.google_for_tambon(
                    address_dict, possible_tambons)
                decent_tambon = googled_tambon
                is_alert = True
                self.app.POP_UP.show("Caution!!", f""""ตำบล"อันนี้มั่วมาโปรดตรวจสอบก่อนออกบิล""", "alert")

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

    def get_vatinfo_data(self, tax_num, branch):
        if branch == "":
            branch = "สำนักงานใหญ่"
        print(f'ใช้ vatinfo_req และส่ง data body ด้วย : {str(tax_num)}, สาขา {str(branch)}')

        # * หาชื่อใบกำกับจาก vatinfo
        result = self.get_res_vatinfo(str(tax_num), str(branch))

        # * กรณีหาจาก taxinfo ไม่มี ทำให้ต้อง หาจาก Excel ที่ import เข้ามา
        if bool(result) == False:
            # * หาตำบล จาก address ที่ลูกค้าให้มา
            cus_address_from_table = self.address_seperator(
                self.app.data_frame, self.app.cus_order.get())

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
                #! ไม่มีช่องว่าง แปลว่าอับปรีย์
                result['name'] = result['name'].replace(
                    "บริษัท", "บริษัท ").replace(
                    "ห้างหุ้นส่วนจำกัด", "ห้างหุ้นส่วนจำกัด ")
                print("ไม่เจอช่องว่างจาก response แต่เพิ่มให้แล้ว", result['name'])

        return result

    def final_popup_after_green_btn_handler(self):
        self.app.is_bot_browser_busy.set(False)
        auto_radio_times = 0
        while not self.operation_thread.is_set():
            time.sleep(1)
            try:
                # print("auto click Before print loop")
                # final_popup = self.driver.find_element(By.XPATH, """//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]""") #! ปุ่มนี้น่าจะหายไปละ
                final_popup = self.driver.find_element(By.XPATH, """//div[@class = 'swal2-content']""")
                convert_full_tax_modal_element = self.driver.find_element(
                    By.XPATH, "//div[@id = 'convertFullTaxModal']")
                is_final_page = self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[1]/span[1]')
                #!พัง self.etax_radio_sendmail = self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[2]/label/input') element etax อยู่ไหนไม่รู้
                print("is_final_page= ", is_final_page)
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

            #! ตรงนี้อาจจะย้ายไปเป็นฟังชั่นใหม่
            # elif convert_full_tax_modal_element.is_displayed():
            #     print("convertFullTaxModal displayed")
            #     try:
            #         if
            #         pass
            #     except:

            #         pass

            elif is_final_page.is_displayed() == False:
                print("หน้า final หายไป")
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
                    # *> ให้เวลาดูเลขบิล 1 วิ
                    time.sleep(1)

                    alert_text = self.driver.find_element(
                        By().XPATH, """//div[@class = 'swal2-content']""").text  # อันนี้น่าจะใช้ไม่ได้ละ

                    match = re.search(r'B\d+-\w.*\d+-\d+', alert_text)
                    print("match: ", match)
                    # * ถ้าไม่มีบิล, match จะ = none ทำให้ .group() ไม่ได้ แล้ว return error ห
                    inv_number = match.group()
                    print("inv_number: ", inv_number)
                    self.app.update_log(f'เลขบิล: {inv_number}')

                    # * สลับไปreprintก่อนแล้วค่อยกลับมากด เพราะมันช้ากรอกรอไว้เลย
                    # * ไปหน้า Reprint ##########################################################################################
                    if is_etax and inv_number != "":
                        print("has etax")
                        self.etax_reprint(inv_number)
                        # * Update Accel file //////////////////////
                        try:
                            self.app.accel_mode.used_serials
                            print("Accel mode used")
                            # * ใช้ getattr() แทน self.app.accel_mode.used_serialsโดยตรง เพราะ ค่า self.app.accel_mode.used_serials จะเกิดขึ้นในกรณีใช้ accel mode เท่านั้น
                            self.app.accel_mode.deduct_accel_file_data(
                                self.app.cus_order,
                                getattr(self.app.accel_mode, "used_serials", []))
                        except:
                            print("Accel mode not used")
                            pass
                        # * ถ้ามี etax ก็ print แล้วจบไป
                        time.sleep(0.75)
                        # final_popup_btn.click() #! ปุ่มนี้น่าจะหายไปละ
                        break

                    # self.wait50.until(EC.invisibility_of_element_located((By.XPATH, """//div[@class = 'swal2-content']""")))
                    # time.sleep(1)
                    # final_popup_btn.click() #! ปุ่มนี้น่าจะหายไปละ

                    # * ลอง click container ดู ใช้ได้แล้ว
                    print("click container!")
                    self.driver.execute_script(
                        "document.querySelector('.swal2-overlay').click();")  # * อันนี้ดีย์

                    # * > printing
                    # * >> รอหน้า canvas โผล่ก่อน
                    self.wait50.until(EC.visibility_of_element_located(
                        (By.XPATH, '/html/body/div[2]/div[3]/div[10]/div/div[2]/div[2]/div/embed')))
                    time.sleep(1)

                    #! วิธี print แบบเก่า
                    # self.printtingPage()
                    # self.justPressP()
                    # * วิธี print แบบใหม่
                    self.printing_thread = threading.Thread(
                        target=self.get_pdf_src_and_print, args=(inv_number,))
                    self.printing_thread.start()
                    #! self.get_pdf_src_and_print(inv_number) ถ้าบรรทัดข้างบนใช้ได้มึงโดนโละแน่

                    # * Update Accel file //////////////////////
                    try:
                        self.app.accel_mode.used_serials
                        print("Accel mode used")
                        # * ใช้ getattr() แทน self.app.accel_mode.used_serialsโดยตรง เพราะ ค่า self.app.accel_mode.used_serials จะเกิดขึ้นในกรณีใช้ accel mode เท่านั้น
                        self.app.accel_mode.deduct_accel_file_data(
                            self.app.cus_order, getattr(self.app.accel_mode, "used_serials", []))

                    except:
                        print("Accel mode not used")
                        pass

                except Exception as err:
                    # time.sleep(1)
                    # print("ไม่ได้เลขบิล")
                    # final_popup.click()
                    try:
                        final_popup_btn.click()  # ! ปุ่มนี้น่าจะหายไปละ
                    except:
                        pass
                    print("พัง ข้ามไปเลยละกัน", err)

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
                # self.justPressP()
                # break

            # * >> แบบมี ETAX มันจะ redirect กลับไปหน้าเดิม
            elif is_final_page.is_displayed() == False:
                print("End or back")
                if bool(
                    re.search(
                        r"\w{5}\-\w{3}-\w{10}", self.driver.find_element(
                            By.XPATH, '/html/body/div[2]/div[3]/div[10]/div/div[1]/div[1]').text)):
                    print("ไปหน้าสุดท้าย จบ loop")
                    break
                elif self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/form/label') and self.is_input_empty == "":
                    print("มันจบละ")
                    break
                elif self.driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/form/label'):
                    print("กลับมาหน้าเดิม")
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


if __name__ == "__main__":
    def on_closing():
        print("Tkinter window is closing")
        root.destroy()
        PopUp.destroy_all()

    # def ctrl_saraea_copy(event):
    #     ctrl_state = event.state & 0x4 != 0  # 0x4 คือ flag สำหรับ Control key
    #     # 67 คือรหัสสำหรับสระแอในภาษาไทย (อาจแตกต่างบนระบบอื่นๆ)
    #     if ctrl_state and event.keycode == 67:
    #         event.widget.event_generate("<<Copy>>")

    # * เทคนิคคือ เช็คว่า ascii คือไร แล้วดูด้วยว่า นอกจากรับแบบ ascii แล้วรับแบบ keysym(ตัวอักษรจริง)ว่าตรงกับ ascii ไหม ถ้าไม่ตรงแปลว่าคนละภาษาแน่นอน เพราะ มันจะได้ ??
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

    # * Create Instance
    app = MyApp(root)
    if getattr(sys, 'frozen', False):
        pyi_splash.close()
    root.mainloop()
    print("Program closed")
