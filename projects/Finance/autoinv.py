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
import time
import queue

from modules.selenium_webdriver import ChromeDriver
from modules.chrome_starter import CustomChrome

from loguru import logger

OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"assets\frame0")


def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


logger.add("autoinv_log.log", format="{time} {level} {message}", level="INFO", rotation="1 day", retention="7 days")


class MainApp:
    def __init__(self, root):
        self.root = root
        # * variables
        self.import_file_name = tk.StringVar(value="None")
        self.stop_event = threading.Event()
        self.reprint_thread = None
        self.loading_progress = tk.StringVar(value="0 %")

        # * main process
        self.create_main_window()
        CustomChrome(8989)
        self.chrome_driver = ChromeDriver(app=self)

    def create_main_window(self):
        self.root.geometry("452x481")
        self.root.configure(bg="#FFFFFF")
        self.canvas = tk.Canvas(
            self.root,
            bg="#FFFFFF",
            height=481,
            width=452,
            bd=0,
            highlightthickness=0,
            relief="ridge"
        )
        self.canvas.place(x=0, y=0)

        # * Add File Component-----------------------------------------------------------------------------------------------------------
        self.canvas.create_text(
            31.0,
            46.0,
            anchor="nw",
            text="Target File",
            fill="#000000",
            font=("RobotoRoman Light", 15 * -1)
        )

        self.add_file_img = tk.PhotoImage(file=relative_to_assets("add_file_btn.png"))
        self.add_file_btn = tk.Button(
            image=self.add_file_img,
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.receive_dir(),
            relief="flat",
        )
        self.add_file_btn.place(
            x=31.0,
            y=65.0,
            width=106.0,
            height=31.0
        )

        # * Start Button start component------------------------------------------------------------------------------------------------------
        self.start_btn_img = tk.PhotoImage(file=relative_to_assets("start_btn.png"))
        self.start_btn = tk.Button(
            image=self.start_btn_img,
            borderwidth=0,
            highlightthickness=0,
            command=lambda: self.start_task(),
            relief="flat"
        )
        self.start_btn.place(
            x=315.0,
            y=64.0,
            width=106.0,
            height=31.0
        )

        # * import file name component--------------------------------------------------------------------------------------------------
        self.canvas.create_text(
            31.0,
            117.0,
            anchor="nw",
            text="Added File Name",
            fill="#000000",
            font=("RobotoRoman Light", 15 * -1)
        )

        self.import_file_name_entry = tk.Entry(
            bd=0,
            # bg="#D9D9D9",
            readonlybackground="#D9D9D9",
            fg="#000716",
            highlightthickness=0,
            textvariable=self.import_file_name,
            state='readonly',
        )
        self.import_file_name_entry.place(
            x=39.0,
            y=136.0,
            width=374.0,
            height=29.0
        )

        self.import_file_name_img = tk.PhotoImage(file=relative_to_assets("import_file_name_entry.png"))
        self.import_file_name_img_entry_bg = self.canvas.create_image(
            226.0,
            151.5,
            image=self.import_file_name_img
        )

        # * Progress bar component----------------------------------------------------------------------------------------------------------------
        self.progressbar = ttk.Progressbar(orient=tk.HORIZONTAL, mode='determinate', maximum=100)
        self.progressbar.place(x=32.0, y=210.0, width=387.0, height=20.0)
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
            fg_color="transparent", #transparent ปลอม
            text_color="#000000",
            textvariable=self.loading_progress
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
            self.log_queue = queue.Queue()
            self.read_data_thread = threading.Thread(
                target=lambda: self.read_data_from_file_dir(self.import_dir, self.log_queue), daemon=True)
            self.read_data_thread.start()

            self.root.after(100, self.process_log_queue)  # Schedule UI updates
        else:
            self.import_file_name.set("ไม่มีการเลือกไฟล์")

    def process_log_queue(self):
        try:
            while True:
                log_message = self.log_queue.get_nowait()
                self.update_log(log_message, self.log_textbox)
        except queue.Empty:
            pass

        if self.read_data_thread.is_alive():
            self.root.after(100, self.process_log_queue)  # Continue checking the queue

    def read_data_from_file_dir(self, dir, log_queue):
        global invs_list_state
        self.log_textbox.delete(0.0, 'end')
        self.target_col = "invoice_no"
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

            self.inv_state_df = pandas.read_excel('inv_state.xlsx', dtype=str, na_filter=True).drop_duplicates()
            self.inv_state_df.dropna(inplace=True)
            self.invs_list_state = self.inv_state_df.copy()
            self.data_range = self.invs_list_state[self.target_col].__len__()
            for inv in self.invs_list_state[self.target_col]:
                log_queue.put(f"{inv}")

            log_queue.put(f"Data Imported : {self.data_range} records")
        except Exception as err:
            print(err)
            logger.error(err)
            log_queue.put(f"ดึงข้อมูลจากไฟล์ไม่ได้: {err}")

    #! wip กำลังทำตัวตัด เลข bil เนื่องจาก ถ้าหากเกิดข้อผิดพลาด มันจะได้รันต่อได้ อาจจะต้องทำ ไฟล์สำหรับเก็บ state แยกออกมา เมื่อรับไฟล์เข้ามาให้เอา data ไปลง อีกไฟล์ แล้วเอาไฟล์ใหม่เป็น state
    def deduct_accel_file_data(self, order, to_deduct_inv=[]):
        order = order.get()
        df = self.invs_list_state
        print("deduct_accel_file_data df มีมาก่อนเหรอ: ", df)
        print("deduct_accel_file_data order: ", order)
        print("deduct_accel_file_data ref: ", df.loc[df['orders'] == order, 'orders'])
        # * ใช้ loc ของ df โดยดูว่า column 'orders' == order ที่รับเข้ามาหรือไม่, โดยให้ดึงค่าจาก column orders
        has_order = df.loc[df['orders'] == order, 'orders']
        if not has_order.empty:
            df.loc[df['orders'] == order, 'orders'] = ''

        print("to_deduct_inv ไม่ได้ได้ไง: ", to_deduct_inv)
        if to_deduct_inv:
            for sn in to_deduct_inv:
                df.loc[df[sn['sku']] == sn['sn'], sn['sku']] = ''
        df.to_excel(self.accel_file_dir, sheet_name='Sheet1', index=False)

    def start_task(self):
        if self.reprint_thread and self.reprint_thread.is_alive():
            self.stop_event.set()
            self.wait_for_stop()
        else:
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

    def wait_for_stop(self):
        if self.reprint_thread.is_alive():
            self.root.after(100, self.wait_for_stop)
        else:
            self.stop_event.clear()
            self.reprint_thread = threading.Thread(target=lambda: self.chrome_driver.inv_reprint(
                self.invs_list_state['invoice_no'], self.stop_event, self.progressbar, self.root, self), daemon=True)
            self.reprint_thread.start()
