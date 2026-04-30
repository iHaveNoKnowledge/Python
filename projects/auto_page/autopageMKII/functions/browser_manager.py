import time
import traceback
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    InvalidSessionIdException
)
from webdriver_manager.chrome import ChromeDriverManager
from functions.network_response_utils import NetworkResponseCapture

class BrowserManager:
    def __init__(self, app, bot_instance, logger_instance=logger, max_memory_mb=70):
        self.app = app
        self.bot = bot_instance
        self.logger = logger_instance
        self.max_memory_mb = max_memory_mb
        
        # State tracking
        self.operation_count = 0
        self.memory_check_interval = 10
        self.is_memory_checking = False
        self.merged_dict = {}
        
        # Setup WebDriver
        self.driver = self.setup_chrome()
        self.driver.execute_cdp_cmd("Network.enable", {})
        
        # Setup helpers
        self.wait50 = WebDriverWait(self.driver, 50)
        self.wait5 = WebDriverWait(self.driver, 5)
        self.network_capture = NetworkResponseCapture(self.driver)

    def setup_chrome(self):
        opt = Options()
        opt.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        opt.add_experimental_option("debuggerAddress", "localhost:8989")
        opt.add_argument("--disable-popup-blocking")

        try:
            print("Connecting to existing Chrome at localhost:8989...")
            driver = webdriver.Chrome(options=opt)
            print("Driver connected successfully!")
            return driver

        except Exception as e:
            print(f"Direct connection failed: {e}")
            print("Attempting to fix driver version with WebDriverManager...")

            try:
                new_path = ChromeDriverManager().install()
                driver = webdriver.Chrome(
                    service=Service(new_path),
                    options=opt
                )
                return driver
            except Exception as final_err:
                print(f"Critical Error: {final_err}")
                raise

    def is_driver_alive(self):
        """ตรวจสอบว่า WebDriver ยังทำงานอยู่หรือไม่"""
        try:
            _ = self.driver.current_url
            return True
        except Exception as e:
            print(f"Driver is not alive: {type(e).__name__}: {e}")
            self.logger.error(f"Driver connection lost: {type(e).__name__}: {e}")
            return False

    def reconnect_driver(self):
        """
        Reconnect WebDriver หลังจาก connection หาย (เช่น หลัง sleep)
        Chrome ยังเปิดอยู่ แต่ ChromeDriver process ตายไป
        """
        try:
            print("🔄 Attempting to reconnect WebDriver...")
            self.logger.info("Attempting WebDriver reconnection...")
            self.app.update_log("🔄 Reconnecting to browser...")

            # สร้าง driver ใหม่เชื่อมต่อ Chrome ที่ยังเปิดอยู่
            self.driver = self.setup_chrome()
            self.driver.execute_cdp_cmd("Network.enable", {})

            # อัปเดต WebDriverWait
            self.wait50 = WebDriverWait(self.driver, 50)
            self.wait5 = WebDriverWait(self.driver, 5)

            # อัปเดต AutoAddProduct ถ้ามี
            if hasattr(self.bot, 'AutoAddProduct') and self.bot.AutoAddProduct:
                self.bot.AutoAddProduct.driver = self.driver
                self.bot.AutoAddProduct.wait = self.wait50

            # อัปเดต NetworkResponseCapture
            self.network_capture = NetworkResponseCapture(self.driver)

            # อัปเดต tabs
            self.get_tabs()

            print("✅ WebDriver reconnected successfully!")
            self.logger.info("WebDriver reconnected successfully")
            self.app.update_log("✅ Browser reconnected!")
            return True
        except Exception as e:
            print(f"❌ Failed to reconnect WebDriver: {e}")
            self.logger.error(f"WebDriver reconnection failed: {e}")
            self.app.update_log(f"❌ Cannot reconnect: {e}")
            return False

    def retry_on_stale_element(self, func, max_retries=5, delay=0.5, *args, **kwargs):
        """
        Retry wrapper สำหรับ operations ที่อาจเจอ NoSuchElementException หรือ StaleElementReferenceException
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (NoSuchElementException, StaleElementReferenceException, TimeoutException, InvalidSessionIdException) as e:
                last_exception = e
                error_msg = str(e)
                if "NewConnectionError" in error_msg or "MaxRetryError" in error_msg or "ConnectionRefusedError" in error_msg or "invalid session id" in error_msg.lower() or isinstance(e, InvalidSessionIdException):
                    print(f"Driver connection lost during retry: {type(e).__name__}")
                    self.logger.error(f"Driver connection lost during retry: {e}")
                    raise ConnectionError(f"WebDriver connection lost: {e}") from e
                if attempt < max_retries - 1:
                    print(f"Retry attempt {attempt + 1}/{max_retries} due to: {type(e).__name__}")
                    time.sleep(delay)
                    continue
                else:
                    print(f"Max retries ({max_retries}) reached. Giving up.")
                    raise last_exception

    def get_tabs(self):
        if self.bot.parent.winfo_exists():
            print("รายงานจำนวนtabs")
            title_list = []
            value_list = []

            # * check ว่า self.driver เดิมยังทำงานได้ไหม
            try:
                # * เช็คก่อนว่า driver ใช้ได้ไหม หรือการเชื่อมต่อ session หลุดไหม
                self.driver.window_handles
                print("driver is still running")
            except Exception as e:
                # * driver หลุดก็ออก seesion เก่า
                print(f"Driver connection lost in get_tabs ({e}). Attempting to reconnect...")
                try:
                    print("Quit old driver, not sure if this process is auto or not")
                    self.driver.quit()
                except:
                    print("No need to quit old driver, no driver found")
                    pass

                try:
                    success = self.reconnect_driver()
                    if not success:
                        print("❌ Failed to create new driver session. Please check ChromeDriver version.")
                        self.app.update_log("❌ ChromeDriver Error: Please update C:\\bin\\chromedriver.exe to match your Chrome version.")
                        return
                except Exception as reconnect_err:
                    print(f"❌ Error during reconnect in get_tabs: {reconnect_err}")
                    self.app.update_log(f"❌ ChromeDriver Error: {reconnect_err}")
                    return

            for idx, handle in enumerate(self.driver.window_handles):
                try:
                    self.driver.switch_to.window(handle)
                    print("self.driver.title: ", self.driver.title)
                    title_list.append(self.driver.title)
                    value_list.append(self.driver.current_window_handle)
                except Exception as e:
                    print(f"Error accessing tab index {idx} (handle: {handle}): {e}")
                    continue

            unique_titles = []
            counter = {}
            for item in title_list:
                if item in counter:
                    counter[item] += 1
                    print("counter[item] คือไร: ", counter[item])
                    unique_titles.append(f"{item}{counter[item]-1}")
                else:
                    counter[item] = 1
                    unique_titles.append(item)

            self.merged_dict = dict(zip(unique_titles, value_list))
            print("มี tabs ไรบ้าง", self.merged_dict)

    # -------------------------------------------------------------
    # Memory Management Methods
    # -------------------------------------------------------------

    def get_current_tab_memory_usage(self):
        """ตรวจสอบการใช้หน่วยความจำ ของ tab ปัจจุบัน"""
        try:
            memory_info = self.driver.execute_script(
                "return {'usedJSHeapSize': performance.memory.usedJSHeapSize, "
                "'totalJSHeapSize': performance.memory.totalJSHeapSize}"
            )
            used_mb = memory_info['usedJSHeapSize'] / 1024 / 1024
            total_mb = memory_info['totalJSHeapSize'] / 1024 / 1024

            print(f"Memory: {used_mb:.1f}MB used / {total_mb:.1f}MB allocated (Threshold: {self.max_memory_mb}MB)")
            print(f"  Current URL: {self.driver.current_url[:60]}...")

            if used_mb > self.max_memory_mb:
                print(f"  ⚠️  MEMORY EXCEEDED! {used_mb:.1f}MB > {self.max_memory_mb}MB")

            return used_mb
        except Exception as e:
            print(f"Error checking memory usage: {e}")
            return 0

    def close_and_reopen_tab_if_memory_high(self, tab_name=None):
        """ปิดแท็บเก่าแล้วเปิดใหม่ ถ้า memory เกิน limit (Optimized for RAM clearing)"""
        try:
            try:
                current_url = self.driver.current_url
            except Exception:
                self.logger.warning("ไม่สามารถอ่าน current_url ได้ อาจไม่มีแท็บเปิดอยู่")
                return False

            if "devtools://" in current_url or "chrome://" in current_url or "Tab Search" in (tab_name or "") or "DevTools" in (tab_name or ""):
                print(f"Skipping internal page: {tab_name or current_url}")
                return False

            current_handle = self.driver.current_window_handle
            memory_usage = self.get_current_tab_memory_usage()

            self.logger.info(f"{getattr(self.bot, 'cus_order', '')}: Checking memory for '{tab_name or current_url}' ({memory_usage:.1f}MB)")

            if memory_usage > self.max_memory_mb:
                print(f"Memory usage ({memory_usage:.1f}MB) exceeds limit ({self.max_memory_mb}MB)")
                print(f"Reopening tab: {tab_name or current_url}")

                try:
                    scroll_position = self.driver.execute_script("return document.scrollingElement.scrollTop;")
                except Exception:
                    scroll_position = 0

                old_handles = set(self.driver.window_handles)
                safe_opener_handle = current_handle
                if len(old_handles) > 1:
                    for h in old_handles:
                        if h != current_handle:
                            safe_opener_handle = h
                            break

                self.driver.switch_to.window(safe_opener_handle)

                try:
                    self.driver.execute_script("window.open(arguments[0], '_blank', 'noopener');", current_url)
                    self.logger.info(f"Executed window.open for: {current_url}")
                except Exception as e:
                    self.logger.warning(f"window.open failed: {e}, trying alternative method")

                time.sleep(0.5)

                new_handles = set(self.driver.window_handles) - old_handles
                if len(new_handles) == 0:
                    self.logger.warning("No new tab detected, trying driver.switch_to.new_window")
                    try:
                        self.driver.switch_to.new_window('tab')
                        time.sleep(0.5)
                        self.driver.get(current_url)
                        new_handles = set(self.driver.window_handles) - old_handles
                    except Exception as e:
                        self.logger.error(f"Alternative tab opening method also failed: {e}")
                        raise

                WebDriverWait(self.driver, 10).until(lambda d: len(set(d.window_handles) - old_handles) > 0)
                new_handle = list(set(self.driver.window_handles) - old_handles)[0]
                self.logger.info(f"{getattr(self.bot, 'cus_order', '')}: Opened new tab for '{tab_name or current_url}'")

                self.driver.switch_to.window(current_handle)
                try:
                    self.driver.get("about:blank")
                    time.sleep(0.5)
                except Exception as e:
                    self.logger.warning(f"Error navigating to about:blank: {e}")

                try:
                    self.driver.close()
                    self.logger.info(f"{getattr(self.bot, 'cus_order', '')}: Closed old tab for '{tab_name or current_url}'")
                except Exception as e:
                    self.logger.warning(f"Error closing old tab: {e}")

                self.driver.switch_to.window(new_handle)

                WebDriverWait(self.driver, 20).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                try:
                    self.driver.execute_script(f"document.scrollingElement.scrollTop = {scroll_position};")
                except Exception:
                    pass

                self.get_tabs()

                updated = False
                for key, value in list(self.merged_dict.items()):
                    if value == current_handle:
                        self.merged_dict[key] = new_handle
                        updated = True
                        print(f"Updated {key} handle → new tab")
                if not updated:
                    print("⚠️ No merged_dict entry matched old handle")

                print("✅ Tab closed and reopened successfully (memory cleaned)")
                return True

            return False

        except Exception as e:
            print(f"❌ Error closing/reopening tab: {e}")
            print(traceback.format_exc())
            self.logger.error(f"close_and_reopen_tab_if_memory_high failed: {e}")
            return False

    def refresh_tab_if_memory_high(self, tab_name=None):
        """Refresh tab ถ้าใช้ memory เกินกำหนด (backup method)"""
        return self.close_and_reopen_tab_if_memory_high(tab_name)

    def force_garbage_collection(self):
        """บังคับให้ browser ทำ garbage collection"""
        try:
            self.driver.execute_script(
                "if (window.gc) { window.gc(); } "
                "else if (window.CollectGarbage) { window.CollectGarbage(); }"
            )
            self.driver.execute_script(
                "if (typeof window.caches !== 'undefined') {"
                "  caches.keys().then(names => {"
                "    names.forEach(name => caches.delete(name));"
                "  });"
                "}"
            )
            print("Forced garbage collection completed")
        except Exception as e:
            print(f"Error during garbage collection: {e}")

    def pre_operation_memory_cleanup(self, operation_name="operation"):
        """ตรวจสอบและจัดการ memory ก่อนเริ่ม operation สำคัญ (เฉพาะ SMCO tabs)"""
        print(f"\n=== Pre-operation Memory Cleanup: {operation_name} ===")
        self.is_memory_checking = True
        try:
            current_handle = self.driver.current_window_handle
            all_handles = self.driver.window_handles

            print(f"Checking memory for {len(all_handles)} tabs before {operation_name}")
            tabs_cleaned = 0
            smco_tabs_found = 0

            for i, handle in enumerate(all_handles):
                try:
                    self.driver.switch_to.window(handle)
                    tab_title = self.driver.title
                    print(f"handle No. {i+1}: {tab_title}")
                    if "SMCO :: " in tab_title:
                        smco_tabs_found += 1
                        memory_usage = self.get_current_tab_memory_usage()
                        print(f"SMCO Tab {smco_tabs_found}: {tab_title[:50]} - {memory_usage:.1f}MB")

                        if memory_usage > self.max_memory_mb:
                            print(f"  → Cleaning SMCO tab (memory too high)")
                            self.logger.info(f"{getattr(self.bot, 'cus_order', '')}: Pre-operation cleanup: Closing and reopening tab '{tab_title}' due to high memory ({memory_usage:.1f}MB)")
                            if self.close_and_reopen_tab_if_memory_high(tab_title):
                                tabs_cleaned += 1
                        else:
                            print(f"  → Memory OK")
                    else:
                        print(f"Other Tab {i+1}: {tab_title[:30]} - Skipped (not SMCO)")

                except Exception as e:
                    print(f"  → Error checking tab {i+1}: {e}")

            try:
                self.driver.switch_to.window(current_handle)
            except:
                for handle in self.driver.window_handles:
                    try:
                        self.driver.switch_to.window(handle)
                        if "SMCO :: " in self.driver.title:
                            print("Switched to first available SMCO tab")
                            break
                    except:
                        continue

            self.force_garbage_collection()
            print(f"Memory cleanup completed: {tabs_cleaned}/{smco_tabs_found} SMCO tabs cleaned")
            self.is_memory_checking = False

        except Exception as e:
            print(f"Error in pre-operation memory cleanup: {e}")
            self.is_memory_checking = False

    def manage_browser_memory(self, operation_name="operation"):
        """หลัก method สำหรับจัดการ memory ของ browser (ใช้แค่สำหรับการนับ operation)"""
        self.operation_count += 1
        print(f"Operation count: {self.operation_count} ({operation_name})")

    def reset_all_tabs_memory(self):
        """Reset memory ของทุก tabs ที่เปิดอยู่"""
        try:
            current_handle = self.driver.current_window_handle
            all_handles = self.driver.window_handles

            print(f"Resetting memory for {len(all_handles)} tabs")
            for handle in all_handles:
                try:
                    self.driver.switch_to.window(handle)
                    tab_title = self.driver.title[:50]
                    self.refresh_tab_if_memory_high(tab_title)
                except Exception as e:
                    print(f"Error resetting tab {handle}: {e}")

            self.driver.switch_to.window(current_handle)
            self.force_garbage_collection()
            print("Memory reset completed for all tabs")

        except Exception as e:
            print(f"Error in reset_all_tabs_memory: {e}")
