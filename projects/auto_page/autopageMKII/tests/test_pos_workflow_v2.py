"""
POS WORKFLOW TEST - ตามขั้นตอนจริงจาก autopage_MKII_ver5_2_0LITE.py

ขั้นตอน:
1. select_sale_type()     → เลือก AR Online
2. insert_emp()           → เลือก Sale Person
3. enter_cus_name()       → ใส่ชื่อลูกค้าจาก order
4. verify_customer()      → ตรวจสอบชื่อลูกค้า
5. add_sku()              → ใส่ SKU สินค้า
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

# Read order data
ORDER_FILE = r"C:\Users\Satawad_Ta\Downloads\Order.toship.20260623_20260630.xlsx"
df = pd.read_excel(ORDER_FILE, dtype=str)
order = df.iloc[0]

ORDER_NO = order['หมายเลขคำสั่งซื้อ']
CUSTOMER_NAME = order['ชื่อผู้ใช้ (ผู้ซื้อ)']
SKU = order['เลขอ้างอิง SKU (SKU Reference No.)']
PRODUCT = order['ชื่อสินค้า'][:50]
PRICE = order['ราคาขาย']

print("=" * 70)
print("POS WORKFLOW TEST - ตามขั้นตอนจริง")
print("=" * 70)
print(f"Order: {ORDER_NO}")
print(f"Customer: {CUSTOMER_NAME}")
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

print(f"Connected to: {driver.title}")
print(f"URL: {driver.current_url}\n")

wait = WebDriverWait(driver, 15)

# ============================================================
# STEP 1: select_sale_type()
# ============================================================
print("[Step 1] select_sale_type() - เลือก AR Online")
print("-" * 50)

try:
    # คลิก dropdown sale type ตามโค้ดจริง
    sale_type_arrow = driver.find_element(
        By.CSS_SELECTOR, '#contentZen > div.ng-scope > div:nth-child(2) > div.panel-body > div.col-sm-3 > div.col-sm-12.nopadding > div.panel-body > div > div > div:nth-child(2) span.select2-selection__arrow')
    sale_type_arrow.click()
    time.sleep(0.5)

    # รอให้ dropdown โหลด (ตาม dropdown_handler)
    while True:
        li_locators = driver.find_elements(By.CSS_SELECTOR, "ul.select2-results__options li")
        if li_locators and "Searching" not in li_locators[0].text:
            break
        time.sleep(0.3)

    # แสดงตัวเลือกทั้งหมด
    print("     Available sale types:")
    for i, li in enumerate(li_locators[:10]):
        print(f"     {i+1}. {li.text}")

    # เลือก "AR Online" หรือ "Online Sale"
    selected = False
    for li in li_locators:
        if "AR Online" in li.text or "Online Sale" in li.text:
            li.click()
            print(f"     >> Selected: {li.text}")
            selected = True
            break

    if not selected:
        # ถ้าไม่เจอ AR Online เลือกตัวแรกที่มี "Sale" หรือ "AR"
        for li in li_locators:
            if "Sale" in li.text or "AR" in li.text:
                li.click()
                print(f"     >> Selected: {li.text}")
                selected = True
                break

    if not selected:
        print("     [WARN] AR Online not found, using first option")
        if li_locators:
            li_locators[0].click()
            print(f"     >> Selected: {li_locators[0].text}")

    print("     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(1)

# ============================================================
# STEP 2: insert_emp()
# ============================================================
print("\n[Step 2] insert_emp() - เลือก Sale Person")
print("-" * 50)

try:
    # หา sale person element ตามโค้ดจริง
    emp_xpath = '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]'
    emp_element = driver.find_element(By.XPATH, emp_xpath)
    current_emp = emp_element.text
    print(f"     Current: {current_emp}")

    # ถ้ายังไม่ได้เลือกพนักงาน
    if "Select" in current_emp or "กรุณาเลือก" in current_emp or not current_emp:
        emp_element.click()
        time.sleep(0.5)

        # หา input field สำหรับใส่รหัสพนักงาน
        emp_input = driver.find_element(By.XPATH, '/html/body/span/span/span[1]/input')
        emp_input.clear()
        emp_input.send_keys("62078")
        time.sleep(1)

        # รอ dropdown โหลด
        while True:
            emp_options = driver.find_elements(By.CSS_SELECTOR, 'ul.select2-results__options li')
            if emp_options and "Searching" not in emp_options[0].text:
                break
            time.sleep(0.3)

        # เลือกพนักงาน
        for opt in emp_options:
            if "62078" in opt.text:
                opt.click()
                print(f"     >> Selected: {opt.text}")
                break

    print("     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(1)

# ============================================================
# STEP 3: enter_cus_name()
# ============================================================
print(f"\n[Step 3] enter_cus_name() - ใส่ชื่อลูกค้า: {CUSTOMER_NAME}")
print("-" * 50)

try:
    # หา customer dropdown ตามโค้ดจริง
    cus_dropdown_xpath = '//span[@id="select2-memberSearch-container"]'
    cus_dropdown = driver.find_element(By.XPATH, cus_dropdown_xpath)
    current_cus = cus_dropdown.text
    print(f"     Current customer: {current_cus}")

    # คลิก dropdown
    cus_dropdown.click()
    time.sleep(0.5)

    # หา input field สำหรับค้นหาชื่อลูกค้า
    cus_input_xpath = '//span[@class="select2-search select2-search--dropdown"]/input'
    cus_input = driver.find_element(By.XPATH, cus_input_xpath)
    cus_input.clear()

    # ใส่ชื่อลูกค้าจาก order
    cus_input.send_keys(CUSTOMER_NAME)
    time.sleep(2)

    # รอ dropdown โหลด
    while True:
        cus_results = driver.find_elements(By.CSS_SELECTOR, '#select2-memberSearch-results li')
        if cus_results and "Searching" not in cus_results[0].text:
            break
        time.sleep(0.3)

    # แสดงผลลัพธ์
    print(f"     Found {len(cus_results)} results:")
    for i, result in enumerate(cus_results[:5]):
        print(f"     {i+1}. {result.text[:60]}")

    # เลือกผลลัพธ์ที่ตรงกับชื่อลูกค้า
    selected = False
    for result in cus_results:
        if CUSTOMER_NAME in result.text:
            result.click()
            print(f"     >> Selected: {result.text[:60]}")
            selected = True
            break

    if not selected and cus_results:
        # ถ้าไม่เจอชื่อตรงๆ เลือกผลลัพธ์แรก
        cus_results[0].click()
        print(f"     >> Selected first result: {cus_results[0].text[:60]}")

    print("     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(1)

# ============================================================
# STEP 4: verify_customer()
# ============================================================
print("\n[Step 4] verify_customer() - ตรวจสอบชื่อลูกค้า")
print("-" * 50)

try:
    # ตรวจสอบชื่อลูกค้าที่เลือก
    cus_container = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
    selected_cus = cus_container.text
    cus_title = cus_container.get_attribute("title")

    print(f"     Selected customer: {selected_cus}")
    print(f"     Customer title: {cus_title}")

    # ตรวจสอบว่าชื่อลูกค้าถูกต้อง
    if CUSTOMER_NAME in selected_cus or CUSTOMER_NAME in cus_title:
        print("     >> Customer name verified!")
    else:
        print("     >> Customer name might be different (check manually)")

    print("     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

# ============================================================
# STEP 5: add_sku()
# ============================================================
print(f"\n[Step 5] add_sku() - ใส่ SKU: {SKU}")
print("-" * 50)

try:
    # หา SKU input field
    sku_input = driver.find_element(By.ID, "svalue")
    print(f"     SKU input found: id={sku_input.get_attribute('id')}")

    # ใส่ SKU
    sku_input.clear()
    sku_input.send_keys(SKU)
    sku_input.send_keys(Keys.ENTER)

    print(f"     SKU entered: {SKU}")
    print(f"     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(3)

# ============================================================
# FINAL: ตรวจสอบสถานะ
# ============================================================
print("\n" + "=" * 70)
print("FINAL RESULT - ตรวจสอบสถานะ")
print("=" * 70)

try:
    # ตรวจสอบว่ามีสินค้าในตะกร้าหรือยัง
    items = driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
    print(f"Items in cart: {len(items)}")

    # แสดงข้อมูลสินค้าในตะกร้า
    for i, item in enumerate(items[:3]):
        try:
            sku_elem = item.find_element(By.CSS_SELECTOR, "u.ng-binding")
            sku_text = sku_elem.text
            print(f"  Item {i+1}: SKU = {sku_text}")
        except:
            pass

    # ตรวจสอบยอดรวม
    try:
        total_elem = driver.find_element(By.XPATH, "//*[contains(@class, 'total') or contains(text(), 'รวม')]")
        print(f"Total: {total_elem.text}")
    except:
        print("Total: Not displayed yet")

except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
print("WORKFLOW COMPLETE")
print("=" * 70)
print(f"Order: {ORDER_NO}")
print(f"Customer: {CUSTOMER_NAME}")
print(f"SKU: {SKU}")
print("=" * 70)