# * เก่า
        # self.stop_event.clear()
        # if not self.stop_event.is_set():
        #     print("start task")
        #     self.reprint_thread = threading.Thread(target=lambda: self.chrome_driver.inv_reprint(
        #         self.invs_list_state['invoice_no'], self.stop_event, self.progressbar, self.root, self), daemon=True)
        #     self.reprint_thread.start()
        #     self.check_threads(self.reprint_thread)
        #     self.stop_event.clear()
        # else:
        #     print("stop task")
        #     self.stop_event.clear()
        #     self.reprint_thread.join()

        # while True:
        #     if self.stop_event.is_set():
        #         self.reprint_thread.join()
        #         break
        #     else:
        #         continue

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

    root = CTk()
    # * options
    # * > ทำลาย root tkInter เมื่อmain_guiถูกปิด เพื่อไม่ให้มีการทำงานตกค้าง
    root.protocol("WM_DELETE_WINDOW", on_closing)
    # * > ลืมไปละ น่าจะเกี่ยวกับช่องไฟ
    root.columnconfigure(0, weight=1)

    # * > ปรับขนาดจอ
    root.resizable(False, False)

    # * > ทำให้กด copy, paste, cut จากภาษาอะไรก็ได้
    root.bind('<Key>', _onKeyRelease)

    # * Create Instance
    # * เก็บ ตัว object ของ app ไว้ใน main_gui เพื่อเรียกใช้ functions kill_remaining_threads เมื่อ tkinter ถูกปิด
    main_gui = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
