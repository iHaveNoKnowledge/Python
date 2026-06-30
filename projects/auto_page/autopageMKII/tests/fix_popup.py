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

# Dismiss any popups
try:
    popups = driver.find_elements(By.CSS_SELECTOR, ".swal2-confirm, .swal2-cancel, .swal2-close")
    for p in popups:
        if p.is_displayed():
            p.click()
            print("Dismissed popup")
            time.sleep(0.5)
except:
    pass

# Click overlay to dismiss
try:
    overlay = driver.find_element(By.CSS_SELECTOR, ".swal2-overlay")
    if overlay.is_displayed():
        driver.execute_script('arguments[0].style.display = "none";', overlay)
        print("Hidden overlay")
except:
    pass

time.sleep(1)

# Now try to select sale type
arrow = driver.find_element(
    By.CSS_SELECTOR, "#contentZen > div.ng-scope > div:nth-child(2) > div.panel-body > div.col-sm-3 > div.col-sm-12.nopadding > div.panel-body > div > div > div:nth-child(2) span.select2-selection__arrow")
arrow.click()
time.sleep(1)

lis = driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
print("Options:", [li.text for li in lis[:5]])

# Click AR Online SHP
for li in lis:
    if "AR Online SHP" in li.text:
        driver.execute_script("arguments[0].click();", li)
        print("Selected:", li.text)
        break

time.sleep(1)

# Check current sale type
try:
    rendered = driver.find_elements(By.CSS_SELECTOR, "span.select2-selection__rendered")
    for r in rendered:
        if "AR Online" in r.text:
            print("Current sale type:", r.text)
            break
except:
    pass
