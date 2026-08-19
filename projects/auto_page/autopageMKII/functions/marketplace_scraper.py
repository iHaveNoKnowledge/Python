import re
import time
import traceback
from dataclasses import dataclass
from typing import Any, Optional

from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@dataclass
class MarketplaceOrderResult:
    """Encapsulates the scraped result and validation state of a marketplace order."""
    order_no: str
    marketplace: str
    status: str = ""
    purchased_channel: Optional[str] = None
    is_forbid: bool = False
    is_skip: bool = False
    skip_reason: Optional[str] = None
    error_message: Optional[str] = None


class MarketplaceScraper:
    """
    Handles marketplace-specific scraping, searching, and order status verification
    (e.g., Shopee Seller Centre, Lazada Seller Center).
    """

    def __init__(self, bot: Any):
        self.bot = bot
        self.app = bot.app
        self.driver = bot.driver
        self.wait50 = bot.wait50

    def scrape_order(self, order_no: str, marketplace: str) -> MarketplaceOrderResult:
        """
        Main entry point for scraping and verifying an order on the specified marketplace.
        """
        marketplace = (marketplace or "").upper().strip()
        if marketplace == 'SHOPEE':
            return self._scrape_shopee(order_no)
        elif marketplace == 'LAZADA':
            return self._scrape_lazada(order_no)
        else:
            print(f"Cannot define marketplace: '{marketplace}'")
            return MarketplaceOrderResult(
                order_no=order_no,
                marketplace=marketplace,
                error_message=f"Unsupported marketplace: {marketplace}"
            )

    def _scrape_shopee(self, order_no: str) -> MarketplaceOrderResult:
        """
        Scrapes and verifies an order on Shopee Seller Centre.
        """
        result = MarketplaceOrderResult(order_no=order_no, marketplace='SHOPEE')

        # 1. Wait for memory check if active
        while getattr(self.bot, 'is_memory_checking', False):
            try:
                print("Wait for memory checking.....")
                time.sleep(0.35)
            except Exception:
                print("Memory checking done.")
                break

        # 2. Switch to Shopee Seller Centre tab
        self.driver.switch_to.window(self.bot.merged_dict['Seller Centre'])
        print("Switched to 'Seller Centre'")
        time.sleep(1)

        # 3. Read subaccount info / purchased channel
        try:
            shopee_sub_account_name_element = self.driver.find_element(
                By.CSS_SELECTOR, 'div.subaccount-info span.subaccount-name')
            result.purchased_channel = self.driver.execute_script(
                "return arguments[0].innerText;", shopee_sub_account_name_element)
            print(f"Shopee purchased_channel: {result.purchased_channel}")
        except Exception as e:
            print(f"Could not read Shopee subaccount name: {e}")

        cur_url = self.driver.current_url

        # 4. Navigate to "ทั้งหมด" (All Orders) tab if needed
        if cur_url != "https://seller.shopee.co.th/portal/sale/order":
            def click_tab():
                return self.driver.find_element(
                    By.CSS_SELECTOR, 'div.eds-tabs__nav div.eds-tabs__nav-warp div div div.tab-label').click()

            self.bot.retry_on_stale_element(click_tab)
        else:
            print("Already on Shopee all orders page")

        # 5. Enter order number into search input
        try:
            def find_search_element():
                return self.wait50.until(EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, 'div.eds-input__inner.eds-input__inner--normal input')
                ))

            search_elmt = self.bot.retry_on_stale_element(find_search_element)
            search_elmt.clear()
            search_elmt.send_keys(order_no)

            # Click search button
            search_btn = self.driver.find_element(
                By.CSS_SELECTOR,
                'div.order-search-buttons button.search-btn.eds-button.eds-button--primary.eds-button--normal.eds-button--outline'
            )
            self.driver.execute_script("arguments[0].click();", search_btn)
        except Exception:
            print("Cannot search Shopee order")
            tb_str = traceback.format_exc()
            if any(err_type in tb_str for err_type in ["NewConnectionError", "MaxRetryError", "ConnectionRefusedError"]):
                print("WebDriver connection lost during search")
                logger.error(f"Order: {order_no} - WebDriver connection lost during search")
                self.app.update_log("❌ Browser connection lost. Please restart the browser.")
                raise ConnectionError(f"WebDriver connection lost during operation_start: {tb_str}") from None
            raise ValueError(f"Shopee search order Error: {tb_str}")

        time.sleep(1)

        # 6. Wait for search result or empty indicator
        found_order = False
        search_timeout = 10.0
        start_time = time.time()
        while not self.bot.operation_thread.is_set():
            try:
                status_el = self.driver.find_elements(By.CLASS_NAME, 'status-wrapper')
                order_sn_el = self.driver.find_elements(By.XPATH, "//div/span[@class='order-sn']")

                if (status_el and status_el[0].is_displayed()) or (order_sn_el and order_sn_el[0].is_displayed()):
                    found_order = True
                    print("Found order in Shopee")
                    break
            except Exception as e:
                print(f"Error checking Shopee elements: {e}")

            try:
                page_text = self.driver.page_source.lower()
                empty_indicators = ["no data", "ไม่มีข้อมูล", "no orders", "no results"]
                empty_el = self.driver.find_elements(
                    By.CSS_SELECTOR, ".eds-empty, .empty-wrapper, .no-orders, .no-data")

                if (empty_el and any(el.is_displayed() for el in empty_el)) or any(ind in page_text for ind in empty_indicators):
                    print("Detected empty page in Shopee (order not found)")
                    break
            except Exception:
                pass

            if time.time() - start_time > search_timeout:
                print("Search timeout in Shopee")
                break
            time.sleep(0.5)

        if not found_order:
            error_msg = f"ไม่พบออเดอร์ {order_no} ในระบบ Shopee หรือค้นหาไม่สำเร็จ"
            self.app.update_log(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # 7. Extract status text
        status_text = ""
        try:
            status_text = self.driver.find_element(By.CLASS_NAME, 'status-wrapper').text
        except Exception:
            try:
                status_text = self.driver.find_element(
                    By.XPATH,
                    '/html/body/div[2]/div[2]/div[2]/div/div/div/div[2]/div[4]/div/div/div[2]/div[4]/div/div[2]/a/div[2]/div/div/div[3]/div/div[1]/span'
                ).text
            except Exception as e:
                print(f"Could not read Shopee status text: {e}")

        result.status = status_text.strip()
        self.app.cus_cur_status.set(result.status)

        # 8. Update GUI status indicator & Check forbidden states
        self.app.display_current_status.configure(text_color="#000000", fg_color="#8fd4ff")
        if result.status == "ส่งสินค้าแล้ว":
            self.app.display_current_status.configure(fg_color="#00ff11", text_color="#000000")
            if hasattr(self.app, 'POP_UP'):
                self.app.POP_UP.show("Caution!!", f"Order {order_no} มีสถานะ '{result.status}'", "alert")
            logger.info(f"Order: {order_no} has status: '{result.status}'")

        elif "ยกเลิก" in result.status:
            self.app.display_current_status.configure(fg_color="#ff2b2b", text_color="#FFF")
            result.is_forbid = True
            if hasattr(self.app, 'POP_UP'):
                self.app.POP_UP.show("Caution!!", f"Order {order_no} มีสถานะ '{result.status}'", "alert")
            logger.info(f"Order: {order_no} has status: '{result.status}'")

        self.bot.is_status_true = (self.app.order_status == result.status)
        if self.bot.is_status_true:
            print("Status in the file is reliable")
        else:
            print("Status in the file is unreliable, suggest downloading a new Export File")

        # 9. Handle Auto-Invoice Mode filtering
        if hasattr(self.app, 'is_auto_invoice_mode') and self.app.is_auto_invoice_mode.get():
            shopee_status = result.status
            if not shopee_status:
                raise ValueError("ไม่สามารถระบุสถานะออเดอร์ Shopee ได้ (ค่าสถานะเป็นค่าว่าง)")

            if shopee_status != "ที่ต้องจัดส่ง":
                if "ยกเลิก" in shopee_status:
                    is_failed = False
                elif "ยังไม่ชำระ" in shopee_status:
                    is_failed = True
                else:
                    is_failed = False

                if is_failed:
                    error_msg = f"ออเดอร์มีสถานะ '{shopee_status}' (ถือว่า Failed ตามเงื่อนไข)"
                    self.app.update_log(f"❌ {error_msg}")
                    raise ValueError(error_msg)
                else:
                    success_msg = f"ข้ามออเดอร์ (สถานะ: {shopee_status}) ถือว่า Complete ตามเงื่อนไข"
                    self.app.update_log(f"✅ {success_msg}")
                    if hasattr(self.app, 'accel_mode'):
                        if hasattr(self.app.accel_mode, 'deduct_accel_file_data'):
                            try:
                                self.app.accel_mode.deduct_accel_file_data(order_no, remove_order=True)
                            except Exception as xl_err:
                                logger.warning(f"ไม่สามารถ deduct order จาก Sheet1 ได้: {xl_err}")
                        if hasattr(self.app.accel_mode, 'record_completed_order'):
                            self.app.accel_mode.record_completed_order(order_no, status=f"ข้าม (สถานะ: {shopee_status})")

                    result.is_skip = True
                    result.skip_reason = f"ข้าม (สถานะ: {shopee_status})"
                    return result

        return result

    def _scrape_lazada(self, order_no: str) -> MarketplaceOrderResult:
        """
        Scrapes and verifies an order on Lazada Seller Center.
        """
        result = MarketplaceOrderResult(order_no=order_no, marketplace='LAZADA')

        # 1. Switch to Lazada Seller Center tab
        try:
            self.driver.switch_to.window(self.bot.merged_dict['การจัดการคำสั่งซื้อ - Lazada Seller Center'])
        except Exception:
            self.driver.switch_to.window(self.bot.merged_dict['การจัดการคำสั่งซื้อ - Seller Center'])

        cur_url = self.driver.current_url

        # 2. Navigate to "ทั้งหมด" (All Orders) tab if needed
        if "status=all" not in cur_url:
            try:
                self.driver.find_element(
                    By.XPATH,
                    '/html/body/div/section/div[2]/div/div[1]/div/div/div[2]/div/div[1]/div/div/div/ul/li[1]/div'
                ).click()
                time.sleep(0.75)
                self.wait50.until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        '/html/body/div/section/div[2]/div/div[1]/div/div/div[3]/div/div[3]/div[1]/div[1]/div[2]/div[2]/span[1]/span[2]/span/a'
                    ))
                )
            except Exception as e:
                print(f"Could not switch to Lazada all orders tab: {e}")

        # 3. Enter order number into search input
        laz_order_input_path = "//span[@class='next-select-trigger-search']/input[@role='combobox' and @name='orderNumbers']"
        search_elmt = self.wait50.until(EC.visibility_of_element_located((By.XPATH, laz_order_input_path)))
        self.driver.find_element(By.XPATH, laz_order_input_path).clear()

        # Clear existing search tag chips if any
        try:
            laz_close_btn_path = "//div[@class='next-tag next-tag-closable next-tag-small next-tag-level-primary next-tag-closable']/span[@class='next-tag-close-btn']"
            close_btn = self.driver.find_element(By.XPATH, laz_close_btn_path)

            input_count = None
            try:
                laz_order_input_amount_path = '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/div[2]/span/span'
                input_count = self.driver.find_element(By.XPATH, laz_order_input_amount_path)
            except Exception:
                pass

            if input_count and input_count.is_displayed() and close_btn.is_displayed():
                clicks = re.sub(r'\W', "", input_count.text)
                for click in range(int(clicks) if clicks.isdigit() else 1):
                    close_btn = self.driver.find_element(
                        By.XPATH,
                        '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/span/span[1]/span[1]/div[1]/span[2]'
                    )
                    close_btn.click()
            else:
                close_btn.click()
        except Exception:
            pass

        search_elmt.clear()
        search_elmt.send_keys(order_no)

        # 4. Click Search button
        search_btn = self.driver.find_element(
            By.XPATH,
            '/html/body/div/section/div[2]/div/div[1]/div/div/form/div[2]/div/div/div/div[1]/div[3]/div[1]/div/div/div[1]'
        )
        search_btn.click()
        time.sleep(0.75)

        # 5. Wait for result or empty indicator
        found_order = False
        search_timeout = 10.0
        start_time = time.time()
        status_btn_xpath = '/html/body/div/section/div[2]/div/div[1]/div/div/div[3]/div/div[3]/div/div[2]/div/div/div[5]/div[1]/button'

        while not self.bot.operation_thread.is_set():
            try:
                status_el = self.driver.find_elements(By.XPATH, status_btn_xpath)
                if status_el and status_el[0].is_displayed():
                    found_order = True
                    print("Found order in Lazada")
                    break
            except Exception as e:
                print(f"Error checking Lazada elements: {e}")

            try:
                page_text = self.driver.page_source.lower()
                empty_el = self.driver.find_elements(By.CSS_SELECTOR, ".next-table-empty, .empty, .no-data")
                if (empty_el and any(el.is_displayed() for el in empty_el)) or "ไม่มีข้อมูล" in page_text or "no data" in page_text:
                    print("Detected empty page in Lazada (order not found)")
                    break
            except Exception:
                pass

            if time.time() - start_time > search_timeout:
                print("Search timeout in Lazada")
                break
            time.sleep(0.5)

        if not found_order:
            error_msg = f"ไม่พบออเดอร์ {order_no} ในระบบ Lazada หรือค้นหาไม่สำเร็จ"
            self.app.update_log(f"❌ {error_msg}")
            raise ValueError(error_msg)

        # 6. Extract status text
        try:
            status_text = self.driver.find_element(By.XPATH, status_btn_xpath + '/span').text
            result.status = status_text.strip()
        except Exception as e:
            print(f"Could not read Lazada status text: {e}")

        self.app.cus_cur_status.set(result.status)

        # 7. Update GUI status indicator
        print("Lazada realtime_status_text:", result.status)
        self.app.display_current_status.configure(text_color="#000000", fg_color="#8fd4ff")
        if "พิมพ์ใบแจ้งหนี้" in result.status or "ยกเลิก" in result.status:
            self.app.display_current_status.configure(fg_color="#ff2b2b", text_color="#FFF")
            result.is_forbid = True
        elif result.status == "สถานะการจัดส่ง":
            self.app.display_current_status.configure(fg_color="#00ff11", text_color="#000000")

        return result
