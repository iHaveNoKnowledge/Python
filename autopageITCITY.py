# เสิชคำว่า "ยังไม่เสร็จ" เพื่อหางานที่ทำค้างไว้ // "optional" เพื่อหาโค้ดที่ทำเป็น ทางเลือกไว้ เพราะไม่ชัวว่า option ไหนดีกว่ากัน
# หลักๆ ใช้ setup
import time
# ไม่รู้คือไร แต่ใช้แล้ว มันทำให้ควบคุม context เมนูได้
import win32com.client as comclt
import re
import multiprocessing

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
import win32clipboard
import pyperclip
from tkinter import Tk
# import clipboard

# ดูด excel มาใช้
import pandas as pd

# ดัก event
from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener
from selenium.webdriver.support.abstract_event_listener import AbstractEventListener
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Modulesกูเอง
from python_modules3.SMCO.cusNameFixer import cusNameFixer, currencyRemover, addressExtractor

# setting
opt = Options()
opt.add_experimental_option("debuggerAddress", "localhost:8989")
# opt.add_argument('--headless') ##สาระ, น่าสนใจ## ยังไม่ได้ลองใช้ แต่ เวลาใช้ เว็บมันจะเปลือยๆมั้ง ซึ่งการเปลืือยในที่นี้คือ มันจะไม่มีลูกเล่นของ JS ทำให้เข้าถึง datacontent ได้ง่าย แต่จะเหมือนโจรยังไงไม่รู้
# download new ver.
driver = webdriver.Chrome(service=Service(
    ChromeDriverManager().install()), options=opt)
# driver= webdriver.Chrome(service=Service(r'C:\Users\ONLINE_MIS\.wdm\drivers\chromedriver\win32\109.0.5414\chromedriver.exe'), options=opt) ## ใส่ r ไว้หน้า path จะให้มันเป็น string ที่แท้จริง string ดิบๆ ถ้าไม่ใช่ มันจะมองบางตัวเป็นตัวอักษรสำหรับ syntaxต่อให้ "" ครอบก็ตาม
# print("มันลงไว้ที่ ",ChromeDriverManager().install()) ##ก้อนนี้ returns path ที่มันลงไว้ ซึ่งมันโหลดตัวลงไว้เฉยๆ เป็น zip แล้วแตกไฟล์
# service2 = Service(executable_path=ChromeDriverManager().install())
# driver2= webdriver.Chrome(service=service2)

## variable###
allOrdersPage = "https://cms.itcity.in.th/order-management"
smcoURL1 = 'http://115.31.167.28:8080/smartcore/smartpos/posmain.htm'
smcoURL2 = 'http://115.31.167.28:8080/smartcore/smartpos/posmain.htm#'
foundOrderElement = ''
tax_Bool = False
wsh = comclt.Dispatch("WScript.Shell")  # win32control controling context gui
titleList = []
titleListIdx = []

# สาระ, น่าสนใจ## enumerate() จะคืนค่าให้ตัวแปรloop เป็น object ทำให้เจ้าfor loop ดึงตัวแปรสำหรับ loop ได้มากกว่า 1 ตัว {'ตัวแรกจะได้index', 'ตัวที่สอง จะได้ ค่าvalue'}
for idx, handle in enumerate(driver.window_handles):
    driver.switch_to.window(handle)
    titleListIdx.append(driver.title + "["+str(idx)+"]")
    titleList.append(driver.title)
print("มีไรบ้าง", titleListIdx)
print("จำนวน tabs ตอนเริ่มต้น", len(titleListIdx))

tax_name = ""
tax_address = ""
tax_ID = ""
tax_tel = "1"

# หน้า smartCore XPATHlist
cusNameSpan = '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[2]'
cusNameInput = '/html/body/span/span/span[1]/input'
cusSearchSMCO = '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[7]/a'
cusCreateBtn = '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[2]/button'
cusNameLi = '/html/body/span/span/span[2]/ul/li'

# functions


def addNormalCustomer(cusSearchSMCO, cusCreateBtn):
    element = wait.until(
        EC.visibility_of_element_located((By.XPATH, cusSearchSMCO)))
    element.click()  # กดแว่นขยาย
    btnElement = wait.until(
        EC.visibility_of_element_located((By.XPATH, cusCreateBtn)))
    btnElement.click()  # create
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(tax_name_g)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(tax_name_g)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(tax_address_g)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(tax_tel_g)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()
    driver.find_element(
        By.XPATH, '/html/body/div[12]/div[2]/button[1]').click()


