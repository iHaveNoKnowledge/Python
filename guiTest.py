import tkinter as tk  # python3
from functionsForGui import mySumFunction

# * Functions


def button_click():
    value = int(txt.get())

    result = mySumFunction(value, 1)
    print("ผลลัพธฺ", result)
    print("Button clicked")


def close_Gui():
    try:
        if root.winfo_exists():
            try:
                root.destroy()
            except:
                pass
    except:
        print("ไม่มี ไอ้ root แล้ว")

    try:
        if canvas.winfo_exists():
            try:
                canvas.destroy()
            except:
                pass
    except:
        print("ไม่มี ไอ้ canvas แล้ว")


# * กำหนดหน้าต่างหลัก
root = tk.Tk()  # สร้าง Body
root.title("Root Widget")

# canvas = tk.Toplevel(root)
# canvas.title("Canvas Widget")

# * create frame
frame1 = tk.Frame(root)
frame1.pack(anchor="w")

frame2 = tk.Frame(root)
frame2.pack(anchor="w")


# กำหนดขนาดหน้าจอ

root.geometry("300x400+0+0")
# canvas.geometry("800x600-0+0")


# * widget Label
label = tk.Label(frame1, text="Hello world",
                 foreground="yellow", font=20, bg="black")
# packคือเอา widget วางลงไปใน root gui
label.grid(row=0, column=0)

label2 = tk.Label(frame1, text="OrderNumber: ", fg="blue", bg="white")
label2.grid(row=1, column=0)

# * widget  btn
b1 = tk.Button(frame1, text="กดคลำนวน",
               command=button_click, fg="white", bg="black")
b1.grid(row=1, column=2)

b2 = tk.Button(frame1, text="BTN2", command=lambda: tk.Label(
    frame2, text="Hi", ).pack())
b2.grid(row=1, column=3)


# * widget input entry
txt = tk.StringVar()
num = 0
entry_input = tk.Entry(frame1, textvariable=txt).grid(row=1, column=1)

# # * widget text
# text_display = tk.Text().grid(row=2, column=0, columnspan=4)


# * เมื่อมี Body  Body จะเริ่มโชว์ GUI ได้
# root.after(5555, close_Gui)
root.mainloop()
