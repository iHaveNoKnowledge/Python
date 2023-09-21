from multiprocessing import Value
from xml.dom.minidom import Element
import pyautogui, requests, bs4, time, urllib.request
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import win32api
import win32con
import win32gui


### หาเลขคู่ เลขขี้
# theInput = int(input("ใส่เลขเข้ามา : "))

# if theInput % 2 == 0:
#     print(str(theInput) + " เป็นเลขคู่")
# else :
#     print(str(theInput) + " เป็นเลขขี้")


# print(pyautogui.position())


###try ....except เอาไว้ดักว่า หาก(try){a}มีปัญหา ให้แสดง(except){b} หาก a มีปัญหา ให้แสดง b แทน
# try:
#     x  = int(input("ใส่เลขเข้ามาสิ: "))
#     print(x)
    
# except:
    
#     print("มึงไม่ได้ใส่เลขเข้ามาไอสัส")
#     print("มึงใส่ " + x + " มา")


### scrap shopee
# time.sleep(10)
# url = "https://stackpython.co/tutorial/web-scraping-python-beautifulsoup-requests"

# res = requests.get(url)
# res.encoding = "utf-8"
# # print(res)
# if res.status_code == 200:
#     print("Successful (status 200)")
# elif res.status_code == 404:
#     print("Error 404 page not found (the URL does not exist)")
# else:
#     print("Not both 200 and 404")

# soup = BeautifulSoup(res.text, 'html.parser')
# # print(soup.prettify())

# print(soup.body)

# #### scrap ด้วย urllib
# time.sleep(10)
# urllib.request
# f = urllib.request.urlopen("https://seller.shopee.co.th/portal/sale/order/120028101216883")

# print(f.read(300).decode('utf-8'))

#### เครื่องหมาย ? ที่ขึ้นใน SMCO คือ u200b 
# x = "กฤษติกร​ แสนเมือง​"
# newX = x.split()
# print(newX)

# inspectElement = 821,339
# targetElement = pyautogui.doubleClick(inspectElement)
# copyTarget = pyautogui.hotkey("ctrl","c")
# print(copyTarget) #ค่าที่้ได้เป็นค่าว่าง

# driver = webdriver.Chrome("C:/bin/chromedriver.exe")
# driver.get("https://www.google.co.th/?hl=th")

#################AUTO website ###########################
###Variables
# loginData = {
#     "id":"itcity:billing",
#     "pw":"itcity1234"
# }

# def launchBrowser():
#    options = webdriver.ChromeOptions()
#    options.add_experimental_option('excludeSwitches', ['enable-logging']) #add_experimental_optionมี2 parameter ตัวแรกจะเป็นชื่อของ option //ตัวสองคือ ค่าที่ต้องการตั้งให้ option นั้นๆ
# #    options.add_experimental_option("debuggerAddres","localhost:8989")
#    driver = webdriver.Chrome(options=options)
#    chrome_options = Options()
#    chrome_options.binary_location="../Microsoft edge" #Google Chrome
#    chrome_options.add_argument("disable-infobars") ##แอดไมวะ
#    driver = webdriver.Chrome(options=options,service=Service(ChromeDriverManager().install())) # เก็บ parameter "C:/bin/chromedriver.exe",
#    driver.get("https://seller.shopee.co.th/portal/sale/shipment?type=toship")

#    idElement = driver.find_element(By.XPATH,'/html/body/div[1]/div[2]/div/div/div/div[3]/div/div/div/form/div[1]/div/div/div/div/input')
#    idElement.send_keys(loginData.id)

#    #สร้างตัวแปร element มาเก็บค่า โดย driverจะใช้ method หา element ที่เป็น Tag html center (ง่ายๆคือ หา<center>ในหน้า page)
#    # element = driver.find_element(By.TAG_NAME, 'center') 
#    #หลังจาก ได้ <center> ทั้งหมดมาเก็บใน element ก็ใช้ method find_elements (มีs) เพื่อหา childElement ทั้งหมด ที่มี tag <input>
#    # elements = element.find_elements(By.TAG_NAME, 'input')
#    #ใช้ for in loop เอา childElements ทั้งหมดมา loop แต่ละก้อนที่ loop ออกมา นำมา สกัด attribute ที่มีชื่อ attribute = "value" ออกมา
#    # for e in elements:
#    #    print(e.get_attribute("value"))


#    while(True):
#        pass
    

   
# launchBrowser()

# # options = Options()

# # options.add_experimental_option('excludeSwitches', ['enable-logging'])

# # driver = webdriver.Chrome(executable_path=r"C:/bin/chromedriver.exe",chrome_options=options)

# # url = 'http://www.google.com/'

# # driver.get(url)


##เงื่อนไข จาก tab ปัจจุบัน
# lis01 = ["data", "SMCO", "SMCO"]
# x = "SMCO" in lis01
# if x:
#     if 0 < lis01.count("SMCO") == 1:
#         print("ขาด SMCO เปิดมันออกมา 1 ")
#         print("เปิด SMCO 1 อัน")


#     if lis01.count("SMCO") >= 2:
#         print("มีSMCO แล้ว")
#         print("เปิด INDEX ได้เลย")
# else:
#     print("ไม่มี SMCO เปิดมันออกมา 2 อัน")
#     print("เปิดSMCO 2 อัน")


#### ทดลองสร้างตัวแปร



# # Find the window handle for the window you want to control
# hwnd = win32gui.FindWindow(None, 'Seller Centre')


# # Display the context menu for the window
# win32api.SendMessage(hwnd, win32con.WM_CONTEXTMENU, 0, 0)

# # Select the first item from the context menu
# win32api.SendMessage(hwnd, win32con.WM_COMMAND, 0, 0)

# def getAnswer(prompt):
#     answer = input(prompt)
#     answer = bool(answer)
#     while answer==False :
#         answer = input(prompt)
#     return answer

# print(getAnswer("Element ที่ส่องอยู่มีค่าข้างในเป็น 0 หรือไม่"))

####ต้นแบบ
# def get_input():
#     while True:
#         user_input = input("Please provide a boolean input: ")
#         try:
#             user_input = eval(user_input) ##เป็นการเอา "ข้อความ" มาแปลงเป็น code python ถ้าแปลงไม่ได้จะ Error
#             if isinstance(user_input, bool): ##เป็นการตรวจสอบว่า parameter1(typeเป็นobject) เป็น instance ของ param2(type) หรือไม่ บรรทัดนี้ความหมายคือ user_input มีค่าเป็น bool  หรือไม่ 
#                 if user_input:
#                     return user_input
#                 else:
#                     print("False input! Please try again.")
#             else:
#                 print("Invalid input, Please enter a boolean value2")
#         except:
#             print("Invalid input, Please enter a boolean value1")
            
# result = get_input()

## Custom Ver.
def get_input(boolean, cb):
    # while True:
        # boolean = input("Please provide a boolean input: ")
        try:
            # boolean = eval(boolean) ##เป็นการเอา "ข้อความ" มาแปลงเป็น code python ถ้าแปลงไม่ได้จะ Error พอ error มันจะไปดำเนินการต่อจาก except แทน
            # print(boolean)

            if isinstance(boolean, bool): ##เป็นการตรวจสอบว่า parameter1(typeเป็นobject) เป็น instance ของ param2(type) หรือไม่ บรรทัดนี้ความหมายคือ user_input มีค่าเป็น bool  หรือไม่ 
                if  boolean:
                    cb()
                    # return boolean
                else:
                    print("False input! Please try again.")
            else:
                print("Invalid input, Please enter a boolean value2")
        except:
            print("Invalid input, Please enter a boolean value1")


            






