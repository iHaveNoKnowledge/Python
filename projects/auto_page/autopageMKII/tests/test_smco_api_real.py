"""
Integration test - ทดสอบ API จริงด้วย cookies จาก browser
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
import json

# UAT URL
UAT_ORIGIN = "http://192.168.0.142:9099"

def test_smco_api_with_real_cookies():
    print("=" * 60)
    print("API TEST - Real cookies from browser")
    print("=" * 60)

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

    # Get cookies from browser
    cookies = driver.get_cookies()
    cookie_dict = {c['name']: c['value'] for c in cookies}
    print(f"Cookies: {list(cookie_dict.keys())}")

    # Test 1: Get product info
    print("\n[Test 1] Get product info (getProductMasterInfoPOSV3)...")
    try:
        url = f"{UAT_ORIGIN}/smartcore/smartpos/pointofsales/posmainv3/getProductMasterInfoPOSV3.htm"
        payload = {
            'activeFlag': 'true',
            'requestText': 'PR2',  # Search for PR2 products
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
        print(f"     Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                print(f"     Found {len(data['data'])} products")
                for i, product in enumerate(data['data'][:3]):
                    print(f"     - {product.get('sku', 'N/A')}: {product.get('name', 'N/A')[:30]}")
            else:
                print(f"     Response: {str(data)[:100]}")
            print(f"     [PASS]")
        else:
            print(f"     [FAIL] Status {response.status_code}")
    except Exception as e:
        print(f"     [FAIL] {e}")

    # Test 2: Get serial list
    print("\n[Test 2] Get serial list (getSerialInfoList)...")
    try:
        url = f"{UAT_ORIGIN}/smartcore/inventory/stock/v2/getSerialInfoList.htm"
        search_value = json.dumps({
            'byId': '100',
            'byMasterId': 180,
            'byParentId': 441,
        }, separators=(',', ':'))

        payload = {
            'draw': '2',
            'order[0][column]': '0',
            'order[0][dir]': 'asc',
            'start': '0',
            'length': '10',
            'search[value]': search_value,
            'search[regex]': 'false',
        }

        response = requests.post(url, data=payload, cookies=cookie_dict, headers=headers, verify=False)
        print(f"     Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                print(f"     Found {len(data['data'])} serial records")
                for i, serial in enumerate(data['data'][:3]):
                    print(f"     - SN: {serial.get('serialNo', 'N/A')}")
            print(f"     [PASS]")
        else:
            print(f"     [FAIL] Status {response.status_code}")
    except Exception as e:
        print(f"     [FAIL] {e}")

    # Test 3: Get customer search
    print("\n[Test 3] Get customer search (getCustomerSearchPOS)...")
    try:
        url = f"{UAT_ORIGIN}/smartcore/uilts/oper/pos/getCustomerSearchPOS/selectoption.htm"
        payload = {
            'requestText': 'test',
            'target': 'N',
        }

        response = requests.post(url, data=payload, cookies=cookie_dict, headers=headers, verify=False)
        print(f"     Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                print(f"     Found {len(data['data'])} customers")
            print(f"     [PASS]")
        else:
            print(f"     [FAIL] Status {response.status_code}")
    except Exception as e:
        print(f"     [FAIL] {e}")

    # Summary
    print("\n" + "=" * 60)
    print("API TEST SUMMARY")
    print("=" * 60)
    print(f"Origin: {UAT_ORIGIN}")
    print(f"Cookies used: {len(cookie_dict)}")
    print("Status: API tests completed")
    print("=" * 60)

if __name__ == "__main__":
    test_smco_api_with_real_cookies()
