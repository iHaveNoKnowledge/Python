import os
import re
import time
from tkinter import filedialog

import pandas as pd
from openpyxl import load_workbook
from pypdf import PdfReader
from selenium.webdriver.common.by import By
from loguru import logger


class AccelMode:
    def __init__(self, main_app):
        self.main_app = main_app
        self.accel_file_dir = ""
        self.accel_df_state = {}
        self.accel_file_columns = []
        self.obj_data_from_accel_file = {}
        self.accel_orders_list = []
        self.CP_list = []
        self.accel_orders_count = 0
        self.excel_save_failed = False

    def select_accel_file(self):
        self.accel_file_dir = filedialog.askopenfilename(title="Select Accel File")
        if self.accel_file_dir:
            self.main_app.accl_dir_namedisplay_on_btn.configure(text=f"{self.accel_file_dir.split('/')[-1]}")
        else:
            self.main_app.accl_dir_namedisplay_on_btn.configure(text=f"ยังไม่เลือก Accel File")

        self.read_accel_file_to_state(self.accel_file_dir)

    def read_accel_file_to_state(self, accel_file_dir):
        self.accel_file_dir = accel_file_dir
        self.accel_df_state = pd.read_excel(self.accel_file_dir, dtype=str)
        print("before self.accel_df_state: ", self.accel_df_state)
        self.accel_df_state.loc[self.accel_df_state.duplicated(subset=['orders']), 'orders'] = pd.NA
        self.accel_df_state['orders'].dropna(inplace=True)
        print("after self.accel_df_state: ", self.accel_df_state)

        self.accel_file_columns = self.accel_df_state.columns.dropna().tolist()
        self.obj_data_from_accel_file = {
            col: [str(x).strip() for x in self.accel_df_state[col].dropna().tolist() if str(x).strip() != 'nan']
            for col in self.accel_file_columns}

        self.accel_orders_list = self.accel_df_state['orders'].dropna().tolist()
        self.CP_list = self.accel_df_state['cp'].dropna().tolist()
        print(self.accel_orders_list)
        print('self.obj_data_from_accel_file: ', self.obj_data_from_accel_file)
        print(self.CP_list)

    def deduct_accel_file_data(self, order, sku_serials=[], remove_order=True, update_memory=True):
        order = order.get()
        df = self.accel_df_state
        print("deduct_accel_file_data df มีมาก่อนเหรอ: ", df)
        print("deduct_accel_file_data order: ", order)

        if remove_order:
            print("deduct_accel_file_data ref: ", df.loc[df['orders'] == order, 'orders'])
            has_order = df.loc[df['orders'] == order, 'orders']
            if not has_order.empty:
                print(f'remove {order} from state df')
                df.loc[df['orders'] == order, 'orders'] = pd.NA

        print("sku_serials ไม่ได้ได้ไง: ", sku_serials)
        if sku_serials:
            for sn in sku_serials:
                df.loc[df[sn['sku']] == sn['sn'], sn['sku']] = pd.NA

        print("form state df to new excel")
        print(f"Check if accel file is accesible {os.access(self.accel_file_dir, os.W_OK)}")

        try:
            df.to_excel(self.accel_file_dir, sheet_name='Sheet1', index=False)
            print(f"Successfully updated {self.accel_file_dir}")
            self.excel_save_failed = False

            if update_memory:
                # อ่าน dataframe ใหม่หลังจากอัปเดต Excel file
                self.accel_df_state = pd.read_excel(self.accel_file_dir, dtype=str)
                self.obj_data_from_accel_file = {
                    col: [str(x).strip() for x in self.accel_df_state[col].dropna().tolist()
                          if str(x).strip() != 'nan'] for col in self.accel_file_columns}
        except PermissionError as e:
            print(f"Permission denied: {e}")
            logger.warning(f"ไฟล์ Excel ถูกเปิดอยู่ในโปรแกรมอื่น บันทึกไม่สำเร็จ จะใช้ข้อมูลในหน่วยความจำแทน: {e}")
            self.excel_save_failed = True
            if update_memory:
                # ใช้ข้อมูลในหน่วยความจำแทน ไม่อัปเดตไฟล์
                self.accel_df_state = df
                self.obj_data_from_accel_file = {
                    col: [str(x).strip() for x in self.accel_df_state[col].dropna().tolist()
                          if str(x).strip() != 'nan'] for col in self.accel_file_columns}
        except Exception as e:
            print(f"Error updating Excel file: {e}")
            self.excel_save_failed = True
            if update_memory:
                # ใช้ข้อมูลในหน่วยความจำแทน
                self.accel_df_state = df
                self.obj_data_from_accel_file = {
                    col: [str(x).strip() for x in self.accel_df_state[col].dropna().tolist()
                          if str(x).strip() != 'nan'] for col in self.accel_file_columns}

    def extract_sn_btn(self, accel_file_dir):
        if not accel_file_dir:
            print("select accel file first!!")
            return

        target_dirs = filedialog.askopenfilenames(title="Select SN PDF files")
        if len(target_dirs) != 0:
            for target_dir in target_dirs:
                self.sn_extractor(accel_file_dir, target_dir)
        else:
            print("You have not selected any transfer file, Extraction ends!!")
        self.accel_df_state = pd.read_excel(self.accel_file_dir, dtype=str)

        self.read_accel_file_to_state(self.accel_file_dir)

    def sn_extractor(self, output_excel, target_dir):
        extracted_txt = self._extract_text_from_pdf(target_dir)
        extracted_txt = self._clean_text(extracted_txt)

        product_codes = self._extract_skus(extracted_txt)
        serial_numbers = self._extract_serial_numbers(extracted_txt)

        cleaned_serial_numbers = self._clean_serial_numbers(serial_numbers)
        serial_numbers_grouped = self._group_serial_numbers(cleaned_serial_numbers)

        self._print_debug_info(product_codes, cleaned_serial_numbers, serial_numbers_grouped)
        self._write_to_excel(output_excel, product_codes, serial_numbers_grouped)

    def _extract_text_from_pdf(self, target_dir):
        reader = PdfReader(target_dir)
        extracted_txt = ""
        for page in reader.pages:
            extracted_txt += page.extract_text()
        return extracted_txt

    def _clean_text(self, text):
        pattern = r'^.*?(?=No\. Product Code Barcode Product Name Transfer No\. Order Ship Status)'
        text = re.sub(pattern, '', text, flags=re.DOTALL).lstrip()

        pattern2 = r'ผู้ส่งสินค้า.*?(?:No\. Product Code Barcode Product Name Transfer No\. Order Ship Status|วันที่ _ _ _ / _ _ _ / _ _ _)'
        text = re.sub(pattern2, '', text, flags=re.DOTALL)

        text = re.sub(r'Serial\s:', '', text, flags=re.DOTALL)
        text = re.sub(r'\d+\s{0,}(?=([A-Z0-9]{3}-[0-9]{6}))', '', text, flags=re.DOTALL)

        return text

    def _extract_skus(self, text):
        sku_pattern = r'([A-Z0-9]{3}-[0-9]{6})'
        return re.findall(sku_pattern, text)

    def _extract_serial_numbers(self, text):
        serial_pattern = r'(?:Shipped|Confirm)\s*([\w, \n, \/]+)(?=(?:[A-Z0-9]{3}-[0-9]{6}|\nผู้ส่งสินค้า|$))'
        return re.findall(serial_pattern, text, re.DOTALL)

    def _clean_serial_numbers(self, serial_numbers):
        cleaned = []
        for serial in serial_numbers:
            serial = re.sub(r'\n', '', serial).strip()
            cleaned.append(serial)
        return cleaned

    def _group_serial_numbers(self, cleaned_serial_numbers):
        return [serial.replace(" ", "").split(",") for serial in cleaned_serial_numbers]

    def _print_debug_info(self, product_codes, cleaned_serial_numbers, serial_numbers_grouped):
        print("Product Codes:")
        for i, code in enumerate(product_codes, 1):
            print(i, code)

        print("\nSerial Numbers:")
        for i, serial in enumerate(cleaned_serial_numbers, 1):
            serial_list = serial.replace(" ", "").split(",")
            print(f"{i} {len(serial_list)} [{serial}]")

        print("SKU Matches:", len(product_codes), product_codes)
        print("Serial Numbers Grouped:", len(serial_numbers_grouped), serial_numbers_grouped)

    def _write_to_excel(self, output_excel, product_codes, serial_numbers_grouped):
        try:
            book = load_workbook(output_excel)
            sheet = book.active

            # * Map existing SKUs to their columns to avoid duplicates
            existing_skus = {}
            for col in range(1, sheet.max_column + 1):
                sku = sheet.cell(row=1, column=col).value
                if sku:
                    existing_skus[sku] = col

            # * Add new SKUs and their serial numbers, avoiding duplicates
            for sku, serials in zip(product_codes, serial_numbers_grouped):  # *the incoming new data from PDF
                if sku in existing_skus:
                    col = existing_skus[sku]

                    existing_serials = []
                    for row in range(2, sheet.max_row + 1):
                        val = sheet.cell(row=row, column=col).value
                        if val:
                            existing_serials.append(val)

                    merged_serials = existing_serials.copy()
                    for s in serials:
                        if s not in merged_serials:
                            existing_serials.append(s)

                else:
                    # * ถ้าเป็น SKU ใหม่ ให้เพิ่มคอลัมน์ใหม่ แล้วใส่ serials ลงไปเรื่อยๆจนหมด
                    col = sheet.max_column + 1
                    sheet.cell(row=1, column=col, value=sku)
                    for row, serial in enumerate(serials, start=2):
                        sheet.cell(row=row, column=col, value=serial)
                    existing_skus[sku] = col

            book.save(output_excel)
            print(f"ข้อมูลถูกเพิ่ม/อัปเดตลงใน {output_excel} เรียบร้อยแล้ว")

        except PermissionError as e:
            print(f"Permission denied: {e}")
            print("ไฟล์ Excel อาจถูกเปิดอยู่ในโปรแกรมอื่น กรุณาปิดไฟล์แล้วลองใหม่")
        except Exception as e:
            import traceback
            print(f"เกิดข้อผิดพลาด: {e}")
            traceback.print_exc()

    # * start searching orders from accel file to check if order needed to be processed
    def accel_search(self):
        self.main_app.is_accel_mode_activated.set(True)
        self.accel_orders_count = len(self.accel_orders_list)

        def start_next_cycle(count):
            # ดึงข้อมูลจาก Excel ใหม่ทุกรอบเพื่อให้ได้ SN บนสุดที่ยังเหลืออยู่ (เหมือน reload magazine)
            # แต่ถ้าเซฟครั้งก่อนไม่สำเร็จ (PermissionError) ให้ใช้ข้อมูลในหน่วยความจำล่าสุดแทนการไปดึงจากไฟล์เดิมบนดิสก์
            if getattr(self, 'excel_save_failed', False):
                logger.warning("ตรวจพบการบันทึก Excel ล้มเหลวก่อนหน้า จะใช้ข้อมูลในหน่วยความจำล่าสุดแทนการโหลดใหม่จากไฟล์ดิสก์")
            else:
                try:
                    self.accel_df_state = pd.read_excel(self.accel_file_dir, dtype=str)
                    self.obj_data_from_accel_file = {
                        col: [str(x).strip() for x in self.accel_df_state[col].dropna().tolist() if str(x).strip() != 'nan']
                        for col in self.accel_file_columns}
                except Exception as e:
                    logger.error(f"เกิดข้อผิดพลาดในการโหลดไฟล์ Excel: {e}")
            if count < self.accel_orders_count:
                if self.main_app.is_accel_mode_activated.get():
                    self.main_app.search_order(self.accel_orders_list[count], lambda: start_next_cycle(count+1))
                else:
                    logger.info("Accel mode has been stopped by user.")
            else:
                pass

        self.main_app.search_order(self.accel_orders_list[0], lambda: start_next_cycle(1))

    # * ดึงรายการ SN ที่พร้อมใช้งานในสต็อกของ SMCO ทั้งหมดสำหรับ SKU นี้
    def get_available_sns_from_smco(self, driver, sku):
        """
        ดึงรายการ SN ที่พร้อมใช้งานในสต็อกของ SMCO ทั้งหมดสำหรับ SKU นี้
        """
        try:
            import re
            from loguru import logger

            # 1. เตรียม Cookies และ Origin จาก Browser
            cookies = self.main_app.bot.get_cookies_from_driver()
            current_url = driver.current_url
            matched_str = re.search(r'\/[A-z].*', current_url).group()
            origin = current_url.replace(matched_str, '')

            # 2. ค้นหา Product ID จาก SKU
            resp_prod = self.main_app.smco_api.get_product_info(origin, sku, cookies)
            product_data = resp_prod.json()

            if not product_data or len(product_data) == 0:
                logger.warning(f"ไม่พบข้อมูลสินค้าสำหรับ SKU: {sku}")
                return []

            product_id = product_data[0].get('productId') or product_data[0].get('id')
            master_id = 180
            parent_id = 441

            if not product_id:
                return []

            # 3. ค้นหา Serial List จาก Product ID
            resp_sn = self.main_app.smco_api.get_serial_list(
                origin, product_id, master_id, parent_id, cookies
            )
            sn_list_data = resp_sn.json().get('data', [])

            # ดึงเฉพาะ serialNo ของตัวที่พร้อมใช้งาน
            found_sns = [str(item.get('serialNo')).strip() for item in sn_list_data if item.get('serialNo')]
            logger.debug(f"SMCO API ส่งกลับมารวม {len(found_sns)} รายการสำหรับ product {product_id}")
            return found_sns

        except Exception as e:
            from loguru import logger
            logger.error(f"Error while fetching available SNs via API: {e}")
            return "API_ERROR"

    # * ตรวจสอบว่า SN นั้นมีอยู่ในระบบ SMCO จริงหรือไม่ (รักษา signature เดิมไว้เผื่อใช้ร่วมกับส่วนอื่น)
    def is_sn_in_smco(self, driver, sku, sn_to_check):
        """
        ตรวจสอบ SN ผ่าน API ว่ามีในสต็อกของ SMCO จริงไหม
        """
        res = self.get_available_sns_from_smco(driver, sku)
        if res == "API_ERROR":
            return "API_ERROR"
        return sn_to_check in res

    # * เอาไว้ใช้กับ smco โดยการเอา sn จาก accel file มาใส่ในช่อง sku input บนเว็บ smco
    def accel_fill_sku(self, driver, operation_thread):
        from loguru import logger
        from selenium.webdriver.common.keys import Keys

        accel_available_skus_list = list(self.obj_data_from_accel_file.keys())
        self.used_serials = []
        ordered_product_data_rows = self.main_app.items
        print('accel_fill_sku() ตรวจสอบ items = ', ordered_product_data_rows)

        if len(ordered_product_data_rows) > 0:
            for i, ordered_item in enumerate(ordered_product_data_rows):
                print("item ordered by customer", ordered_item)
                current_sku = ordered_item['เลขอ้างอิง SKU (SKU Reference No.)']
                print("current_sku: ", current_sku)
                sku_qtys = ordered_item['จำนวน']
                is_sku_ready_to_pick = [key for key in accel_available_skus_list if key in current_sku]

                if len(is_sku_ready_to_pick) > 0:
                    # 1. ดึงรายการ Available SN จาก SMCO สำหรับ SKU นี้เพียงครั้งเดียว (ลดจำนวน API call)
                    print(f"กำลังเช็คสต็อกทั้งหมดสำหรับ SKU: {current_sku} ผ่าน API...")
                    available_sns = self.get_available_sns_from_smco(driver, current_sku)

                    if available_sns == "API_ERROR":
                        logger.warning(f"เช็ค API สำหรับ SKU {current_sku} ล้มเหลวชั่วคราว -> ข้ามการเลือก Serial สำหรับ SKU นี้ในรอบนี้")
                        continue

                    # 2. กรองและหักลบตัวที่มีใน Excel แต่ไม่มีใน SMCO (เป็นตัวที่ขายไปแล้ว) ออกในคราวเดียว
                    candidates = self.obj_data_from_accel_file.get(current_sku, [])
                    invalid_candidates = [c for c in candidates if c not in available_sns]
                    if invalid_candidates:
                        logger.warning(
                            f"พบ Serial ที่ไม่มีในสต็อก SMCO จริงสำหรับ SKU {current_sku}: {invalid_candidates} -> กำลังลบออกจาก Excel")
                        # ลบ Serial ที่ไม่มีสต็อกออกทีเดียวทั้งหมด
                        deduct_items = [{'sku': current_sku, 'sn': c} for c in invalid_candidates]
                        self.deduct_accel_file_data(
                            self.main_app.cus_order, deduct_items,
                            remove_order=False, update_memory=False)
                        # เอาออกจาก memory queue ด้วย
                        self.obj_data_from_accel_file[current_sku] = [c for c in candidates if c in available_sns]

                    # 3. ดำเนินการกรอก Serial ตามจำนวนชิ้นที่สั่ง
                    for item in range(sku_qtys):
                        # ดึงข้อมูลตัวแรกในคิวที่ผ่านการ Double-check (เช็คสดวินาทีสุดท้าย)
                        valid_sn = None
                        while self.obj_data_from_accel_file[current_sku]:
                            candidate_sn = self.obj_data_from_accel_file[current_sku][0]
                            print(f"Double-check ล่าสุดสำหรับ SN: {candidate_sn}")

                            # เช็คสดกับรายการ available_sns ใน memory ที่ดึงมาแล้วแทนการยิง API ซ้ำใน loop
                            check_latest = candidate_sn in available_sns if isinstance(available_sns, list) else False
                            if check_latest is True:
                                valid_sn = candidate_sn
                                break
                            elif check_latest == "API_ERROR":
                                logger.warning(f"Double-check สำหรับ SN {candidate_sn} ล้มเหลวชั่วคราว -> ข้ามไปก่อนชั่วคราวโดยไม่ลบจาก Excel")
                                self.obj_data_from_accel_file[current_sku].pop(0)
                            else:
                                logger.warning(f"Double-check พบว่า SN {candidate_sn} เพิ่งถูกขาย/จองไป -> กำลังลบออกจาก Excel")
                                self.deduct_accel_file_data(
                                    self.main_app.cus_order, [{'sku': current_sku, 'sn': candidate_sn}],
                                    remove_order=False, update_memory=False)
                                self.obj_data_from_accel_file[current_sku].pop(0)

                        if valid_sn:
                            sn = valid_sn
                            print(f"มี SN ที่ผ่านการ Double-check และพร้อมใช้งานจริง: {sn}")
                            time.sleep(1)

                            while not operation_thread.is_set():
                                try:
                                    driver.find_element(
                                        By.XPATH,
                                        '/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')
                                    break
                                except:
                                    continue

                            skuInput = driver.find_element(
                                By.XPATH,
                                '/html/body/div[2]/div[3]/div[2]/div[2]/div[1]/div[1]/from/div/div/div[1]/div[1]/span/input')
                            skuInput.clear()
                            attempts = 10
                            while attempts > 0:
                                try:
                                    skuInput.send_keys(sn)
                                    # เอาออกจาก memory queue (ตัวที่ใช้จริง)
                                    self.obj_data_from_accel_file[current_sku].pop(0)
                                    break
                                except:
                                    time.sleep(0.5)
                                    attempts -= 1
                            else:
                                logger.error('sku input in smco cannot be interact from order: ',
                                             self.main_app.cus_order.get())
                                raise ValueError('sku input in smco cannot be interact')

                            print("fill sn complete")

                            skuInput.send_keys(Keys().ENTER)
                            print("pressed Enter at SKU-Input")
                            print(f'to_sent_dict = sku: {current_sku}, sn: {sn} ')
                            to_sent_dict = {'sku': current_sku, 'sn': sn}
                            self.used_serials.append(to_sent_dict)
                            print("current self.used_serials = ", self.used_serials)
                            time.sleep(2)
                        else:
                            logger.warning(f"ไม่มี SN เหลือที่ใช้งานได้ในสต็อกสำหรับ SKU: {current_sku}")
                            break
                else:
                    logger.info(
                        f"""มี current_sku ใน Accel_File หรือไม่?: {current_sku in self.obj_data_from_accel_file}""")
                    print("มี current_sku ใน Accel_File หรือไม่?:",
                          current_sku in self.obj_data_from_accel_file)
        else:
            print("No items, return!!")
            return
