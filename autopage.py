# เสิชคำว่า "ยังไม่เสร็จ" เพื่อหางานที่ทำค้างไว้ // "optional" เพื่อหาโค้ดที่ทำเป็น ทางเลือกไว้ เพราะไม่ชัวว่า option ไหนดีกว่ากัน
from pynput.mouse import Listener
from xml.dom.minidom import Document
import myFunctions
from python_modules3.SMCO.cusNameFixer import cusNameFixer, currencyRemover, addressExtractor, cusNameFixer2, cusNameFixer3
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.abstract_event_listener import AbstractEventListener
from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import multiprocessing
import re
import win32com.client as comclt
import time

import os
import sys
# ดึงเส้นทาง (path) ปัจจุบัน
current_path = os.getcwd()

# ตัดชื่อโฟลเดอร์ออกจากเส้นทางปัจจุบัน
parent_path = os.path.dirname(current_path)

# กลับไปยังโฟลเดอร์ก่อนหน้า
os.chdir(parent_path)

# เพิ่มเส้นทางปัจจุบันเป็นเส้นทางหลัก (main path) ใหม่
sys.path.insert(0, parent_path)
sys.path.append('../Python/python_modules3')

# หลักๆ ใช้ setup
# ไม่รู้คือไร แต่ใช้แล้ว มันทำให้ควบคุม context เมนูได้


# ดัก event

# Modulesกูเอง
# from python_modules3.SMCO.cusNameFixer import cusNameFixer ##test พังไหม ทดสอบน่าจะเรียกmoduleผิดวิธี
# from python_modules3.SMCO.from_commart.python01.pybot01 import SMCO_login ##แค่ import มา ก็ใช้เองแล้ว

# ไปๆมาๆไม่ได้ใช้

# ใช้ได้ๆ แต่ต้องเปิด web ก่อน
# ต้องรัน chrome จาก cmd ก่อน chrome.exe --remote-debugging-port=8989 --user-data-dir="C:\bin\chromeprofile


class LoginData:
    id = "itcity:billing",
    pw = "itcity1234"


# setting
opt = Options()
# opt2=Options()
opt.add_experimental_option("debuggerAddress", "localhost:8989")
# opt.add_argument('--headless') ##สาระ, น่าสนใจ## ยังไม่ได้ลองใช้ แต่ เวลาใช้ เว็บมันจะเปลือยๆมั้ง ซึ่งการเปลืือยในที่นี้คือ มันจะไม่มีลูกเล่นของ JS ทำให้เข้าถึง datacontent ได้ง่าย แต่จะเหมือนโจรยังไงไม่รู้
# download new ver.
# driver = webdriver.Chrome(service=Service(
#     ChromeDriverManager().install()), options=opt)
# ใส่ r ไว้หน้า path จะให้มันเป็น string ที่แท้จริง string ดิบๆ ถ้าไม่ใช่ มันจะมองบางตัวเป็นตัวอักษรสำหรับ syntaxต่อให้ "" ครอบก็ตาม
driver = webdriver.Chrome(service=Service(
    r'C:\\Users\\ONLINE_MIS\\.wdm\\drivers\\chromedriver\\win64\\116.0.5845.111\\chromedriver.exe'), options=opt)
# print("มันลงไว้ที่ ",ChromeDriverManager().install()) ##ก้อนนี้ returns path ที่มันลงไว้ ซึ่งมันโหลดตัวลงไว้เฉยๆ เป็น zip แล้วแตกไฟล์
# service2 = Service(executable_path=ChromeDriverManager().install())
# driver2= webdriver.Chrome(service=service2)

#### auto shopee######
## variable###
allOrdersPage = "https://seller.shopee.co.th/portal/sale/shipment?type=toship"
logInUrl = "https://seller.shopee.co.th/account/signin?next=%2Fportal%2Fsale%2Fshipment%3Ftype%3Dtoship"
smcoURL1 = 'http://115.31.167.28:8080/smartcore/smartpos/posmain.htm'
smcoURL2 = 'http://115.31.167.28:8080/smartcore/smartpos/posmain.htm#'
foundOrderElement = '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[2]/div/div[2]/a'
taxBool = False
wsh = comclt.Dispatch("WScript.Shell")
shippingCost = "/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div[2]/div[4]"

titleList = []
value_list = []

title_dict_sorted = {}
title_dict = {}
title_order = ['Seller Centre', 'SMCO :: เปิดการขาย',
               'SMCO :: เปิดการขาย', 'SMCO :: พิมพ์ใบเสร็จซ้ำ']
