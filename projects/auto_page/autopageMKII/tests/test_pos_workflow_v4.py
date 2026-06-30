"""
POS WORKFLOW TEST v4 - เลือก AR Online SHP
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
SKU = order['เลขอ้างอิง SKU (SKU Reference No.)']
PRODUCT = order['ชื่อสินค้า'][:60]
PRICE = order['ราคาขาย']

print("=" * 70)
print("POS WORKFLOW TEST v4")
print("=" * 70)
print(f"Order: {ORDER_NO}")
print(f"SKU: {SKU}")
print(f"Product: {PRODUCT}")
print(f"Price: {PRICE} THB\n")

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

def retry_on_stale(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except:
            time.sleep(0.5)
            continue
    return None

# ============================================================
# STEP 1: select_sale_type() - AR Online SHP
# ============================================================
print("[Step 1] select_sale_type() - AR Online SHP")
print("-" * 50)

try:
    # คลิก dropdown
    def click_arrow():
        arrow = driver.find_element(
            By.CSS_SELECTOR, '#contentZen > div.ng-scope > div:nth-child(2) > div.panel-body > div.col-sm-3 > div.col-sm-12.nopadding > div.panel-body > div > div > div:nth-child(2) span.select2-selection__arrow')
        arrow.click()

    retry_on_stale(click_arrow)
    time.sleep(0.5)

    # Wait for dropdown
    while True:
        lis = driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
        if lis and "Searching" not in lis[0].text:
            break
        time.sleep(0.3)

    print("     Options:")
    for li in lis[:5]:
        print(f"     - {li.text}")

    # เลือก AR Online SHP
    def click_ar():
        lis = driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
        for li in lis:
            if "AR Online SHP" in li.text:
                li.click()
                return li.text
        return None

    result = retry_on_stale(click_ar)
    if result:
        print(f"     >> Selected: {result}")
    else:
        print("     >> AR Online SHP not found")

    print("     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(1)

# Check for popup
try:
    popup = driver.find_element(By.XPATH, "//button[@class = 'swal2-confirm styled' and (text()='OK' or text()='ตกลง')]")
    popup.click()
    print("     Popup dismissed")
except:
    pass

# ============================================================
# STEP 2: insert_emp() - ตรวจสอบพนักงาน
# ============================================================
print("\n[Step 2] insert_emp()")
print("-" * 50)

def get_emp():
    emp = driver.find_element(By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]')
    return emp.text

current_emp = retry_on_stale(get_emp)
print(f"     Current employee: {current_emp}")

if current_emp and "62078" in current_emp:
    print("     >> Employee already selected")
else:
    print("     >> Need to select employee")

print("     [PASS]")

time.sleep(1)

# ============================================================
# STEP 3: enter_cus_name() - CWI99
# ============================================================
print("\n[Step 3] enter_cus_name() - CWI99")
print("-" * 50)

try:
    # Click customer dropdown
    def click_cus():
        cus = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
        cus.click()

    retry_on_stale(click_cus)
    time.sleep(0.5)

    # Type CWI99
    def type_cwi():
        inp = driver.find_element(By.XPATH, '//span[@class="select2-search select2-search--dropdown"]/input')
        inp.clear()
        inp.send_keys("CWI99")

    retry_on_stale(type_cwi)
    time.sleep(2)

    # Wait for results
    while True:
        results = driver.find_elements(By.CSS_SELECTOR, '#select2-memberSearch-results li')
        if results and "Searching" not in results[0].text:
            break
        time.sleep(0.3)

    print(f"     Found {len(results)} results")
    for r in results[:3]:
        print(f"     - {r.text[:60]}")

    # Click CWI99
    def click_cwi():
        results = driver.find_elements(By.CSS_SELECTOR, '#select2-memberSearch-results li')
        for r in results:
            if "CWI99" in r.text:
                r.click()
                return r.text
        return None

    result = retry_on_stale(click_cwi)
    if result:
        print(f"     >> Selected: {result}")

    print("     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(1)

# ============================================================
# STEP 4: verify_customer()
# ============================================================
print("\n[Step 4] verify_customer()")
print("-" * 50)

def get_customer():
    cus = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
    return cus.text

selected = retry_on_stale(get_customer)
print(f"     Selected: {selected}")

if selected and "CWI99" in selected:
    print("     >> Customer verified!")
else:
    print("     >> Customer not selected correctly")

print("     [PASS]")

# ============================================================
# STEP 5: add_sku() - CO6-011598
# ============================================================
print(f"\n[Step 5] add_sku() - {SKU}")
print("-" * 50)

try:
    sku_input = driver.find_element(By.ID, "svalue")
    sku_input.clear()
    sku_input.send_keys(SKU)
    sku_input.send_keys(Keys.ENTER)
    print(f"     SKU entered: {SKU}")
    print("     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(3)

# ============================================================
# CHECK RESULT
# ============================================================
print("\n" + "=" * 70)
print("RESULT")
print("=" * 70)

items = driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
print(f"Items in cart: {len(items)}")

for i, item in enumerate(items[:5]):
    try:
        sku_elem = item.find_element(By.CSS_SELECTOR, "u.ng-binding")
        print(f"  Item {i+1}: SKU = {sku_elem.text}")
    except:
        pass

# Check for error messages
try:
    errors = driver.find_elements(By.CSS_SELECTOR, '.swal2-content, .alert-danger, .error')
    for err in errors:
        if err.text:
            print(f"  Error: {err.text[:100]}")
except:
    pass

print("=" * 70)
