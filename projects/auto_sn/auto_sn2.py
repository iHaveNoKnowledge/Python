import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

from modules.selenium_webdriver import ChromeDriver
from modules.unified_table_data import UnifyData


class MainApp:
    def __init__(self, root):
        self.root = root
        # * for query
        # self.data_file_dir = ''
        self.data_file_dir = tk.StringVar(value="")
        self.file_name = tk.StringVar(value="ไม่มีไฟล์")
        self.sku = tk.StringVar(value="")
        self.set_num = tk.StringVar(value="")
        # * เอาไว้เก็บ object ที่รับค่าจาก excel, import file, อะไรก็ตามที่เป็น data table ที่นำเข้ามา
        self.data_table = {}
        self.create_main_window()
        # ใช้ class unified
        ChromeDriver()

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
        sku = self.sku.get()
        set = self.set_num.get()
        data_dict = self.data_table.get_result(sku, set)
        #! wip you are here

        # self.search_query = self.entered_order.get()
        # print("search() ทำงานและได้ผลลัพธ์: ", self.search_query)
        # self.entered_order.set("")
        # if self.search_query != "":
        #     self.report_log.config(state=NORMAL)
        #     self.report_log.delete("1.0", "end")
        #     # self.report_log.insert(END, self.search_query + "\n")
        #     self.report_log.config(state=DISABLED)
        # else:
        #     self.report_log.config(state=NORMAL)
        #     self.report_log.delete("1.0", "end")
        #     self.report_log.config(state=DISABLED)

        # self.search_complete = threading.Event()
        # # self.search_complete.set()
        # self.search_thread = threading.Thread(
        #     target=lambda: self.order_search(self.search_query, self.search_complete))
        # self.get_tabs_thread = threading.Thread(target=self.bot.get_tabs)

        # print("เริ่มThreadใหม่")
        # self.search_thread.start()
        # self.display_bot_status_label.config(
        #     text=f"Bot Status: ᕦʕ •ᴥ•ʔᕤ Botกำลังทำงาน", bg="#cf1313", fg="#ffffff")
        # # ปิดชั่วคราว get_tabs
        # try:
        #     self.get_tabs_thread.start()
        # except EXCEPTION as err:
        #     print("err จาก get_tabs", err)

        # timer = threading.Timer(0.2, self.on_thread_done)
        # timer.start()

    def create_widgets(self):
        # * Dir locator component
        # * > Button
        self.find_dir_btn = tk.Button(
            self.locator_frame, text=f"ใส่ Import File", command=self.add_file, bg="#969696")
        self.find_dir_btn.grid(row=0, column=0, padx=(5, 0))
        # * > Labels
        self.find_dir_display = tk.Label(
            self.locator_frame, textvariable=self.file_name)
        self.find_dir_display.grid(row=0, column=1, padx=(5, 0))

        # * Code Display Component
        # * > Labels
        self.code_label = tk.Label(self.result_frame, text="Code ", bg="#FFF")
        self.code_label.grid(row=0, column=0, padx=(5, 0),
                             pady=(0, 5), sticky='w')
        # * > Input
        self.code_display = tk.Entry(
            self.result_frame, width=20,  borderwidth=1, textvariable=self.sku, relief="groove")
        self.code_display.grid(row=0, column=1, padx=(1, 0))

        # * Set Number Display Component
        # * > Labels
        self.set_num_label = tk.Label(
            self.result_frame, text="Set Number ", bg="#FFF",)
        self.set_num_label.grid(row=1, column=0, padx=(
            5, 0),  pady=(0, 5),  sticky='w')
        # * > Input
        self.set_num_display = tk.Entry(
            self.result_frame, width=20,  borderwidth=1, textvariable=self.set_num, relief="groove")
        self.set_num_display.grid(row=1, column=1, padx=(1, 0), sticky='w')

        # * Execution Btn Component
        # * > BTN
        self.execute_btn = tk.Button(
            self.execute_frame, text="Execute!!", command=self.search)
        self.execute_btn.grid()

    def create_main_window(self):
        self.root.geometry("400x400+400+300")

        self.root.title("Auto SN v0.2")

        # * use CANVAS as BG #################
        self.canvas = tk.Canvas(self.root, bg="#bdbdbd")
        # Expand to fill the whole window
        self.canvas.pack(fill="both", expand=True)

        # * FRAMES ###########################
        # *> Frame 1 Dir locator
        self.locator_frame = tk.Frame(
            self.canvas, padx=5, pady=5, borderwidth=1, relief="groove", bg="#a1a1a1")
        self.locator_frame.pack(side='top', padx=5, pady=7, anchor='w')

        # *> Frame 2 Search result Display
        self.result_frame = tk.Frame(
            self.canvas, padx=5, pady=5, borderwidth=1, relief="groove", bg="#a1a1a1")
        self.result_frame.pack(side='top', padx=5, pady=7, anchor='w')

        # *> Frame 3 Execution frame
        self.execute_frame = tk.Frame(
            self.canvas, padx=5, pady=5, borderwidth=1, bg="#bdbdbd")
        self.execute_frame.pack(side='top', padx=(90, 5), pady=7, anchor='w')

        self.create_widgets()


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
