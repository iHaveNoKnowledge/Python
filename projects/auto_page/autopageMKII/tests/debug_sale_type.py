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

# Click sale type dropdown
arrow = driver.find_element(
    By.CSS_SELECTOR, "#contentZen > div.ng-scope > div:nth-child(2) > div.panel-body > div.col-sm-3 > div.col-sm-12.nopadding > div.panel-body > div > div > div:nth-child(2) span.select2-selection__arrow")
arrow.click()
time.sleep(1)

# Get all li elements
lis = driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
print("Found", len(lis), "options")
for i, li in enumerate(lis):
    print(f"{i}: text='{li.text}', displayed={li.is_displayed()}, enabled={li.is_enabled()}")

# Try to click AR Online SHP using JavaScript
for li in lis:
    if "AR Online SHP" in li.text:
        print(f"Found AR Online SHP, clicking with JS...")
        driver.execute_script("arguments[0].click();", li)
        time.sleep(1)
        break

# Check current sale type
try:
    sale_type = driver.find_element(By.CSS_SELECTOR, "#divSaletype2 span.select2-selection__rendered")
    print(f"Current sale type: {sale_type.text}")
except Exception as e:
    print(f"Error: {e}")
