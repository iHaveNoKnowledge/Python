import tkinter as tk
from tkinter import ttk
from pathlib import Path
from tkinter import filedialog
from customtkinter import *
import threading
import time
import json
import re
import os
import pandas
from openpyxl import Workbook
import time
import queue

from modules.selenium_webdriver import ChromeDriver
from modules.chrome_starter import CustomChrome

from loguru import logger

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"assets\frame0")


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


logger.add(
    "autoinv_main_log.log",
    format="{time} {level} {message}",
    level="INFO",
    rotation="1 day",
    retention="7 days"
)


class MainApp:
    def __init__(self, root):
        self.root = root
        # * variables
        self.import_file_name = tk.StringVar(value="None")
        self.stop_event = threading.Event()
        self.reprint_thread = None
        self.loading_progress = tk.StringVar(value="0 %")
        self.log_queue = queue.Queue()
        self.target_col = "invoice_no"

        # * main process
        self.create_main_window()
        self.create_state_excel()
        CustomChrome(8989)
        self.chrome_driver = ChromeDriver(app=self)
        self.get_state_thread = threading.Thread(target=lambda: self.get_state_from_file(self.log_queue), daemon=True)
        self.get_state_thread.start()
        self.root.after(100, self.process_log_queue, self.get_state_thread)

    def create_main_window(self):
        self.root.geometry("452x481")
        self.root.configure(bg="#FFFFFF")
        self.btn_font = CTkFont(family="Arial", size=16, weight="bold")
        self.canvas = tk.Canvas(
            self.root,
            bg="#63666e",
            height=481,
            width=452,
            bd=0,
            highlightthickness=0,
            relief="ridge"
        )
        self.canvas.place(x=0, y=0)

        # * Add File Component-----------------------------------------------------------------------------------------------------------
        self.create_text = CTkLabel(
            self.canvas,
            anchor="nw",
            text="Target File",
            text_color="#000000",
            font=("RobotoRoman Light", 15 * -1)
        )
        self.create_text.place(
            x=31.0,
            y=46.0,
        )

        self.add_file_img = tk.PhotoImage(file=relative_to_assets("add_file_btn.png"))
        self.add_file_btn = CTkButton(
            self.canvas,
            # image=self.add_file_img,
            fg_color="#7CC283",
            text_color="#000000",
            border_width=0,
            border_spacing=0,
            # highlightthickness=0,
            command=lambda: self.receive_dir(),
            # relief="flat",
            width=106.0,
            height=31.0,
            text="Add Data",
            font=self.btn_font
        )
        self.add_file_btn.place(
            x=31.0,
            y=65.0,
        )

        # * Status display component----------------------------------------------------------------------------------------------------------
        self.status_display = CTkLabel(
            self.canvas,
            text=f"Bot Status: ไม่มีการทำงาน",
            fg_color="#1f242e",
            text_color="#ffec1f",
            padx=10,
            justify="right",
            anchor="center",
            width=200
        )
        self.status_display.place(
            x=220,
            y=35,

        )

        # * Start Button start component------------------------------------------------------------------------------------------------------
        self.start_btn_img = tk.PhotoImage(file=relative_to_assets("start_btn.png"))
        self.start_btn = CTkButton(
            self.canvas,
            # image=self.start_btn_img,
            fg_color="#F2E67A",
            text_color="#000000",
            font=self.btn_font,
            border_width=0,
            border_spacing=0,
            # highlightthickness=0,
            command=lambda: self.start_task(),
            # relief="flat"
            width=106.0,
            height=31.0,
            text="Start"
        )
        self.start_btn.place(
            x=315.0,
            y=64.0,
        )

        # * import file name component--------------------------------------------------------------------------------------------------
        self.add_file_name_text = CTkLabel(
            self.canvas,
            anchor="nw",
            text="Added File Name",
            text_color="#000000",
            font=("RobotoRoman Light", 15 * -1),
            fg_color="transparent",
            pady=0
        )
        self.add_file_name_text.place(
            x=31.0,
            y=117.0,
        )

        self.import_file_name_entry = CTkEntry(
            self.canvas,
            # bd=0,
            # bg="#D9D9D9",
            # readonlybackground="#D9D9D9",
            # highlightthickness=0,
            text_color="#000716",
            fg_color="#D9D9D9",
            textvariable=self.import_file_name,
            state='readonly',
            width=392.0,
            height=29.0
        )
        self.import_file_name_entry.place(
            x=30.0,
            y=136.0
        )

        # self.import_file_name_img = tk.PhotoImage(file=relative_to_assets("import_file_name_entry.png"))
        # self.import_file_name_img_entry_bg = self.canvas.create_image(
        #     226.0,
        #     151.5,
        #     image=self.import_file_name_img
        # )

        # * Progress bar component----------------------------------------------------------------------------------------------------------------
        self.progressbar = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, mode='determinate', maximum=100)
        # self.progressbar.place(x=32.0, y=210.0, width=387.0, height=20.0)
        self.progressbar.place(relx=0.0708, rely=0.4366, relwidth=0.86, relheight=0.040)
        # self.image_image_1 = tk.PhotoImage(file=relative_to_assets("image_1.png"))
        # self.image_1 = self.canvas.create_image(
        #     226.0,
        #     219.0,
        #     image=self.image_image_1
        # )

        self.canvas.create_text(
            31.0,
            185.0,
            anchor="nw",
            text="Progress",
            fill="#000000",
            font=("RobotoRoman Light", 15 * -1)
        )
        # * Progress bar display value of the progress bar
        self.progress_text_display = CTkLabel(
            self.canvas,
            fg_color="transparent",  # transparent ปลอม
            text_color="#000000",
            textvariable=self.loading_progress,
            justify="right"
        )

        self.progress_text_display.place(x=395.0, y=180.0)

        # * log widget ----------------------------------------------------------------------------------------------------------------------------------
        self.log_textbox = CTkTextbox(
            self.canvas,
            width=387,
            # bg="#D9D9D9",
            state='disabled',
        )
        self.log_textbox.place(x=32.0, y=260.0)
 # * functions ----------------------------------------------------------------------------------------------------------------

    def create_state_excel(self):
        if not os.path.exists('inv_state.xlsx'):
            # * create workbook and new sheet
            self.wb = Workbook()
            self.ws = self.wb.active

            # * add data into cel A1
            self.ws['A1'] = 'invoice_no'

            # * save as .xlsx
            self.wb.save('inv_state.xlsx')

    def update_log(self, text, log_widget=None):
        self.text = text
        self.widget = log_widget

        if log_widget:
            self.widget.configure(state="normal")
            self.widget.insert("end", f"{self.text}\n")
            self.widget.yview_moveto(1.0)
            self.widget.configure(state="disabled")
        else:
            self.widget.insert("end", f"None\n")

    def clear_log(self, log_widget=None):
        self.widget = log_widget
        if log_widget:
            self.widget.configure(state="normal")
            self.widget.delete("1.0", "end")
            self.widget.configure(state="disabled")
        else:
            self.widget.insert("end", f"None\n")

    def receive_dir(self):
        self.import_dir = filedialog.askopenfilename(title="Select Excel File Data")
        self.clear_log(self.log_textbox)
        if self.import_dir:
            self.import_file_name.set(self.import_dir.split('/')[-1])
            self.read_data_thread = threading.Thread(
                target=lambda: self.read_data_from_file_dir(self.import_dir, self.log_queue), daemon=True)
            self.read_data_thread.start()

            self.root.after(100, self.process_log_queue, self.read_data_thread)  # Schedule UI updates
        else:
            self.import_file_name.set("ไม่มีการเลือกไฟล์")

    def process_log_queue(self, thread):
        try:
            while True:
                log_message = self.log_queue.get_nowait()
                self.update_log(log_message, self.log_textbox)
        except queue.Empty:
            pass

        if thread.is_alive():
            self.root.after(100, self.process_log_queue, thread)  # Continue checking the queue

    def read_data_from_file_dir(self, dir, log_queue):
        self.log_textbox.delete(0.0, 'end')
        try:
            self.incoming_file_df = pandas.read_excel(dir, dtype=str, na_filter=True).drop_duplicates()
            self.incoming_file_df.columns = self.incoming_file_df.columns.str.lower()
            # *สร้างไฟล์ state
            if os.path.exists('inv_state.xlsx'):
                df_existing = pandas.read_excel('inv_state.xlsx')
                df_combined = pandas.concat([df_existing[self.target_col], self.incoming_file_df[self.target_col]])
                df_combined = df_combined.drop_duplicates()
                df_combined.dropna(inplace=True)
                df_combined.to_excel('inv_state.xlsx', index=False)
            else:
                self.incoming_file_df[self.target_col].to_excel('inv_state.xlsx', index=False)

            self.get_state_from_file(log_queue)

        except Exception as err:
            print(err)
            logger.error(err)

    def get_state_from_file(self, log_queue):
        logger.info("get_state_from_file: called")
        global invs_list_state
        try:
            self.inv_state_df = pandas.read_excel('inv_state.xlsx', dtype=str, na_filter=True).drop_duplicates()
            self.inv_state_df.dropna(inplace=True)
            self.invs_list_state = self.inv_state_df.copy()
            self.data_range = self.invs_list_state[self.target_col].__len__()
            self.state_series = self.invs_list_state[self.target_col]
            self.show_state_log_ui(self.state_series, log_queue)
            logger.info("get_state_from_file, try: finished")
        except Exception as err:
            print(err)
            logger.error("get_state_from_file:", err)
            log_queue.put(f"ดึงข้อมูลจากไฟล์ไม่ได้: {err}")

    def show_state_log_ui(self, state_series, log_queue):
        self.state_series_inv = state_series
        for inv in self.state_series_inv:
            log_queue.put(f"{inv}")
        log_queue.put(f"Data State : {self.state_series_inv.__len__()} records To print")

    #! wip กำลังทำตัวตัด เลข bil เนื่องจาก ถ้าหากเกิดข้อผิดพลาด มันจะได้รันต่อได้ อาจจะต้องทำ ไฟล์สำหรับเก็บ state แยกออกมา เมื่อรับไฟล์เข้ามาให้เอา data ไปลง อีกไฟล์ แล้วเอาไฟล์ใหม่เป็น state
    def deduct_accel_file_data(self, to_decuct_inv):
        self.deduct_inv = to_decuct_inv
        df = self.invs_list_state
        logger.info("invs before deduction: ", df)
        try:
            has_inv = df.loc[df['invoice_no'] == self.deduct_inv, 'invoice_no']
            if not has_inv.empty:
                df.loc[df['invoice_no'] == self.deduct_inv, 'invoice_no'] = ''

            df.to_excel('inv_state.xlsx', index=False)
            self.inv_state_df = pandas.read_excel('inv_state.xlsx', dtype=str, na_filter=True).drop_duplicates()
            self.inv_state_df.dropna(inplace=True)
            self.invs_list_state = self.inv_state_df.copy()
        except Exception as err:
            print("deduct error: ", err)

        logger.info("invs after deduction: ", df)

    def start_task(self):
        if self.reprint_thread and self.reprint_thread.is_alive():
            print("start task: Previous Thread is alive")
            self.stop_event.set()
            # self.wait_for_stop()
        elif not self.reprint_thread or not self.reprint_thread.is_alive():
            print("start task: Reprint Thread is not alive")
            self.start_btn.configure(text="Stop")
            self.stop_event.clear()
            self.reprint_thread = threading.Thread(
                target=lambda: self.chrome_driver.inv_reprint(
                    self.invs_list_state['invoice_no'],
                    self.stop_event,
                    self.progressbar,
                    self.root,
                    self
                ),
                daemon=True
            )
            self.reprint_thread.start()

            logger.info("Start Reprint Thread")
        else:
            print("start task: Reprint Thread is still alive")

    def wait_for_stop(self):
        print("wait_for_stop() executed")
        if self.reprint_thread.is_alive():
            print("wait_for_stop() : Reprint Thread is still alive")
            self.root.after(100, self.wait_for_stop)
        else:
            print("wait_for_stop() : Reprint Thread is not alive anymore")
            self.stop_event.clear()
            self.reprint_thread = threading.Thread(target=lambda: self.chrome_driver.inv_reprint(
                self.invs_list_state['invoice_no'],
                self.stop_event,
                self.progressbar,
                self.root,
                self
            ),
                daemon=True
            )
            self.reprint_thread.start()

    def check_threads(self, callback=None):
        if not self.reprint_thread.is_alive():
            print(f"self.reprint_thread.is_alive(): {self.reprint_thread.is_alive()}")
            self.reprint_thread.join()
            self.stop_event.set()
            return
        self.root.after(100, lambda: self.check_threads(callback))  # * ถ้าไม่เขียน lambda มันไม่รอ


