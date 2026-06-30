from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

opt = Options()
opt.add_experimental_option("debuggerAddress", "localhost:8989")
driver = webdriver.Chrome(options=opt)

for handle in driver.window_handles:
    driver.switch_to.window(handle)
    if "SMCO" in driver.title:
        break

print("Connected to:", driver.title)

# Check current sale type
elements = driver.find_elements(By.CSS_SELECTOR, "span.select2-selection__rendered")
print("\nRendered elements:")
for e in elements:
    if e.text:
        print(f"  - {e.text[:60]}")

# Check employee
try:
    emp = driver.find_element(By.XPATH, "/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]")
    print(f"\nEmployee: {emp.text}")
except:
    print("\nEmployee: not found")

# Check customer
try:
    cus = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
    print(f"Customer: {cus.text}")
except:
    print("Customer: not found")

# Check items in cart
items = driver.find_elements(By.CSS_SELECTOR, ".col-sm-12.panel.panel-default.ng-scope")
print(f"\nItems in cart: {len(items)}")

# Check SKU input
try:
    sku = driver.find_element(By.ID, "svalue")
    print(f"SKU input value: {sku.get_attribute('value')}")
except:
    print("SKU input: not found")
