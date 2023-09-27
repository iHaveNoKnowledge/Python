# %%
import pandas as pd
import re

# %%

# *  function
# def clean_address(address):
#     keywords = ["เขต", "แขวง", "ต.", "ตำบล", "อ.", "อำเภอ", "จ.", "จังหวัด"]

#     # ตรวจสอบว่าสตริงมีคำ "จังหวัด" และ ("เขต" หรือ "แขวง") หรือไม่
#     if "จังหวัด" in address and any(keyword in address for keyword in ["เขต", "แขวง"]):
#         # ลบคำ "จังหวัด" ออกจากสตริง
#         address = address.replace("จังหวัด", "")
        
#     if "\n" in address:
#         address = address.replace('\n', " ")

#     for keyword in keywords:
#         if keyword in address:
#             address = address.replace(keyword + " ", keyword)
#             if keyword in ["เขต", "แขวง", "ต.", "ตำบล", "อ.", "อำเภอ"]:
#                 index = address.find(keyword)
#                 if index != -1:
#                     next_space = address[index + len(keyword):].find(" ")
#                     if next_space != -1:
#                         sub_string = address[index:index + len(keyword) + next_space]
#                         if sub_string.count(" ") > 1:
#                             address = address.replace(sub_string, keyword + " " + sub_string.replace(" ", "", 1))
#     return address

# def clean_duplicate_parts(address):
#     # ใช้ regex เพื่อค้นหาและลบคำย่อที่มีส่วนที่มากกว่าคำเต็ม
#     pattern = r'(ต\..+?)\s+?(ตำบล|อ\..+?)\s+?(อำเภอ|จ\..+?)\s+?(จังหวัด|โครงการ)'
    
#     matches = re.findall(pattern, address)
#     if matches:
#         cleaned_address = address
#         for match in matches:
#             full_word, abbr_word1, abbr_word2, abbr_word3 = match
#             if len(full_word) > len(abbr_word1):
#                 cleaned_address = cleaned_address.replace(abbr_word1, full_word)
#             if len(full_word) > len(abbr_word2):
#                 cleaned_address = cleaned_address.replace(abbr_word2, full_word)
#             if len(full_word) > len(abbr_word3):
#                 cleaned_address = cleaned_address.replace(abbr_word3, full_word)
#     else:
#         cleaned_address = address

#     return cleaned_address
# def clean_address(address):
#     def clean_duplicate_parts(address):
#         # ใช้ regex เพื่อค้นหาและลบคำย่อที่มีส่วนที่มากกว่าคำเต็ม
#         pattern = r'(ต\..+?)\s+?(ตำบล|อ\..+?)\s+?(อำเภอ|จ\..+?)\s+?(จังหวัด)'
        
#         matches = re.findall(pattern, address)
#         if matches:
#             cleaned_address = address
#             for match in matches:
#                 full_word, abbr_word1, abbr_word2, abbr_word3 = match
#                 if len(full_word) > len(abbr_word1):
#                     cleaned_address = cleaned_address.replace(abbr_word1, full_word)
#                 if len(full_word) > len(abbr_word2):
#                     cleaned_address = cleaned_address.replace(abbr_word2, full_word)
#                 if len(full_word) > len(abbr_word3):
#                     cleaned_address = cleaned_address.replace(abbr_word3, full_word)
#         else:
#             cleaned_address = address

#         return cleaned_address

#     keywords = ["เขต", "แขวง", "ต.", "ตำบล", "อ.", "อำเภอ", "จ.", "จังหวัด"]

#     # ตรวจสอบว่าสตริงมีคำ "จังหวัด" และ ("เขต" หรือ "แขวง") หรือไม่
#     if "จังหวัด" in address and any(keyword in address for keyword in ["เขต", "แขวง"]):
#         # ลบคำ "จังหวัด" ออกจากสตริง
#         address = address.replace("จังหวัด", "")
        
#     if "\n" in address:
#         address = address.replace('\n', " ")

#     # เริ่มต้นโดยการแยกคำด้วยช่องว่าง
#     parts = address.split()
    
#     # สร้าง list เพื่อเก็บคำที่ไม่ใช่คำย่อ
#     cleaned_parts = []
    
#     for part in parts:
#         # ตรวจสอบว่าคำนี้เป็นคำย่อหรือไม่
#         is_abbreviation = any(part.startswith(keyword) for keyword in ["ต.", "อ.", "จ."])
        
#         if not is_abbreviation:
#             cleaned_parts.append(part)
    
#     # นำคำที่ไม่ใช่คำย่อมาเชื่อมกลับเป็นสตริงใหม่
#     cleaned_address = ' '.join(cleaned_parts)
    
#     # ลบคำที่มีส่วนที่เหมือนกันออก
#     cleaned_address = clean_duplicate_parts(cleaned_address)
    
#     # แก้ไขเครื่องหมายช่องว่างที่เหลือหลังการลบคำ
#     cleaned_address = cleaned_address.replace("  ", " ")
    
#     return cleaned_address


