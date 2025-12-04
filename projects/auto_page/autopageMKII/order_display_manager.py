"""
OrderDisplayManager - จัดการการแสดงผล order ที่ลูกค้าสั่งมา
รวม header, data rows, และ summary section (ค่าขนส่ง, voucher, ราคารวม)
"""
from tkinter import StringVar

import customtkinter as ctk
import pandas as pd
from customtkinter import CTkButton, CTkEntry


class OrderDisplayManager:
    """
    Class สำหรับจัดการการแสดงผล order ในรูปแบบตาราง
    รวมถึง header, data rows, และ summary section
    """

    def __init__(self, parent_frame, app_instance):
        """
        Initialize the order display manager

        Args:
            parent_frame: The CTkFrame where widgets will be placed (mp_products_list_frame)
            app_instance: Reference to MyApp instance for accessing variables
        """
        self.parent_frame = parent_frame
        self.app = app_instance

        # Widget storage
        self.header_widgets = []
        self.data_row_widgets = []  # List of lists, each inner list contains widgets for one row
        self.summary_widgets = []

        # Configuration for table layout
        self.colspan_amount = [1, 18, 2, 2, 2, 2, 2, 1, 1]
        self.cols_location = [0, 1, 19, 21, 23, 25, 27, 29, 30]
        self.cols_width = [35, 450, 80, 50, 80, 80, 60, 35, 35]

        # Track current row position
        self.current_data_row = 1  # Start after header (row 0)

    def create_header(self, column_headers):
        """
        สร้าง header row สำหรับตาราง
        Refactored from row_header_maker

        Args:
            column_headers: List of header names
        """
        # Clear existing header if any
        for widget in self.header_widgets:
            widget.destroy()
        self.header_widgets.clear()

        # Create header widgets
        for i, header_name in enumerate(column_headers):
            header_widget = CTkEntry(
                self.parent_frame,
                text_color="#000000",
                fg_color="#fff",
                width=int(self.cols_width[i]),
                height=14
            )
            header_widget.insert(0, header_name)
            header_widget.grid(
                row=0,
                column=self.cols_location[i],
                columnspan=self.colspan_amount[i],
                sticky='nsew'
            )
            header_widget.configure(state="readonly")
            self.header_widgets.append(header_widget)

    def create_data_rows(self, ordered_items: dict):
        """
        สร้าง data rows สำหรับแสดงรายการสินค้าที่สั่ง
        Refactored from row_table_data_maker

        Args:
            ordered_items: Dictionary containing order item data
        """
        # Clear existing data rows
        self.clear_data_rows()

        # State variables for adjust price inputs
        self.app.adjust_amount_vars = {}

        # Reset row counter
        self.current_data_row = 1

        # Storage for mimic list item states
        self.app.mimic_list_item_states = []

        # Create rows
        for item_idx, row in enumerate(ordered_items):
            row_widgets = []

            # Column 0: No. (Button for auto-add product)
            no_btn = CTkButton(
                self.parent_frame,
                width=int(self.cols_width[0]),
                height=14,
                text=str(item_idx + 1),
                fg_color="#81ed55",
                text_color="#1E1E1E",
                border_width=2,
                border_color="#969696",
                command=lambda idx=item_idx: self.app.auto_add_product_threaded(
                    self.app.correct_sku_pattern(
                        ordered_items[idx]['เลขอ้างอิง SKU (SKU Reference No.)']),
                    ordered_items[idx]['จำนวน'],
                    get_tabs=self.app.bot.get_tabs
                )
            )
            row_widgets.append(no_btn)

            # Column 1: Product name
            product_name_entry = CTkEntry(
                self.parent_frame,
                width=int(self.cols_width[1]),
                height=14
            )
            product_name_entry.insert(
                0,
                f"{' '.join(self.app.correct_sku_pattern(str(row['เลขอ้างอิง SKU (SKU Reference No.)'])))}"
                f"{' : ' + str(row['ชื่อตัวเลือก']) if not pd.isna(row['ชื่อตัวเลือก']) else ''} : {str(row['ชื่อสินค้า'])}"
            )
            row_widgets.append(product_name_entry)
            self.app.mimic_list_item_states.append(
                f"{str(row['เลขอ้างอิง SKU (SKU Reference No.)'])}")

            # Column 2: Price per unit
            price_unit_entry = CTkEntry(
                self.parent_frame,
                width=int(self.cols_width[2]),
                height=14
            )
            price_unit_entry.insert(0, f"{float(row['ราคาขาย']):,.2f}")
            row_widgets.append(price_unit_entry)

            # Column 3: Quantity
            qty_entry = CTkEntry(
                self.parent_frame,
                width=int(self.cols_width[3]),
                height=14
            )
            qty_entry.insert(0, int(row['จำนวน']))
            row_widgets.append(qty_entry)

            # Column 4: Total price
            total_price_entry = CTkEntry(
                self.parent_frame,
                width=int(self.cols_width[4]),
                height=14
            )
            total_price_entry.insert(0, f"{float(row['ราคาขายสุทธิ']):,.2f}")
            row_widgets.append(total_price_entry)

            # Column 5: Total rebate price
            total_rebate_entry = CTkEntry(
                self.parent_frame,
                width=int(self.cols_width[5]),
                height=14
            )
            total_rebate_entry.insert(
                0, f"{float(row['ราคาขายสุทธิ']) + float(row['ส่วนลดจาก Shopee']):,.2f}")
            row_widgets.append(total_rebate_entry)

            # Column 6: Adjust price input
            self.app.adjust_amount_vars[item_idx] = StringVar(value="0")
            adjust_price_entry = CTkEntry(
                self.parent_frame,
                width=int(self.cols_width[6]),
                height=14,
                textvariable=self.app.adjust_amount_vars[item_idx]
            )
            row_widgets.append(adjust_price_entry)

            # Column 7: OC Button (Overcharge - ขึ้นราคา)
            oc_btn = CTkButton(
                self.parent_frame,
                width=int(self.cols_width[7]),
                height=14,
                text='ขึ้น',
                fg_color="#ED1C24",
                hover_color="#9A0C04",
                text_color="#080808",
                border_width=2,
                border_color="#969696",
                command=lambda idx=item_idx: self.app.bot.smco_set_overcharge_product(
                    ordered_items[idx]['เลขอ้างอิง SKU (SKU Reference No.)'],
                    self.app.adjust_amount_vars[idx].get()
                )
            )
            row_widgets.append(oc_btn)

            # Column 8: DC Button (Discount - ลดราคา)
            dc_btn = CTkButton(
                self.parent_frame,
                width=int(self.cols_width[8]),
                height=14,
                text='ลง',
                fg_color="#00A2E8",
                text_color="#080808",
                border_width=2,
                border_color="#969696",
                command=lambda idx=item_idx:
                #     print(
                #     "DC Btn clicked for item:",
                #     ordered_items[idx]['เลขอ้างอิง SKU (SKU Reference No.)'],
                #     ordered_items[idx]['จำนวน']

                # )
                self.app.bot.smco_set_discount_product(
                    ordered_items[idx]['เลขอ้างอิง SKU (SKU Reference No.)'],
                    self.app.adjust_amount_vars[idx].get(),
                    ordered_items[idx]['จำนวน']
                )
            )
            row_widgets.append(dc_btn)

            # Grid all widgets in this row
            for col_idx, widget in enumerate(row_widgets):
                widget.grid(
                    row=self.current_data_row,
                    column=self.cols_location[col_idx],
                    columnspan=self.colspan_amount[col_idx]
                )

            # Store row widgets
            self.data_row_widgets.append(row_widgets)
            self.current_data_row += 1

    def create_summary_section(self, marketplace, products_list, nondistorted_data):
        """
        สร้าง summary section แสดงค่าขนส่ง, voucher, และราคารวม
        แทนที่การแสดงผลใน Treeview

        Args:
            marketplace: 'SHOPEE' or 'LAZADA'
            products_list: List of product dictionaries
            nondistorted_data: Original data containing voucher and total price info
        """
        # Clear existing summary
        self.clear_summary()

        # Calculate total price from products
        total_price = 0
        for product in products_list:
            price = product["ราคาขายสุทธิ"]
            shopee_rebate = product['ส่วนลดจาก Shopee']
            price_plusrebate = price + shopee_rebate
            total_price += price_plusrebate

        # Get shipping and voucher values
        ship_cost = self.app.cus_ship_cost.get()
        seller_voucher = self.app.cus_seller_voucher.get()

        # Start summary from current row position
        summary_start_row = self.current_data_row

        if marketplace == 'SHOPEE':
            # SHOPEE: ค่าขนส่ง, Seller Voucher, ราคาที่ต้องออก, Shopee Voucher, ลูกค้าจ่ายทั้งหมด

            # Row 1: ค่าขนส่ง
            total_price += ship_cost
            self._add_summary_row(
                summary_start_row,
                "ค่าขนส่ง",
                self._format_number(ship_cost)
            )

            # Row 2: Seller Voucher
            total_price -= seller_voucher
            self._add_summary_row(
                summary_start_row + 1,
                "Seller Voucher",
                "-" + self._format_number(seller_voucher)
            )

            # Row 3: ราคาที่ต้องออก
            self._add_summary_row(
                summary_start_row + 2,
                "ราคาที่ต้องออก",
                self._format_number(total_price),
                highlight=True
            )

            # Row 4: Shopee Voucher
            shopee_voucher = nondistorted_data[
                'โค้ดส่วนลดชำระโดย Shopee (เช่น โค้ดจากโปรแกรม ร้านโค้ดคุ้ม, โค้ดส่วนลด Shopee, โค้ดส่วนลด Shopee Mall)'] * -1
            self._add_summary_row(
                summary_start_row + 3,
                "Shopee Voucher",
                self._format_number(shopee_voucher)
            )

            # Row 5: ลูกค้าจ่ายทั้งหมด
            customer_total = nondistorted_data['จำนวนเงินทั้งหมด']
            self._add_summary_row(
                summary_start_row + 4,
                "ลูกค้าจ่ายทั้งหมด",
                self._format_number(customer_total),
                highlight=True
            )

        elif marketplace == 'LAZADA':
            # LAZADA: Seller Voucher, ราคาที่ต้องออก(Noขนส่ง), ค่าขนส่ง, ราคาที่ต้องออก(+ขนส่ง)

            # Row 1: Seller Voucher
            total_price -= seller_voucher
            self._add_summary_row(
                summary_start_row,
                "Seller Voucher",
                "-" + self._format_number(seller_voucher)
            )

            # Row 2: ราคาที่ต้องออก (No ขนส่ง)
            self._add_summary_row(
                summary_start_row + 1,
                "ราคาที่ต้องออก(Noขนส่ง)",
                self._format_number(total_price),
                highlight=True
            )

            # Row 3: ค่าขนส่ง
            self._add_summary_row(
                summary_start_row + 2,
                "ค่าขนส่ง",
                self._format_number(ship_cost)
            )

            # Row 4: ราคาที่ต้องออก (+ขนส่ง)
            total_with_ship = total_price + ship_cost
            self._add_summary_row(
                summary_start_row + 3,
                "ราคาที่ต้องออก(+ขนส่ง)",
                self._format_number(total_with_ship),
                highlight=True
            )

    def _add_summary_row(self, row_num, label_text, value_text, highlight=False):
        """
        เพิ่ม summary row เดียว

        Args:
            row_num: Row number in grid
            label_text: Text for label
            value_text: Text for value
            highlight: Whether to highlight this row (for important totals)
        """
        # Determine colors
        if highlight:
            label_bg = "#FFD700"  # Gold for important rows
            value_bg = "#FFD700"
            text_color = "#000000"
        else:
            label_bg = "#E8F4F8"  # Light blue
            value_bg = "#FFFFFF"
            text_color = "#000000"

        # Label (spans first few columns)
        label_widget = CTkEntry(
            self.parent_frame,
            width=int(sum(self.cols_width[:6])),  # Span across first 6 columns
            height=14,
            fg_color=label_bg,
            text_color=text_color,
            border_width=1,
            border_color="#969696"
        )
        label_widget.insert(0, label_text)
        label_widget.configure(state="readonly")
        label_widget.grid(
            row=row_num,
            column=0,
            columnspan=sum(self.colspan_amount[:6]),
            sticky='ew'
        )
        self.summary_widgets.append(label_widget)

        # Value (spans remaining columns)
        value_widget = CTkEntry(
            self.parent_frame,
            width=int(sum(self.cols_width[6:])),
            height=14,
            fg_color=value_bg,
            text_color=text_color,
            border_width=1,
            border_color="#969696"
        )
        value_widget.insert(0, value_text)
        value_widget.configure(state="readonly")
        value_widget.grid(
            row=row_num,
            column=self.cols_location[6],
            columnspan=sum(self.colspan_amount[6:]),
            sticky='ew'
        )
        self.summary_widgets.append(value_widget)

    def _format_number(self, number):
        """
        Format number with thousand separators

        Args:
            number: Number to format

        Returns:
            Formatted string
        """
        return '{0:n}'.format(number)

    def clear_all(self):
        """ลบ widgets ทั้งหมด (header, data rows, summary)"""
        self.clear_header()
        self.clear_data_rows()
        self.clear_summary()

    def clear_header(self):
        """ลบ header widgets"""
        for widget in self.header_widgets:
            widget.destroy()
        self.header_widgets.clear()

    def clear_data_rows(self):
        """ลบ data row widgets (เก็บ header ไว้)"""
        for row_widgets in self.data_row_widgets:
            for widget in row_widgets:
                widget.destroy()
        self.data_row_widgets.clear()
        self.current_data_row = 1  # Reset to start after header

    def clear_summary(self):
        """ลบ summary section widgets"""
        for widget in self.summary_widgets:
            widget.destroy()
        self.summary_widgets.clear()
