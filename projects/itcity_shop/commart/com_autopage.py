import tkinter as tk
from tkinter import filedialog
from customtkinter import *
import threading
import time
import json
import re

from modules.selenium_webdriver import ChromeDriver
from modules.supabase_client import Supabase_client


class MainApp:
    def __init__(self, root):
        self.root = root
        self.data_file_dir = tk.StringVar(value="")
        self.file_name = tk.StringVar(value="ไม่มีไฟล์")
        self.sku = tk.StringVar(value="")
        self.set_num = tk.StringVar(value="")
        self.current_task = None
        self.stop_event = threading.Event()
        self.data_table = {}
        self.is_bot_working = tk.BooleanVar(value=False)
        self.bot_status = tk.StringVar(value="ไม่ได้ทำงาน")
        self.Supabase_client = Supabase_client(self, root)

        # * ตัวแปรสำหรับจัดการ inputs
        self.cus_order_name = tk.StringVar(value="")
        self.cus_fname = tk.StringVar(value="")
        self.cus_lname = tk.StringVar(value="")
        self.cus_is_fulltax = tk.BooleanVar(value=False)
        self.cus_is_hq = tk.BooleanVar(value=False)
        self.cus_display_name = tk.StringVar(value="")
        self.cus_tax_num = tk.StringVar(value="")
        self.cus_address = ""
        self.cus_province = tk.StringVar(value="")
        self.cus_district = tk.StringVar(value="")
        self.cus_sub_district = tk.StringVar(value="")
        self.cus_zip_code = tk.StringVar(value="")
        self.cus_tel = tk.StringVar(value="")
        self.cus_purchased_products = []
        self.cus_purchased_premiums = []
        self.cus_remark = ""
        self.cus_tax_name = tk.StringVar(value="")
        self.cus_tax_type = tk.StringVar(value="")

        # * functions start here
        self.create_main_window()

    def reset_all_values(self):
        self.cus_order_name.set("")
        self.cus_fname.set("")
        self.cus_lname.set("")
        self.cus_is_fulltax.set(False)
        self.cus_is_hq.set(False)
        self.cus_display_name.set("")
        self.cus_tax_num.set("")
        self.update_textbox_widgets(
            "", self.address_display, 'cus_address')
        self.cus_province.set("")
        self.cus_district.set("")
        self.cus_sub_district.set("")
        self.cus_zip_code.set("")
        self.cus_tel.set("")
        self.update_item_display(widget="product")
        self.update_item_display(widget="premium")
        self.update_item_display(widget="remark")
        # self.update_textbox_widgets("", ยังไม่มี widget, self.cus_remark)

    def update_bot_status(self, is_bot_working=False):
        self.is_bot_working.set(False)
        self.status_display.configure(fg_color="#70ff29")
        self.bot_status.set("ไม่ได้ทำงาน")

        if is_bot_working:
            self.is_bot_working.set(True)
            self.status_display.configure(fg_color="#ff2929")
            self.bot_status.set("กำลังทำงาน")

    def resetInput(self):
        self.sku.set("")
        self.set_num.set("")

    def data_formatter_json(self, data_input):
        self.result
        self.result = re.sub(
            r'\s{2,}', " ", data_input.strip().replace('\u200b', '')).strip()

    def kill_remaining_threads(self):
        if self.current_task and self.current_task.is_alive():
            self.stop_event.set()
            self.current_task.join()

    def input_receiver(self, input):
        self.input_data = input
        try:
            self.input_data = json.loads(input)
        except Exception as e:
            print("แปลงเป็น dict ไม่สําเร็จ: ")
            print("START: ", e, "END")
            #! อัพเดท status
            raise

        if self.input_data:
            print("input: ", self.input_data)
            self.update_from_qr(self.input_data)
        else:
            print("ไม่ได้ใส่ค่า input", self.input_data)

    def input_receiver2(self, input):
        self.input_data = input
        if self.input_data:
            self.order_details = self.Supabase_client.get_order(input)
            print("input: ", self.order_details)
            self.update_from_qr2(self.order_details)
            self.input_qr.set("")
        else:
            # PopUp("Warning", "")
            raise Exception("ไม่ได้ใส่ค่า order", self.input_data)

    # * my_function เป็น function ที่มีการรอ ใช้ทดสอบ Thread

    def my_function(self):
        print("Starting function")
        try:
            for i in range(10):
                if self.stop_event.is_set():
                    print("Function was stopped")
                    return
                time.sleep(1)
                print(f"Running... {i+1}/10")
        except Exception as e:
            print(f"Error occurred: {e}")
            return
        print("Function completed")

    def operation_start(self):
        self.update_bot_status(True)
        self.ChromDriver = ChromeDriver(app=self,
                                        update_bot_stat_fn=self.update_bot_status
                                        )
        print('ChromDriver is running.')

    def start_task(self, input={}):
        # * ล้าง inputเก่าก่อน
        self.reset_all_values()

        # * รับ input เข้า program
        print("input type: ", type(input))
        self.input_receiver2(input)

        # * จัดการ Thread
        if self.current_task and self.current_task.is_alive():
            self.stop_event.set()
            self.current_task.join()
            print("ทำการรวม Thread")
            print("รวมThreadแล้ว จำนวนThread: ", threading.active_count())
            print("threads: ", threading.enumerate())

        self.stop_event.clear()
        self.current_task = threading.Thread(target=self.operation_start)
        self.current_task.start()
        print("เริ่มการทำงาน")

    def update_log(self, update_txt=""):
        self.update_txt = update_txt
        self.log_display.config(state=tk.NORMAL)
        self.log_display.insert(tk.END, self.update_txt + "\n")
        self.log_display.config(state=tk.DISABLED)

    def clear_log(self):
        print('เคลีย!!')
        self.log_display.config(state=tk.NORMAL)
        self.log_display.delete("1.0", tk.END)
        self.log_display.config(state=tk.DISABLED)

    def on_start_button_click(self, input_qr=""):

        print("จำนวนThread: ", threading.active_count())
        print("threads: ", threading.enumerate())
        thread = threading.Thread(target=self.start_task, args=(input_qr, ))
        thread.start()

    def create_widgets(self):
        # * started widgets variables
        self.input_qr = tk.StringVar()

        # *** widgets /////////////////////////////////////////////
        # ** variables for setting
        self.pady = (0, 16)

        # ** frame_top widgets ************************************
        # * QR input component ////////////
        self.qr_display = CTkLabel(
            self.frame_top, text="QR Input", width=70, anchor=tk.W)
        self.qr_display.grid(row=0, column=0, padx=(0, 0), pady=self.pady)

        self.qr_input = CTkEntry(
            self.frame_top, width=180, textvariable=self.input_qr)
        self.qr_input.grid(row=0, column=1, pady=self.pady, sticky="w")

        self.qr_btn = CTkButton(self.frame_top, width=70, anchor=tk.W,
                                text="Start", command=lambda: self.on_start_button_click(self.input_qr.get()))
        self.qr_btn.grid(row=0, column=2, padx=(
            0, 0), pady=self.pady, sticky="w")

        # * Order display component ////////////
        self.order_label = CTkLabel(
            self.frame_top, text="เลขที่คำสั่งซื้อ", width=70, anchor=tk.W)
        self.order_label.grid(row=0, column=3, padx=(10, 10), pady=self.pady)

        self.order_display = CTkEntry(
            self.frame_top,
            width=180,
            state="readonly",
            textvariable=self.cus_order_name
        )
        self.order_display.grid(row=0, column=4, padx=(1, 1), pady=self.pady)

        # * ชื่อลูกค้า cus_name component ///////////
        self.name_label = CTkLabel(
            self.frame_top, text="ชื่อออกบิล", width=70, anchor=tk.W)
        self.name_label.grid(row=1, column=0, padx=(0, 0))

        self.name_display = CTkEntry(
            self.frame_top, width=300, state="readonly", textvariable=self.cus_display_name)
        self.name_display.grid(row=1, column=1, padx=(0, 1))

        # * เลขผู้เสียภาษี cus_tax_num component ///////////
        self.tax_num_label = CTkLabel(
            self.frame_top, text="เลขผู้เสียภาษี", width=70, anchor=tk.W)
        self.tax_num_label.grid(row=1, column=3, padx=(10, 10))

        self.tax_num_display = CTkEntry(
            self.frame_top, width=180, state="readonly", textvariable=self.cus_tax_num)
        self.tax_num_display.grid(row=1, column=4, padx=(0, 1))

        # * Bot Status cus_tax_num component ///////////
        self.status_label = CTkLabel(
            self.frame_top, text="Status", width=70)
        self.status_label.grid(row=0, column=5, padx=(10, 0))

        self.status_display = CTkEntry(
            self.frame_top, width=150, state="readonly", textvariable=self.bot_status, fg_color="#70ff29",  text_color="#000")
        self.status_display.grid(row=0, column=6, sticky="w")

        # ** frame_1 widgets ************************************
        # * ที่อยู่ cus_address component ///////////
        self.address_label = CTkLabel(
            self.frame_1, text="ที่อยู่ ", width=70, anchor=tk.W)
        self.address_label.grid(row=0, column=0, padx=(
            0, 0), pady=(0, 5), sticky='nw')

        self.address_display = CTkTextbox(self.frame_1, width=300, height=100)
        self.address_display.insert("0.0", "Ready" + '\n')
        self.address_display.configure(state="disabled")
        self.address_display.grid(row=0, column=1, padx=(1, 0))

        # * รายละเอียดที่อยู่ ต อ เขต แขวง จ address_details components ///////////
        self.frame_1_1 = CTkFrame(master=self.frame_1)
        self.frame_1_1.grid(row=0, column=2, sticky='nw', padx=5)

        address_components_settings = [
            {"label": "จังหวัด", "position": {"row": 0, "column": 1},
                "variable": self.cus_province},
            {"label": "อําเภอ/เขต", "position": {"row": 0,
                                                 "column": 3}, "variable": self.cus_district},
            {"label": "ตำบล/แขวง", "position": {"row": 0, "column": 5},
                "variable": self.cus_sub_district},
            {"label": "รหัสไปรษณีย์", "position": {
                "row": 1, "column": 1}, "variable": self.cus_zip_code},
            {"label": "เบอร์โทร.", "position": {
                "row": 1, "column": 3}, "variable": self.cus_tel},
        ]
        for item in address_components_settings:
            # * >> Labels
            self.address_sub_label = CTkLabel(
                self.frame_1_1,
                text=item['label'],
                anchor=W
            )
            self.address_sub_label.grid(
                row=item['position']['row'],
                column=item['position']['column'],
                padx=(5, 0),  pady=(0, 5),  sticky='NW',
            )

            # * >> Inputs
            self.address_sub_input = CTkEntry(
                self.frame_1_1,
                width=90,
                textvariable=item['variable']
            )
            self.address_sub_input.grid(
                row=item['position']['row'], column=item['position']['column']+1, padx=(1, 0), sticky='NW')

        # * Frame Bottom Section /////////////////////////////////////////////////////////////////////////////
        self.bottom_component_settings = [
            {"label": "สินค้า", "position": {"row": 0, "column": 0},
                "widgets": {},  "setting": {"width": 200}},
            {"label": "ของแถม", "position": {"row": 0, "column": 1},
                "widgets": {},  "setting": {"width": 200}},
            {"label": "Remark", "position": {"row": 0, "column": 2},
                "widgets": {}, "setting": {"width": 500}},
        ]

        for index, item in enumerate(self.bottom_component_settings):
            print(item, index)
            # * Frame1 Section /////////////////////////////////////////////////////////////////////////////
            # * > address display Conponent /////////////////////
            # * >> Label
            self.items_label = CTkLabel(
                self.frame_bottom,
                text=item['label'],
                width=70,
                anchor=tk.W
            )
            self.items_label.grid(
                row=item['position']['row'],
                column=item['position']['column'],
                padx=(0, 5),
                pady=(0, 5),
                sticky='nw'
            )

            # * > DisplayField
            self.items_display = CTkTextbox(
                self.frame_bottom,
                height=150,
                width=item['setting']['width'],
                state=tk.DISABLED
            )
            self.items_display.grid(
                row=item['position']['row'] + 1,
                column=item['position']['column'],
                padx=(0, 5),
                pady=(0, 5),
                sticky='w',
            )

            self.bottom_component_settings[index]['widgets'][f'items_label'] = self.items_label
            self.bottom_component_settings[index]['widgets'][f'items_display'] = self.items_display

    # * รวม update textfield ////////////////////////////////////
    # * update จาก input QR
    # todo interesting code การใช้ getattr(obj, attr) เหมือนเปนการเอา ค่าจากทางขวาไปใส่ทางซ้ายโดย จับคู่ key ของ dict กับ attributes ของ obj
    def update_from_qr(self, input_qr=""):
        input = input_qr
        attributes = {
            'cus_order_name': 'order',
            'cus_name': 'name',
            'cus_tax_num': 'tax_Num',
            'cus_province': 'province',
            'cus_district': 'district',
            'cus_sub_district': 'sub_District',
            'cus_zip_code': 'zip_Code',
            'cus_tel': 'tel'
        }

        for attr, key in attributes.items():
            try:
                getattr(self, attr).set(input[key])
            except KeyError:
                getattr(self, attr).set("-")

        try:
            self.update_textbox_widgets(
                input['address'], self.address_display,  'cus_address')
        except:
            print("input ไม่มี prop address ส่งเข้ามา")
            self.update_textbox_widgets(
                "-", self.address_display, 'cus_address')

        self.update_item_display(input['com_Order_Items'], "product")
        self.update_item_display(input['com_Order_Premiums'], "premium")
        self.update_item_display(input['re_mark'], "remark")

    def update_from_qr2(self, input_qr=""):
        input = input_qr

        attributes = {
            'cus_order_name': 'order_Name',
            'cus_fname': 'customer_fname',
            'cus_lname': 'customer_lname',
            'cus_is_fulltax': 'want_full_tax',
            'cus_is_hq': 'is_headquarter',
            'cus_tax_num': 'full_tax_id',
            'cus_province': 'province',
            'cus_district': 'district',
            'cus_sub_district': 'sub_District',
            'cus_zip_code': 'zip_Code',
            'cus_tel': 'customer_tel',
            'cus_tax_name': 'company_name_of_tax',
            'cus_tax_type': 'full_tax_type'
        }

        # *update แบบ loop // attr ที่ดึงมาคือฝั่งซ้าย ส่วน ฝั่งขวาคือ key
        for attr, key in attributes.items():
            try:
                new_nalue = input[key]
                if input[key] == None:
                    new_nalue = "-"
                getattr(self, attr).set(new_nalue)
            except KeyError:
                getattr(self, attr).set("-")

        # *update ค่าแบบไม่ loop
        try:
            self.update_textbox_widgets(
                input['address'], self.address_display,  'cus_address')
        except:
            print("input ไม่มี prop address ส่งเข้ามา")
            self.update_textbox_widgets(
                "-", self.address_display, 'cus_address')

        self.cus_display_name_selector()
        self.update_item_display(input['com_Order_Items'], "product")
        self.update_item_display(input['com_Order_Premiums'], "premium")
        self.update_item_display(input['re_mark'], "remark")

    # * มันมีเรื่องของใบกำกับว่าจะออกแบบชื่อตัวเองหรือชื่อ บริษัท เลยต้องมีฟังชั่นสำหรับเลือก
    def cus_display_name_selector(self):
        self.display_name_result = f"""{
            self.cus_fname.get()} {self.cus_lname.get()}"""
        if self.cus_is_fulltax.get():
            print("แล้วมัน นิติบุคคล หรือ บุคคล")
            if self.cus_tax_type.get() == "Entity":
                self.display_name_result = f"""{self.cus_tax_name.get()}"""

        return self.cus_display_name.set(self.display_name_result)

    # * update รายการของที่ลูกค้าซื้อ

    def update_item_display(self, data=[], widget=None):
        # widget รับว่าจะอัพเดท ช่องไหน ระหว่าง product หรือ premium
        print("เข้ามาเป็นอะไร: ", data)

        if "product" in widget:
            widget_target = self.bottom_component_settings[0]['widgets'][f'items_display']
            if len(self.cus_purchased_products) != 0:
                self.cus_purchased_products.append(data)
            else:
                self.cus_purchased_products = []
        elif "premium" in widget:
            widget_target = self.bottom_component_settings[1]['widgets'][f'items_display']
            if len(self.cus_purchased_products) != 0:
                self.cus_purchased_premiums.append(data)
            else:
                self.cus_purchased_premiums = []
        elif "remark" in widget:
            widget_target = self.bottom_component_settings[2]['widgets'][f'items_display']
            if len(self.cus_purchased_products) != 0:
                self.cus_remark = data
            else:
                self.cus_remark = []

        widget_target.configure(state=NORMAL)
        widget_target.delete(1.0, END)
        if type(data) == list:
            for input in data:
                if "product" in widget:
                    widget_target.insert(
                        END, input['com_Products']['code_Itcity']+"\n")
                elif "premium" in widget:
                    widget_target.insert(
                        END, input['com_Premiums']['code_Itcity']+"\n")
        elif type(data) == str:
            widget_target.insert(END, data+"\n")

        widget_target.configure(state=DISABLED)

    # * update ที่อยู่ลูกค้า
    def update_textbox_widgets(self, address_input, address_widget, to_update_var=None):

        if address_input != "":
            input = address_input.strip()
        elif self.cus_order_name.get() != "":
            input = "-"
        else:
            input = ""

        if to_update_var is not None:
            # todo setattr interesting code น่าสนใจ เป็นการ่เลือก obj แล้ว ส่ง str ของ attribute แล้วตามด้วยค่าที่ต้องการ update
            setattr(self, to_update_var, input)

        address_widget.configure(state=NORMAL)
        address_widget.delete(1.0, END)
        address_widget.insert(END, input)
        address_widget.configure(state=DISABLED)

    def create_main_window(self):
        self.root.geometry("1000x450+400+300")
        self.root.title("Commart Autopage v0.1")
        # * use CANVAS as BG #################
        self.canvas = CTkFrame(master=self.root, width=500, corner_radius=0)
        self.canvas.pack(fill="both", expand=True, padx=5, pady=7)
        # * FRAMES ###########################
        # *> TopFrame
        self.frame_top = CTkFrame(master=self.canvas)
        self.frame_top.pack(side='top', fill='x', padx=5, pady=7, anchor='w')

        # *> ContentsFrame
        self.frame_1 = CTkFrame(
            master=self.canvas,
            # bg_color="#a1a1a1" มันคือไอขอบๆมันเป็นขอบเพราะว่า style พื้นฐานมันมี borderradius ที่fgซึ่งเปนสีดำ พอ setbg มันจะเห็นสีของ bg เป็นขอบ
        )
        self.frame_1 = CTkFrame(master=self.canvas)
        self.frame_1.pack(side='top', fill='x', padx=5, pady=7, anchor='w')

        # *> BottomFrame
        self.frame_bottom = CTkFrame(master=self.canvas)
        self.frame_bottom.pack(side='bottom', padx=5,
                               pady=7, anchor='w', fill='x')

        self.create_widgets()

    class PopUp:
        """
        Class PopUp use for create a pop-up for THE BOT GUI
        Parameters:
            - title (str): Title name of the pop-up.
            - message (str): For display a message in the pop-up.
            - parent (obj): class parent obj.
            - mode (str): มี 2 ทางเลือก "form" สำหรับ submit, "alert" สำหรับ alert
        """

        def __init__(self, title, message, parent, mode):
            self.mode_opt = {"form": "Submit", "alert": "Close"}
            self.mode = mode
            self.parent = parent
            self.title = title
            self.message = message
            self.create_subwindow()

        def delete(self):
            self.subwindow.destroy()

        def create_subwindow(self):
            self.subwindow = tk.Toplevel(self.parent)
            self.subwindow.transient(self.parent)
            self.subwindow.geometry("400x140+650+400")
            self.subwindow.title(f"{self.title}")
            self.subwindow.grab_set()
            self.subwindow.resizable(True, False)

            # * สร้างเฟรม
            self.subwin_frame = CTkFrame(self.subwindow)
            self.subwin_frame.pack(padx=10, pady=10, fill='x', expand=True)

            # * สร้าง Texted widget
            self.id_label = CTkTextbox(
                self.subwin_frame, font=("bazooka", 14))
            self.id_label.insert(END, f'{self.message}')
            self.id_label.pack(fill=BOTH, expand=True)
            self.id_label.configure(state=DISABLED)

            # * Submit Button
            self.submit_btn = CTkButton(
                self.subwin_frame, text=f"{self.mode_opt[self.mode]}", command=self.delete)
            self.submit_btn.pack(fill='x', expand=True)

            # * ยก widget นี้ ขึ้นมาหน้าสุด
            # > กำหนดตำแหน่งเฉยๆ ยังไม่ขยับ ต้องไปสั่งขยับอีกที
            self.subwindow.attributes('-topmost', 1)
            # > ยกมาในตำแหน่งที่กำหนดจาก attribute ที่แล้ว
            self.subwindow.lift()