# %%
def clean_address(address):
    def clean_duplicate_parts(address):
        # ใช้ regex เพื่อค้นหาและลบคำย่อที่มีส่วนที่มากกว่าคำเต็ม
        pattern = r'(ต\..+?)\s+?(ตำบล|อ\..+?)\s+?(อำเภอ|จ\..+?)\s+?(จังหวัด)'
        
        matches = re.findall(pattern, address)
        if matches:
            cleaned_address = address
            for match in matches:
                full_word, abbr_word1, abbr_word2, abbr_word3 = match
                if len(full_word) > len(abbr_word1):
                    cleaned_address = cleaned_address.replace(abbr_word1, full_word)
                if len(full_word) > len(abbr_word2):
                    cleaned_address = cleaned_address.replace(abbr_word2, full_word)
                if len(full_word) > len(abbr_word3):
                    cleaned_address = cleaned_address.replace(abbr_word3, full_word)
        else:
            cleaned_address = address
        print("After_Clean_dup: ",cleaned_address)
        return cleaned_address

    keywords = ["เขต", "แขวง", "ต.", "ตำบล", "อ.", "อำเภอ", "จ.", "จังหวัด"]

    # ตรวจสอบว่าสตริงมีคำ "จังหวัด" และ ("เขต" หรือ "แขวง") หรือไม่
    if "จังหวัด" in address and any(keyword in address for keyword in ["เขต", "แขวง"]):
        # ลบคำ "จังหวัด" ออกจากสตริง
        address = address.replace("จังหวัด", "")
        
    if "\n" in address:
        address = address.replace('\n', " ")

    # เริ่มต้นโดยการแยกคำด้วยช่องว่าง
    parts = address.split()
    
    # สร้าง list เพื่อเก็บคำที่ไม่ใช่คำย่อ
    cleaned_parts = []
    
    for part in parts:
        # ตรวจสอบว่าคำนี้เป็นคำย่อหรือไม่
        is_abbreviation = any(part.startswith(keyword) for keyword in ["ต.", "อ.", "จ."])
        
        if not is_abbreviation:
            cleaned_parts.append(part)
    
    # นำคำที่ไม่ใช่คำย่อมาเชื่อมกลับเป็นสตริงใหม่
    cleaned_address = ' '.join(cleaned_parts)
    
    # ลบคำที่มีส่วนที่เหมือนกันออก
    cleaned_address = clean_duplicate_parts(cleaned_address)
    
    # แก้ไขเครื่องหมายช่องว่างที่เหลือหลังการลบคำ
    cleaned_address = cleaned_address.replace("  ", " ")
    
    return cleaned_address

# address = '124/10 ม.4 ต.โคกสำโรง อ.โคกสำโรง จ.ลพบุรี 15120  อำเภอโคกสำโรง จังหวัดลพบุรี 15120'
# cleaned_address = clean_address(address)
# cleaned_address


# * เตรียม data frame
def get_data_frame():
    global data_frame
    file_path = r"test\test_pandas01\excel\Order.toship.20230903_20230914 (1).xlsx"
    
    try:
        data_frame = pd.read_excel(file_path)
        if data_frame.empty :
            print("ไม่มี Data Frame")
        else:
            print("มี Data Frame")
    except FileNotFoundError:
        print("File not found.") 
    except NameError as e:
        print(f"ตัวแปร '{e.name}' ไม่มีอยู่จริง")
    except Exception as e:
        print(f"อะไรสักอย่างพัง {e}")
## Todo 
get_data_frame()

# * รับ InputOrder ####################################################################
order= "230909SXCMTRXN"

def order_receive(order):
    
    order_input = order
    print("Order is: ", order_input)
    filter_data = data_frame[(data_frame["หมายเลขคำสั่งซื้อ"]
                            == order_input)]
    
    # target_row เป็น row ที่เลือกจากเลข Order ที่รับเข้ามา
    target_row = data_frame["หมายเลขคำสั่งซื้อ"] == order_input
    if data_frame[target_row]['สถานะการสั่งซื้อ'].iloc[0] == "ที่ต้องจัดส่ง":
        print("boolfilter มี type เป็นไร", type(target_row))
        print("สถานะOrder: ", data_frame[target_row]['สถานะการสั่งซื้อ'].iloc[0])
        # print("find in data_frame: ", filter_data)
        # * ############# หาค่าจาก ตาราง ###############################
        # * ประเภทใบกำกับภาษี
        # * เลือก Column มาแสดงผล โดยการใช้ iloc[0]
        global tax_bool
        if data_frame[target_row]['ประเภทใบกำกับภาษี'].iloc[0] == 'Personal':
            tax_bool = False
        else:
            tax_bool = True

        # *  ของมีอะไรบ้าง
        # products_list = data_frame[target_row]['เลขอ้างอิง SKU (SKU Reference No.)', 'ชื่อสินค้า'].to_dict(
        # )
        products_list = data_frame[target_row].to_dict(
        )
        # * แสดงผล
        print("ใบกำกับ?", tax_bool)
        # pd.DataFrame(products_list)
        # products_list

        # data_frame = target_row[target_row].map(lambda x: x.strip() if isinstance(x, str) else x)


        print("ไม่มีใบกำกับ")
        # cust_name = data_frame[target_row].ชื่อ[0]
        address = filter_data.iat[0,15]
        print("ข้อความ",address)
        # cleaned_address = clean_duplicate_parts(address)
        cleaned_address = clean_address(address)
        # print(data_frame[target_row].ชื่อ[0])
        # print(data_frame.iat[0,15])
        print("Addressที่คลีนแล้ว: ",cleaned_address)
        # print(data_frame.iat[0,16], data_frame.iat[0,18], data_frame.iat[0,19], data_frame.iat[0,20])

        # data_frame[target_row].ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป[0]

        # data_frame[target_row].หมายเลขคำสั่งซื้อ
        # print("สินค้ามีไรบ้าง", products_list)
    else :
        print("Orderนี้ ขอยกเลิกมานะ")