# * Initializer-----------------------------------------------------------------------------------------------------------
def main():

    def on_closing():
        print('ui window is closed')
        root.destroy()
        main_gui.check_threads()

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

    def dynamic_scaling(base_width=1920, base_height=1080):

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # * calculate scale
        scaling_factor = min(screen_width / base_width, screen_height / base_height)

        set_window_scaling(scaling_factor)
        set_widget_scaling(scaling_factor)

    root = CTk()
    # * options
    # * > Set Name
    root.title("Inv iterator v1")

    # * > Set Theme
    set_default_color_theme("dark-blue")

    # * > ทำลาย root tkInter เมื่อmain_guiถูกปิด เพื่อไม่ให้มีการทำงานตกค้าง
    root.protocol("WM_DELETE_WINDOW", on_closing)
    # * > ลืมไปละ น่าจะเกี่ยวกับช่องไฟ
    root.columnconfigure(0, weight=1)

    # * > ปรับขนาดจอ
    root.resizable(False, False)

    # * > UI Scaling
    # scaling_factor = min(1360 / 1920, 768/1080)
    # set_window_scaling(scaling_factor)
    dynamic_scaling()

    # * > ทำให้กด copy, paste, cut จากภาษาอะไรก็ได้
    root.bind('<Key>', _onKeyRelease)

    # * Create Instance
    # * เก็บ ตัว object ของ app ไว้ใน main_gui เพื่อเรียกใช้ functions kill_remaining_threads เมื่อ tkinter ถูกปิด
    main_gui = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
