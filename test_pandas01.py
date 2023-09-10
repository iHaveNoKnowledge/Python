import pandas as pd

file_path = './test_pandas01/Order.toship.20230820_20230826.xlsx'
data_frame = pd.read_excel(file_path)
print(type(data_frame))
filtered_data = data_frame[(data_frame['หมายเลขคำสั่งซื้อ'] == '230823EJW39APX')] 
print(filtered_data[['หมายเลขคำสั่งซื้อ','สถานะการสั่งซื้อ']])

# items = ("ตู่", "ป้อม", "เต้")
# idx = [10,1,2]
# x = pd.Series(items)
# # print(x)

# colors= {"green":"เขียว", "char2":"ลุงตู่", "char3":"ลุงป้อม"}
# dict_x = pd.Series(colors)
# print(f"""{dict_x.to_frame()}""")