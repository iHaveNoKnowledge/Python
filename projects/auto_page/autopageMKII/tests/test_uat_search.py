"""
Integration test - ค้นหาสินค้าใน UAT ด้วยคำค้นหาทั่วไป
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
import json

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

# Get cookies
cookies = driver.get_cookies()
cookie_dict = {c['name']: c['value'] for c in cookies}

UAT_ORIGIN = "http://192.168.0.142:9099"

# Test search with different terms
search_terms = ["ASUS", "LENOVO", "LG", "monitor", "laptop"]

print("\n" + "=" * 70)
print("SEARCH TEST - ค้นหาสินค้าด้วยคำค้นหาทั่วไป")
print("=" * 70)

for term in search_terms:
    print(f"\nSearching for: '{term}'")

    url = f"{UAT_ORIGIN}/smartcore/smartpos/pointofsales/posmainv3/getProductMasterInfoPOSV3.htm"
    payload = {
        'activeFlag': 'true',
        'requestText': term,
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
            print(f"  Found {len(data['data'])} products:")
            for i, product in enumerate(data['data'][:3]):
                sku = product.get('sku', 'N/A')
                name = product.get('name', 'N/A')[:50]
                price = product.get('price', 'N/A')
                print(f"    {i+1}. SKU: {sku}")
                print(f"       Name: {name}")
                print(f"       Price: {price}")
        else:
            print(f"  No products found")
    else:
        print(f"  HTTP Error: {response.status_code}")

print("\n" + "=" * 70)
