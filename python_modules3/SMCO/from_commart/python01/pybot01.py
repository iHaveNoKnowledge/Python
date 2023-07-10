##Modules
import time
import win32com.client as comclt
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

##setup
opt = Options()
opt.add_experimental_option("debuggerAddress","localhost:8990")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)


##urls
SMCO = "http://115.31.167.28:8080/smartcore/smartpos/posmain.htm"

##testfield เก็บเว็บที่ใช้ได้
# currentWebsites = ["open_sale","authorization","geegee"]
# useable_tab = 0
# for item in currentWebsites:
#     if item == "open_sale" or item == "authorization":
#         useable_tab += 1
# print(useable_tab)


##variable
tabs  = list([])
SMCO_ID = "62078"
SMCO_PASS = "ITcity@2018"


##functions
def currentTabs():
    tabs.clear()
    handles = driver.window_handles
    i = 0
    for item in handles:
        driver.switch_to.window(item)
        tabs.append(driver.title) 
        i += 1
    print("มีจำนวน tab : ",i," EA",tabs)
    
    
def SMCO_summoner():
    if tabs.count('SMCO :: เปิดการขาย') == 2 or tabs.count('Authentication Service') == 2:
        print("มี SMCO 2 หน้าครบแล้ว")
        

    elif tabs.count('SMCO :: เปิดการขาย') == 0 or tabs.count('Authentication Service') == 0:
        print("รัน SMCO1")
        driver.switch_to.new_window('tab')
        driver.get(SMCO)

        print("รัน SMCO2")
        driver.switch_to.new_window('tab')
        driver.get(SMCO)

    elif tabs.count('SMCO :: เปิดการขาย') == 1 or tabs.count('Authentication Service') == 1:
        print("รัน SMCO 1 ตัวพอ")
        driver.switch_to.new_window('tab')
        driver.get(SMCO)

def customerInput():
    global cusName
    global cusTel
    cusName = str(input("(1/2)ชื่อ นามสกุล : "))
    cusTel = str(input("(2/2)TEL : "))
    print(cusName, cusTel)
    return cusName, cusTel

def SMCO_login():
    currentTabs()
    if "Authentication Service" in tabs:
        currentTabs()
        driver.find_element(By().XPATH,'/html/body/div[1]/center/div[1]/div/form/div/div[1]/div[1]/div/button[2]').click()
        driver.find_element(By().XPATH,'/html/body/div[1]/center/div[1]/div/form/div/div[2]/div/div[1]/input[2]').send_keys(SMCO_ID)
        driver.find_element(By().XPATH,'/html/body/div[1]/center/div[1]/div/form/div/div[2]/div/div[2]/input[2]').send_keys(SMCO_PASS)
        time.sleep(1)
        driver.find_element(By().XPATH,'/html/body/div[1]/center/div[1]/div/form/div/div[2]/div/div[4]/input[2]').click() ##กดล็อคอินหน้าแรก
        time.sleep(0.70)
        driver.find_element(By().XPATH,'/html/body/div[1]/center/div[1]/div/div[1]/div[3]/div/a').click() #เลือกสาขา
        time.sleep(0.70)
        driver.find_element(By().XPATH,'/html/body/div[1]/center/div[1]/div/div[2]/div[9]/div/a').click() #เลือกคลัง

def fill_customer_details(cusName, cusTel):
    ######Add Customer Name################
    handles = driver.window_handles
    driver.switch_to.window(handles[0])

    ## press addcustomer btn
    try:
        driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/form/div[2]/a').click()
    except:    
        ## press create btn
        driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[2]/button').click()

    time.sleep(1)

    ## press create btn
    try:
        driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[11]/div/div/div[2]/div/form/div[2]/button').click()
    except:
        pass

    time.sleep(0.9)
    ##fill customer inputs
    driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[1]/input').send_keys(cusName)
    driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[3]/div[2]/input').send_keys(cusName)
    driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[14]/div[2]/input').send_keys(cusTel)
    ##save and submit new customer เปิดปิดบรรทัด 108 และ 109 เพื่อ เทส การกรอก
    driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[11]/div/div/div[3]/div/form/div[16]/center/button[1]').click()
    driver.find_element(By().XPATH,'/html/body/div[12]/div[2]/button[1]').click()

def SMCO_Start(cusName, cusTel):

    ##operation
    ##ตัวแปรทดลอง input
    # cusName = "พอเจตต์ จันทร์แต่งผล"
    # cusTel = "0897610023"


    SMCO_login()
    # customerInput()
    currentTabs()
    SMCO_summoner()
    # currentTabs()
    # print("ชื่อ: ",cusName,"เบอ :",cusTel)

    handles = driver.window_handles

    ## ใส่รอ
    driver.switch_to.window(handles[1])
    driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/form/div[1]/span/span[1]/span/span[1]').click()
    driver.find_element(By().XPATH,'/html/body/span/span/span[1]/input').send_keys(cusName)

   
    # ######Add Customer Name################
    fill_customer_details(cusName, cusTel)

    driver.switch_to.window(handles[1])
    try:
        element = WebDriverWait(driver, 30).until(
        EC.text_to_be_present_in_element((By.XPATH, '/html/body/span/span/span[2]/ul/li'),cusName)
        )
        if element == True:
         driver.find_element(By().XPATH,'/html/body/span/span/span[2]/ul/li').click()
    except:
        print("driverwait timeout")

def SMCO_Starttax(cusName, cusTel, ):

    ##operation
    ##ตัวแปรทดลอง input
    # cusName = "พอเจตต์ จันทร์แต่งผล"
    # cusTel = "0897610023"


    SMCO_login()
    # customerInput()
    currentTabs()
    SMCO_summoner()
    # currentTabs()
    # print("ชื่อ: ",cusName,"เบอ :",cusTel)

    handles = driver.window_handles

    ## ใส่รอ
    driver.switch_to.window(handles[1])
    driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[5]/form/div[1]/span/span[1]/span/span[1]').click()
    driver.find_element(By().XPATH,'/html/body/span/span/span[1]/input').send_keys(cusName)

   
    # ######Add Customer Name################
    fill_customer_details(cusName, cusTel)

    driver.switch_to.window(handles[1])
    try:
        element = WebDriverWait(driver, 30).until(
        EC.text_to_be_present_in_element((By.XPATH, '/html/body/span/span/span[2]/ul/li'),cusName)
        )
        if element == True:
         driver.find_element(By().XPATH,'/html/body/span/span/span[2]/ul/li').click()
    except:
        print("driverwait timeout")
    
################## OPERATION START ################################################
SMCO_Start("ทรัพย์สาคร ธิเลิศ", "0800699885")
# handles = driver.window_handles
# driver.switch_to.window(handles[0])

# boolean = driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[3]/div/div[2]/a/div[2]/div/div/div')
# print(boolean)
# wait = WebDriverWait(driver,1)
# element = wait.until(EC.text_to_be_present_in_element((By.XPATH,'/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[3]/div/div[2]/a/div[1]/div[2]/span[1]'),text_="Invoice"))
# print(element)
# if element:
#     print("true")
# else:
#     print("false")

# wait = WebDriverWait(driver,1)
# try:
#     element = wait.until(EC.text_to_be_present_in_element((By.XPATH,'/html/body/div[1]/div[2]/div[2]/div/div/div[2]/div[2]/div/div/div[3]/div/div[2]/a/div[1]/div[2]/span[1]'),text_="Invoice"))
#     print(element)

#     if element:
#         print("true")
    
# except:
#     print("ไม่มี")

# wsh = comclt.Dispatch("WScript.Shell")
# wsh.SendKeys("{Escape}")

