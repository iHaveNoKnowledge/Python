import pandas as pd

# * เตรียม data frame
file_path = r"C:\Users\ONLINE_MIS\Desktop\Trans-am 31-01-2022\Projects\python\Python\test_pandas01\Order.toship.20230903_20230914 (1).xlsx"
data_frame = pd.read_excel(file_path)

# * เลือก Order
order_input = input("Order?: ")
print("Order is: ", order_input)
filter_data = data_frame[(data_frame["หมายเลขคำสั่งซื้อ"]
                          == order_input)]
bool_filter = data_frame["หมายเลขคำสั่งซื้อ"] == order_input
print("boolfilter มี type เป็นไร", type(bool_filter))
print("ใช้ boolfilter", data_frame[bool_filter])
# print("find in data_frame: ", filter_data)

# * เลือก Column มาแสดงผล
# order_status = filter_data["สถานะการสั่งซื้อ"]
# print(order_input, "มีสถานะ: ", order_status)
