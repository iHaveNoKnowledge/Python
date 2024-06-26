import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from customtkinter import *

from modules.selenium_webdriver import ChromeDriver
# from modules.unified_table_data import UnifyData

import traceback


class MainApp:
    def __init__(self, root):
        self.root = root
        # * for query
        # self.data_file_dir = ''
        self.data_file_dir = StringVar(value="")
        self.file_name = StringVar(value="ไม่มีไฟล์")
        self.sku = StringVar(value="")
        self.set_num = StringVar(value="")
        # * เอาไว้เก็บ object ที่รับค่าจาก excel, import file, อะไรก็ตามที่เป็น data table ที่นำเข้ามา
        self.data_table = {}
        self.create_main_window()
        # ใช้ class unified
        self.chromdriver_controller = ChromeDriver()

    def resetAllValue(self):
        self.data_file_dir.set(value="")
        self.sku.set(value="")
        self.set_num.set(value="")

    def resetInput(self):
        self.sku.set(value="")
        self.set_num.set(value="")

    def add_file(self):
        self.data_file_dir.set('')
        self.data_file_dir.set(filedialog.askopenfilename(
            title="Select an import file"))
        # * ตัดเอาเฉพาะ ชื่อไฟล์
        if self.data_file_dir.get():
            self.file_name.set(f"{self.data_file_dir.get().split('/')[-1]}")
            print('มีชื่อไฟล์', self.file_name.get())
            print('dirของ import file', self.data_file_dir.get())
            target_dir = self.data_file_dir.get()
            try:
                self.data_table = UnifyData(target_dir)
                print(self.data_table.data_state)
            except:
                print("ไม่มีไฟล์อัพโหลดเข้ามา")
        else:
            self.resetAllValue()
            print("ไม่มีชื่อไฟล์", self.data_file_dir.get())

            pass

    def search(self):
        # * ลบ result products list เก่า
        try:
            sku = self.sku.get().strip()
            set = self.set_num.get().strip()

            # * เกี่ยวกับการแสดงผล GUI
            self.clear_log()
            data_dict = self.data_table.get_result(sku, set)
            self.update_log(f"ชื่อชุด: {sku}")
            self.update_log(f"เลขSet: {set}")
            self.sku.set("")
            self.set_num.set("")

            # todo Continue from here// wip you are here
            try:
                self.chromdriver_controller.operation_start(sku, data_dict)
            except ValueError as e:
                error_message = str(e)
                self.update_log(error_message)
        except:
            self.update_log("พัง")
            raise ValueError('search พัง: ', traceback.format_exc())

    def update_log(self, update_txt=""):
        self.update_txt = update_txt
        self.log_display.config(state=NORMAL)
        self.log_display.insert(END, self.update_txt + "\n")
        self.log_display.config(state=DISABLED)

    def clear_log(self):
        print('เคลีย!!')
        self.log_display.config(state=NORMAL)
        self.log_display.delete("1.0", END)
        self.log_display.config(state=DISABLED)

    def create_widgets(self):
        # * Variables for setting options
        self.pady = (0, 16)

        # * Frame Top Section /////////////////////////////////////////////////////////////////////////////
        # * > QR Input Component
        # * >> Labels
        self.find_dir_display = CTkLabel(
            self.frame_top, text="QR Input")
        self.find_dir_display.grid(
            row=0, column=0, padx=(0, 0),  pady=self.pady)
        # * >> Inputs
        self.qr_input = CTkEntry(
            self.frame_top,
            width=180,
        )
        self.qr_input.grid(row=0, column=1, pady=self.pady, sticky="w")
        # * >> Button
        self.find_dir_btn = CTkButton(
            self.frame_top,
            width=80,
            text=f"Start",
            command=self.add_file,
        )
        self.find_dir_btn.grid(row=0, column=2, padx=(
            0, 0), pady=self.pady, sticky="w")

        # * > Order display Conponent
        # * >> Label
        self.order_label = CTkLabel(
            self.frame_top, text="เลขที่คำสั่งซื้อ")
        self.order_label.grid(row=0, column=3, padx=(10, 10), pady=self.pady)
        # * >> Display
        self.order_display = CTkEntry(
            self.frame_top,
            width=180,
            state="readonly",
        )
        self.order_display.grid(row=0, column=4, padx=(
            1, 1), pady=self.pady)

        # * > Name Display component
        # * >> Label
        self.name_label = CTkLabel(
            self.frame_top, text="ชื่อออกบิล")
        self.name_label.grid(row=1, column=0, padx=(0, 10))
        # * >> Display
        self.name_display = CTkEntry(
            self.frame_top,
            width=300,
            # state="readonly",

        )
        self.name_display.grid(row=1, column=1, padx=(0, 1))

        # * > TaxNum display Conponent
        # * >> Label
        self.tax_num_label = CTkLabel(
            self.frame_top, text="เลขผู้เสียภาษี")
        self.tax_num_label.grid(row=1, column=3, padx=(10, 10))
        # * >> Display
        self.tax_num_display = CTkEntry(
            self.frame_top,
            width=180,
            state="readonly",
        )
        self.tax_num_display.grid(row=1, column=4, padx=(0, 1))

        # * Frame1 Section /////////////////////////////////////////////////////////////////////////////
        # * > address display Conponent
        # * >> Label
        self.address_label = CTkLabel(
            self.frame_1,
            text="ที่อยู่ ",
        )
        self.code_label.grid(row=0, column=0, padx=(5, 0),
                             pady=(0, 5), sticky='w')
        # * >> Display
        self.code_display = CTkEntry(
            self.frame_1,
            width=20,
            # borderwidth=1,
            textvariable=self.sku,
            # relief="groove"
        )
        self.code_display.grid(row=0, column=1, padx=(1, 0))

        # * Set Number Display Component
        # * > Labels
        self.set_num_label = CTkLabel(
            self.frame_1,
            text="Set Number ",
        )
        self.set_num_label.grid(row=1, column=0, padx=(
            5, 0),  pady=(0, 5),  sticky='w')
        # * > Input
        self.set_num_display = CTkEntry(
            self.frame_1,
            width=20,
            # borderwidth=1,
            textvariable=self.set_num,
            # relief="groove"
        )
        self.set_num_display.grid(row=1, column=1, padx=(1, 0), sticky='w')

        # * Frame Bottom Section /////////////////////////////////////////////////////////////////////////////
        # * > DisplayField
        self.log_display = CTkTextbox(self.frame_bottom, state=DISABLED)
        self.log_display.grid(row=0, column=0, sticky='w')

    def create_main_window(self):
        self.root.geometry("1000x400+400+300")

        self.root.title("Commart Autopage v0.1")

        # * use CANVAS as BG #################
        self.canvas = self.scrollable_frame = CTkFrame(
            master=self.root,
            width=500,
            height=400,
            corner_radius=0,
            bg_color="gray95")
        # Expand to fill the whole window
        self.canvas.pack(fill="both", expand=True, padx=5, pady=7)

        # * FRAMES ###########################
        # *> TopFrame
        self.frame_top = CTkFrame(
            master=self.canvas,
            # padx=5, pady=5,
            # bg_color="#a1a1a1"
        )
        self.frame_top.pack(side='top', fill='x', padx=5, pady=7, anchor='w')

        # *> ContentsFrame
        self.frame_1 = CTkFrame(
            master=self.canvas,
            # padx=5, pady=5,
            # bg_color="#a1a1a1" มันคือไอขอบๆมันเป็นขอบเพราะว่า style พื้นฐานมันมี borderradius ที่fgซึ่งเปนสีดำ พอ setbg มันจะเห็นสีของ bg เป็นขอบ
        )
        self.frame_1.pack(side='top', padx=5, pady=7, anchor='w')

        # *> BottomFrame
        self.frame_bottom = CTkFrame(
            master=self.canvas,
            # padx=5, pady=5,
            # borderwidth=1,
            bg_color="#bdbdbd")
        self.frame_bottom.pack(side='bottom', padx=5, pady=7, anchor='w')

        self.create_widgets()


def main():
    def on_closing():
        print('ui window is closed')
        root.destroy()

    def ctrl_saraea_copy(event):
        ctrl_state = event.state & 0x4 != 0  # 0x4 คือ flag สำหรับ Control key
        # 67 คือรหัสสำหรับสระแอในภาษาไทย (อาจแตกต่างบนระบบอื่นๆ)
        if ctrl_state and event.keycode == 67:
            event.widget.event_generate("<<Copy>>")

    root = CTk()
    # * options
    # * > ทำลาย root tkInter เมื่อguiถูกปิด เพื่อไม่ให้มีการทำงานตกค้าง
    root.protocol("WM_DELETE_WINDOW", on_closing)
    # * > ลืมไปละ น่าจะเกี่ยวกับช่องไฟ
    root.columnconfigure(0, weight=1)

    # * > ปรับขนาดจอ
    # root.resizable(False, False)

    # * > ทำให้กด copy จากภาษาอะไรก็ได้
    root.bind('<Key>', ctrl_saraea_copy)

    # * Create Instance
    gui = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

# * hints
# * ชื่อชุด kit กับ เลข set แยกกัน input