## Todo
order_receive(order)

# %%
def amphoe_finder():
    text = '124/10 ม.4 ต.โคกสำโรง อ.โคกสำโรง จ.ลพบุรี 15120  อำเภอโคกสำโรง จังหวัดลพบุรี 15120'

    # ใช้ regex เพื่อค้นหาข้อความ 'อ.โคกสำโรง' และ 'อำเภอโคกสำโรง' แยกออกจากกัน
    matches = re.findall(r'อ\.(.*?) |อำเภอ(.*?) ', text)

    if len(matches) == 2:
        amphoe = matches[0][0]
        aumper = matches[1][1]
        print("อ.{} และ อำเภอ{}".format(amphoe, aumper))
    else:
        print("ไม่พบข้อมูลที่ต้องการ")




# %%
def cus_address_cleaner():
    text = '124/10 ม.4 ต.โคกสำโรง อ.โคกสำโรง จ.ลพบุรี 15120  อำเภอโคกสำโรง จังหวัดลพบุรี 15120'

    # ใช้ regex เพื่อค้นหาและนับจำนวนข้อความ 'อ.|อำเภอ'
    # matches = re.findall(r'(อ\.(.*?)\ |อำเภอ(.*?) |ต\.(.*?)\ |ตำบล(.*?)\ )', text)
    matches = re.findall(r'(อ\.|อำเภอ)', text)

    print(matches)

    # หาจำนวนข้อความที่ตรงกับรูปแบบ
    amphoe_count = matches.count('อ.|อำเภอ')

    # ถ้ามี 'อ.|อำเภอ' มากกว่า 1 ครั้ง
    if amphoe_count > 1:
        # หาคำเต็มและคำย่อ
        full_word = re.search(r'อ\.(.*?) |อำเภอ(.*?) ', text)
        
        # ถ้าหากมีคำเต็มให้ใช้คำเต็ม
        if full_word:
            amphoe_full = full_word.group(1) if full_word.group(1) else full_word.group(2)
            
            # แทนที่ข้อความ 'อ.|อำเภอ' ทั้งหมดในข้อความด้วยคำเต็ม
            result = re.sub(r'อ\.(.*?) |อำเภอ(.*?) ', amphoe_full, text)
            
            print(result)
        else:
            print("ไม่พบคำเต็มที่ต้องการ")
    else:
        print(text)


# %%
def issue_address_format():
    text = '124/10 ม.4 ต.โคกสำโรง อ.โคกสำโรง จ.ลพบุรี 15120  อำเภอโคกสำโรง จังหวัดลพบุรี 15120'

    # ใช้ regex เพื่อค้นหาและนับจำนวนครั้งที่พบข้อความ 'อ.|อำเภอ' ใน amphoe
    amphoe_count = len(re.findall(r'อ\.|อำเภอ', text))

    # ใช้ regex เพื่อค้นหาและนับจำนวนครั้งที่พบข้อความ 'ต.|ตำบล' ใน tambon
    tambon_count = len(re.findall(r'ต\.|ตำบล', text))

    # ใช้ regex เพื่อค้นหาและนับจำนวนครั้งที่พบข้อความ 'จ.|จังหวัด' ใน province
    province_count = len(re.findall(r'จ\.|จังหวัด', text))

    print("จำนวน 'อ.|อำเภอ':", amphoe_count)
    print("จำนวน 'ต.|ตำบล':", tambon_count)
    print("จำนวน 'จ.|จังหวัด':", province_count)




# %%
def issue_address_format2():
    text= '124/10 ม.4 ต.โคกสำโรง อ.โคกสำโรง จ.ลพบุรี 15120  อำเภอโคกสำโรง จังหวัดลพบุรี 15120'

    is_bangkok = "กรุงเทพ" in text

    amphoe_count = len(re.findall(r'อ\.|อำเภอ', text))
    tambon_count = len(re.findall(r'ต.|ตำบล', text))
    province_count = len(re.findall(r'จ.|จังหวัด', text))

    print("กรุงเทพปะ", is_bangkok)
    print("อำเภอ", amphoe_count)

    print("ตำบล",tambon_count)
    print("จังหวัด",province_count)


