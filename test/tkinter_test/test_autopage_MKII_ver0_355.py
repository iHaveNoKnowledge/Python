
from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
from tkinter import font
# from test_auto_cus_name_MKII import *
import pandas as pd

# * selenium
import time
import win32com.client as comclt
import re
import multiprocessing
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

import locale
from decimal import Decimal
locale.setlocale(locale.LC_ALL, 'en_us')


class MyApp:
    def __init__(self, root):
        self.root = root
        self.result = ""
        self.table_location = ""
        self.cus_order = StringVar(value="")
        self.tax_bool = BooleanVar(value=False)
        self.tax_num = StringVar(value="")
        self.is_tax = StringVar(value="")
        self.tax_branch = StringVar(value="")
        self.cus_name = StringVar(value="")
        self.cus_account_name = StringVar(value="")
        self.cus_address = ""
        self.cus_province = StringVar(value="")
        self.cus_district = StringVar(value="")
        self.cus_sub_district = StringVar(value="")
        self.cus_tel = StringVar(value="")
        self.cus_cur_status = StringVar(value="")
        self.cus_ship_cost = DoubleVar(value=0)
        self.cus_seller_voucher = DoubleVar(value=0)
        self.cus_purchase_time = StringVar(value="")
        self.bot = Bot_POS(self.root, self)
        self.create_main_window()
        self.get_dataframe()
        self.cus_arrow_btn = '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[2]'
        self.cusNameInput = '/html/body/span/span/span[1]/input'
        self.cusSearchSMCO = '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[7]/a'
        self.cusCreateBtn = '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[2]/button'
        self.cusNameLi1 = '/html/body/span/span/span[2]/ul/li'
        self.bot_state = BooleanVar(value=False)

    def create_main_window(self):
        self.root.geometry("1000x900+400+300")
        self.root.title("Autosamatic ver0.351")
        self.root.configure(bg="#444")

        # #* BG CANVAS ##################################################################################
        self.canvas = Canvas(self.root)
        self.canvas.configure(bg="#444")
        self.canvas.pack(fill="both", expand=True)
        # self.canvas.create_window((0, 0), window=self.entry_frame, anchor="nw")
        # #* Scrollbar For Root ##################################################################################
        self.root_scrollbar = Scrollbar(self.canvas, command=self.canvas.yview)
        self.root_scrollbar.pack(side=RIGHT, fill="y")
        self.canvas.configure(yscrollcommand=self.root_scrollbar.set)

        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        # #* FRAMES #####################################################################################################
        # > Frame1 Order Entry
        self.entry_frame = Frame(self.canvas, padx=5, pady=5, bg="#444")
        self.entry_frame.pack(pady=(10, 10))

        # > Frame2 Log Frame
        self.log_frame = Frame(self.canvas, bg="#444")
        self.log_frame.pack(side='bottom', pady=(0, 30))

        # > Frame3 ImportFile Status
        self.import_file_frame = Frame(self.canvas, bg="#444")
        self.import_file_frame.pack(anchor=W, padx=(0, 5), pady=(5, 0))

        # > Frame4 Customer Details
        self.order_details_frame = Frame(self.canvas, bg="#444", )
        self.order_details_frame.pack(anchor=W, padx=(0, 5), pady=(5, 0))

        # > Frame5 Products Lists
        self.products_list_frame = Frame(self.canvas, bg="#445")
        self.products_list_frame.pack(padx=(5, 5), pady=(5, 5), fill=X)

        # > Frame6 Margetplace(MP) Products Lists
        self.mp_products_list_frame = Frame(self.canvas, bg="#444")
        self.mp_products_list_frame.pack(padx=(5, 5), pady=(5, 5), fill=X)

        # Create widgets in the main window
        self.create_widgets()

    def measure_text(self, text):
        return font.Font().measure(str(text).strip())

    def row_header_maker(self, list_of_cols):

        # สร้าง header
        self.list_of_cols = list_of_cols
        self.colspan_amount = [1, 19, 2, 2, 2, 2]
        self.cols_location = [0, 1, 21, 23, 25, 27]
        self.cols_width = [5, 112, 10, 10, 10, 10]
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
                row=0, column=self.cols_location[idx], columnspan=self.colspan_amount[idx])
            entry.configure(state="readonly")

    def create_widgets(self):
        # * > search order component
        # >> Labels
        self.inp1_label_order = Label(
            self.entry_frame, text="Order: ", bg="#FFF", width=10)
        self.inp1_label_order.grid(row=0, column=0, padx=5)
        # >> Inputs
        self.entered_order = StringVar()
        self.inp1_order_input = Entry(
            self.entry_frame, textvariable=self.entered_order, width=50)
        self.inp1_order_input.grid(row=0, column=2)
        # >> Buttons
        self.inp1_search_btn = Button(
            self.entry_frame, text="Start", bg="#747474", command=self.search, width=10)
        self.inp1_search_btn.grid(row=0, column=4, padx=5)

        # * > ExportFile location display component
        self.display_location_label = Label(
            self.import_file_frame, text=f"File located: ")
        self.display_location_label.grid(row=0, column=0, padx=(5, 0))
        self.display_location_result = Label(
            self.import_file_frame, text=f"ยังไม่เลือก Import File")
        self.display_location_result.grid(row=0, column=1, padx=(5, 0))
        self.display_location_result_btn = Button(
            self.import_file_frame, text=f"ใส่ Import File", command=self.select_excel)
        self.display_location_result_btn.grid(row=0, column=2, padx=(5, 0))

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
        self.label_is_tax.grid(row=2, column=2, padx=(5, 0), sticky=W)
        # >> Value display
        self.display_is_tax = Label(
            self.order_details_frame, width=12,  borderwidth=0, textvariable=self.is_tax, foreground="#000000", background="#fff")
        self.display_is_tax.grid(row=2, column=3, padx=(1, 0), sticky=W)

        # * > Tax Number display component
        # >> Labels
        self.label_tax_number = Label(
            self.order_details_frame, text="เลขใบกำกับ: ", bg="#FFF")
        self.label_tax_number.grid(row=2, column=4, padx=(5, 0), sticky=W)
        # >> Value display
        self.display_tax_number = Entry(
            self.order_details_frame, width=15,  borderwidth=0, textvariable=self.tax_num, foreground="#000000", background="#fff", readonlybackground="white", state="readonly")
        self.display_tax_number.grid(row=2, column=5, padx=(1, 0), sticky=W)

        # * > Customer Name display component
        # >> Labels
        self.label_cus_name = Label(
            self.order_details_frame, text="ชื่อ: ", bg="#FFF", height=1)
        self.label_cus_name.grid(row=2, column=0, padx=(5, 0), pady=(2, 2), )
        # >> Value display
        self.display_cus_name = Entry(
            self.order_details_frame, width=40,  borderwidth=0, textvariable=self.cus_name, foreground="#000000", background="#fff", state="readonly")
        self.display_cus_name.grid(row=2, column=1, padx=(1, 0), sticky=W)

        # * > Customer Address display component
        # >> Labels
        self.label_cus_address = Label(
            self.order_details_frame, text="ที่อยู่: ", bg="#FFF", height=1,)
        self.label_cus_address.grid(row=3, column=0, padx=(5, 0), pady=(2, 2))
        # >> Value display
        self.display_cus_address = Text(
            self.order_details_frame, width=50, height=5, borderwidth=0, foreground="#000000", background="#fff", state="disabled")
        self.display_cus_address.grid(
            row=3, column=1, padx=(1, 0), columnspan=3, sticky=W)
        self.display_cus_address.tag_add("left", "1.0", "1.end")

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
        self.tree.configure(yscrollcommand=self.y_scrollbar.set)

        # * > Margetplace Products display Header
        headers = ['No.', 'สินค้าทั้งหมด', 'ราคาต่อชิ้น',
                   'จำนวน', 'ราคาขายสุทธิ', 'ราคารวมรีเบท']
        self.row_header_maker(headers)

        # * > Log windows component
        self.report_log = Text(self.log_frame, state=DISABLED, height=13)
        self.scrollbar = Scrollbar(
            self.log_frame, command=self.report_log.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.scrollbar.config()
        self.report_log.pack(side='bottom', fill=X)
        self.report_log.config(yscrollcommand=self.scrollbar.set)

        ## * Create DataSourceSelector instance ###########
        self.data_source_selector = DataSourceSelector(self.root, self)

    def reset_all_display(self):
        self.result = ""
        self.table_location = ""
        self.cus_order.set("")
        self.tax_bool.set(False)
        self.tax_num.set("")
        self.is_tax.set("")
        self.cus_name.set("")
        self.cus_address = ""
        self.update_address('')
        self.cus_province.set("")
        self.cus_district.set("")
        self.cus_sub_district.set("")
        self.cus_tel.set("")
        self.cus_cur_status.set("")
        self.cus_account_name.set("")
        self.display_is_tax.config(
            background="#FFF", foreground="#000", font='Chiller 10 normal')

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

    def select_excel(self):
        self.result = "Excel"
        print("Select Excel")
        self.table_location = filedialog.askopenfilename()
        self.display_location_result.config(
            text=f"{self.table_location.split('/')[-1]}")
        self.get_data_frame()
        print("Table Location:", self.table_location)
        self.update_log("แอดไฟล์")

    def f(self, d):
        return '{0:n}'.format(d)

    def get_data_frame(self):
        print("มีป่าวหว่า", self.table_location)
        self.file_path = self.table_location

        try:
            self.data_frame = pd.read_excel(self.file_path,
                                            dtype={
                                                'หมายเลขประจำตัวผู้เสียภาษี': str, 'รหัสไปรษณีย์.1': str, 'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี': str, 'จำนวน': int, 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ': float, 'โค้ดส่วนลดชำระโดยผู้ขาย': float, 'แขวง/ตำบล': str, 'ประเภทสาขา': str,
                                                'สาขาย่อย': str})

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
        except Exception as e:
            print(f"อะไรสักอย่างพัง {e}")

    def update_address(self, address):
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
        self.total_price += self.cus_ship_cost.get()
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

    def order_search(self, order,  on_complete):
        print("order_search ทำงาน")
        self.on_complete = on_complete
        self.order = order.strip()
        self.cus_order.set(order)
        differential_col_data = [
            'เลขอ้างอิง SKU (SKU Reference No.)', 'ชื่อสินค้า', 'ราคาขาย', 'จำนวน', 'ราคาขายสุทธิ', 'ส่วนลดจาก Shopee']
        non_differential_col_data = ['หมายเลขคำสั่งซื้อ', 'สถานะการสั่งซื้อ', 'โค้ดส่วนลดชำระโดยผู้ขาย', 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ',  'ประเภทใบกำกับภาษี', 'ชื่อ',
                                     'ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป', 'แขวง/ตำบล', 'เขต/อำเภอ.1', 'จังหวัด.1', 'รหัสไปรษณีย์.1', 'หมายเลขประจำตัวผู้เสียภาษี', 'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี', 'อีเมลสำหรับรับใบกำกับภาษี', 'ชื่อผู้ใช้ (ผู้ซื้อ)', 'จำนวนเงินทั้งหมด', 'วันที่ทำการสั่งซื้อ', 'โค้ดส่วนลดชำระโดย Shopee', 'รายละเอียดที่อยู่', 'ประเภทสาขา',
                                     'รหัสประจำสาขา']

        if self.order != "":
            if not self.data_frame[(self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order)].empty:
                # ? self.filter_data จะเป็นการทำComparisionให้เรียบร้อยแล้วคืน DataFrame ที่กรองแล้วทันที --------------------ไวกว่า
                self.filter_data = self.data_frame[(self.data_frame["หมายเลขคำสั่งซื้อ"]
                                                    == self.order)]
                # ? self.target_row เป็น การหา เอาคอล "หมายเลขคำสั่งซื้อ" ทั้งหมดมาตรวจแล้วคืนค่าเป็น Boolean เท่านั้น ---------ช้ากว่า
                self.target_row = self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order

                self.order_status = self.data_frame[self.target_row]['สถานะการสั่งซื้อ'].iloc[0]

                # *  ของมีอะไรบ้าง
                self.items = self.data_frame[differential_col_data][self.target_row].to_dict(
                    'records')
                self.nondistortedData = self.data_frame[self.target_row][non_differential_col_data].iloc[0].to_dict(
                )

                self.update_log(f"สินค้าที่มี")
                for row in self.items:
                    self.update_log(
                        f"SKU: {str(row['เลขอ้างอิง SKU (SKU Reference No.)'])} ชื่อสินค้า: {str(row['ชื่อสินค้า'])} ")
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
                        0, f"{str(row['เลขอ้างอิง SKU (SKU Reference No.)'])}: {str(row['ชื่อสินค้า'])}")
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
                self.cus_name.set(
                    re.sub(r'\s{2,}', " ", self.nondistortedData['ชื่อ'].strip().replace('\u200b', '')))
                # * ประเภทใบกำกับภาษี
                # * เลือก Column มาแสดงผล โดยการใช้ iloc[0]
                self.branch_type = str(self.nondistortedData['ประเภทสาขา'])
                if pd.isna(self.data_frame[self.target_row]['หมายเลขประจำตัวผู้เสียภาษี'].iloc[0]):
                    self.tax_bool.set(False)
                    self.is_tax.set("ไม่ขอใบกำกับ")
                    self.display_is_tax.config(
                        background="#6ec7ff", foreground="#000", font='Chiller 10 normal')
                    self.tax_num.set("ไม่มี")

                else:
                    if self.branch_type == "สำนักงานใหญ่" or self.branch_type == "สาขาย่อย":
                        self.tax_bool.set(True)
                        self.is_tax.set("ขอใบกำกับ")
                        self.display_is_tax.config(
                            background="#ff0000", foreground="#FFF", font='Chiller 13 bold')
                        self.tax_num.set(
                            self.nondistortedData['หมายเลขประจำตัวผู้เสียภาษี'])
                    else:
                        self.tax_bool.set(True)
                        self.is_tax.set("ไม่ขอแต่มีเลข")
                        self.display_is_tax.config(
                            background="#ff9e36", foreground="#FFF", font='Chiller 13 bold')
                        self.tax_num.set(
                            self.nondistortedData['หมายเลขประจำตัวผู้เสียภาษี'])

                # * แสดงผล
                # print("ใบกำกับ?", self.tax_bool)
                # self.address = self.filter_data.iat[0, 59]
                self.address = self.nondistortedData['รายละเอียดที่อยู่']
                # print("ข้อความ", self.address)
                self.cleaned_address = f"""{self.get_pure_address(
                    self.clean_address(self.address))} {self.nondistortedData['แขวง/ตำบล']} {self.nondistortedData['เขต/อำเภอ.1']} {self.nondistortedData['จังหวัด.1']} {self.nondistortedData['รหัสไปรษณีย์.1']}"""
                if "กรุงเทพ" in self.cleaned_address:
                    self.cleaned_address = self.cleaned_address.replace(
                        "จังหวัด", '')
                # print("Addressที่คลีนแล้ว: ", self.cleaned_address)
                result = {"status": self.order_status,
                          "is_tax": self.tax_bool, "address": self.cleaned_address, "details": self.nondistortedData, "items": self.items}

                self.cus_account_name.set(
                    self.nondistortedData['ชื่อผู้ใช้ (ผู้ซื้อ)'].strip())
                print("self.cus_account_name: ", self.cus_account_name.get())
                try:
                    if not str(self.nondistortedData['แขวง/ตำบล']) == "nan":
                        print("ไม่มี nan: ", type(
                            self.nondistortedData['แขวง/ตำบล']))
                        self.update_address(
                            re.sub(r'\s{2,}', " ", self.cleaned_address.replace('\u200b', '')).strip())
                    else:
                        print("ถ้ามี nan")
                        self.update_address(re.sub(
                            r'\s{2,}', " ", self.nondistortedData['ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป'].strip().replace('\u200b', '')))
                except:
                    self.update_address('-')

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
                    self.cus_tel.set(
                        self.nondistortedData['หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี'])
                else:
                    self.cus_tel.set("1")

                self.cus_ship_cost.set(
                    self.nondistortedData['ค่าจัดส่งที่ชำระโดยผู้ซื้อ'])
                self.cus_seller_voucher.set(
                    self.nondistortedData['โค้ดส่วนลดชำระโดยผู้ขาย'])
                self.cus_purchase_time.set(
                    self.nondistortedData['วันที่ทำการสั่งซื้อ'])

                self.net_prices_list = []
                for item in self.items:
                    net_price = item['ราคาขายสุทธิ'] + \
                        item['ส่วนลดจาก Shopee']
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
                    f"สินค้ารวมค่าส่งหัก seller: {self.f((self.sum_price+self.cus_ship_cost.get())-self.cus_seller_voucher.get())}")

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

    def cusNameFixer4(self, name2, account_name):
        if re.search("[(,)]", name2):  # หาว่ามีให้แมชหรือป่าว
            nameParentheses = re.search("[(,)]", name2)
            # ใช้ method span() เพ่ือดึงค่า span โดยไอ span จะเป็นเลขบอกตำแหน่งของสิ่งที่เราหา (ทำไมไม่ทำเป็น attribute  555)
            parenthesesIndex = nameParentheses.span()
            slicingIndex = slice(parenthesesIndex[0])
            name2 = name2[slicingIndex]
            name2 = name2.strip()  # ตอนแรกๆไม่มีปัญหา หลังๆ มีปัญหา เรื่อง space ไม่เท่ากัน
        else:
            name2 = name2.strip()

        if len(name2.split()) == 1:
            name2 += " "+account_name

        print("มันมีชื่อว่า", name2)
        return name2

    def search(self):
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

        if self.search_thread.is_alive() or self.get_tabs_thread.is_alive():
            print("Thread ยังไม่ตาย")
            self.bot_state.set(False)
            print("ฆ่า Thread")
        self.bot_state.set(True)
        while self.bot_state.get():
            print("เริ่มThreadใหม่")
            self.search_thread.start()
            self.get_tabs_thread.start()
        # self.search_complete.self.wait1()
        # self.search_thread.join()

        # self.get_tabs_thread.join()

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
        self.app.get_data_frame()
        print("Table Location:", self.app.table_location)
        self.subwindow.destroy()
        self.app.update_log("เพิ่มไฟล์แล้ว")

    def on_close(self):
        self.subwindow.destroy()


