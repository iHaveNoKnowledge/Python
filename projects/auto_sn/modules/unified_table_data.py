import pandas as pd
import numpy as np



#! ใช้ read_excel แบบนี้มันจะทำงานแบบทันที
# data_frames = pd.read_excel(file_path, sheet_name=None, dtype=str)
# qty_series = data_frames['สรุป']['qty']
# print(data_frames)
# print("เช็ค", qty_series)

# for sheet_name, df in data_frames.items():
#     print(f"ข้อมูลใน Sheet: {sheet_name}")
#     print(df)

#     if 'qty' in df.columns:
#         data_frames[sheet_name]['qty'] = data_frames[sheet_name]['qty'].astype(
#             int)
#     else:
#         continue

# #* สร้าง State สำหรับเก็บค่าจาก file
# data_state = {}

# #! #! พัง
# # for sheet_name in data_frames:
# #     if 'spec' in df.columns :
# #         print(f"Sheet: {sheet_name} จะถูกจัดเก็บใน items_list")
# #     else:

# #         print(f"Sheet: {sheet_name} ไม่มี รายการสินค้า")

#! ใช้แบบ ExcelFile มันจะทำงานแบบ lazy loading ซึ่งหมายความว่ามันจะไม่โหลดข้อมูลจริงจนกว่าคุณจะใช้ method parse() เพื่อโหลดข้อมูลจากแผ่นข้อมูลในไฟล์ Excel นั้นๆ ทำให้มีประสิทธิภาพมากขึ้น

file_path = r"C:\Users\CSH0041\Downloads\DATA Program nHack.xlsx"
excel_file = pd.ExcelFile(file_path)
sheet_names = excel_file.sheet_names

data_state = {}
# * อยากให้col ไหนเป็น int มาเติมที่ list 'must_be_int_cols'
must_be_int_cols = ['qty']
for sheet_name in sheet_names:
    df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)

    # * ปรับ dtype
    if any(must_be_int_cols) in df.columns:
        for col in must_be_int_cols:
            try:
                df[col].astype(int)
            except:
                continue

    lowercase_columns = [column.lower() for column in df.columns]
    df.columns = lowercase_columns
    if 'spec' in lowercase_columns:
        print(f"ค่าของ Sheet {sheet_name} จะถูกจัดเก็บใน key items_list")
        data_state['items_list'] = df
    elif 'set' in lowercase_columns:
        print(f"Sheet: {sheet_name} จะถูกจัดเก็บใน key sn")
        data_state['sn'] = df

# print(f"items_list: {data_state['items_list']}")
# print(f"items_list type: {type(data_state['items_list'])}")
# print(f"sn: {data_state['sn']}")
# print(f"sn type: {type(data_state['sn'])}")
# print(f"data_state: {data_state}")
# print(f"data_state: {pd.DataFrame(data_state)['sn']}")
barcode_receive = '758/001'
find_dict = data_state['sn'][data_state['sn']
                             ['set'] == barcode_receive].iloc[0]
print('all')
print(find_dict)
