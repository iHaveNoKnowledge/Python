import pandas as pd

file_path = './test_pandas01/Order.toship.20230903_20230914 (1).xlsx'
data_frame = pd.read_excel(file_path)
filtered_data = data_frame[(
    data_frame['หมายเลขคำสั่งซื้อ'] == '230909SXC7FH38')]
order_status = filtered_data['สถานะการสั่งซื้อ']
products = filtered_data['เลขอ้างอิง SKU (SKU Reference No.)']
# print(filtered_data[['หมายเลขคำสั่งซื้อ','สถานะการสั่งซื้อ']])
print(filtered_data)
print(order_status)
print(order_status == 'ที่ต้องจัดส่ง')

print("ซื้อไรบ้าง")
print(products)

# if order_status == 'ที่ต้องจัดส่ง':
#     print("ต้องส่ง")
# else :
#     print("ยกเลิก")

# items = ("ตู่", "ป้อม", "เต้")
# idx = [10,1,2]
# x = pd.Series(items)
# # print(x)

# colors= {"green":"เขียว", "char2":"ลุงตู่", "char3":"ลุงป้อม"}
# dict_x = pd.Series(colors)
# print(f"""{dict_x.to_frame()}""")
