import tkinter as tk
from tkinter import filedialog
from customtkinter import *
import threading
import time


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
        self.create_main_window()

    def resetAllValue(self):
        self.data_file_dir.set("")
        self.sku.set("")
        self.set_num.set("")

    def resetInput(self):
        self.sku.set("")
        self.set_num.set("")

    def add_file(self):
        self.data_file_dir.set('')
        self.data_file_dir.set(filedialog.askopenfilename(
            title="Select an import file"))
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

    def search(self):
        try:
            sku = self.sku.get().strip()
            set = self.set_num.get().strip()

            self.clear_log()
            data_dict = self.data_table.get_result(sku, set)
            self.update_log(f"ชื่อชุด: {sku}")
            self.update_log(f"เลขSet: {set}")
            self.sku.set("")
            self.set_num.set("")

            try:
                self.chromdriver_controller.operation_start(sku, data_dict)
            except ValueError as e:
                error_message = str(e)
                self.update_log(error_message)
        except:
            self.update_log("พัง")
            raise ValueError('search พัง: ', traceback.format_exc())

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

    def kill_task(self):
        if self.current_task and self.current_task.is_alive():
            self.stop_event.set()
            self.current_task.join()

    def start_task(self, input={}):
        if self.current_task and self.current_task.is_alive():
            self.stop_event.set()
            self.current_task.join()
        self.stop_event.clear()
        self.current_task = threading.Thread(target=self.my_function)
        self.current_task.start()
        print("เริ่มการทำงาน")
        print("input: ", input)

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

    def create_widgets(self):
        self.pady = (0, 16)

        self.qr_display = CTkLabel(
            self.frame_top, text="QR Input", width=70, anchor=tk.W)
        self.qr_display.grid(row=0, column=0, padx=(0, 0), pady=self.pady)

        self.qr_input = CTkEntry(self.frame_top, width=180)
        self.qr_input.grid(row=0, column=1, pady=self.pady, sticky="w")

        self.qr_btn = CTkButton(self.frame_top, width=70, anchor=tk.W,
                                text="Start", command=self.on_start_button_click)
        self.qr_btn.grid(row=0, column=2, padx=(
            0, 0), pady=self.pady, sticky="w")

        self.order_label = CTkLabel(
            self.frame_top, text="เลขที่คำสั่งซื้อ", width=70, anchor=tk.W)
        self.order_label.grid(row=0, column=3, padx=(10, 10), pady=self.pady)

        self.order_display = CTkEntry(
            self.frame_top, width=180, state="readonly")
        self.order_display.grid(row=0, column=4, padx=(1, 1), pady=self.pady)

        self.name_label = CTkLabel(
            self.frame_top, text="ชื่อออกบิล", width=70, anchor=tk.W)
        self.name_label.grid(row=1, column=0, padx=(0, 0))

        self.name_display = CTkEntry(self.frame_top, width=300)
        self.name_display.grid(row=1, column=1, padx=(0, 1))

        self.tax_num_label = CTkLabel(
            self.frame_top, text="เลขผู้เสียภาษี", width=70, anchor=tk.W)
        self.tax_num_label.grid(row=1, column=3, padx=(10, 10))

        self.tax_num_display = CTkEntry(
            self.frame_top, width=180, state="readonly")
        self.tax_num_display.grid(row=1, column=4, padx=(0, 1))

        self.address_label = CTkLabel(
            self.frame_1, text="ที่อยู่ ", width=70, anchor=tk.W)
        self.address_label.grid(row=0, column=0, padx=(
            0, 0), pady=(0, 5), sticky='nw')

        self.address_text = CTkTextbox(self.frame_1, width=300, height=100)
        self.address_text.insert("0.0", "Ready" + '\n')
        self.address_text.configure(state="disabled")
        self.address_text.grid(row=0, column=1, padx=(1, 0))

        self.frame_1_1 = CTkFrame(master=self.frame_1)
        self.frame_1_1.grid(row=0, column=2, sticky='nw', padx=5)

        address_components_settings = [
            {"label": "จังหวัด", "position": {"row": 0, "column": 1}},
            {"label": "อําเภอ/เขต", "position": {"row": 0, "column": 3}},
            {"label": "ตำบล/แขวง", "position": {"row": 0, "column": 5}},
            {"label": "รหัสไปรษณีย์", "position": {"row": 1, "column": 1}},
            {"label": "เบอร์โทร.", "position": {"row": 1, "column": 3}},
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
            )
            self.address_sub_input.grid(
                row=item['position']['row'], column=item['position']['column']+1, padx=(1, 0), sticky='NW')

        # * Frame Bottom Section /////////////////////////////////////////////////////////////////////////////
        bottom_component_settings = [
            {"label": "สินค้า", "position": {"row": 0, "column": 0}},
            {"label": "ของแถม", "position": {"row": 0, "column": 1}},
        ]

        for item in bottom_component_settings:
            # * Frame1 Section /////////////////////////////////////////////////////////////////////////////
            # * > address display Conponent /////////////////////
            # * >> Label
            self.address_label = CTkLabel(
                self.frame_bottom, text=item['label'], width=70, anchor=tk.W)
            self.address_label.grid(row=item['position']['row'], column=item['position']['column'], padx=(
                0, 5), pady=(0, 5), sticky='nw')
            # * > DisplayField
            self.log_display = CTkTextbox(
                self.frame_bottom, height=150, state=tk.DISABLED)
            self.log_display.grid(
                row=item['position']['row'] + 1, column=item['position']['column'], padx=(0, 5), pady=(0, 5), sticky='w')

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
        self.frame_bottom = CTkFrame(
            master=self.canvas,
        )
        self.frame_bottom = CTkFrame(master=self.canvas)
        self.frame_bottom.pack(side='bottom', padx=5, pady=7, anchor='w')

        self.create_widgets()

    def on_start_button_click(self):
        threading.active_count()
        thread = threading.Thread(target=self.start_task)
        thread.start()


def main():
    def on_closing():
        print('ui window is closed')
        root.destroy()
        main_gui.kill_task()

    def ctrl_saraea_copy(event):
        ctrl_state = event.state & 0x4 != 0
        if ctrl_state and event.keycode == 67:
            event.widget.event_generate("<<Copy>>")

    root = CTk()
    # * options
    # * > ทำลาย root tkInter เมื่อmain_guiถูกปิด เพื่อไม่ให้มีการทำงานตกค้าง
    root.protocol("WM_DELETE_WINDOW", on_closing)
    # * > ลืมไปละ น่าจะเกี่ยวกับช่องไฟ
    root.columnconfigure(0, weight=1)

    # * > ปรับขนาดจอ
    # root.resizable(False, False)

    # * > ทำให้กด copy จากภาษาอะไรก็ได้
    root.bind('<Key>', ctrl_saraea_copy)

    # * Create Instance
    #* เก็บ ตัว object ของ app ไว้ใน main_gui เพื่อเรียกใช้ functions kill_task เมื่อ tkinter ถูกปิด
    main_gui = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
