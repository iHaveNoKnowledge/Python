##Modules
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service 
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

##setup
opt = Options()
opt.add_experimental_option("debuggerAddress","localhost:8989")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)

##operation
SO_number = input("ใส่เลข SO : ")

tabName = driver.title
print("find_SO_tab_name: ",tabName)
driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[2]/div[2]/div[8]/div/div[2]').click()
driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[7]/div[2]/div[1]/div[3]/center/a').click()
driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[7]/div[2]/div[1]/div[3]/center/a').click()
driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[7]/div[2]/div[1]/div[1]/div[1]/div[1]/button').click()
time.sleep(0.25)
driver.find_element(By().XPATH,'/html/body/div[1]/div[2]/div[7]/div[2]/div[1]/div[1]/div[1]/div[2]/div/div/div[2]/div/div/span/span[1]/span/ul/li/input').send_keys(str(SO_number))


