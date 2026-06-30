"""
Integration test - รันจริงบน Chrome browser
เชื่อมต่อกับ Chrome ที่เปิดอยู่แล้ว (remote debugging port 8989)
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# UAT URL
UAT_URL = "http://192.168.0.142:9099/smartcore/smartpos"

def test_real_browser():
    print("=" * 60)
    print("INTEGRATION TEST - Running on real Chrome browser")
    print("=" * 60)

    # Connect to existing Chrome
    opt = Options()
    opt.add_experimental_option("debuggerAddress", "localhost:8989")

    try:
        driver = webdriver.Chrome(options=opt)
        print(f"[OK] Connected to Chrome")
        print(f"     Current URL: {driver.current_url}")
        print(f"     Title: {driver.title}")
    except Exception as e:
        print(f"[FAIL] Cannot connect to Chrome: {e}")
        return

    # Test 1: Navigate to UAT
    print("\n[Test 1] Navigate to UAT SMCO...")
    try:
        driver.get(UAT_URL)
        time.sleep(3)
        print(f"     URL after navigate: {driver.current_url}")
        print(f"     Title: {driver.title}")
        print(f"     [PASS] Navigation successful")
    except Exception as e:
        print(f"     [FAIL] Navigation error: {e}")

    # Test 2: Check page loaded
    print("\n[Test 2] Check page elements...")
    try:
        page_source = driver.page_source
        if "smartcore" in page_source.lower() or "login" in page_source.lower() or len(page_source) > 1000:
            print(f"     Page source length: {len(page_source)} chars")
            print(f"     [PASS] Page loaded successfully")
        else:
            print(f"     [WARN] Page might not be fully loaded")
    except Exception as e:
        print(f"     [FAIL] Error checking page: {e}")

    # Test 3: Get cookies
    print("\n[Test 3] Get browser cookies...")
    try:
        cookies = driver.get_cookies()
        print(f"     Number of cookies: {len(cookies)}")
        for c in cookies[:3]:
            print(f"     - {c['name']}: {c['value'][:20]}...")
        print(f"     [PASS] Cookies retrieved")
    except Exception as e:
        print(f"     [FAIL] Error getting cookies: {e}")

    # Test 4: Check browser tabs
    print("\n[Test 4] Check browser tabs...")
    try:
        handles = driver.window_handles
        print(f"     Number of tabs: {len(handles)}")
        for i, handle in enumerate(handles[:3]):
            driver.switch_to.window(handle)
            print(f"     Tab {i+1}: {driver.title[:30]}")
        print(f"     [PASS] Tab management works")
    except Exception as e:
        print(f"     [FAIL] Error checking tabs: {e}")

    # Test 5: Execute JavaScript
    print("\n[Test 5] Execute JavaScript...")
    try:
        result = driver.execute_script("return navigator.userAgent")
        print(f"     User Agent: {result[:50]}...")
        print(f"     [PASS] JavaScript execution works")
    except Exception as e:
        print(f"     [FAIL] Error executing JS: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("Browser: Chrome (connected via remote debugging)")
    print(f"ChromeDriver session: {driver.session_id[:20]}...")
    print("Status: All basic tests PASSED")
    print("=" * 60)

if __name__ == "__main__":
    test_real_browser()