def addTaxInvCustomer(cusSearchSMCO, cusCreateBtn):
    driver.find_element(By.XPATH, cusSearchSMCO).click()
    time.sleep(0.75)
    driver.find_element(By.XPATH, cusCreateBtn).click()
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(tax_name_g)  # nameTH
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(tax_name_g)  # nameEN
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[3]/input').send_keys(tax_ID)  # Identity ID
    # [finAddress, finSubdistrict, finDistrict, finProvince, finZipCode] = addressExtractor(tax_address) ##ปัญหา บางเคสลูกค้าใส่ comma มามากกว่า 5 อัน ทำให้ error
    # finProvince = finProvince.strip().lstrip("จังหวัด")

    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(address_detail_only)  # Address

    # dropdown Country
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[9]/div[1]/div/span/span[1]/span/span[1]').click()
    time.sleep(1.75)
    # select thailand in dropdown
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[2]/ul/li[2]').click()

    # province dropdown
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[9]/div[2]/div/span/span[1]/span/span[1]').click()
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(province)  # province input
    time.sleep(1.55)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[1]/div/span/span[1]/span/span[1]').click()  # District drop
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(district)  # District
    time.sleep(1.55)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

    # SubDistrict drop
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[3]/div/span/span[1]/span/span[1]').click()
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(sub_district)  # SubDistrict
    time.sleep(1.55)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

    # tel.
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(tax_tel_g)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()
    driver.find_element(
        By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()


def justPressP():
    wsh.SendKeys("P")
    time.sleep(1.35)
    wsh.SendKeys("{Enter}")
    print("print แล้วโว้ย")
    time.sleep(0.75)
    wsh.SendKeys("{ESC}")
    print("กด esc แล้ว")
    # ถ้าเขียนเป็น cb แล้วมันจะพัง


def printtingPage():
    printing_page = driver.find_element(By().XPATH, '/html/body')
    action01 = ActionChains(driver).context_click(printing_page)
    action01.perform()
    time.sleep(0.5)


def inputCustomerTaxName():  # ใส่ชื่อลูกค้าใบกำกับ
    driver.switch_to.window(driver.window_handles[1])
    wait = WebDriverWait(driver, 30)
    element = wait.until(
        EC.visibility_of_element_located((By.XPATH, cusNameSpan)))
    element.click()
    driver.find_element(By().XPATH, cusNameInput).clear()
    driver.find_element(By().XPATH, cusNameInput).send_keys(tax_ID)
    handles = driver.window_handles
    driver.switch_to.window(handles[2])
    addTaxInvCustomer(cusSearchSMCO, cusCreateBtn)


tax_name


def search_order():
    searchBtn = driver.find_element(
        By.XPATH, '/html/body/div[1]/div[1]/div[3]/div[3]/div[2]/section/div[2]/div[2]/form/div[2]/div[4]/div/button[2]')
    searchBtn.click()
    search_result_element = wait.until(EC.text_to_be_present_in_element(
        (By.XPATH, '/html/body/div[1]/div[1]/div[3]/div[3]/div[2]/section/div[3]/div[2]/table/tbody/tr/td[2]'), order))  # ดูผลลัพว่าใช้ order ที่เราเสิชจริงๆหรือไม่ เป็น bool
    return search_result_element


def customer_details(raw_data):
    input_text = raw_data
    global tax_ID
    tax_ID = ""

    # หาคำว่า "ชื่อที่ออกใบกำกับภาษี"+สเปซบา1ช่อง+วงเล็บหมายถึงเก็บค่าข้างใน จุด คือเอาอักษรไรก็ได้ยกเว้นขึ้นบรรทัดใหม่มีดอกจันตามหลังแปลว่าเงื่อนไขข้างหน้ามันจะเอาหรือไม่ก็ได้ ถ้ามีก็มีกี่ตัวก็ได้
    name_regex = re.compile(r"ชื่อที่ออกใบกำกับภาษี\s+(.*)")
    tax_ID_regex = re.compile(r"เลขประจำตัวผู้เสียภาษี\s+(.*)")
    tel_regex = re.compile(r"เบอร์โทร\s+\b(\d+)")
    address_regex = re.compile(r"ที่อยู่\s+(.*)")

    global tax_name_g
    # ถ้าไม่ใส่ group จะได้ object ถ้าใส่ group(0)จะได้ค่า "ชื่อที่ออกใบกำกับภาษี Stu Thuzar Khine Nyein Chan Aung" ถ้าใส่ group(1)จะได้ค่า "Stu Thuzar Khine Nyein Chan Aung"
    tax_name_g = re.search(name_regex, input_text).group(1)

    global tax_ID_input_g
    tax_ID_input_g = re.search(tax_ID_regex, input_text).group(1)

    if (tax_ID_input_g != "-"):
        tax_ID = tax_ID_input_g

    global tax_tel_g
    tax_tel_g = re.search(tel_regex, input_text).group(1)

    global tax_address_g
    tax_address_g = re.search(address_regex, input_text).group(1)
    # ไม่ต้องใช้ละ ในเว็บมันดันไม่มีคำว่า ตำบล อำเภอ  เวลา copy ออกมา
    # sub_district_regex = re.compile(r"\bแขวง[ก-๙]+\S|\bตำบล[ก-๙]+\S")
    # district_regex = re.compile(r"\bเขต[ก-๙]+\S|\bอำเภอ[ก-๙]+\S")
    # province_regex = re.compile(r"")

    x = tax_address_g.split(" ")
    # ตัวแปรที่สร้าง 3 ตัวด้านล่างนี้ จะเป็นค่า ต. อ. จ. จากระบบ เราจะอิงของลูกค้าเป็นหลักของระบบช่างมันเดะลูกค้าหาว่าเราเบี้ยว
    global address_detail_only, sub_district, district, province
    sub_district = re.sub('เขต|แขวง', '', x[-4])
    district = re.sub('เขต|แขวง', '', x[-3])
    province = x[-2]
    post_code = x[-1]
    # address_detail_only = re.sub(sub_district,"",tax_address_g)
    # address_detail_only = re.sub(district,"",tax_address_g)
    # address_detail_only = re.sub(province,"",tax_address_g)
    # ตัดทุกอย่างหลังจากเจอ regex เหล่านี้
    address_detail_only = re.sub(
        r'ต\..*|ตำบล.*|อ\..*|อำเภอ.*|เขต.*|แขวง.*', '', tax_address_g)

    # ทำ address ใหเป็น address_detail_only
    result = sub_district in address_detail_only and sub_district and address_detail_only and province in address_detail_only
    if result:
        address_detail_only = re.sub(sub_district, '', address_detail_only)
        address_detail_only = re.sub(district, '', address_detail_only)
        address_detail_only = re.sub(province, '', address_detail_only)
        address_detail_postal = address_detail_only.split(
            " ")[-1]  # ดึงเลข ปณ จาก ก้อน string
        print("เพียวๆ: "+address_detail_only)
        print("ดึงตัวหลังสุดออกมา: "+address_detail_only.split(" ")[-1])

        if type(int(float(address_detail_postal))) == int:

            address_detail_only = str(
                re.sub(address_detail_only.split(" ")[-1], '', address_detail_only))
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
    print("เลขปณ.", post_code)


# ############operation start

handles = driver.window_handles
driver.switch_to.window(handles[0])
print("ตอนนี้ focus อยู่ที่", driver.current_url)
order = str(input("Order?: "))
time.sleep(0.75)
handles = driver.window_handles
driver.switch_to.window(handles[0])

# หน้า ITCITY
# ช่อง search
wait = WebDriverWait(driver, 100)
searchInput = wait.until(EC.visibility_of_element_located(
    (By.XPATH, '/html/body/div[1]/div[1]/div[3]/div[3]/div[2]/section/div[2]/div[2]/form/div[1]/div[1]/fieldset/div/input')))  # ช่อง input
searchInput.clear()
searchInput.send_keys(order)
print("ช่องเสิชมีอะไร", searchInput.get_attribute("value"))
# คลิกปุ่ม search
while True:
    search_order()  # ดูผลลัพว่าใช้ order ที่เราเสิชจริงๆหรือไม่ เป็น bool
    if search_order():
        print('หา %s เจอ' % (order))
        break
# เข้าไปใน detail
driver.find_element(
    By.XPATH, '/html/body/div[1]/div[1]/div[3]/div[3]/div[2]/section/div[3]/div[2]/table/tbody').click()

# เก็บข้อมูลลูกค้า
# wait.until(EC.visibility_of_element_located((By.XPATH,'/html/body/div[1]/div[1]/div[3]/div[3]/div[2]/section/div/div/div/div/form[3]/fieldset/div/div/div[2]/button'))) ##รอดูว่า element ท้ายสุดมารึยัง
# driver.find_element(By.XPATH,'/html/body/div[1]/div[1]/div[3]/div[3]/div[2]/section/div/div/div/div/form[2]/fieldset[2]/div/div/div/button').click() ##click แล้วแต่ไม่ได้ข้อมูล
wait.until(EC.text_to_be_present_in_element(
    (By.XPATH, '/html/body/div[2]/div[3]/div/div/div[1]/div/div/div/div/h5'), 'Copied billing address'))
# check_text = driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div[3]/div[3]/div[2]/section/div/div/div/div/form[2]/fieldset[2]/div/div/fieldset[2]/div/div/input').get_property('attributes')
# print("คือไร",check_text)
win32clipboard.OpenClipboard()
data = win32clipboard.GetClipboardData()
# print(str(data).encode(encoding='utf-8'))
print(data)
customer_details(data)

driver.switch_to.window(driver.window_handles[1])
wait = WebDriverWait(driver, 50)
element = wait.until(EC.visibility_of_element_located((By.XPATH, cusNameSpan)))
element.click()
driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[2]")
driver.find_element(By.XPATH, cusNameInput).send_keys(tax_name_g)

# SMCO go to customer Add Page
handles = driver.window_handles
driver.switch_to.window(handles[2])
addTaxInvCustomer(cusSearchSMCO, cusCreateBtn)

driver.switch_to.window(driver.window_handles[1])
result_li_el = driver.find_element(By.XPATH, cusNameLi)
try:
    if result_li_el.text == "No results found":

        driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[2]")
        driver.find_element(By.XPATH, cusNameInput).send_keys(tax_name_g)
        print("ใส่ชื่อใหม่อีกครั้ง")
except:
    print("ใส่ชื่อใหม่อีกครั้งไม่ได้")


# pd.options.display.max_columns = 1
# data = pd.read_csv(r'C:\Users\ONLINE_MIS\Downloads\order_list (59).csv')
# df =pd.DataFrame(data,['Customer_Full_Name'])
# print(df)
