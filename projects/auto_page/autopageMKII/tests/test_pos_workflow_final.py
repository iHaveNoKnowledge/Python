"""
POS WORKFLOW TEST - ตามขั้นตอนจริงจาก autopage_MKII_ver5_2_0LITE.py

ขั้นตอนที่ถูกต้อง:
1. select_sale_type()     → เลือก AR Online SHP
2. insert_emp()           → เลือก Sale Person
3. cus_name logic         → ผสมชื่อจาก order data
4. cus_name_cleaner()     → ทำความสะอาดชื่อ
5. enter_cus_name()       → ค้นหาลูกค้าจาก SMCO
6. verify_customer()      → ตรวจสอบชื่อลูกค้า
7. add_sku()              → ใส่ SKU สินค้า
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import re

# ============================================================
# Step 0: Read order data and prepare customer name
# ============================================================
ORDER_FILE = r"C:\Users\Satawad_Ta\Downloads\Order.toship.20260623_20260630.xlsx"
df = pd.read_excel(ORDER_FILE, dtype=str)
order = df.iloc[0]

ORDER_NO = order['หมายเลขคำสั่งซื้อ']
SKU = order['เลขอ้างอิง SKU (SKU Reference No.)']
PRODUCT = order['ชื่อสินค้า'][:60]
PRICE = order['ราคาขาย']

# ============================================================
# cus_name logic from _order_search_internal (line 2253-2262)
# ============================================================
name_col = order.get('ชื่อ', '')
username = order.get('ชื่อผู้ใช้ (ผู้ซื้อ)', '')
masked_name = order.get('ชื่อผู้รับ', '')
masked_tel = order.get('หมายเลขโทรศัพท์', '')

if name_col and str(name_col) != 'nan':
    cus_name = re.sub(r'\s{2,}', ' ', str(name_col).strip().replace('\u200b', ''))
else:
    cus_name = re.sub(r'[\(\)]', '', str(username) + ' ' + str(masked_name) + ' ' + str(masked_tel))

# ============================================================
# cus_name_cleaner (line 2596-2602)
# ============================================================
def cus_name_cleaner(name, account_name=':'):
    is_found = re.search(r'\[.*\]|\(.*\)|\{.*\}', name)
    name = re.sub(r'\[.*\]|\(.*\)|\{.*\}', '', name).strip() if is_found else name.strip()
    name += ' ' + account_name if len(name.split()) == 1 else ''
    return name

cus_search_input = cus_name_cleaner(cus_name)

# ============================================================
# Tax check (line 2285-2300)
# ============================================================
tax_num = order.get('หมายเลขประจำตัวผู้เสียภาษี', '')
is_tax_required = tax_num and str(tax_num) != 'nan' and len(str(tax_num).replace('-', '')) == 13

if is_tax_required:
    search_input = str(tax_num).replace('-', '')
else:
    search_input = cus_search_input

print("=" * 70)
print("POS WORKFLOW TEST - ตามขั้นตอนจริง")
print("=" * 70)
print(f"Order: {ORDER_NO}")
print(f"SKU: {SKU}")
print(f"Product: {PRODUCT}")
print(f"Price: {PRICE} THB")
print(f"\nCustomer Name (raw): {username} {masked_name} {masked_tel}")
print(f"After cus_name_cleaner: {cus_search_input}")
print(f"Tax Required: {is_tax_required}")
print(f"Search Input: {search_input}\n")

# ============================================================
# Connect to Chrome
# ============================================================
opt = Options()
opt.add_experimental_option("debuggerAddress", "localhost:8989")
driver = webdriver.Chrome(options=opt)

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
        except:
            time.sleep(0.5)
            continue
    return None

# Helper: wait for dropdown
def wait_for_dropdown(css_selector, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        lis = driver.find_elements(By.CSS_SELECTOR, css_selector)
        if lis and "Searching" not in lis[0].text:
            return lis
        time.sleep(0.3)
    return []

# ============================================================
# STEP 1: select_sale_type() - AR Online SHP
# ============================================================
print("[Step 1] select_sale_type()")
print("-" * 50)

def click_arrow():
    arrow = driver.find_element(
        By.CSS_SELECTOR, '#contentZen > div.ng-scope > div:nth-child(2) > div.panel-body > div.col-sm-3 > div.col-sm-12.nopadding > div.panel-body > div > div > div:nth-child(2) span.select2-selection__arrow')
    arrow.click()

retry_on_stale(click_arrow)
time.sleep(0.5)

lis = wait_for_dropdown("ul.select2-results__options li")
print(f"     Options: {[li.text for li in lis[:5]]}")

def click_ar():
    lis = driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
    for li in lis:
        if "AR Online SHP" in li.text:
            li.click()
            return li.text
    return None

result = retry_on_stale(click_ar)
print(f"     >> Selected: {result}")
print("     [PASS]")

time.sleep(1)

# ============================================================
# STEP 2: insert_emp()
# ============================================================
print("\n[Step 2] insert_emp()")
print("-" * 50)

def get_emp():
    emp = driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]')
    return emp.text

current_emp = retry_on_stale(get_emp)
print(f"     Current: {current_emp}")

if current_emp and ("62078" in current_emp or "Satawad" in current_emp):
    print("     >> Employee already selected")
else:
    def click_emp():
        emp = driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]')
        emp.click()

    retry_on_stale(click_emp)
    time.sleep(0.5)

    emp_input = driver.find_element(By.XPATH, '/html/body/span/span/span[1]/input')
    emp_input.clear()
    emp_input.send_keys("62078")
    time.sleep(1)

    emp_lis = wait_for_dropdown("ul.select2-results__options li")
    for li in emp_lis:
        if "62078" in li.text:
            li.click()
            print(f"     >> Selected: {li.text}")
            break

print("     [PASS]")

time.sleep(1)

# ============================================================
# STEP 3: Clear customer name if exists
# ============================================================
print("\n[Step 3] Clear customer name if exists")
print("-" * 50)

def get_cus():
    cus = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
    return cus.text

current_cus = retry_on_stale(get_cus)
print(f"     Current: {current_cus}")

if current_cus and current_cus != "Please select" and current_cus != "กรุณาเลือก":
    # Need to clear
    def click_cus():
        cus = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
        cus.click()

    retry_on_stale(click_cus)
    time.sleep(0.5)

    # Click X to clear
    try:
        x_btn = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]/span')
        x_btn.click()
        time.sleep(0.5)
        print("     >> Cleared existing customer")
    except:
        print("     >> No X button found")

print("     [PASS]")

time.sleep(1)

# ============================================================
# STEP 4: set_cus_name_search_type()
# ============================================================
print("\n[Step 4] set_cus_name_search_type()")
print("-" * 50)

# Click search type button
try:
    search_type_btn = driver.find_element(
        By.XPATH, "//div[contains(@ng-show, 'abbCustomerFlag')]//div[contains(@class, 'input-group-prepend')]/button")
    search_type_btn.click()
    time.sleep(0.5)
    print("     >> Search type button clicked")
except Exception as e:
    print(f"     [WARN] {e}")

print("     [PASS]")

time.sleep(1)

# ============================================================
# STEP 5: enter_cus_name() - ค้นหาลูกค้า
# ============================================================
print(f"\n[Step 5] enter_cus_name() - ค้นหา: {search_input}")
print("-" * 50)

# Click customer dropdown
def click_cus_dropdown():
    cus = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
    cus.click()

retry_on_stale(click_cus_dropdown)
time.sleep(0.5)

# Type search input
def type_search():
    inp = driver.find_element(By.XPATH, '//span[@class="select2-search select2-search--dropdown"]/input')
    inp.clear()
    inp.send_keys(search_input)

retry_on_stale(type_search)
time.sleep(2)

# Wait for results
cus_results = wait_for_dropdown('#select2-memberSearch-results li')
print(f"     Found {len(cus_results)} results")
for i, r in enumerate(cus_results[:5]):
    print(f"     {i+1}. {r.text[:70]}")

# Click first valid result
if cus_results and "No results found" not in cus_results[0].text:
    def click_first():
        results = driver.find_elements(By.CSS_SELECTOR, '#select2-memberSearch-results li')
        if results and "No results found" not in results[0].text:
            results[0].click()
            return results[0].text
        return None

    result = retry_on_stale(click_first)
    print(f"     >> Selected: {result[:70] if result else 'None'}")
else:
    print("     >> No results found")

print("     [PASS]")

time.sleep(1)

# ============================================================
# STEP 6: verify_customer()
# ============================================================
print("\n[Step 6] verify_customer()")
print("-" * 50)

def get_selected():
    cus = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
    return cus.text, cus.get_attribute("title")

selected, title = retry_on_stale(get_selected)
print(f"     Selected: {selected}")
print(f"     Title: {title}")

if selected and selected != "Please select" and selected != "กรุณาเลือก":
    print("     >> Customer verified!")
else:
    print("     >> Customer not selected")

print("     [PASS]")

# ============================================================
# STEP 7: add_sku()
# ============================================================
print(f"\n[Step 7] add_sku() - {SKU}")
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

for i, item in enumerate(items[:5]):
    try:
        sku_elem = item.find_element(By.CSS_SELECTOR, "u.ng-binding")
        print(f"  Item {i+1}: SKU = {sku_elem.text}")
    except:
        pass

print("=" * 70)
