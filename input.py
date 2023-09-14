import pandas as pd

file_path = r"C:\Users\ONLINE_MIS\Desktop\Trans-am 31-01-2022\Projects\python\Python\test_pandas01\Order.toship.20230903_20230914 (1).xlsx"
data_frame = pd.read_excel(file_path)

order_input = input("Order?: ")
print("Order is: ", order_input)

filter_data = data_frame["หมายเลขคำสั่งซื้อ"] == order_input
print("find in data_frame: ", filter_data[0])
