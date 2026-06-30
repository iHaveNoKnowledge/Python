"""
Integration test - ทดสอบค้นหาสินค้าจาก Order data จริง
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
skus = df['เลขอ้างอิง SKU (SKU Reference No.)'].unique()[:5]

print("=" * 70)
print("ORDER DATA TEST - ทดสอบค้นหาสินค้าจาก Order file")
print("=" * 70)
print(f"Order file: {ORDER_FILE}")
print(f"Total orders: {len(df)}")
print(f"Unique SKUs: {len(df['เลขอ้างอิง SKU (SKU Reference No.)'].unique())}")
print(f"\nTesting with SKUs: {list(skus)}")

# Connect to Chrome
opt = Options()
opt.add_experimental_option("debuggerAddress", "localhost:8989")
driver = webdriver.Chrome(options=opt)

# Find SMCO tab
for handle in driver.window_handles:
    driver.switch_to.window(handle)
    if "SMCO" in driver.title:
        break

print(f"\nConnected to: {driver.title}")
print(f"URL: {driver.current_url}\n")

# Test each SKU
results = []
for i, sku in enumerate(skus):
    print(f"[{i+1}/{len(skus)}] Testing SKU: {sku}")

    # Get order info for this SKU
    order_info = df[df['เลขอ้างอิง SKU (SKU Reference No.)'] == sku].iloc[0]
    product_name = order_info['ชื่อสินค้า'][:50]
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

        # Wait for results
        time.sleep(2)

        # Check if product was found
        page_source = driver.page_source
        if sku in page_source:
            print(f"     Result: FOUND in page")
            results.append({'sku': sku, 'status': 'FOUND', 'product': product_name})
        else:
            print(f"     Result: NOT found in page source")
            results.append({'sku': sku, 'status': 'NOT_FOUND', 'product': product_name})

    except Exception as e:
        print(f"     Result: ERROR - {e}")
        results.append({'sku': sku, 'status': 'ERROR', 'product': product_name})

    print()

# Summary
print("=" * 70)
print("TEST RESULTS SUMMARY")
print("=" * 70)
print(f"{'SKU':<15} {'Status':<12} {'Product'}")
print("-" * 70)
for r in results:
    print(f"{r['sku']:<15} {r['status']:<12} {r['product'][:40]}")
print("-" * 70)

found_count = sum(1 for r in results if r['status'] == 'FOUND')
print(f"\nTotal: {len(results)} SKUs tested")
print(f"Found: {found_count}")
print(f"Not Found: {len(results) - found_count}")
print("=" * 70)
