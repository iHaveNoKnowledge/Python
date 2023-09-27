
from tkinter import *
from tkinter import messagebox
from test_auto_cus_name_MKII import *
# %run test_input_receiver.ipynb


get_data_frame()


window1 = Tk()
window1.title("Autosamatic")

# ---
 
# # CUSTOM WINDOWS ##################################################
# > Window1
window1.geometry("800x600+400+300")
window1.configure(bg="#444")



# # FUNCTIONS #########################################
def search():
    search_query = entered_order.get()  
    print("search() ทำงานและได้ผลลัพธ์: ",search_query)
    entered_order.set("")
    report_log.config(state=NORMAL)
    report_log.insert(END, search_query + "\n")
    report_log.config(state=DISABLED)
    order_receive(search_query)


# Subwindow Close
def on_subwindow_close(sub_window):
    sub_window.destroy()

# ---

 
# # FRAMES ######################################################
# > Frame1
entry_frame = Frame(window1, padx=5, pady=5, bg="#444")
entry_frame.pack()

# > Frame2
log_frame = Frame(window1, bg="#444")
log_frame.pack(side='bottom', pady=(0,30))

# ---

# # **WIDGETS** ####################################################


# > Labels
inp1_label_order = Label(entry_frame, text="Order: ", bg="#FFF", width=10)
inp1_label_order.grid(row=0,column=0, padx=5)

# > Inputs
entered_order = StringVar()
inp1_order_input = Entry(entry_frame, textvariable=entered_order, width=50)
inp1_order_input.grid(row=0,column=2)

# > Buttons
inp1_search_btn = Button(entry_frame, text="ค้นหา", bg="#747474", command=search, width=10)
inp1_search_btn.grid(row=0,column=4, padx=5)

# > Log windows
report_log = Text(log_frame, state=DISABLED)
scrollbar= Scrollbar(log_frame, command=report_log.yview)
scrollbar.pack(side="right", fill="y") 
scrollbar.config()
report_log.pack(side='bottom', fill=X)
report_log.config(yscrollcommand=scrollbar.set)


# > Subwindow
window1_sub1 = Toplevel(window1)
window1_sub1.transient(window1)
window1_sub1.geometry("300x200+450+400")
window1_sub1.title("Data Source")
window1_sub1_label = Label(window1_sub1, text="")
window1.grab_set()



##*  function
def on_close():
    window1_sub1.destroy()
window1_sub1.protocol("WM_DELETE_WINDOW", on_close)

def select_api():
    global result 
    result = "API"
    print("Select API")
    window1_sub1.destroy()
window1_sub1.protocol("WM_DELETE_WINDOW", on_close)
    

def select_excel():
    global result 
    result = "Excel"
    print("Select Excel")
    window1_sub1.destroy()
window1_sub1.protocol("WM_DELETE_WINDOW", on_close)
    


##* btn
sub1_btn1 = Button(window1_sub1, text="API", command=select_api).pack()
sub1_btn2 = Button(window1_sub1, text="Excel", command=select_excel).pack()

result = ""
window1_sub1.wait_window()
window1.focus_set()
print("รอปิด")
print("Result: ", result)
if (result == "API"):
    print("เลือก API")
    report_log.config(state=NORMAL)
    report_log.insert(END, "ยังไม่พร้อมใช้งานแค่ทำปุ่มรอไว้เฉยๆ" + "\n")
    report_log.config(state=DISABLED)
elif (result == "Excel"):
    print("เลือก Excel")
    report_log.config(state=NORMAL)
    report_log.insert(END, "ใช้ Excel " + "\n")
    report_log.config(state=DISABLED)




##* optional
# result_sub = messagebox.askyesno("vcvcv", )


 
# ---

 
# # **RUN GUI** ########################################

# > Check DataFrame

# > Launch Gui


window1.mainloop()