titleListIdx = []
matched_string = ""
head_office_str_elmt = '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[4]/div[2]/div[2]/div[2]/div[1]/div[3]/div[2]'
# สาระ, น่าสนใจ## enumerate() จะคืนค่าให้ตัวแปรloop เป็น object ทำให้เจ้าfor loop ดึงตัวแปรสำหรับ loop ได้มากกว่า 1 ตัว {'ตัวแรกจะได้index', 'ตัวที่สอง จะได้ ค่าvalue'}
for idx, handle in enumerate(driver.window_handles):
    driver.switch_to.window(handle)
    titleListIdx.append(driver.title + "["+str(idx)+"]")
    titleList.append(driver.title)

    value_list.append(driver.current_window_handle)
    title_dict.update({driver.title: driver.current_window_handle})
print("มีไรบ้าง", titleListIdx)
print("จำนวน tabs ตอนเริ่มต้น", len(titleListIdx))

taxName = ""
head_office_str = ""
taxAddress = ""
taxID = ""
taxTel = "1"

# หน้า smartCore XPATHlist
cusNameSpan = '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[6]/form/div/span/span[1]/span/span[2]'
cusNameInput = '/html/body/span/span/span[1]/input'
cusSearchSMCO = '/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[7]/a'
cusCreateBtn = '/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[2]/button'
cusNameLi = '/html/body/span/span/span[2]/ul/li'

# functions


def loginShopee():
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div/div/div/div[3]/div/div/div/div[2]/button').click()
    time.sleep(1)

    subLoginName = driver.find_element(
        By.XPATH, '/html/body/div/main/div/div[1]/div/div/div/div/div/div/div[2]/div[1]/div/div/div/input')
    subLoginName.clear()
    subLoginName.send_keys(LoginData.id)

    subLoginPw = driver.find_element(
        By.XPATH, '/html/body/div/main/div/div[1]/div/div/div/div/div/div/div[2]/div[3]/div/div/input')
    subLoginPw.clear()
    subLoginPw.send_keys(LoginData.pw)


def addNormalCustomer(cusSearchSMCO, cusCreateBtn):
    element = wait.until(
        EC.visibility_of_element_located((By.XPATH, cusSearchSMCO)))
    element.click()  # กดแว่นขยาย
    btnElement = wait.until(
        EC.visibility_of_element_located((By.XPATH, cusCreateBtn)))
    btnElement.click()  # create
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(cusName)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(cusName)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(cus_normal_address)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(1)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()
    driver.find_element(
        By.XPATH, '/html/body/div[16]/div[2]/button[1]').click()


def addTaxInvCustomer(cusSearchSMCO, cusCreateBtn):
    driver.find_element(By.XPATH, cusSearchSMCO).click()
    time.sleep(0.75)
    driver.find_element(By.XPATH, cusCreateBtn).click()
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(taxName)  # nameTH
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(taxName)  # nameEN
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[3]/input').send_keys(taxID)  # Identity ID
    [finAddress, finSubdistrict, finDistrict, finProvince, finZipCode] = addressExtractor(
        taxAddress)  # ปัญหา บางเคสลูกค้าใส่ comma มามากกว่า 5 อัน ทำให้ error
    finProvince = finProvince.strip().lstrip("จังหวัด")

    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[7]/div/textarea').send_keys(finAddress)  # Address

    # dropdown Country
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[9]/div[1]/div/span/span[1]/span/span[1]').click()
    time.sleep(1)
    # select thailand in dropdown
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[2]/ul/li[2]').click()

    # province dropdown
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[9]/div[2]/div/span/span[1]/span/span[1]').click()
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(finProvince)  # province input
    time.sleep(1.75)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[1]/div/span/span[1]/span/span[1]').click()  # District drop
    driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
        finDistrict.strip().lstrip("เขต").replace("อำเภอ", ""))  # District
    time.sleep(1.75)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

    # SubDistrict drop
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[11]/div[3]/div/span/span[1]/span/span[1]').click()
    driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(
        finSubdistrict.strip().lstrip("แขวง").replace("ตำบล", ""))  # SubDistrict
    time.sleep(1.75)
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/span/span/span[1]/input').send_keys(Keys().ENTER)

    # tel.
    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(taxTel)
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
    driver.switch_to.window(merged_dict['SMCO :: เปิดการขาย'])
    wait = WebDriverWait(driver, 30)
    element = wait.until(
        EC.visibility_of_element_located((By.XPATH, cusNameSpan)))
    element.click()
    wait.until(
        EC.visibility_of_element_located((By.XPATH, cusNameInput)))
    driver.find_element(By().XPATH, cusNameInput).clear()
    driver.find_element(By().XPATH, cusNameInput).send_keys(taxID)
    handles = driver.window_handles
    driver.switch_to.window(merged_dict['SMCO :: เปิดการขาย1'])
    addTaxInvCustomer(cusSearchSMCO, cusCreateBtn)


