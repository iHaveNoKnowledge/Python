##imported modules
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

##initial setting 9090
opt = Options()
opt.add_experimental_option("debuggerAddress", "localhost:8990")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
driver.get("https://www.google.com")

order = input("ใส่เข้ามาสิ ใส่ order ของนายไง: ")
def selectOrder(order):
    print(order)

selectOrder(order)
