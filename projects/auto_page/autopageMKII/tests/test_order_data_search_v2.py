"""
Integration test - ทดสอบค้นหาสินค้าจาก Order data จริง (v2)
รอผลลัพธ์ AJAX โหลดเสร็จ
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

# Get unique SKUs
skus = df['เลขอ้างอิง SKU (SKU Reference No.)'].unique()[:3]

print("=" * 70)
print("ORDER DATA TEST v2 - ทดสอบค้นหาสินค้าจาก Order file")
print("=" * 70)
print(f"Order file: {ORDER_FILE}")
print(f"Total orders: {len(df)}")
print(f"Testing with SKUs: {list(skus)}\n")

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

# Test each SKU
results = []
for i, sku in enumerate(skus):
    print(f"[{i+1}/{len(skus)}] Testing SKU: {sku}")

    # Get order info
    order_info = df[df['เลขอ้างอิง SKU (SKU Reference No.)'] == sku].iloc[0]
    product_name = order_info['ชื่อสินค้า'][:60]
    price = order_info['ราคาขาย']
    order_no = order_info['หมายเลขคำสั่งซื้อ']

    print(f"     Product: {product_name}...")
    print(f"     Price: {price} THB")
    print(f"     Order: {order_no}")

    try:
        # Find SKU input field
        sku_input = driver.find_element(By.ID, "svalue")
        sku_input.clear()
        sku_input.send_keys(sku)
        sku_input.send_keys(Keys.ENTER)

        # Wait for results to load (AJAX)
        print(f"     Waiting for search results...")
        time.sleep(3)

        # Check for product popup/modal or table rows
        try:
            # Look for product selection popup
            popup = driver.find_element(By.XPATH, "//div[contains(@class, 'modal') and contains(@style, 'display: block')]")
            print(f"     Popup appeared: YES")

            # Look for product rows in popup
            rows = popup.find_elements(By.TAG_NAME, "tr")
            print(f"     Rows in popup: {len(rows)}")

            if len(rows) > 0:
                # Click first product row
                first_row = rows[0]
                first_row.click()
                time.sleep(1)
                print(f"     Selected first product")
                results.append({'sku': sku, 'status': 'SELECTED', 'product': product_name, 'price': price})
            else:
                results.append({'sku': sku, 'status': 'NO_ROWS', 'product': product_name, 'price': price})

        except Exception as e:
            # No popup, check page content
            page_text = driver.find_element(By.TAG_NAME, "body").text
            if sku in page_text:
                print(f"     SKU found in page text")
                results.append({'sku': sku, 'status': 'FOUND', 'product': product_name, 'price': price})
            else:
                print(f"     SKU not found, checking for SN input...")
                # Check if SN input appeared (means product was found)
                try:
                    sn_input = driver.find_element(By.XPATH, "//div[contains(@class, 'modal') and contains(@style, 'display: block')]//input")
                    print(f"     SN input appeared - product found!")
                    results.append({'sku': sku, 'status': 'SN_INPUT', 'product': product_name, 'price': price})
                except:
                    print(f"     No SN input found")
                    results.append({'sku': sku, 'status': 'NOT_FOUND', 'product': product_name, 'price': price})

    except Exception as e:
        print(f"     Result: ERROR - {e}")
        results.append({'sku': sku, 'status': 'ERROR', 'product': product_name, 'price': price})

    print()

# Summary
print("=" * 70)
print("TEST RESULTS SUMMARY")
print("=" * 70)
print(f"{'SKU':<15} {'Status':<12} {'Price':<12} {'Product'}")
print("-" * 70)
for r in results:
    print(f"{r['sku']:<15} {r['status']:<12} {r.get('price', 'N/A'):<12} {r['product'][:35]}")
print("-" * 70)

found_count = sum(1 for r in results if r['status'] in ['FOUND', 'SELECTED', 'SN_INPUT'])
print(f"\nTotal: {len(results)} SKUs tested")
print(f"Found/Selected: {found_count}")
print(f"Not Found: {len(results) - found_count}")
print("=" * 70)
