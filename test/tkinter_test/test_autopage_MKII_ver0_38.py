
from bs4 import BeautifulSoup
from googletrans import Translator
import requests

# * user interface
from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
from tkinter import font
# * dataframe table
import numpy as np
import pandas as pd
# from test_auto_cus_name_MKII import *

# * selenium
import time
import win32com.client as comclt
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener
from selenium.webdriver.support.abstract_event_listener import AbstractEventListener
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
# from ....python_modules3.SMCO.cusNameFixer import cusNameFixer, currencyRemover, addressExtractor, cusNameFixer2, cusNameFixer3

from xml.dom.minidom import Document
import os
import sys

import threading
from concurrent.futures import ThreadPoolExecutor

import locale
from decimal import Decimal
locale.setlocale(locale.LC_ALL, 'en_us')

# beautifulsoup


class MyApp:
    def __init__(self, root):
        self.root = root
        # self.validate_input_variable = self.root.register(self.validate_input)
        self.user_id = StringVar(value="")
        self.user_pw = StringVar(value="")
        self.result = ""
        self.table_location = ""
        self.marketplace_target = StringVar(value="MarketPlace")
        self.bg_by_market_place = {
            'SHOPEE': '#ee4d2d', 'LAZADA': '#201adb', '': '#747474'}
        self.cus_order = StringVar(value="")
        self.tax_bool = BooleanVar(value=False)
        self.tax_num = StringVar(value="")
        self.is_tax = StringVar(value="")
        self.tax_branch = StringVar(value="")
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
        self.cus_ship_cost = DoubleVar(value=0)
        self.cus_seller_voucher = DoubleVar(value=0)
        self.cus_purchase_time = StringVar(value="")
        self.cus_arrow_btn = '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[2]'
        self.cusNameInput = '/html/body/span/span/span[1]/input'
        self.cusSearchSMCO = '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[7]/a'
        self.cusCreateBtn = '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[1]/div[2]/button[1]'
        self.cusNameLi1 = '/html/body/span/span/span[2]/ul/li'
        self.cus_name_ul = '/html/body/span/span/span[2]/ul'
        # self.bot_state = BooleanVar(value=False)
        self.bot = Bot_POS(self.root, self)
        self.create_main_window()
        self.get_dataframe()

    def validate_input(self, value):
        pattern = r'[A-z]'
        if re.fullmatch(pattern, value) is None:
            return False

        return True

    def on_canvas_configure(self, event):
        self.canvas_width = event.width
        self.canvas_height = event.height
        self.root_frame.config(width=self.canvas_width,
                               height=self.canvas_height)

    def create_main_window(self):
        self.root.geometry("1000x900+400+300")
        self.root.title("Autosamatic ver0.38")
        self.root.configure(bg="#444")

        # #* BG CANVAS ##################################################################################
        self.canvas = Canvas(self.root, bg="#444")

        # * Scrollbar For Root ##################################################################################
        self.root_scrollbar_y = Scrollbar(
            self.canvas, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.root_scrollbar_y.set)
        self.root_scrollbar_y.pack(side=RIGHT, fill="y")

        self.root_scrollbar_x = Scrollbar(
            self.root, command=self.canvas.xview, orient='horizontal')
        self.root_scrollbar_x.pack(side=BOTTOM, fill="x")

        self.canvas.config(xscrollcommand=self.root_scrollbar_x.set)
        self.canvas.configure(xscrollcommand=self.root_scrollbar_x.set)
        self.canvas.pack(side="left", fill="both", expand=True)

        # #* FRAMES #####################################################################################################
        # self.root_frame = Frame(self.canvas,  bg="pink") ใช้ได้แต่รอก่อน
        # self.canvas.create_window((0, 0), window=self.root_frame, anchor="nw") ใช้ได้แต่รอก่อน

        # > Frame1 Order Entry
        self.entry_frame = Frame(self.canvas, padx=5, pady=5, bg="#444",
                                 borderwidth=1, relief="groove", highlightbackground="#ccc")
        self.entry_frame.pack(side='top', pady=(10, 10))

        # > Frame2 Log Frame
        self.log_frame = Frame(self.canvas, bg="#444")
        self.log_frame.pack(side='bottom', pady=(0, 30))

        # > Frame3 ImportFile Status and Bot Status
        self.import_file_frame = Frame(self.canvas, bg="#444")
        self.import_file_frame.pack(
            side='top', anchor=W, padx=(5, 5), pady=(5, 0))

        # > Frame4 Customer Details
        self.order_details_frame = Frame(self.canvas, bg="#444", )
        self.order_details_frame.pack(
            side='top', anchor=W, padx=(5, 5), pady=(5, 0))

        # > Frame7 For Customer's Invoice Details
        self.invoice_details_frame = Frame(self.canvas, bg="#445")
        self.invoice_details_frame.pack(
            side='top', anchor=W, padx=(5, 5), pady=(5, 0))

        # > Frame5 Products Lists
        self.products_list_frame = Frame(self.canvas, bg="#445")
        self.products_list_frame.pack(
            side='top', padx=(5, 5), pady=(5, 5), fill=X)

        # > Frame6 Margetplace(MP) Products Lists
        self.mp_products_list_frame = Frame(self.canvas, bg="#444")
        self.mp_products_list_frame.pack(side='top',  padx=(
            5, 5), pady=(5, 5), fill="x")

        # Create widgets in the main window
        self.create_widgets()

        # start the scrollbar
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.canvas.bind_all("<MouseWheel>", lambda event: self.canvas.yview_scroll(
            int(-1*(event.delta/120)), "units"))
        # self.canvas.bind("<Configure>", self.on_canvas_configure) ใช้ได้แต่รอก่อน

    def measure_text(self, text):
        return font.Font().measure(str(text).strip())

    def row_header_maker(self, list_of_cols):

        # สร้าง header
        self.list_of_cols = list_of_cols
        self.colspan_amount = [1, 19, 2, 2, 2, 2]
        self.cols_location = [0, 1, 21, 23, 25, 27]
        self.cols_width = [5, 112, 10, 10, 10, 10]
        # self.cols_width = [1, 22, 2, 2, 2, 2]
        self.entry_list = []
        i = 0
        for header in self.list_of_cols:
            self.mp_products_header = Entry(
                self.mp_products_list_frame, foreground="#000000", background="#fff", width=int(self.cols_width[i]))
            self.mp_products_header.insert(0, header)
            self.entry_list.append(self.mp_products_header)
            i += 1

        for idx, entry in enumerate(self.entry_list):
            entry.grid(
                row=0, column=self.cols_location[idx], columnspan=self.colspan_amount[idx], sticky='nsew')
            entry.configure(state="readonly")

    def create_widgets(self):
        # * > MarketPlace
        # >> Label
        self.marketplace_label = Label(
            self.entry_frame, textvariable=self.marketplace_target, bg="#747474", fg="#FFF", font='bazooka 10 bold')
        self.marketplace_label.grid(row=0, column=0, padx=5)

        # * > search order component
        # >> Labels
        self.inp1_label_order = Label(
            self.entry_frame, text="Order: ", bg="#FFF", width=10)
        self.inp1_label_order.grid(row=0, column=1, padx=5)
        # >> Inputs
        self.entered_order = StringVar()
        self.inp1_order_input = Entry(
            self.entry_frame, textvariable=self.entered_order, width=50)
        self.inp1_order_input.grid(row=0, column=3)
        # >> Buttons
        self.inp1_search_btn = Button(
            self.entry_frame, text="Start", bg="#747474", command=self.search, width=10)
        self.inp1_search_btn.grid(row=0, column=5, padx=5)

        # * > A BTN to display the User_account
        self.btn_display = f"ID:{self.user_id.get()}" if self.user_id.get(
        ) and self.user_pw.get() else "Login"
        self.display_acc_btn = Button(
            self.entry_frame, text=self.btn_display, command=lambda: UserAccount(self.root, self))
        self.display_acc_btn.grid(row=0, column=6, padx=5)

        # * > Export File and Bot status location display component
        self.display_location_label = Label(
            self.import_file_frame, text=f"File located: ")
        self.display_location_label.grid(row=0, column=0, padx=(5, 0))
        self.display_location_result = Label(
            self.import_file_frame, text=f"ยังไม่เลือก Import File")
        self.display_location_result.grid(row=0, column=1, padx=(5, 0))
        self.display_location_result_btn = Button(
            self.import_file_frame, text=f"ใส่ Import File", command=self.select_excel)
        self.display_location_result_btn.grid(row=0, column=2, padx=(5, 0))
        # >> bot status
        self.display_bot_status_label = Label(
            self.import_file_frame, text=f"Bot Status: ไม่มีการทำงาน (⸝⸝ᴗ﹏ᴗ⸝⸝) ᶻ 𝗓 𐰁", bg="#1f242e", fg="#ffec1f")
        self.display_bot_status_label.grid(row=0, column=3, padx=(5, 0))

        # * > Current Order display component
        # >> Labels
        self.label_current_order = Label(
            self.order_details_frame, text="Current Order: ", bg="#FFF",)
        self.label_current_order.grid(row=1, column=0, padx=(5, 0))
        self.display_current_order = Entry(
            self.order_details_frame, width=40, state="readonly",  borderwidth=0, textvariable=self.cus_order)
        self.display_current_order.grid(row=1, column=1, padx=(1, 0), sticky=W)

        # * > Current Status display component
        # >> Labels
        self.label_current_status = Label(
            self.order_details_frame, text="Status: ", bg="#FFF",)
        self.label_current_status.grid(
            row=1, column=2, padx=(5, 0), columnspan=1)
        self.display_current_status = Label(
            self.order_details_frame, width=20,  borderwidth=0, textvariable=self.cus_cur_status, fg="#000000", bg="#8fd4ff")

        self.display_current_status.grid(
            row=1, column=3, padx=(1, 0), sticky=W)

        # * > Is Tax?? display component
        # >> Labels
        self.label_is_tax = Label(
            self.order_details_frame, text="ใบกำกับ: ", bg="#FFF")
        self.label_is_tax.grid(row=2, column=2, padx=(5, 0), sticky='ew')
        # >> Value display
        self.display_is_tax = Label(
            self.order_details_frame,  borderwidth=0, textvariable=self.is_tax, foreground="#000000", background="#fff")
        self.display_is_tax.grid(row=2, column=3, padx=(1, 0), sticky='ew')

        # * > Tax Number display component
        # >> Labels
        self.label_tax_number = Label(
            self.order_details_frame, text="เลขใบกำกับ: ", bg="#FFF")
        self.label_tax_number.grid(row=2, column=4, padx=(5, 0), sticky='ew')
        # >> Value display
        self.display_tax_number = Entry(
            self.order_details_frame, width=15,  borderwidth=0, textvariable=self.tax_num, foreground="#000000", background="#fff", readonlybackground="white", state="readonly")
        self.display_tax_number.grid(row=2, column=5, padx=(1, 0), sticky='ew')

        # * > Customer Name display component
        # >> Labels
        self.label_cus_name = Label(
            self.order_details_frame, text="ชื่อ: ", bg="#FFF", height=1)
        self.label_cus_name.grid(row=2, column=0, padx=(
            5, 0), pady=(2, 2), sticky='ew')
        # >> Value display
        self.display_cus_name = Entry(
            self.order_details_frame, width=40,  borderwidth=0, textvariable=self.cus_name, foreground="#000000", background="#fff", state="readonly")
        self.display_cus_name.grid(row=2, column=1, padx=(1, 0), sticky='ew')

        # * > Customer Address display component ส่วนแสดงผลที่อยู่ลูกค้า
        # * >>Address
        # >>> Labels
        self.label_cus_address = Label(
            self.invoice_details_frame, text="ที่อยู่: ", bg="#FFF", height=1,)
        self.label_cus_address.grid(
            row=3, column=0, padx=(5, 0), pady=(2, 2), sticky="nsew")
        # >>> Value display
        self.display_cus_address = Text(
            self.invoice_details_frame, width=44, height=5, borderwidth=0, foreground="#000000", background="#fff", state="disabled")
        self.display_cus_address.grid(
            row=3, column=1, padx=(1, 0), columnspan=2, sticky=W)
        self.display_cus_address.tag_add("left", "1.0", "1.end")

        # * >> Customer remark display component ส่วนแสดงผลหมายเหตุลูกค้า col 4-5
        # >>> Labels
        self.label_cus_remark = Label(
            self.invoice_details_frame, text="หมายเหตุจากผู้ซื้อ: ", bg="#FFF", height=1,)
        self.label_cus_remark.grid(row=3, column=4, padx=(
            5, 0), pady=(2, 2), sticky="nsew")
        # >>> Value display
        self.display_cus_remark = Text(
            self.invoice_details_frame, width=20, height=5, borderwidth=0, foreground="#000000", background="#fff", state="disabled")
        self.display_cus_remark.grid(
            row=3, column=5, padx=(1, 0), columnspan=1, sticky=W)
        self.display_cus_remark.tag_add("left", "1.0", "1.end")

        # * >> Order Note display component ส่วนแสดงผลหมายเหตุลูกค้า col 6-7
        # >>> Labels
        self.label_order_note = Label(
            self.invoice_details_frame, text="บันทึก: ", bg="#FFF", height=1,)
        self.label_order_note.grid(row=3, column=6, padx=(
            5, 0), pady=(2, 2), sticky="nsew")
        # >>> Value display
        self.display_order_note = Text(
            self.invoice_details_frame, width=20, height=5, borderwidth=0, foreground="#000000", background="#fff", state="disabled")
        self.display_order_note.grid(
            row=3, column=7, padx=(1, 0), columnspan=1, sticky=W)
        self.display_order_note.tag_add("left", "1.0", "1.end")

        # * > Customter Products List
        self.label_cus_products = Label(
            self.products_list_frame, text="รายการสินค้า: ", bg="#FFF", height=1)
        self.label_cus_products.pack()

        # * >> สร้าง Treeview widget
        self.tree = ttk.Treeview(self.products_list_frame, columns=(
            "Productname", "Price", "QTY"), show="headings")
        self.tree.column("Productname", anchor=W, width=350)
        self.tree.column("Price", width=self.measure_text("Price")+10)
        self.tree.column("QTY", width=self.measure_text("QTY")+10)
        self.tree.heading("Productname", text="Product")
        self.tree.heading("Price", text="Price")
        self.tree.heading("QTY", text="QTY")

        self.y_scrollbar = ttk.Scrollbar(
            self.products_list_frame, command=self.tree.yview)

        self.y_scrollbar.pack(side="right", fill="y")
        self.tree.pack(side='bottom', fill=X)
        self.tree.config(yscrollcommand=self.y_scrollbar.set)

        # * > Margetplace Products display Header
        headers = ['No.', 'สินค้าทั้งหมด', 'ราคาต่อชิ้น',
                   'จำนวน', 'ราคาขายสุทธิ', 'ราคารวมรีเบท']
        self.row_header_maker(headers)

        # * > Log windows component
        self.report_log = Text(self.log_frame, state=DISABLED, height=13)

        self.scrollbar = Scrollbar(
            self.log_frame, command=self.report_log.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.report_log.pack(side='bottom', fill=X)
        self.report_log.config(yscrollcommand=self.scrollbar.set)

        ## * Create DataSourceSelector instance ###########

        self.data_source_selector = DataSourceSelector(self.root, self)
        self.user_account = UserAccount(self.root, self)

    def reset_all_display(self):
        self.result = ""
        self.table_location = ""
        self.cus_order.set("")
        self.tax_bool.set(False)
        self.tax_num.set("")
        self.is_tax.set("")
        self.cus_name.set("")
        self.cus_address = ""
        self.cus_remark = ""
        self.order_note = ""
        self.update_gui_address('')
        self.cus_province.set("")
        self.cus_district.set("")
        self.cus_sub_district.set("")
        self.cus_tel.set("")
        self.cus_cur_status.set("")
        self.cus_account_name.set("")
        self.display_is_tax.config(
            background="#FFF", foreground="#000", font='Chiller 10 normal')
        for i in self.tree.get_children():
            self.tree.delete(i)

    def update_log(self, update_txt):
        self.update_txt = update_txt
        self.report_log.config(state=NORMAL)
        self.report_log.insert(END, self.update_txt + "\n")
        self.report_log.config(state=DISABLED)

    def update_mp_frame(self, data_list):
        data_list
        self.report_log.config(state=NORMAL)
        self.report_log.insert(END, self.update_txt + "\n")
        self.report_log.config(state=DISABLED)

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
        self.table_location = filedialog.askopenfilename()
        self.display_location_result.config(
            text=f"{self.table_location.split('/')[-1]}")

        # target should come before get dataframe
        self.marketplace_target.set(self.define_marketplace())
        result = self.marketplace_target.get()
        print("ต้องตีเว็บไหน", result)
        # self.canvas.config(bg=f'{self.bg_by_market_place[self.marketplace_target.get()}')
        self.entry_frame.config(
            bg=f'{self.bg_by_market_place[str(result)]}')
        self.marketplace_label.config(
            bg=f'{self.bg_by_market_place[str(result)]}')
        # self.import_file_frame.config(
        #     bg=f'{self.bg_by_market_place[self.marketplace_target.get()]}')

        self.get_data_frame()
        print("Table Location:", self.table_location)
        self.update_log("แอดไฟล์")

        #! WIP กำลังทำ ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def group_by_order(self, file_input, dtype):
        print(f"รับ df เข้ามา df หน้าตาเป็นแบบ: {file_input} ")
        df = pd.read_excel(file_input, dtype=dtype)

        # เพิ่มส่วนที่ไม่มี และหาไม่ได้
        df['ส่วนลดจาก Shopee'], df['ประเภทใบกำกับภาษี'], df['อีเมลสำหรับรับใบกำกับภาษี'], df[
            'โค้ดส่วนลดชำระโดย Shopee'], df['ประเภทสาขา'], df['หมายเหตุจากผู้ซื้อ'], df['บันทึก'] = 0.00, "", "", 0, "", "", ""
        # กำหนด Datatype
        data_types = {'orderNumber': str, 'ส่วนลดจาก Shopee': float, 'ประเภทใบกำกับภาษี': str, 'อีเมลสำหรับรับใบกำกับภาษี': str,
                      'โค้ดส่วนลดชำระโดย Shopee': float, 'ประเภทสาขา': str, 'หมายเหตุจากผู้ซื้อ': str, 'บันทึก': str, 'paidPrice': float, 'variation': str, 'taxCode': str, 'billingAddr': str, 'createTime': str, 'branchNumber': str, 'billingAddr2': str}
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
            print("ทำไมคืนค่า0: ", column_type[column])
            if column_type[column] == 'float':
                df[column] = df[column].replace(np.nan, 0)
            elif column_type[column] == 'object':
                df[column] = df[column].replace('nan', '')
            elif column_type[column] == 'str':
                df[column] = df[column].replace('nan', '')
            else:
                df.fillna(value=0, inplace=True)

        # เพิ่มส่วนที่ไม่มี แต่สามารถหาคำนวณเพิ่มเองได้
        result_count = df.groupby(['orderNumber', 'sellerSku', 'itemName',
                                  'unitPrice', 'variation']).size().reset_index(name='จำนวน')

        # total_variation_df = df.groupby('orderNumber')['variation'].agg().reset_index(name='ชื่อตัวเลือก')
        # result_count = pd.merge(
        #     result_count, total_variation_df, on='orderNumber', how='left')

        result_with_additional_columns_df = df.groupby('orderNumber').agg({
            'status': 'first',
            'ส่วนลดจาก Shopee': 'first',
            'ประเภทใบกำกับภาษี': 'first',
            'อีเมลสำหรับรับใบกำกับภาษี': 'first',
            'โค้ดส่วนลดชำระโดย Shopee': 'first',
            'ประเภทสาขา': 'first',
            'หมายเหตุจากผู้ซื้อ': 'first',
            'บันทึก': 'first',
            'billingName': 'first', 'billingAddr': 'first', 'billingAddr2': 'first', 'billingAddr4': 'first', 'billingAddr3': 'first', 'billingAddr5': 'first', 'taxCode': 'first', 'billingPhone': 'first', 'customerName': 'first', 'paidPrice': 'sum', 'createTime': 'first', 'branchNumber': 'first'
        })
        result_with_additional_columns_df = result_with_additional_columns_df.astype(
            {'billingAddr5': str, 'taxCode': str, 'billingPhone': str})

        # เก็บไว้ก่อน['billingName', 'billingAddr', 'billingAddr2', 'billingAddr4', 'billingAddr3', 'billingAddr5', 'taxCode', 'billingPhone', 'customerName', 'paidPrice', 'createTime', 'branchNumber']
        # สร้าง sum_column  ขึ้นมาใหม่
        # > 'ราคาขายสุทธิ'
        total_per_order_df = df.groupby('orderNumber')[
            'unitPrice'].sum().reset_index(name='ราคาขายสุทธิ')

        # > 'โค้ดส่วนลดชำระโดยผู้ขาย'
        total_sellerDiscountTotal_df = df.groupby('orderNumber')[
            'sellerDiscountTotal'].sum().reset_index(name='โค้ดส่วนลดชำระโดยผู้ขาย')
        total_sellerDiscountTotal_df['โค้ดส่วนลดชำระโดยผู้ขาย'] *= -1

        # > 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ'
        total_shippingfee_df = df.groupby('orderNumber')['shippingFee'].sum(
        ).reset_index(name='ค่าจัดส่งที่ชำระโดยผู้ซื้อ')

        merge1 = pd.merge(result_count, total_per_order_df,
                          on='orderNumber', how='left')
        merge2 = pd.merge(merge1, total_sellerDiscountTotal_df,
                          on='orderNumber', how='left')
        merge3 = pd.merge(
            merge2, result_with_additional_columns_df, on='orderNumber', how='left')
        result = pd.merge(merge3, total_shippingfee_df,
                          on='orderNumber', how='left')
        # result = pd.concat([result_count, total_per_order_df,
        #                    total_sellerDiscountTotal_df, total_shippingfee_df], ignore_index=True)

        # เราต้องการ column ที่มีชื่อต่างกัน แต่ข้อมูลเหมือนกัน เลยต้อง copy เพิ่ม
        result['รายละเอียดที่อยู่'] = result['billingAddr'].copy()

        # ตรวจสอบผลลัพธ์
        print(f"""qty ใน lazada""")
        print(result_count)

        print("ราคาขายสุทธิ")
        print(total_per_order_df)

        # เปลี่ยนชื่อ column
        result.rename(columns={'orderNumber': 'หมายเลขคำสั่งซื้อ',
                               'sellerSku': 'เลขอ้างอิง SKU (SKU Reference No.)', 'itemName': 'ชื่อสินค้า', 'unitPrice': 'ราคาขาย',  'status': 'สถานะการสั่งซื้อ', 'billingName': 'ชื่อ', 'billingAddr': 'ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป', 'billingAddr2': 'แขวง/ตำบล', 'billingAddr4': 'เขต/อำเภอ.1', 'billingAddr3': 'จังหวัด.1', 'billingAddr5': 'รหัสไปรษณีย์.1', 'taxCode': 'หมายเลขประจำตัวผู้เสียภาษี', 'billingPhone': 'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี', 'customerName': 'ชื่อผู้ใช้ (ผู้ซื้อ)', 'paidPrice': 'จำนวนเงินทั้งหมด', 'createTime': 'วันที่ทำการสั่งซื้อ', 'branchNumber': 'รหัสประจำสาขา', 'variation': 'ชื่อตัวเลือก'}, inplace=True)
        result['หมายเลขคำสั่งซื้อ'] = result['หมายเลขคำสั่งซื้อ'].astype(str)
        print("ตารางใหม่")
        print(result)
        excel_file_path = "output_test.xlsx"
        result.to_excel(excel_file_path, index=False)
        return result

    def f(self, d):
        return '{0:n}'.format(d)

    def get_data_frame(self):
        print("มีป่าวหว่า", self.table_location)
        self.file_path = self.table_location
        print('self.marketplace_target.get()', self.marketplace_target.get())
        shopee = {'หมายเลขประจำตัวผู้เสียภาษี': str, 'รหัสไปรษณีย์.1': str, 'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี': str, 'จำนวน': int, 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ': float, 'โค้ดส่วนลดชำระโดยผู้ขาย': float, 'แขวง/ตำบล': str, 'ประเภทสาขา': str,
                  'สาขาย่อย': str, 'รหัสประจำสาขา': str, 'หมายเหตุจากผู้ซื้อ': str, 'บันทึก': str}
        lazada = {'หมายเลขประจำตัวผู้เสียภาษี': str, 'รหัสไปรษณีย์.1': str, 'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี': str, 'จำนวน': int, 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ': float, 'โค้ดส่วนลดชำระโดยผู้ขาย': float, 'แขวง/ตำบล': str, 'ประเภทสาขา': str,
                  'สาขาย่อย': str, 'รหัสประจำสาขา': str, 'หมายเหตุจากผู้ซื้อ': str, 'บันทึก': str}
        self.columns = shopee if self.marketplace_target.get(
        ) == 'SHOPEE' else lazada if self.marketplace_target.get() == 'LAZADA' else ''
        try:
            if self.marketplace_target.get() == 'SHOPEE':
                print("เปลี่ยน dtype เป็น form shopee")
                self.data_frame = pd.read_excel(
                    self.file_path, dtype=self.columns)
                self.data_frame['หมายเลขประจำตัวผู้เสียภาษี'].astype(str)
            elif self.marketplace_target.get() == 'LAZADA':
                self.data_frame = self.group_by_order(
                    self.file_path, self.columns)

            print("df มี type เป็นไร", type(self.data_frame))
            print("self.data_frame หน้าตาเปนไง: ", self.data_frame)
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

    def update_gui_address(self, address):
        self.address = address.strip()
        if address != "":
            self.cus_address = self.address
            self.display_cus_address.config(state=NORMAL)
            self.display_cus_address.delete(1.0, END)
            self.display_cus_address.insert(END, self.address)
            self.display_cus_address.config(state=DISABLED)
        else:
            self.cus_address = "-"
            self.display_cus_address.config(state=NORMAL)
            self.display_cus_address.delete(1.0, END)
            self.display_cus_address.insert(END, '')
            self.display_cus_address.config(state=DISABLED)

    def update_gui_remark(self):
        if self.cus_remark == "" or self.cus_remark == "nan":
            self.display_cus_remark.config(state=NORMAL)
            self.display_cus_remark.delete(1.0, END)
            self.display_cus_remark.insert(END, 'ไม่มี')
            self.display_cus_remark.config(state=DISABLED)

        else:
            self.display_cus_remark.config(state=NORMAL)
            self.display_cus_remark.delete(1.0, END)
            self.display_cus_remark.insert(END, self.cus_remark)
            self.display_cus_remark.config(state=DISABLED)

    def update_gui_note(self):
        if self.order_note == "" or self.order_note == "nan":
            self.display_order_note.config(state=NORMAL)
            self.display_order_note.delete(1.0, END)
            self.display_order_note.insert(END, 'ไม่มี')
            self.display_order_note.config(state=DISABLED)

        else:
            self.display_order_note.config(state=NORMAL)
            self.display_order_note.delete(1.0, END)
            self.display_order_note.insert(END, self.order_note)
            self.display_order_note.config(state=DISABLED)

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

        # Shopee + ค่าขนส่ง แต่ Lazada ไม่ต้อง + ค่าขนส่งในบางกรณี
        if self.marketplace_target.get() == 'SHOPEE':
            self.total_price += self.cus_ship_cost.get()
            self.phase1_sum_price = self.total_price
            self.tree.insert("", "end", value=(
                "ค่าขนส่ง", self.f(self.cus_ship_cost.get()), 1))
            self.total_price -= self.cus_seller_voucher.get()
            self.tree.insert("", "end", value=(
                "Seller Voucher",  "-"+self.f(self.cus_seller_voucher.get()), 1))

            self.tree.insert("", "end", values=(
                "ราคาที่ต้องออก", self.f(self.total_price)))

            self.tree.insert("", "end", values=("Shopee Voucher",
                                                self.f(self.nondistortedData['โค้ดส่วนลดชำระโดย Shopee']*-1)))

            self.tree.insert("", "end", values=("ลูกค้าจ่ายทั้งหมด",
                                                self.f(self.nondistortedData['จำนวนเงินทั้งหมด'])))

        elif self.marketplace_target.get() == 'LAZADA':
            # * มันต้องมีทั้ง ราคาที่ต้องออกแบบ +ขนส่งกับ ไม่มีขนส่ง
            self.total_price -= self.cus_seller_voucher.get()
            self.tree.insert("", "end", value=(
                "Seller Voucher",  "-"+self.f(self.cus_seller_voucher.get()), 1))
            # > แบบไม่มีขนส่ง
            self.total_price_no_ship_cost = self.total_price
            self.tree.insert("", "end", values=(
                "ราคาที่ต้องออก(Noขนส่ง)", self.f(self.total_price_no_ship_cost)))

            # > แบบมีขนส่ง
            self.total_price_with_ship = self.total_price + self.cus_ship_cost.get()
            self.tree.insert("", "end", value=(
                "ค่าขนส่ง", self.f(self.cus_ship_cost.get()), 1))
            self.tree.insert("", "end", values=(
                "ราคาที่ต้องออก(+ขนส่ง)", self.f(self.total_price_with_ship)))

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

        print(truncated_address.strip())
        return truncated_address.strip()

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
            is_abbreviation = any(part.startswith(keyword)
                                  for keyword in ["ต.", "อ.", "จ."])

            if not is_abbreviation:
                cleaned_parts.append(part)

        # นำคำที่ไม่ใช่คำย่อมาเชื่อมกลับเป็นสตริงใหม่
        cleaned_address = ' '.join(cleaned_parts)

        # ลบคำที่มีส่วนที่เหมือนกันออก
        cleaned_address = self.clean_duplicate_parts(cleaned_address)

        # แก้ไขเครื่องหมายช่องว่างที่เหลือหลังการลบคำ
        cleaned_address = cleaned_address.replace("  ", " ")

        return cleaned_address

    def note_extractor(self):
        if self.order_note != 'nan':
            self.name_match = re.search(r'ชื่อ:(.*?)\n', self.order_note)
            self.branch_match = re.search(r'สาขา:(.*?)\n', self.order_note)
            self.address_match = re.search(r'ที่อยู่:(.*?)\n', self.order_note)
            self.tax_id_match = re.search(r'Tax id:(.*?)', self.order_note)
            print("regexบันทึก: ", self.name_match)
            print("ใช้ group กับ regexบันทึก: ", self.name_match.group(1))
        else:
            print("ไม่มีค่า")

    def translator(self, text):
        # ตรวจสอบว่าชื่อไม่ใช่ภาษาไทย, อังกฤษ, หรือตัวเลข
        pattern = re.compile(r'^[a-zA-Z0-9ก-๙\s\W]+$')
        is_usable = bool(re.match(pattern, text))
        if is_usable:
            return text
        else:
            translator = Translator()
            lang_src = translator.detect(text).lang
            print("Whare are you from: ", lang_src)
            translation = translator.translate(text, src=lang_src, dest='en')
            print("Translated name", translation.text)
            return translation.text

    def cus_tel_fixer(self, tel):
        b_no_code = tel[2:]
        print("เบอร์มีขนาดความยาว: ", len(tel))
        if len(tel) == 10:
            return tel
        elif len(tel) == 9:
            print("ดูก่อนว่าเบอร์บ้านไหม")
        else:
            if b_no_code[0] != "0":
                b_no_code_fixed = "0"+b_no_code
                print("แบบตัดรหัสประเทศและเพิ่มเลข0", b_no_code_fixed)
                return b_no_code_fixed
            else:
                print("แบบตัดรหัสประเทศ", b_no_code)
                return b_no_code

    def find_branch(self, input):
        # ตัวแปร branch
        input = re.sub(r'\s+', '', input)
        branch = str(input).strip()

        pattern = re.compile(r"สำนักงานใหญ่|ใหญ่|สนงใหญ่|สนง\.ใหญ่|สนง|^0+$")
        match = pattern.findall(branch)
        # ตรวจสอบค่าของตัวแปร branch
        if match:
            # print("ค่าของตัวแปร branch เป็น 'สำนักงานใหญ่' เลขสาขาเป็น 00000")
            print("return ค่า 'สำนักงานใหญ่'")
            return 'สำนักงานใหญ่'
        elif re.match(r'^[0-9]+$', branch):
            if len(branch) > 5:
                print("Branch: ", branch[-5:])
                return branch[-5:]
            else:
                txt = "{:0>5}"
                print("Branch: ", txt.format(branch))
                return txt.format(branch)
        else:
            print("Branch not found return as Headoffice")
            return 'สำนักงานใหญ่'

    def order_search(self, order,  on_complete):
        print("order_search ทำงาน")
        self.on_complete = on_complete
        self.order = order.strip()
        self.cus_order.set(order)
        differential_col_data = [
            'เลขอ้างอิง SKU (SKU Reference No.)', 'ชื่อสินค้า', 'ราคาขาย', 'จำนวน', 'ราคาขายสุทธิ', 'ส่วนลดจาก Shopee', 'ชื่อตัวเลือก']
        non_differential_col_data = ['หมายเลขคำสั่งซื้อ', 'สถานะการสั่งซื้อ', 'โค้ดส่วนลดชำระโดยผู้ขาย', 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ',  'ประเภทใบกำกับภาษี', 'ชื่อ',
                                     'ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป', 'แขวง/ตำบล', 'เขต/อำเภอ.1', 'จังหวัด.1', 'รหัสไปรษณีย์.1', 'หมายเลขประจำตัวผู้เสียภาษี', 'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี', 'อีเมลสำหรับรับใบกำกับภาษี', 'ชื่อผู้ใช้ (ผู้ซื้อ)', 'จำนวนเงินทั้งหมด', 'วันที่ทำการสั่งซื้อ', 'โค้ดส่วนลดชำระโดย Shopee', 'รายละเอียดที่อยู่', 'ประเภทสาขา',
                                     'รหัสประจำสาขา', 'หมายเหตุจากผู้ซื้อ', 'บันทึก']

        if self.order != "":
            print("self.order err?: ", self.order, type(self.order))
            if not self.data_frame[(self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order)].empty:
                # ? self.filter_data จะเป็นการทำComparisionให้เรียบร้อยแล้วคืน DataFrame ที่กรองแล้วทันที --------------------ไวกว่า
                self.filter_data = self.data_frame[(
                    self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order)]
                # ? self.target_row เป็น การหา เอาคอล "หมายเลขคำสั่งซื้อ" ทั้งหมดมาตรวจแล้วคืนค่าเป็น Boolean เท่านั้น ---------ช้ากว่า
                self.target_row = self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order
                # print(
                #     "err?: ", self.data_frame[self.target_row]['สถานะการสั่งซื้อ'])
                self.order_status = self.data_frame[self.target_row]['สถานะการสั่งซื้อ'].iloc[0]

                # *  ของมีอะไรบ้าง
                print("ของมีไรบ้าง: ", self.data_frame['ชื่อตัวเลือก'])
                print("ของมีไรบ้าง: ", self.data_frame['ราคาขายสุทธิ'])
                print("ของมีไรบ้าง: ", self.data_frame['ส่วนลดจาก Shopee'])
                self.items = self.data_frame[differential_col_data][self.target_row].to_dict(
                    'records')
                self.nondistortedData = self.data_frame[self.target_row][non_differential_col_data].iloc[0].to_dict(
                )

                self.update_log(f"สินค้าที่มี")

                for row in self.items:
                    print("ตัวเลือก", str(row['ชื่อตัวเลือก']))
                    self.update_log(
                        f"SKU: {str(row['เลขอ้างอิง SKU (SKU Reference No.)'])} ชื่อสินค้า: {str(row['ชื่อสินค้า'])} ")
                    # if str(row['ชื่อตัวเลือก']) != "nan"
                    self.update_log(
                        f"ราคาขาย: {float(row['ราคาขาย'])} จำนวน: {int(row['จำนวน'])} ราคาขายสุทธิ: {float(row['ราคาขายสุทธิ'])} ส่วนลดจาก Shopee: {float(row['ส่วนลดจาก Shopee'])}")
                self.widget_no_col_lst = []
                self.widget_product_col_lst = []
                self.widget_prc_unit_lst = []
                self.widget_qty_lst = []
                self.widget_total_prc_lst = []
                self.widget_total_rebt_prc_lst = []
                self.all_cols = [self.widget_no_col_lst, self.widget_product_col_lst, self.widget_prc_unit_lst,
                                 self.widget_qty_lst, self.widget_total_prc_lst, self.widget_total_rebt_prc_lst]
                self.idx = 0
                for row in self.items:

                    self.no_col_value = Entry(
                        self.mp_products_list_frame, width=int(self.cols_width[0]))
                    self.no_col_value.insert(0, self.idx+1)
                    self.widget_no_col_lst.append(self.no_col_value)
                    self.idx += 1

                    self.product_col_name_value = Entry(
                        self.mp_products_list_frame, width=int(self.cols_width[1]))
                    self.product_col_name_value.insert(
                        0, f"{str(row['เลขอ้างอิง SKU (SKU Reference No.)'])} : {str(row['ชื่อสินค้า'])}")
                    self.widget_product_col_lst.append(
                        self.product_col_name_value)

                    self.price_unit_col_value = Entry(
                        self.mp_products_list_frame, width=int(self.cols_width[2]))
                    self.price_unit_col_value.insert(0, float(row['ราคาขาย']))
                    self.widget_prc_unit_lst.append(self.price_unit_col_value)

                    self.qty_col_value = Entry(
                        self.mp_products_list_frame, width=int(self.cols_width[3]))
                    self.qty_col_value.insert(0, int(row['จำนวน']))
                    self.widget_qty_lst.append(self.qty_col_value)

                    self.total_price_col_value = Entry(
                        self.mp_products_list_frame, width=int(self.cols_width[4]))
                    self.total_price_col_value.insert(
                        0, float(row['ราคาขายสุทธิ']))
                    self.widget_total_prc_lst.append(
                        self.total_price_col_value)

                    self.total_rebate_price_col_value = Entry(
                        self.mp_products_list_frame, width=int(self.cols_width[5]))
                    self.total_rebate_price_col_value.insert(
                        0, float(row['ราคาขายสุทธิ'])+float(row['ส่วนลดจาก Shopee']))
                    self.widget_total_rebt_prc_lst.append(
                        self.total_rebate_price_col_value)
                print("none ได้ไง:", self.widget_no_col_lst)
                print("ไม่สามารถ grid: ", self.all_cols)
                for colidx, col_list in enumerate(self.all_cols):
                    for idxrow, col in enumerate(col_list):
                        col.grid(
                            row=idxrow+1, column=self.cols_location[colidx], columnspan=self.colspan_amount[colidx])
                        col.configure(state="readonly")

                # self.row_header_maker(self.items)
                # * ชื่อที่ต้องอกใบกำกับ
                self.cus_name.set(self.translator(re.sub(
                    r'\s{2,}', " ", self.nondistortedData['ชื่อ'].strip().replace('\u200b', ''))))
                # * ปรับคำบอกประเภทการจดทะเบียนของใบกำกับ
                self.cus_name.set(
                    self.tax_name_standarizer(self.cus_name.get()))

                # * ประเภทใบกำกับภาษี
                # * เราดูว่าขอใบกำกับหรือไม่ จากที่ว่า 1)มีเลขผู้เสียภาษี 2)มี branch_type
                # * เลือก Column และ row ที่เฉพาะเจาะจง มาแสดงผล โดยการใช้ ['ชื่อคอลั่ม'].iloc[0]
                self.branch_type = str(self.nondistortedData['ประเภทสาขา'])
                print("รหัสประจำสาขา= ",
                      self.data_frame[self.target_row]['รหัสประจำสาขา'].iloc[0])
                branch = self.find_branch(
                    str(self.nondistortedData['รหัสประจำสาขา']))
                self.tax_branch.set(branch)

                print("self.nondistortedData['หมายเลขประจำตัวผู้เสียภาษี'] พัง",
                      bool(pd.isna(self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0])), pd.isna(self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0]))

                # ถ้า col หมายเลขประจำตัวผู้เสียภาษี ไม่ใช่ nan จะเก็บค่าลงใน tax_num_only
                if not pd.isna(self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0]):
                    tax_num_only = re.sub(
                        r'\D', '', str(self.nondistortedData['หมายเลขประจำตัวผู้เสียภาษี']))
                else:
                    tax_num_only = ""

                if pd.isna(self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0]) or tax_num_only == "":
                    self.tax_bool.set(False)
                    self.is_tax.set("ไม่ขอใบกำกับ")
                    self.display_is_tax.config(
                        background="#6ec7ff", foreground="#000", font='Chiller 10 normal')
                    self.tax_num.set("ไม่มี")
                elif tax_num_only != "" and len(tax_num_only) != 13:
                    self.tax_bool.set(False)
                    self.is_tax.set("ขอ//เลขไม่ครบ")
                    self.display_is_tax.config(
                        background="#8502d1", foreground="#FFF", font='Chiller 10 normal')
                    self.tax_num.set("ไม่มี")

                else:

                    if "สำนักงานใหญ่" in self.branch_type:
                        self.tax_bool.set(True)
                        self.is_tax.set("ขอใบกำกับ สนงใหญ่")
                        self.display_is_tax.config(
                            background="#ff0000", foreground="#FFF", font='Chiller 10 bold')
                        self.tax_num.set(tax_num_only)
                    elif self.branch_type == "สาขาย่อย" and not pd.isna(self.data_frame[self.target_row]['รหัสประจำสาขา'].iloc[0]):
                        self.tax_bool.set(True)
                        self.is_tax.set("ขอใบกำกับ สาขาย่อย")
                        self.display_is_tax.config(
                            background="#ff0055", foreground="#FFF", font='Chiller 10 bold')
                        self.tax_num.set(tax_num_only)
                    else:
                        self.tax_bool.set(True)
                        self.is_tax.set("ไม่ขอแต่มีเลข")
                        self.display_is_tax.config(
                            background="#ff9e36", foreground="#FFF", font='Chiller 12 bold')
                        self.tax_num.set(tax_num_only)

                if self.tax_bool.get() == True and len(tax_num_only) == 13:
                    pass

                # * แสดงผล
                # self.address = self.filter_data.iat[0, 59]
                self.address = self.nondistortedData['รายละเอียดที่อยู่']
                self.cus_remark: str = str(
                    self.nondistortedData['หมายเหตุจากผู้ซื้อ'])
                self.order_note: str = str(self.nondistortedData['บันทึก'])
                self.cus_email.set(
                    str(self.nondistortedData['อีเมลสำหรับรับใบกำกับภาษี']))

                print("ตรวจหมายเหตุ: ", self.cus_remark)
                print("ตรวจบันทึก: ", self.order_note,
                      "type: ", type(self.order_note))

                if self.marketplace_target.get() == 'SHOPEE':
                    self.note_extractor()
                elif self.marketplace_target.get() == 'LAZADA':
                    pass

                self.cleaned_address = f"""{self.get_pure_address(self.clean_address(self.address))} {self.nondistortedData['แขวง/ตำบล']} {self.nondistortedData['เขต/อำเภอ.1']} {self.nondistortedData['จังหวัด.1']} {self.nondistortedData['รหัสไปรษณีย์.1']}"""

                if "กรุงเทพ" in self.cleaned_address:
                    self.cleaned_address = self.cleaned_address.replace(
                        "จังหวัด", '')
                # print("Addressที่คลีนแล้ว: ", self.cleaned_address)
                self.search_result = {"status": self.order_status,
                                      "is_tax": self.tax_bool.get(), "address": self.cleaned_address, "details": self.nondistortedData, "items": self.items}

                # * สร้างสูตรสำหรับสร้าง input gui
                print("มีไอเทมไรบ้าง", self.search_result['items'])
                self.input_formula = []
                for item in self.search_result['items']:
                    amount = int(item['จำนวน'])
                    sku = str(item['เลขอ้างอิง SKU (SKU Reference No.)'])
                    result = {'sku': sku, 'qty': amount}
                    self.input_formula.append(result)
                    print("จำนวน", int(item['จำนวน']),
                          type(int(item['จำนวน'])))
                print("สูตรสร้าง input", self.input_formula)
                for idx, item in enumerate(self.input_formula):
                    print("รายการที่ ", idx+1, item['sku'])
                    for idx in range(item['qty']):
                        print("สร้างinputอันที่ ", idx+1)

                self.cus_account_name.set(
                    self.nondistortedData['ชื่อผู้ใช้ (ผู้ซื้อ)'].strip())
                print("self.cus_account_name: ", self.cus_account_name.get())

                # * update display text ใน gui
                # เลือกว่าจะใช้ที่อยู่ แบบรายcol หรือ แบบสำเร็จ ไปอัพเดทและแสดงผลที่อยู่ใน gui โดยอัพเดท the gui ด้วย method update_gui_address
                # การจะเลือกรายcol ได้ต้องชัวร์ว่า col แขวง/ตำบลต้องไม่ใช่ค่าว่าง หรือต้องไม่ Return เป็น "nan"
                try:
                    if not str(self.nondistortedData['แขวง/ตำบล']) == "nan":
                        print("แขวง/ตำบล ไม่เท่ากับ nan: ",
                              self.nondistortedData['แขวง/ตำบล'])
                        self.update_gui_address(
                            re.sub(r'\s{2,}', " ", self.cleaned_address.replace('\u200b', '')).strip())
                    else:
                        print("ถ้ามี nan")
                        self.update_gui_address(re.sub(
                            r'\s{2,}', " ", self.nondistortedData['ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป'].strip().replace('\u200b', '')))
                except:
                    self.update_gui_address('-')

                self.update_gui_remark()
                self.update_gui_note()

                # * เก็บค่ารายละเอียดที่อยู่
                self.cus_province.set(
                    self.nondistortedData['จังหวัด.1'].strip())
                self.cus_district.set(
                    self.nondistortedData['เขต/อำเภอ.1'].strip())
                if self.cus_sub_district != "":
                    self.cus_sub_district.set(
                        self.nondistortedData['แขวง/ตำบล'])
                else:
                    self.cus_sub_district.set('')
                if not str(self.nondistortedData['หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี']) == "nan":
                    tel_for_set = self.cus_tel_fixer(
                        self.nondistortedData['หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี'])
                    self.cus_tel.set(tel_for_set)
                else:
                    self.cus_tel.set("1")

                self.cus_ship_cost.set(
                    self.nondistortedData['ค่าจัดส่งที่ชำระโดยผู้ซื้อ'])
                self.cus_seller_voucher.set(abs(
                    self.nondistortedData['โค้ดส่วนลดชำระโดยผู้ขาย']))
                self.cus_purchase_time.set(
                    self.nondistortedData['วันที่ทำการสั่งซื้อ'])

                self.net_prices_list = []
                for item in self.items:
                    net_price = item['ราคาขายสุทธิ'] + item['ส่วนลดจาก Shopee']
                    self.net_prices_list.append(net_price)
                # print(f"ขอใบกำกับไหม? {result['is_tax'].get()}")
                # print(f"ที่อยู่: {result['address']}")
                # print("self.bot.get_tabs() ต้องถูกใช้ที่นี่")
                # self.update_log(f"ขอใบกำกับไหม? {result['is_tax'].get()}")
                # self.update_log(f"ที่อยู่: {result['address']}")
                # self.update_log("self.bot.get_tabs() ต้องถูกใช้ที่นี่")
                # loopสินค้า

                self.sum_price = sum(self.net_prices_list)
                self.show_products(self.items)
                print("จำนวนเงิน", self.f(
                    self.nondistortedData['จำนวนเงินทั้งหมด']))
                print('สินค้ารวมค่าส่ง: ',
                      self.f(self.nondistortedData['จำนวนเงินทั้งหมด']+float(self.cus_ship_cost.get())))
                self.update_log(f"เวลาที่สั่ง: {self.cus_purchase_time.get()}")
                self.update_log(
                    f"ค่าขนส่ง: {self.f(self.cus_ship_cost.get())}")
                self.update_log(
                    f"ราคาที่ต้องยิงทั้งหมด+ค่าส่ง: {self.f(float(self.sum_price)+float(self.cus_ship_cost.get()))}")
                self.update_log(
                    f"seller voucher: -{self.f(self.cus_seller_voucher.get())}")
                self.update_log(
                    f"สินค้าเฉยๆ หักseller: {self.f((self.sum_price)-self.cus_seller_voucher.get())}")
                self.update_log(
                    f"สินค้ารวมค่าส่ง หักseller: {self.f((self.sum_price+self.cus_ship_cost.get())-self.cus_seller_voucher.get())}")

            else:
                print(
                    f"Order ที่ยิงมา {self.cus_order.get()} ไม่สามารถหาใน Export File ได้")
                print(
                    "อาจเกิดจาก เลข Order ที่กรอกเข้ามาผิดพลาด หรือไม่ก็ ไฟล์เก่าเกินไป")
                print("ถ้าไฟล์เก่าแนะนำให้ไป Export File มาใหม่ จาก Link ที่ให้ด้านล่าง")
                print("https://seller.shopee.co.th/portal/sale/shipment?type=toship")

                self.update_log(
                    f"Order ที่ยิงมา {self.cus_order.get()} ไม่สามารถหาใน Export File ได้")
                self.update_log(
                    "อาจเกิดจาก เลข Order ที่กรอกเข้ามาผิดพลาด หรือถ้า Order ไม่ผิด ก็แปลว่าไฟล์ไม่มีข้อมูล")
                self.update_log(
                    "ถ้าไฟล์เก่าแนะนำให้ไป Export File มาใหม่ จาก Link ที่ให้ด้านล่าง")
                self.update_log(
                    "https://seller.shopee.co.th/portal/sale/shipment?type=toship")
                self.reset_all_display()

        else:
            self.reset_all_display()
        print("ถึงแน่นอล")
        self.on_complete.set()
        print("จบ")

    def cusNameFixer5(self, name, account_name=":"):
        is_found = re.search(r"\[.*\]|\(.*\)|\{.*\}", name)
        name = re.sub(r"\[.*\]|\(.*\)|\{.*\}", '',
                      name).strip() if is_found else name.strip()
        # เช็คว่าถ้ามองชื่อเป็น list มันจะแบ่งได้กี่ส่วน
        name += " "+account_name if len(name.split()) == 1 else ""
        print("name:", name)
        return name

    def tax_name_standarizer(self, name):
        name_edited = name.replace('\u200b', '')
        # ** ลบคำที่ไม่ใช่ชื่อลูกค้า
        # * > ลบประเภทการจดทะเบียน ถ้าชื่อลูกค้าไม่มี บจก หรือ หจก เราก็จะไม่รู้ว่าลูกค้าให้ออกอะไร เลยทำให้ ไม่มีเงื่อนไขของคนที่ไม่ได้บอก
        if "หจก" in name_edited or "ห้างหุ้นส่วนจำกัด" in name_edited:
            print("เงื่อนไขชื่อใบกำกับใน if", name_edited)
            name_edited = name_edited.replace(
                "หจก.", "").replace("ห้างหุ้นส่วนจำกัด", "").strip()
            name_edited = f"""ห้างหุ้นส่วนจำกัด {
                name_edited}"""

        elif "บจก" in name_edited or "บริษัท" in name_edited or "จำกัด" in name_edited:
            print("เงื่อนไขชื่อใบกำกับใน elif", name_edited)
            name_edited = name_edited.replace(
                "บจก.", "").replace("บริษัท", "").replace("จำกัด", "").strip()
            name_edited = f"""บริษัท {
                name_edited} จำกัด"""

        # * > ลบประเภทสาขา
        if "สำนักงานใหญ่" in name_edited or "(สำนักงานใหญ่)" in name_edited:
            name_edited = name_edited.replace(
                "(สำนักงานใหญ่)", "").replace("สำนักงานใหญ่", "").strip()
        elif "(สาขา" in name_edited or "สาขา" in name_edited:
            name_edited = re.sub(
                r'\(สาขา.*\)', '', name_edited)
            name_edited = re.sub(
                r'\สาขา\d*', '', name_edited)

        return name_edited

    def on_thread_done(self):
        self.get_tabs_stat = self.get_tabs_thread.is_alive()
        self.search_thread_stat = self.search_thread.is_alive()
        print("ก่อนifเช็คตัวรัน tab", self.get_tabs_stat)
        print("ก่อนifเช็คตัวรัน excel", self.search_thread_stat)
        if self.get_tabs_thread.is_alive():
            # self.search_complete.set()
            self.get_tabs_thread.join()

        print("Thread is done คงเหงาแย่")

        self.get_tabs_stat = self.get_tabs_thread.is_alive()
        self.search_thread_stat = self.search_thread.is_alive()
        print("หลังifเช็คตัวรัน tab", self.get_tabs_stat)
        print("หลังifเช็คตัวรัน excel", self.search_thread_stat)

        print("Thread is done")
        self.display_bot_status_label.config(
            text=f"Bot Status: ˶ᵔ ᵕ ᵔ˶ จบการทำงาน", bg="#d9f2ff", fg="#000")
        if self.get_tabs_thread.is_alive():
            print("มีthreadใหม่มาต่อ")
            self.display_bot_status_label.config(
                text=f"Bot Status: ᕦʕ •ᴥ•ʔᕤ กำลังทำงาน", bg="#cf1313", fg="#ffffff")

    def search(self):
        self.autofinal = False
        # ลบ result products list เก่า
        for widget in self.mp_products_list_frame.winfo_children()[6:]:
            widget.destroy()

        self.search_query = self.entered_order.get()
        print("search() ทำงานและได้ผลลัพธ์: ", self.search_query)
        self.entered_order.set("")
        if self.search_query != "":
            self.report_log.config(state=NORMAL)
            self.report_log.delete("1.0", "end")
            # self.report_log.insert(END, self.search_query + "\n")
            self.report_log.config(state=DISABLED)
        else:
            self.report_log.config(state=NORMAL)
            self.report_log.delete("1.0", "end")
            self.report_log.config(state=DISABLED)

        self.search_complete = threading.Event()
        # self.search_complete.set()
        self.search_thread = threading.Thread(
            target=lambda: self.order_search(self.search_query, self.search_complete))
        self.get_tabs_thread = threading.Thread(target=self.bot.get_tabs)

        # if self.search_thread.is_alive() or self.get_tabs_thread.is_alive():
        #     print("Thread ยังไม่ตาย")
        #     self.bot_state.set(False)
        #     print("ฆ่า Thread")
        # self.bot_state.set(True)

        print("เริ่มThreadใหม่")
        self.search_thread.start()
        self.display_bot_status_label.config(
            text=f"Bot Status: ᕦʕ •ᴥ•ʔᕤ Botกำลังทำงาน", bg="#cf1313", fg="#ffffff")
        # ปิดชั่วคราว get_tabs
        try:
            self.get_tabs_thread.start()
        except EXCEPTION as err:
            print("err จาก get_tabs", err)

        timer = threading.Timer(0.2, self.on_thread_done)
        timer.start()

    def open_subwindow(self):
        self.data_source_selector.create_subwindow()

    def get_dataframe(self):
        print("เรียกหา dataframe")


