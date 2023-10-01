from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
try:
    browser = webdriver.Chrome(ChromeDriverManager(chrome_type='chromium').install())
except Exception as e:
    print("Error:", e)
browser.get("https://www.google.co.th/?hl=th")
