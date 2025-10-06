import customtkinter as ctk
import threading
import time

# ปรับธีม
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# สร้างหน้าต่างหลัก
app = ctk.CTk()
app.geometry("400x250")
app.title("Thread Control Example")

# ตัวแปรควบคุมการหยุด thread
stop_event = threading.Event()
worker_thread = None

# ฟังก์ชันทำงานใน thread
def background_task():
    count = 0
    while not stop_event.is_set():
        count += 1
        print(f"กำลังทำงาน... {count}")
        time.sleep(1)
    print("หยุดการทำงานแล้วจ้า~")

# ปุ่มเริ่ม thread
def start_thread():
    global worker_thread
    if worker_thread is None or not worker_thread.is_alive():
        stop_event.clear()
        worker_thread = threading.Thread(target=background_task)
        worker_thread.start()
        status_label.configure(text="กำลังทำงาน~", text_color="green")
    else:
        status_label.configure(text="Thread ทำงานอยู่แล้ว!", text_color="orange")

# ปุ่มหยุด thread
def stop_thread():
    stop_event.set()
    status_label.configure(text="หยุดเรียบร้อยแล้ว~", text_color="red")

# UI components
start_button = ctk.CTkButton(app, text="Start", command=start_thread)
stop_button = ctk.CTkButton(app, text="Stop", command=stop_thread)
status_label = ctk.CTkLabel(app, text="ยังไม่ได้เริ่ม", text_color="gray")

start_button.pack(pady=10)
stop_button.pack(pady=10)
status_label.pack(pady=10)

# รันแอป
app.mainloop()