class Bot_POS:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.setup_chrome()

    def setup_chrome(self):
        self.opt = Options()
        # opt2=Options()
        self.opt.add_experimental_option("debuggerAddress", "localhost:8989")
        self.driver = webdriver.Chrome(service=Service(
            r'C:\bin\chromedriver.exe'), options=self.opt)
        # self.driver = webdriver.Chrome(service=Service(
        #     ChromeDriverManager().install()), options=self.opt)

    def get_tabs(self):
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
                self.unique_titles.append(f"{item}{self.counter[item]-1}")
            else:
                self.counter[item] = 1
                self.unique_titles.append(item)
        # เอาList มารวมกัน
        self.merged_dict = dict(zip(self.unique_titles, self.value_list))

        print("มี tabs ไรบ้าง", self.merged_dict)
        self.operation_start()

    def operation_start(self):
        self.autofinal = False
        print("operation start!! ยังไม่มีไรจะใส่ใส่เป็น placeholderไว้ก่อน")
        self.wait1 = WebDriverWait(self.driver, 7200)
        # * เปลี่ยนไปtab shopee เพื่อเช็ค status
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

        # * ตรวจสอบ Status
        # รอให้ elemtn ที่อยู๋หลังสุดปรากดก่อน
        self.wait1.until(EC.visibility_of_element_located(
            (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[3]/div/div[2]/a/div[2]/div/div/div/div[5]/div/div')))
        # * ต้องใช้ try except เพราะ element ของ shopee มันดันแบ่งเป็นสองแบบหากมีสถานะ order ที่ต่างกัน แทนที่จะเขียนให้เหมือนกัน ยุ่งยากกว่าเดิม
        try:
            # สำหรับ หาข้อความ "ที่ต้องจัดส่ง" ต่อให้มี element ที่บรรจุคำว่า "จะถูกยกเลินใน x วัน" หรือ "การจัดส่งช้า" ตราบใดที่ข้างล่างมี ที่ต้องจัดส่ง จะมี class big-text เสมอ
            self.app.cus_cur_status.set(self.driver.find_element(
                By.CLASS_NAME, 'big-text').text)

        except:
            # สำหรับ หาข้อความ "ส่งสินค้าแล้ว", "ยกเลิกแล้ว", "สำเร็จ"
            self.app.cus_cur_status.set(self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[3]/div/div[2]/a/div[2]/div/div/div/div[3]/div[1]/span').text)
        # จะได้ element มา
        print("realtime_status_text", self.app.cus_cur_status.get())
        if self.app.cus_cur_status.get() == "ส่งสินค้าแล้ว":
            self.app.display_current_status.config(
                bg="#00ff11", fg="#000000")
        elif "ยกเลิก" in self.app.cus_cur_status.get():
            self.app.display_current_status.config(
                bg="#ff2b2b", fg="#FFF")

        self.is_status_true = self.app.order_status == self.app.cus_cur_status.get()
        if self.is_status_true:
            print(self.app.order_status == self.app.cus_cur_status.get())
            print("ตรง")
        else:
            print(self.app.order_status == self.app.cus_cur_status.get())
            print("ไม่ตรง แนะนำให้ไป Export File มาใหม่ จาก Link ที่ให้ด้านล่าง")
            print("https://seller.shopee.co.th/portal/sale/shipment?type=toship")

        # * เปลี่ยนไปtab SMCO0 เพื่อเช็ค ชื่อลูกค้า
        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])

        # * เปลี่ยน auto เป็น name
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/button').click()
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/div/div/a[2]').click()

        # * จับตาดูว่า ul เปิดอยู่ไหม
        self.is_ul_not_open = False if self.driver.find_elements(
            By.XPATH, '/html/body/span/span/span[2]/ul') else True
        # * conditional ternary like
        self.cus_search = self.app.tax_num.get() if self.app.tax_bool.get(
        ) else self.app.cusNameFixer4(self.app.cus_name.get(), self.app.cus_account_name.get())
        if self.is_ul_not_open:
            self.driver.find_element(By.XPATH, self.app.cus_arrow_btn).click()

            self.wait1.until(EC.visibility_of_element_located(
                (By.XPATH, self.app.cusNameInput)))

        self.driver.find_element(By.XPATH, self.app.cusNameInput).clear()
        self.driver.find_element(
            By.XPATH, self.app.cusNameInput).send_keys(self.cus_search)
        print("กรอกชื่อเสร็จ")
        self.wait_condition = self.driver.find_element(
            By.XPATH, self.app.cusNameLi1)
        print("มันทำไม", self.wait_condition.text)

        #! น่าสงสัย เป็นเหตุให้หน้าท้ายค้าง
        while True:
            self.wait1.until(EC.visibility_of_element_located(
                (By.XPATH, self.app.cusNameLi1)))
            self.wait_condition = self.driver.find_element(
                By.XPATH, self.app.cusNameLi1)
            print("เริ่ม", self.wait_condition)

            if self.wait_condition.text == "Searching...":
                continue
            elif self.wait_condition.text:
                print("get text ไม่ได้")
                pass

            self.wait1.until(EC.visibility_of_element_located(
                (By.XPATH, self.app.cusNameLi1)))
            self.wait_condition = self.driver.find_element(
                By.XPATH, self.app.cusNameLi1)
            if self.wait_condition.text == "No results found":
                print("Noresult found")
                # * ขอใบกำกับป่าว
                if self.app.tax_bool.get():
                    print("Tax_needed")
                    self.addTaxInvCustomer()
                    # กำลังทำ กำลังปรับปรุง ยังไม่เสร็จ
                    # result = self.wait1.until(EC.text_to_be_present_in_element()))
                else:
                    print("no_Tax_needed")
                    self.addNormalCustomer(self.cus_search)

                # self.wait1.until(EC.invisibility_of_element_located(By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div'))
                self.driver.switch_to.window(
                    self.merged_dict['SMCO :: เปิดการขาย'])
                self.driver.find_element(
                    By.XPATH, self.app.cusNameInput).clear()
                self.driver.find_element(
                    By.XPATH, self.app.cusNameInput).send_keys(self.cus_search)
                print("Re enter name after add")
            else:
                self.driver.switch_to.window(
                    self.merged_dict['SMCO :: เปิดการขาย'])
                break
            continue

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
        self.app.update_log("มันจบแค่นี้")
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
                    By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[1]/input')
                self.changePriceInput = self.changePriceInput.clear()
                self.changePriceInput = self.driver.find_element(
                    By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[1]/input').send_keys(self.app.cus_ship_cost.get())
                self.driver.find_element(
                    By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[2]/input').send_keys("62078")
                self.driver.find_element(
                    By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[3]/input').send_keys("ITcity@2017")
                self.driver.find_element(
                    By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[5]/div/textarea').send_keys("Online")

                self.driver.find_element(
                    By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[6]/a[1]').click()
            except Exception as err:
                print("ค่าขนส่งโดนข้าม")
                print(err)
        else:
            print("เงื่อนไขค่าขนส่ง มี Boolean เป็น False")

        self.autofinal = True
        while self.autofinal:
            print("เข้าloop ยัง")
            print("รอให้มันโผล่")
            while True:
                self.is_input_empty = self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[1]')
                self.is_final_displayed = self.driver.find_element(
                    By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]').is_displayed()
                if self.is_input_empty.text != "Select Customer" and self.is_final_displayed == False:
                    continue
                elif self.is_input_empty.text == "Select Customer" and self.is_final_displayed == False:
                    break
                elif self.is_input_empty.text != "Select Customer" and self.is_final_displayed == True:
                    # self.wait1.until(EC.visibility_of_element_located(
                    #     (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[8]/div/div[13]')))
                    # self.is_btn_disappeared = self.wait1.until(EC.invisibility_of_element_located(
                    #     (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[8]/div/div[13]')))
                    # if self.is_btn_disappeared:
                    # print("เริ่ม AutoFinal", self.is_btn_disappeared)
                    # while True:
                    # print("หน้าไร display")
                    # if self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span').is_displayed():
                    #     print("หน้า เดิม")

                    # elif self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]').is_displayed():
                    print("หน้า จ่ายตัง")
                    self.is_final_page2 = self.wait1.until(EC.text_to_be_present_in_element(
                        (By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]'), "Payment:"))
                    self.last_page = self.driver.find_element(
                        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]')
                    if self.last_page.text == "Payment:":
                        # Auto หน้าท้าย ทำได้ครั้งเดียว
                        self.is_final_page2 = self.wait1.until(EC.text_to_be_present_in_element(
                            (By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]'), "Payment:"))

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

                            # เลือก shopee
                            self.driver.find_element(
                                By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[2]/div/div/div[4]/a').click()

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

                            if self.app.cus_name.get():
                                self.driver.find_element(
                                    By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').send_keys(self.app.cus_name.get())
                            else:
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

                        self.is_previous_page = self.wait1.until(EC.invisibility_of_element_located(
                            (By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[1]/span[1]')))
                        if self.is_previous_page:
                            if bool(re.search(r"\w{5}\-\w{3}-\w{10}", self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[8]/div/div[1]/span').text)):
                                print("ไปหน้าสุดท้าย จบ loop")
                                break
                            elif self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/form/label'):
                                print("กลับมาหน้าเดิม")
                                continue
                    else:
                        print("จบสูตร")
                    self.autofinal = False
                    break

                break
            break
        print("จบ auto_last_page")
        self.autofinal = False

    def addNormalCustomer(self, cusname_adjusted):
        is_functionworking = False
        is_functionworking = True
        while is_functionworking:
            self.driver.switch_to.window(
                self.merged_dict['SMCO :: เปิดการขาย1'])

            self.element = self.driver.find_element(
                By.XPATH, self.app.cusSearchSMCO)
            self.element.click()  # กดแว่นขยาย
            self.btnElement = self.wait1.until(
                EC.visibility_of_element_located((By.XPATH, self.app.cusCreateBtn)))
            self.btnElement.click()  # create

            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').clear()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(cusname_adjusted)

            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').clear()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(cusname_adjusted)

            # self.driver.find_element(
            #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').clear()
            # self.driver.find_element(
            #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(self.app.cus_address)

            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').clear()
            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(1)

            self.driver.find_element(
                By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()
            self.wait1.until(EC.visibility_of_element_located(
                (By.XPATH, '/html/body/div[16]/div[2]/button[1]')))
            self.driver.find_element(
                By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()
            is_functionworking = False

    def addressExtractor(self, cusAddress):
        self.splited = cusAddress.split(",")
        return (self.splited)

    def addTaxInvCustomer(self):

        print("ชื่อลูกค้าเป็นไง", self.app.cus_name.get())
        self.cus_tax_name_edited = self.app.cus_name.get().replace('\u200b', '')
        # ** ลบคำที่ไม่ใช่ชื่อลูกค้า
        # * > ลบประเภทการจดทะเบียน ถ้าชื่อลูกค้าไม่มี บจก หรือ หจก เราก็จะไม่รู้ว่าลูกค้าให้ออกอะไร เลยทำให้ ไม่มีเงื่อนไขของคนที่ไม่ได้บอก
        if "หจก" in self.cus_tax_name_edited or "ห้างหุ้นส่วนจำกัด" in self.cus_tax_name_edited:
            print("เงื่อนไขชื่อใบกำกับใน if", self.cus_tax_name_edited)
            self.cus_tax_name_edited = self.cus_tax_name_edited.replace(
                "หจก.", "").replace("ห้างหุ้นส่วนจำกัด", "").strip()
            self.cus_tax_name_edited = f"ห้างหุ้นส่วนจำกัด {
                self.cus_tax_name_edited}"

        elif "บจก" in self.cus_tax_name_edited or "บริษัท" in self.cus_tax_name_edited or "จำกัด" in self.cus_tax_name_edited:
            print("เงื่อนไขชื่อใบกำกับใน elif", self.cus_tax_name_edited)
            self.cus_tax_name_edited = self.cus_tax_name_edited.replace(
                "บจก.", "").replace("บริษัท", "").replace("จำกัด", "").strip()
            self.cus_tax_name_edited = f"บริษัท {
                self.cus_tax_name_edited} จำกัด"

        # * > ลบประเภทสาขา
        if "สำนักงานใหญ่" in self.cus_tax_name_edited or "(สำนักงานใหญ่)" in self.cus_tax_name_edited:
            self.cus_tax_name_edited = self.cus_tax_name_edited.replace(
                "(สำนักงานใหญ่)", "").replace("สำนักงานใหญ่", "").strip()
        elif "(สาขา" in self.cus_tax_name_edited or "สาขา" in self.cus_tax_name_edited:
            self.cus_tax_name_edited = re.sub(
                r'\(สาขา.*\)', '', self.cus_tax_name_edited)
            self.cus_tax_name_edited = re.sub(
                r'\สาขา\d*', '', self.cus_tax_name_edited)

        if str(self.app.nondistortedData['ประเภทสาขา']) == 'สำนักงานใหญ่':
            self.app.tax_branch.set(self.app.nondistortedData['ประเภทสาขา'])
            self.cus_tax_name_edited = f"{
                self.app.cus_name.get()} ({self.app.tax_branch.get()})"
        elif self.app.branch_type == "สาขาย่อย":
            self.app.tax_branch.set(self.app.nondistortedData['รหัสประจำสาขา'])
            self.cus_tax_name_edited = f"{
                self.app.cus_name.get()} (สาขา{self.app.tax_branch.get()})"

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
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(f'{self.cus_tax_name_edited} Tax ID: {self.app.tax_num.get()}')

        self.driver.find_element(
            # nameEN
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').clear()
        self.driver.find_element(
            # nameEN
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(f'{self.cus_tax_name_edited} Tax ID: {self.app.tax_num.get()}')

        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[3]/input').clear()  # Identity ID
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[3]/input').send_keys(self.app.tax_num.get())  # Identity ID
        # [finAddress, finSubdistrict, finDistrict, finProvince, finZipCode] = self.addressExtractor(
        #     self.app.cus_address)  # ปัญหา บางเคสลูกค้าใส่ comma มามากกว่า 5 อัน ทำให้ error
        # self.finProvince = finProvince.strip().lstrip("จังหวัด")

        self.driver.find_element(
            # Address
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').clear()
        self.driver.find_element(
            # Address
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(self.app.cus_address)

        # # dropdown Country
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[9]/div[1]/div/span/span[1]/span/span[1]').click()
        # time.sleep(1)
        # # select thailand in dropdown
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[2]/ul/li[2]').click()

        # # province dropdown
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[9]/div[2]/div/span/span[1]/span/span[1]').click()
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()  # province input
        # self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
        #     self.app.cus_province.get().replace("จังหวัด", ""))  # province input
        # time.sleep(1.75)
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[1]/div/span/span[1]/span/span[1]').click()  # District drop
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()  # District
        # self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
        #     self.app.cus_district.get().replace("อำเภอ", "").replace("เขต", "").replace("ต.", ""))  # District
        # time.sleep(1.75)
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

        # # SubDistrict drop
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[3]/div/span/span[1]/span/span[1]').click()
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').clear()  # SubDistrict
        # self.driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
        #     self.app.cus_sub_district.get().replace("ตำบล", "").replace("แขวง", "").replace("ต.", ""))  # SubDistrict
        # time.sleep(1.75)
        # self.driver.find_element(
        #     By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

        # tel.
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').clear()
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(self.app.cus_tel.get())
        self.driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()
        # กดเองตรวจเอง
        self.wait1.until(EC.visibility_of_element_located(
            (By.XPATH, '/html/body/div[16]/div[2]/button[1]')))
        self.driver.find_element(
            By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()


if __name__ == "__main__":
    root = Tk()
    app = MyApp(root)
    # root.resizable(False, False)

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
# !12 ทำ input ID PASS
# !13 ยังแก้ไม่ได้ลูกสึก bigM ยังมีปัญหากับตรงนี้อยู่ อาจจะลองแก้ด้วย while True // searhลูกค้า ไม่เจอแล้วแอด มันมีโอกาสที่แอดแล้วไม่เสิชต่อ
# !14 ทำแยกตารางใหม่โดยใช้ layout แบบ Shopee //ตัวอักษรใน LOG หรือ ทำให้ Log อ่านและแยกแยะง่ายขึ้น ใช่ มันอ่านยากจริงๆ
# ?15 ตรวจดูแล้วยังไม่เจอสาเหตุ** ข้อความ "เพิ่มไฟล์แล้ว" แสดงผลไม่ถูกต้อง เนื่องจาก แสดงผล แม้ไม่ได้ แอดไฟล์จริงๆ
# *16 รายงาน มาว่าไม่เจอ แก้แล้วไม่รู้ใช้ได้ยัง // U200b display as ?
# !17 สินค้าบางประเภทต้องใส่ Variations ของมันด้วย ใน log จะได้แยกได้ เช่น หมึก มันจะไม่บอกสีใน ชื่อสินค้า แต่บอกใน variations
# *18 มีเลขลำดับบอกใน productslist
# !19 order เคสใบกำกับที่น่าสนใจ 23101524SPSNEC มีเลขมาแต่ไม่ได้ป็นบริษัท
# !20 order ไม่มี แต่ยังทำงานอยู่ เกิดจากการทำงานมันแยก thread กัน ต้องเอาผลลัพจากการเสิช มาเป็นเงื่อนไขว่าจะทำต่อหรือไม่
# todo 21 แก้แล้วรอทดสอบ//ใบกำกับไม่มีคำว่า ใน margetplace มีคำว่า (สำนักงานใหญ่) แต่พอแอดมาดันไม่มี
# todo 22 ทำได้แล้วรอทดสอบ //หน้าสุดท้ายกรอกเบิ้ล หากมีการยกเลิก หรือ รันบอททับ (ยากชิพไห) แต่หลักๆแก้ด้วย while True
# !23 พวกไม่ขอแต่มีเลข มันจะได้สาขา nan มา ต้องแก้ด้วย
# *24  เพราะลูกค้าไม่ได้บอกว่าเป็น หจก หรือ บจก ไง เลยทำเงื่อนไขไม่ได้ เพราะกูก็ไม่รู้ว่าต้องเขียนชื่อเป็นอะไร // 231021G8CWC1N5 คำว่า บริษัทไม่ขึ้น
# ?25 เดาว่าน่าจะเป็นที่ตัวแอดลูกค้าแก้แล้ว รอเทส //อาการค้างยังไม่หาย
# *26 แก้แล้ว//เวลาสินค้ามีมากกว่า 1 รายการ แล้วถัดไปมีน้อยลง element ที่แสดงรายการ ของ order ที่แล้วจะไม่หายไป
