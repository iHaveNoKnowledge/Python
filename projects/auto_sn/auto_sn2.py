import tkinter as tk
from tkinter import ttk

from modules.selenium_webdriver import *


class MainApp:
    def __init__(self, root):
        self.root = root
        self.data_file_dir = ''
        self.sku = ''
        self.set_num = ''
        ChromeDriver()
        
    


def main():
    def on_closing():
        print('ui window is closed')
        root.destroy()

    root = tk.Tk()
    # * options
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.columnconfigure(0, weight=1)

    # * Create Instance
    gui = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

# * hints
# * ชื่อชุด kit กับ เลข set แยกกัน input
