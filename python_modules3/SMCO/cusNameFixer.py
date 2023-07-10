import re
def cusNameFixer(name2):
    name2 = name2[:-10] ##ลบตัวท้าย 10 หลัก
    if re.search("[(,)]", name2): ## หาว่ามีให้แมชหรือป่าว
        nameParentheses = re.search("[(,)]",name2)
        parenthesesIndex = nameParentheses.span() ##ใช้ method span() เพ่ือดึงค่า span โดยไอ span จะเป็นเลขบอกตำแหน่งของสิ่งที่เราหา (ทำไมไม่ทำเป็น attribute  555)
        slicingIndex = slice(parenthesesIndex[0]) 
        name2 = name2[slicingIndex]
        name2 = name2.strip() ##ตอนแรกๆไม่มีปัญหา หลังๆ มีปัญหา เรื่อง space ไม่เท่ากัน
    else:
        name2 = name2.strip()
    name2 += " :"
    print("มันมีชื่อว่า", name2)
    return name2

##"แอ๋ม ราชวานิช(ต่อ) ******99",
# test =   "ทวีวรรณ ปั้นอุดม (ครูวี)"
# cusNameFixer(test)

def cusNameFixer2(name):
    name = name+" "+name
    # print("ชื่อที่ได้หลัง fix: ", name)
    return name

def cusNameFixer3(name2):
    if re.search("[(,)]", name2): ## หาว่ามีให้แมชหรือป่าว
        nameParentheses = re.search("[(,)]",name2)
        parenthesesIndex = nameParentheses.span() ##ใช้ method span() เพ่ือดึงค่า span โดยไอ span จะเป็นเลขบอกตำแหน่งของสิ่งที่เราหา (ทำไมไม่ทำเป็น attribute  555)
        slicingIndex = slice(parenthesesIndex[0]) 
        name2 = name2[slicingIndex]
        name2 = name2.strip() ##ตอนแรกๆไม่มีปัญหา หลังๆ มีปัญหา เรื่อง space ไม่เท่ากัน
    else:
        name2 = name2.strip()
    name2 += " :"
    print("มันมีชื่อว่า", name2)
    return name2

def currencyRemover(text):
    cost = text.lstrip('฿')
    return cost
    # print(float(cost))

# test2 = "฿990"
# currencyRemover(test2)

### 94/72 ถ.เทศบาล4, ตำบลปากเพรียว, อำเภอเมืองสระบุรี, จังหวัดสระบุรี, 18000 << อันนีร้ splitแล้วมี ปัญหา เดะไว้ลองเทสดู
### Nalada.shop.official@gmail.com, บริษัท พรนาลดา จัำกัด, 0155564000594, 35/66, ตำบลศาลาแดง, อำเภอเมืองอ่างทอง, จังหวัดอ่างทอง, 14000 ,order 221213HCMPMS6Y
def addressExtractor(cusAddress):
    splited = cusAddress.split(",")
    return(splited)

# cusAddress = "35/66, ตำบลศาลาแดง, อำเภอเมืองอ่างทอง, จังหวัดอ่างทอง, 14000"
# cusAddress2 = "5/12​ หมู่​ 15​ ต.ท่าผา​ อ.บ้านโป่ง​ จ.ราชบุรี​ 70110, ตำบลท่าผา, อำเภอบ้านโป่ง, จังหวัดราชบุรี, 70110"

# splitedAddress = addressExtractor(cusAddress2)
# amper = splitedAddress[2].strip() ##result >> อำเภอบ้านโป่ง
# amperex = re.search("^อำเภอ.", amper) ##result >> อำเภอบ
# amperSlicer = slice(5, -1) ##ไม่มีผลลัพธ์
# amperReady = amper.replace("อำเภอ","")
# # print(amperReady) ## ณเวลาที่ทดลอง คือมันแก้ปัญหา สระ  ำ ได้ละ ปัญหาคือมันคืออักษาเดียวแต่เวลาโปรแกรมมันนับ index มันจะนะเป็น 2 ทำให้เวลาเจอสระ ำ มันจะตัดคำเกินเสมอ
# print(splitedAddress[0])

