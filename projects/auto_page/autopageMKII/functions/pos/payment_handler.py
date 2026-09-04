import gc
import re
import time
from typing import Any, Optional

from loguru import logger
from selenium.common.exceptions import InvalidSessionIdException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class POSPaymentHandler:
    """
    Handles POS Final Payment page workflows:
    - Waiting and detecting the Payment summary page
    - Filling Remark (Order No) & applying Tracking Number
    - Selecting Payment Channel (Shopee / LAZ / Transfer)
    - Calculating and entering Final Price into Cash input
    - Entering PO No. & Customer Name
    - Checking wrimagecard balance and clicking Green Button (#btnPayment) with retries
    - Handling and validating the Final Success / Error Popup (swal2) and triggering receipt print & Excel updates
    """

    def __init__(self, bot: Any):
        self.bot = bot
        self.app = bot.app
        self.driver = bot.driver
        self.wait50 = bot.wait50
        self.last_page: Optional[WebElement] = None

    @property
    def cus_order(self) -> str:
        return self.app.cus_order.get()

    def process_final_payment(self) -> bool:
        """
        Executes the final payment page loop and billing submission.
        Returns True if payment and billing completion succeeded, False otherwise.
        """
        self.bot.autofinal = True
        while self.bot.autofinal and not self.bot.operation_thread.is_set():
            self.app.is_bot_browser_busy.set(False)
            print("Enter final loop")
            print("Waiting for element to appear")

            while self.bot.parent.winfo_exists() and not self.bot.operation_thread.is_set():
                time.sleep(0.55)
                saler_name_input_element = None
                title_attribute = ""
                is_final_page_displayed = False

                while not self.bot.operation_thread.is_set():
                    try:
                        saler_name_input_element = self.driver.find_element(
                            By.CSS_SELECTOR, '#select2-salePersonSearch-container'
                        )
                        title_attribute = saler_name_input_element.get_attribute("title") or ""

                        # Check if final page is displayed
                        some_last_page_text_element_xpath = "//*[contains(text(),' Payment: ') or contains(text(), 'ชำระเงิน:') or contains(text(), 'CN Reason')]"
                        is_final_page_displayed = self.driver.find_element(
                            By.XPATH, some_last_page_text_element_xpath).is_displayed()
                        break
                    except InvalidSessionIdException:
                        print("Invalid session ID. Attempting to relaunch driver.")
                        self.app.update_log("❌ Browser session lost. Attempting to relaunch the browser...")
                        logger.error(f"Order: {self.cus_order} - Browser session lost during final page wait loop.")
                        self.bot.reconnect_driver()
                        try:
                            self.driver.switch_to.window(self.bot.merged_dict['SMCO :: เปิดการขาย'])
                        except Exception as sw_err:
                            print(f"Cannot switch to SMCO window after reconnect: {sw_err}")
                        time.sleep(1)
                        continue

                    except Exception as err:
                        err_str = str(err).lower()
                        if "target window already closed" in err_str or "no such window" in err_str:
                            print("Browser window is closed. Exiting wait loop.")
                            self.bot.autofinal = False
                            break
                        else:
                            print(f"Cannot see elements from final page, waiting... Error details: {type(err).__name__}")
                            time.sleep(1)
                            continue

                if not self.bot.autofinal:
                    break

                # Extract employee name from title
                matched_obj = re.search(r"^[A-Z0-9?]+", title_attribute)
                emp_name_from_element = matched_obj.group() if matched_obj else ""

                if emp_name_from_element == "" and not is_final_page_displayed:
                    print("Emp name disappeared")
                    break
                elif saler_name_input_element and (
                    "Select " not in title_attribute or "กรุณาเลือก" not in title_attribute
                ) and not is_final_page_displayed:
                    continue
                elif saler_name_input_element and is_final_page_displayed:
                    self.app.is_bot_browser_busy.set(True)
                    time.sleep(0.55)
                    print("Page Payment")

                    # Check or reload last_page element
                    reload = False
                    if not hasattr(self, "last_page") or not isinstance(self.last_page, WebElement):
                        reload = True
                    else:
                        try:
                            _ = self.last_page.text
                        except Exception as err:
                            print("Old last_page element stale, reloading:", err)
                            reload = True

                    if reload:
                        print("Reloading last_page element...")
                        while not self.bot.operation_thread.is_set():
                            try:
                                self.last_page = self.driver.find_element(
                                    By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[1]/span[1]'
                                )
                                print("Reloaded last_page successfully")
                                break
                            except Exception as e:
                                print("Cannot reload last_page element:", e)
                                time.sleep(0.5)

                    if self.last_page and self.last_page.text in ["Payment:", "ชำระเงิน:"]:
                        try:
                            # 1. Collect and apply Tracking Number & Order No to Remark Modal
                            time.sleep(0.75)
                            remark_text = self.cus_order
                            if getattr(self.app, 'tracking_from_data_complete', False):
                                print(f"Tracking จาก data ครบ: {self.app.tracking_from_data} ข้าม collect_tracking")
                                self.app.update_log(
                                    f"✅ เลข tracking มีใน data ครบ ({len(self.app.tracking_from_data)} รายการ) ไม่ต้องย้อนไป shopee"
                                )
                                self.bot.tracking_manager.trackings = list(self.app.tracking_from_data)
                            else:
                                expected_tracking_count = (
                                    len(self.app.filter_data)
                                    if hasattr(self.app, 'filter_data') and self.app.filter_data is not None and not getattr(self.app.filter_data, 'empty', True)
                                    else None
                                )
                                try:
                                    self.bot.tracking_manager.collect_tracking(remark_text, expected_count=expected_tracking_count)
                                except Exception as track_err:
                                    print(f"Tracking collection failed: {track_err}, returning SMCO to first page...")
                                    self.app.update_log(f"⚠️ {track_err} -> กำลังกดย้อนกลับไปหน้าแรกของ SMCO...")
                                    self.return_to_first_page()
                                    raise track_err

                            # กรอก Order ไปที่ cnRemark และ modal (ref1RemarkTemp), Tracking ไปที่ ref2/ref3RemarkTemp
                            self.bot.tracking_manager.apply_tracking_to_final_page(order_no=self.cus_order)

                            # 3. Select Payment Type and Calculate final_price
                            time.sleep(0.75)
                            final_price = 0
                            if self.app.marketplace_target.get() == 'SHOPEE':
                                final_price = (self.app.sum_price + self.app.cus_ship_cost.get()) - self.app.cus_seller_voucher.get()
                                try:
                                    channel_key = f"{self.bot.operation_states.get('purchased_channel')}"
                                    channel = self.bot.channel_options.get(channel_key, "SHOPEE")
                                    print("Payment channel:", channel)
                                    payment_type_btn_element = self.driver.find_element(
                                        By.XPATH, f"//a//label[text()='{channel}']")
                                    self.driver.execute_script("arguments[0].click();", payment_type_btn_element)
                                except Exception:
                                    payment_type_btn_element = self.driver.find_element(
                                        By.XPATH, "//a[contains(., 'Transfer') and @ng-click='addPaymentType(btnsubList)']")
                                    self.driver.execute_script("arguments[0].click();", payment_type_btn_element)

                            elif self.app.marketplace_target.get() == 'LAZADA':
                                final_price = self.app.sum_price - self.app.cus_seller_voucher.get()
                                payment_type_btn_element = self.driver.find_element(By.XPATH, "//a[contains(., 'LAZ')]")
                                self.driver.execute_script("arguments[0].click();", payment_type_btn_element)

                            self.app.final_price = final_price

                            # 4. Fill PO No.
                            try:
                                po_no_input_element = self.driver.find_element(By.XPATH, "//input[@id='textbox81037000102']")
                                self.bot.js_input_value(po_no_input_element, self.cus_order)
                            except Exception as e:
                                print("Cannot fill PO No:", e)

                            # 5. Toggle CN Ref Flag if dev user or finish order triggered
                            if self.app.user_id.get() == "62078" or self.app.is_finish_order_triggered.get():
                                try:
                                    cn_flag_element = self.driver.find_element(By.CSS_SELECTOR, '#cnRefFlag')
                                    self.driver.execute_script("arguments[0].click();", cn_flag_element)
                                except Exception as cn_err:
                                    print("Cannot toggle cnRefFlag:", cn_err)

                            try:
                                self.driver.find_element(
                                    By.XPATH,
                                    '/html/body/div[1]/div[2]/div[6]/form/div[2]/div/div[5]/div[3]/div[1]/div[1]/div/div/div/div/div[2]/center/button[2]'
                                ).click()
                            except Exception:
                                pass

                            # 6. Fill Customer Name into textbox81037000101
                            cus_name_val = self.app.cus_name.get() if self.app.cus_name.get() else self.cus_order
                            final_cus_name_input_element = self.driver.find_element(By.XPATH, "//input[@id='textbox81037000101']")
                            self.bot.js_input_value(final_cus_name_input_element, cus_name_val)

                        except Exception as err:
                            print("Final page form filling failed, skip to waiting for price:", err)
                            break

                        # 7. Enter final price into ripCash00
                        try:
                            print("Auto enter price:", final_price)
                            final_price_element = self.driver.find_element(By.XPATH, "//input[@id='ripCash00']")
                            self.bot.js_input_value(final_price_element, final_price)
                        except Exception as e:
                            print("auto_final_price broken:", e)

                        # 8. Check all final page elements & Click green submit button (when Finish button pressed)
                        if self.app.is_finish_order_triggered.get():
                            try:
                                # First verification attempt
                                verification = self.verify_final_page_elements(
                                    expected_po=self.cus_order,
                                    expected_cus_name=cus_name_val,
                                    expected_price=final_price,
                                )

                                # If not all ok, attempt auto-recovery (re-fill missing elements once)
                                if not verification.get("all_ok", False):
                                    print(
                                        f"⚠️ [Payment Verification] Initial check failed: {verification}. Attempting auto-recovery..."
                                    )
                                    self.app.update_log(
                                        "⚠️ ข้อมูลหน้าท้ายยังไม่ครบ กำลังพยายามเติมค่าซ้ำอัตโนมัติ..."
                                    )
                                    self._recover_missing_elements(
                                        verification, final_price, cus_name_val
                                    )
                                    time.sleep(0.5)
                                    # Re-verify after recovery attempt
                                    verification = self.verify_final_page_elements(
                                        expected_po=self.cus_order,
                                        expected_cus_name=cus_name_val,
                                        expected_price=final_price,
                                    )

                                if verification.get("all_ok", False):
                                    time.sleep(0.75)
                                    print(
                                        "✅ All final page elements verified! Clicking btnPayment with retries..."
                                    )
                                    self.app.update_log(
                                        "✅ ตรวจสอบข้อมูลหน้าท้ายครบถ้วน กำลังกดปุ่มชำระเงิน (ปุ่มเขียว)..."
                                    )
                                    btn_payment = self.driver.find_element(
                                        By.XPATH,
                                        "//div[contains(@class,'wrimagecard')]//a[@id='btnPayment']",
                                    )
                                    click_done = False
                                    for click_attempt in range(1, 4):
                                        try:
                                            self.driver.execute_script(
                                                "arguments[0].scrollIntoView({block: 'center'});",
                                                btn_payment,
                                            )
                                            time.sleep(0.2)
                                            btn_payment.click()
                                            print(
                                                f"Clicked btnPayment successfully (attempt {click_attempt})"
                                            )
                                            click_done = True
                                            break
                                        except Exception as c_err:
                                            print(
                                                f"btnPayment click attempt {click_attempt} failed: {c_err}"
                                            )
                                            time.sleep(0.5)

                                    if not click_done:
                                        print(
                                            "Standard click failed, falling back to JS click on btnPayment"
                                        )
                                        self.driver.execute_script(
                                            "arguments[0].click();", btn_payment
                                        )
                                else:
                                    failed_fields = [
                                        k
                                        for k, v in verification.items()
                                        if k != "all_ok" and not v.get("ok", False)
                                    ]
                                    err_msg = (
                                        f"ไม่สามารถกดปุ่มเขียวได้ เนื่องจากข้อมูลหน้าท้ายไม่ครบถ้วน: {failed_fields}"
                                    )
                                    print(f"❌ {err_msg}")
                                    self.app.update_log(f"❌ {err_msg}")
                                    logger.error(f"Order: {self.cus_order} - {err_msg}")
                            except Exception as e:
                                print(f"Verification and payment submission failed: {e}")
                                logger.error(f"Verification and payment error: {e}")
                            finally:
                                self.app.is_finish_order_triggered.set(False)

                        # 9. Handle final popup after clicking green button
                        popup_success = self.final_popup_handler(is_etax=False, operation_obj=self.bot)
                        self.bot.autofinal = False
                        return popup_success

                    else:
                        print("จบสูตร")
                    self.bot.autofinal = False
                    break

                print("While หลัก ถ้ามาถึงนี่แปลว่าต้องเริ่มใหม่")
                break
            break

        print("operation_thread is set or autofinal is false, exit final loop")
        return True

    def verify_final_page_elements(
        self,
        expected_po: Optional[str] = None,
        expected_cus_name: Optional[str] = None,
        expected_price: Optional[float] = None,
    ) -> dict:
        """
        ตรวจสอบว่าข้อมูลใน Element ต่างๆ บนหน้าท้าย (Payment Page) มีค่าครบถ้วนและถูกต้องก่อนกดปุ่มเขียว
        - PO No. (textbox81037000102)
        - Customer Name (textbox81037000101)
        - Final Price (ripCash00)
        - CN Remark (posPaymentHead.data.cnRemark)
        - Remaining Balance (wrimagecard-lightGray) ต้องเป็น 0.00
        - Payment Button (#btnPayment) ต้องแสดงผลและพร้อมคลิก
        """
        target_po = expected_po if expected_po is not None else self.cus_order
        target_name = (
            expected_cus_name
            if expected_cus_name is not None
            else (
                self.app.cus_name.get()
                if hasattr(self.app, 'cus_name') and self.app.cus_name.get()
                else self.cus_order
            )
        )
        target_price = (
            expected_price
            if expected_price is not None
            else getattr(self.app, 'final_price', 0.0)
        )

        results: dict = {
            "po_no": {"ok": False, "value": "", "expected": target_po},
            "cus_name": {"ok": False, "value": "", "expected": target_name},
            "cash_price": {"ok": False, "value": None, "expected": target_price},
            "cn_remark": {"ok": False, "value": "", "expected": target_po},
            "balance": {"ok": False, "value": None, "expected": 0.0},
            "btn_payment": {"ok": False},
            "all_ok": False,
        }

        # 1. Check PO No.
        try:
            po_el = self.driver.find_element(By.XPATH, "//input[@id='textbox81037000102']")
            actual_po = (po_el.get_attribute("value") or "").strip()
            results["po_no"]["value"] = actual_po
            results["po_no"]["ok"] = bool(actual_po) and (
                not target_po or target_po in actual_po or actual_po == target_po
            )
        except Exception as e:
            results["po_no"]["error"] = str(e)

        # 2. Check Customer Name
        try:
            name_el = self.driver.find_element(By.XPATH, "//input[@id='textbox81037000101']")
            actual_name = (name_el.get_attribute("value") or "").strip()
            results["cus_name"]["value"] = actual_name
            results["cus_name"]["ok"] = bool(actual_name)
        except Exception as e:
            results["cus_name"]["error"] = str(e)

        # 3. Check Cash Input (ripCash00)
        try:
            cash_el = self.driver.find_element(By.XPATH, "//input[@id='ripCash00']")
            actual_cash_str = (
                (cash_el.get_attribute("value") or "").replace(",", "").strip()
            )
            if actual_cash_str != "":
                actual_cash = float(actual_cash_str)
                results["cash_price"]["value"] = actual_cash
                if target_price is not None:
                    results["cash_price"]["ok"] = abs(actual_cash - float(target_price)) < 0.01
                else:
                    results["cash_price"]["ok"] = True
            else:
                results["cash_price"]["value"] = None
                results["cash_price"]["ok"] = False
        except Exception as e:
            results["cash_price"]["error"] = str(e)

        # 4. Check CN Remark
        try:
            remark_el = None
            try:
                remark_el = self.driver.find_element(
                    By.XPATH, "//textarea[@ng-model='posPaymentHead.data.cnRemark']"
                )
            except Exception:
                remark_el = self.driver.find_element(
                    By.XPATH, "//div[@class='col-sm-4 nopadding']/textarea"
                )
            actual_remark = (remark_el.get_attribute("value") or "").strip()
            results["cn_remark"]["value"] = actual_remark
            results["cn_remark"]["ok"] = bool(actual_remark) and (
                not target_po or target_po in actual_remark
            )
        except Exception as e:
            results["cn_remark"]["error"] = str(e)

        # 5. Check Remaining Balance (wrimagecard-lightGray)
        try:
            balance_el = None
            try:
                balance_el = self.driver.find_element(
                    By.XPATH, "//div[contains(@class, 'wrimagecard-lightGray')]"
                )
            except Exception:
                balance_el = self.driver.find_element(
                    By.XPATH,
                    "//div[@class='col-sm-12    wrimagecard-lightGray wrimagecard-topimage ng-binding']",
                )
            balance_text = balance_el.text.strip().replace(",", "")
            balance_val = float(balance_text)
            results["balance"]["value"] = balance_val
            results["balance"]["ok"] = abs(balance_val) < 0.01
        except Exception as e:
            results["balance"]["error"] = str(e)

        # 6. Check Payment Button (#btnPayment)
        try:
            btn_el = self.driver.find_element(
                By.XPATH, "//div[contains(@class,'wrimagecard')]//a[@id='btnPayment']"
            )
            results["btn_payment"]["ok"] = btn_el.is_displayed()
        except Exception as e:
            try:
                btn_el = self.driver.find_element(By.XPATH, "//a[@id='btnPayment']")
                results["btn_payment"]["ok"] = btn_el.is_displayed()
            except Exception as e2:
                results["btn_payment"]["error"] = str(e2)

        results["all_ok"] = all(
            v.get("ok", False) for k, v in results.items() if k != "all_ok"
        )

        status_icon = "✅" if results["all_ok"] else "❌"
        print(f"[POSPaymentHandler.verify_final_page_elements] {status_icon} Verification: {results}")
        return results

    def _recover_missing_elements(
        self,
        verification: dict,
        final_price: float,
        cus_name_val: str,
    ) -> None:
        """
        พยายามกรอกข้อมูลในช่องที่ตรวจสอบแล้วพบว่ายังไม่ผ่าน/หลุดหาย
        """
        # เติม PO No.
        if not verification.get("po_no", {}).get("ok", False):
            try:
                print("⚠️ Auto-recovery: Re-filling PO No...")
                po_el = self.driver.find_element(By.XPATH, "//input[@id='textbox81037000102']")
                self.bot.js_input_value(po_el, self.cus_order)
            except Exception as e:
                print(f"Failed to recover PO No: {e}")

        # เติม Customer Name
        if not verification.get("cus_name", {}).get("ok", False):
            try:
                print("⚠️ Auto-recovery: Re-filling Customer Name...")
                name_el = self.driver.find_element(By.XPATH, "//input[@id='textbox81037000101']")
                self.bot.js_input_value(name_el, cus_name_val)
            except Exception as e:
                print(f"Failed to recover Customer Name: {e}")

        # เติม Final Price
        if not verification.get("cash_price", {}).get("ok", False):
            try:
                print("⚠️ Auto-recovery: Re-filling Cash Price...")
                price_el = self.driver.find_element(By.XPATH, "//input[@id='ripCash00']")
                self.bot.js_input_value(price_el, final_price)
            except Exception as e:
                print(f"Failed to recover Cash Price: {e}")

        # เติม CN Remark
        if not verification.get("cn_remark", {}).get("ok", False):
            try:
                print("⚠️ Auto-recovery: Re-filling CN Remark...")
                remark_xpath = "//div[@class='col-sm-4 nopadding']/textarea[@ng-model='posPaymentHead.data.cnRemark']"
                el = self.driver.find_element(By.XPATH, remark_xpath)
                self.bot.js_input_value(el, self.cus_order)
            except Exception as e:
                print(f"Failed to recover CN Remark: {e}")


    def final_popup_handler(self, is_etax: bool = False, operation_obj: Any = None) -> bool:
        """
        Monitors for the SweetAlert2 popup after clicking the green payment button.
        Extracts receipt number, prints receipt, and updates Excel records.
        """
        self.app.is_bot_browser_busy.set(False)
        loop_counter = 0

        while not self.bot.operation_thread.is_set():
            time.sleep(1)
            loop_counter += 1

            # Periodic Garbage Collection (every ~60 seconds)
            if loop_counter % 60 == 0:
                print(f"Performing garbage collection... (Loop count: {loop_counter})")
                gc.collect()

            try:
                final_popup = self.driver.find_element(By.XPATH, """//div[@class = 'swal2-content']""")
                self.bot.check_for_refresh_popup(final_popup)
                convert_full_tax_modal_element = self.driver.execute_script(
                    """ return document.querySelector("div[id='convertFullTaxModal']"); """
                )
                is_final_page = self.driver.find_element(
                    By.XPATH, '/html/body/div[2]/div[3]/div[6]/div[1]/span[1]')
            except Exception as loop_err:
                continue

            if final_popup.is_displayed():
                self.app.is_bot_browser_busy.set(True)
                print("final pop-up has displayed!")
                try:
                    time.sleep(0.5)

                    # Extract alert text from swal2-content
                    alert_text = ""
                    try:
                        alert_text = self.driver.find_element(By.XPATH, """//div[@class = 'swal2-content']""").text
                    except Exception:
                        pass

                    match = re.search(r'(?:ABB-)?B\d+-\w.*\d+-\d+', alert_text)
                    print(f"match: {match}, alert_text: '{alert_text}'")

                    if match:
                        inv_number = match.group()
                        print("inv_number: ", inv_number)
                        self.app.update_log(f'เลขบิล: {inv_number}')
                        self.bot.current_checkpoint = f"สร้างใบเสร็จสำเร็จ (เลขบิล: {inv_number})"

                        # E-tax flow if required
                        if is_etax and inv_number != "":
                            print("has etax")
                            try:
                                self.bot.etax_reprint(inv_number)
                            except Exception as e:
                                print(f"etax_reprint error: {e}")
                                logger.error(f"etax_reprint error: {e}")
                            self.bot._update_accel_on_complete(inv_number, is_etax=True)
                            time.sleep(0.75)
                            return True

                        # Update Excel record
                        self.bot._update_accel_on_complete(inv_number, is_etax=False)

                        # Close popup overlay (คลิกพื้นหลังสีดำ)
                        print("click container!")
                        self.driver.execute_script("document.querySelector('.swal2-overlay').click();")

                        # Wait for canvas/PDF embed to load & trigger print
                        self.wait50.until(EC.visibility_of_element_located(
                            (By.XPATH, '/html/body/div[2]/div[3]/div[10]/div/div[2]/div[2]/div/embed')
                        ))
                        time.sleep(1)

                        try:
                            self.bot.get_pdf_src_and_print(inv_number)
                            self.bot.current_checkpoint = "พิมพ์เอกสารใบเสร็จสำเร็จ"
                        except Exception as e:
                            print(f"get_pdf_src_and_print error: {e}")
                            logger.error(f"get_pdf_src_and_print error: {e}")

                        return True
                    else:
                        print("Popup displayed but no invoice number pattern matched yet, dismissing and re-clicking green button...")
                        try:
                            # 1. คลิกปุ่ม OK/ตกลง เพื่อปิด Popup แจ้งเตือน
                            confirm_btn = self.driver.find_element(
                                By.XPATH, "//button[@class='swal2-confirm styled' or contains(@class, 'swal2-confirm')]")
                            try:
                                confirm_btn.click()
                            except Exception:
                                self.driver.execute_script("arguments[0].click();", confirm_btn)
                            print("Clicked swal2-confirm button successfully")
                            time.sleep(0.75)

                            # 2. กดปุ่มเขียว (#btnPayment) อีกครั้งเพื่อจบ Order
                            btn_payment = self.driver.find_element(
                                By.XPATH, "//div[contains(@class,'wrimagecard')]//a[@id='btnPayment']")
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn_payment)
                            time.sleep(0.2)
                            try:
                                btn_payment.click()
                                print("Re-clicked btnPayment successfully (Standard click)")
                            except Exception:
                                self.driver.execute_script("arguments[0].click();", btn_payment)
                                print("Re-clicked btnPayment successfully (JS click)")
                            time.sleep(0.5)
                        except Exception as pop_err:
                            print(f"Error handling non-invoice popup or re-clicking green button: {pop_err}")
                            time.sleep(0.5)
                        continue

                except Exception as err:
                    print("เกิดข้อผิดพลาดระหว่างจัดการ Popup หน้าท้าย:", err)
                    time.sleep(1)
                    continue

            elif not is_final_page.is_displayed():
                print("หน้า final หายไป")
            elif convert_full_tax_modal_element and getattr(convert_full_tax_modal_element, 'is_displayed', lambda: False)():
                while not self.bot.operation_thread.is_set() and convert_full_tax_modal_element.is_displayed():
                    print("หน้าเลือกแบบย่อแบบเต็มยังแสดงผลอยู่")
                    if self.app.is_tax_required.get():
                        try:
                            el = self.driver.find_element(
                                By.CSS_SELECTOR, "input[name='radioConvertFullTaxModal'][ng-value='93003002']")
                            self.driver.execute_script("arguments[0].click();", el)
                            cus_name_element = self.driver.find_element(
                                By.XPATH, "//span[@id='select2-memberSearchft-container']")
                            convert_tax_cus_name = self.driver.execute_script(
                                "return arguments[0].getAttribute('title');", cus_name_element)
                            print("convert_tax_cus_name: ", convert_tax_cus_name)
                            if convert_tax_cus_name is None:
                                print("ยังไม่ได้เลือกใบกำกับ")
                                self.bot.set_cus_name_search_type_last_page()
                                self.bot.select_cusname_address_last_page()
                            break
                        except Exception as err:
                            print("radioConvertFullTaxModalErr: ", err)
                            time.sleep(0.5)
                            continue
                    else:
                        print("ไม่เอาใบกำกับ")
                    time.sleep(1)
            else:
                continue

    def return_to_first_page(self) -> None:
        """
        กดย้อนกลับจากหน้าชำระเงิน (Payment) กลับไปยังหน้าแรก (เปิดการขาย) ของ SMCO
        """
        try:
            # 1. สลับมาที่แท็บ SMCO เปิดการขาย
            if hasattr(self.bot, 'merged_dict') and 'SMCO :: เปิดการขาย' in self.bot.merged_dict:
                try:
                    self.driver.switch_to.window(self.bot.merged_dict['SMCO :: เปิดการขาย'])
                except Exception:
                    pass

            # 2. ค้นหาและกดปุ่มย้อนกลับ / Cancel บนหน้าจอชำระเงิน
            back_clicked = False
            back_selectors = [
                (By.XPATH, "//a[@class='btn btn-danger btn-sm' and @ng-click='cancelPayment()']"),
                (By.XPATH, "//button[@ng-click='cancelPayment()' or @ng-click='back()' or @ng-click='cancel()']"),
                (By.XPATH, "//a[@id='btnBack' or @id='btnCancel']"),
                (By.XPATH, "//button[contains(., 'ย้อนกลับ') or contains(., 'กลับหน้าแรก') or contains(., 'ยกเลิก')]"),
                (By.XPATH, "//a[contains(., 'ย้อนกลับ') or contains(., 'กลับหน้าแรก') or contains(., 'ยกเลิก')]"),
                (By.XPATH, "//div/a[@id='controlKeyF1' or @id='controlKeyEsc']"),
            ]

            for by, selector in back_selectors:
                try:
                    elements = self.driver.find_elements(by, selector)
                    for el in elements:
                        if el.is_displayed():
                            try:
                                el.click()
                            except Exception:
                                self.driver.execute_script("arguments[0].click();", el)
                            print(f"Clicked back button using selector: {selector}")
                            back_clicked = True
                            time.sleep(0.75)
                            break
                    if back_clicked:
                        break
                except Exception:
                    continue

            # 3. ลองส่งปุ่ม ESC (Keyboard fallback)
            if not back_clicked:
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    from selenium.webdriver.common.keys import Keys
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    print("Sent ESC key to return from payment page")
                    time.sleep(0.5)
                except Exception as esc_err:
                    print(f"Error sending ESC key: {esc_err}")

        except Exception as e:
            print(f"Error returning to first page: {e}")

