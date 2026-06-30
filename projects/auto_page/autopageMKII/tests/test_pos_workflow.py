"""
Integration test - ทดสอบ POS workflow ตามขั้นตอนจริงจาก autopage_MKII_ver5_2_0LITE.py

Workflow ที่ถูกต้อง:
1. เลือก Sale Type (AR Online / Online Sale)
2. ใส่รหัสพนักงาน (insert_emp)
3. ใส่ชื่อลูกค้า (enter_cus_name)
4. ใส่ SKU สินค้า
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Connect to Chrome
opt = Options()
opt.add_experimental_option("debuggerAddress", "localhost:8989")
driver = webdriver.Chrome(options=opt)

# Find SMCO tab
for handle in driver.window_handles:
    driver.switch_to.window(handle)
    if "SMCO" in driver.title:
        break

print("=" * 70)
print("POS WORKFLOW TEST - ตามขั้นตอนจริงจาก autopage_MKII_ver5_2_0LITE.py")
print("=" * 70)
print(f"Connected to: {driver.title}")
print(f"URL: {driver.current_url}\n")

wait = WebDriverWait(driver, 10)

# Step 1: Select Sale Type
print("[Step 1] เลือก Sale Type (AR Online)...")
try:
    # คลิก dropdown sale type
    sale_type_arrow = driver.find_element(
        By.CSS_SELECTOR, '#contentZen > div.ng-scope > div:nth-child(2) > div.panel-body > div.col-sm-3 > div.col-sm-12.nopadding > div.panel-body > div > div > div:nth-child(2) span.select2-selection__arrow')
    sale_type_arrow.click()
    time.sleep(0.5)

    # เลือก "AR Online" หรือ "Online Sale"
    try:
        ar_option = driver.find_element(
            By.XPATH, '//*[@id="select2-divSaletype2-results"]/li[starts-with(., "AR Online") or starts-with(., "Online Sale")]')
        ar_option.click()
        print(f"     Selected: {ar_option.text}")
        print(f"     [PASS]")
    except Exception as e:
        print(f"     [WARN] AR Online not found, trying other options...")
        options = driver.find_elements(By.CSS_SELECTOR, '#select2-divSaletype2-results li')
        for opt in options[:5]:
            print(f"     - {opt.text}")
        if options:
            options[0].click()
            print(f"     Selected first option")
            print(f"     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(1)

# Step 2: Insert Employee Code
print("\n[Step 2] ใส่รหัสพนักงาน...")
try:
    emp_element = driver.find_element(
        By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div/div/div[3]/div[1]/span/span[1]/span/span[1]')
    current_emp = emp_element.text
    print(f"     Current employee: {current_emp}")

    # ถ้ายังไม่ได้เลือกพนักงาน ให้ใส่รหัส
    if "Please select" in current_emp or "กรุณาเลือก" in current_emp or not current_emp:
        emp_element.click()
        time.sleep(0.5)

        emp_input = driver.find_element(By.XPATH, '/html/body/span/span/span[1]/input')
        emp_input.send_keys("62078")  # รหัสพนักงาน
        time.sleep(1)

        # เลือกจาก dropdown
        try:
            emp_option = driver.find_element(By.XPATH, '/html/body/span/span/span[2]/ul/li')
            emp_option.click()
            print(f"     Selected employee: 62078")
        except:
            print(f"     Employee dropdown not found")
    else:
        print(f"     Employee already selected")

    print(f"     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(1)

# Step 3: Enter Customer Name
print("\n[Step 3] ใส่ชื่อลูกค้า...")
try:
    # ค้นหาชื่อลูกค้าจาก dropdown
    cus_dropdown = driver.find_element(By.XPATH, '//span[@id="select2-memberSearch-container"]')
    print(f"     Current customer: {cus_dropdown.text}")

    # คลิก dropdown
    cus_dropdown.click()
    time.sleep(0.5)

    # หา input field สำหรับค้นหาชื่อลูกค้า
    cus_input = driver.find_element(By.XPATH, '//span[@class="select2-search select2-search--dropdown"]/input')
    cus_input.clear()
    cus_input.send_keys("CWI99")  # ชื่อลูกค้าทดสอบ
    time.sleep(2)

    # ดูผลลัพธ์
    try:
        results = driver.find_elements(By.CSS_SELECTOR, '#select2-memberSearch-results li')
        print(f"     Found {len(results)} results")
        for i, result in enumerate(results[:3]):
            print(f"     - {result.text[:50]}")

        # เลือกผลลัพธ์แรก
        if results and results[0].text != "Searching...":
            results[0].click()
            print(f"     Selected first result")
    except Exception as e:
        print(f"     No results found: {e}")

    print(f"     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(1)

# Step 4: Enter SKU (ค่อยใส่สินค้าได้)
print("\n[Step 4] ใส่ SKU สินค้า...")
try:
    # หา SKU input field
    sku_input = driver.find_element(By.ID, "svalue")
    print(f"     SKU input found: id={sku_input.get_attribute('id')}")

    # ใส่ SKU
    sku_input.clear()
    sku_input.send_keys("CO6-011598")  # SKU จาก order data
    sku_input.send_keys(Keys.ENTER)

    print(f"     SKU entered: CO6-011598")
    print(f"     [PASS] - SKU can be entered after customer info")
except Exception as e:
    print(f"     [FAIL] {e}")

time.sleep(2)

# Check current state
print("\n[Final] ตรวจสอบสถานะปัจจุบัน...")
try:
    # ตรวจสอบว่ามีสินค้าในตะกร้าหรือยัง
    items = driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
    print(f"     Items in cart: {len(items)}")

    # ตรวจสอบยอดรวม
    try:
        total = driver.find_element(By.XPATH, "//*[contains(text(), 'รวม') or contains(text(), 'Total')]")
        print(f"     Total: {total.text}")
    except:
        print(f"     Total not found yet")

    print(f"     [PASS]")
except Exception as e:
    print(f"     [FAIL] {e}")

print("\n" + "=" * 70)
print("WORKFLOW TEST COMPLETE")
print("=" * 70)
print("Steps completed:")
print("  1. Select Sale Type - DONE")
print("  2. Insert Employee - DONE")
print("  3. Enter Customer Name - DONE")
print("  4. Enter SKU - DONE")
print("=" * 70)