def customer_details(raw_data):
    ####กำหนดตัวแปร
    input_text = raw_data
    global tax_ID
    tax_ID = ""

    ####REGEX สำหรับ complie
    name_regex = re.compile(r"ชื่อที่ออกใบกำกับภาษี\s+(.*)") ##หาคำว่า "ชื่อที่ออกใบกำกับภาษี"+สเปซบา1ช่อง+วงเล็บหมายถึงเก็บค่าข้างใน จุด คือเอาอักษรไรก็ได้ยกเว้นขึ้นบรรทัดใหม่มีดอกจันตามหลังแปลว่าเงื่อนไขข้างหน้ามันจะเอาหรือไม่ก็ได้ ถ้ามีก็มีกี่ตัวก็ได้
    tax_ID_regex = re.compile(r"เลขประจำตัวผู้เสียภาษี\s+(.*)")
    tel_regex = re.compile(r"\b(\d+)")
    address_regex = re.compile(r"ที่อยู่\s+(.*)")
    
    ####ใช้ REGEX ค้นหา จาก INPUT
    global tax_name_g
    tax_name_g = re.search(name_regex, input_text).group(1) ##ถ้าไม่ใส่ group จะได้ object ถ้าใส่ group(0)จะได้ค่า "ชื่อที่ออกใบกำกับภาษี Stu Thuzar Khine Nyein Chan Aung" ถ้าใส่ group(1)จะได้ค่า "Stu Thuzar Khine Nyein Chan Aung" 

    global tax_ID_input_g
    tax_ID_input_g = re.search(tax_ID_regex, input_text).group(1)

    if(tax_ID_input_g != "-"):
        tax_ID = tax_ID_input_g

    global tax_tel_g
    tax_tel_g  = re.search(tel_regex, input_text).group(1)
    

    global tax_address_g
    tax_address_g = re.search(address_regex, input_text).group(1)

    ####ไม่ต้องใช้ละ ในเว็บมันดันไม่มีคำว่า ตำบล อำเภอ  เวลา copy ออกมา 
    # sub_district_regex = re.compile(r"\bแขวง[ก-๙]+\S|\bตำบล[ก-๙]+\S")
    # district_regex = re.compile(r"\bเขต[ก-๙]+\S|\bอำเภอ[ก-๙]+\S")
    # province_regex = re.compile(r"")

    ####ดัดแปลงและขัดเกลาINPUT ที่extractด้วยREGEX ให้สวยงามพร้อมใช้งาน แล้วเก็บเข้าตัวแปร
    x = tax_address_g.split(" ")
    global address_detail_only,sub_district, district, province
    sub_district = re.sub('เขต|แขวง','',x[-4])
    district = re.sub('เขต|แขวง','',x[-3])
    province = x[-2]
    # address_detail_only = re.sub(sub_district,"",tax_address_g)
    # address_detail_only = re.sub(district,"",tax_address_g)
    # address_detail_only = re.sub(province,"",tax_address_g)
    address_detail_only = re.sub(r'ต\..*|ตำบล.*|อ\..*|อำเภอ.*|เขต.*|แขวง.*', '', tax_address_g)
    result = sub_district in address_detail_only or sub_district in address_detail_only or province in address_detail_only
    if result:
        address_detail_only = re.sub(sub_district,'',address_detail_only)
        address_detail_only = re.sub(district,'',address_detail_only)
        address_detail_only = re.sub(province,'',address_detail_only)
        if type(int(address_detail_only.split(" ")[-1]))==int:
           
            address_detail_only = re.sub(address_detail_only.split(" ")[-1],'', address_detail_only)
        else:
            print("ไม่ int")

    else:
        return address_detail_only

    print("Name:", tax_name_g)
    print("Tax ID :", tax_ID) 
    print("Telephone:", tax_tel_g)
    print("details",  address_detail_only)
    print("ตำบล ", sub_district)
    print("อำเภอ ", district)
    print("จังหวัด ", province)

# raw_data = '''ITC23021000001
# ชื่อที่ออกใบกำกับภาษี Kong Su
# เลขประจำตัวผู้เสียภาษี -
# เบอร์โทร +660933409
# ที่อยู่ 9/9 Moo7 DeePlus Residence (Room-A605) Soi Abac, Bangna Trat Km26 บางบ่อ บางบ่อ สมุทรปราการ 10560'''
# customer_details(raw_data)

