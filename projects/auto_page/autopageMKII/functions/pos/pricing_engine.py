"""
Module: functions.pos.pricing_engine
Contains:
  - OrderFinancials: Single Source of Truth (SSOT) for order-level and item-level financial calculations.
  - POSPricingReconciler: Handles price mismatch detection, campaign coupon (CP) matching from Excel,
    overcharge (OC) / discount (DC) adjustments on the SMCO POS cart, and 2-step verification.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


@dataclass
class OrderFinancials:
    """
    Single Source of Truth (SSOT) สำหรับการคำนวณราคาและส่วนลดทั้งหมดใน Order
    """
    items: List[Dict[str, Any]]
    shipping_cost: float = 0.0
    seller_voucher: float = 0.0
    marketplace: str = "SHOPEE"
    
    # Computed fields
    aggregated_items: Dict[str, Dict[str, float]] = field(default_factory=dict)
    item_expected_prices: Dict[str, float] = field(default_factory=dict)
    sum_price: float = 0.0
    total_cart_price: float = 0.0
    final_billing_price: float = 0.0

    def __post_init__(self):
        self.recalculate()

    def recalculate(self) -> None:
        """คำนวณตัวเลขทางการเงินทั้งหมดจาก items, shipping_cost, seller_voucher"""
        self.aggregated_items.clear()
        self.item_expected_prices.clear()

        total_net_sum = 0.0

        for item in self.items:
            sku_key = str(item.get('เลขอ้างอิง SKU (SKU Reference No.)', '')).strip()
            if not sku_key:
                continue

            raw_price = str(item.get('ราคาขายสุทธิ', item.get('ราคาตั้งต้น', 0))).replace(',', '')
            price_val = float(raw_price) if raw_price else 0.0

            raw_qty = str(item.get('จำนวน', 1)).replace(',', '')
            qty_val = float(raw_qty) if raw_qty else 1.0

            raw_discount = str(item.get('ส่วนลดจาก Shopee', 0)).replace(',', '')
            shopee_discount = float(raw_discount) if raw_discount else 0.0

            if sku_key not in self.aggregated_items:
                self.aggregated_items[sku_key] = {
                    "total_qty": qty_val,
                    "total_price": price_val,
                    "total_discount": shopee_discount
                }
            else:
                self.aggregated_items[sku_key]["total_qty"] += qty_val
                self.aggregated_items[sku_key]["total_price"] += price_val
                self.aggregated_items[sku_key]["total_discount"] += shopee_discount

            total_net_sum += price_val + shopee_discount

        for sku_key, data in self.aggregated_items.items():
            t_qty = data["total_qty"] if data["total_qty"] > 0 else 1.0
            unit_expected = (data["total_price"] + data["total_discount"]) / t_qty
            self.item_expected_prices[sku_key] = round(unit_expected, 2)

        self.sum_price = round(total_net_sum, 2)

        # คำนวณราคายอดรวมตะกร้า (Shopee คิดค่าส่งร่วมด้วย)
        if self.marketplace.upper() == "SHOPEE":
            self.total_cart_price = round(self.sum_price + self.shipping_cost, 2)
            self.final_billing_price = max(0.0, round(self.total_cart_price - self.seller_voucher, 2))
        else:  # LAZADA
            self.total_cart_price = self.sum_price
            self.final_billing_price = max(0.0, round(self.sum_price - self.seller_voucher, 2))


class POSPricingReconciler:
    """
    รับผิดชอบงานตรวจเช็คราคา (Price Reconciliation) และปรับราคาในหน้า POS
    - แมตช์คูปอง CP จาก Excel (cp_data.xlsx)
    - ใส่ส่วนลดสินค้า (smco_set_discount_product) / ปรับราคาขึ้น (smco_set_overcharge_product)
    - เลือกคูปอง (cp_sonic_blow_process)
    - ดำเนินการขั้นตอน verify_all() ทั้ง 2 รอบ
    """

    def __init__(self, bot):
        self.bot = bot
        self.app = bot.app
        self.driver = bot.driver
        self.wait50 = bot.wait50

    # ══════════════════════════════════════════════════════════════════════════
    # HELPER UTILITIES
    # ══════════════════════════════════════════════════════════════════════════
    def sku_formater(self, sku_input: str) -> str:
        """แปลง SKU ให้อยู่ในฟอร์แมตมาตรฐาน เช่น sp2-1703 -> SP2-001703"""
        prog = re.findall(r'[A-Za-z]{2,}[A-Za-z0-9]?-?\d{1,6}', str(sku_input))
        result = ""
        for item in prog:
            if '-' in item:
                prefix, number = item.split('-', 1)
                uppered_prefix = prefix.upper()
                number_padded = number.zfill(6)
                result += f"{uppered_prefix}-{number_padded} "
            else:
                result += f"{item.upper()} "
        return result.strip()

    def oc_amounts_calculator(self, entered_data: Any) -> Union[int, float, str]:
        """คำนวณยอดเงิน OC / DC ที่อาจเป็น expression เช่น 100+20 หรือ 500-50"""
        entered_data = str(entered_data).replace(',', '')
        if "+" in entered_data:
            operands = [float(x.strip()) for x in entered_data.split("+") if x.strip()]
            return sum(operands)
        elif "-" in entered_data and not entered_data.strip().startswith("-"):
            operands = [float(x.strip()) for x in entered_data.split("-") if x.strip()]
            if operands:
                res = operands[0]
                for op in operands[1:]:
                    res -= op
                return res
        try:
            return float(entered_data.strip())
        except ValueError:
            return entered_data

    # ══════════════════════════════════════════════════════════════════════════
    # EXCEL CP LOOKUP & MISSING RECORDING
    # ══════════════════════════════════════════════════════════════════════════
    def reload_cp_if_modified(self) -> None:
        """ตรวจสอบและ reload CP Data อัตโนมัติเมื่อตรวจพบว่าไฟล์ Excel มีการแก้ไขหรือเซฟใหม่ (mtime เปลี่ยน)"""
        if hasattr(self.app, 'reload_cp_df_if_modified'):
            self.app.reload_cp_df_if_modified()
            return

        excel_path = getattr(self.app, 'cp_table_location', '')
        if not excel_path or not os.path.exists(excel_path):
            return

        try:
            current_mtime = os.path.getmtime(excel_path)
            if getattr(self.app, 'cp_df', None) is None or current_mtime > getattr(self.app, '_cp_last_mtime', 0):
                df = pd.read_excel(excel_path)
                if 'usage_start_date' in df.columns:
                    df['usage_start_date'] = pd.to_datetime(df['usage_start_date'], format='mixed', dayfirst=True, errors='coerce')
                if 'usage_end_date' in df.columns:
                    df['usage_end_date'] = pd.to_datetime(df['usage_end_date'], format='mixed', dayfirst=True, errors='coerce')
                self.app.cp_df = df
                self.app._cp_last_mtime = current_mtime
                print(f"[CP Cache] ตรวจพบการแก้ไขไฟล์ CP Data -> โหลดข้อมูลใหม่สำเร็จ ({len(self.app.cp_df)} รายการ)")
        except PermissionError as e:
            print(f"[CP Cache] ไฟล์ CP Data ถูกเปิดอยู่ในโปรแกรมอื่น: {e}")
        except Exception as e:
            print(f"[CP Cache] เกิดข้อผิดพลาดในการตรวจสอบ/โหลด CP Data: {e}")

    def find_all_cp_candidates_from_excel(self, sku: str, platform_price: float, purchased_date_str: str) -> list:
        """
        ค้นหา CP ทุกชุดที่เป็นไปได้จากไฟล์ cp_data.xlsx (self.app.cp_df) และส่งกลับเป็น list of dict
        """
        # ตรวจสอบและ reload อัตโนมัติหากไฟล์ถูกแก้ไขภายนอก
        self.reload_cp_if_modified()

        if self.app.cp_df is None or self.app.cp_df.empty:
            print("[CP Lookup] No CP data loaded")
            return []

        # 1. Parse purchased date
        try:
            purchased_dt = pd.to_datetime(purchased_date_str, format='mixed', dayfirst=True)
            if pd.isna(purchased_dt):
                return []
        except Exception as e:
            print(f"[CP Lookup] Date parsing error for '{purchased_date_str}': {e}")
            return []

        # 2. Filter by SKU
        sku_clean = str(sku).strip().upper()
        formatted_skus = [s.strip().upper() for s in self.app.correct_sku_pattern(sku)]

        def sku_match(row_sku) -> bool:
            row_sku_str = str(row_sku).strip().upper()
            return (row_sku_str == sku_clean) or (row_sku_str in formatted_skus)

        sku_mask = self.app.cp_df['sku'].apply(sku_match)
        df_filtered = self.app.cp_df[sku_mask]

        if df_filtered.empty:
            print(f"[CP Lookup] No matching SKU found in CP Data for: {sku}")
            return []

        # 3. Filter by Date Range
        valid_rows = []
        date_rejected_reasons = []
        for idx, row in df_filtered.iterrows():
            try:
                start_date = pd.to_datetime(row.get('usage_start_date'), format='mixed', dayfirst=True)
                end_date = pd.to_datetime(row.get('usage_end_date'), format='mixed', dayfirst=True)

                in_range = True
                if pd.notna(start_date) and pd.notna(end_date):
                    if not (start_date.date() <= purchased_dt.date() <= end_date.date()):
                        in_range = False
                elif pd.notna(start_date):
                    if not (start_date.date() <= purchased_dt.date()):
                        in_range = False
                elif pd.notna(end_date):
                    if not (purchased_dt.date() <= end_date.date()):
                        in_range = False

                if in_range:
                    valid_rows.append(row)
                else:
                    s_str = start_date.strftime('%d/%m/%Y') if pd.notna(start_date) else 'N/A'
                    e_str = end_date.strftime('%d/%m/%Y') if pd.notna(end_date) else 'N/A'
                    cp_code = row.get('cp_name', '')
                    price_val = row.get('sale_price', '')
                    date_rejected_reasons.append(f"CP: '{cp_code}' (ราคา {price_val}, ช่วงวัน: {s_str} - {e_str})")
            except Exception as date_err:
                print(f"[CP Lookup] Row date validation error at index {idx}: {date_err}")

        if not valid_rows:
            reasons_str = "; ".join(date_rejected_reasons) if date_rejected_reasons else "ไม่มีช่วงวันระบุ"
            print(f"[CP Lookup] SKU {sku} found, but date {purchased_dt.date()} is not within any CP usage range. (รายละเอียดช่วงวัน: {reasons_str})")
            return []

        df_valid = pd.DataFrame(valid_rows)

        # 4. Filter by Price (sale_price == platform_price)
        price_tolerance = 0.05
        df_price_matched = df_valid[(df_valid['sale_price'] - platform_price).abs() <= price_tolerance]

        if df_price_matched.empty:
            print(f"[CP Lookup] SKU {sku} date matched, but no matching sale_price for platform_price={platform_price}. Available prices in valid date range: {df_valid['sale_price'].tolist()}")
            return []

        # 5. เรียงลำดับตาม usage_start_date ล่าสุด
        if len(df_price_matched) > 1:
            df_price_matched = df_price_matched.copy()
            df_price_matched['temp_start_date'] = pd.to_datetime(
                df_price_matched.get('usage_start_date'), format='mixed', dayfirst=True, errors='coerce'
            )
            df_price_matched = df_price_matched.sort_values(
                by='temp_start_date', ascending=False, na_position='last'
            )

        candidates = []
        for _, row in df_price_matched.iterrows():
            cp_name = row.get('cp_name')
            oc_amount = row.get('oc_amount')
            dc_amount = row.get('dc_amount')
            candidates.append({
                "cp_name": str(cp_name).strip() if pd.notna(cp_name) else "",
                "oc_amount": str(oc_amount).strip() if pd.notna(oc_amount) else "",
                "dc_amount": str(dc_amount).strip() if pd.notna(dc_amount) else ""
            })

        return candidates

    def find_cp_from_excel(self, sku: str, platform_price: float, purchased_date_str: str) -> Optional[dict]:
        """
        ค้นหา CP ชุดแรกจากไฟล์ cp_data.xlsx (Backward Compatibility)
        """
        candidates = self.find_all_cp_candidates_from_excel(sku, platform_price, purchased_date_str)
        return candidates[0] if candidates else None

    def add_missing_cp_to_excel(self, sku_key: str, expected_price: float) -> None:
        """บันทึก SKU และราคาที่ยังไม่มี CP ลงไฟล์ Excel เพื่อให้กรอกข้อมูลต่อได้"""
        try:
            excel_path = getattr(self.app, 'cp_table_location', '')
            if not excel_path or str(excel_path).strip() == "":
                return

            import os
            if not os.path.exists(excel_path):
                return

            try:
                df = pd.read_excel(excel_path)
            except Exception as read_err:
                print(f"[add_missing_cp_to_excel] Error reading excel: {read_err}")
                return

            new_row = {'sku': sku_key, 'sale_price': expected_price}
            new_df = pd.DataFrame([new_row])

            for col in df.columns:
                if col not in new_df.columns:
                    new_df[col] = ""
            new_df = new_df[df.columns]

            df_combined = pd.concat([df, new_df], ignore_index=True)
            df_combined.to_excel(excel_path, index=False)
            if os.path.exists(excel_path):
                try:
                    self.app._cp_last_mtime = os.path.getmtime(excel_path)
                except Exception:
                    pass

            self.app.update_log(
                f"💾 บันทึก SKU: {sku_key} (ราคาเป้าหมาย: {expected_price}) ลงใน CP Data เรียบร้อยแล้ว"
            )

            if self.app.cp_df is not None:
                if 'usage_start_date' in new_df.columns:
                    new_df['usage_start_date'] = pd.to_datetime(new_df['usage_start_date'], format='mixed', dayfirst=True, errors='coerce')
                if 'usage_end_date' in new_df.columns:
                    new_df['usage_end_date'] = pd.to_datetime(new_df['usage_end_date'], format='mixed', dayfirst=True, errors='coerce')
                self.app.cp_df = pd.concat([self.app.cp_df, new_df], ignore_index=True)

        except Exception as err:
            print(f"[add_missing_cp_to_excel] Error appending row: {err}")

    # ══════════════════════════════════════════════════════════════════════════
    # COUPON SELECTION & ADJUSTMENTS ON POS CART
    # ══════════════════════════════════════════════════════════════════════════
    def cp_sonic_blow_process(self, item_no: int, cp_no: str) -> bool:
        """
        เลือก coupon สำหรับสินค้าที่ระบุ รองรับการเลือกหลาย coupon ในครั้งเดียว
        รองรับทั้งการระบุเป็นลำดับตัวเลข (Index เช่น "1 5") หรือระบุเป็นชื่อ/รหัสคูปองโดยตรง (เช่น "CP2605220025, DC2605220017")
        และรองรับสินค้าที่มีหลาย SKU ใน 1 รายการ (เช่น "SP2-001610+SP2-001611+...") ให้เลือกคูปองให้ครบทุก SKU

        Args:
            item_no (int): เลขลำดับสินค้า (1-indexed)
            cp_no (str): ลำดับคูปอง (ตัวเลข) หรือ รหัสคูปอง (ข้อความ) แยกด้วยเว้นวรรคหรือเครื่องหมายจุลภาค
        """
        item_idx = int(item_no) - 1
        raw_tokens = []
        for part in str(cp_no).split(','):
            for token in part.split():
                if token.strip():
                    raw_tokens.append(token.strip())

        if not raw_tokens:
            return False

        # * สำหรับหน้าเลือก coupon เก็บชื่อ coupon ที่เลือกแต่ละตัว เพื่อนำไปใช้กับ SKU ถัดไป
        cp_target_names = []

        cp_name_loc = "//div[@ng-show='posbook.data.cnFormPaymentId===undefined']//span[@class='text-primary price-sku-h1 ng-binding']"
        selected_cp_btn_loc = "//div[@ng-show='posbook.data.cnFormPaymentId===undefined']//button[@ng-click='selectCoupon(oms.currentProductByProcessCoupon,pmt)']"

        demonic_ordered_items_list = self.app.correct_sku_pattern(
            self.app.items[item_idx]['เลขอ้างอิง SKU (SKU Reference No.)']
        )
        print(f"demonic_ordered_items_list: {demonic_ordered_items_list}")
        print(f"raw_tokens: {raw_tokens}")

        self.driver.switch_to.window(self.bot.merged_dict['SMCO :: เปิดการขาย'])
        green_agree_btn_xpath = 'button[ng-click="okCoupon()"]'

        any_success = False

        # * Loop ผ่านแต่ละ item ในรายการสินค้า (สำหรับ pattern ที่ 1 รายการมีหลาย SKU เช่น SP2-001610+SP2-001611+...)
        for idx, item in enumerate(demonic_ordered_items_list):
            item_position = idx + 1
            print(f"item [{item_position}/{len(demonic_ordered_items_list)}] จาก demonic_ordered_items_list: {item}")

            # ดึงข้อมูลรายการสินค้าบนหน้าเว็บใหม่ทุกรอบของแต่ละสินค้า เพื่อรองรับความเปลี่ยนแปลงของหน้าเว็บและตำแหน่งที่อาจสลับได้เสมอ!
            try:
                item_texts = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('.col-sm-12.panel.panel-default.ng-scope')).map(el => el.innerText);
                """)
            except Exception as e:
                print("ไม่สามารถดึงข้อมูลรายการสินค้าจากหน้าเว็บได้:", e)
                item_texts = []

            # สร้าง dict mapping ระหว่าง SKU -> Index สำหรับรอบนั้นๆ
            sku_to_index = {}
            for pos_idx, text in enumerate(item_texts):
                if item in text:
                    sku_to_index[item] = pos_idx
                    break

            if item not in sku_to_index:
                print(f"ไม่พบ SKU: {item} ในรายการขายหน้าเว็บ (ข้าม)")
                continue

            target_idx = sku_to_index[item]
            print(f"เจอสินค้า {item} ที่ตำแหน่ง Index: {target_idx}")

            try:
                # ดึงรายการปุ่ม Coupon ล่าสุดสดๆ เสมอเพื่อเลี่ยง Stale Element
                item_list_cp_btn_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, 'div.col-sm-4.nopadding button.btn-coupon.btn.btn-sm'
                )
                if target_idx >= len(item_list_cp_btn_elements):
                    print(f"ดึงปุ่ม coupon ของ {item} ไม่สำเร็จ (index เกินรายการ)")
                    continue

                # * คลิกปุ่ม coupon เพื่อเปิดหน้ารายการ coupon (เปิดครั้งเดียว)
                cp_btn_xpath = item_list_cp_btn_elements[target_idx]
                cp_btn_xpath.click()
                time.sleep(0.3)  # * รอให้หน้า coupon list โหลด

                # * Loop ผ่านแต่ละ coupon token ที่ต้องการเลือก
                for cp_idx, token in enumerate(raw_tokens):
                    print(f"กำลังเลือก coupon: {token} สำหรับ item: {item}")

                    # ค้นหาปุ่มคูปองเป้าหมาย
                    target_btn_idx = -1

                    # ดึงข้อมูลชื่อคูปองและปุ่มบนหน้าจอสดๆ เสมอ
                    cp_name_elements = self.driver.find_elements(By.XPATH, cp_name_loc)
                    cp_btn_elements = self.driver.find_elements(By.XPATH, selected_cp_btn_loc)

                    if not cp_name_elements or not cp_btn_elements:
                        print("ไม่พบรายการคูปองหรือปุ่มคูปองบนหน้าจอ")
                        continue

                    # กรณีที่ 1: token เป็นรหัสคูปอง/ชื่อคูปองโดยตรง (มีตัวอักษรปน เช่น CPxxxx, DCxxxx)
                    if not token.isdigit():
                        token_clean = token.replace(" ", "").upper()
                        for idx3, element in enumerate(cp_name_elements):
                            element_text_cleaned = element.text.replace(" ", "").upper()
                            if token_clean in element_text_cleaned:
                                target_btn_idx = idx3
                                break
                        if target_btn_idx == -1:
                            print(f"ไม่พบคูปองที่มีชื่อ/รหัส: {token} ในรายการ")
                            continue

                    # กรณีที่ 2: token เป็นลำดับตัวเลข (Index เช่น "1", "2")
                    else:
                        original_idx = int(token) - 1

                        # รักษาความสามารถเดิม: ถ้ามี cp_target_name จากรอบก่อน ให้ใช้ชื่อนั้นค้นหาแทนเพื่อกันตำแหน่งสลับ
                        if cp_idx < len(cp_target_names) and cp_target_names[cp_idx] != "":
                            for idx3, element in enumerate(cp_name_elements):
                                element_text_cleaned = element.text.replace(" ", "").upper()
                                if cp_target_names[cp_idx] in element_text_cleaned:
                                    target_btn_idx = idx3
                                    break
                            if target_btn_idx == -1:
                                target_btn_idx = original_idx
                        else:
                            target_btn_idx = original_idx

                    # คลิกเลือกคูปองที่ต้องการ
                    if 0 <= target_btn_idx < len(cp_btn_elements):
                        cp_btn_elements[target_btn_idx].click()
                        time.sleep(0.2)  # * รอให้ UI อัพเดท

                        # ดึงชื่อคูปองล่าสุดอีกรอบในกรณีที่มีการ update เพื่อความปลอดภัย
                        latest_cp_name_elements = self.driver.find_elements(By.XPATH, cp_name_loc)
                        if target_btn_idx < len(latest_cp_name_elements):
                            selected_cp_name = latest_cp_name_elements[target_btn_idx].text.replace(" ", "").upper()
                        else:
                            selected_cp_name = ""

                        # * เก็บหรืออัพเดทชื่อ CP ที่เลือกเพื่อใช้ในสินค้าตัวถัดไป
                        if cp_idx >= len(cp_target_names):
                            cp_target_names.append(selected_cp_name)
                            print(f"cp_target_name[{cp_idx}] now is: {selected_cp_name}")
                        else:
                            cp_target_names[cp_idx] = selected_cp_name

                        any_success = True
                    else:
                        print(f"ตำแหน่ง Index {target_btn_idx} นอกขอบเขตของรายการปุ่มคูปองที่มีอยู่ ({len(cp_btn_elements)})")

                # * กดยืนยัน (ครั้งเดียวหลังจากเลือกครบทุก coupon แล้วสำหรับ SKU นี้)
                print(f"click OK ในรอบของ: {item}, เลือก coupon ทั้งหมด: {raw_tokens}")
                try:
                    agree_btns = self.driver.find_elements(By.CSS_SELECTOR, green_agree_btn_xpath)
                    if agree_btns and agree_btns[0].is_displayed():
                        agree_btns[0].click()
                    else:
                        self.driver.find_element(By.CSS_SELECTOR, green_agree_btn_xpath).click()
                except Exception:
                    pass
                time.sleep(0.2)

            except Exception as err:
                print("Demonic CP Bot inner Exception Error:", err)
                try:
                    agree_btns = self.driver.find_elements(By.CSS_SELECTOR, green_agree_btn_xpath)
                    if agree_btns and agree_btns[0].is_displayed():
                        agree_btns[0].click()
                except Exception:
                    pass

        print(f"เลือก coupon เสร็จสิ้น: {cp_target_names}")
        return any_success

    def scan_matching_cp_candidates_on_smco(self, item_no: int, cp_candidates: list) -> list:
        """
        สแกนดูคูปองทั้งหมดบนหน้าต่าง Modal ของ SMCO แล้วจับคู่กับ cp_candidates
        ส่งกลับ list ของ candidate ที่พบคูปองบนหน้าเว็บ SMCO จริง (หรือ candidate ที่ไม่จำเป็นต้องใช้ CP)
        """
        item_idx = int(item_no) - 1
        demonic_ordered_items_list = self.app.correct_sku_pattern(
            self.app.items[item_idx]['เลขอ้างอิง SKU (SKU Reference No.)']
        )
        self.driver.switch_to.window(self.bot.merged_dict['SMCO :: เปิดการขาย'])
        green_agree_btn_xpath = 'button[ng-click="okCoupon()"]'
        cp_name_loc = "//div[@ng-show='posbook.data.cnFormPaymentId===undefined']//span[@class='text-primary price-sku-h1 ng-binding']"

        target_idx = None
        for idx, item in enumerate(demonic_ordered_items_list):
            try:
                item_texts = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('.col-sm-12.panel.panel-default.ng-scope')).map(el => el.innerText);
                """)
            except Exception:
                item_texts = []

            for pos_idx, text in enumerate(item_texts):
                if item in text:
                    target_idx = pos_idx
                    break
            if target_idx is not None:
                break

        if target_idx is None:
            return []

        try:
            item_list_cp_btn_elements = self.driver.find_elements(
                By.CSS_SELECTOR, 'div.col-sm-4.nopadding button.btn-coupon.btn.btn-sm'
            )
            if target_idx >= len(item_list_cp_btn_elements):
                return []

            # เปิด Modal ดูรายการคูปองที่มีบนหน้าเว็บ
            item_list_cp_btn_elements[target_idx].click()
            time.sleep(0.3)

            cp_name_elements = self.driver.find_elements(By.XPATH, cp_name_loc)
            smco_coupon_names = [el.text.replace(" ", "").upper() for el in cp_name_elements if el.text.strip()]
            self.last_scanned_smco_coupons = [el.text.strip() for el in cp_name_elements if el.text.strip()]

            # ปิด Modal ชั่วคราว (ยังไม่เลือก)
            try:
                agree_btns = self.driver.find_elements(By.CSS_SELECTOR, green_agree_btn_xpath)
                if agree_btns and agree_btns[0].is_displayed():
                    agree_btns[0].click()
            except Exception:
                pass

            # ตรวจสอบ Candidate แต่ละชุดว่ามีคูปองอยู่บนหน้าเว็บ SMCO จริงไหม
            matched_candidates = []
            for cand in cp_candidates:
                cp_name = cand.get("cp_name", "")
                is_bypass = str(cp_name).strip().upper() in ["NONE", "BYPASS", "NO_CP", "NO CP", "PASSTHROUGH"]

                if not cp_name or is_bypass or cp_name.strip() == "":
                    # ชุดที่ไม่มีคูปอง (มีแต่ OC/DC หรือ bypass) ถือว่า match ได้
                    matched_candidates.append(cand)
                else:
                    raw_tokens = [t.strip().upper() for part in str(cp_name).split(',') for t in part.split() if t.strip()]
                    all_tokens_in_smco = True
                    for token in raw_tokens:
                        token_clean = token.replace(" ", "")
                        found = False
                        if token.isdigit():
                            target_i = int(token) - 1
                            if 0 <= target_i < len(smco_coupon_names):
                                found = True
                        else:
                            for idx_el, elem_name in enumerate(smco_coupon_names):
                                if token_clean in elem_name:
                                    found = True
                                    break
                        if not found:
                            all_tokens_in_smco = False
                            break

                    if all_tokens_in_smco:
                        matched_candidates.append(cand)

            return matched_candidates

        except Exception as err:
            print("[scan_matching_cp_candidates_on_smco] Error:", err)
            try:
                agree_btns = self.driver.find_elements(By.CSS_SELECTOR, green_agree_btn_xpath)
                if agree_btns and agree_btns[0].is_displayed():
                    agree_btns[0].click()
            except Exception:
                pass
            return []

    def smco_set_overcharge_product(self, items_user_input: str = None, oc_amounts_input: str = None) -> None:
        """ปรับราคาขึ้น (Overcharge) สำหรับ SKU ที่ต้องการ"""
        if items_user_input is None or oc_amounts_input is None:
            return

        formatted_items_to_oc = self.sku_formater(items_user_input).split(" ")
        oc_amounts_list_prog = str(oc_amounts_input).split()
        oc_amounts_list = [int(self.oc_amounts_calculator(a)) for a in oc_amounts_list_prog]
        items_list_element = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')

        for idx, item in enumerate(formatted_items_to_oc):
            oc_amount = oc_amounts_list[0]
            if len(oc_amounts_list) > 1 and idx < len(oc_amounts_list):
                oc_amount = oc_amounts_list[idx]

            if oc_amount > 0:
                for idx2, div in enumerate(items_list_element):
                    try:
                        if div.text.find(item) != -1:
                            li_loc = idx2 + 1
                            srp_btn_css = f'.col-sm-12.panel.panel-default.ng-scope:nth-child({li_loc}) div.panel-body:nth-child(1) div.row.col-sm-6:nth-child(2) > div:nth-child(1) div:nth-child(1) div a:nth-child(1)'
                            self.driver.find_element(By.CSS_SELECTOR, srp_btn_css).click()
                            time.sleep(0.5)

                            change_price_input = self.driver.find_element(By.XPATH, "//input[@ng-keyup='onPistive(oms)']")
                            based_price = self.driver.execute_script("return angular.element(arguments[0]).val();", change_price_input)
                            new_price = float(str(based_price).replace(",", "")) + float(oc_amount)

                            self.driver.execute_script(
                                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                                change_price_input, 0)
                            self.driver.execute_script(
                                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                                change_price_input, new_price)

                            user_id_input = self.driver.find_element(
                                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[2]/input')
                            self.bot.js_input_value(user_id_input, self.app.user_id.get())

                            user_pw_input = self.driver.find_element(
                                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[2]/div[3]/input')
                            self.bot.js_input_value(user_pw_input, self.app.user_pw.get())

                            note_textarea = self.driver.find_element(
                                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[5]/div/textarea')
                            self.bot.js_input_value(note_textarea, "Online")

                            green_submit_btn = self.driver.find_element(
                                By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[6]/a[1]')
                            self.driver.execute_script("arguments[0].click();", green_submit_btn)

                            try:
                                self.wait50.until(EC.invisibility_of_element_located(
                                    (By.XPATH, '/html/body/div[2]/div[3]/div[2]/div[2]/div[8]/div/div/div[2]/div[6]/a[1]')))
                            except Exception:
                                time.sleep(1)
                            break
                    except Exception as err:
                        logger.error(f"Order: {self.bot.cus_order}: smco_set_overcharge error: {err}")

    def smco_set_discount_product(self, items_user_input: str = None, dc_amounts_input: str = None, qty: Any = ["1"]) -> None:
        """ปรับราคาลด (Discount) สำหรับ SKU ที่ต้องการ"""
        if items_user_input is None or dc_amounts_input is None:
            return

        formatted_items_to_dc = self.sku_formater(items_user_input).split(" ")
        dc_amounts_list_prog = str(dc_amounts_input).split()
        dc_amounts_list = [float(self.oc_amounts_calculator(a)) for a in dc_amounts_list_prog]
        item_elements = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')

        for idx, item in enumerate(formatted_items_to_dc):
            dc_amount = dc_amounts_list[0]
            if len(dc_amounts_list) > 1 and idx < len(dc_amounts_list):
                dc_amount = dc_amounts_list[idx]

            qty_val = 1.0
            if qty is not None:
                try:
                    if isinstance(qty, list):
                        qty_val = float(qty[idx] if idx < len(qty) else qty[0])
                    else:
                        qty_val = float(qty)
                except Exception:
                    qty_val = 1.0

            if dc_amount > 0:
                for idx2, div in enumerate(item_elements):
                    try:
                        if div.text.find(item) != -1:
                            li_loc = idx2 + 1
                            total_net_btn_css = f'#bodyOfSku > div:nth-child({li_loc}) > div > div:nth-child(2) > div:nth-child(1) > div:nth-child(9) > a:nth-child(3)'
                            self.driver.find_element(By.CSS_SELECTOR, total_net_btn_css).click()
                            time.sleep(0.5)

                            manual_dc_input = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '#mdseScroll > div.panel.panel-default > div.panel-body > div:nth-child(1) > div > div:nth-child(1) > input'
                            )
                            sum_dc_amount = dc_amount * qty_val
                            self.driver.execute_script(
                                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                                manual_dc_input, sum_dc_amount
                            )

                            note_textarea = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '#mdseScroll > div.panel.panel-default > div.panel-body > div:nth-child(2) > div > div > textarea'
                            )
                            self.driver.execute_script("""
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input'));
                                arguments[0].dispatchEvent(new Event('change'));
                            """, note_textarea, "Online")

                            user_id_input = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '#mdseScroll > div.panel.panel-default > div.panel-body > div:nth-child(3) > div > div:nth-child(1) > input'
                            )
                            self.driver.execute_script("""
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input'));
                                arguments[0].dispatchEvent(new Event('change'));
                            """, user_id_input, self.app.user_id.get())

                            user_pw_input = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '#mdseScroll > div.panel.panel-default > div.panel-body > div:nth-child(3) > div > div:nth-child(2) > input'
                            )
                            self.driver.execute_script("""
                                arguments[0].value = arguments[1];
                                arguments[0].dispatchEvent(new Event('input'));
                                arguments[0].dispatchEvent(new Event('change'));
                            """, user_pw_input, self.app.user_pw.get())

                            green_btn_submit = self.driver.find_element(
                                By.CSS_SELECTOR,
                                '.row.row-space div.text-center a.btn.btn-success.text-center#saveCustomerBtn[ng-click="okChagePrice()"]'
                            )
                            self.driver.execute_script("arguments[0].click();", green_btn_submit)

                            try:
                                self.wait50.until(EC.invisibility_of_element_located(
                                    (By.CSS_SELECTOR, '.row.row-space div.text-center a.btn.btn-success.text-center#saveCustomerBtn[ng-click="okChagePrice()"]')))
                            except Exception:
                                time.sleep(1)
                            break
                    except Exception as err:
                        logger.error(f"Order: {self.bot.cus_order}: smco_set_discount error: {err}")

    # ══════════════════════════════════════════════════════════════════════════
    # PRICE MISMATCH RESOLUTION PIPELINE
    # ══════════════════════════════════════════════════════════════════════════
    def process_price_mismatches(self, verification_result: dict) -> None:
        """
        ตรวจสอบความแตกต่างของราคาสินค้าแต่ละ SKU และเรียกใช้คูปองหรือปรับราคาหากมีส่วนต่าง
        """
        price_result = verification_result.get("price", {})

        def is_valid_adjustment(amount_str: Any) -> bool:
            if not amount_str or str(amount_str).strip() == "" or str(amount_str).strip().upper() == "NONE":
                return False
            tokens = str(amount_str).split()
            for token in tokens:
                clean = token.replace('-', '').replace('+', '').split('.')[0].strip()
                if clean.isdigit() and int(clean) > 0:
                    return True
            return False

        processed_skus = set()
        for i, item in enumerate(self.app.items):
            sku_key = item.get('เลขอ้างอิง SKU (SKU Reference No.)')
            if not sku_key or sku_key in processed_skus:
                continue
            processed_skus.add(sku_key)

            if sku_key in price_result:
                item_price_info = price_result[sku_key]
                if not item_price_info.get("ok", True):
                    diff_val = item_price_info.get("diff", 0)
                    expected_price = item_price_info.get("expected", 0)
                    actual_price = item_price_info.get("actual", 0)
                    item_no_1indexed = i + 1
                    purchased_date = self.app.cus_purchase_time.get()

                    if actual_price == "NOT_FOUND":
                        error_msg = f"ไม่มีสินค้าให้ตรวจสอบและปรับราคา สำหรับ SKU: {sku_key} (วันที่: {purchased_date}, ราคาที่ต้องออกบิล: {expected_price})"
                        self.app.update_log(f"❌ {error_msg}")
                        raise ValueError(error_msg)

                    # ดึง Candidate CP/DC ทั้งหมดที่เป็นไปได้สำหรับ SKU และราคานี้
                    cp_candidates = self.find_all_cp_candidates_from_excel(sku_key, expected_price, purchased_date)

                    if not isinstance(diff_val, (int, float)):
                        continue

                    # กรณีที่ 1: marketplace_item_price > smco_item_price? (diff > 0)
                    if diff_val > 0:
                        applied = False
                        if cp_candidates:
                            for cand in cp_candidates:
                                if is_valid_adjustment(cand.get("oc_amount", "")):
                                    oc_amount_str = cand.get("oc_amount", "")
                                    self.app.update_log(f"⚡ ปรับราคาขึ้น (Overcharge) จากข้อมูลแคมเปญ: {oc_amount_str} บาท")
                                    self.smco_set_overcharge_product(sku_key, str(oc_amount_str))
                                    applied = True
                                    break
                        if not applied:
                            self.app.update_log(f"⚡ ปรับราคาขึ้น (Overcharge) สำหรับ SKU: {sku_key} จำนวน {diff_val} บาท")
                            self.smco_set_overcharge_product(sku_key, str(diff_val))

                    # กรณีที่ 2: marketplace_item_price < smco_item_price? (diff < 0)
                    elif diff_val < 0:
                        self.app.update_log(f"🔍 กำลังหาคูปองลดราคาสำหรับ SKU: {sku_key} (พบ {len(cp_candidates)} รูปแบบใน CP Data)")

                        # สแกนดูว่าในบรรดา candidates ทั้งหมด มีกี่ชุดที่พบคูปองบนหน้าเว็บ SMCO จริง
                        available_candidates = self.scan_matching_cp_candidates_on_smco(item_no_1indexed, cp_candidates) if cp_candidates else []

                        # ─── CASE 0: ไม่พบชุดใดที่ใช้ได้บน SMCO เลย ───
                        if len(available_candidates) == 0:
                            has_entry = len(cp_candidates) > 0
                            if not has_entry:
                                self.add_missing_cp_to_excel(sku_key, expected_price)

                            log_msg = f"❌ ไม่พบชุด CP/DC ใดที่ตรงกับในระบบ SMCO สำหรับ SKU: {sku_key} (วันที่: {purchased_date}, ราคาที่ต้องออก: {expected_price}) -> หยุดปรับราคาและสร้างคำถาม"
                            logger.warning(log_msg)
                            self.app.update_log(log_msg)
                            self._raise_missing_cp_guide(item, sku_key, actual_price, expected_price, purchased_date, has_entry=has_entry, cp_candidates=cp_candidates)

                        # ─── CASE 1: พบชุดที่ตรงบน SMCO พอดี 1 ชุด ───
                        elif len(available_candidates) == 1:
                            chosen_cand = available_candidates[0]
                            cp_name = chosen_cand.get("cp_name", "")
                            oc_amount_str = chosen_cand.get("oc_amount", "")
                            dc_amount_str = chosen_cand.get("dc_amount", "")
                            is_bypass_signal = str(cp_name).strip().upper() in ["NONE", "BYPASS", "NO_CP", "NO CP", "PASSTHROUGH"]

                            if is_bypass_signal:
                                self.app.update_log(f"⏩ ข้ามการปรับราคาสำหรับ SKU: {sku_key} (กำหนดเป็น {cp_name})")
                                continue

                            has_valid_cp = bool(cp_name and not is_bypass_signal and cp_name.strip() != "")
                            has_valid_oc = is_valid_adjustment(oc_amount_str)
                            has_valid_dc = is_valid_adjustment(dc_amount_str)

                            if not (has_valid_cp or has_valid_oc or has_valid_dc):
                                self._raise_missing_cp_guide(item, sku_key, actual_price, expected_price, purchased_date, has_entry=True)

                            if has_valid_cp:
                                self.app.update_log(f"🔍 เลือกคูปอง [{cp_name}] สำหรับ SKU: {sku_key}...")
                                cp_ok = self.cp_sonic_blow_process(item_no_1indexed, cp_name)
                                if not cp_ok:
                                    log_err = f"❌ เกิดข้อผิดพลาดขณะกดเลือกคูปอง [{cp_name}] บน SMCO สำหรับ SKU: {sku_key}"
                                    logger.error(log_err)
                                    self.app.update_log(log_err)
                                    self._raise_missing_cp_guide(item, sku_key, actual_price, expected_price, purchased_date, has_entry=True)
                                time.sleep(0.5)

                            if has_valid_oc:
                                self.app.update_log(f"⚡ ปรับราคาขึ้น (Overcharge) จากข้อมูลแคมเปญ: {oc_amount_str} บาท")
                                self.smco_set_overcharge_product(sku_key, str(oc_amount_str))
                                time.sleep(0.5)

                            if has_valid_dc:
                                item_qty = int(item.get('จำนวน', 1))
                                total_dc = float(dc_amount_str) * item_qty
                                self.app.update_log(f"📉 ปรับราคาลด (Discount): {dc_amount_str} x {item_qty} = {total_dc} บาท")
                                self.smco_set_discount_product(sku_key, str(dc_amount_str), qty=item_qty)
                                time.sleep(0.5)

                            self.app.update_log(f"✅ ใช้ชุด CP/DC สำหรับ SKU: {sku_key} สำเร็จ")

                        # ─── CASE 2: พบชุดที่ตรงบน SMCO มากกว่า 1 ชุด (Ambiguity Detected!) ───
                        else:
                            ambiguous_details = []
                            for idx_a, ac in enumerate(available_candidates, start=1):
                                desc = f"ชุดที่ {idx_a}: CP='{ac.get('cp_name')}', OC='{ac.get('oc_amount')}', DC='{ac.get('dc_amount')}'"
                                ambiguous_details.append(desc)

                            ambiguity_str = "\n".join(f"  • {d}" for d in ambiguous_details)
                            log_warn = (
                                f"⚠️ [Ambiguity Alert] พบชุด CP/DC ที่ตรงเงื่อนไขบนหน้าเว็บ SMCO มากกว่า 1 ชุด ({len(available_candidates)} ชุด) สำหรับ SKU: {sku_key}\n"
                                f"{ambiguity_str}\n"
                                f"ระบบจะหยุดการปรับราคาอัตโนมัติเพื่อป้องกันการเลือกผิดพลาด (Option B: Strict Safety)"
                            )
                            logger.warning(log_warn)
                            self.app.update_log(log_warn)

                            # -------------------------------------------------------------
                            # [OPTION A] Auto-Resolve by Newest Date (Commented out)
                            # หากต้องการเปลี่ยนไปใช้ Option A ในอนาคต ให้ uncomment ส่วนนี้:
                            # -------------------------------------------------------------
                            # chosen_cand = available_candidates[0]  # เรียงตาม usage_start_date ล่าสุดไว้แล้ว
                            # cp_name = chosen_cand.get("cp_name", "")
                            # oc_amount_str = chosen_cand.get("oc_amount", "")
                            # dc_amount_str = chosen_cand.get("dc_amount", "")
                            # self.app.update_log(f"⚡ [Option A] เลือกใช้ชุดโปรโมชั่นล่าสุดอัตโนมัติ: CP='{cp_name}'")
                            # if cp_name and cp_name.strip():
                            #     self.cp_sonic_blow_process(item_no_1indexed, cp_name)
                            #     time.sleep(0.5)
                            # if is_valid_adjustment(oc_amount_str):
                            #     self.smco_set_overcharge_product(sku_key, str(oc_amount_str))
                            #     time.sleep(0.5)
                            # if is_valid_adjustment(dc_amount_str):
                            #     item_qty = int(item.get('จำนวน', 1))
                            #     self.smco_set_discount_product(sku_key, str(dc_amount_str), qty=item_qty)
                            #     time.sleep(0.5)
                            # self.app.update_log(f"✅ [Option A] ปรับราคาตามโปรล่าสุดเรียบร้อยแล้ว")
                            # -------------------------------------------------------------

                            # [OPTION B] Strict Safety: ไม่เลือกสุ่มสี่สุ่มห้า หยุดปรับราคา และสร้างคำถามพร้อมแจ้งรายละเอียดชุดที่พบ
                            self._raise_ambiguous_cp_guide(item, sku_key, actual_price, expected_price, purchased_date, available_candidates)

    def _raise_ambiguous_cp_guide(self, item: dict, sku_key: str, actual_price: Any, expected_price: Any, purchased_date: str, candidate_list: list) -> None:
        """แจ้งเตือนและจัดรูปแบบข้อความขอวิธีปรับราคาเมื่อพบคูปองที่ตรงเงื่อนไขซ้ำซ้อนกันมากกว่า 1 ชุด"""
        marketplace = self.app.marketplace_target.get()
        purchase_time = self.app.cus_purchase_time.get()
        product_name = str(item.get('ชื่อสินค้า', '')).strip()
        if product_name.lower() == 'nan':
            product_name = ''

        try:
            actual_formatted = f"{float(actual_price):,.2f}"
        except Exception:
            actual_formatted = str(actual_price)
        try:
            expected_formatted = f"{float(expected_price):,.2f}"
        except Exception:
            expected_formatted = str(expected_price)

        cand_lines = []
        for idx, c in enumerate(candidate_list, start=1):
            cp = c.get('cp_name') or '-'
            oc = c.get('oc_amount') or '-'
            dc = c.get('dc_amount') or '-'
            cand_lines.append(f"  {idx}) CP: {cp} | OC: {oc} | DC: {dc}")

        cand_str = "\n".join(cand_lines)

        pattern_msg = (
            f"\n{marketplace} เวลาสั่งซื้อ {purchase_time}\n"
            f"{sku_key} {product_name}\n"
            f"ยิงขายขึ้น {actual_formatted} บาท\n"
            f"ลูกค้าซื้อราคา {expected_formatted} บาท\n"
            f"ขอวิธีปรับราคาครับ (พบคูปอง/ส่วนลดที่เข้าเงื่อนไข {len(candidate_list)} ชุดบน SMCO):\n"
            f"{cand_str}"
        )
        self.app.update_log(pattern_msg)
        error_msg = f"Order skipped, multiple ambiguous CP/DC options found for SKU: {sku_key} (วันที่: {purchased_date}, ราคาที่ต้องออกบิล: {expected_price})\n{pattern_msg}"
        self.app.update_log(f"❌ {error_msg}")
        logger.warning(f"Order: {self.bot.cus_order}: {error_msg}")
        raise ValueError(error_msg)

    def _raise_missing_cp_guide(self, item: dict, sku_key: str, actual_price: Any, expected_price: Any, purchased_date: str, has_entry: bool, cp_candidates: list = None) -> None:
        """แจ้งเตือนและจัดรูปแบบข้อความขอวิธีปรับราคาเมื่อไม่พบคูปอง"""
        marketplace = self.app.marketplace_target.get()
        purchase_time = self.app.cus_purchase_time.get()
        product_name = str(item.get('ชื่อสินค้า', '')).strip()
        if product_name.lower() == 'nan':
            product_name = ''

        try:
            actual_formatted = f"{float(actual_price):,.2f}"
        except Exception:
            actual_formatted = str(actual_price)
        try:
            expected_formatted = f"{float(expected_price):,.2f}"
        except Exception:
            expected_formatted = str(expected_price)

        excel_cp_names = [c.get('cp_name') for c in (cp_candidates or []) if c.get('cp_name')]
        smco_scanned = getattr(self, 'last_scanned_smco_coupons', [])

        if has_entry:
            excel_str = ", ".join(excel_cp_names) if excel_cp_names else "ระบุแต่ยังไม่มีรหัส CP"
            smco_str = ", ".join(smco_scanned) if smco_scanned else "ไม่พบปุ่ม CP หรือไม่มีคูปองบนหน้า SMCO"
            extra_note = f" (มี SKU ใน CP_data แล้ว แต่ CP ใน Excel กับหน้า SMCO ไม่ตรงกัน:\n  • ใน cp_data.xlsx ระบุ: {excel_str}\n  • บนหน้า SMCO มี: {smco_str})"
        else:
            extra_note = ""

        pattern_msg = (
            f"\n{marketplace} เวลาสั่งซื้อ {purchase_time}\n"
            f"{sku_key} {product_name}\n"
            f"ยิงขายขึ้น {actual_formatted} บาท\n"
            f"ลูกค้าซื้อราคา {expected_formatted} บาท\n"
            f"ขอวิธีปรับราคาครับ{extra_note}"
        )
        self.app.update_log(pattern_msg)
        error_msg = f"Order skipped, CP/DC not set for SKU: {sku_key} (วันที่: {purchased_date}, ราคาที่ต้องออกบิล: {expected_price})\n{pattern_msg}"
        self.app.update_log(f"❌ {error_msg}")
        raise ValueError(error_msg)

    # ══════════════════════════════════════════════════════════════════════════
    # FULL RECONCILIATION & VERIFICATION PIPELINE
    # ══════════════════════════════════════════════════════════════════════════
    def reconcile_and_verify(self) -> None:
        """
        ดำเนินการยิงสินค้าลง POS, ตรวจสอบรอบที่ 1, ปรับราคา mismatch, และตรวจสอบรอบที่ 2
        """
        try:
            self.bot.ProductManager.auto_add_all_items()
            self.bot.current_checkpoint = "กรอกสินค้าลง POS สำเร็จ"

            # รอบที่ 1: ตรวจสอบราคาและจำนวน
            verification_result = self.bot.ProductManager.verify_all()
            print("verification_result (Round 1): ", verification_result)
            self.bot.current_checkpoint = "ตรวจสอบราคาและจำนวนสำเร็จ"

            # เช็คจำนวนสินค้า (ขาด SN หรือ ยิงไม่ติด) -> fail order ทันที
            qty_shortage_lines = []
            for sku, info in verification_result.get("qty", {}).items():
                if not info.get("ok", True):
                    qty_shortage_lines.append(
                        f"  • {sku}: ลูกค้าสั่ง {info.get('expected')} แต่ลง POS ได้ {info.get('actual')}"
                    )
            if qty_shortage_lines:
                err_msg = "จำนวนไม่พอ (ลง POS ได้น้อยกว่าที่ลูกค้าสั่ง):\n" + "\n".join(qty_shortage_lines)
                self.app.update_log(f"❌ {err_msg}")
                raise ValueError(err_msg)

            # ดำเนินการปรับราคาและใส่คูปอง
            self.process_price_mismatches(verification_result)
            self.bot.current_checkpoint = "ปรับราคา/ใส่คูปองสำเร็จ (จบ process ปรับราคา)"

            # รอบที่ 2: ตรวจสอบซ้ำเฉพาะกรณีที่รอบแรกไม่ผ่าน
            if verification_result.get("all_ok"):
                self.app.update_log("ราคาตรงทั้งหมดตั้งแต่แรก ไม่ต้องตรวจสอบซ้ำ")
                post_verification = verification_result
                self.app.last_pricing_status = "TEST_SUCCESS (ราคาตรงตั้งแต่แรก/All OK)"
            else:
                self.app.update_log("🔍 กำลังตรวจสอบราคาและจำนวนสินค้าอีกครั้งหลังปรับราคา...")
                post_verification = self.bot.ProductManager.verify_all()
                print("post_verification_result (Round 2): ", post_verification)
                if post_verification.get("all_ok"):
                    self.app.last_pricing_status = "TEST_SUCCESS (ปรับราคาและใส่คูปองสำเร็จ/All OK)"
                else:
                    self.app.last_pricing_status = "TEST_FAILED (ตรวจสอบราคาไม่ผ่านหลังปรับ)"

            self.app.last_pricing_detail = self._format_pricing_detail(post_verification)

            if post_verification.get("all_ok"):
                self._log_price_verification_summary(post_verification)
                if self.app.is_testing:
                    self.app.update_log("🧪 TEST MODE: กรอกของและตรวจสอบสินค้า/ราคาผ่านแล้ว (All OK). หยุดก่อนกด finish_order()")
                    self.bot.current_checkpoint = "TEST MODE: ตรวจสินค้าผ่าน หยุดก่อน finish_order()"
                else:
                    self.app.update_log("✅ ตรวจสอบราคาสำเร็จและถูกต้อง (All OK). กำลังดำเนินการออกบิล...")
                    self.app.finish_order()
                    self.bot.current_checkpoint = "กรอก Skus ลง POS"

                # ตรวจสอบ Popup แจ้งเตือนขาด Serial
                if self.app.is_accel_mode.get() and self.app.is_auto_invoice_mode.get():
                    self._check_missing_serial_popups()
            else:
                self._handle_post_verification_failures(post_verification)

        except Exception as err:
            err_str = str(err).lower()
            if any(k in err_str for k in ["connection refused", "target machine actively refused it", "max retries exceeded", "winerror 10061"]):
                logger.error(f"Connection lost during items verification: {err}")
                self.app.update_log("⚠️ Session lost while adding items. Attempting to reconnect...")
                self.bot.reconnect_driver()
                self.app.update_log("⚠️ Reconnected. Please check the items manually.")
            else:
                logger.error(f"Error occurred while verifying items: {err}")
                self.bot.record_failed_with_checkpoint(str(err))
                raise err

    def _check_missing_serial_popups(self) -> None:
        """ตรวจสอบ Warning Popup และปุ่มสีแดง ng-redalert ในกรณีขาด Serial Number"""
        time.sleep(1.5)
        warning_popups = self.driver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'swal2-icon') and contains(@class, 'swal2-warning') and contains(@class, 'pulse-warning')]"
        )
        has_warning = any(
            "display: block" in (p.get_attribute("style") or "") or "display:block" in (p.get_attribute("style") or "")
            for p in warning_popups
        )

        if has_warning:
            err_msg = "พบป๊อปอัปแจ้งเตือน แต่ไม่พบข้อความผิดพลาด"
            for content in self.driver.find_elements(By.XPATH, "//div[contains(@class, 'swal2-content')]"):
                c_style = content.get_attribute("style") or ""
                if "display: block" in c_style or "display:block" in c_style:
                    err_msg = content.text
                    break

            if any(kw in err_msg.lower() for kw in ["please input serial", "กรุณาใส่ข้อมูลซีเรียล"]):
                pm = getattr(self.bot, "ProductManager", None)
                if pm:
                    qty_res = pm.verify_item_qty()
                    missing_lines = []
                    for sku, info in qty_res.items():
                        expected = int(info.get("expected", 0))
                        actual = info.get("actual", "NOT_FOUND")
                        if actual == "NOT_FOUND":
                            missing_lines.append(f"  • {sku}: ต้องการ {expected} ชิ้น แต่ไม่พบบน POS (ขาด SN)")
                        elif actual != expected:
                            missing_lines.append(f"  • {sku}: ต้องการ {expected} ชิ้น แต่ลงได้ {actual} (ขาด {expected - actual})")
                    if missing_lines:
                        err_msg += "\n\n📋 Item ที่น่าจะขาด SN:\n" + "\n".join(missing_lines)
                    else:
                        red_buttons = self.driver.find_elements(
                            By.XPATH, "//button[contains(@class, 'btn-serial') and contains(@class, 'ng-redalert')]"
                        )
                        sku_elems = self.driver.find_elements(
                            By.XPATH, "//span[(contains(@ng-click, 'productNameChangeChk(x)')) and not(contains(@class, 'ng-hide'))]//u"
                        )
                        red_alert_skus = []
                        for btn in red_buttons:
                            matched_sku = None
                            try:
                                panel = btn.find_element(By.XPATH, "./ancestor::div[contains(@class, 'panel')][1]")
                                sku_panel = panel.find_elements(By.XPATH, ".//span[contains(@ng-click, 'productNameChangeChk(x)')]//u")
                                if sku_panel:
                                    matched_sku = sku_panel[0].text.strip()
                            except Exception:
                                pass
                            if not matched_sku:
                                try:
                                    idx = red_buttons.index(btn)
                                    if idx < len(sku_elems):
                                        matched_sku = sku_elems[idx].text.strip()
                                except Exception:
                                    pass
                            red_alert_skus.append(matched_sku or "<ไม่ทราบ SKU>")

                        if red_alert_skus:
                            err_msg += "\n\n🔴 SKU ที่ยังค้างปุ่ม serial สีแดง:\n" + "\n".join(f"  • {s}" for s in red_alert_skus)

            try:
                swal_ok = self.driver.find_element(
                    By.XPATH, "//button[contains(@class, 'swal2-confirm') and (text()='OK' or text()='ตกลง')]"
                )
                if swal_ok.is_displayed():
                    self.driver.execute_script("arguments[0].click();", swal_ok)
            except Exception:
                pass

            self.app.update_log(f"❌ พบข้อผิดพลาดจากป๊อปอัป: {err_msg}")
            raise ValueError(err_msg)

    def _log_price_verification_summary(self, verification_res: dict) -> None:
        """พิมพ์สรุปรายงานผลการตรวจสอบราคาสินค้าแต่ละ SKU และยอดรวมทั้งหมดลง Log"""
        price_lines = []
        for sku, pinfo in verification_res.get("price", {}).items():
            expected = pinfo.get('expected', 0)
            actual = pinfo.get('actual', 0)
            is_ok = pinfo.get('ok', False)
            status_icon = "✅" if is_ok else "❌"
            
            try:
                exp_str = f"{float(expected):,.2f}"
            except Exception:
                exp_str = str(expected)
            try:
                act_str = f"{float(actual):,.2f}" if actual != "NOT_FOUND" else "ไม่พบสินค้าบน POS"
            except Exception:
                act_str = str(actual)

            price_lines.append(f"  • {sku}: บน POS = {act_str} บาท | ราคาที่ต้องออกบิล = {exp_str} บาท [{status_icon}]")

        total_info = verification_res.get("total", {})
        t_exp = total_info.get("expected", 0)
        t_act = total_info.get("actual", 0)
        t_ok = total_info.get("ok", False)
        t_icon = "✅" if t_ok else "❌"
        try:
            t_exp_str = f"{float(t_exp):,.2f}"
        except Exception:
            t_exp_str = str(t_exp)
        try:
            t_act_str = f"{float(t_act):,.2f}" if t_act != "NOT_FOUND" else "N/A"
        except Exception:
            t_act_str = str(t_act)

        summary_msg = (
            "📊 รายงานผลการตรวจสอบราคาสินค้าบน SMCO POS:\n" +
            "\n".join(price_lines) +
            f"\n  • ยอดรวมตระกร้าทั้งหมด (Grand Total): บน POS = {t_act_str} บาท | เป้าหมาย = {t_exp_str} บาท [{t_icon}]"
        )
        self.app.update_log(summary_msg)

    def _handle_post_verification_failures(self, post_verification: dict) -> None:
        """รวบรวม Error และแจ้งเตือนเมื่อการตรวจสอบรอบ 2 ยังไม่ผ่าน"""
        self._log_price_verification_summary(post_verification)
        qty_errors = [
            f"จำนวนไม่พอ: {sku} (expected {info.get('expected')}, actual {info.get('actual')})"
            for sku, info in post_verification.get("qty", {}).items() if not info.get("ok", True)
        ]
        price_errors = [
            f"SKU Price mismatch: {sku} (expected {info.get('expected')}, actual {info.get('actual')}, diff {info.get('diff')})"
            for sku, info in post_verification.get("price", {}).items() if not info.get("ok", True)
        ]
        total_res = post_verification.get("total", {})
        total_errors = (
            [f"Total Price mismatch (expected {total_res.get('expected')}, actual {total_res.get('actual')})"]
            if not total_res.get("ok", True) else []
        )

        all_errors = qty_errors + price_errors + total_errors
        error_msg = f"ราคา/จำนวนไม่ตรงหลังปรับราคา: " + " | ".join(all_errors)
        self.app.update_log(f"❌ {error_msg}")
        raise ValueError(error_msg)

    def _format_pricing_detail(self, verification_res: dict) -> str:
        """สร้างข้อความสรุปผลการปรับราคาแต่ละ SKU และผลลัพธ์ว่าตรงหรือไม่ตรง"""
        parts = []
        for sku, pinfo in verification_res.get("price", {}).items():
            expected = pinfo.get('expected', 0)
            actual = pinfo.get('actual', 0)
            is_ok = pinfo.get('ok', False)
            match_str = "ตรง ✅" if is_ok else f"ต่าง {pinfo.get('diff', 0):+,.2f} ❌"
            try:
                act_str = f"{float(actual):,.2f}" if actual != "NOT_FOUND" else "NOT_FOUND"
            except Exception:
                act_str = str(actual)
            try:
                exp_str = f"{float(expected):,.2f}"
            except Exception:
                exp_str = str(expected)
            parts.append(f"{sku}: POS={act_str}/เป้า={exp_str} [{match_str}]")

        total_info = verification_res.get("total", {})
        t_exp = total_info.get("expected", 0)
        t_act = total_info.get("actual", 0)
        t_ok = total_info.get("ok", False)
        t_match_str = "ตรง ✅" if t_ok else f"ต่าง {total_info.get('diff', 0):+,.2f} ❌"
        try:
            t_act_str = f"{float(t_act):,.2f}" if t_act != "NOT_FOUND" else "N/A"
        except Exception:
            t_act_str = str(t_act)
        try:
            t_exp_str = f"{float(t_exp):,.2f}"
        except Exception:
            t_exp_str = str(t_exp)

        parts.append(f"Total: POS={t_act_str}/เป้า={t_exp_str} [{t_match_str}]")
        return " | ".join(parts)

