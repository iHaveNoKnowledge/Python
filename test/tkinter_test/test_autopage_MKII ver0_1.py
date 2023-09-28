
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
        # > Frame1
        self.entry_frame = Frame(self.root, padx=5, pady=5, bg="#444")
        self.entry_frame.pack()

        # > Frame2
        self.log_frame = Frame(self.root, bg="#444")
        self.log_frame.pack(side='bottom', pady=(0,30))


        # Create widgets in the main window
        self.create_widgets()
        

    def create_widgets(self):
        # > Labels
        self.inp1_label_order = Label(self.entry_frame, text="Order: ", bg="#FFF", width=10)
        self.inp1_label_order.grid(row=0,column=0, padx=5)
        
        self.display_location_label = Label(text=f"File located: ")
        self.display_location_label.pack(side="left", padx=(20, 5), pady=(0, 100))
        self.display_location_result = Label(text=f"ยังไม่มีไฟล์ที่เลือก")
        self.display_location_result.pack(side="left", pady=(0, 100))

        # > Inputs
        self.entered_order = StringVar()
        self.inp1_order_input = Entry(self.entry_frame, textvariable=self.entered_order, width=50)
        self.inp1_order_input.grid(row=0,column=2)

        # > Buttons
        self.inp1_search_btn = Button(self.entry_frame, text="ค้นหา", bg="#747474", command=self.search, width=10)
        self.inp1_search_btn.grid(row=0,column=4, padx=5)

        # > Log windows
        self.report_log = Text(self.log_frame, state=DISABLED)
        self.scrollbar= Scrollbar(self.log_frame, command=self.report_log.yview)
        self.scrollbar.pack(side="right", fill="y") 
        self.scrollbar.config()
        self.report_log.pack(side='bottom', fill=X)
        self.report_log.config(yscrollcommand=self.scrollbar.set)

        # Create DataSourceSelector instance
        self.data_source_selector = DataSourceSelector(self.root, self)
        
        
    def get_data_frame(self):
        print("มีป่าวหว่า", self.table_location)
        self.file_path = self.table_location
        
        try:
            self.data_frame = pd.read_excel(self.file_path)
            if self.data_frame.empty :
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
        print("Order is: ", self.order)
        self.filter_data = self.data_frame[(self.data_frame["หมายเลขคำสั่งซื้อ"]
                                == self.order)]
        
        # target_row เป็น row ที่เลือกจากเลข Order ที่รับเข้ามา
        self.target_row = self.data_frame["หมายเลขคำสั่งซื้อ"] == self.order
        if self.data_frame[self.target_row]['สถานะการสั่งซื้อ'].iloc[0] == "ที่ต้องจัดส่ง":
            print("boolfilter มี type เป็นไร", type(self.target_row))
            print("สถานะOrder: ", self.data_frame[self.target_row]['สถานะการสั่งซื้อ'].iloc[0])
            # * ############# หาค่าจาก ตาราง ###############################
            # * ประเภทใบกำกับภาษี
            # * เลือก Column มาแสดงผล โดยการใช้ iloc[0]
            self.tax_bool
            if self.data_frame[self.target_row]['ประเภทใบกำกับภาษี'].iloc[0] == 'Personal':
                self.tax_bool = False
            else:
                self.tax_bool = True

            # *  ของมีอะไรบ้าง
            self.products_list = self.data_frame[self.target_row].to_dict(
            )
            # * แสดงผล
            print("ใบกำกับ?", self.tax_bool)
            self.address = self.filter_data.iat[0,15]
            print("ข้อความ",self.address)
            self.cleaned_address = self.clean_address(self.address)
            print("Addressที่คลีนแล้ว: ",self.cleaned_address)

        else :
            print("Orderนี้ ขอยกเลิกมานะ")
            
    def clean_duplicate_parts(self, address):
        # ใช้ regex เพื่อค้นหาและลบคำย่อที่มีส่วนที่มากกว่าคำเต็ม
        pattern = r'(ต\..+?)\s+?(ตำบล|อ\..+?)\s+?(อำเภอ|จ\..+?)\s+?(จังหวัด)'
        
        matches = re.findall(pattern, address)
        if matches:
            cleaned_address = address
            for match in matches:
                full_word, abbr_word1, abbr_word2, abbr_word3 = match
                if len(full_word) > len(abbr_word1):
                    cleaned_address = cleaned_address.replace(abbr_word1, full_word)
                if len(full_word) > len(abbr_word2):
                    cleaned_address = cleaned_address.replace(abbr_word2, full_word)
                if len(full_word) > len(abbr_word3):
                    cleaned_address = cleaned_address.replace(abbr_word3, full_word)
        else:
            cleaned_address = address
        print("After_Clean_dup: ",cleaned_address)
        return cleaned_address


    def clean_address(self, address):
        

        keywords = ["เขต", "แขวง", "ต.", "ตำบล", "อ.", "อำเภอ", "จ.", "จังหวัด"]

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

    def search(self):
        self.search_query = self.entered_order.get()  
        print("search() ทำงานและได้ผลลัพธ์: ",self.search_query)
        self.entered_order.set("")
        self.report_log.config(state=NORMAL)
        self.report_log.insert(END, self.search_query + "\n")
        self.report_log.config(state=DISABLED)
        self.order_search(self.search_query)


    def open_subwindow(self):
        self.data_source_selector.create_subwindow()
        
    def get_dataframe(self):
        print("เรียกหา dataframe")

    


## สำหรับเลือกที่มาของแหล่งข้อมูล
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
        
        

        self.api_btn = Button(self.subwindow, text="API", command=self.select_api)
        self.api_btn.pack(side='left', expand=TRUE, fill="both")
        self.excel_btn = Button(self.subwindow, text="Excel", command=self.select_excel)
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
        self.app.display_location_result.config(text=f"{self.app.table_location}")
        self.app.get_data_frame()
        print("Table Location:", self.app.table_location)
        self.subwindow.destroy()

    def on_close(self):
        self.subwindow.destroy()


if __name__ == "__main__":
    root = Tk()
    app = MyApp(root)
    root.mainloop()