def main():
    def on_closing():
        print('ui window is closed')
        root.destroy()
        main_gui.kill_remaining_threads()

#* เทคนิคคือ เช็คว่า ascii คือไร แล้วดูด้วยว่า นอกจากรับแบบ ascii แล้วรับแบบ keysym(ตัวอักษรจริง)ว่าตรงกับ ascii ไหม ถ้าไม่ตรงแปลว่าคนละภาษาแน่นอน เพราะ มันจะได้ ??
    def _onKeyRelease(event):
        print("press :", event.keysym)
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
    # * > ทำลาย root tkInter เมื่อmain_guiถูกปิด เพื่อไม่ให้มีการทำงานตกค้าง
    root.protocol("WM_DELETE_WINDOW", on_closing)
    # * > ลืมไปละ น่าจะเกี่ยวกับช่องไฟ
    root.columnconfigure(0, weight=1)

    # * > ปรับขนาดจอ
    # root.resizable(False, False)

    # * > ทำให้กด copy, paste, cut จากภาษาอะไรก็ได้
    root.bind('<Key>', _onKeyRelease)

    # * Create Instance
    # * เก็บ ตัว object ของ app ไว้ใน main_gui เพื่อเรียกใช้ functions kill_remaining_threads เมื่อ tkinter ถูกปิด
    main_gui = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
