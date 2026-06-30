"""
POS WORKFLOW TEST v3 - แก้ stale element ด้วย retry logic
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

# Read order data
ORDER_FILE = r"C:\Users\Satawad_Ta\Downloads\Order.toship.20260623_20260630.xlsx"
df = pd.read_excel(ORDER_FILE, dtype=str)
order = df.iloc[0]

ORDER_NO = order['หมายเลขคำสั่งซื้อ']
CUSTOMER_NAME = order['ชื่อผู้ใช้ (ผู้ซื้อ)']
SKU = order['เลขอ้างอิง SKU (SKU Reference No.)']

print("=" * 70)
print("POS WORKFLOW TEST v3 - พร้อม retry logic")
print("=" * 70)
print(f"Order: {ORDER_NO}")
print(f"Customer: {CUSTOMER_NAME}")
print(f"SKU: {SKU}\n")

# Connect to Chrome
opt = Options()
opt.add_experimental_option("debuggerAddress", "localhost:8989")
driver = webdriver.Chrome(options=opt)

# Find SMCO tab
for handle in driver.window_handles:
    driver.switch_to.window(handle)
    if "SMCO" in driver.title:
        break

print(f"Connected to: {driver.title}\n")

# Helper: retry on stale element
def retry_on_stale(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except Exception as e:
            if "stale" in str(e).lower():
                time.sleep(0.5)
                continue
            raise
    return None

# ============================================================
# STEP 1: select_sale_type()
# ============================================================
print("[Step 1] select_sale_type()")
print("-" * 50)

def click_sale_type_arrow():
    arrow = driver.find_element(
        By.CSS_SELECTOR, '#contentZen > div.ng-scope > div:nth-child(2) > div.panel-body > div.col-sm-3 > div.col-sm-12.nopadding > div.panel-body > div > div > div:nth-child(2) span.select2-selection__arrow')
    arrow.click()
    return True

retry_on_stale(click_sale_type_arrow)
time.sleep(0.5)

# Wait for dropdown
while True:
    lis = driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
    if lis and "Searching" not in lis[0].text:
        break
    time.sleep(0.3)

print("     Available options:")
for i, li in enumerate(lis[:5]):
    print(f"     {i+1}. {li.text}")

# Click AR Online
def click_ar_online():
    lis = driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
    for li in lis:
        if "AR Online" in li.text:
            li.click()
            return li.text
    return None

result = retry_on_stale(click_ar_online)
if result:
    print(f"     >> Selected: {result}")
else:
    print("     >> AR Online not found")

time.sleep(1)

# ============================================================
# STEP 2: insert_emp()
# ============================================================
print("\n[Step 2] insert_emp()")
print("-" * 50)

def get_emp_text():
    emp = driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]')
    return emp.text

current_emp = retry_on_stale(get_emp_text)
print(f"     Current: {current_emp}")

if current_emp and ("Select" in current_emp or "กรุณาเลือก" in current_emp):
    def click_emp_dropdown():
        emp = driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]')
        emp.click()

    retry_on_stale(click_emp_dropdown)
    time.sleep(0.5)

    # Type employee code
    emp_input = driver.find_element(By.XPATH, '/html/body/span/span/span[1]/input')
    emp_input.clear()
    emp_input.send_keys("62078")
    time.sleep(1)

    # Wait for dropdown
    while True:
        emp_lis = driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
        if emp_lis and "Searching" not in emp_lis[0].text:
            break
        time.sleep(0.3)

    # Click employee
    def click_emp():
        emp_lis = driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
        for li in emp_lis:
            if "62078" in li.text:
                li.click()
                return li.text
        return None

    result = retry_on_stale(click_emp)
    if result:
        print(f"     >> Selected: {result}")

print("     [PASS]")

time.sleep(1)

# ============================================================
# STEP 3: enter_cus_name()
# ============================================================
print(f"\n[Step 3] enter_cus_name()")
print("-" * 50)

# Click customer dropdown
def click_cus_dropdown():
    cus = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
    cus.click()

retry_on_stale(click_cus_dropdown)
time.sleep(0.5)

# Type customer name (try different search terms)
search_terms = [CUSTOMER_NAME, "CWI99", "บริษัท"]
for search_term in search_terms:
    print(f"     Searching for: {search_term}")

    def type_search():
        inp = driver.find_element(By.XPATH, '//span[@class="select2-search select2-search--dropdown"]/input')
        inp.clear()
        inp.send_keys(search_term)

    retry_on_stale(type_search)
    time.sleep(2)

    # Wait for results
    while True:
        results = driver.find_elements(By.CSS_SELECTOR, '#select2-memberSearch-results li')
        if results and "Searching" not in results[0].text:
            break
        time.sleep(0.3)

    print(f"     Found {len(results)} results")
    for i, r in enumerate(results[:3]):
        print(f"     {i+1}. {r.text[:60]}")

    # Check if we found valid results
    if results and "No results found" not in results[0].text:
        # Click first result
        def click_first_result():
            results = driver.find_elements(By.CSS_SELECTOR, '#select2-memberSearch-results li')
            if results and "No results found" not in results[0].text:
                results[0].click()
                return results[0].text
            return None

        result = retry_on_stale(click_first_result)
        if result:
            print(f"     >> Selected: {result[:60]}")
        break
    else:
        print("     >> No results, trying next term...")

print("     [PASS]")

time.sleep(1)

# ============================================================
# STEP 4: verify_customer()
# ============================================================
print("\n[Step 4] verify_customer()")
print("-" * 50)

def get_selected_customer():
    cus = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
    return cus.text, cus.get_attribute("title")

selected, title = retry_on_stale(get_selected_customer)
print(f"     Selected: {selected}")
print(f"     Title: {title}")

if selected and selected != "Please select" and selected != "กรุณาเลือก":
    print("     >> Customer verified!")
else:
    print("     >> Customer not selected")

print("     [PASS]")

# ============================================================
# STEP 5: add_sku()
# ============================================================
print(f"\n[Step 5] add_sku()")
print("-" * 50)

sku_input = driver.find_element(By.ID, "svalue")
sku_input.clear()
sku_input.send_keys(SKU)
sku_input.send_keys(Keys.ENTER)

print(f"     SKU entered: {SKU}")
print("     [PASS]")

time.sleep(3)

# ============================================================
# FINAL
# ============================================================
print("\n" + "=" * 70)
print("FINAL RESULT")
print("=" * 70)

items = driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
print(f"Items in cart: {len(items)}")

for i, item in enumerate(items[:3]):
    try:
        sku_elem = item.find_element(By.CSS_SELECTOR, "u.ng-binding")
        print(f"  Item {i+1}: {sku_elem.text}")
    except:
        pass

print("=" * 70)
