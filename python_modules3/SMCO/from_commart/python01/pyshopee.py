##Modules
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import pybot01

##setup
opt = Options()
opt.add_experimental_option("debuggerAddress","localhost:8989")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)


##variable


##functions
def currentTabs():
    global tabs
    tabs  = list([])
    tabs.clear()
    handles = driver.window_handles
    global index
    index = 0
    for item in handles:
        driver.switch_to.window(item)
        tabs.append(driver.title) 
        index +=1
    print("มีจำนวน tab : ",index," EA",tabs)


currentTabs()
# time.sleep(0.75) ##ต้องใช้ป่าววะ


driver.get('https://seller.shopee.co.th/portal/sale/order')
currentTabs()
handles2 = driver.window_handles

pybot01.SMCO_Start()