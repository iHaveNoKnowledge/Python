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

        # * main process
        self.create_main_window()
        CustomChrome(8989)
        self.chrome_driver = ChromeDriver(app=self)

    def create_main_window(self):
        self.root.geometry("452x281")
        self.root.configure(bg="#FFFFFF")
        self.canvas = tk.Canvas(
            self.root,
            bg="#FFFFFF",
            height=281,
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
            command=lambda: print("start_btn clicked"),
            relief="flat"
        )
        self.start_btn.place(
            x=315.0,
            y=64.0,
            width=106.0,
            height=31.0
        )

        # * import file name component--------------------------------------------------------------------------------------------------
        self.import_file_name_img = tk.PhotoImage(file=relative_to_assets("import_file_name_entry.png"))
        self.import_file_name_img_entry_bg = self.canvas.create_image(
            226.0,
            151.5,
            image=self.import_file_name_img
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

        self.canvas.create_text(
            31.0,
            117.0,
            anchor="nw",
            text="Added File Name",
            fill="#000000",
            font=("RobotoRoman Light", 15 * -1)
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

    def receive_dir(self):
        print("askopenfile")
        self.import_dir = filedialog.askopenfilename(title="Select Excel File Data")

        if self.import_dir:
            self.import_file_name.set(self.import_dir.split('/')[-1])
            self.read_data_from_file_dir(self.import_dir)
            logger.info(f"รับไฟล์: {self.import_dir}")
        else:
            self.import_file_name.set("ไม่มีการเลือกไฟล์")

    def read_data_from_file_dir(self, dir):
        self.dir = dir
        self.target_col = "INVOICE_NO"
        self.df = pandas.read_excel(self.dir, dtype=str, na_filter=True)
        self.invs_list: list = self.df[self.target_col].tolist()
        self.invs_list_state = self.invs_list.copy()
        print(f"Data imported: {self.invs_list}")

    def start_task(self):
        print("start task")

    def kill_remaining_threads(self):
        return
        if self.current_task and self.current_task.is_alive():
            self.stop_event.set()
            self.current_task.join()


# * Initializer-----------------------------------------------------------------------------------------------------------
def main():
    def on_closing():
        print('ui window is closed')
        root.destroy()
        main_gui.kill_remaining_threads()

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
