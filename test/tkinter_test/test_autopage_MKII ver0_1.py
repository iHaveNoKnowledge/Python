
from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
# from test_auto_cus_name_MKII import *
import pandas as pd
import re


class MyApp:
    def __init__(self, root):
        self.root = root
        self.result = ""
        self.table_location = ""
        self.tax_bool = bool
        self.create_main_window()
        self.get_dataframe()
        

    def create_main_window(self):
        self.root.geometry("800x600+400+300")
        self.root.title("Autosamatic")
        self.root.configure(bg="#444")

        # #* FRAMES #####################################################################################################
        # > Frame1 Order Entry
        self.entry_frame = Frame(self.root, padx=5, pady=5, bg="#444")
        self.entry_frame.pack()

        # > Frame2 Log Frame
        self.log_frame = Frame(self.root, bg="#444")
        self.log_frame.pack(side='bottom', pady=(0, 30))

        # > Frame3 ImportFile Status
        self.import_file_frame = Frame(self.root, bg="#444")
        self.import_file_frame.pack(anchor=W, padx=(0, 5), pady=(5, 0))

        # > Frame4 Customer Details
        self.order_details_frame = Frame(self.root, bg="#444", )
        self.order_details_frame.pack(anchor=W, padx=(0, 5), pady=(5, 0))

        # Create widgets in the main window
        self.create_widgets()

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
            self.entry_frame, text="ค้นหา", bg="#747474", command=self.search, width=10)
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
            self.order_details_frame, text="Current Order: ", bg="#FFF")
        self.label_current_order.grid(row=1, column=0, padx=(5, 0))
        self.display_current_order = Text(
            self.order_details_frame, width=30, height=self.order_details_frame.winfo_height()+0, state=DISABLED,  borderwidth=0)
        self.display_current_order.grid(row=1, column=1, padx=(5, 0))

        # * > Is Tax?? display component
        # >> Labels
        self.label_is_tax = Label(
            self.order_details_frame, text="ใบกำกับ: ", bg="#FFF")
        self.label_is_tax.grid(row=1, column=2, padx=(5,0))
        self.display_is_tax = Text(
            self.order_details_frame, width=5, height=self.order_details_frame.winfo_height()+0, state=DISABLED,  borderwidth=0)
        self.display_is_tax.grid(row=1, column=3, padx=(5, 0))

        # * > Log windows component
        self.report_log = Text(self.log_frame, state=DISABLED)
        self.scrollbar = Scrollbar(
            self.log_frame, command=self.report_log.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.scrollbar.config()
        self.report_log.pack(side='bottom', fill=X)
        self.report_log.config(yscrollcommand=self.scrollbar.set)

        ## * Create DataSourceSelector instance ###########
        self.data_source_selector = DataSourceSelector(self.root, self)

    def update_log(self, update_txt):
        self.update_txt = update_txt
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

    def get_data_frame(self):
        print("มีป่าวหว่า", self.table_location)
        self.file_path = self.table_location

        try:
            self.data_frame = pd.read_excel(self.file_path)
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

    def order_search(self, order):
        self.order = order
        differential_col_data = [
            'เลขอ้างอิง SKU (SKU Reference No.)', 'ชื่อสินค้า', 'ราคาขาย', 'จำนวน', 'ราคาขายสุทธิ']
        non_differential_col_data = ['หมายเลขคำสั่งซื้อ', 'สถานะการสั่งซื้อ', 'โค้ดส่วนลดชำระโดยผู้ขาย', 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ',  'ประเภทใบกำกับภาษี', 'ชื่อ',
                                     'ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป', 'แขวง/ตำบล', 'เขต/อำเภอ', 'จังหวัด', 'รหัสไปรษณีย์', 'หมายเลขประจำตัวผู้เสียภาษี', 'หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี', 'อีเมลสำหรับรับใบกำกับภาษี']
        
        #? self.filter_data จะเป็นการทำComparisionให้เรียบร้อยแล้วคืน DataFrame ที่กรองแล้วทันที --------------------ไวกว่า
        self.filter_data = self.data_frame[(self.data_frame["หมายเลขคำสั่งซื้อ"]
                                            == self.order)]
        #? self.target_row เป็น การหา เอาคอล "หมายเลขคำสั่งซื้อ" ทั้งหมดมาตรวจแล้วคืนค่าเป็น Boolean เท่านั้น ---------ช้ากว่า
        self.target_row = self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order
        
        self.order_status = self.data_frame[self.target_row]['สถานะการสั่งซื้อ'].iloc[0]
        
        print("สถานะOrder: ", self.order_status)
        # * ############# หาค่าจาก ตาราง ###############################
        # * ประเภทใบกำกับภาษี
        # * เลือก Column มาแสดงผล โดยการใช้ iloc[0]
        self.tax_bool
        if self.data_frame[self.target_row]['ประเภทใบกำกับภาษี'].iloc[0] == 'Personal':
            self.tax_bool = False
        else:
            self.tax_bool = True

        # *  ของมีอะไรบ้าง
        self.items = self.data_frame[differential_col_data][self.target_row].to_dict('records')
        
        # * แสดงผล
        self.nondistortedData = self.data_frame[self.target_row][non_differential_col_data].iloc[0].to_dict()
        print("พวกค่าแต่ละrowไม่บิดเบี้ยว: ",
                self.nondistortedData, 'ประเภทข้อมูล',type(self.nondistortedData))
        print("เลือกพวกค่าที่มันบิดเบี้ยวแต่ละrow: ", self.items)
        # print("ใบกำกับ?", self.tax_bool)
        self.address = self.filter_data.iat[0, 15]
        # print("ข้อความ", self.address)
        self.cleaned_address = self.clean_address(self.address)
        # print("Addressที่คลีนแล้ว: ", self.cleaned_address)
        result = {"status": self.order_status,
                    "is_tax": self.tax_bool, "address": self.cleaned_address, "details":self.nondistortedData, "items":self.items}

        print("ขอใบกำกับไหม? ", result["is_tax"])
        print("ที่อยู่ ", result["address"])
        return result

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

    def search(self):
        self.search_query = self.entered_order.get()
        print("search() ทำงานและได้ผลลัพธ์: ", self.search_query)
        self.entered_order.set("")
        self.report_log.config(state=NORMAL)
        self.report_log.insert(END, self.search_query + "\n")
        self.report_log.config(state=DISABLED)
        self.display_current_order.config(state=NORMAL)
        self.display_current_order.delete("1.0", "end")
        self.display_current_order.insert("1.0", self.search_query.strip())
        self.display_current_order.config(state=DISABLED)
        self.order_search(self.search_query)

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


if __name__ == "__main__":
    root = Tk()
    app = MyApp(root)
    root.mainloop()
