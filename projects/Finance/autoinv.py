import tkinter as tk
from tkinter import filedialog
from customtkinter import *
import threading
import time
import json
import re
import os

from modules.selenium_webdriver import ChromeDriver
from modules.supabase_client import Supabase_client



class MainApp:
    def __init__(self, root):
        self.root = root
        self.data_file_dir = tk.StringVar(value="")
        
    def create_main_window(self):
        self.root.geometry("452x281")
        self.root.configure(bg = "#FFFFFF")
        canvas = tk.Canvas(
            self.root,
            bg = "#FFFFFF",
            height = 281,
            width = 452,
            bd = 0,
            highlightthickness = 0,
            relief = "ridge"
        )

        canvas.place(x = 0, y = 0)
        entry_image_1 = tk.PhotoImage(
            file=relative_to_assets("entry_1.png"))
        entry_bg_1 = canvas.create_image(
            226.0,
            151.5,
            image=entry_image_1
        )
        entry_1 = tk.Entry(
            bd=0,
            bg="#D9D9D9",
            fg="#000716",
            highlightthickness=0
        )
        entry_1.place(
            x=39.0,
            y=136.0,
            width=374.0,
            height=29.0
        )

        image_image_1 = tk.PhotoImage(
            file=relative_to_assets("image_1.png"))
        image_1 = canvas.create_image(
            226.0,
            219.0,
            image=image_image_1
        )

        button_image_1 = tk.PhotoImage(
            file=relative_to_assets("button_1.png"))
        button_1 = Button(
            image=button_image_1,
            borderwidth=0,
            highlightthickness=0,
            command=lambda: print("button_1 clicked"),
            relief="flat"
        )
        button_1.place(
            x=31.0,
            y=65.0,
            width=106.0,
            height=31.0
        )

        button_image_2 = tk.PhotoImage(
            file=relative_to_assets("button_2.png"))
        button_2 = Button(
            image=button_image_2,
            borderwidth=0,
            highlightthickness=0,
            command=lambda: print("button_2 clicked"),
            relief="flat"
        )
        button_2.place(
            x=315.0,
            y=64.0,
            width=106.0,
            height=31.0
        )

        canvas.create_text(
            31.0,
            185.0,
            anchor="nw",
            text="Progress",
            fill="#000000",
            font=("RobotoRoman Light", 15 * -1)
        )

        canvas.create_text(
            31.0,
            117.0,
            anchor="nw",
            text="Target Directory",
            fill="#000000",
            font=("RobotoRoman Light", 15 * -1)
        )

        canvas.create_text(
            31.0,
            46.0,
            anchor="nw",
            text="Target File",
            fill="#000000",
            font=("RobotoRoman Light", 15 * -1)
        )

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