def remove_text(text):
    return re.sub(r'\s\(สำนักงานใหญ่\)|\(สำนักงานใหญ่\)', '', text)


def my_key_function(item):
    if item == "Seller Centre":
        return 1
    elif item == "SMCO :: เปิดการขาย":
        return 2
    elif item == "SMCO :: พิมพ์ใบเสร็จซ้ำ":
        return 3
    else:
        return 4


def build_list(list):
    global result
    result = []
    counter = {}
    for item in list:
        if item in counter:
            counter[item] += 1
            print("counter[item] คือไร: ", counter[item])
            result.append(f"{item}{counter[item]-1}")
        else:
            counter[item] = 1
            result.append(item)
    return result


# ############operation start
# สร้างlistแบบไม่ซ้ำเพื่อทำ unique keyเกบใน title_new
title_new = build_list(titleList)
# เอา unique key รวม กับ value (value ไม่ต้องทำ unique เพราะ unique อยู่แล้ว)
merged_dict = dict(zip(title_new, value_list))

handles = driver.window_handles
print("handlesมีอะไร: ", handles)
driver.switch_to.window(merged_dict['Seller Centre'])
print("ตอนนี้ focus อยู่ที่", driver.current_url)
order = str(input("Order?: "))
# time.sleep(0.75)
# handles = driver.window_handles
# driver.switch_to.window(handles[0])

x = "SMCO :: เปิดการขาย" in titleList
if x:
    if titleList.count("SMCO :: เปิดการขาย") == 1:
        driver.execute_script(
            "window.open('http://115.31.167.28:8080/smartcore/smartpos/posmain.htm');")
    elif titleList.count("SMCO :: เปิดการขาย") >= 2:
        pass
else:
    driver.execute_script(
        "window.open('http://115.31.167.28:8080/smartcore/smartpos/posmain.htm');")
    # ใช้ได้ๆ มันออกมาจริง แต่ บราวเซอร์มันจะตกใจ popup
    driver.execute_script(
        "window.open('http://115.31.167.28:8080/smartcore/smartpos/posmain.htm');")

if (driver.current_url == allOrdersPage):
    print("ตอนนี้อยู่ที่" + str(driver.current_url))
elif (driver.current_url == logInUrl):
    loginShopee()
elif (driver.current_url == smcoURL1 or driver.current_url == smcoURL2):
    driver.switch_to.new_window()
    driver.get(allOrdersPage)
    print("เงื่อนไข3")
else:
    driver.get(allOrdersPage)
    time.sleep(1)
    # loginShopee()

print("เช็คหลังจากรันสองเว็บ"+str(driver.current_url))
driver.switch_to.window(merged_dict['Seller Centre'])
print("เช็คหลังจากย้ายหน้า window_handlesไปที่ [0]"+str(driver.current_url))


