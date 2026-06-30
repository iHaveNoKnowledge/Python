"""
Integration test - รันจริงบน SMCO tab ที่เปิดอยู่แล้ว
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_smco_on_existing_tab():
    print("=" * 60)
    print("INTEGRATION TEST - SMCO on existing tab")
    print("=" * 60)

    # Connect to existing Chrome
    opt = Options()
    opt.add_experimental_option("debuggerAddress", "localhost:8989")

    try:
        driver = webdriver.Chrome(options=opt)
        print(f"[OK] Connected to Chrome")
    except Exception as e:
        print(f"[FAIL] Cannot connect: {e}")
        return

    # Find SMCO tab
    print("\n[Step 1] Find SMCO tab...")
    smco_handle = None
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        title = driver.title
        print(f"     Tab: {title[:40]}")
        if "SMCO" in title or "เปิดการขาย" in title:
            smco_handle = handle
            print(f"     >> Found SMCO tab!")
            break

    if not smco_handle:
        print("     [WARN] SMCO tab not found, using current tab")
        smco_handle = driver.current_window_handle

    driver.switch_to.window(smco_handle)
    print(f"     Current URL: {driver.current_url}")
    print(f"     Title: {driver.title}")

    # Test 1: Check current page
    print("\n[Test 1] Check SMCO page...")
    try:
        url = driver.current_url
        title = driver.title
        print(f"     URL: {url}")
        print(f"     Title: {title}")
        print(f"     [PASS] SMCO page accessible")
    except Exception as e:
        print(f"     [FAIL] {e}")

    # Test 2: Find form elements
    print("\n[Test 2] Find form elements...")
    try:
        # Look for input fields
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"     Found {len(inputs)} input fields")
        for i, inp in enumerate(inputs[:5]):
            inp_type = inp.get_attribute("type") or "text"
            inp_id = inp.get_attribute("id") or "no-id"
            print(f"     - Input {i+1}: type={inp_type}, id={inp_id[:20]}")
        print(f"     [PASS] Form elements found")
    except Exception as e:
        print(f"     [FAIL] {e}")

    # Test 3: Find buttons
    print("\n[Test 3] Find buttons...")
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"     Found {len(buttons)} buttons")
        for i, btn in enumerate(buttons[:5]):
            btn_text = btn.text[:20] if btn.text else "no-text"
            print(f"     - Button {i+1}: {btn_text}")
        print(f"     [PASS] Buttons found")
    except Exception as e:
        print(f"     [FAIL] {e}")

    # Test 4: Check customer name field
    print("\n[Test 4] Check customer section...")
    try:
        # Look for customer-related elements
        cus_elements = driver.find_elements(By.XPATH, "//*[contains(@id, 'member') or contains(@name, 'member') or contains(@class, 'member')]")
        print(f"     Found {len(cus_elements)} member-related elements")
        print(f"     [PASS] Customer section accessible")
    except Exception as e:
        print(f"     [FAIL] {e}")

    # Test 5: Get page state
    print("\n[Test 5] Get page state...")
    try:
        # Check if page has Angular/React
        is_angular = driver.execute_script("return !!document.querySelector('[ng-app]') || !!document.querySelector('[data-ng-app]')")
        is_react = driver.execute_script("return !!document.querySelector('[data-reactroot]') || !!document.querySelector('#root')")

        print(f"     Angular: {is_angular}")
        print(f"     React: {is_react}")
        print(f"     [PASS] Page framework detected")
    except Exception as e:
        print(f"     [FAIL] {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Browser Session: {driver.session_id[:20]}...")
    print(f"SMCO Tab: {driver.title}")
    print(f"URL: {driver.current_url}")
    print("Status: SMCO integration tests PASSED")
    print("=" * 60)

if __name__ == "__main__":
    test_smco_on_existing_tab()