# สำหรับเลือกที่มาของแหล่งข้อมูล
class DataSourceSelector:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.create_subwindow()

    def create_subwindow(self):
        self.subwindow = Toplevel(self.parent)
        self.subwindow.transient(self.parent)
        self.subwindow.geometry("250x75+650+400")
        self.subwindow.title("Data Source")
        self.subwindow.grab_set()
        self.subwindow.resizable(False, False)

        self.api_btn = Button(self.subwindow, text="API",
                              command=self.select_api)
        self.api_btn.pack(side='left', expand=TRUE, fill="both")
        self.excel_btn = Button(
            self.subwindow, text="Excel", command=self.select_excel)
        self.excel_btn.pack(side='left', expand=TRUE, fill="both")

        self.subwindow.protocol("WM_DELETE_WINDOW", self.on_close)

    def select_api(self):
        self.app.result = "API"
        print("Select API")
        self.subwindow.destroy()

    def select_excel(self):
        self.app.result = "Excel"
        print("Select Excel")
        self.app.table_location = filedialog.askopenfilename()
        self.app.display_location_result.config(
            text=f"{self.app.table_location.split('/')[-1]}")
        # target should come before get dataframe
        self.app.marketplace_target.set(self.app.define_marketplace())
        result = self.app.marketplace_target.get()
        print("ต้องตีเว็บไหน", result)
        # self.canvas.config(bg=f'{self.bg_by_market_place[self.app.marketplace_target.get()}')
        self.app.entry_frame.config(
            bg=f'{self.app.bg_by_market_place[str(result)]}')
        self.app.marketplace_label.config(
            bg=f'{self.app.bg_by_market_place[str(result)]}')
        # self.import_file_frame.config(
        #     bg=f'{self.bg_by_market_place[self.app.marketplace_target.get()]}')

        self.app.get_data_frame()
        print("Table Location:", self.app.table_location)
        self.subwindow.destroy()
        self.app.update_log("เพิ่มไฟล์แล้ว")

    def on_close(self):
        self.app.marketplace_target.set("")
        self.subwindow.destroy()