# หน้า Order Shopee
# ช่อง search
wait = WebDriverWait(driver, 100)
searchInput = wait.until(EC.visibility_of_element_located(
    (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[1]/div[2]/div[2]/div[1]/span[2]/div/div[1]/div/div/input')))  # ช่อง input
# orderResult = wait.until(EC.)
searchInput.clear()
searchInput.send_keys(order)
print("ช่องเสิชมีอะไร", searchInput.get_attribute("value"))
# คลิกปุ่ม search
searchBtn = driver.find_element(
    By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[1]/div[2]/div[2]/div[2]/button[1]')
searchBtn.click()
time.sleep(1.5)

# หลังจากเจอOrder จะได้ list component ของ order ที่ค้นหา 1 component เช็คว่ามีใบกำกับหรือไม่
waitLi = WebDriverWait(driver, 30)
foundLi = waitLi.until(EC.visibility_of_element_located(
    (By().XPATH, foundOrderElement)))
try:
    wait = WebDriverWait(driver, 1)
    element = wait.until(EC.text_to_be_present_in_element(
        (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[2]/div/div[2]/a/div[1]/div[2]/span[1]'), text_="Invoice Requested"))
    if element:
        print("มีใบกำกับ")
        taxBool = True
    foundLi = driver.find_element(
        By().XPATH, '/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[2]/div/div[2]/a')
    foundLi.click()  # กดที่ลิงค์หลังเสิช
except:
    print("ไม่มีใบกำกับ")
    taxBool = False
    waitLi = WebDriverWait(driver, 30)
    foundLi = waitLi.until(EC.visibility_of_element_located(
        (By().XPATH, foundOrderElement)))
    foundLi.click()  # กดที่ลิงค์หลังเสิช

time.sleep(1)
# ย้ายไปหน้า 3 (หน้ารายละเอียดOrder ที่เปิดล่าสุดนั้นแหละ) เพื่อไปเลือกว่าจะเอาข้อมูลปกติ หรือ ใบกำกับ โดยตัดสินจาก boolean
driver.switch_to.window(driver.window_handles[4])
wait = WebDriverWait(driver, 40)
wait.until(EC.visibility_of_element_located(
    (By.XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[1]')))  # ดูว่า div แรกออกมายัง
time.sleep(1)
cusName = ""

# มาตัดสินกันว่า จะใช้ชื่อลูกค้าปกติ หรือ ใช้ ใบกำกับภาษี
if taxBool:
    try:  # ตรวจดูว่ามี คำว่า "สำนักงานใหญ่หรือไม่" ถ้ามีให้เก็บมา ไม่มีให้ข้ามไปใส่ปกติ
        head_office_str = driver.find_element(
            By.XPATH, head_office_str_elmt).text
        taxName = driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[4]/div[2]/div[2]/div[2]/div[1]/div[1]/div[2]').text
        taxName = remove_text(taxName)
        # จะได้ ชื่อบริษัท (สำนักงานใหญ่)
        taxName = taxName+" "+"("+head_office_str+")"
    except:
        print("ใส่คำว่า (สำนักงานใหญ่) ไม่ได้")
        taxName = driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[4]/div[2]/div[2]/div[2]/div[1]/div[1]/div[2]').text
        pass

    taxAddress = driver.find_element(
        By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[4]/div[2]/div[2]/div[2]/div[1]/div[2]/div[2]').text
    taxID = driver.find_element(
        By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[4]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]').text
    try:
        if driver.find_element(By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[4]/div[2]/div[2]/div[2]/div[2]/div[2]').is_enabled():
            taxTel = driver.find_element(
                By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[4]/div[2]/div[2]/div[2]/div[2]/div[2]/div[2]').text
        else:
            pass
    except:
        print("ชื่อในใบกำกับคือ", taxName)
else:
    # #### 3 บรรทัดล่าง ใช้ไม่ได้เพราะว่าชื่อลูกค้าเป็นเครื่องหมาย **** ต้องเปลี่ยนไปใช้ชื่อ account แทน
    # cusNameElement = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[2]/div[2]/div[1]')
    # cusName = cusNameElement.text ##เก็บชื่อลูกค้า
    # cusName = cusNameFixer(cusName)

    # ### 3บรรทัดล่างเป็นการใช้ account เป็นชื่อแทน เรื่องออกใบกำกับเริ่มจริงจัง เลยอาจจะใช้ไม่ได้
    # cus_account_Name_element = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[3]/div/div/div[2]/div')
    # cusName = cus_account_Name_element.text ##เก็บชื่อลูกค้า
    # cusName = cusNameFixer2(cusName)

    # 4บรรทัดล่างเป็นการใช้ ชื่อลูกค้าแบบใหม่ที่ไม่รู้มันจะทำมาทำเพื่ออะไร เป็นชื่อแทน เพราะอันบนมัน มี "**" มาแทรกในชื่อ
    wait.until(EC.visibility_of_element_located(
        (By.XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div/div/div/div/div[2]')))
    cus_account_Name_element_v2 = driver.find_element(
        By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[4]/div[2]/div[2]/div[2]/div[1]/div[1]/div[2]')
    cusName = cus_account_Name_element_v2.text  # เก็บชื่อลูกค้า
    cusName = cusNameFixer3(cusName)

    # ####(optionnal)address(1)ที่อยู่ลูกค้าแบบเก่า ณ ปัจจุบันมันเอา ** มาแทรกทำให้ใช้ไม่ได้
    # cus_normal_address_Element = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[2]/div[2]/div[2]')

    # (optionnal)address(2)ที่อยู๋ลูกค้าแบบใหม่ ที่ไม่รู้มันจะทำมาทำเพื่ออะไร เพราะอันบนมัน มี "**" มาแทรกในที่อยู่เช่นเดียวกันกัะบชื่อ
    cus_normal_address_Element = driver.find_element(
        By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[2]/div/div[4]/div[2]/div[2]/div[2]/div[1]/div[2]/div[2]')

    cus_normal_address = cus_normal_address_Element.text

# หาค่าขนส่ง ที่ต้อง try except เพราะ จำนวน div มัน dynamic
time.sleep(1)
try:
    try:
        # แหวก dropdownแบบที่3 เพราะ 1 หรือ 2 ใช้ไม่ได้ ไม่รู้
        element3 = driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div/div/div/div[2]')
        element3.click()
        try:
            wait_few_sec = WebDriverWait(driver, 2)
            isShippingCost = wait_few_sec.until(EC.text_to_be_present_in_element(
                (By.XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div/div/div[2]/div[3]'), "ค่าจัดส่ง"))
            if (isShippingCost):
                shippingCostValue = driver.find_element(
                    By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div/div/div[2]/div[4]')  # ต้องเปิดก่อนมันมองไม่เหน path นี้
                shippingCostValue = currencyRemover(shippingCostValue.text)
        except:
            isShippingCost = wait.until(EC.text_to_be_present_in_element(
                (By.XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div/div/div[2]/div[5]'), "ค่าจัดส่ง"))
            if (isShippingCost):
                shippingCostValue = driver.find_element(
                    By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div/div/div[2]/div[6]')  # ต้องเปิดก่อนมันมองไม่เหน path นี้
                shippingCostValue = currencyRemover(shippingCostValue.text)
        # element1 = driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[6]/div/div/div/div[2]') ##แหวก dropdownแบบที่1
        # element1.click()
        # time.sleep(0.55)
        # shippingCostValue = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[6]/div/div/div[2]/div[4]')##ต้องเปิดก่อนมันมองไม่เหน path นี้
        # shippingCostValue = currencyRemover(shippingCostValue.text)
        try:
            seller_voucher = driver.find_element(
                By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div/div/div[2]/div[8]')
            seller_voucher = currencyRemover(seller_voucher.text)
        except:
            seller_voucher = driver.find_element(
                By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[7]/div/div/div/div/div[2]/div[8]')
            seller_voucher = currencyRemover(seller_voucher.text)

    except:
        element2 = driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[7]/div/div/div/div/div/div[2]')  # แหวก dropdownแบบที่2
        element2.click()
        time.sleep(0.55)

        is_shipiing_cost_label = driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[7]/div/div/div/div/div[2]/div[3]')
        if is_shipiing_cost_label.text == "ค่าจัดส่ง":
            shippingCostValue = driver.find_element(
                By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[7]/div/div/div/div/div[2]/div[4]')
        else:
            shippingCostValue = driver.find_element(
                By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[7]/div/div/div/div/div[2]/div[6]')

        shippingCostValue = currencyRemover(shippingCostValue.text)

        try:
            seller_voucher = driver.find_element(
                By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div/div/div[2]/div[8]')
            seller_voucher = currencyRemover(seller_voucher.text)
        except:
            seller_voucher = driver.find_element(
                By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[7]/div/div/div/div/div[2]/div[8]')
            seller_voucher = currencyRemover(seller_voucher.text)
except:
    element3 = driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[8]/div/div/div/div/div/div[2]')  # แหวก dropdownแบบที่2
    element3.click()
    time.sleep(0.55)
    shippingCostValue = driver.find_element(
        By().XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[8]/div/div/div/div/div[2]/div[4]')
    shippingCostValue = currencyRemover(shippingCostValue.text)

# finally:
#     element3 = driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div/div/div/div[2]') ##แหวก dropdownแบบที่3 เพราะ 1 หรือ 2 ใช้ไม่ได้ ไม่รู้
#     element3.click()
#     isShippingCost = wait.until(EC.text_to_be_present_in_element((By.XPATH,'/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div/div/div[2]/div[3]'),"ค่าจัดส่ง"))
#     if(isShippingCost):
#         driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div/div/div[2]/div[4]').click()

# shippingCostValue = wait.until(EC.visibility_of_element_located((By.XPATH,'/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[5]/div/div/div[2]/div[4]'))) ##ต้องเปิดก่อนมันมองไม่เหน path นี้
# shippingCostValue = currencyRemover(shippingCostValue.text)
print(cusName)
print("ค่าจัดส่ง ", shippingCostValue, "บาท")
time.sleep(1)

# creat and fill customer invName
if taxBool:  # ถ้าเป็นจริง = มีใบกำกับ
    inputCustomerTaxName()
    print("ใช้ฟังชั่น เพิ่มชื่อ tax")
    # แอดไม่ทันเสร็จ มันไปเลือกชื่อลูกค้าแล้ว error เลยเพราะหา element ต่อไปไม่เจอ
    time.sleep(8)
    # ตอนแรก รอ 3, 5 วิ แล้วไม่ทัน แต่ 10 ทัน รันสบาย
    print("ครบ 10 วิหลังใช้ เพิ่มชื่อ tax")
else:  # กรณีเท็จ จะออกลูกค้าปกติ
    # SMCO go to customer Add Page
    handles = driver.window_handles
    driver.switch_to.window(merged_dict['SMCO :: เปิดการขาย1'])
    addNormalCustomer(cusSearchSMCO, cusCreateBtn)

    # SMCOMain เอาชื่อลูกค้ามาใส่รอโหลดระหว่างแอดชื่อลูกค้า
    driver.switch_to.window(merged_dict['SMCO :: เปิดการขาย'])
    wait = WebDriverWait(driver, 50)
    element = wait.until(
        EC.visibility_of_element_located((By.XPATH, cusNameSpan)))
    element.click()
    # driver.find_element(By.XPATH,cusNameInput).clear() น่าจะไม่ต้องใช้
    driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[2]")
    driver.find_element(By.XPATH, cusNameInput).send_keys(cusName)


# ปิดเพื่อปรับปรุง
# #Back To MainSMCO page กดเลือกชื่อลูกค้าจาก dropdownlist ที่เพิ่ง add มา
handles = driver.window_handles
# เปิดครั้งแรก การสลับมาหน้า 1 มันขึ้น out of range โดย เวลานั้น บรรทัด 281 ยังไม่มี handles = driver.window_handles ตอนนี้ใส่เพิ่มแล้วไม่รู้จะเป็นอีกไหม
driver.switch_to.window(merged_dict['SMCO :: เปิดการขาย'])
try:
    try:
        print("รอชื่อลูกค้าขึ้น")
        element = WebDriverWait(driver, 6).until(
            EC.text_to_be_present_in_element(
                (By.XPATH, '/html/body/span/span/span[2]/ul/li'), taxName | cusName)
        )

        if element == True:

            driver.find_element(
                By().XPATH, '/html/body/span/span/span[2]/ul/li').click()
    except:
        print("ไม่ขึ้นก็ใส่ใหม่")
        driver.find_element(By.XPATH, cusNameInput).clear()
        if taxBool:
            driver.find_element(By.XPATH, cusNameInput).send_keys(taxID)
        else:
            driver.find_element(By.XPATH, cusNameInput).send_keys(cusName)

        element = WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element(
                (By.XPATH, '/html/body/span/span/span[2]/ul/li'), cusName)
        )
        if element == True:

            driver.find_element(
                By().XPATH, '/html/body/span/span/span[2]/ul/li').click()
except:
    print("driverwait timeout")

# ใส่ค่าขนส่ง
try:
    if int(shippingCostValue) != int(0):
        skuInput = WebDriverWait(driver, 50).until(EC.visibility_of_element_located(
            (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')))
        # skuInput = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')
        skuInput.clear()
        skuInput.send_keys("SV0-000101")
        print("กรอก Code ขนส่งสำเร็จ")

        skuAddBtn = wait.until(EC.visibility_of_element_located(
            (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')))
        # skuAddBtn = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')
        skuAddBtn.send_keys(Keys().ENTER)
        print("กด Enter ที่ช่อง SKU Input สำเร็จ")
        time.sleep(2)

        # ทำไมต้องใส่วงเล็บ คลุม BY.XPATH เพราะ ถ้าไม่ใส่ ฟังชัน visibility จะมอง xpath เป็น argument ที่สอง ของ method visibility
        definePrice = wait.until(EC.visibility_of_element_located(
            (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div[1]/div/a[1]')))
        # definePrice = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div[1]/div[2]/div[1]/div/div[2]/div[1]/div[1]/div/a[1]')
        definePrice.click()
        time.sleep(1)
        # ค่าขนส่งโดนข้า230208FX99FUGGมหลังจากตรงนี้
        print("กดที่ SKU ELEMENT 1 สำเร็จ")

        changePriceInput = driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[1]/input')
        changePriceInput = changePriceInput.clear()
        changePriceInput = driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[1]/input').send_keys(shippingCostValue)

        driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[2]/input').clear()
        driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[2]/input').send_keys("62078")

        driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[3]/input').clear()
        driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[2]/div[3]/input').send_keys("ITcity@2017")

        driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[5]/div/textarea').clear()
        driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[5]/div/textarea').send_keys("Online")

        driver.find_element(
            By().XPATH, '/html/body/div[1]/div[2]/div[2]/div[6]/div/div/div[2]/div[6]/a[1]').click()
    else:
        print("เงื่อนไขค่าขนส่ง มี Boolean เป็น False")
        pass
except:
    print("ค่าขนส่งโดนข้าม")


# หน้าจ่ายตัง
wait2 = WebDriverWait(driver, 3600)
# * เติม Order ในจุด Remark
# is_final_page2 = wait2.until(EC.text_to_be_present_in_element((By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[1]/textarea'),)
is_final_page = wait2.until(EC.visibility_of_element_located(
    (By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[1]/textarea')))
try:
    if seller_voucher:
        # ถ้ามี เซลเลอร์ให้ ให้กรอกให้ด้วย
        driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[3]/div[1]/div[2]/input').send_keys(seller_voucher)

    # ถ้าไม่มี seller ก็ไปกรอก remark ได้เลย
    driver.find_element(
        By.XPATH, "/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[1]/textarea").send_keys(order)

    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[2]/div/div/div[4]/a').click()

    driver.find_element(
        By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[3]/div/div[2]/div[2]/div[3]/div[2]/div[1]/div[2]/input').send_keys(order)

    if cusName:
        driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').send_keys(cusName)
    else:
        driver.find_element(
            By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[7]/div/div[3]/div/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/input').send_keys("a")
except:
    print("Auto หน้าท้ายพัง ข้ามไปรอราคาเลย")
    pass
wait2 = WebDriverWait(driver, 3600)
zeroExpectElmt = wait2.until(EC.text_to_be_present_in_element(
    (By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[2]/div[4]/div'), "0.00"))
# print("มึงเป็น Boolean ป่าววะเพือน ", zeroExpectElmt)
myFunctions.get_input(zeroExpectElmt, lambda:
                      driver.find_element(By.XPATH, '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[3]/div[2]/div/div').click())  # Paymenbtnกดปุ่มเขียว แล้วจะมี pop-up เด้งมา

# ####(optional)popup สุดท้ายเด้ง สำหรับ etax
# if taxBool: ##มีใบกำกับ
#     final_popup_element_email = wait2.until(EC.visibility_of_element_located((By.XPATH,'/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[2]/label/input'))) ##เจอradio Send Email
#     final_popup_element_email.click()
# else: ##ไม่มีใบกำกับ ต้อง print
#     final_popup_element_print = wait2.until(EC.visibility_of_element_located((By.XPATH,'/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[1]/label/input'))) ##เจอradio Print Out
#     driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[5]/center/button').click()
#     wait.until(EC.visibility_of_element_located((By.XPATH,'/html/body/div[12]/div[2]/div[6]')))
#     inv_num_string = driver.find_element(By.XPATH,'/html/body/div[12]/div[2]/div[6]').text ##หรือาจจะใช้ได้วะ ใช้ได้ๆ
#     print("ข้อความนั้น",inv_num_string) ##ชุดข้อความที่จะต้องสกัดเอาเลขใบกำกับ
#     pattern = re.compile(r'B0183-W06-[0-9]{10}')
#     match = pattern.search(inv_num_string)

#     if match:
#         matched_string = match.group() ##เลขบิลสดแท้ๆ
#         print("Matched string:", matched_string)
#     else:
#         print("Match not found.")

#     driver.switch_to.window(handles[3])
#     driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div[1]/div[2]/div/div[1]/div[1]/div/span/span[1]/span/span[1]').click() ##แหก dropdown ออกมา
#     driver.find_element(By.XPATH,'/html/body/span/span/span[1]/input').send_keys(matched_string.strip())
#     wait.until(EC.text_to_be_present_in_element((By.XPATH,'/html/body/span/span/span[2]/ul/li[1]'),matched_string))
#     driver.find_element(By.XPATH,'/html/body/span/span/span[2]/ul/li').click()
#     driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div[1]/div[2]/div/div[2]/div[2]/div/textarea').send_keys("No email")
#     driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div[1]/div[1]/span/button[2]').click() ##กดปุ่มเซฟเขียว
#     last_choice = wait.until(EC.visibility_of_element_located((By.XPATH,'/html/body/div[1]/div[2]/div[1]/div[2]/div/div[6]/div/div/div[2]/div/div[5]/center/button')))
#     last_choice.click() ##คลิกที่ปุ่ม print_out
#     # driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div[1]/div[2]/div/div[6]/div/div/div[2]/div/div[5]/center/button').click()
#     last_btn = wait.until(EC.visibility_of_element_located((By.XPATH,'/html/body/div[8]/div[2]/button[1]')))
#     last_btn.click() ##คลิกที่ปุ่มปิดเพื่อเข้าไปหน้า print pdf มั้ง
#     # driver.find_element(By.XPATH,'/html/body/div[8]/div[2]/button[1]').click()


# (optional)สำหรับแบบเดิม
if zeroExpectElmt:
    # time.sleep(1)
    # driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[3]/div[2]/div/div').click() ##Paymenbtn
    # optional - Clicking the final btn before the prtinting page
    # option01 using time.sleep()
    # รอ popup เลข บิลมันโผล่ ต้องใช้เวลานิดนึง เอาจริงๆเวลาไม่ค่อยแน่นอนอาจจะต้องใช้ wait
    time.sleep(2.5)
    wait.until(EC.visibility_of_element_located(
        (By.XPATH, "/html/body/div[16]/div[2]/button[1]"))).click()
    # driver.find_element(By().XPATH,'/html/body/div[12]/div[2]/button[1]').click() ##press blue_btn_Okay

    # option02 using wait เดาว่าน่าจะเป็นปุ่มของ pop-up
    # okBtn = wait.until(EC.visibility_of_element_located((By().XPATH,'/html/body/div[12]/div[2]/button[1]')))
    # okBtn.click()


else:
    print("มันยังมีตังทอนอยู่")

time.sleep(1.5)
printtingPage()
justPressP()


# # handles = driver.window_handles ##เป็นการเรียกหา จำนวนหน้าต่างทั้งหมด เข้าถึงได้ด้วย index datatype เป็น list
# titleList= []
# for handle in driver.window_handles:
#     driver.switch_to.window(handle)
#     titleList += driver.title
#     print(driver.window_handles,driver.title) ##Loop จะพามาจอดที่หน้าสุดท้าย(หน้าที่เปิดล่าสุด)พอดีขั้นตอนต่อไปเลยสั่ง driver.close() ได้เลย

# driver.close()


################################################################### Experiment ZONE###########################################################################
# driver.switch_to.window(driver.window_handles[2]) ##สำคัญมากต้องใช้เพราะ driver มันไม่ได้ไปหน้า3 เหมือนกับ gui ที่แสดงให้ user เห็น สรุป driver เห็นเป็นหน้า[1] แต่คนใช้จะเห็นเป็น[2] ทำให้code ข้างล่างต่อจากนี้หา element ไม่เจอเพราะมันไปหา หน้า [1] ไม่ใช่ [2]

# ยัง งง อยู่
# import win32api
# import win32con
# import win32gui

# # Find the window handle for the window you want to control
# hwnd = win32gui.FindWindow(None, 'windowTest00')
# print(hwnd.GetWindowText)
# # Display the context menu for the window
# win32api.SendMessage(hwnd, win32con.WM_CONTEXTMENU, 0, 0)

# # Select the first item from the context menu
# win32api.SendMessage(hwnd, win32con.WM_COMMAND, 0, 0)

# ดูด path มาก่อน ยังไงก็ต้องใช้ (pathที่ยังไม่ได้ใช้, รอเอาไปใช้)
# กรณี Printing Paper
# popup สุดท้าย ใช้อันนี้เพื่อ print กรณี ใบกำกับ False
finalPrintRadio = "/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[1]/label/input"
# popup สุดท้าย ปุ่มส่งเมลเพื่อจบการทำงาน (locatorเดียวกับปุ่มsend email)
finalPrintBtn = "/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[5]/center/button"
# กรณี Sending email
# popup สุดท้าย ใช้อันนี้ เพื่อส่งเมล คู่กับ ใบกำกับ True
finalSendEmailRadio = "/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[2]/label/input"
# popup สุดท้าย ช่องinput สำหรับกรอก email
finalEmailInputElmt = "/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[3]/div[3]/input"
# popup สุดท้าย ปุ่มส่งเมลเพื่อจบการทำงาน (locatorเดียวกับปุ่มPrint)
finalSendEmailBtn = "/html/body/div[1]/div[2]/div[6]/div[1]/div/div/div[2]/div/div[5]/center/button"


# handles = driver.window_handles
# driver.switch_to.window(handles[0])
# print(driver.title)
# mainElement = driver.find_elements(By().XPATH,'/html/body/div[1]/div[2]/div/div/div/div/div/div/div/div[1]/div[1]/div[4]/div/div/div/div[2]')
# for i in mainElement:
#     print("เหล่าเด็กน้อย: \n"+i.text)

# ##login
# SMCO_login()
