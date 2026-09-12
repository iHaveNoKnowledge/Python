"""
Module: functions.pos.pricing_engine
Contains:
  - OrderFinancials: Single Source of Truth (SSOT) for order-level and item-level financial calculations.
  - POSPricingReconciler: Handles price mismatch detection, campaign coupon (CP) matching from Excel,
    overcharge (OC) / discount (DC) adjustments on the SMCO POS cart, and 2-step verification.
"""

from __future__ import annotations

import datetime
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from dateutil import parser
from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def parse_smart_date(val: Any) -> Optional[datetime.date]:
    """
    แปลงค่าวันที่หลากหลายรูปแบบให้กลายเป็น datetime.date มาตรฐานเดียวกัน
    รองรับ:
    - datetime.date, datetime.datetime, pd.Timestamp
    - รูปแบบ ISO (ปี 4 หลักขึ้นหน้า): '2026-09-01', '2026/09/01', '2026-09-01 0:00:00'
    - รูปแบบไทย/สากล (ปี 4 หลักลงท้าย): '7/9/2026', '07/09/2026', '7-9-2026', '30/09/2026'
    - ปี พ.ศ. (พุทธศักราช): '7/9/2569', '2569-09-07' -> แปลงเป็น ค.ศ. (ลบ 543)
    - ค่าว่าง / NaN / NaT -> คืนค่า None
    """
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime.date, datetime.datetime, pd.Timestamp)):
        return val.date() if hasattr(val, 'date') else val
    s = str(val).strip()
    if not s or s.lower() in ['nan', 'nat', 'none', '-']:
        return None
    try:
        match_be = re.search(r'\b(25\d{2})\b', s)
        if match_be:
            be_year = int(match_be.group(1))
            ce_year = be_year - 543
            s = s[:match_be.start(1)] + str(ce_year) + s[match_be.end(1):]
        if re.match(r'^\d{4}[-/.]', s):
            dt = parser.parse(s, yearfirst=True, dayfirst=False)
            return dt.date()
        dt = parser.parse(s, dayfirst=True)
        return dt.date()
    except Exception:
        try:
            p_dt = pd.to_datetime(s, format='mixed', dayfirst=True, errors='coerce')
            if pd.notna(p_dt):
                return p_dt.date()
        except Exception:
            pass
        return None


def is_valid_adjustment(amount_str: Any) -> bool:
    """ตรวจสอบว่าค่าการปรับราคา (OC/DC) มีตัวเลขที่ถูกต้องและมากกว่า 0 หรือไม่"""
    if not amount_str or str(amount_str).strip() == "" or str(amount_str).strip().upper() == "NONE":
        return False
    tokens = str(amount_str).split()
    for token in tokens:
        clean = token.replace('-', '').replace('+', '').split('.')[0].strip()
        if clean.isdigit() and int(clean) > 0:
            return True
    return False


def is_seller_voucher_desc(desc: Any) -> bool:
    """ตรวจสอบว่าคำอธิบายคูปองมีข้อความบ่งชี้ว่าเป็น Seller Voucher หรือไม่ (รองรับทั้งไทยและอังกฤษ ยืดหยุ่นต่อช่องว่างและตัวพิมพ์)"""
    if not desc or pd.isna(desc):
        return False
    normalized = re.sub(r'[\s_]+', '', str(desc)).lower()
    keywords = [
        "sellervoucher",
        "couponvoucher",
        "ส่วนลดผู้ขาย",
        "คูปองร้านค้า",
        "ส่วนลดร้านค้า",
        "shopvoucher",
        "storevoucher",
    ]
    return any(k in normalized for k in keywords)