# class สำหรับรับ ID PASS


class PopUp:
    def __init__(self, title, message, parent):
        self.parent = parent
        self.title = title
        self.message = message
        self.create_subwindow()

    def delete(self):
        self.subwindow.destroy()

    def create_subwindow(self):
        self.subwindow = Toplevel(self.parent)
        self.subwindow.transient(self.parent)
        self.subwindow.geometry("250x140+650+400")
        self.subwindow.title(f"{self.title}")
        self.subwindow.grab_set()
        self.subwindow.resizable(False, False)
        # สร้างเฟรม
        self.subwin_frame = Frame(self.subwindow)
        self.subwin_frame.pack(padx=10, pady=10, fill='x', expand=True)
        # สร้าง widget
        self.id_label = Label(
            self.subwin_frame, text=self.message, font=("bazooka", 9))
        self.id_label.pack(fill='x', expand=True)

        # Submit Button
        self.submit_btn = Button(
            self.subwin_frame, text="Submit", command=self.delete)
        self.submit_btn.pack(fill='x', expand=True)


class UserAccount:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.create_subwindow()

    def create_subwindow(self):
        self.subwindow = Toplevel(self.parent)
        self.subwindow.transient(self.parent)
        self.subwindow.geometry("250x140+650+400")
        self.subwindow.title("Loginปลอม")
        self.subwindow.grab_set()
        self.subwindow.resizable(False, False)

        # * Event Enter
        self.subwindow.bind(
            "<Return>", lambda event=None: self.submit_btn.invoke())

        # * สร้างเฟรม
        self.subwin_frame = Frame(self.subwindow)
        self.subwin_frame.pack(padx=10, pady=10, fill='x', expand=True)

        # * สร้าง widget
        self.id_label = Label(
            self.subwin_frame, text="SMCO ID", font=("bazooka", 9), anchor="w")
        self.id_label.pack(fill='x', expand=True)
        # self.id_input = Entry(self.subwin_frame, textvariable=self.app.user_id,
        #                       validate="key", validatecommand=(self.app.validate_input_variable, '%P'))
        self.id_input = Entry(self.subwin_frame, textvariable=self.app.user_id)
        self.id_input.pack(fill='x', expand=True)
        self.id_input.focus()

        self.pass_label = Label(
            self.subwin_frame, text="SMCO Password", font=("bazooka", 9), anchor="w")
        self.pass_label.pack(fill='x', expand=True)
        # self.pass_input = Entry(
        #     self.subwin_frame, textvariable=self.app.user_pw, show="*", validate="key", validatecommand=(self.app.validate_input_variable, '%P'))
        self.pass_input = Entry(
            self.subwin_frame, textvariable=self.app.user_pw, show="*")
        self.pass_input.pack(fill='x', expand=True)

        # * checkBox
        self.chk_bx_show_pw = Checkbutton(self.subwin_frame, text="Show Pass", font=(
            'bazooka', 9), command=self.show_and_hide)
        self.chk_bx_show_pw.pack()

        # Submit Button
        self.submit_btn = Button(
            self.subwin_frame, text="Submit", command=self.update_btn)
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

        response = requests.post(
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
            self.login_alert = PopUp(
                "Login Fail!!", "พาสเวิร์ดผิดหรือป่าว~\nถ้าถูกแล้วก็อาจจะเป็นที่ SMCO\nลองเช็ค SMCO ดู", self.parent)
            return False

    def update_btn(self):
        if self.app.user_id.get() and self.app.user_pw.get():

            # is_closable = self.login()
            is_closable = True
            print("ปิดได้ไหม ", is_closable)
            if is_closable:
                self.display_btn_txt = f"Logged in !! ID : {self.app.user_id.get()}"
                self.app.display_acc_btn.config(text=self.display_btn_txt)
                self.subwindow.destroy()
                return self.display_btn_txt
            else:
                print("ไม่ติด")
                self.display_btn_txt = "Login"
                # self.subwindow.destroy()
                # return self.display_btn_txt

    def show_and_hide(self):
        if self.pass_input['show'] == '*':
            self.pass_input['show'] = ''
        else:
            self.pass_input['show'] = '*'


class Bot_POS:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.setup_chrome()

    def setup_chrome(self):
        self.opt = Options()
        exepath = sys.argv[0]
        Dir_path = os.path.dirname(os.path.abspath(exepath))
        self.custom_path = r'D:\\bin\\'
        Download_dir = Dir_path+self.custom_path

        os.environ["WDM_LOCAL"] = self.custom_path
        self.opt.add_experimental_option("debuggerAddress", "localhost:8989")
        # self.opt.add_experimental_option("prefs",{
        #     "download.default_directory" : Download_dir,
        #     "directory_upgrade": True
        # })

        self.driver = webdriver.Chrome(service=Service(
            r'C:\bin\chromedriver.exe'), options=self.opt)
        # self.driver = webdriver.Chrome(service=Service(
        #     ChromeDriverManager().install()), options=self.opt)

    def get_tabs(self):
        try:
            if self.parent.winfo_exists():
                print("รายงานจำนวนtabs")

                self.title_list = []
                self.title_list_Idx = []
                self.value_list = []
                self.title_dict = {}
                for idx, handle in enumerate(self.driver.window_handles):
                    self.driver.switch_to.window(handle)
                    self.title_list_Idx.append(
                        self.driver.title + "["+str(idx)+"]")
                    self.title_list.append(self.driver.title)

                    self.value_list.append(self.driver.current_window_handle)
                    self.title_dict.update(
                        {self.driver.title: self.driver.current_window_handle})

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
                self.operation_start()
        except Exception as e:
            print(f"An error occirred: {e}")

    def enter_cus_name(self, cus_search):
        # เคลียและกรอกชื่อลูกค้า
        self.driver.find_element(By.XPATH, self.app.cusNameInput).clear()
        self.driver.find_element(
            By.XPATH, self.app.cusNameInput).send_keys(cus_search)

    def printtingPage(self):
        time.sleep(2)
        self.printing_page = self.driver.find_element(By().XPATH, '/html/body')
        self.action01 = ActionChains(
            self.driver).context_click(self.printing_page)
        self.action01.perform()

    def operation_start(self):
        if self.app.order != "":
            ### * MARKETPLACES Part ########################################################################################
            self.autofinal = False
            print("operation start!! ยังไม่มีไรจะใส่ใส่เป็น placeholderไว้ก่อน")
            self.wait1 = WebDriverWait(self.driver, 50)
            # * เปลี่ยนไปtab MARKETPLACES เพื่อเช็ค status (เพราะไม่มี API เลยต้องทำ และเพื่อดูรูปว่ามีของแถมหรือไม่)

            #### IF MARKETPLACE IS SHOPEE ###################################################################################################################################
            if self.app.marketplace_target.get() == 'SHOPEE':
                self.driver.switch_to.window(self.merged_dict['Seller Centre'])
                cur_url = self.driver.current_url

                # * เปลี่ยนไปใช้หน้า "ทั้งหมด" เพราะ ในที่หน้าต่างกัน css, elements มันต่างกัน บังคับให้มันใช้อันที่ถูก
                if cur_url != "https://seller.shopee.co.th/portal/sale/order":
                    # self.driver.get("https://seller.shopee.co.th/portal/sale/order")
                    self.driver.find_element(
                        By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[1]/div[1]/div/div/div/div[1]/div/div[1]/div[1]').click()
                    self.wait1.until(EC.text_to_be_present_in_element(
                        (By.XPATH, '/html/body/div[1]/div[1]/div/div[1]/div/div[2]/div[1]/a'), 'การขายของฉัน'))
                else:
                    pass

                # * กรอก order ลงในช่อง search
                self.search_elmt = self.wait1.until(EC.visibility_of_element_located(
                    (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[1]/div[2]/div[2]/div[1]/span[2]/div/div[1]/div/div/input')))
                self.search_elmt.clear()
                self.search_elmt.send_keys(self.app.cus_order.get())

                # * กด Search เพื่อ เก็บ Status
                self.searchBtn = self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[1]/div[2]/div[2]/div[2]/button[1]')
                self.searchBtn.click()

                # * ตรวจสอบ Status และ update
                # รอให้ elemtn ที่อยู๋หลังสุดปรากดก่อน
                try:
                    self.driver.find_element(
                        By.CLASS_NAME, 'big-text').is_displayed()
                except:
                    self.wait1.until(EC.element_to_be_clickable(
                        (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[3]/div/div[3]/a/div[2]/div/div/div')))

                #  ต้องใช้ try except เพราะ element ของ shopee มันดันแบ่งเป็นสองแบบหากมีสถานะ order ที่ต่างกัน แทนที่จะเขียนให้เหมือนกัน ยุ่งยากกว่าเดิม
                try:
                    # สำหรับ หาข้อความ "ที่ต้องจัดส่ง" ต่อให้มี element ที่บรรจุคำว่า "จะถูกยกเลินใน x วัน" หรือ "การจัดส่งช้า" ตราบใดที่ข้างล่างมี ที่ต้องจัดส่ง จะมี class big-text เสมอ
                    self.app.cus_cur_status.set(self.driver.find_element(
                        By.CLASS_NAME, 'big-text').text)

                except:
                    # สำหรับ หาข้อความ "ส่งสินค้าแล้ว", "ยกเลิกแล้ว", "สำเร็จ"
                    self.app.cus_cur_status.set(self.driver.find_element(
                        By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[3]/div/div[3]/a/div[2]/div/div/div/div[3]/div[1]/span').text)

                # จะได้ element มา
                print("realtime_status_text", self.app.cus_cur_status.get())
                self.app.display_current_status.config(
                    fg="#000000", bg="#8fd4ff")
                if self.app.cus_cur_status.get() == "ส่งสินค้าแล้ว":
                    self.app.display_current_status.config(
                        bg="#00ff11", fg="#000000")
                elif "ยกเลิก" in self.app.cus_cur_status.get():
                    self.app.display_current_status.config(
                        bg="#ff2b2b", fg="#FFF")

                self.is_status_true = self.app.order_status == self.app.cus_cur_status.get()
                if self.is_status_true:
                    print(self.app.order_status ==
                          self.app.cus_cur_status.get())
                    print("Status in the file is reliable")
                else:
                    print(self.app.order_status ==
                          self.app.cus_cur_status.get())
                    print(
                        "Status in the file is unreliable, suggest downloading a new Export File from the link below")
                    print(
                        "https://seller.shopee.co.th/portal/sale/shipment?type=toship")

            #### IF MARKETPLACE IS LAZADA ###########################################################################################################################
            elif self.app.marketplace_target.get() == 'LAZADA':
                self.driver.switch_to.window(
                    self.merged_dict['การจัดการคำสั่งซื้อ - Seller Center'])
                cur_url = self.driver.current_url

                # * เปลี่ยนไปใช้หน้า "ทั้งหมด" เพราะ ในที่หน้าต่างกัน css, elements มันต่างกัน บังคับให้มันใช้อันที่ถูก
                if cur_url != "https://sellercenter.lazada.co.th/apps/order/list?oldVersion=1&spm=a1zawg.23708326.navi_left_sidebar.droot_normal_ordersreviews_ordersnewui.3fa34edfUCdGFY&status=all":
                    self.driver.find_element(
                        By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/div[2]/div/div[1]/div/div/div/ul/li[1]/div').click()
                    time.sleep(0.75)
                    self.wait1.until(EC.element_to_be_clickable(
                        (By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/div[3]/div/div[3]/div[1]/div[1]/div[2]/div[2]/span[1]/span[2]/span/a')))
                # else:
                #     pass

                # * กรอก order ลงในช่อง search
                self.search_elmt = self.wait1.until(EC.visibility_of_element_located(
                    (By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/span/input')))

                self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/span/input').clear()

                self.input_count = []

                try:
                    close_btn = self.driver.find_element(
                        By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/div[1]/span[2]')

                    try:
                        self.input_count = self.driver.find_element(
                            By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/div[2]/span/span')
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
                                By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/div[1]/span[2]')
                            print("click", click)

                            close_btn.click()
                    else:
                        print("1 times click")
                        close_btn.click()

                except Exception as err:
                    # print("ไม่กดวะ: ", err)
                    # print(
                    #     "Cannot find the variable self.input_count (no counter number, so skip!)")
                    # # print("1 times click as well")
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
                    By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/div[1]')
                self.searchBtn.click()
                time.sleep(0.75)

                # * ตรวจสอบ Status และ update
                # รอให้ btn element กดได้
                self.wait1.until(EC.element_to_be_clickable(
                    (By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/div[3]/div/div[3]/div/div[2]/div/div/div[5]/div[1]/button')))

                # เก็บ status order เข้าตัวแปรไปแสดงผลใน GUI
                self.app.cus_cur_status.set(self.driver.find_element(
                    By.XPATH, '/html/body/div/section/div[2]/div/div[1]/div/div/div[3]/div/div[3]/div/div[2]/div/div/div[5]/div[1]/button/span').text)

                # จะได้ element มา
                print("realtime_status_text", self.app.cus_cur_status.get())
                self.app.display_current_status.config(
                    fg="#000000", bg="#8fd4ff")
                if "พิมพ์ใบแจ้งหนี้" in self.app.cus_cur_status.get():
                    self.app.display_current_status.config(
                        bg="#ff2b2b", fg="#FFF")
                elif self.app.cus_cur_status.get() == "สถานะการจัดส่ง":
                    self.app.display_current_status.config(
                        bg="#00ff11", fg="#000000")

            #### IF MARKETPLACE NON OF THEM ABOVE ###################################################################################################################
            else:
                self.driver.switch_to.window(self.merged_dict[''])
                print('Cannot Define What marketplace you are working with')

            ### * SMCO PART ############################################################################
            # * เปลี่ยนไปtab SMCO0 เพื่อเช็ค ชื่อลูกค้า
            self.driver.switch_to.window(
                self.merged_dict['SMCO :: เปิดการขาย'])

            # * ดูก่อนว่าเคลียชื่อลูกค้าแล้วเหรอยัง
            print("Error น่าจะอยู่แถวนี้")
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
                        # ถ้ามีสินค้าจะ error คลิกไม่ได้จะกลายเป็น except
                        try:
                            print("wait for pop-up(try)")
                            # ระบุปุ่ม ok
                            if self.driver.find_element(By.XPATH, '/html/body/div[16]/div[2]/button[1]'):
                                print("has pop-up")
                                self.driver.find_element(
                                    By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()
                                print("Click OK")
                                pass
                        except:
                            print("wait for pop-up(except)")
                            time.sleep(1)
                            # ระบุปุ่ม ok
                            if self.driver.find_element(By.XPATH, '/html/body/div[16]/div[2]/button[1]'):
                                print("has pop-up")
                                self.driver.find_element(
                                    By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()
                                print("Click OK")
                                pass

                    print("หน้าใหม่พร้อมแล้ว")
                elif self.is_reset == False:
                    print("ไม่ต้องรี")
            except EXCEPTION as err:
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
            # while True:
            #     if self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/button'):
            #         print("เจอแล้วออก")
            #         break
            #     else:
            #         continue

            self.wait1.until(EC.element_to_be_clickable(
                (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/button')))

            time.sleep(1)
            # * เปลี่ยน auto เป็น name ไม่ก็ email โดยขึ้นอยู่กับว่าขอใบกำกับหรือไม่
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/button').click()
            print("self.app.tax_bool: ", self.app.tax_bool.get())
            if self.app.tax_bool.get() == True:
                # ขอใบกำกับ **Trick** สามารถใส่single qoute สามตัวได้ หากด้านในมีการใช้ qoute และ bouble qoute ไปแล้ว แต่ทั้งหมดต้องเป็น string อีกที >>  ('''function("vbvb, x='แมว'")''')
                if self.app.marketplace_target.get() == "SHOPEE":
                    print("ขอใบกำกับSHOPEE ใช้ E:")
                    self.driver.find_element(
                        By.XPATH, r'''/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/div/a[contains(@ng-click, "st='E'")]''').click()
                elif self.app.marketplace_target.get() == "LAZADA":
                    print("ขอใบกำกับLazada ใช้ P:")
                    self.driver.find_element(
                        By.XPATH, r'''/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/div/a[contains(@ng-click, "st='T'")]''').click()
            elif self.app.tax_bool.get() == False:
                # ไม่ขอใบกำกับ
                print("ไม่ขอใบกำกับใช้ N:")
                self.driver.find_element(
                    By.XPATH, r'''/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/div/a[contains(@ng-click,"st='N'")]''').click()

            # * ดูว่า self.cus_search จะเป็นเลขหรือชื่อ อิงจาก tax_bool choosing by ternary like conditional
            # 09/11/2023 ใช้เลขใบกำกับเสิชไม่ได้แล้ว ฉะนั้นไม่ต้องเลือกแล้ว เอาชื่อเสิชให้หมดเลย

            if self.app.marketplace_target.get() == "SHOPEE":
                self.cus_search = self.app.cus_email.get() if self.app.tax_bool.get(
                ) else self.app.cusNameFixer5(self.app.cus_name.get(), self.app.cus_account_name.get())
            elif self.app.marketplace_target.get() == "LAZADA":
                self.cus_search = self.app.tax_num.get() if self.app.tax_bool.get(
                ) else self.app.cusNameFixer5(self.app.cus_name.get(), self.app.cus_account_name.get())

            # * จับตาดูว่า ul เปิดอยู่ไหม
            self.is_ul_not_open = False if self.driver.find_elements(
                By.XPATH, self.app.cus_name_ul) else True
            # กรณีไม่ได้เปิดไว้ จะเปิดให้
            if self.is_ul_not_open:
                self.driver.find_element(
                    By.XPATH, self.app.cus_arrow_btn).click()

                self.wait1.until(EC.visibility_of_element_located(
                    (By.XPATH, self.app.cusNameInput)))
            # ถ้าเปิดแล้วจะข้ามมานี่
            self.enter_cus_name(self.cus_search)
            print("กรอกชื่อเสร็จ")
            self.wait_condition = self.driver.find_element(
                By.XPATH, self.app.cusNameLi1)
            print("มันทำไม", self.wait_condition.text)

            #! น่าสงสัย เป็นเหตุให้หน้าท้ายค้าง
            self.customer_add_times = 0
            self.customer_name_search_count = 0
            while True:
                if self.driver.find_element(By.XPATH, self.app.cus_name_ul):
                    time.sleep(0.7)
                    # self.wait1.until(EC.visibility_of_element_located(
                    #     (By.XPATH, self.app.cusNameLi1)))
                    self.wait_condition = self.driver.find_element(
                        By.XPATH, self.app.cusNameLi1)

                    try:
                        if self.wait_condition.text == "Searching...":
                            continue
                        elif self.wait_condition.text:
                            print("text element disappeared")
                            pass
                    except:
                        pass

                    self.wait1.until(EC.visibility_of_element_located(
                        (By.XPATH, self.app.cusNameLi1)))
                    self.wait_condition = self.driver.find_element(
                        By.XPATH, self.app.cusNameLi1)
                    if self.wait_condition.text == "No results found" and self.customer_add_times == 0:
                        print("No results found and NeverAdd")
                        # * ขอใบกำกับป่าว
                        if self.app.tax_bool.get():
                            print("Tax_needed")
                            if self.app.marketplace_target.get() == 'SHOPEE':
                                self.addTaxInvCustomer()

                            # กำลังทำ กำลังปรับปรุง ยังไม่เสร็จ การหาลูกค้าของ laz มันมีกรณี excel และ api
                            # elif self.app.marketplace_target.get() == 'LAZADA':
                            #     self.addTaxInvCustomerLaz()

                        else:
                            print("no_Tax_needed")
                            self.addNormalCustomer(self.cus_search)

                        # เพิ่มจำนวนครั้งที่ add
                        self.customer_add_times += 1
                        self.driver.switch_to.window(
                            self.merged_dict['SMCO :: เปิดการขาย'])
                        print("ก่อนRe Enter ชื่อลูกค้า")
                        self.enter_cus_name(self.cus_search)
                        print(f"Re enter name after add")
                        continue
                    elif self.wait_condition.text == "No results found" and self.customer_name_search_count < 1:
                        self.enter_cus_name(self.cus_search)
                        self.customer_name_search_count += 1
                        print(
                            f"Re enter name after add extra times{self.customer_name_search_count}")
                        continue
                    elif self.wait_condition.text == "No results found" and self.customer_add_times == 1:
                        print(
                            "I've already add it, but the element still shows 'No results found', you have to add by yourself")
                        break
                    else:
                        self.driver.switch_to.window(
                            self.merged_dict['SMCO :: เปิดการขาย'])
                        break
                print("addcustomer and select While end!")
                break

            self.driver.find_element(By.XPATH, self.app.cusNameLi1).click()
            print("Click the cusname li result")
            if self.driver.find_element(By.XPATH, "/html/body/div[16]/div[2]"):
                try:
                    self.driver.find_element(
                        By.XPATH, "/html/body/div[16]/div[2]/button[1]").click()
                    self.driver.find_element(
                        By.XPATH, self.app.cus_arrow_btn).click()
                    self.wait1.until(EC.visibility_of_element_located(
                        (By.XPATH, self.app.cusNameInput)))
                except:
                    print("ข้าม Element ไม่โผล่")
            else:
                pass

            print("search หายไปแล้ว")
            self.wait1.until(EC.invisibility_of_element_located(
                (By.XPATH, self.app.cusNameInput)))

            # ใส่ค่าขนส่ง

            if int(self.app.cus_ship_cost.get()) != int(0):
                try:
                    self.skuInput = self.wait1.until(EC.visibility_of_element_located(
                        (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')))
                    # skuInput = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')
                    self.skuInput.clear()
                    self.skuInput.send_keys("SV0-000101")
                    print("กรอก Code ขนส่งสำเร็จ")

                    self.skuAddBtn = self.wait1.until(EC.visibility_of_element_located(
                        (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')))
                    # skuAddBtn = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')
                    self.skuAddBtn.send_keys(Keys().ENTER)
                    print("กด Enter ที่ช่อง SKU Input สำเร็จ")
                    time.sleep(2)

                    # ทำไมต้องใส่วงเล็บ คลุม BY.XPATH เพราะ ถ้าไม่ใส่ ฟังชัน visibility จะมอง xpath เป็น argument ที่สอง ของ method visibility
                    self.definePrice = self.wait1.until(EC.visibility_of_element_located(
                        (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div[1]/div/a[1]')))
                    # self.definePrice = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div[1]/div/a[1]')
                    self.definePrice.click()
                    time.sleep(1)
                    # ค่าขนส่งโดนข้า230208FX99FUGGมหลังจากตรงนี้
                    print("กดที่ SKU ELEMENT 1 สำเร็จ")

                    self.changePriceInput = self.driver.find_element(
                        By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[1]/input')
                    self.changePriceInput.clear()
                    self.changePriceInput.send_keys(
                        self.app.cus_ship_cost.get())
                    self.driver.find_element(
                        By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[2]/input').clear()
                    self.driver.find_element(
                        By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[2]/input').send_keys(self.app.user_id.get())

                    self.driver.find_element(
                        By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[3]/input').clear()
                    self.driver.find_element(
                        By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[3]/input').send_keys(self.app.user_pw.get())

                    self.driver.find_element(
                        By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[6]/div/div/div[2]/div[5]/div/textarea').clear()
                    self.driver.find_element(
                        By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[6]/div/div/div[2]/div[5]/div/textarea').send_keys("Online")

                    self.driver.find_element(
                        By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[6]/div/div/div[2]/div[6]/a[1]').click()
                    try:
                        print("รอหาย")
                        self.wait1(EC.invisibility_of_element_located((
                            By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[6]/div/div/div[2]/div[6]/a[1]')))
                    except:
                        print("ไม่มีให้รอ")
                except Exception as err:
                    print("ค่าขนส่งโดนข้าม")
                    print(err)
            else:
                print("เงื่อนไขค่าขนส่ง มี Boolean เป็น False")

            self.app.update_log(
                "Autoหน้าแรก มันจบแค่นี้ ยิงของ, ใส่คูปอง, กดไปหน้าถัดไปได้เลย")
            self.app.display_bot_status_label.config(
                text=f"Bot Status: Your Turn", bg="#21ff29", fg="#000")

            ### PHASE2 After Add customer name###############################################################################################################
            # # #เช็คของเติม CP อัตโนมัติ กำลังทำ ถ้าเอาไปใส่ใน while loop ข้างล่างมันจะบัค ไม่สามารถแปลงเป็น float ได้
            # while True:
            #     self.phase1_net_price = self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[2]/div/div/div/div/span[1]')
            #     self.phase1_net_price = float(self.phase1_net_price.text)
            #     if self.app.phase1_sum_price != self.phase1_net_price:
            #         print("ราคาไม่ตรง", self.app.phase1_sum_price,  " = ",self.phase1_net_price)
            #         continue
            #     else:
            #         print("ราคาตรงแล้ว")
            #         break

            self.autofinal = True
            while self.autofinal:
                print("เข้า final loop ")
                print("รอให้มันโผล่")
                while self.parent.winfo_exists() and self.autofinal:
                    time.sleep(0.1)
                    self.is_input_empty = self.driver.find_element(
                        By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]/span')
                    self.is_final_displayed = self.driver.find_element(
                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]').is_displayed()

                    if (self.is_input_empty.text == "Select Customer" or self.is_input_empty.text == "กรุณาเลือกลูกค้า") and self.is_final_displayed == False:
                        break
                    elif (self.is_input_empty.text != "Select Customer" or self.is_input_empty.text != "กรุณาเลือกลูกค้า") and self.is_final_displayed == False:
                        continue
                    elif (self.is_input_empty.text != "Select Customer" or self.is_input_empty.text != "กรุณาเลือกลูกค้า") and self.is_final_displayed == True:
                        time.sleep(0.75)
                        print("หน้า จ่ายตัง")
                        self.is_final_page2 = self.wait1.until(EC.visibility_of_element_located(
                            (By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]')))
                        self.last_page = self.driver.find_element(
                            By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]')
                        if (self.last_page.text == "Payment:") or (self.last_page.text == "ชำระเงิน:"):
                            # Auto หน้าท้าย ทำได้ครั้งเดียว
                            self.is_final_page2 = self.wait1.until(EC.visibility_of_element_located(
                                (By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]')))

                            # self.is_final_page = self.wait1.until(EC.visibility_of_element_located(
                            #     (By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[1]/textarea')))
                            try:
                                if self.app.cus_seller_voucher.get():
                                    # ถ้ามี เซลเลอร์ให้ ให้กรอกให้ด้วย
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[3]/div[1]/div[2]/input').clear()
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[3]/div[1]/div[2]/input').send_keys(self.app.cus_seller_voucher.get())

                                # ถ้าไม่มี seller ก็ไปกรอก remark ได้เลย
                                self.driver.find_element(
                                    By.XPATH, "/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[1]/textarea").clear()
                                self.driver.find_element(
                                    By.XPATH, "/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[1]/textarea").send_keys(self.app.cus_order.get())

                                # เลือกประเภทชำระเงิน
                                if self.app.marketplace_target.get() == 'SHOPEE':
                                    # เลือก shopee
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[2]/div/div/div[4]/a').click()
                                elif self.app.marketplace_target.get() == 'LAZADA':
                                    # เลือก lazada
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[2]/div/div/div[3]/a').click()

                                self.driver.find_element(
                                    By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[3]/div/div[2]/div[2]/div[3]/div[2]/div[1]/div[2]/input').clear()
                                self.driver.find_element(
                                    By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[3]/div/div[2]/div[2]/div[3]/div[2]/div[1]/div[2]/input').send_keys(self.app.cus_order.get())

                                try:
                                    self.driver.find_element(
                                        # จู่ๆ brows()btn มันก็ทำงานเลยต้องคลิกเพื่อปิด
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[3]/div[1]/div[1]/div/div/div/div/div[2]/center/button[2]').click()
                                except:
                                    print("ปุ่ม Brows() ไม่โผล่")
                                # ลูกค้ามีชื่อไหม ถ้าไม่มี ใส่ a
                                if self.app.cus_name.get():
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').clear()
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').send_keys(self.app.cus_name.get())
                                else:
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').clear()
                                    self.driver.find_element(
                                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').send_keys("a")
                            except:
                                print("Auto หน้าท้ายพัง ข้ามไปรอราคาเลย")
                                break

                            # ค้นหา element โดยใช้ XPath
                            self.is_input_on = self.driver.find_element(
                                By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]')

                            # ดึงข้อความจาก element ที่ค้นหาได้
                            text_value = self.is_input_on.get_attribute(
                                "title")

                            # พิมพ์ผลลัพธ์
                            print("ตรวจหาชื่อลูกค้า self.is_input_on:", text_value)

                            while True:
                                self.final_popup = self.driver.find_element(
                                    By.XPATH, '/html/body/div[16]/div[2]/button[1]')
                                # self.is_previous_page = self.wait1.until(EC.invisibility_of_element_located(
                                #     (By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]')))
                                self.is_previous_page = self.driver.find_element(
                                    By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]')
                                # print("self.is_previous_page= ",
                                #       self.is_previous_page)
                                if self.final_popup.is_displayed() == True:
                                    try:
                                        self.wait1.until(EC.element_to_be_clickable(
                                            (By.XPATH, '/html/body/div[16]/div[2]/button[1]'))).click()
                                    except:
                                        self.final_popup.click()

                                    # > รอหน้า canvas โผล่ก่อน
                                    self.wait1.until(EC.visibility_of_element_located(
                                        (By.XPATH, '/html/body/div[1]/div[2]/div[8]/div/div[2]')))
                                    self.printtingPage()
                                    break

                                elif self.is_previous_page.is_displayed() == False:
                                    print("End or back")
                                    if bool(re.search(r"\w{5}\-\w{3}-\w{10}", self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[8]/div/div[1]/span').text)):
                                        print("ไปหน้าสุดท้าย จบ loop")
                                        break
                                    elif self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/form/label'):
                                        print("กลับมาหน้าเดิม")
                                        break

                                else:
                                    continue

                                    # try:
                                    #     print('จุดจบ')
                                    #     # * กดปุ่มใน pop-up สุดท้าย
                                    #     self.driver.find_element(
                                    #         By.XPATH, '/html/body/div[16]/div[2]/button[1]')
                                    #     self.wait1.until(EC.visibility_of_element_located(
                                    #         (By.XPATH, '/html/body/div[16]/div[2]/button[1]')))
                                    #     self.wait1.until(EC.element_to_be_clickable(
                                    #         (By.XPATH, '/html/body/div[16]/div[2]/button[1]'))).click()
                                    #     # > รอหน้า canvas โผล่ก่อน
                                    #     self.wait1.until(EC.visibility_of_element_located(
                                    #         (By.XPATH, '/html/body/div[1]/div[2]/div[8]/div/div[2]')))
                                    #     self.printtingPage()
                                    #     break
                                    # except Exception as err:
                                    #     print('ไม่ใช่จุดจบ', err)
                                    #     pass
                            if self.final_popup.is_displayed() == True:
                                break
                            else:
                                # continue
                                break

                        else:
                            print("จบสูตร")
                        self.autofinal = False
                        break

                    break
                break

            print("จบ auto_last_page")
            self.autofinal = False
        else:
            print("ไม่มีOrder ไม่รู้จะทำอะไร")

    def addNormalCustomer(self, cusname_fixed):
        is_functionworking = False
        is_functionworking = True
        while is_functionworking:
            self.driver.switch_to.window(
                self.merged_dict['SMCO :: เปิดการขาย1'])

            self.element = self.driver.find_element(
                By.XPATH, self.app.cusSearchSMCO)
            self.element.click()  # กดแว่นขยาย
            self.btnElement = self.wait1.until(
                EC.element_to_be_clickable((By.XPATH, self.app.cusCreateBtn)))
            time.sleep(0.65)
            self.btnElement.click()  # create

            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').clear()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(cusname_fixed)

            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').clear()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(cusname_fixed)

            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').clear()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(self.app.cus_address)

            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').clear()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(1)

            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()

            # # 09/11/2023 partนี้ ทาง SMCO ลบออกไปแล้ว
            # self.wait1.until(EC.visibility_of_element_located(
            #     (By.XPATH, '/html/body/div[16]/div[2]/button[1]')))
            # self.driver.find_element(
            #     By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()

            # รอมันหายก่อน
            self.wait1.until(EC.invisibility_of_element_located(
                (By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]')))
            is_functionworking = False

    def addressExtractor(self, cusAddress):
        self.splited = cusAddress.split(",")
        return (self.splited)

    def addTaxInvCustomer(self):
        print("ชื่อลูกค้าเป็นไง", self.app.cus_name.get())
        name = self.app.cus_name.get()
        # * เติมสาขาให้เรียบร้อย
        if self.app.branch_type == 'สำนักงานใหญ่':
            self.app.tax_branch.set(self.app.nondistortedData['ประเภทสาขา'])
            name = f"""{name} ({self.app.tax_branch.get()})"""
        elif self.app.branch_type == "สาขาย่อย" and not pd.isna(self.app.data_frame[self.app.target_row]['รหัสประจำสาขา'].iloc[0]):
            name = f"""{name} (สาขา{self.app.tax_branch.get()})"""

        self.driver.switch_to.window(
            self.merged_dict['SMCO :: เปิดการขาย1'])
        self.driver.find_element(By.XPATH, self.app.cusSearchSMCO).click()
        time.sleep(0.75)
        self.driver.find_element(By.XPATH, self.app.cusCreateBtn).click()
        self.driver.find_element(
            # nameTH
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').clear()
        self.driver.find_element(
            # nameTH
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(f'{name} Tax ID: {self.app.tax_num.get()}')

        self.driver.find_element(
            # nameEN
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').clear()
        self.driver.find_element(
            # nameEN
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(f'{name} Tax ID: {self.app.tax_num.get()}')

        # กรอก Address
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').clear()
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(self.app.cus_address)

        # กรอก email
        self.email_input = self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[13]/div[2]/input')
        self.email_input.clear()
        self.email_input.send_keys(self.app.cus_email.get())

        # tel.
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').clear()
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(self.app.cus_tel.get())
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()
        # # กดเองตรวจเอง // 09/11/2023 partนี้ ลบออกไปแล้ว
        # self.wait1.until(EC.visibility_of_element_located(
        #     (By.XPATH, '/html/body/div[16]/div[2]/button[1]')))
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()
        # รอมันหายก่อน
        self.wait1.until(EC.invisibility_of_element_located(
            (By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]')))

    def addTaxInvCustomerLaz(self):
        tax_info = self.get_tax_info(
            self.app.tax_num.get(), self.app.tax_branch)
        print("ชื่อลูกค้าเป็นไง", self.app.cus_name.get())
        name = self.app.cus_name.get()
        # * เติมสาขาให้เรียบร้อย
        if self.app.branch_type == 'สำนักงานใหญ่':
            self.app.tax_branch.set(self.app.nondistortedData['ประเภทสาขา'])
            name = f"""{name} ({self.app.tax_branch.get()})"""
        elif self.app.branch_type == "สาขาย่อย" and not pd.isna(self.app.data_frame[self.app.target_row]['รหัสประจำสาขา'].iloc[0]):
            name = f"""{name} (สาขา{self.app.tax_branch.get()})"""

        self.driver.switch_to.window(
            self.merged_dict['SMCO :: เปิดการขาย1'])
        self.driver.find_element(By.XPATH, self.app.cusSearchSMCO).click()
        time.sleep(0.75)
        self.driver.find_element(By.XPATH, self.app.cusCreateBtn).click()
        self.driver.find_element(
            # nameTH
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').clear()
        self.driver.find_element(
            # nameTH
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(f"{tax_info['name']}")

        self.driver.find_element(
            # nameEN
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').clear()
        self.driver.find_element(
            # nameEN
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(f"{tax_info['name']}")

        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[3]/input').clear()  # Identity ID
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[3]/input').send_keys(self.app.tax_num.get())  # Identity ID
        # [finAddress, finSubdistrict, finDistrict, finProvince, finZipCode] = self.addressExtractor(
        #     self.app.cus_address)  # ปัญหา บางเคสลูกค้าใส่ comma มามากกว่า 5 อัน ทำให้ error
        # self.finProvince = finProvince.strip().lstrip("จังหวัด")

        # กรอก Address
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').clear()
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(tax_info['address_shortened'])

        # # กรอก email
        # self.email_input = self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[13]/div[2]/input')
        # self.email_input.clear()
        # self.email_input.send_keys(self.app.cus_email.get())

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
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()  # province input
        self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
            tax_info['province'].replace("จังหวัด", ""))  # province input
        time.sleep(1.75)
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[1]/div/span/span[1]/span/span[1]').click()  # District drop
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()  # District
        self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
            tax_info['dist'].replace("อำเภอ", "").replace("เขต", "").replace("ต.", ""))  # District
        time.sleep(1.75)
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

        # SubDistrict drop
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[3]/div/span/span[1]/span/span[1]').click()
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()  # SubDistrict
        self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
            tax_info['sub_dist'].replace("ตำบล", "").replace("แขวง", "").replace("ต.", ""))  # SubDistrict
        time.sleep(1.75)
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

        # tel.
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').clear()
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(self.app.cus_tel.get())
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()
        # # กดเองตรวจเอง // 09/11/2023 partนี้ ลบออกไปแล้ว
        # self.wait1.until(EC.visibility_of_element_located(
        #     (By.XPATH, '/html/body/div[16]/div[2]/button[1]')))
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()
        # รอมันหายก่อน
        self.wait1.until(EC.invisibility_of_element_located(
            (By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]')))

    def extract_address_info(self, input):
        try:
            # Create a copy of the output dictionary
            result = input.copy()

            # Remove the "ตำบล" and everything after it from the address
            address_only = re.compile(r'ตำบล.*')
            result['address_shortened'] = address_only.sub(
                '', result['address']).strip()

            # Define the regular expression pattern
            pattern = re.compile(
                r'ตำบล/แขวง\s+(\S+).*?เขต\s+(\S+).*?จังหวัด\s+(\S+)')

            # Use the pattern to find matches in the address
            matches = pattern.search(result['address'])

            # Extract the matched groups
            if matches:
                result['sub_dist'] = matches.group(1)
                result['dist'] = matches.group(2)
                result['province'] = matches.group(3)
            else:
                result['sub_dist'] = None
                result['dist'] = None
                result['province'] = None

            # Add a space after the word "บริษัท" in the company name
            result['name'] = re.sub(r'(บริษัท)\s*', r'\1 ', result['name'])

            return result
        except:
            return input

    def get_tax_info(self, tax_num, tax_branch):
        tax_input = str(tax_num)
        branch = str(tax_branch)
        jsession_id = ''

        cookies = {
            'JSESSIONID': '0000uelEKnUmVBz9ciAzvgnusDG:-1',
        }

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

        while True:
            if times == 1:
                print("times = 1")
                response = requests.post(
                    'https://vsreg.rd.go.th/VATINFOWSWeb/jsp/VATInfoWSServlet', params=params, headers=headers, data=data)
                print("responseไรมา", response.cookies)
                jsession_id = response.cookies['JSESSIONID']
            elif times > 1:
                print("jsession_id", jsession_id)
                cookies['JSESSIONID'] = f'{jsession_id}'
                data2['goto_page'] = f'{times}'
                response = requests.post('https://vsreg.rd.go.th/VATINFOWSWeb/jsp/VATInfoWSServlet?',
                                         params=params, cookies=cookies, headers=headers, data=data2)
            try:
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                # print("ได้ไรออกมา", soup)
                # หาว่า response มี <tr> หรือไม่ มีเท่าไหร่
                menu_elements = soup.select('tr[class^="trMenu"]')
                is_many_page = soup.select("""span[onclick^="gotoPage('"]""")
                print("มีหลายหน้า?: ", is_many_page)
                search_result = []
                output = ""

                # ตรวจหา element รายการข้อมูลใบกำกับ ซึ่งมันจะมี class ชื่อ trmenu
                if len(menu_elements):
                    # มี <tr>
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
                        # tr = menu_element.find('tr')
                        # ในแต่ละ <tr> มี <td> หลายอัน
                        tds = menu_element.find_all('td')
                        for idx, key in enumerate(result_data):
                            b = tds[idx].find('b')
                            result = b.find('font').text.strip()
                            result = re.sub("\s{2,}", " ", result)

                            # ช่วงใบกำกับ จะตัดเอาค่า 13 หลักจากด้านหลัง เพราะไอ 10 หลักตอนแรกมันคือไรไม่รู้
                            if idx == 1 and len(result) > 13:
                                result = result[-13:]

                            print(result)
                            result_data[key] = result
                        print(" ")
                        search_result.append(result_data)

                    # เอา search_result มาดูว่าตรงกับสาขาที่ต้องการหรือไม่
                    for item in search_result:
                        if item['branch'] == branch:
                            output = item
                            print("เกบค่าลง output")
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
                    print("ไม่มีใบกำกับ")
                    break

            except requests.exceptions.HTTPError as e:
                print(f"HTTP Error occurred: {e}")
            except Exception as e:
                print(f"An error occured: {e}")
            break

        output = self.extract_address_info(output)
        print("output: ", output)
        return output


if __name__ == "__main__":
    def on_closing():
        print("Tkinter window is closing")
        root.destroy()

    root = Tk()
    # * options
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.columnconfigure(0, weight=1)
    # root.resizable(False, False)
    # * Create Instance
    app = MyApp(root)
    root.mainloop()

# ปัญหาที่ต้องแก้
# *1แก้แล้ว** บรรทัดล่างสุด"สินค้ารวมค่าส่งหัก seller: " เลขยอดเงิน ที่แสดงผล เมื่อเจอ list mี่มีสมาชิกหลายตัว มันจะรวมแค่ตัวแรกอย่างเดียว ต้องใช้ forloop รวมราคาทุกตัว
# !2 เวลา kb เป็น ภาษาไทย จะกcopy ข้อความใน log ไม่ได้ น่าจะเป็นเพราะ เครื่องไม่ได้รับค่า ctrl+c แต่เป็น ctrl+แ
# *3 แอดใบกำกับ บัค ตรงที่ เราเหลือ ปุ่มสุดท้ายยังไม่กด แต่พอยังไม่กด มันไม่รอ มัน error ไปเลย
# *4 ลูกค้าธรรมดาไม่ต้องกรอก address แต่ใบกำกับกรอกให้แม่น
# *5 แก้แล้ว**ใบกำกับ/บิล ลืมล้างค่าก่อน แอด จริงๆ ทุก input ต้องล้างก่อนแอด ควรทำเป็นนิสัย ยังไม่เสร็จ
# *6แก้แล้ว** ตัวอย่าง order ทำ scrollbar "231010GK0S3VV3" เพราะมีหลายรายการ
# *7 หน้าท้ายรัน Auto ไปด้วย จะได้ไม่ต้อง copy
# *8 ปิด thread หลังจบคำสั่งด้วย terminateไม่ได้ แก้ด้วยข้อ 22 แทน
# *9แก้แล้ว** Total LastPage in SMCO -> ราคาที่ต้องออก
# *10แก้แล้ว** "Auto หน้าท้าย ทำได้ครั้งเดียว ส่วนนี้มันจะดัก" เวลามี pop-up ขึ้นกรณียิงของแล้ว SN ไม่มี มันจะ BUG  wait มันจะ Error ทีก่อนหน้านี้ waitfail ดันไม่ error งงชิพไห
# * /html/body/div[16]/div[2]/div[6] มีข้อความ "Your data has been successfully saved doing print Invoice No : B0183-W06-2310130023"
# *11 มีบัคตรงที่ลูกค้าบางคนใส่ (สำนักงานใหญ่) บางคนไม่ใส่ (สำนักงานใหญ่)//เปลี่ยนวิธี Add ลูกค้า และ ใบกำกับใหม่ ใช้สูตร BigM
# *12 ทำแล้ว //ทำ input ID PASS
# *13 แก้แล้วแต่จะใส่ให้สองครั้ง//ยังแก้ไม่ได้ลูกสึก bigM ยังมีปัญหากับตรงนี้อยู่ อาจจะลองแก้ด้วย while True // searhลูกค้า ไม่เจอแล้วแอด มันมีโอกาสที่แอดแล้วไม่เสิชต่อ
# *14 ทำแล้ว // ทำแยกตารางใหม่โดยใช้ layout แบบ Shopee //ตัวอักษรใน LOG หรือ ทำให้ Log อ่านและแยกแยะง่ายขึ้น ใช่ มันอ่านยากจริงๆ
# ?15 ตรวจดูแล้วยังไม่เจอสาเหตุ** ข้อความ "เพิ่มไฟล์แล้ว" แสดงผลไม่ถูกต้อง เนื่องจาก แสดงผล แม้ไม่ได้ แอดไฟล์จริงๆ
# *16 รายงาน มาว่าไม่เจอ แก้แล้วไม่รู้ใช้ได้ยัง // U200b display as ?
# !17 สินค้าบางประเภทต้องใส่ Variations ของมันด้วย ใน log จะได้แยกได้ เช่น หมึก มันจะไม่บอกสีใน ชื่อสินค้า แต่บอกใน variations
# *18 มีเลขลำดับบอกใน productslist
# ?19 แก้แล้ว!!!ยากมาก!!!เลยไม่ชัวว่าแก้ได้จริงป่าว ///order ไม่มี แต่ยังทำงานอยู่ เกิดจากการทำงานมันแยก thread กัน ต้องเอาผลลัพจากการเสิช มาเป็นเงื่อนไขว่าจะทำต่อหรือไม่
# *20 แก้แล้ว //แก้แล้วรอทดสอบ//ใบกำกับไม่มีคำว่า ใน margetplace มีคำว่า (สำนักงานใหญ่) แต่พอแอดมาดันไม่มี
# *21 ใช้ได้แล้ว //ทำได้แล้วรอทดสอบ //หน้าสุดท้ายกรอกเบิ้ล หากมีการยกเลิก หรือ รันบอททับ (ยากชิพไห) แต่หลักๆแก้ด้วย while True
# *22 แก้แล้ว//พวกไม่ขอแต่มีเลข มันจะได้สาขา nan มา ต้องแก้ด้วย
# *23  เพราะลูกค้าไม่ได้บอกว่าเป็น หจก หรือ บจก ไง เลยทำเงื่อนไขไม่ได้ เพราะกูก็ไม่รู้ว่าต้องเขียนชื่อเป็นอะไร // 231021G8CWC1N5 คำว่า บริษัทไม่ขึ้น
# *24 แก้แล้ว//เวลาสินค้ามีมากกว่า 1 รายการ แล้วถัดไปมีน้อยลง element ที่แสดงรายการ ของ order ที่แล้วจะไม่หายไป
# ?25 แก้แล้วเมื่อมี error thread จะถูกปิดทันที //Threading ทำให้ chrome กิน ram หนักมาก จนทำให้ browser ค้าง
# *26 แก้แล้วเกิดจาก ใช้ตัวแปรผิด ลืมใช้ตัวแปรที่เก็บค่าที่ลบคำแล้ว แต่ใช้ค่าเดิมไปเติม (สำนักงานใหญ่) จึงทำให้คนที่ให้ชื่อที่มีคำว่า "(สำนักงานใหญ่)" จะได้รับการเพิ่มคำว่า "(สำนักงานใหญ่)" ทำให้เบิ้ล //คำว่า สำนักงานใหญ่ เบิ้ล
# *27 แก้แล้ว // ลูกค้าขอใบกำกับแต่ให้คำว่า สาขาย่อย แต่ไม่มีชื่อสาขา และไม่มีรหัสสาขา แต่code ให้ผลลัพธ์ว่า (สาขาnan)
# *28 เพิ่ม Bot Status ว่ากำลังทำไรอยู่
# TODO29 เพิ่มช่องหมาเหตุจากผู้ซื้อ และ บันทึก
# *30 ปรับการทำงานให้เข้ากับ SMCO v6.2 อันเดิมคือ 6.1.1
# *31 แก้แล้ว//เพิ่มหน่วงเวลาให้ตอนกดแอดลูกค้าดูเหมือนว่า element ที่แอดลูกค้า มันจะขึ้นมาช้า locator มันเจอ แต่ กดไม่ได้ ซึ่งcodeผมมันสั่งให้กดไวไป = กับว่า การใช้ wait elment โผล่ กับ clickable element โผล่มันจะไวกว่า ต้องใช้อะไรที่ช้ากว่านั้นก็คือ clickable
# !32 ทำ auto ตอนเริ่ม phase2 แต่ตอนนี้มีปัญหา error data type ถ้าเอาตัวauto ไปใช้ ใน final whileloop
# !!33 ใน phase2 ก่อน final loop จะต้องเช็คก่อนว่าเข้า final ได้ไหม โดยการเช็ค "ราคารวมก่อนหักseller voucher"  ว่ามีค่าตรงกับ '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[2]/div/div/div/div/span[1]' หรือไม่ ถ้าไม่ตรงให้ finalloop ไม่ต้องทำงานแต่จะกด esc ย้อนกลับไปหน้าเก่า
# *34 แก้แล้วหายแล้ว//แต่ยังบัคอยู่//แก้แล้ว//ตัว auto print bug ย้อนกลับหน้าเดิมไม่ได้
# *35 แก้แล้วใช้ได้//SMCO เอา Auto ออกทำให้ใช้ไม่ได้
# !36 ใช้หาใบกำกับได้ดีกว่า vatinfo สะอีก https://www.dataforthai.com/company/{เลข13หลัก}/
# !37 ใน log ด้านล่าง จะไม่ได้แยกการแสดงผลของ SHOPEE กับ LAZADA นะ


# เก็บข้อมูล
# รอให้ final pop-up poped up /html/body/div[16]/div[2]/div[6]
# หรือ
# กดปุ่ม รอจนกว่าปุ่มนี้จะกดได้ /html/body/div[16]/div[2]/button[1] then click
