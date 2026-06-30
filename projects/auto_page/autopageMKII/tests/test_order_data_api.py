"""
Integration test - ทดสอบค้นหาสินค้าจาก Order data (v3)
ใช้ API ค้นหาแทน
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
import pandas as pd
import json

# Read order data
ORDER_FILE = r"C:\Users\Satawad_Ta\Downloads\Order.toship.20260623_20260630.xlsx"
df = pd.read_excel(ORDER_FILE, dtype=str)

# Get unique SKUs
skus = df['เลขอ้างอิง SKU (SKU Reference No.)'].unique()[:5]

print("=" * 70)
print("ORDER DATA TEST v3 - ทดสอบค้นหาสินค้าผ่าน API")
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
print(f"URL: {driver.current_url}")

# Get cookies
cookies = driver.get_cookies()
cookie_dict = {c['name']: c['value'] for c in cookies}
print(f"Cookies: {list(cookie_dict.keys())}\n")

UAT_ORIGIN = "http://192.168.0.142:9099"

# Test each SKU via API
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

    try:
        # Search product via API
        url = f"{UAT_ORIGIN}/smartcore/smartpos/pointofsales/posmainv3/getProductMasterInfoPOSV3.htm"
        payload = {
            'activeFlag': 'true',
            'requestText': sku,
            'start': '1',
            'length': '5',
            'order[0][column]': '0',
            'order[0][dir]': 'asc',
            'modeScan': 'Y',
            'isIgnoreQty': 'false',
            'onlyProduct': 'false',
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
        }

        response = requests.post(url, data=payload, cookies=cookie_dict, headers=headers, verify=False)

        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                product = data['data'][0]
                found_sku = product.get('sku', 'N/A')
                found_name = product.get('name', 'N/A')[:50]
                found_price = product.get('price', 'N/A')
                print(f"     API Result: FOUND")
                print(f"     Found SKU: {found_sku}")
                print(f"     Found Name: {found_name}")
                print(f"     Found Price: {found_price}")
                results.append({
                    'sku': sku,
                    'status': 'FOUND',
                    'product': product_name,
                    'price': price,
                    'api_sku': found_sku,
                    'api_price': found_price
                })
            else:
                print(f"     API Result: NOT FOUND (empty data)")
                results.append({
                    'sku': sku,
                    'status': 'NOT_FOUND',
                    'product': product_name,
                    'price': price
                })
        else:
            print(f"     API Result: HTTP {response.status_code}")
            results.append({
                'sku': sku,
                'status': 'API_ERROR',
                'product': product_name,
                'price': price
            })
    except Exception as e:
        print(f"     Result: ERROR - {e}")
        results.append({
            'sku': sku,
            'status': 'ERROR',
            'product': product_name,
            'price': price
        })
    print()

# Summary
print("=" * 70)
print("TEST RESULTS SUMMARY")
print("=" * 70)
print(f"{'SKU':<15} {'Status':<12} {'Order Price':<12} {'API Price':<12} {'Product'}")
print("-" * 70)
for r in results:
    api_price = r.get('api_price', 'N/A')
    print(f"{r['sku']:<15} {r['status']:<12} {r.get('price', 'N/A'):<12} {api_price:<12} {r['product'][:30]}")
print("-" * 70)

found_count = sum(1 for r in results if r['status'] == 'FOUND')
print(f"\nTotal: {len(results)} SKUs tested")
print(f"Found in UAT: {found_count}")
print(f"Not Found: {len(results) - found_count}")

if found_count > 0:
    print("\nPrice comparison (Order vs UAT):")
    for r in results:
        if r['status'] == 'FOUND':
            order_price = r.get('price', 'N/A')
            api_price = r.get('api_price', 'N/A')
            match = "✓" if str(order_price) == str(api_price) else "✗"
            print(f"  {r['sku']}: Order={order_price}, UAT={api_price} {match}")

print("=" * 70)
