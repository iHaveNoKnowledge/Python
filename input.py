import pandas as pd

# * เตรียม data frame
file_path = r"./test_pandas01/Order.toship.20230903_20230914 (1).xlsx"
data_frame = pd.read_excel(file_path)

# * เลือก Order
order_input = input("Order?: ")
print("Order is: ", order_input)
filter_data = data_frame[(data_frame["หมายเลขคำสั่งซื้อ"]
                          == order_input)]
filtered_row = data_frame["หมายเลขคำสั่งซื้อ"] == order_input
print("boolfilter มี type เป็นไร", type(filtered_row))
print("ใช้ boolfilter", data_frame[filtered_row]['สถานะการสั่งซื้อ'])
# print("find in data_frame: ", filter_data)

# * ############# หาค่าจาก ตาราง ###############################
# * ประเภทใบกำกับภาษี
# * เลือก Column มาแสดงผล โดยการใช้ iloc[0]
if data_frame[filtered_row]['ประเภทใบกำกับภาษี'].iloc[0] == 'Personal':
    tax_bool = False
else:
    tax_bool = True

# *  ของมีอะไรบ้าง
# products_list = data_frame[filtered_row]['เลขอ้างอิง SKU (SKU Reference No.)', 'ชื่อสินค้า'].to_dict(
# )
products_list = data_frame[filtered_row].to_dict(
)


# * แสดงผล
print("ใบกำกับ?", tax_bool)
print("สินค้ามีไรบ้าง", products_list)