def get_coupon_recency_score(code: str, desc: str = "") -> int:
    """
    คำนวณคะแนนความใหม่ของคูปอง SMCO เพื่อนำมาจัดเรียงจากใหม่สุดไปเก่าสุด (Latest First)
    รหัสคูปอง SMCO มักอยู่ในรูปแบบ CP/DC + YYMMDD + XXXX เช่น CP2609100001
    """
    if not code:
        return 0
    # ดึงตัวเลขลำดับจากรหัสคูปอง (เช่น CP2609100001 -> 2609100001)
    m = re.search(r'\d{6,10}', str(code))
    if m:
        try:
            return int(m.group(0))
        except Exception:
            pass

    # fallback: ดึงวันที่จากข้อความรายละเอียด (เช่น 10/09/2026)
    m_date = re.search(r'(\d{2})/(\d{2})/(\d{4})', f"{code} {desc}")
    if m_date:
        try:
            d, m_val, y = int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3))
            return (y % 100) * 100000000 + m_val * 1000000 + d * 10000
        except Exception:
            pass

    return 0




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

            # ตรวจสอบส่วนลดร้านค้าในระดับแถวสินค้า (ถ้ามี)
            raw_seller_v = str(item.get('โค้ดส่วนลดชำระโดยผู้ขาย', item.get('ส่วนลดจากร้านค้า', 0))).replace(',', '')
            row_seller_voucher = abs(float(raw_seller_v)) if raw_seller_v and raw_seller_v.lower() != 'nan' else 0.0

            if sku_key not in self.aggregated_items:
                self.aggregated_items[sku_key] = {
                    "total_qty": qty_val,
                    "total_price": price_val,
                    "total_discount": shopee_discount,
                    "total_seller_voucher": row_seller_voucher
                }
            else:
                self.aggregated_items[sku_key]["total_qty"] += qty_val
                self.aggregated_items[sku_key]["total_price"] += price_val
                self.aggregated_items[sku_key]["total_discount"] += shopee_discount
                self.aggregated_items[sku_key]["total_seller_voucher"] += row_seller_voucher

            total_net_sum += price_val + shopee_discount

        # หากในระดับแถวสินค้าไม่มี seller voucher ระบุไว้ แต่ระดับออเดอร์มี seller_voucher > 0
        total_item_level_voucher = sum(d.get("total_seller_voucher", 0.0) for d in self.aggregated_items.values())
        if total_item_level_voucher == 0.0 and self.seller_voucher > 0 and self.aggregated_items:
            # กรณีออเดอร์ทั่วไป (1 SKU หรือระบุรวม) ให้นำ seller_voucher ไปหักกับ SKU ที่มีมูลค่าสูงสุด
            target_sku = max(self.aggregated_items.keys(), key=lambda k: self.aggregated_items[k]["total_price"])
            self.aggregated_items[target_sku]["total_seller_voucher"] = float(self.seller_voucher)

        for sku_key, data in self.aggregated_items.items():
            t_qty = data["total_qty"] if data["total_qty"] > 0 else 1.0
            # ราคาเป้าหมายต่อหน่วยหลังหัก Seller Voucher (เพื่อให้จับคู่ CP ใน cp_data.xlsx และตรวจบน POS ถูกต้อง)
            v_amt = data.get("total_seller_voucher", 0.0)
            unit_expected = (data["total_price"] + data["total_discount"] - v_amt) / t_qty
            self.item_expected_prices[sku_key] = round(max(0.0, unit_expected), 2)

        self.sum_price = round(total_net_sum, 2)

        # คำนวณราคายอดรวมตะกร้าบน POS หลังหัก CP/Seller Voucher
        total_cart_items = sum(
            self.item_expected_prices[k] * self.aggregated_items[k]["total_qty"]
            for k in self.item_expected_prices
        )

        if self.marketplace.upper() == "SHOPEE":
            self.total_cart_price = round(total_cart_items + self.shipping_cost, 2)
            self.final_billing_price = max(0.0, round(self.sum_price + self.shipping_cost - self.seller_voucher, 2))
        else:  # LAZADA
            self.total_cart_price = round(total_cart_items, 2)
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

        # 1. Parse purchased date ด้วย Smart Date Parser
        purchased_date = parse_smart_date(purchased_date_str)
        if not purchased_date:
            print(f"[CP Lookup] Date parsing error for '{purchased_date_str}'")
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

        # 3. Filter by Date Range (เปรียบเทียบ datetime.date มาตรฐานเดียวกันทุกรูปแบบ)
        valid_rows = []
        date_rejected_reasons = []
        for idx, row in df_filtered.iterrows():
            try:
                start_date = parse_smart_date(row.get('usage_start_date'))
                end_date = parse_smart_date(row.get('usage_end_date'))

                in_range = True
                if start_date and end_date:
                    if not (start_date <= purchased_date <= end_date):
                        in_range = False
                elif start_date:
                    if not (start_date <= purchased_date):
                        in_range = False
                elif end_date:
                    if not (purchased_date <= end_date):
                        in_range = False

                if in_range:
                    valid_rows.append(row)
                else:
                    s_str = start_date.strftime('%d/%m/%Y') if start_date else 'N/A'
                    e_str = end_date.strftime('%d/%m/%Y') if end_date else 'N/A'
                    cp_code = row.get('cp_name', '')
                    price_val = row.get('sale_price', '')
                    date_rejected_reasons.append(f"CP: '{cp_code}' (ราคา {price_val}, ช่วงวัน: {s_str} - {e_str})")
            except Exception as date_err:
                print(f"[CP Lookup] Row date validation error at index {idx}: {date_err}")

        if not valid_rows:
            reasons_str = "; ".join(date_rejected_reasons) if date_rejected_reasons else "ไม่มีช่วงวันระบุ"
            print(f"[CP Lookup] SKU {sku} found, but date {purchased_date} is not within any CP usage range. (รายละเอียดช่วงวัน: {reasons_str})")
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
            df_price_matched['temp_start_date'] = df_price_matched['usage_start_date'].apply(parse_smart_date)
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

        # หากมีแถว candidate ใน Excel ให้ตัดแถวเปล่าที่ไม่มีข้อมูลใดๆ (ไม่มีทั้ง cp_name, oc_amount, dc_amount) ทิ้งทันที
        active_candidates = [
            c for c in candidates
            if c.get("cp_name") or is_valid_adjustment(c.get("oc_amount")) or is_valid_adjustment(c.get("dc_amount"))
            or str(c.get("cp_name")).strip().upper() in ["NONE", "BYPASS", "NO_CP", "NO CP", "PASSTHROUGH"]
        ]
        return active_candidates


    def find_cp_from_excel(self, sku: str, platform_price: float, purchased_date_str: str) -> Optional[dict]:
        """
        ค้นหา CP ชุดแรกจากไฟล์ cp_data.xlsx (Backward Compatibility)
        """
        candidates = self.find_all_cp_candidates_from_excel(sku, platform_price, purchased_date_str)
        return candidates[0] if candidates else None

    def add_missing_cp_to_excel(self, sku_key: str, expected_price: float, suggested_cp: str = "") -> None:
        """บันทึก SKU และราคาที่ยังไม่มี CP ลงไฟล์ Excel เพื่อให้กรอกข้อมูลต่อได้ พร้อมระบุคูปองแนะนำ (suggested_cp) ถ้ามี"""
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

            col_name = 'suggested_cp'
            if col_name not in df.columns:
                df[col_name] = ""

            sku_clean = str(sku_key).strip().upper()
            mask = (df['sku'].astype(str).str.strip().str.upper() == sku_clean) & ((df['sale_price'] - expected_price).abs() <= 0.05)

            if mask.any():
                # มีแถวเดิมอยู่แล้ว: อัปเดตคอลัมน์ suggested_cp ถ้ามีการระบุค่าแนะนำ
                if suggested_cp:
                    df.loc[mask, col_name] = suggested_cp
                df_combined = df
            else:
                new_row = {'sku': sku_key, 'sale_price': expected_price, col_name: suggested_cp}
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

            log_sugg = f" (แนะนำ: {suggested_cp})" if suggested_cp else ""
            self.app.update_log(
                f"💾 บันทึก SKU: {sku_key} (ราคาเป้าหมาย: {expected_price}){log_sugg} ลงใน CP Data เรียบร้อยแล้ว"
            )

            if self.app.cp_df is not None:
                if 'suggested_cp' not in self.app.cp_df.columns:
                    self.app.cp_df['suggested_cp'] = ""
                if mask.any() and suggested_cp:
                    self.app.cp_df.loc[mask, col_name] = suggested_cp
                elif not mask.any():
                    if 'usage_start_date' in new_df.columns:
                        new_df['usage_start_date'] = new_df['usage_start_date'].apply(parse_smart_date)
                    if 'usage_end_date' in new_df.columns:
                        new_df['usage_end_date'] = new_df['usage_end_date'].apply(parse_smart_date)
                    self.app.cp_df = pd.concat([self.app.cp_df, new_df], ignore_index=True)

        except Exception as err:
            print(f"[add_missing_cp_to_excel] Error appending row: {err}")

    def find_suggested_cp_for_discount(self, target_discount: float, require_seller_voucher: bool = False) -> Optional[dict]:
        """
        คำนวณหาคูปอง (ตัวเดียว หรือคู่ผสม) จากรายการคูปองที่สแกนได้บนหน้าเว็บ SMCO
        ที่มีมูลค่าส่วนลดตรงกับ target_discount พอดี (ความคลาดเคลื่อน <= 0.05 บาท)
        หาก require_seller_voucher=True จะพิจารณาเฉพาะคูปองที่มีข้อความบ่งชี้ว่าเป็น Seller Voucher เท่านั้น
        โดยจะแนะนำคูปองที่ใหม่ที่สุด (Latest First) เสมอ
        """
        details = getattr(self, 'last_scanned_smco_coupon_details', [])
        if not details or target_discount <= 0:
            return None

        # 1. ตรวจสอบคูปองเดี่ยว (Single Coupon) - รวบรวมทั้งหมดแล้วเลือกตัวที่ใหม่ที่สุด
        matching_singles = []
        for c in details:
            if require_seller_voucher and not is_seller_voucher_desc(c.get("desc", "")):
                continue
            if abs(c['discount'] - target_discount) <= 0.05 and c['discount'] > 0:
                matching_singles.append({
                    "suggested_code": c['code'],
                    "discount": c['discount'],
                    "type": "single",
                    "score": get_coupon_recency_score(c.get('code', ''), c.get('desc', ''))
                })

        # 2. ตรวจสอบคูปองคู่ผสม (Combination เช่น CP 1 ตัว + DC 1 ตัว หรือ CP 2 ตัว)
        matching_combos = []
        for i in range(len(details)):
            for j in range(i + 1, len(details)):
                c1 = details[i]
                c2 = details[j]
                if require_seller_voucher:
                    has_sv = is_seller_voucher_desc(c1.get("desc", "")) or is_seller_voucher_desc(c2.get("desc", ""))
                    if not has_sv:
                        continue
                total_disc = c1['discount'] + c2['discount']
                if abs(total_disc - target_discount) <= 0.05 and total_disc > 0:
                    s1 = get_coupon_recency_score(c1.get('code', ''), c1.get('desc', ''))
                    s2 = get_coupon_recency_score(c2.get('code', ''), c2.get('desc', ''))
                    combo_score = max(s1, s2)
                    matching_combos.append({
                        "suggested_code": f"{c1['code']} {c2['code']}",
                        "discount": total_disc,
                        "type": "combo",
                        "score": combo_score
                    })

        best = None
        if matching_singles:
            matching_singles.sort(key=lambda x: x["score"], reverse=True)
            best = matching_singles[0]
        elif matching_combos:
            matching_combos.sort(key=lambda x: x["score"], reverse=True)
            best = matching_combos[0]

        if not best:
            return None

        # ตรวจสอบคูปองที่เป็นค่าเริ่มต้น (Pre-selected coupons บน SMCO)
        preselected = getattr(self, 'last_preselected_smco_coupons', None)
        if preselected is None:
            preselected = []
            for c in details:
                if c.get("is_selected") and c.get("code") and c.get("code") not in preselected:
                    preselected.append(c.get("code"))

        # ดึงรหัส preselected ที่มีอยู่เดิมบนหน้าเว็บ (เช่น Default CP หรือ DC) โดยไม่ใส่ซ้ำกับคูปองใหม่ที่แนะนำ
        if preselected:
            new_tokens = [tok.strip().upper() for tok in best["suggested_code"].split()]
            pre_codes = [p for p in preselected if p.strip().upper() not in new_tokens]
            if pre_codes:
                final_code = f"{' '.join(pre_codes)} {best['suggested_code']}"
            else:
                final_code = best["suggested_code"]
        else:
            final_code = best["suggested_code"]
            pre_codes = []

        return {
            "suggested_code": final_code,
            "preselected_codes": pre_codes,
            "new_code": best["suggested_code"],
            "discount": best["discount"],
            "type": best["type"]
        }


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
                # * คลิกปุ่ม coupon เพื่อเปิดหน้ารายการ coupon (มี retry ด้วย Selenium ปกติ)
                modal_opened = False
                for attempt in range(2):
                    try:
                        item_list_cp_btn_elements = self.driver.find_elements(
                            By.XPATH, "//button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]"
                        )
                        if target_idx >= len(item_list_cp_btn_elements):
                            print(f"ดึงปุ่ม coupon ของ {item} ไม่สำเร็จ (index เกินรายการ)")
                            break

                        cp_btn_xpath = item_list_cp_btn_elements[target_idx]
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", cp_btn_xpath)
                        except Exception:
                            pass
                        cp_btn_xpath.click()

                        # ตรวจสอบว่า modal เปิดขึ้นมาจริง
                        for _ in range(8):
                            c_btns = self.driver.find_elements(By.XPATH, selected_cp_btn_loc)
                            if c_btns and any(b.is_displayed() for b in c_btns):
                                modal_opened = True
                                break
                            time.sleep(0.05)

                        if modal_opened:
                            break
                    except Exception:
                        time.sleep(0.05)

                if not modal_opened:
                    print(f"ไม่สามารถเปิดหน้าต่างคูปองของ {item} ได้")
                    continue

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
                        target_btn = cp_btn_elements[target_btn_idx]
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", target_btn)
                        except Exception:
                            pass
                        target_btn.click()
                        time.sleep(0.1)  # * รอให้ UI อัพเดท

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

                # รอให้ modal และ backdrop ปิดสนิท (ไม่หลงเหลือ backdrop ที่บังคลิกรายการถัดไป)
                for _ in range(8):
                    backdrops = self.driver.find_elements(
                        By.CSS_SELECTOR, 'body > div.modal-backdrop, .modal-backdrop, div.modal.in, div.modal.show'
                    )
                    if not any(b.is_displayed() for b in backdrops):
                        break
                    time.sleep(0.05)

            except Exception as err:
                print("Demonic CP Bot inner Exception Error:", err)
                try:
                    agree_btns = self.driver.find_elements(By.CSS_SELECTOR, green_agree_btn_xpath)
                    if agree_btns and agree_btns[0].is_displayed():
                        agree_btns[0].click()
                except Exception:
                    pass
                for _ in range(8):
                    backdrops = self.driver.find_elements(By.CSS_SELECTOR, 'body > div.modal-backdrop, .modal-backdrop')
                    if not any(b.is_displayed() for b in backdrops):
                        break
                    time.sleep(0.05)

        print(f"เลือก coupon เสร็จสิ้น: {cp_target_names}")
        return any_success

    def get_existing_panel_coupons(self, item_no_1indexed: int) -> list:
        """ดึงรหัสคูปอง (CP/DC) ที่ปรากฏอยู่บน Item Panel ของสินค้านั้นบนหน้า POS Cart"""
        found_codes = []
        try:
            panels = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
            if 1 <= item_no_1indexed <= len(panels):
                target_panel = panels[item_no_1indexed - 1]
                # 1. จาก tooltip elements
                tooltip_elements = target_panel.find_elements(By.XPATH, ".//a[@data-toggle='tooltip'] | .//*[@data-toggle='tooltip']")
                for el in tooltip_elements:
                    text = el.text or ""
                    title = el.get_attribute("title") or el.get_attribute("data-original-title") or ""
                    combined = f"{text} {title}".upper()
                    matches = re.findall(r'\b((?:CP|DC)\d+)\b', combined)
                    for m in matches:
                        if m not in found_codes:
                            found_codes.append(m)

                # 2. จากข้อความทั้งหมดใน panel ที่มี pattern CP/DC
                panel_text = target_panel.text or ""
                matches = re.findall(r'\b((?:CP|DC)\d+)\b', panel_text.upper())
                for m in matches:
                    if m not in found_codes:
                        found_codes.append(m)
        except Exception as e:
            print(f"[get_existing_panel_coupons] Error: {e}")
        return found_codes

    def scan_matching_cp_candidates_on_smco(self, item_no: int, cp_candidates: list, required_seller_voucher: float = 0.0) -> list:
        """
        สแกนดูคูปองทั้งหมดบนหน้าต่าง Modal ของ SMCO แล้วจับคู่กับ cp_candidates
        ส่งกลับ list ของ candidate ที่พบคูปองบนหน้าเว็บ SMCO จริง (หรือ candidate ที่ไม่จำเป็นต้องใช้ CP)
        หากระบุ required_seller_voucher > 0 จะบังคับว่า candidate นั้นต้องมีคูปอง Seller Voucher ที่มีมูลค่าตรงกันพอดี
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
            # ดึงรหัสคูปองเริ่มต้น (Default CP/DC) ที่ติดอยู่บน Item Panel บน POS Cart ก่อนเปิด Modal
            panel_codes = self.get_existing_panel_coupons(item_no)

            item_list_cp_btn_elements = self.driver.find_elements(
                By.XPATH, "//button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]"
            )
            if target_idx >= len(item_list_cp_btn_elements):
                return []

            # เปิด Modal ดูรายการคูปองที่มีบนหน้าเว็บ
            scan_btn = item_list_cp_btn_elements[target_idx]
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", scan_btn)
            except Exception:
                pass
            scan_btn.click()

            for _ in range(8):
                cp_name_elements = self.driver.find_elements(By.XPATH, cp_name_loc)
                if cp_name_elements and any(b.is_displayed() for b in cp_name_elements):
                    break
                time.sleep(0.05)

            cp_name_elements = self.driver.find_elements(By.XPATH, cp_name_loc)
            smco_coupon_names = [el.text.replace(" ", "").upper() for el in cp_name_elements if el.text.strip()]
            self.last_scanned_smco_coupons = [el.text.strip() for el in cp_name_elements if el.text.strip()]

            # ดึงรายการคูปองพร้อมส่วนลดและคำอธิบายจาก XPath ที่ระบุ
            scanned_details = []
            try:
                list_items = self.driver.find_elements(
                    By.XPATH, "//div[contains(@ng-show, 'posbook.data.cnFormPaymentId===undefined')]/div[contains(@class,'row list-group-item ng-scope')]"
                )
                if not list_items:
                    list_items = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'row list-group-item')]")

                for item_el in list_items:
                    # 1. ค้นหารหัสคูปอง (Coupon Code)
                    name_spans = item_el.find_elements(
                        By.XPATH, ".//span[@class='text-primary price-sku-h1 ng-binding' or contains(@class,'price-sku-h1')]"
                    )
                    c_name = name_spans[0].text.strip() if name_spans else ""
                    item_text_str = str(item_el.text) if hasattr(item_el, 'text') and not isinstance(item_el.text, MagicMock if 'MagicMock' in globals() else type(None)) else ""
                    if not item_text_str and hasattr(item_el, 'text') and isinstance(item_el.text, str):
                        item_text_str = item_el.text

                    if not c_name and item_text_str:
                        m_code = re.search(r'\b(CP\d+|DC\d+)\b', item_text_str)
                        if m_code:
                            c_name = m_code.group(1)

                    # 2. ค้นหาคำอธิบายและ Remark (Description)
                    c_desc = ""
                    desc_spans = item_el.find_elements(
                        By.XPATH, ".//span[@ng-show='pmt.couponDesc !== undefined' or contains(@class,'font-color-secondary')]"
                    )
                    for ds in desc_spans:
                        t = ds.text.strip() if hasattr(ds, 'text') and isinstance(ds.text, str) else str(getattr(ds, 'text', ''))
                        if t:
                            c_desc = t
                            if is_seller_voucher_desc(t):
                                break

                    # หากหา xpath แรกไม่เจอ หรือข้อความไม่ใช่ Seller Voucher ให้ตรวจที่ fallback xpath
                    if not c_desc or not is_seller_voucher_desc(c_desc):
                        fallback_desc_spans = item_el.find_elements(
                            By.XPATH, ".//span[contains(@ng-show, 'couponDetailRemark') or contains(@class, 'font-color')]"
                        )
                        for fb_el in fallback_desc_spans:
                            fb_text = fb_el.text.strip() if hasattr(fb_el, 'text') and isinstance(fb_el.text, str) else str(getattr(fb_el, 'text', ''))
                            if fb_text:
                                if not c_desc or is_seller_voucher_desc(fb_text):
                                    c_desc = fb_text
                                    if is_seller_voucher_desc(fb_text):
                                        break

                    # ตรวจสอบเพิ่มเติมจากบรรทัดทั้งหมดใน item_text_str (ดักจับคำว่า coupon voucher / seller voucher)
                    if not is_seller_voucher_desc(c_desc) and item_text_str:
                        for line_t in item_text_str.split('\n'):
                            if is_seller_voucher_desc(line_t):
                                c_desc = line_t.strip()
                                break

                    # 3. ค้นหามูลค่าส่วนลด (Discount Amount)
                    disc_val = 0.0
                    disc_text = ""

                    # วิธีที่ 1: ค้นหาจาก span หรือข้อความที่มีรูปแบบ "ตัวเลข.-" (เช่น 200.-, 400.-) ซึ่งเป็นรูปแบบเฉพาะของส่วนลด SMCO
                    amount_spans = item_el.find_elements(
                        By.XPATH, ".//span[contains(text(), '.-') or contains(@class, 'text-danger')]"
                    )
                    for asp in amount_spans:
                        t = asp.text.strip() if hasattr(asp, 'text') and isinstance(asp.text, str) else str(getattr(asp, 'text', ''))
                        m_amt = re.search(r'([\d,]+(?:\.\d+)?)\s*\.-', t)
                        if m_amt:
                            disc_text = t
                            disc_val = float(m_amt.group(1).replace(',', ''))
                            break

                    # วิธีที่ 2: ค้นหารูปแบบ "ตัวเลข.-" จาก item_text_str ทั้งหมด
                    if disc_val == 0.0 and item_text_str:
                        m_amt = re.search(r'([\d,]+(?:\.\d+)?)\s*\.-', item_text_str)
                        if m_amt:
                            disc_text = m_amt.group(0)
                            disc_val = float(m_amt.group(1).replace(',', ''))

                    # วิธีที่ 3: fallback สำหรับกรณีไม่มี ".-"
                    if disc_val == 0.0:
                        disc_spans = item_el.find_elements(
                            By.XPATH, ".//div[@class='col-xs-12']/span[@class='ng-binding'] | .//div[contains(@class,'col-xs-12')]/span[contains(@class,'ng-binding')]"
                        )
                        disc_text = disc_spans[0].text.strip() if disc_spans and hasattr(disc_spans[0], 'text') and isinstance(disc_spans[0].text, str) else ""
                        cleaned = disc_text.replace(',', '')
                        m = re.search(r'(\d+(?:\.\d+)?)', cleaned)
                        if m:
                            try:
                                disc_val = float(m.group(1))
                            except Exception:
                                disc_val = 0.0

                    # 4. ตรวจสอบสถานะการเลือกของคูปอง:
                    # - คูปองที่ถูกเลือกแล้ว: ปุ่มสีน้ำเงินเขียนว่า "Selected", หรือมี class "btn-primary", หรือมีคำว่า "เลือกแล้ว"
                    # - คูปองอัตโนมัติ (Default/Auto): แสดงคำว่า "Auto" หรือ "อัตโนมัติ" (อาจไม่มีแท็ก button)
                    # - คูปองที่ยังไม่ถูกเลือก: ปุ่มสีขาวเขียนว่า "Un select" (หรือมี class btn-default)
                    is_sel = False
                    try:
                        # 4.1 ตรวจสอบว่าตรงกับคูปองที่ติดอยู่บน Item Panel ของสินค้าหรือไม่
                        if c_name and c_name in panel_codes:
                            is_sel = True

                        # 4.2 ตรวจสอบ class btn-primary โดยตรง
                        if not is_sel:
                            primary_btns = item_el.find_elements(
                                By.XPATH, ".//button[contains(@class, 'btn-primary')]"
                            )
                            if primary_btns and any(b.is_displayed() for b in primary_btns):
                                is_sel = True
                            elif primary_btns:
                                is_sel = True

                        # 4.3 ตรวจสอบสถานะ Auto (คูปองระบบคำนวณให้อัตโนมัติตั้งแต่ต้น)
                        if not is_sel:
                            item_raw_text = item_el.text if hasattr(item_el, 'text') and isinstance(item_el.text, str) else ""
                            auto_elements = item_el.find_elements(
                                By.XPATH, ".//*[contains(text(), 'Auto') or contains(text(), 'auto') or contains(text(), 'อัตโนมัติ')]"
                            )
                            if auto_elements and any(a.is_displayed() for a in auto_elements):
                                is_sel = True
                            elif re.search(r'\bAuto\b', item_raw_text, re.IGNORECASE):
                                is_sel = True

                        # 4.4 ตรวจสอบปุ่มในแถว
                        if not is_sel:
                            btn_elements = item_el.find_elements(By.XPATH, ".//button")
                            for btn in btn_elements:
                                b_text = btn.text.strip() if hasattr(btn, 'text') and isinstance(btn.text, str) else ""
                                b_class = btn.get_attribute("class") or ""

                                # หากเป็น Un select แปลว่ายังไม่ถูกเลือก
                                if "un select" in b_text.lower() or "unselect" in b_text.lower():
                                    is_sel = False
                                    break

                                # หากเป็น Selected หรือ class btn-primary หรือมีคำว่าเลือกแล้ว
                                if "selected" in b_text.lower() or "เลือกแล้ว" in b_text.lower() or "btn-primary" in b_class:
                                    is_sel = True
                                    break

                        # 4.5 Fallback จากข้อความในแถว (บรรทัดแรกๆ เช่น "Selected", "Auto")
                        if not is_sel and item_raw_text:
                            first_lines = item_raw_text.split('\n')[:3]
                            for line in first_lines:
                                line_clean = line.strip().lower()
                                if "un select" in line_clean or "unselect" in line_clean:
                                    is_sel = False
                                    break
                                if line_clean == "selected" or line_clean.startswith("selected") or line_clean == "auto":
                                    is_sel = True
                                    break
                    except Exception as ex_sel:
                        print(f"[scan_matching_cp_candidates_on_smco] Error checking is_selected: {ex_sel}")

                    if c_name:
                        scanned_details.append({
                            "code": c_name,
                            "discount": disc_val,
                            "desc": c_desc,
                            "raw_discount": disc_text,
                            "is_selected": is_sel
                        })
            except Exception as e:
                print(f"[scan_matching_cp_candidates_on_smco] Error scraping coupon details: {e}")

            self.last_scanned_smco_coupon_details = scanned_details
            preselected = []
            for sc in scanned_details:
                if sc.get("is_selected") and sc.get("code") and sc.get("code") not in preselected:
                    preselected.append(sc.get("code"))

            # รวมคูปองเริ่มต้น (Default CP/DC) ที่ติดอยู่บน Item Panel ของสินค้าบนหน้า POS Cart
            for pc in panel_codes:
                if pc and pc not in preselected:
                    preselected.append(pc)

            self.last_preselected_smco_coupons = preselected

            # ปิด Modal ชั่วคราว (ยังไม่เลือก)
            try:
                agree_btns = self.driver.find_elements(By.CSS_SELECTOR, green_agree_btn_xpath)
                if agree_btns and agree_btns[0].is_displayed():
                    agree_btns[0].click()
            except Exception:
                pass

            for _ in range(8):
                backdrops = self.driver.find_elements(By.CSS_SELECTOR, 'body > div.modal-backdrop, .modal-backdrop')
                if not any(b.is_displayed() for b in backdrops):
                    break
                time.sleep(0.05)

            # ตรวจสอบ Candidate แต่ละชุดว่ามีคูปองอยู่บนหน้าเว็บ SMCO จริงไหม
            matched_candidates = []
            for cand in cp_candidates:
                cp_name = cand.get("cp_name", "")
                is_bypass = str(cp_name).strip().upper() in ["NONE", "BYPASS", "NO_CP", "NO CP", "PASSTHROUGH"]
                has_oc = is_valid_adjustment(cand.get("oc_amount", ""))
                has_dc = is_valid_adjustment(cand.get("dc_amount", ""))
                has_cp = bool(cp_name and not is_bypass and str(cp_name).strip() != "")

                # หากไม่มีทั้ง CP, OC, DC และไม่ใช่ Bypass (แถวว่างเปล่าทั้งหมด) -> ข้ามทันที
                if not (has_cp or is_bypass or has_oc or has_dc):
                    continue

                # หากมีการบังคับ Seller Voucher (required_seller_voucher > 0)
                # candidate จะต้องมีคูปอง (has_cp ต้องเป็นจริง ไม่ใช่ bypass หรือ oc/dc ล้วน)
                if required_seller_voucher > 0 and (not has_cp or is_bypass):
                    continue

                if not cp_name or is_bypass or str(cp_name).strip() == "":
                    # ชุดที่ไม่มีคูปอง (มีแต่ OC/DC หรือ bypass) ถือว่า match ได้
                    matched_candidates.append(cand)
                else:
                    raw_tokens = [t.strip().upper() for part in str(cp_name).split(',') for t in part.split() if t.strip()]
                    all_tokens_in_smco = True
                    has_matching_seller_voucher_token = False

                    for token in raw_tokens:
                        token_clean = token.replace(" ", "")
                        found = False
                        token_is_matching_sv = False

                        if token.isdigit():
                            target_i = int(token) - 1
                            if 0 <= target_i < len(smco_coupon_names):
                                found = True
                                if 0 <= target_i < len(scanned_details):
                                    sc_item = scanned_details[target_i]
                                    if is_seller_voucher_desc(sc_item.get("desc", "")) and abs(sc_item.get("discount", 0.0) - required_seller_voucher) <= 0.05:
                                        token_is_matching_sv = True
                        else:
                            for idx_el, elem_name in enumerate(smco_coupon_names):
                                if token_clean in elem_name:
                                    found = True
                                    if idx_el < len(scanned_details):
                                        sc_item = scanned_details[idx_el]
                                        if is_seller_voucher_desc(sc_item.get("desc", "")) and abs(sc_item.get("discount", 0.0) - required_seller_voucher) <= 0.05:
                                            token_is_matching_sv = True
                                    break

                        if not found:
                            all_tokens_in_smco = False
                            break

                        if token_is_matching_sv:
                            has_matching_seller_voucher_token = True

                    # หากต้องการ Seller Voucher แต่ไม่มี token ไหนเป็น Seller Voucher ที่มูลค่าตรง -> ไม่ผ่าน
                    if required_seller_voucher > 0 and not has_matching_seller_voucher_token:
                        all_tokens_in_smco = False

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

    def find_and_apply_seller_voucher_on_smco(self, item_no: int, required_seller_voucher: float, cp_candidates: list = None, require_candidate_match: bool = True) -> tuple[bool, str, Optional[dict]]:
        """
        [Phase 1: Seller Voucher]
        สแกนคูปองบนหน้าเว็บ SMCO และค้นหาคูปองที่มีคำว่า 'Seller Voucher' และมีส่วนลดตรงกับ required_seller_voucher พอดี
        - หากพบตรงเงื่อนไข:
          1. ตรวจสอบว่าใน cp_candidates มีการระบุรหัสคูปองตัวใดไว้ใน cp_name หรือไม่ -> ถ้ามี ให้เลือกรหัสนั้นและสั่งเลือกใช้งาน
          2. หากไม่มีใน cp_candidates:
             - หาก require_candidate_match=True: จะไม่เลือกใช้งานสุ่มสี่สุ่มห้า และส่งคืน status="UNCONFIGURED" เพื่อให้หยุดแนะนำให้ผู้ใช้ตรวจสอบก่อน
             - หาก require_candidate_match=False: เลือกตัวที่ใหม่ที่สุด (Latest First) จากคะแนน recency score

        Returns:
            (success: bool, status: str, coupon_info: Optional[dict])
            status สามารถเป็น: 'APPLIED', 'NOT_FOUND', 'UNCONFIGURED', 'ERROR'
        """
        try:
            # สแกนคูปองบน SMCO เพื่อดึงรายละเอียดลง self.last_scanned_smco_coupon_details
            self.scan_matching_cp_candidates_on_smco(item_no, [], required_seller_voucher=0.0)
            details = getattr(self, 'last_scanned_smco_coupon_details', [])
            print(f"[find_and_apply_seller_voucher_on_smco] Scanned {len(details)} coupons: {details}")

            matching_sv = []
            for d in details:
                if is_seller_voucher_desc(d.get("desc", "")) and abs(d.get("discount", 0.0) - required_seller_voucher) <= 0.05:
                    matching_sv.append(d)

            # เรียงลำดับให้คูปองที่ใหม่ที่สุดขึ้นมาก่อนเสมอ
            matching_sv.sort(
                key=lambda x: get_coupon_recency_score(x.get('code', ''), x.get('desc', '')),
                reverse=True
            )

            if len(matching_sv) == 0:
                print(f"[find_and_apply_seller_voucher_on_smco] No matching seller voucher found for amount {required_seller_voucher}. Available details: {details}")
                return False, "NOT_FOUND", None

            # ตรวจสอบว่าใน cp_candidates มีการระบุคูปองตัวใดตัวหนึ่งใน matching_sv ไว้แล้วหรือไม่
            chosen = None
            if cp_candidates:
                for cand in cp_candidates:
                    cp_str = str(cand.get("cp_name", "")).upper()
                    cand_tokens = [tok.strip() for part in cp_str.split(',') for tok in part.split() if tok.strip()]
                    for sv in matching_sv:
                        if sv.get("code", "").upper() in cand_tokens:
                            chosen = sv
                            print(f"[find_and_apply_seller_voucher_on_smco] Matched Seller Voucher from cp_candidates: {chosen['code']}")
                            break
                    if chosen:
                        break

            # หากไม่พบที่ระบุใน cp_candidates
            if not chosen:
                chosen = matching_sv[0]
                if require_candidate_match:
                    print(f"[find_and_apply_seller_voucher_on_smco] Seller voucher {chosen['code']} found on SMCO but NOT configured in cp_candidates. Halting for user verification.")
                    return False, "UNCONFIGURED", chosen

                if len(matching_sv) > 1:
                    print(f"[find_and_apply_seller_voucher_on_smco] Multiple matching vouchers ({[m['code'] for m in matching_sv]}), auto-selecting newest: {chosen['code']}")

            cp_code = chosen.get("code", "")
            ok = self.cp_sonic_blow_process(item_no, cp_code)
            if ok:
                return True, "APPLIED", chosen
            else:
                return False, "ERROR", chosen
        except Exception as e:
            print(f"[find_and_apply_seller_voucher_on_smco] Error: {e}")
            return False, "ERROR", None

    def smco_set_overcharge_product(self, items_user_input: str = None, oc_amounts_input: str = None) -> None:
        """ปรับราคาขึ้น (Overcharge) สำหรับ SKU ที่ต้องการ"""
        if items_user_input is None or oc_amounts_input is None:
            return

        formatted_items_to_oc = self.sku_formater(items_user_input).split(" ")
        oc_amounts_list_prog = str(oc_amounts_input).split()
        oc_amounts_list = [float(self.oc_amounts_calculator(a)) for a in oc_amounts_list_prog]
        items_list_element = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')

        for idx, item in enumerate(formatted_items_to_oc):
            oc_amount = oc_amounts_list[0]
            if len(oc_amounts_list) > 1 and idx < len(oc_amounts_list):
                oc_amount = oc_amounts_list[idx]

            if oc_amount > 0:
                sku_variants = [item]
                try:
                    sku_variants = self.app.correct_sku_pattern(item)
                except Exception:
                    pass

                found_panel = False
                for idx2, div in enumerate(items_list_element):
                    try:
                        div_text = div.text
                        if any(variant in div_text for variant in sku_variants):
                            found_panel = True
                            li_loc = idx2 + 1
                            srp_btn_css = f'.col-sm-12.panel.panel-default.ng-scope:nth-child({li_loc}) div.panel-body:nth-child(1) div.row.col-sm-6:nth-child(2) > div:nth-child(1) div:nth-child(1) div a:nth-child(1)'
                            self.driver.find_element(By.CSS_SELECTOR, srp_btn_css).click()
                            time.sleep(0.5)

                            # รอให้ Modal เปลี่ยนราคาเปิดและช่องกรอกราคาแสดงขึ้นมา
                            change_price_input = self.wait50.until(
                                EC.visibility_of_element_located((By.XPATH, "//input[@ng-keyup='onPistive(oms)']"))
                            )
                            time.sleep(0.3)
                            based_price = self.driver.execute_script("return angular.element(arguments[0]).val();", change_price_input)
                            new_price = float(str(based_price).replace(",", "")) + float(oc_amount)

                            self.driver.execute_script(
                                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                                change_price_input, 0)
                            self.driver.execute_script(
                                "angular.element(arguments[0]).val(arguments[1]).triggerHandler('input')",
                                change_price_input, new_price)

                            # รอช่องกรอก User ID
                            user_id_input = self.wait50.until(
                                EC.visibility_of_element_located((By.XPATH, "//div[@id='modalChageProductPrice']//input[@ng-model='oms.currentApprUser'] | //input[@ng-model='oms.currentApprUser' and @title]"))
                            )
                            self.bot.js_input_value(user_id_input, self.app.user_id.get())

                            # รอช่องกรอก Password
                            user_pw_input = self.wait50.until(
                                EC.visibility_of_element_located((By.XPATH, "//div[@id='modalChageProductPrice']//input[@ng-model='oms.currentApprPassword' and @type='password']"))
                            )
                            self.bot.js_input_value(user_pw_input, self.app.user_pw.get())

                            # รอช่องกรอก Note
                            note_textarea = self.wait50.until(
                                EC.visibility_of_element_located((By.XPATH, "//div[@id='modalChageProductPrice']//textarea"))
                            )
                            self.bot.js_input_value(note_textarea, "Online")

                            # รอและกดปุ่มยืนยัน
                            green_submit_btn = self.wait50.until(
                                EC.element_to_be_clickable((By.XPATH, "//a[@class='btn btn-success text-center' and @ng-click='okChagePriceProduct()']"))
                            )
                            time.sleep(0.3)
                            self.driver.execute_script("arguments[0].click();", green_submit_btn)

                            try:
                                self.wait50.until(EC.invisibility_of_element_located(
                                    (By.XPATH, "//a[@class='btn btn-success text-center' and @ng-click='okChagePriceProduct()']")))
                            except Exception:
                                time.sleep(1)
                            break
                    except Exception as err:
                        err_msg = f"การปรับราคาขึ้น (Overcharge) สำหรับ SKU: {item} ผิดพลาด: {err}"
                        logger.error(f"Order: {self.bot.cus_order}: {err_msg}")
                        self.app.update_log(f"❌ {err_msg}")
                        raise ValueError(err_msg)

                if not found_panel:
                    err_msg = f"การปรับราคาขึ้น (Overcharge) ผิดพลาด: ไม่พบสินค้า SKU: {item} บนหน้าเว็บ SMCO"
                    logger.error(f"Order: {self.bot.cus_order}: {err_msg}")
                    self.app.update_log(f"❌ {err_msg}")
                    raise ValueError(err_msg)

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

    def apply_candidate_coupons_if_missing(self, item_no_1indexed: int, sku_key: str, cp_name: str) -> bool:
        """ตรวจสอบคูปองที่ถูกเลือกไว้แล้วบนหน้าเว็บ SMCO และเลือกเฉพาะคูปองที่ยังขาดอยู่ตาม cp_name"""
        if not cp_name or str(cp_name).strip().upper() in ["NONE", "BYPASS", "NO_CP", "NO CP", "PASSTHROUGH"]:
            return True

        sku_variants = [sku_key]
        try:
            sku_variants = self.app.correct_sku_pattern(sku_key)
        except Exception:
            pass

        panels = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
        target_panel = None
        for panel in panels:
            panel_text = panel.text
            if any(variant in panel_text for variant in sku_variants):
                target_panel = panel
                break

        existing_cps = []
        if target_panel:
            tooltip_elements = target_panel.find_elements(By.XPATH, ".//a[@data-toggle='tooltip']")
            for el in tooltip_elements:
                text = el.text or ""
                title = el.get_attribute("title") or ""
                combined = (text + " " + title).replace(" ", "").upper()
                existing_cps.append(combined)

        target_tokens = []
        for part in str(cp_name).split(','):
            for token in part.split():
                tok = token.strip().upper()
                if tok:
                    target_tokens.append(tok)

        missing_tokens = []
        for token in target_tokens:
            matched = False
            for existing in existing_cps:
                if token in existing:
                    matched = True
                    break
            if not matched:
                missing_tokens.append(token)

        if not missing_tokens:
            self.app.update_log(f"✨ คูปอง {cp_name} สำหรับ SKU: {sku_key} ถูกเลือกไว้ครบก่อนแล้ว ข้ามการเลือกซ้ำ")
            return True

        missing_cp_str = " ".join(missing_tokens)
        self.app.update_log(f"✅ คูปองที่ยังไม่ถูกเลือกคือ: {missing_cp_str} กำลังดำเนินการแอดคูปอง...")
        return self.cp_sonic_blow_process(item_no_1indexed, missing_cp_str)

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

        # ตรวจสอบสถานะโหมด Auto Invoice และยอด Seller Voucher ของออเดอร์
        is_auto_inv = False
        try:
            if hasattr(self.app, 'is_auto_invoice_mode') and hasattr(self.app.is_auto_invoice_mode, 'get'):
                v = self.app.is_auto_invoice_mode.get()
                is_auto_inv = bool(v) if isinstance(v, (bool, int)) else False
            elif hasattr(self, 'main_app') and hasattr(self.main_app, 'is_auto_invoice_mode') and hasattr(self.main_app.is_auto_invoice_mode, 'get'):
                v = self.main_app.is_auto_invoice_mode.get()
                is_auto_inv = bool(v) if isinstance(v, (bool, int)) else False
        except Exception:
            is_auto_inv = False

        seller_voucher = 0.0
        try:
            if hasattr(self.app, 'financials') and hasattr(self.app.financials, 'seller_voucher'):
                sv = self.app.financials.seller_voucher
                if isinstance(sv, (int, float)) and not isinstance(sv, bool):
                    seller_voucher = float(sv)
                elif isinstance(sv, str) and sv.strip() and sv.strip().replace('.', '', 1).isdigit():
                    seller_voucher = float(sv.strip())

            if seller_voucher == 0.0 and hasattr(self.app, 'cus_seller_voucher') and hasattr(self.app.cus_seller_voucher, 'get'):
                sv = self.app.cus_seller_voucher.get()
                if isinstance(sv, (int, float)) and not isinstance(sv, bool):
                    seller_voucher = float(sv)
                elif isinstance(sv, str) and sv.strip() and sv.strip().replace('.', '', 1).isdigit():
                    seller_voucher = float(sv.strip())
        except Exception:
            seller_voucher = 0.0

        # Multi-SKU Guard: หากมีหลาย SKU และมี Seller Voucher > 0 -> ข้ามเพื่อให้ทำแบบ Manual
        if is_auto_inv and seller_voucher > 0:
            unique_skus = set()
            for it in (self.app.items or []):
                sk = str(it.get('เลขอ้างอิง SKU (SKU Reference No.)', '')).strip()
                if sk:
                    unique_skus.add(sk)
            if len(unique_skus) > 1:
                err_msg = f"ออเดอร์มีหลาย SKU ({len(unique_skus)} รายการ) และมี Seller Voucher ({seller_voucher:,.2f} บาท) -> ข้ามเพื่อให้ทำแบบ Manual"
                self.app.update_log(f"⚠️ {err_msg}")
                logger.warning(f"Order {getattr(self.bot, 'cus_order', '')}: {err_msg}")
                raise ValueError(err_msg)

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

                    # ══════════════════════════════════════════════════════════
                    # ขั้นตอนที่ 1 (Phase 1): เติมคูปอง Seller Voucher ก่อน
                    # ══════════════════════════════════════════════════════════
                    if is_auto_inv and seller_voucher > 0:
                        self.app.update_log(
                            f"🔍 [Phase 1: Seller Voucher] ค้นหาและตรวจสอบคูปอง Seller Voucher ({seller_voucher:,.2f} บาท) บน SMCO ให้กับ SKU: {sku_key} ก่อนเป็นอันดับแรก..."
                        )
                        sv_ok, sv_status, sv_chosen = self.find_and_apply_seller_voucher_on_smco(
                            item_no_1indexed, seller_voucher, cp_candidates=cp_candidates, require_candidate_match=True
                        )

                        if not sv_ok:
                            sugg_info = self.find_suggested_cp_for_discount(
                                seller_voucher, require_seller_voucher=True
                            )
                            suggested_cp_code = sugg_info["suggested_code"] if sugg_info else ((sv_chosen.get("code") if sv_chosen else ""))
                            has_entry = len(cp_candidates) > 0
                            self.add_missing_cp_to_excel(sku_key, expected_price, suggested_cp=suggested_cp_code)

                            if sv_status == "NOT_FOUND":
                                log_msg = (
                                    f"❌ มี Seller Voucher ({seller_voucher:,.2f} บาท) แต่ไม่พบคูปอง Seller Voucher "
                                    f"ที่มีมูลค่าส่วนลดตรงกันบน SMCO สำหรับ SKU: {sku_key} -> ยกเลิก/ข้ามออเดอร์ทันที"
                                )
                            elif sv_status == "UNCONFIGURED":
                                log_msg = (
                                    f"⚠️ พบคูปอง Seller Voucher บน SMCO แต่ยังไม่ได้ระบุใน cp_data.xlsx สำหรับ SKU: {sku_key} "
                                    f"-> แนะนำ: [{suggested_cp_code}] (บันทึกใส่คอลัมน์ suggested_cp แล้ว) หยุดเพื่อให้ตรวจสอบก่อน"
                                )
                            else:
                                log_msg = f"❌ ไม่สามารถกดเลือกคูปอง Seller Voucher บนหน้าเว็บ SMCO ได้สำหรับ SKU: {sku_key}"

                            logger.warning(log_msg)
                            self.app.update_log(log_msg)
                            self._raise_missing_cp_guide(
                                item, sku_key, actual_price, expected_price, purchased_date,
                                has_entry=has_entry, cp_candidates=cp_candidates, suggested_cp_info=sugg_info
                            )

                        self.app.update_log(
                            f"🎫 [Phase 1 สำเร็จ] ใส่คูปอง Seller Voucher [{sv_chosen['code']}] ให้กับ SKU: {sku_key} เรียบร้อยแล้ว"
                        )
                        time.sleep(0.5)

                        # ตรวจสอบราคาบน POS อีกครั้งหลังใส่ Seller Voucher
                        new_price_res = self.bot.ProductManager.verify_item_price()
                        if sku_key in new_price_res:
                            item_price_info = new_price_res[sku_key]
                            diff_val = item_price_info.get("diff", 0)
                            actual_price = item_price_info.get("actual", 0)
                        else:
                            diff_val = 0

                        if item_price_info.get("ok", False) or abs(diff_val) <= 0.05:
                            self.app.update_log(
                                f"✅ ราคา SKU: {sku_key} หลังใส่ Seller Voucher ตรงกับราคาเป้าหมายแล้ว ({actual_price:,.2f} บาท)"
                            )
                            continue

                        self.app.update_log(
                            f"🔄 [Phase 2: Pattern CP เดิม] หลังใส่ Seller Voucher ราคายังมีส่วนต่าง ({diff_val:+,.2f} บาท) เข้าสู่ขั้นตอนปรับราคาตาม Pattern เดิม..."
                        )

                    # ══════════════════════════════════════════════════════════
                    # ขั้นตอนที่ 2 (Phase 2): ปรับราคาตาม Pattern เดิมใน cp_data.xlsx
                    # ══════════════════════════════════════════════════════════
                    # กรณีที่ 1: marketplace_item_price > smco_item_price? (diff > 0)
                    # ถ้าราคาขายบน SMCO ต่ำกว่าราคาที่ลูกค้าซื้อ (diff > 0) ให้ปรับราคาขึ้น (Overcharge) ทันที
                    if diff_val > 0:
                        bypassed = False
                        oc_amount_to_apply = None
                        matched_cand = None

                        if cp_candidates:
                            for cand in cp_candidates:
                                cp_signal = str(cand.get("cp_name", "")).strip().upper()
                                if cp_signal in ["NONE", "BYPASS", "NO_CP", "NO CP", "PASSTHROUGH"]:
                                    self.app.update_log(f"⏩ ข้ามการปรับราคาสำหรับ SKU: {sku_key} (กำหนดเป็น {cand.get('cp_name')})")
                                    bypassed = True
                                    break
                                elif is_valid_adjustment(cand.get("oc_amount", "")):
                                    oc_amount_to_apply = str(cand.get("oc_amount", "")).strip()
                                    matched_cand = cand
                                    self.app.update_log(f"⚡ ปรับราคาขึ้น (Overcharge) จากข้อมูลแคมเปญ: {oc_amount_to_apply} บาท")
                                    break

                        if not bypassed:
                            if oc_amount_to_apply is not None:
                                self.smco_set_overcharge_product(sku_key, str(oc_amount_to_apply))
                            elif seller_voucher > 0:
                                # หากเป็นออเดอร์ที่มี Seller Voucher: ไม่อนุญาตให้ auto-overcharge โดยพลการหากไม่มี oc_amount ระบุใน cp_data.xlsx
                                self.app.update_log(
                                    f"ℹ️ ออเดอร์มี Seller Voucher แต่ไม่มีการระบุ oc_amount ใน cp_data.xlsx สำหรับ SKU: {sku_key} (ส่วนต่าง: +{diff_val:,.2f} บาท) -> ไม่ทำการ Overcharge อัตโนมัติ เพื่อความปลอดภัย"
                                )
                            else:
                                # กรณีออเดอร์ทั่วไปที่ไม่มี Seller Voucher: ปรับราคาขึ้นตามส่วนต่าง diff_val ทันที
                                self.app.update_log(f"⚡ ปรับราคาขึ้น (Overcharge) สำหรับ SKU: {sku_key} จำนวน {diff_val} บาท (คำนวณจากส่วนต่าง)")
                                self.smco_set_overcharge_product(sku_key, str(diff_val))

                            # หาก candidate มีการระบุคูปอง (cp_name) ด้วย ให้ตรวจสอบและเลือกคูปองที่ยังขาดอยู่
                            cand_to_use = matched_cand or (cp_candidates[0] if cp_candidates else None)
                            if cand_to_use and cand_to_use.get("cp_name"):
                                cand_cp_name = str(cand_to_use.get("cp_name", "")).strip()
                                is_bp = cand_cp_name.upper() in ["NONE", "BYPASS", "NO_CP", "NO CP", "PASSTHROUGH"]
                                if not is_bp and cand_cp_name:
                                    self.app.update_log(f"🔍 ตรวจสอบและเลือกคูปองที่เหลือ [{cand_cp_name}] สำหรับ SKU: {sku_key}...")
                                    try:
                                        self.apply_candidate_coupons_if_missing(item_no_1indexed, sku_key, cand_cp_name)
                                    except Exception as ex_cp:
                                        print(f"Error applying candidate coupons in diff > 0: {ex_cp}")

                    # กรณีที่ 2: marketplace_item_price < smco_item_price? (diff < 0)
                    elif diff_val < 0:
                        self.app.update_log(f"🔍 กำลังหาคูปองลดราคาสำหรับ SKU: {sku_key} (พบ {len(cp_candidates)} รูปแบบใน CP Data)")

                        # สแกนดูว่าในบรรดา candidates ทั้งหมด มีกี่ชุดที่พบคูปองบนหน้าเว็บ SMCO จริง
                        available_candidates = self.scan_matching_cp_candidates_on_smco(
                            item_no_1indexed, cp_candidates or [], required_seller_voucher=0.0
                        )

                        target_discount = abs(float(diff_val))
                        sugg_info = self.find_suggested_cp_for_discount(
                            target_discount, require_seller_voucher=False
                        )
                        suggested_cp_code = sugg_info["suggested_code"] if sugg_info else ""

                        # ─── CASE 0: ไม่พบชุดใดที่ใช้ได้บน SMCO เลย ───
                        if len(available_candidates) == 0:
                            has_entry = len(cp_candidates) > 0
                            self.add_missing_cp_to_excel(sku_key, expected_price, suggested_cp=suggested_cp_code)
                            log_msg = f"❌ ไม่พบชุด CP/DC ใดที่ตรงกับในระบบ SMCO สำหรับ SKU: {sku_key} (วันที่: {purchased_date}, ราคาที่ต้องออก: {expected_price}) -> หยุดปรับราคาและสร้างคำถาม"

                            logger.warning(log_msg)
                            self.app.update_log(log_msg)
                            self._raise_missing_cp_guide(item, sku_key, actual_price, expected_price, purchased_date, has_entry=has_entry, cp_candidates=cp_candidates, suggested_cp_info=sugg_info)

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
                                self.add_missing_cp_to_excel(sku_key, expected_price, suggested_cp=suggested_cp_code)
                                self._raise_missing_cp_guide(item, sku_key, actual_price, expected_price, purchased_date, has_entry=True, suggested_cp_info=sugg_info)

                            if has_valid_cp:
                                self.app.update_log(f"🔍 ตรวจสอบและเลือกคูปอง [{cp_name}] สำหรับ SKU: {sku_key}...")
                                try:
                                    cp_ok = self.apply_candidate_coupons_if_missing(item_no_1indexed, sku_key, cp_name)
                                    if not cp_ok:
                                        log_err = f"❌ เกิดข้อผิดพลาดขณะกดเลือกคูปอง [{cp_name}] บน SMCO สำหรับ SKU: {sku_key}"
                                        logger.error(log_err)
                                        self.app.update_log(log_err)
                                        self._raise_missing_cp_guide(item, sku_key, actual_price, expected_price, purchased_date, has_entry=True)
                                    time.sleep(0.5)
                                except Exception as check_err:
                                    print(f"Error checking and filtering cp/dc tooltips: {check_err}")
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
                            if suggested_cp_code:
                                self.add_missing_cp_to_excel(sku_key, expected_price, suggested_cp=suggested_cp_code)
                            self._raise_ambiguous_cp_guide(item, sku_key, actual_price, expected_price, purchased_date, available_candidates, suggested_cp_info=sugg_info)

    def _raise_ambiguous_cp_guide(self, item: dict, sku_key: str, actual_price: Any, expected_price: Any, purchased_date: str, candidate_list: list, suggested_cp_info: Optional[dict] = None) -> None:
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

        sugg_str = ""
        if suggested_cp_info:
            s_code = suggested_cp_info.get("suggested_code", "")
            s_disc = suggested_cp_info.get("discount", 0.0)
            sugg_str = (
                f"\n💡 [ระบบคำนวณแนะนำ] พบคูปองบน SMCO ที่ลดแล้วได้ราคา {expected_formatted} บาท พอดีเป๊ะ:\n"
                f"   • แนะนำ: '{s_code}' (ส่วนลด {s_disc:,.2f} บาท)\n"
                f"   • บันทึกใส่คอลัมน์ 'suggested_cp' ใน cp_data.xlsx เรียบร้อยแล้ว (เปิดตรวจสอบและคัดลอกได้)\n"
            )

        pattern_msg = (
            f"\n{marketplace} เวลาสั่งซื้อ {purchase_time}\n"
            f"{sku_key} {product_name}\n"
            f"ยิงขายขึ้น {actual_formatted} บาท\n"
            f"ลูกค้าซื้อราคา {expected_formatted} บาท\n"
            f"ขอวิธีปรับราคาครับ (พบคูปอง/ส่วนลดที่เข้าเงื่อนไข {len(candidate_list)} ชุดบน SMCO):\n"
            f"{cand_str}"
            f"{sugg_str}"
        )
        self.app.update_log(pattern_msg)
        error_msg = f"Order skipped, multiple ambiguous CP/DC options found for SKU: {sku_key} (วันที่: {purchased_date}, ราคาที่ต้องออกบิล: {expected_price})\n{pattern_msg}"
        self.app.update_log(f"❌ {error_msg}")
        logger.warning(f"Order: {self.bot.cus_order}: {error_msg}")
        raise ValueError(error_msg)

    def _raise_missing_cp_guide(self, item: dict, sku_key: str, actual_price: Any, expected_price: Any, purchased_date: str, has_entry: bool, cp_candidates: list = None, suggested_cp_info: Optional[dict] = None) -> None:
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

        # หากมี Seller Voucher ให้แสดงราคาซื้อของลูกค้าแบบไม่รวม Seller Voucher ในข้อความแพทเทิร์นถามราคา
        display_price = expected_price
        try:
            if hasattr(self.app, 'financials') and self.app.financials:
                aggr = getattr(self.app.financials, 'aggregated_items', {})
                if sku_key in aggr:
                    t_qty = aggr[sku_key].get("total_qty", 1.0) or 1.0
                    t_price = aggr[sku_key].get("total_price", 0.0)
                    t_disc = aggr[sku_key].get("total_discount", 0.0)
                    display_price = (t_price + t_disc) / t_qty
            elif hasattr(item, 'get'):
                raw_p = str(item.get('ราคาขายสุทธิ', item.get('ราคาตั้งต้น', expected_price))).replace(',', '')
                raw_d = str(item.get('ส่วนลดจาก Shopee', 0)).replace(',', '')
                raw_q = str(item.get('จำนวน', 1)).replace(',', '')
                qty = float(raw_q) if raw_q else 1.0
                display_price = (float(raw_p) + (float(raw_d) if raw_d else 0.0)) / (qty if qty > 0 else 1.0)
        except Exception:
            display_price = expected_price

        try:
            display_price_formatted = f"{float(display_price):,.2f}"
        except Exception:
            display_price_formatted = str(display_price)

        excel_cp_names = [c.get('cp_name') for c in (cp_candidates or []) if c.get('cp_name')]
        smco_scanned = getattr(self, 'last_scanned_smco_coupons', [])

        if has_entry:
            if excel_cp_names:
                excel_str = ", ".join(excel_cp_names)
                smco_str = ", ".join(smco_scanned) if smco_scanned else "ไม่พบปุ่ม CP หรือไม่มีคูปองบนหน้า SMCO"
                extra_note = f"\n(มี SKU ใน CP_data แล้ว แต่ CP ใน Excel กับหน้า SMCO ไม่ตรงกัน:\n  • ใน cp_data.xlsx ระบุ: {excel_str}\n  • บนหน้า SMCO มี: {smco_str})"
            else:
                extra_note = "\n(มี SKU ใน cp_data.xlsx แล้ว แต่ยังไม่ได้ระบุรหัส CP หรือ Overcharge)"
        else:
            extra_note = ""

        sugg_str = ""
        if suggested_cp_info:
            s_code = suggested_cp_info.get("suggested_code", "")
            s_disc = suggested_cp_info.get("discount", 0.0)
            pre_codes = suggested_cp_info.get("preselected_codes", [])
            new_code = suggested_cp_info.get("new_code", s_code)

            if pre_codes:
                pre_str = ", ".join(pre_codes)
                sugg_str = (
                    f"\n💡 [ระบบคำนวณแนะนำ] พบคูปองบน SMCO ที่ลดแล้วได้ราคา {expected_formatted} บาท พอดีเป๊ะ (แบบคู่ผสม):\n"
                    f"   • คูปองเริ่มต้นที่ติดมากับสินค้า: '{pre_str}'\n"
                    f"   • คูปองที่ต้องเลือกเพิ่ม: '{new_code}' (ส่วนลด {s_disc:,.2f} บาท)\n"
                    f"   • รหัสรวมที่แนะนำ: '{s_code}'\n"
                    f"   • บันทึกใส่คอลัมน์ 'suggested_cp' ใน cp_data.xlsx เรียบร้อยแล้ว (เปิดตรวจสอบและคัดลอกได้)\n"
                )
            else:
                sugg_str = (
                    f"\n💡 [ระบบคำนวณแนะนำ] พบคูปองบน SMCO ที่ลดแล้วได้ราคา {expected_formatted} บาท พอดีเป๊ะ:\n"
                    f"   • แนะนำ: '{s_code}' (ส่วนลด {s_disc:,.2f} บาท)\n"
                    f"   • บันทึกใส่คอลัมน์ 'suggested_cp' ใน cp_data.xlsx เรียบร้อยแล้ว (เปิดตรวจสอบและคัดลอกได้)\n"
                )

        pattern_msg = (
            f"\n{marketplace} เวลาสั่งซื้อ {purchase_time}\n"
            f"{sku_key} {product_name}\n"
            f"ยิงขายขึ้น {actual_formatted} บาท\n"
            f"ลูกค้าซื้อราคา {display_price_formatted} บาท\n"
            f"ขอวิธีปรับราคาครับ"
            f"{extra_note}"
            f"{sugg_str}"
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

            # เช็คจำนวนสินค้า (ขาด SN, ยิงไม่ติด, หรือมีสินค้าตกค้าง) -> fail order ทันที
            qty_shortage_lines = []
            for sku, info in verification_result.get("qty", {}).items():
                if not info.get("ok", True):
                    exp = info.get('expected')
                    act = info.get('actual')
                    if exp == 0:
                        qty_shortage_lines.append(
                            f"  • {sku}: ตรวจพบสินค้าแปลกปลอม/ตกค้างบน POS (ในคำสั่งซื้อนี้ไม่มีสินค้านี้ แต่พบบน POS {act} ชิ้น)"
                        )
                    elif exp == "FOUND_IN_MARKETPLACE":
                        qty_shortage_lines.append(
                            f"  • {sku}: ไม่พบคำสั่งซื้อนี้ในไฟล์นำเข้า Marketplace (Fatal Mismatch)"
                        )
                    elif act == "NOT_FOUND":
                        qty_shortage_lines.append(
                            f"  • {sku}: ไม่พบสินค้านี้บน POS (ลูกค้าสั่ง {exp} ชิ้น)"
                        )
                    else:
                        qty_shortage_lines.append(
                            f"  • {sku}: ลูกค้าสั่ง {exp} แต่ลง POS ได้ {act}"
                        )
            if qty_shortage_lines:
                err_msg = "รายการหรือจำนวนสินค้าบน POS ไม่ตรงกับคำสั่งซื้อ:\n" + "\n".join(qty_shortage_lines)
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
                self._handle_post_verification_failures(post_verification, initial_verification=verification_result)

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

    def _handle_post_verification_failures(self, post_verification: dict, initial_verification: dict = None) -> None:
        """รวบรวม Error และแจ้งเตือนเมื่อการตรวจสอบรอบ 2 ยังไม่ผ่าน โดยจัดรูปแบบราคา mismatch เป็น Pattern ขอวิธีปรับราคา (ราคาก่อนปรับ)"""
        self._log_price_verification_summary(post_verification)
        qty_errors = [
            f"จำนวนไม่พอ: {sku} (expected {info.get('expected')}, actual {info.get('actual')})"
            for sku, info in post_verification.get("qty", {}).items() if not info.get("ok", True)
        ]
        
        mismatch_patterns = []
        marketplace = self.app.marketplace_target.get()
        purchase_time = self.app.cus_purchase_time.get()
        purchased_date = purchase_time

        price_errors = []
        for sku, info in post_verification.get("price", {}).items():
            if not info.get("ok", True):
                price_errors.append(
                    f"SKU Price mismatch: {sku} (expected {info.get('expected')}, actual {info.get('actual')}, diff {info.get('diff')})"
                )
                product_name = ""
                for item in self.app.items:
                    if item.get('เลเลขsku') == sku or item.get('เลขอ้างอิง SKU (SKU Reference No.)') == sku:
                        product_name = str(item.get('ชื่อสินค้า', '')).strip()
                        if product_name.lower() == 'nan':
                            product_name = ''
                        break

                expected_price = info.get('expected', 0)
                # ดึงราคาจริงตั้งต้นก่อนปรับจาก initial_verification (Round 1)
                init_pinfo = (initial_verification or {}).get("price", {}).get(sku, {})
                actual_price = init_pinfo.get('actual', info.get('actual', 0))

                try:
                    actual_formatted = f"{float(actual_price):,.2f}"
                except Exception:
                    actual_formatted = str(actual_price)
                try:
                    expected_formatted = f"{float(expected_price):,.2f}"
                except Exception:
                    expected_formatted = str(expected_price)

                pattern_msg = (
                    f"\n{marketplace} เวลาสั่งซื้อ {purchase_time}\n"
                    f"{sku} {product_name}\n"
                    f"ยิงขายขึ้น {actual_formatted} บาท\n"
                    f"ลูกค้าซื้อราคา {expected_formatted} บาท\n"
                    f"ขอวิธีปรับราคาครับ"
                )
                self.app.update_log(pattern_msg)
                mismatch_patterns.append(pattern_msg)

        total_res = post_verification.get("total", {})
        total_errors = (
            [f"Total Price mismatch (expected {total_res.get('expected')}, actual {total_res.get('actual')})"]
            if not total_res.get("ok", True) else []
        )

        if mismatch_patterns:
            error_msg = f"Order skipped, ราคาหลังปรับไม่ตรงตามเป้าหมายสำหรับ SKU:\n" + "\n".join(mismatch_patterns)
        else:
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

