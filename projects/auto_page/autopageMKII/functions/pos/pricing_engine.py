"""
Module: functions.pos.pricing_engine
Contains:
  - OrderFinancials: Single Source of Truth (SSOT) for order-level and item-level financial calculations.
  - POSPricingReconciler: Handles price mismatch detection, campaign coupon (CP) matching from Excel,
    overcharge (OC) / discount (DC) adjustments on the SMCO POS cart, and 2-step verification.
"""

from __future__ import annotations

import datetime
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import openpyxl
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


def parse_smart_datetime(val: Any) -> Optional[Union[datetime.datetime, datetime.date]]:
    """
    แปลงค่าวันที่และเวลาหลากหลายรูปแบบให้กลายเป็น datetime.datetime หรือ datetime.date
    หากมีเวลาระบุชัดเจนหรือเวลาไม่เท่ากับ 00:00:00 จะคืนค่า datetime.datetime
    หากเป็นวันที่ล้วน (ไม่มีเวลาระบุ) จะคืนค่า datetime.date
    """
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime.datetime, pd.Timestamp)):
        if val.hour != 0 or val.minute != 0 or val.second != 0:
            return val.to_pydatetime() if hasattr(val, 'to_pydatetime') else val
        return val.date() if hasattr(val, 'date') else val
    if isinstance(val, datetime.date):
        return val
    s = str(val).strip()
    if not s or s.lower() in ['nan', 'nat', 'none', '-']:
        return None
    try:
        match_be = re.search(r'\b(25\d{2})\b', s)
        if match_be:
            be_year = int(match_be.group(1))
            ce_year = be_year - 543
            s = s[:match_be.start(1)] + str(ce_year) + s[match_be.end(1):]
        
        has_time = bool(re.search(r'\d{1,2}:\d{2}', s))
        if re.match(r'^\d{4}[-/.]', s):
            dt = parser.parse(s, yearfirst=True, dayfirst=False)
        else:
            dt = parser.parse(s, dayfirst=True)
            
        if has_time or (dt.hour != 0 or dt.minute != 0 or dt.second != 0):
            return dt
        return dt.date()
    except Exception:
        try:
            p_dt = pd.to_datetime(s, format='mixed', dayfirst=True, errors='coerce')
            if pd.notna(p_dt):
                if p_dt.hour != 0 or p_dt.minute != 0 or p_dt.second != 0:
                    return p_dt.to_pydatetime() if hasattr(p_dt, 'to_pydatetime') else p_dt
                return p_dt.date() if hasattr(p_dt, 'date') else p_dt
        except Exception:
            pass
    return None



def format_smart_datetime_str(dt: Any) -> str:
    """แปลง datetime/date เป็น string เช่น '17/09/2026 00:00:01' หรือ '17/09/2026'"""
    if not dt:
        return ""
    if isinstance(dt, (datetime.datetime, pd.Timestamp)):
        if dt.hour != 0 or dt.minute != 0 or dt.second != 0:
            return dt.strftime("%d/%m/%Y %H:%M:%S")
        else:
            return dt.strftime("%d/%m/%Y")
    elif isinstance(dt, datetime.date):
        return dt.strftime("%d/%m/%Y")
    elif isinstance(dt, str):
        parsed = parse_smart_datetime(dt)
        if parsed:
            return format_smart_datetime_str(parsed)
        return dt
    return str(dt)


def to_comparable_datetime(val: Any) -> Optional[datetime.datetime]:
    """แปลงค่า date หรือ datetime ให้เป็น datetime.datetime ที่เปรียบเทียบขนาดกันได้ปลอดภัย 100%"""
    if val is None:
        return None
    if isinstance(val, datetime.datetime):
        return val
    if isinstance(val, datetime.date):
        return datetime.datetime.combine(val, datetime.time.min)
    p = parse_smart_datetime(val)
    if isinstance(p, datetime.datetime):
        return p
    if isinstance(p, datetime.date):
        return datetime.datetime.combine(p, datetime.time.min)
    return None


def swap_day_month(d: Any) -> Optional[datetime.date]:
    """สลับวันและเดือนหากเลขวันและเดือนไม่เกิน 12 และไม่เท่ากัน (แก้ปัญหา US Locale MM/DD)"""
    if d is None:
        return None
    try:
        dt = parse_smart_date(d)
        if dt and 1 <= dt.day <= 12 and 1 <= dt.month <= 12 and dt.day != dt.month:
            return datetime.date(dt.year, dt.day, dt.month)
    except Exception:
        pass
    return None


def correct_cp_date_range(start_val: Any, end_val: Any) -> tuple[Optional[datetime.date], Optional[datetime.date]]:
    """
    ตรวจสอบและ Auto-Correct ช่วงวันโปรโมชัน CP
    หากพบว่า start_date > end_date (เกิดจากการที่ Google Sheets หรือ GAS สลับ Day/Month)
    ระบบจะทำการ Auto-Swap วันกับเดือนให้สอดคล้องกับความเป็นจริงอัตโนมัติ
    """
    start_date = parse_smart_date(start_val)
    end_date = parse_smart_date(end_val)

    if start_date and end_date and start_date > end_date:
        end_swapped = swap_day_month(end_date)
        start_swapped = swap_day_month(start_date)

        if end_swapped and start_date <= end_swapped:
            end_date = end_swapped
        elif start_swapped and start_swapped <= end_date:
            start_date = start_swapped
        elif start_swapped and end_swapped and start_swapped <= end_swapped:
            start_date = start_swapped
            end_date = end_swapped

    return start_date, end_date


def extract_coupon_date_range(text: str) -> tuple[Optional[Union[datetime.datetime, datetime.date]], Optional[Union[datetime.datetime, datetime.date]]]:
    """
    ดึงวันเริ่มและวันสิ้นสุดของคูปองจากข้อความ เช่น '(01/09/2026 - 30/09/2026)', '01/09/26 - 30/09/26'
    คืนค่า (start_date, end_date)
    """
    if not text:
        return None, None
    m = re.search(
        r'\(?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)?)\s*(?:-|to|ถึง|~)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)?)\s*\)?',
        str(text),
        re.IGNORECASE
    )
    if m:
        s_date = parse_smart_datetime(m.group(1)) or parse_smart_date(m.group(1))
        e_date = parse_smart_datetime(m.group(2)) or parse_smart_date(m.group(2))
        return s_date, e_date
    return None, None


def extract_target_price_from_text(text: str) -> Optional[float]:
    """
    ดึงราคาเป้าหมายของสินค้า/เซ็ตสินค้าจาก Remark หรือ Description ของคูปอง
    เช่น 'Shp/TT เดือน ก.ย. ราคาเซ็ทละ 1449', 'Dynamic ก.ย. Shp ราคา 9673', 'ราคาชุดละ 1,449.-', 'ราคาคู่ละ 1017'
    """
    if not text:
        return None
    m = re.search(
        r'(?:ราคา(?:\s*(?:ขาย|เป้าหมาย|เซ็ทละ|เซ็ตละ|ชุดละ|แพ็คละ|แพคละ|คู่ละ|ชิ้นละ|กล่องละ|ขวดละ|ตลับละ|เหลือ|พิเศษ|โปร|net|สุทธิ|เซ็ท|เซ็ต|ชุด|คู่|แพ็ค|แพค))?|เซ็ทละ|เซ็ตละ|ชุดละ|แพ็คละ|แพคละ|คู่ละ|เป้าหมาย|จบที่)\s*[:=]?\s*([\d,]+(?:\.\d+)?)\s*(?:\.-|บาท)?',
        str(text),
        re.IGNORECASE
    )
    if m:
        try:
            val = float(m.group(1).replace(',', ''))
            if val > 0:
                return val
        except Exception:
            pass
    return None

def get_coupon_start_and_end_dates(c: dict) -> tuple[Optional[Union[datetime.datetime, datetime.date]], Optional[Union[datetime.datetime, datetime.date]]]:
    """
    ดึง start_date และ end_date ของคูปอง พร้อมรักษาเวลา (Time) ถ้ามี
    หากไม่มีค่าที่สแกนมา ให้ลอง parse จาก desc หรือรหัสคูปอง (fallback)
    """
    s_raw = c.get("start_date") or c.get("startDate") or c.get("usage_start_date") or c.get("suggested_usage_start_date")
    e_raw = c.get("end_date") or c.get("endDate") or c.get("usage_end_date") or c.get("suggested_usage_end_date")

    if isinstance(s_raw, (datetime.datetime, datetime.date)):
        s_date = s_raw
    else:
        s_date = parse_smart_datetime(s_raw) or parse_smart_date(s_raw) if s_raw else None

    if isinstance(e_raw, (datetime.datetime, datetime.date)):
        e_date = e_raw
    else:
        e_date = parse_smart_datetime(e_raw) or parse_smart_date(e_raw) if e_raw else None

    if s_date and e_date:
        return s_date, e_date

    desc = c.get("desc", "") or c.get("couponDesc", "") or c.get("remark", "") or c.get("couponDetailRemark", "")
    if desc:
        s_dt, e_dt = extract_coupon_date_range(desc)
        if s_dt and not s_date:
            s_date = s_dt
        if e_dt and not e_date:
            e_date = e_dt

    # Fallback ดึงวันเริ่มจากรหัสคูปอง SMCO เช่น CP2609100001 -> 2026-09-10
    if not s_date:
        code = str(c.get("code", "") or c.get("couponCode", ""))
        m = re.search(r'\b(?:CP|DC)(\d{2})(\d{2})(\d{2})\d{4}\b', code, re.IGNORECASE)
        if m:
            try:
                y = 2000 + int(m.group(1))
                m_val = int(m.group(2))
                d_val = int(m.group(3))
                s_date = datetime.date(y, m_val, d_val)
            except Exception:
                pass

    return s_date, e_date

def is_coupon_valid_for_order(c_dict: dict, order_date: Any = None) -> bool:
    """
    ตรวจสอบว่าคูปองไม่หมดอายุ และครอบคลุมวันที่สั่งซื้อหรือไม่ (start_date <= order_date <= end_date)
    """
    if c_dict.get("is_expired"):
        return False
    parsed_order_date = parse_smart_date(order_date) if order_date else None
    if parsed_order_date is None:
        return True
    s = c_dict.get("start_date")
    e = c_dict.get("end_date")
    if not s and not e:
        s, e = extract_coupon_date_range(c_dict.get("desc", ""))
    s_cmp = parse_smart_date(s)
    e_cmp = parse_smart_date(e)
    if s_cmp and parsed_order_date < s_cmp:
        return False
    if e_cmp and parsed_order_date > e_cmp:
        return False
    return True




def format_cp_excel(file_path: str) -> bool:
    """
    จัดรูปแบบไฟล์ Excel cp_data:
    - freeze row 1 (freeze_panes = "A2")
    - ใส่ auto filter ครอบคลุมทุกคอลัมน์ของข้อมูล
    - ขยาย column 1 (คอลัมน์ A / SKU) ให้มี width 32.0 (~2.5 นิ้ว / ~240 pixels)
    """
    if not file_path or not os.path.exists(file_path):
        return False
    if not str(file_path).lower().endswith(('.xlsx', '.xlsm')):
        return False
    try:
        is_xlsm = str(file_path).lower().endswith('.xlsm')
        wb = openpyxl.load_workbook(file_path, keep_vba=is_xlsm)
        modified = False
        for ws in wb.worksheets:
            if ws.max_row > 0 and ws.max_column > 0:
                # 1. Freeze row 1
                if ws.freeze_panes != "A2":
                    ws.freeze_panes = "A2"
                    modified = True
                # 2. Auto filter
                col_max_letter = openpyxl.utils.get_column_letter(ws.max_column)
                target_filter_ref = f"A1:{col_max_letter}{ws.max_row}"
                if ws.auto_filter.ref != target_filter_ref:
                    ws.auto_filter.ref = target_filter_ref
                    modified = True
                # 3. ขยาย column 1 (A) กว้าง 32.0 (~2.5 นิ้ว)
                col_letter = openpyxl.utils.get_column_letter(1)
                if ws.column_dimensions[col_letter].width != 32.0:
                    ws.column_dimensions[col_letter].width = 32.0
                    modified = True
        if modified:
            wb.save(file_path)
        wb.close()
        return True
    except Exception as e:
        logger.warning(f"[format_cp_excel] Warning formatting {file_path}: {e}")
        return False


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
        self._last_recorded_order_id: Optional[str] = None
        self.last_expected_prices: Dict[str, float] = {}
        self._applied_adjustments: Dict[str, Set[str]] = {}
        self._product_master_cache: Dict[str, list] = {}
        self._session_ctx: Optional[Dict[str, Any]] = None

        # Initialize DualSourceCPLoader for real-time sync with Google Sheet & Local Excel
        gas_url = getattr(self.app, 'cp_gas_url', None)
        excel_path = getattr(self.app, 'cp_table_location', '')
        if not excel_path or not os.path.exists(excel_path):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            for cand in [
                os.path.join(base_dir, "tables", "cp_data.xlsx"),
                os.path.join(base_dir, "assets", "tables", "cp_data.xlsx")
            ]:
                if os.path.exists(cand):
                    excel_path = cand
                    break
        try:
            from functions.pos.cp_data_loader import DualSourceCPLoader, DEFAULT_GAS_URL
            self._dual_cp_loader = DualSourceCPLoader(
                gas_url=gas_url or DEFAULT_GAS_URL,
                local_excel_path=excel_path if (excel_path and os.path.exists(excel_path)) else None
            )
        except Exception:
            self._dual_cp_loader = None

    # ══════════════════════════════════════════════════════════════════════════
    # HELPER UTILITIES
    # ══════════════════════════════════════════════════════════════════════════
    def record_product_master_response(self, sku: str, response_data: Union[list, dict]) -> None:
        """
        บันทึก JSON Response จาก /getProductMasterInfoPOSV3.htm สำหรับ SKU นั้นๆ
        ใช้สำหรับรวมส่วนลดคูปองของสินค้าเซ็ต (Multi-SKU Combo Pack)
        """
        if not sku or not response_data:
            return
        if not hasattr(self, '_product_master_cache') or self._product_master_cache is None:
            self._product_master_cache = {}
        if isinstance(response_data, dict):
            response_data = [response_data]
            
        sku_clean = str(sku).strip().upper()
        self._product_master_cache[sku_clean] = response_data
        
        # บันทึกทั้งแบบ standard formatted และ productCode จาก response
        fmt_sku = self.sku_formater(sku_clean).strip().upper()
        if fmt_sku and fmt_sku != sku_clean:
            self._product_master_cache[fmt_sku] = response_data
            
        for rec in response_data:
            if isinstance(rec, dict) and rec.get("productCode"):
                p_code = str(rec.get("productCode")).strip().upper()
                if p_code not in self._product_master_cache:
                    self._product_master_cache[p_code] = response_data
        logger.debug(f"[record_product_master_response] Cached product master info for SKU: {sku_clean} ({len(response_data)} records)")

        # ซิงค์วันที่และข้อมูลคูปองจาก Network Response เข้าสู่ตาราง cp_data ทันที
        try:
            self.sync_product_master_coupon_dates_to_excel(sku_clean, response_data)
        except Exception as sync_ex:
            logger.warning(f"[record_product_master_response] Error syncing coupon dates for {sku_clean}: {sync_ex}")

    def sync_product_master_coupon_dates_to_excel(self, sku: str, response_data: Union[list, dict]) -> None:
        """
        เมื่อดักจับ Response จาก /getProductMasterInfoPOSV3.htm ได้จากการยิง SKU
        ให้สกัดข้อมูล Coupon Details (คูปอง, วันที่เริ่มต้น, วันที่สิ้นสุด, ส่วนลด, Remark)
        และอัปเดตลง cp_df, tables/cp_data.xlsx และ Google Sheets ทันที
        """
        if not sku or not response_data:
            return

        def _scan_coupons(items):
            found = []
            if isinstance(items, list):
                for it in items:
                    found.extend(_scan_coupons(it))
            elif isinstance(items, dict):
                c_c = str(items.get("couponCode") or items.get("code") or "").strip().upper()
                if c_c:
                    found.append(items)
                for k in ["productCouponDetail", "coupons", "couponDetail", "couponDetails", "couponList", "productCoupons", "productCouponList", "listCoupon", "promotions"]:
                    v = items.get(k)
                    if isinstance(v, list):
                        for sub in v:
                            if isinstance(sub, dict):
                                found.append(sub)
            return found

        coupons = _scan_coupons(response_data)
        if not coupons:
            return

        excel_path = getattr(self.app, 'cp_table_location', '')
        if not excel_path or not os.path.exists(excel_path):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            candidates = [
                os.path.join(base_dir, "tables", "cp_data.xlsx"),
                os.path.join(base_dir, "assets", "tables", "cp_data.xlsx")
            ]
            for c in candidates:
                if os.path.exists(c):
                    excel_path = c
                    break

        if not excel_path or not os.path.exists(excel_path):
            return

        try:
            df = pd.read_excel(excel_path)
            df = df.loc[:, ~df.columns.duplicated(keep='first')]
            df = df.loc[:, [c for c in df.columns if not str(c).lower().startswith('unnamed')]]
            df = df.reset_index(drop=True)
        except Exception as read_err:
            logger.warning(f"[sync_product_master_coupon_dates_to_excel] Error reading excel: {read_err}")
            return

        suggested_cols = [
            'suggested_cp', 'suggested_usage_start_date', 'suggested_usage_end_date', 'suggested_remark',
            'usage_start_date', 'usage_end_date', 'last_updated'
        ]
        for col in suggested_cols:
            if col not in df.columns:
                df[col] = ""
            else:
                df[col] = df[col].astype(object)

        sku_clean = str(sku).strip().upper()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated_any = False
        updated_indices = set()

        curr_expected = None
        if hasattr(self, 'last_expected_prices') and self.last_expected_prices:
            curr_expected = self.last_expected_prices.get(sku_clean)

        session_ctx = self.get_smco_session_context()
        for cp in coupons:
            c_code = str(cp.get("couponCode") or cp.get("code") or "").strip().upper()
            if not c_code or c_code.startswith("IS"):
                continue

            # ตรวจสอบสาขา / Store จาก Session Context (ถ้ามีระบุใน couponBranchs)
            if not self.is_coupon_branch_and_store_match(cp, session_ctx):
                logger.debug(
                    f"[sync_product_master_coupon_dates] Skipping coupon {c_code} due to branch/store mismatch "
                    f"(branch_id={session_ctx.get('branch_id')}, store_id={session_ctx.get('store_id')})"
                )
                continue

            s_raw = cp.get("startDate") or cp.get("start_date")
            e_raw = cp.get("endDate") or cp.get("end_date")
            s_dt = parse_smart_datetime(s_raw) if s_raw else None
            e_dt = parse_smart_datetime(e_raw) if e_raw else None
            
            s_str = s_dt.strftime("%d/%m/%Y") if s_dt else (format_smart_datetime_str(s_raw) if s_raw else "")
            e_str = e_dt.strftime("%d/%m/%Y") if e_dt else (format_smart_datetime_str(e_raw) if e_raw else "")

            rem_raw = str(cp.get("couponDetailRemark") or cp.get("remark") or cp.get("couponDesc") or "").strip()

            sku_mask = (df['sku'].astype(str).str.strip().str.upper() == sku_clean)
            if not sku_mask.any():
                fmt_sku = self.sku_formater(sku_clean).strip().upper()
                if fmt_sku:
                    sku_mask = (df['sku'].astype(str).str.strip().str.upper() == fmt_sku)

            if not sku_mask.any():
                continue

            cp_match = sku_mask & (
                (df['cp_name'].astype(str).str.strip().str.upper() == c_code) |
                (df['suggested_cp'].astype(str).str.strip().str.upper() == c_code)
            )

            placeholder_match = sku_mask & (
                (df['cp_name'].isna() | df['cp_name'].astype(str).str.strip().str.lower().isin(['', 'nan', '<na>', 'null', '-', 'none'])) &
                (df['suggested_cp'].isna() | df['suggested_cp'].astype(str).str.strip().str.lower().isin(['', 'nan', '<na>', 'null', '-', 'none']))
            )

            target_mask = None
            if cp_match.any():
                target_mask = cp_match
            elif placeholder_match.any():
                if curr_expected is not None:
                    price_matched = placeholder_match & ((pd.to_numeric(df['sale_price'], errors='coerce') - curr_expected).abs() <= 0.05)
                    if price_matched.any():
                        target_mask = price_matched
                    else:
                        target_mask = placeholder_match
                else:
                    target_mask = placeholder_match

            if target_mask is not None and target_mask.any():
                for idx in df[target_mask].index:
                    if s_str:
                        df.loc[idx, 'usage_start_date'] = s_str
                        df.loc[idx, 'suggested_usage_start_date'] = s_str
                    if e_str:
                        df.loc[idx, 'usage_end_date'] = e_str
                        df.loc[idx, 'suggested_usage_end_date'] = e_str
                    
                    cur_sugg = str(df.loc[idx, 'suggested_cp'] or '').strip()
                    if not cur_sugg or cur_sugg.lower() in ('nan', '<na>', 'none', '-'):
                        df.loc[idx, 'suggested_cp'] = c_code
                    
                    if rem_raw:
                        cur_rem = str(df.loc[idx, 'suggested_remark'] or '').strip()
                        if not cur_rem or cur_rem.lower() in ('nan', '<na>', 'none', '-'):
                            df.loc[idx, 'suggested_remark'] = rem_raw
                    
                    df.loc[idx, 'last_updated'] = now_str
                    updated_any = True
                    updated_indices.add(idx)

                    logger.info(
                        f"🎯 [sync_product_master_coupon_dates] อัปเดตช่วงวันคูปอง {c_code} [{s_str} - {e_str}] "
                        f"สำหรับ SKU {sku_clean} แถวที่ {idx} เรียบร้อยแล้ว"
                    )

        if updated_any:
            try:
                df.to_excel(excel_path, index=False)
                format_cp_excel(excel_path)
                if hasattr(self.app, '_cp_last_mtime'):
                    self.app._cp_last_mtime = os.path.getmtime(excel_path)
                if getattr(self.app, 'cp_df', None) is not None:
                    self.app.cp_df = df.copy()
            except Exception as save_err:
                logger.warning(f"[sync_product_master_coupon_dates_to_excel] Error saving excel: {save_err}")

            try:
                if hasattr(self, '_dual_cp_loader') and self._dual_cp_loader:
                    for idx in updated_indices:
                        row_dict = df.loc[idx].to_dict()
                        payload = {k: ("" if pd.isna(v) else str(v)) for k, v in row_dict.items()}
                        self._dual_cp_loader.push_record_to_gas(payload)
            except Exception as gas_e:
                logger.debug(f"[sync_product_master_coupon_dates_to_excel] GAS push error: {gas_e}")

    def fetch_product_master_info(self, sku: str) -> Optional[List[Dict[str, Any]]]:
        """
        ดึงข้อมูล Product Master Info และ Coupon Details ล่าสุดของ SKU จาก SMCO ผ่าน POS API
        /smartcore/smartpos/pointofsales/posmainv3/getProductMasterInfoPOSV3.htm
        โดยรัน JavaScript POST ในเบราว์เซอร์ และแคชผลลัพธ์ลงใน _product_master_cache
        """
        if not sku or not self.driver:
            return None
        sku_clean = str(sku).strip().upper()
        # หากมีข้อมูลในแคชอยู่แล้ว (เช่น ดักจับได้แล้วตอนยิงสินค้าลง POS) ให้ใช้จากแคช ไม่ต้องยิง JS fetch ซ้ำ
        if hasattr(self, '_product_master_cache') and self._product_master_cache and sku_clean in self._product_master_cache:
            logger.debug(f"[fetch_product_master_info] SKU '{sku_clean}' มีข้อมูลใน cache อยู่แล้ว ข้ามการ fetch ซ้ำ")
            return self._product_master_cache.get(sku_clean)
        try:
            js_fetch = """
            var callback = arguments[arguments.length - 1];
            var sku = arguments[0];
            var formData = new URLSearchParams();
            formData.append('activeFlag', 'true');
            formData.append('requestText', sku);
            formData.append('start', '1');
            formData.append('length', '1');
            formData.append('order[0][column]', '0');
            formData.append('order[0][dir]', 'asc');
            formData.append('modeScan', 'Y');
            formData.append('isIgnoreQty', 'false');
            formData.append('onlyProduct', 'false');

            fetch('/smartcore/smartpos/pointofsales/posmainv3/getProductMasterInfoPOSV3.htm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
                body: formData.toString()
            })
            .then(function(r) { return r.json(); })
            .then(function(d) { callback(d); })
            .catch(function(err) { callback(null); });
            """
            fetched_data = self.driver.execute_async_script(js_fetch, sku_clean)
            if fetched_data:
                self.record_product_master_response(sku_clean, fetched_data)
                logger.info(f"[fetch_product_master_info] Fetched product master info for '{sku_clean}' from SMCO directly")
                return self._product_master_cache.get(sku_clean)
        except Exception as ex_fetch:
            logger.debug(f"[fetch_product_master_info] Error fetching SKU '{sku_clean}': {ex_fetch}")
        return None

    def get_smco_session_context(self) -> Dict[str, Any]:
        """
        ดึงข้อมูลผู้ใช้ สาขา (branch_id) และร้านค้า (store_id) จาก AngularJS scope ของหน้า SMCO
        และ fallback ไปยัง JWT Token (sub) ใน Cookie/Storage หากจำเป็น
        """
        if hasattr(self, '_session_ctx') and self._session_ctx and any(v is not None for v in self._session_ctx.values()):
            return self._session_ctx

        ctx = {"emp_id": None, "branch_id": None, "store_id": None, "store_code": None, "token": None}
        if not self.driver:
            return ctx
        try:
            # สลับไปยังแท็บ SMCO หากจำเป็น
            orig_handle = None
            try:
                if hasattr(self.bot, 'merged_dict') and 'SMCO :: เปิดการขาย' in self.bot.merged_dict:
                    smco_handle = self.bot.merged_dict['SMCO :: เปิดการขาย']
                    if self.driver.current_window_handle != smco_handle:
                        orig_handle = self.driver.current_window_handle
                        self.driver.switch_to.window(smco_handle)
            except Exception:
                pass

            # 1. ดึงข้อมูลตรงจาก AngularJS scope ของ SMCO (แม่นยำที่สุด)
            if hasattr(self.driver, 'execute_script') and callable(self.driver.execute_script):
                try:
                    scope_info = self.driver.execute_script("""
                        try {
                            let el = document.querySelector('[ng-app]') || document.querySelector('body');
                            if (window.angular && el && angular.element(el).scope()) {
                                let sc = angular.element(el).scope();
                                let b_id = sc._branchXId || (sc.storeLogin && sc.storeLogin.branchCustom && sc.storeLogin.branchCustom.id) || (sc.storeCustomLogin && sc.storeCustomLogin.branchCustom && sc.storeCustomLogin.branchCustom.id);
                                let s_id = (sc.storeLogin && sc.storeLogin.id) || (sc.storeCustomLogin && sc.storeCustomLogin.id);
                                let s_code = (sc.storeLogin && sc.storeLogin.storeCode) || (sc.storeCustomLogin && sc.storeCustomLogin.storeCode);
                                let e_id = (sc.empLogin && sc.empLogin[0] && sc.empLogin[0].employeeNo) || (sc._userLogin && sc._userLogin[0] && sc._userLogin[0].empId);
                                return {
                                    branch_id: b_id ? (isNaN(b_id) ? b_id : parseInt(b_id)) : null,
                                    store_id: s_id ? (isNaN(s_id) ? s_id : parseInt(s_id)) : null,
                                    store_code: s_code || null,
                                    emp_id: e_id || null
                                };
                            }
                        } catch (e) {
                            return null;
                        }
                        return null;
                    """)
                    if isinstance(scope_info, dict):
                        if scope_info.get("branch_id") is not None:
                            ctx["branch_id"] = scope_info["branch_id"]
                        if scope_info.get("store_id") is not None:
                            ctx["store_id"] = scope_info["store_id"]
                        if scope_info.get("store_code"):
                            ctx["store_code"] = scope_info["store_code"]
                        if scope_info.get("emp_id"):
                            ctx["emp_id"] = scope_info["emp_id"]
                except Exception as ex_sc:
                    logger.debug(f"[get_smco_session_context] Error reading AngularJS scope: {ex_sc}")

            # 2. Fallback: ดึง JWT Token จาก Cookie/Storage ของ SMCO แล้วแกะ sub -> (emp_id, branch_id, store_id)
            if ctx.get("branch_id") is None or ctx.get("store_id") is None:
                import base64
                import json

                cookies = self.driver.get_cookies() if hasattr(self.driver, 'get_cookies') and callable(self.driver.get_cookies) else []
                token_str = None
                if isinstance(cookies, list):
                    for ck in cookies:
                        if isinstance(ck, dict) and ck.get('name', '').upper() in ['JWT-TOKEN', 'TOKEN', 'AUTHORIZATION', 'ACCESS_TOKEN']:
                            token_str = ck.get('value')
                            break
                if not token_str and hasattr(self.driver, 'execute_script') and callable(self.driver.execute_script):
                    res = self.driver.execute_script("return window.localStorage.getItem('JWT-TOKEN') || window.sessionStorage.getItem('JWT-TOKEN');")
                    if isinstance(res, str):
                        token_str = res

                if isinstance(token_str, str) and token_str:
                    ctx["token"] = token_str
                    parts = token_str.strip().split('.')
                    if len(parts) >= 2:
                        payload_b64 = parts[1] + '=' * (-len(parts[1]) % 4)
                        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode('utf-8'))
                        payload = json.loads(payload_bytes.decode('utf-8'))
                        sub_str = str(payload.get("sub", "")).strip()
                        if sub_str:
                            sub_parts = [p.strip() for p in sub_str.split(',')]
                            if len(sub_parts) >= 3:
                                if ctx.get("emp_id") is None:
                                    ctx["emp_id"] = sub_parts[0]
                                if ctx.get("branch_id") is None:
                                    ctx["branch_id"] = int(sub_parts[1]) if sub_parts[1].isdigit() else sub_parts[1]
                                if ctx.get("store_id") is None:
                                    ctx["store_id"] = int(sub_parts[2]) if sub_parts[2].isdigit() else sub_parts[2]
                            elif len(sub_parts) == 2:
                                if ctx.get("emp_id") is None:
                                    ctx["emp_id"] = sub_parts[0]
                                if ctx.get("branch_id") is None:
                                    ctx["branch_id"] = int(sub_parts[1]) if sub_parts[1].isdigit() else sub_parts[1]
                        if ctx.get("store_id") is None and payload.get("storeId") is not None:
                            ctx["store_id"] = payload.get("storeId")
                        if ctx.get("branch_id") is None and payload.get("branchId") is not None:
                            ctx["branch_id"] = payload.get("branchId")

            if orig_handle:
                try:
                    self.driver.switch_to.window(orig_handle)
                except Exception:
                    pass
        except Exception as ex_jwt:
            logger.debug(f"[get_smco_session_context] Error reading SMCO session context: {ex_jwt}")
            
        if any(v is not None for v in ctx.values()):
            self._session_ctx = ctx
        return ctx

    def is_coupon_branch_and_store_match(self, cp_dict: dict, session_ctx: Optional[dict] = None) -> bool:
        """
        ตรวจสอบว่าคูปองใน cp_dict สามารถใช้งานในสาขา (branch_id) และร้านค้า (store_id) ปัจจุบันได้หรือไม่
        โดยเทียบกับ couponBranchs: [{"couponBranchId": 180, "couponStoreId": 208}, ...]
        หากไม่มีการระบุ couponBranchs หรือค่าว่าง ถือว่าใช้ได้ทุกสาขา/ร้านค้า (True)
        """
        if not isinstance(cp_dict, dict):
            return True

        branches = cp_dict.get("couponBranchs", [])
        if not branches or not isinstance(branches, list):
            return True

        if session_ctx is None:
            session_ctx = self.get_smco_session_context()

        branch_id = session_ctx.get("branch_id")
        store_id = session_ctx.get("store_id")

        if branch_id is None and store_id is None:
            return True

        for b in branches:
            if not isinstance(b, dict):
                continue
            b_br = b.get("couponBranchId") if b.get("couponBranchId") is not None else b.get("branchId")
            b_st = b.get("couponStoreId") if b.get("couponStoreId") is not None else b.get("storeId")

            # ตรวจสอบรหัสสาขา (Branch)
            br_ok = (b_br is None) or (branch_id is None) or (str(b_br).strip() == str(branch_id).strip())

            # ตรวจสอบรหัสร้านค้า (Store)
            st_ok = True
            if store_id is not None and b_st is not None and str(b_st).strip() not in ["", "0", "None"]:
                st_ok = (str(b_st).strip() == str(store_id).strip())

            if br_ok and st_ok:
                return True

        return False


    def get_aggregated_combo_coupons(self, sku_input: Union[str, list], order_date: Any = None) -> list[dict]:
        """
        รวบรวมส่วนลดของแต่ละ Coupon Code จากทุก Sub-SKU ในสินค้าเซ็ต (Combo SKU เช่น SP1-001420+SP1-001421+...)
        โดยนำค่า couponDetailCash + couponDetailDisc ของแต่ละ SKU มารวมกัน
        คืนค่าเป็น list ของ coupon dict ที่มีมูลค่าส่วนลดรวมของทั้งเซ็ตตรงตามความเป็นจริง
        """
        if isinstance(sku_input, list):
            sub_skus = [str(s).strip().upper() for s in sku_input if str(s).strip()]
        else:
            sub_skus = [s.strip().upper() for s in str(sku_input).split('+') if s.strip()]

        if not sub_skus:
            return []

        if not hasattr(self, '_product_master_cache') or self._product_master_cache is None:
            self._product_master_cache = {}

        # ตรวจสอบว่า sub_sku ใดที่ยังไม่อยู่ในแคช หากขาดหายไป ให้ดึงสดจาก SMCO ผ่าน driver ทันที
        missing_skus = []
        for s in sub_skus:
            s_clean = s.strip().upper()
            found = (s_clean in self._product_master_cache or
                     self.sku_formater(s_clean).strip().upper() in self._product_master_cache or
                     any(k == s_clean or s_clean in k or k in s_clean for k in self._product_master_cache.keys()))
            if not found:
                missing_skus.append(s)

        if missing_skus and self.driver:
            for ms in missing_skus:
                self.fetch_product_master_info(ms)

        # ดึงข้อมูลจาก _product_master_cache ด้วย flexible matching
        cached_records = {}
        for s in sub_skus:
            s_clean = s.strip().upper()
            if s_clean in self._product_master_cache:
                cached_records[s] = self._product_master_cache[s_clean]
            else:
                formatted_s = self.sku_formater(s_clean).strip().upper()
                if formatted_s in self._product_master_cache:
                    cached_records[s] = self._product_master_cache[formatted_s]
                else:
                    found = False
                    for k, v in self._product_master_cache.items():
                        k_clean = str(k).strip().upper()
                        if k_clean == s_clean or s_clean in k_clean or k_clean in s_clean:
                            cached_records[s] = v
                            found = True
                            break
                    if not found:
                        logger.debug(f"[get_aggregated_combo_coupons] SKU '{s}' not found in _product_master_cache (available: {list(self._product_master_cache.keys())})")
                        return []

        ctx = self.get_smco_session_context()
        branch_id = ctx.get("branch_id")
        store_id = ctx.get("store_id")

        from collections import defaultdict
        coupon_agg = defaultdict(lambda: {
            "total_discount": 0.0,
            "startDate": None,
            "endDate": None,
            "desc": "",
            "remark": "",
            "sku_count": 0
        })

        def _extract_coupons(rec_data: Any) -> list[dict]:
            extracted = []
            if isinstance(rec_data, list):
                for item in rec_data:
                    extracted.extend(_extract_coupons(item))
            elif isinstance(rec_data, dict):
                if "couponCode" in rec_data or "couponId" in rec_data:
                    extracted.append(rec_data)
                for key in ["productCouponDetail", "coupons", "couponDetail", "couponDetails", "couponList", "productCoupons", "productCouponList", "listCoupon", "promotions"]:
                    val = rec_data.get(key)
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict):
                                extracted.append(item)
            return extracted

        for s in sub_skus:
            rec_list = cached_records[s]
            seen_in_sku = set()
            cp_list = _extract_coupons(rec_list)

            for cp in cp_list:
                if not isinstance(cp, dict) or cp.get("usedFlag") is True:
                    continue

                code = str(cp.get("couponCode") or "").strip().upper()
                if not code or code in seen_in_sku:
                    continue

                # 🛑 กรองไม่เอาคูปองประเภท Payment / ผ่อนชำระ (เช่น IS2604170001 หรือ couponTypeEn/Th = 'Payment')
                c_type_en = str(cp.get("couponTypeEn") or "").strip().lower()
                c_type_th = str(cp.get("couponTypeTh") or "").strip().lower()
                if code.startswith("IS") or c_type_en == "payment" or c_type_th == "payment":
                    logger.debug(f"[get_aggregated_combo_coupons] Skipping Payment/Installment coupon: {code}")
                    continue

                # ✅ ใช้งานเฉพาะ Topup และ Add-on และต้องมี Prefix เป็น CP หรือ DC เท่านั้น
                is_valid_type = (c_type_en in ["topup", "add-on", "addon", ""] or c_type_th in ["topup", "add-on", "addon", ""])
                is_valid_prefix = code.startswith("CP") or code.startswith("DC")
                if not (is_valid_prefix and is_valid_type):
                    logger.debug(f"[get_aggregated_combo_coupons] Skipping non-CP/DC coupon: {code} (type: {c_type_en}/{c_type_th})")
                    continue

                # ตรวจสอบสาขา / Store จาก Session Context (ถ้ามีระบุใน couponBranchs)
                # ต้องตรงกับสาขาที่ระบบเปิดการขายอยู่จริง มิเช่นนั้นบนเว็บ POS จะมองไม่เห็นคูปองนี้
                if not self.is_coupon_branch_and_store_match(cp, ctx):
                    logger.debug(f"[get_aggregated_combo_coupons] Skipping coupon {code} due to branch/store mismatch (branch_id={branch_id}, store_id={store_id})")
                    continue

                seen_in_sku.add(code)
                disc = float(cp.get("couponDetailCash", 0.0)) + float(cp.get("couponDetailDisc", 0.0))
                item = coupon_agg[code]
                item["total_discount"] += disc
                if not item["startDate"]:
                    item["startDate"] = cp.get("startDate")
                if not item["endDate"]:
                    item["endDate"] = cp.get("endDate")
                c_desc = str(cp.get("couponDesc", "") or "").strip()
                c_rem = str(cp.get("couponDetailRemark", "") or cp.get("remark", "") or "").strip()
                if c_desc and (not item["desc"] or ("ราคา" in c_desc and "ราคา" not in str(item["desc"]))):
                    item["desc"] = c_desc
                if c_rem and not item["remark"]:
                    item["remark"] = c_rem
                if not item["remark"] and c_desc:
                    item["remark"] = c_desc
                item["sku_count"] += 1

        aggregated_details = []
        for code, data in coupon_agg.items():
            if data["sku_count"] == len(sub_skus):
                s_dt = parse_smart_datetime(data["startDate"]) or parse_smart_date(data["startDate"])
                e_dt = parse_smart_datetime(data["endDate"]) or parse_smart_date(data["endDate"])
                best_rem = data["remark"]
                desc_text = data["desc"]
                if desc_text and (not best_rem or ("ราคา" in desc_text and "ราคา" not in best_rem)):
                    best_rem = desc_text
                aggregated_details.append({
                    "code": code,
                    "discount": round(data["total_discount"], 2),
                    "desc": desc_text or best_rem,
                    "remark": best_rem,
                    "remark_target_price": extract_target_price_from_text(f"{best_rem} {desc_text}"),
                    "raw_discount": f"{data['total_discount']:.2f}.-",
                    "is_selected": False,
                    "start_date": s_dt,
                    "end_date": e_dt,
                    "is_expired": False,
                    "is_aggregated": True
                })

        logger.debug(f"[get_aggregated_combo_coupons] Aggregated {len(aggregated_details)} coupons across {len(sub_skus)} sub-SKUs: {[a['code'] for a in aggregated_details]}")
        return aggregated_details


    def _track_adjustment(self, sku: str, method: str) -> None:
        """บันทึกประวัติการปรับราคาของ SKU (OC, DC, CP) ในรอบการทำงานปัจจุบัน"""
        if not sku:
            return
        sku_clean = str(sku).strip().upper()
        if not hasattr(self, '_applied_adjustments') or self._applied_adjustments is None:
            self._applied_adjustments = {}
        if sku_clean not in self._applied_adjustments:
            self._applied_adjustments[sku_clean] = set()
        self._applied_adjustments[sku_clean].add(str(method).strip().upper())

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
    # EXCEL / GOOGLE SHEET CP LOOKUP & MISSING RECORDING
    # ══════════════════════════════════════════════════════════════════════════
    def reload_cp_if_modified(self) -> None:
        """ตรวจสอบและ reload CP Data อัตโนมัติ (Dual-Source: GAS Web App + Local Excel)"""
        excel_path = getattr(self.app, 'cp_table_location', '')
        gas_url = getattr(self.app, 'cp_gas_url', None)

        if not hasattr(self, '_dual_cp_loader') or self._dual_cp_loader is None:
            try:
                from functions.pos.cp_data_loader import DualSourceCPLoader, DEFAULT_GAS_URL
                self._dual_cp_loader = DualSourceCPLoader(
                    gas_url=gas_url or DEFAULT_GAS_URL,
                    local_excel_path=excel_path if (excel_path and os.path.exists(excel_path)) else None
                )
            except Exception as e:
                self._dual_cp_loader = None

        if self._dual_cp_loader:
            if excel_path and self._dual_cp_loader.local_excel_path != excel_path:
                self._dual_cp_loader.local_excel_path = excel_path
            df = self._dual_cp_loader.load_cp_df()
            if df is not None and not df.empty:
                self.app.cp_df = df
                return

        if hasattr(self.app, 'reload_cp_df_if_modified'):
            self.app.reload_cp_df_if_modified()
            return

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
                start_date, end_date = correct_cp_date_range(row.get('usage_start_date'), row.get('usage_end_date'))

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
        sale_prices_num = pd.to_numeric(df_valid['sale_price'], errors='coerce')
        df_price_matched = df_valid[(sale_prices_num - float(platform_price)).abs() <= price_tolerance]

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

    def add_missing_cp_to_excel(
        self,
        sku_key: str,
        expected_price: float,
        suggested_cp: str = "",
        start_date: Any = None,
        end_date: Any = None,
        remark: str = "",
        oc_amount: str = "",
        dc_amount: str = "",
        cp_name: str = "",
        **kwargs
    ) -> None:
        """
        บันทึก SKU และราคาที่ยังไม่มี CP หรือเป็นสูตร Pattern ใหม่ลงไฟล์ Excel
        โดยแยก Pattern แต่ละสูตร (คูปองต่างกัน หรือ OC/DC ต่างกัน) ออกเป็นคนละแถวอย่างชัดเจน
        ไม่เขียนทับแถวเดิมที่มีคูปองหรือการปรับราคาคนละแบบ และไม่นำค่า oc_amount/dc_amount ของสูตรเดิมมาปนเปื้อน
        """
        try:
            excel_path = getattr(self.app, 'cp_table_location', '')
            if not excel_path or not os.path.exists(excel_path):
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                for cand in [
                    os.path.join(base_dir, "tables", "cp_data.xlsx"),
                    os.path.join(base_dir, "assets", "tables", "cp_data.xlsx")
                ]:
                    if os.path.exists(cand):
                        excel_path = cand
                        if hasattr(self.app, 'cp_table_location') and not self.app.cp_table_location:
                            self.app.cp_table_location = cand
                        break

            if not excel_path or not os.path.exists(excel_path):
                return

            if not hasattr(self, '_dual_cp_loader') or self._dual_cp_loader is None:
                try:
                    from functions.pos.cp_data_loader import DualSourceCPLoader, DEFAULT_GAS_URL
                    self._dual_cp_loader = DualSourceCPLoader(
                        gas_url=getattr(self.app, 'cp_gas_url', None) or DEFAULT_GAS_URL,
                        local_excel_path=excel_path
                    )
                except Exception:
                    self._dual_cp_loader = None
            elif excel_path and self._dual_cp_loader.local_excel_path != excel_path:
                self._dual_cp_loader.local_excel_path = excel_path

            try:
                df = pd.read_excel(excel_path)
                df = df.loc[:, ~df.columns.duplicated(keep='first')]
                df = df.loc[:, [c for c in df.columns if not str(c).lower().startswith('unnamed')]]
                df = df.reset_index(drop=True)
            except Exception as read_err:
                print(f"[add_missing_cp_to_excel] Error reading excel: {read_err}")
                return

            suggested_cols = [
                'suggested_cp',
                'suggested_usage_start_date',
                'suggested_usage_end_date',
                'suggested_remark'
            ]
            for col in suggested_cols:
                if col not in df.columns:
                    df[col] = ""

            for col in ['oc_amount', 'dc_amount', 'cp_name', 'last_updated']:
                if col not in df.columns:
                    df[col] = ""

            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            start_str = format_smart_datetime_str(start_date) if start_date else ""
            end_str = format_smart_datetime_str(end_date) if end_date else ""
            remark_str = str(remark or "").strip()

            # Sanitize remark: if remark contains target price contradicting expected_price, discard/clear it
            if remark_str and expected_price is not None:
                if "," in remark_str:
                    parts = [p.strip() for p in remark_str.split(",") if p.strip()]
                    has_match = any(
                        extract_target_price_from_text(p) is not None
                        and abs(extract_target_price_from_text(p) - float(expected_price)) <= 0.05
                        for p in parts
                    )
                    has_any_price = any(extract_target_price_from_text(p) is not None for p in parts)
                    if has_any_price and not has_match:
                        kept = [p for p in parts if extract_target_price_from_text(p) is None or abs(extract_target_price_from_text(p) - float(expected_price)) <= 0.05]
                        remark_str = ", ".join(kept)
                else:
                    rem_price = extract_target_price_from_text(remark_str)
                    if rem_price is not None and abs(rem_price - float(expected_price)) > 1.0:
                        remark_str = ""

            sku_clean = str(sku_key).strip().upper()
            target_cp = str(suggested_cp or cp_name or "").strip().upper()
            target_oc = str(oc_amount or "").strip()
            if target_oc.lower() in ('nan', 'none', '<na>', 'null', '-'):
                target_oc = ""
            target_dc = str(dc_amount or "").strip()
            if target_dc.lower() in ('nan', 'none', '<na>', 'null', '-'):
                target_dc = ""

            # หาแถวที่ตรงกับ SKU และ Sale Price เดียวกัน
            sku_price_mask = (df['sku'].astype(str).str.strip().str.upper() == sku_clean) & ((pd.to_numeric(df['sale_price'], errors='coerce') - expected_price).abs() <= 0.05)
            
            # ตรวจสอบว่าในบรรดาแถวที่ตรง SKU และราคา มีแถวใดที่เป็น Recipe Pattern เดียวกันหรือไม่
            pattern_match_idx = None
            if sku_price_mask.any():
                for idx in df[sku_price_mask].index:
                    row = df.loc[idx]
                    r_cp = str(row.get('cp_name', '') or '').strip().upper()
                    if r_cp.lower() in ('nan', 'none', '<na>', 'null', '-'):
                        r_cp = ""
                    r_sugg_cp = str(row.get('suggested_cp', '') or '').strip().upper()
                    if r_sugg_cp.lower() in ('nan', 'none', '<na>', 'null', '-'):
                        r_sugg_cp = ""
                    r_oc = str(row.get('oc_amount', '') or '').strip()
                    if r_oc.lower() in ('nan', 'none', '<na>', 'null', '-'):
                        r_oc = ""
                    if r_oc.endswith('.0') and r_oc[:-2].isdigit():
                        r_oc = r_oc[:-2]
                    r_dc = str(row.get('dc_amount', '') or '').strip()
                    if r_dc.lower() in ('nan', 'none', '<na>', 'null', '-'):
                        r_dc = ""
                    if r_dc.endswith('.0') and r_dc[:-2].isdigit():
                        r_dc = r_dc[:-2]

                    # กรณีที่ 1: แถวเดิมเป็น Placeholder เปล่า (ไม่มีทั้ง cp_name, suggested_cp, oc_amount, dc_amount)
                    is_placeholder = (not r_cp and not r_sugg_cp and not r_oc and not r_dc)
                    
                    # กรณีที่ 2: เป็น Recipe Pattern เดียวกัน (คูปองตรงกัน และการปรับราคา OC/DC ตรงกัน)
                    is_same_cp = bool(target_cp and (r_cp == target_cp or r_sugg_cp == target_cp))
                    is_same_adj = (r_oc == target_oc and r_dc == target_dc)

                    if is_placeholder or (is_same_cp and is_same_adj):
                        pattern_match_idx = idx
                        break

            if pattern_match_idx is not None:
                # พบแถวที่เป็น Pattern เดียวกัน: อัปเดตแถวนี้และย้ายไปต่อท้ายสุด (Move to Bottom)
                matched_row = df.loc[[pattern_match_idx]].copy()
                if suggested_cp:
                    matched_row['suggested_cp'] = suggested_cp
                if start_str:
                    matched_row['suggested_usage_start_date'] = start_str
                if end_str:
                    matched_row['suggested_usage_end_date'] = end_str
                
                existing_rem = str(matched_row['suggested_remark'].iloc[0] or "").strip()
                existing_rem_price = extract_target_price_from_text(existing_rem)
                if remark_str:
                    matched_row['suggested_remark'] = remark_str
                elif existing_rem_price is not None and abs(existing_rem_price - float(expected_price)) > 1.0:
                    matched_row['suggested_remark'] = ""
                matched_row['last_updated'] = now_str
                
                df_without_old = df.drop(index=pattern_match_idx)
                df_combined = pd.concat([df_without_old, matched_row], ignore_index=True)
            else:
                # เป็น Recipe Pattern ใหม่ (คนละคูปอง หรือคนละ OC/DC): แยกบันทึกเป็นแถวใหม่ชัดเจน ไม่เขียนทับแถวเดิม
                new_row = {
                    'sku': sku_key,
                    'sale_price': expected_price,
                    'cp_name': cp_name,
                    'suggested_cp': suggested_cp,
                    'suggested_usage_start_date': start_str,
                    'suggested_usage_end_date': end_str,
                    'suggested_remark': remark_str,
                    'oc_amount': target_oc,
                    'dc_amount': target_dc,
                    'last_updated': now_str
                }
                new_df = pd.DataFrame([new_row]).reindex(columns=df.columns, fill_value="")
                df_combined = pd.concat([df, new_df], ignore_index=True)

            df_combined.to_excel(excel_path, index=False)
            format_cp_excel(excel_path)

            if os.path.exists(excel_path):
                try:
                    self.app._cp_last_mtime = os.path.getmtime(excel_path)
                except Exception:
                    pass

            date_info = f" [{start_str} - {end_str}]" if (start_str or end_str) else ""
            rem_info = f" (Remark: {remark_str})" if remark_str else ""
            log_sugg = f" (แนะนำ: {suggested_cp}{date_info}{rem_info})" if suggested_cp else ""
            adj_info = f" (OC: {target_oc})" if target_oc else (f" (DC: {target_dc})" if target_dc else "")
            action_label = "อัปเดต" if pattern_match_idx is not None else "เพิ่ม Pattern ใหม่"
            self.app.update_log(
                f"💾 {action_label} SKU: {sku_key} (ราคาเป้าหมาย: {expected_price}){log_sugg}{adj_info} ใน CP Data เรียบร้อยแล้ว"
            )

            if self.app.cp_df is not None:
                for col in suggested_cols:
                    if col not in self.app.cp_df.columns:
                        self.app.cp_df[col] = ""
                for col in ['oc_amount', 'dc_amount', 'cp_name', 'last_updated']:
                    if col not in self.app.cp_df.columns:
                        self.app.cp_df[col] = ""

                app_sku_price_mask = (self.app.cp_df['sku'].astype(str).str.strip().str.upper() == sku_clean) & ((pd.to_numeric(self.app.cp_df['sale_price'], errors='coerce') - expected_price).abs() <= 0.05)
                app_pattern_match_idx = None
                if app_sku_price_mask.any():
                    for idx in self.app.cp_df[app_sku_price_mask].index:
                        row = self.app.cp_df.loc[idx]
                        r_cp = str(row.get('cp_name', '') or '').strip().upper()
                        if r_cp.lower() in ('nan', 'none', '<na>', 'null', '-'):
                            r_cp = ""
                        r_sugg_cp = str(row.get('suggested_cp', '') or '').strip().upper()
                        if r_sugg_cp.lower() in ('nan', 'none', '<na>', 'null', '-'):
                            r_sugg_cp = ""
                        r_oc = str(row.get('oc_amount', '') or '').strip()
                        if r_oc.lower() in ('nan', 'none', '<na>', 'null', '-'):
                            r_oc = ""
                        if r_oc.endswith('.0') and r_oc[:-2].isdigit():
                            r_oc = r_oc[:-2]
                        r_dc = str(row.get('dc_amount', '') or '').strip()
                        if r_dc.lower() in ('nan', 'none', '<na>', 'null', '-'):
                            r_dc = ""
                        if r_dc.endswith('.0') and r_dc[:-2].isdigit():
                            r_dc = r_dc[:-2]

                        is_placeholder = (not r_cp and not r_sugg_cp and not r_oc and not r_dc)
                        is_same_cp = bool(target_cp and (r_cp == target_cp or r_sugg_cp == target_cp))
                        is_same_adj = (r_oc == target_oc and r_dc == target_dc)
                        if is_placeholder or (is_same_cp and is_same_adj):
                            app_pattern_match_idx = idx
                            break

                if app_pattern_match_idx is not None:
                    app_rows = self.app.cp_df.loc[[app_pattern_match_idx]].copy()
                    if suggested_cp:
                        app_rows['suggested_cp'] = suggested_cp
                    if start_str:
                        app_rows['suggested_usage_start_date'] = start_str
                    if end_str:
                        app_rows['suggested_usage_end_date'] = end_str
                    app_existing_rem = str(app_rows['suggested_remark'].iloc[0] or "").strip()
                    app_rem_price = extract_target_price_from_text(app_existing_rem)
                    if remark_str:
                        app_rows['suggested_remark'] = remark_str
                    elif app_rem_price is not None and abs(app_rem_price - float(expected_price)) > 1.0:
                        app_rows['suggested_remark'] = ""
                    app_rows['last_updated'] = now_str
                    self.app.cp_df = pd.concat([self.app.cp_df.drop(index=app_pattern_match_idx), app_rows], ignore_index=True)
                else:
                    new_df_copy = pd.DataFrame([{
                        'sku': sku_key,
                        'sale_price': expected_price,
                        'cp_name': cp_name,
                        'suggested_cp': suggested_cp,
                        'suggested_usage_start_date': start_str,
                        'suggested_usage_end_date': end_str,
                        'suggested_remark': remark_str,
                        'oc_amount': target_oc,
                        'dc_amount': target_dc,
                        'last_updated': now_str
                    }]).reindex(columns=self.app.cp_df.columns, fill_value="")
                    self.app.cp_df = pd.concat([self.app.cp_df, new_df_copy], ignore_index=True)

            # ส่งข้อมูลขึ้น Google Sheet ในเบื้องหลัง (ถ้าเชื่อมต่อ GAS ไว้)
            try:
                if hasattr(self, '_dual_cp_loader') and self._dual_cp_loader:
                    cur_sugg_cp = str(suggested_cp or "").strip()
                    cur_start = start_str
                    cur_end = end_str
                    cur_rem = remark_str
                    if pattern_match_idx is not None and 'matched_row' in locals():
                        if not cur_sugg_cp and 'suggested_cp' in matched_row.columns:
                            cur_sugg_cp = str(matched_row['suggested_cp'].iloc[0] or "").strip()
                        if not cur_start and 'suggested_usage_start_date' in matched_row.columns and pd.notna(matched_row['suggested_usage_start_date'].iloc[0]):
                            cur_start = str(matched_row['suggested_usage_start_date'].iloc[0]).strip()
                        if not cur_end and 'suggested_usage_end_date' in matched_row.columns and pd.notna(matched_row['suggested_usage_end_date'].iloc[0]):
                            cur_end = str(matched_row['suggested_usage_end_date'].iloc[0]).strip()
                        if 'suggested_remark' in matched_row.columns:
                            cur_rem = str(matched_row['suggested_remark'].iloc[0] or "").strip()

                    gas_remark = cur_rem if cur_rem else "-"
                    payload = {
                        "sku": sku_clean,
                        "sale_price": float(expected_price),
                        "expected_price": float(expected_price),
                        "suggested_cp": cur_sugg_cp,
                        "suggested_usage_start_date": cur_start,
                        "suggested_usage_end_date": cur_end,
                        "suggested_remark": gas_remark,
                        "oc_amount": target_oc,
                        "dc_amount": target_dc,
                        "last_updated": now_str
                    }
                    if cp_name:
                        payload["cp_name"] = str(cp_name).strip()

                    if pattern_match_idx is not None and 'matched_row' in locals():
                        old_row = matched_row.iloc[0]
                        for c in ['cp_name', 'usage_start_date', 'usage_end_date', 'addtion_cp', 'couponDetailCash', 'couponDetailDisc', 'last_order_id', 'last_used_cp', 'last_actual_price', 'last_adjustment_method']:
                            if c in old_row and pd.notna(old_row[c]) and str(old_row[c]).strip() and c not in payload:
                                payload[c] = str(old_row[c]).strip()
                    self._dual_cp_loader.push_record_to_gas(payload)
            except Exception as gas_err:
                print(f"[add_missing_cp_to_excel] Optional GAS push skipped: {gas_err}")

        except Exception as err:
            print(f"[add_missing_cp_to_excel] Error appending row: {err}")

    def _record_missing_cp_with_dates(
        self,
        sku_key: str,
        expected_price: float,
        suggested_cp_code: str = "",
        sugg_info: Optional[dict] = None,
        oc_amount: str = "",
        dc_amount: str = "",
        cp_name: str = "",
        start_date: Any = None,
        end_date: Any = None,
        remark: str = ""
    ) -> None:
        """บันทึก SKU ที่ยังไม่มี CP ลงไฟล์ Excel พร้อมวันที่ และ Remark ถ้ามีข้อมูล sugg_info โดยรักษาความถูกต้องของแต่ละ Pattern"""
        kwargs = {"suggested_cp": suggested_cp_code}
        if oc_amount:
            kwargs["oc_amount"] = oc_amount
        if dc_amount:
            kwargs["dc_amount"] = dc_amount
        if cp_name:
            kwargs["cp_name"] = cp_name
        if sugg_info:
            if sugg_info.get("suggested_start_date") or sugg_info.get("start_date"):
                kwargs["start_date"] = sugg_info.get("suggested_start_date") or sugg_info.get("start_date")
            if sugg_info.get("suggested_end_date") or sugg_info.get("end_date"):
                kwargs["end_date"] = sugg_info.get("suggested_end_date") or sugg_info.get("end_date")
            if sugg_info.get("suggested_remark") or sugg_info.get("remark"):
                kwargs["remark"] = sugg_info.get("suggested_remark") or sugg_info.get("remark")
            if sugg_info.get("oc_amount") and not oc_amount:
                kwargs["oc_amount"] = sugg_info["oc_amount"]
            if sugg_info.get("dc_amount") and not dc_amount:
                kwargs["dc_amount"] = sugg_info["dc_amount"]
        if start_date and "start_date" not in kwargs:
            kwargs["start_date"] = start_date
        if end_date and "end_date" not in kwargs:
            kwargs["end_date"] = end_date
        if remark and "remark" not in kwargs:
            kwargs["remark"] = remark

        # ถ้าไม่มี remark และไม่พบคูปองที่จับคู่ได้ ให้บันทึก remark แจ้งว่าไม่มี pattern พร้อมระบุจำนวน cp/dc ที่พบบนหน้าจอ
        if not kwargs.get("remark") and not suggested_cp_code:
            cp_dc_count = len([c for c in getattr(self, 'last_scanned_smco_coupon_details', []) if c.get('code') and not str(c['code']).strip().upper().startswith('IS')])
            kwargs["remark"] = f"ไม่มี pattern, cp/dcที่พบ: {cp_dc_count} อัน"

        self.add_missing_cp_to_excel(sku_key, expected_price, **kwargs)

    def resolve_multi_coupon_info(
        self,
        coupon_str: str,
        expected_price: Optional[float] = None,
        default_remark: str = "",
        default_start: Any = None,
        default_end: Any = None,
        sku: Optional[str] = None
    ) -> tuple[str, Any, Any]:
        """
        สำหรับกรณี SKU ที่มีค่า CP/DC หลายตัว (เช่น 'CP... DC...' หรือหลายรหัส):
        1. suggested_remark: ดึง remark ของทุก CP/DC ตามลำดับ คั่นด้วย ', '
        2. เวลา: ดูว่าตัวไหนมี suggested_usage_start_date ใหม่กว่า ถ้าเท่ากันให้เอา suggested_usage_end_date ที่สั้นกว่า
        """
        tokens = [t.strip().upper() for t in str(coupon_str or "").replace(',', ' ').split() if t.strip()]
        if not tokens:
            return default_remark, default_start, default_end

        def _scan_pm_coupons(items):
            found = []
            if isinstance(items, list):
                for it in items:
                    found.extend(_scan_pm_coupons(it))
            elif isinstance(items, dict):
                c_c = str(items.get("couponCode") or items.get("code") or "").strip().upper()
                if c_c:
                    found.append(items)
                for k in ["productCouponDetail", "coupons", "couponDetail", "couponDetails", "couponList", "productCoupons", "productCouponList", "listCoupon", "promotions"]:
                    v = items.get(k)
                    if isinstance(v, list):
                        for sub in v:
                            if isinstance(sub, dict):
                                found.append(sub)
            return found

        # ค้นหาข้อมูลคูปองแต่ละตัวจาก:
        # 1. last_scanned_smco_coupon_details (จาก Modal)
        details = list(getattr(self, 'last_scanned_smco_coupon_details', []))
        token_c_map = {}
        for d in details:
            code = str(d.get("code", "")).strip().upper()
            if code and code not in token_c_map:
                token_c_map[code] = d

        # 2. ค้นหาเพิ่มเติมจาก _product_master_cache (JSON API cache)
        if hasattr(self, '_product_master_cache') and self._product_master_cache:
            for sku_k, rec_list in self._product_master_cache.items():
                for cp_dict in _scan_pm_coupons(rec_list):
                    c_code = str(cp_dict.get("couponCode") or cp_dict.get("code") or "").strip().upper()
                    if c_code and c_code not in token_c_map:
                        token_c_map[c_code] = {
                            "code": c_code,
                            "desc": cp_dict.get("couponDesc") or cp_dict.get("desc") or "",
                            "remark": cp_dict.get("couponDetailRemark") or cp_dict.get("remark") or "",
                            "startDate": cp_dict.get("startDate") or cp_dict.get("start_date"),
                            "endDate": cp_dict.get("endDate") or cp_dict.get("end_date")
                        }

        # หากยังมี token ใดที่ไม่พบใน token_c_map และระบุ sku มา ให้ลองดึงสดจาก SMCO POS API เฉพาะ SKU ที่ยังไม่มีในแคช
        missing_tokens = [t for t in tokens if t not in token_c_map]
        if missing_tokens and sku and self.driver:
            sub_skus = [s.strip().upper() for s in str(sku).split('+') if s.strip()]
            for s in sub_skus:
                if not hasattr(self, '_product_master_cache') or not self._product_master_cache or s not in self._product_master_cache:
                    self.fetch_product_master_info(s)
            if hasattr(self, '_product_master_cache') and self._product_master_cache:
                session_ctx = self.get_smco_session_context()
                for sku_k, rec_list in self._product_master_cache.items():
                    for cp_dict in _scan_pm_coupons(rec_list):
                        if not self.is_coupon_branch_and_store_match(cp_dict, session_ctx):
                            continue
                        c_code = str(cp_dict.get("couponCode") or cp_dict.get("code") or "").strip().upper()
                        if c_code and c_code not in token_c_map:
                            token_c_map[c_code] = {
                                "code": c_code,
                                "desc": cp_dict.get("couponDesc") or cp_dict.get("desc") or "",
                                "remark": cp_dict.get("couponDetailRemark") or cp_dict.get("remark") or "",
                                "startDate": cp_dict.get("startDate") or cp_dict.get("start_date"),
                                "endDate": cp_dict.get("endDate") or cp_dict.get("end_date")
                            }

        # 3. ค้นหาเพิ่มเติมจาก cp_df / local Excel หากยังไม่พบ
        cp_df = getattr(self.app, 'cp_df', None)
        if cp_df is not None and not cp_df.empty:
            for t in tokens:
                    t_masks = []
                    for c_col in ['cp_name', 'suggested_cp', 'last_used_cp']:
                        if c_col in cp_df.columns:
                            t_masks.append(cp_df[c_col].astype(str).str.strip().str.upper() == t)
                    if t_masks:
                        combined_mask = t_masks[0]
                        for m_mask in t_masks[1:]:
                            combined_mask = combined_mask | m_mask
                        if combined_mask.any():
                            valid_rem_mask = combined_mask & (
                                cp_df['suggested_remark'].notna()
                                & ~cp_df['suggested_remark'].astype(str).str.strip().isin(['', '-', 'nan', '<na>'])
                                & ~cp_df['suggested_remark'].astype(str).str.contains('ไม่มี pattern', na=False)
                            )
                            target_df = cp_df[valid_rem_mask] if valid_rem_mask.any() else cp_df[combined_mask]
                            row = target_df.iloc[0]
                            s_val = row.get('usage_start_date') if 'usage_start_date' in row else row.get('suggested_usage_start_date')
                            e_val = row.get('usage_end_date') if 'usage_end_date' in row else row.get('suggested_usage_end_date')
                            r_val = row.get('suggested_remark') if 'suggested_remark' in row else None
                            if r_val and "ไม่มี pattern" in str(r_val):
                                r_val = ""
                            token_c_map[t] = {
                                "code": t,
                                "desc": str(r_val or "") if (pd.notna(r_val) and str(r_val).strip() != "") else "",
                                "remark": str(r_val or "") if (pd.notna(r_val) and str(r_val).strip() != "") else "",
                                "startDate": s_val if pd.notna(s_val) else None,
                                "endDate": e_val if pd.notna(e_val) else None
                            }

        remarks = []
        found_coupons = []
        for t in tokens:
            c = token_c_map.get(t)
            if not c:
                # 4. Fallback สร้าง dict สำหรับ token เสมอเพื่อให้ parse วันที่เริ่มจากรหัสคูปองได้
                c = {"code": t}
            found_coupons.append(c)
            rem_val = str(c.get("remark", "") or "").strip()
            desc_val = str(c.get("desc", "") or "").strip()
            if "ไม่มี pattern" in rem_val:
                rem_val = ""
            if "ไม่มี pattern" in desc_val:
                desc_val = ""
            chosen = rem_val or desc_val
            if expected_price is not None:
                desc_p = extract_target_price_from_text(desc_val)
                rem_p = extract_target_price_from_text(rem_val)
                if desc_p is not None and abs(desc_p - float(expected_price)) <= 0.05:
                    chosen = desc_val
                elif rem_p is not None and abs(rem_p - float(expected_price)) <= 0.05:
                    chosen = rem_val
                elif rem_p is not None and abs(rem_p - float(expected_price)) > 1.0 and desc_val and extract_target_price_from_text(desc_val) is not None:
                    chosen = desc_val
            if chosen and chosen not in remarks:
                remarks.append(chosen)

        # 1. suggested_remark: รวมตามลำดับ คั่นด้วย ", "
        if remarks:
            final_remark = ", ".join(remarks)
        else:
            final_remark = default_remark

        # 2. เวลา: หาตัวที่มี suggested_usage_start_date ใหม่กว่า ถ้าเท่ากันเอา suggested_usage_end_date ที่สั้นกว่า
        if found_coupons:
            best_c = None
            best_s_cmp = None
            best_e_cmp = None
            for c in found_coupons:
                s_dt, e_dt = get_coupon_start_and_end_dates(c)
                s_cmp = to_comparable_datetime(s_dt)
                e_cmp = to_comparable_datetime(e_dt)
                if best_c is None:
                    best_c = c
                    best_s_cmp = s_cmp
                    best_e_cmp = e_cmp
                else:
                    is_better = False
                    if s_cmp and best_s_cmp:
                        if s_cmp > best_s_cmp:
                            is_better = True
                        elif s_cmp == best_s_cmp:
                            if e_cmp and best_e_cmp:
                                if e_cmp < best_e_cmp:
                                    is_better = True
                            elif e_cmp and not best_e_cmp:
                                is_better = True
                    elif s_cmp and not best_s_cmp:
                        is_better = True
                    elif not s_cmp and not best_s_cmp:
                        if e_cmp and best_e_cmp and e_cmp < best_e_cmp:
                            is_better = True
                        elif e_cmp and not best_e_cmp:
                            is_better = True

                    if is_better:
                        best_c = c
                        best_s_cmp = s_cmp
                        best_e_cmp = e_cmp

            best_s, best_e = get_coupon_start_and_end_dates(best_c)
            final_start = best_s or default_start
            final_end = best_e or default_end
        else:
            final_start = default_start
            final_end = default_end

        return final_remark, final_start, final_end


    def scrape_pos_cart_items(self) -> List[Dict[str, Any]]:
        """
        ดึงข้อมูลรายการสินค้าและคูปองที่ถูกเลือก/ใช้งานจริงในตะกร้าหน้าแรก POS (#bodyOfSku):
        - sku: รหัส SKU สินค้า
        - coupons: รหัสคูปองทั้งหมดที่ถูกใช้กับสินค้านี้ (แยกด้วยเว้นวรรค เช่น 'CP... DC...')
        - total_net: ราคาสุทธิรวมของบรรทัดสินค้านี้บน POS
        - unit_net: ราคาสุทธิเฉลี่ยต่อหน่วย
        - qty: จำนวนสินค้า
        """
        results: List[Dict[str, Any]] = []
        if not self.driver:
            return results

        # วิธีที่ 1: ดึงจาก page_source ผ่าน BeautifulSoup (เร็วมาก และป้องกัน StaleElementReference)
        try:
            from bs4 import BeautifulSoup
            page_src = getattr(self.driver, 'page_source', '')
            if page_src and ("bodyOfSku" in page_src or "dataOfDetail" in page_src):
                soup = BeautifulSoup(page_src, "html.parser")
                panels = soup.select("#bodyOfSku .panel-default, #bodyOfSku div[ng-repeat*='dataOfDetail']")

                # กรองไม่ให้ได้ panel ซ้อนกัน (nested)
                filtered_panels = []
                for p in panels:
                    if p not in filtered_panels and not any(p in other.parents for other in panels):
                        filtered_panels.append(p)

                for p in filtered_panels:
                    # 1. รหัส SKU
                    u_tag = p.select_one("span[ng-click*='productNameChangeChk'] u")
                    sku = u_tag.get_text(strip=True) if u_tag else ""
                    if not sku:
                        wrap = p.select_one(".wrap-text")
                        if wrap:
                            m_sku = re.search(r'\b([A-Za-z0-9]{2,}[A-Za-z0-9]?-?\d{1,6})\b', wrap.get_text())
                            if m_sku:
                                sku = m_sku.group(1)

                    if not sku:
                        continue

                    # 2. คูปองที่ถูกใช้
                    coupons: List[str] = []
                    # 2.1 คูปองที่เลือกใช้งาน (dataOfCoupon)
                    for c_div in p.select("div[ng-repeat*='dataOfCoupon']"):
                        exp_span = c_div.select_one(".font-expired")
                        if exp_span and "Discount Expired" in exp_span.get_text() and "ng-hide" not in exp_span.get("class", []):
                            continue
                        link = c_div.select_one("a[data-toggle='tooltip'], a")
                        if link:
                            c_code = link.get_text(strip=True)
                            if c_code and c_code not in coupons:
                                coupons.append(c_code)

                    # 2.2 คูปองอัตโนมัติ/Bundle Condition (couponauto)
                    for cdt in p.select("div[ng-repeat*='couponauto'] span.font-color-base"):
                        m_cp = re.search(r'\b([A-Z]{2}\d{10})\b', cdt.get_text())
                        if m_cp and m_cp.group(1) not in coupons:
                            coupons.append(m_cp.group(1))

                    # 3. จำนวนสินค้า (Qty)
                    qty = 1.0
                    qty_el = p.select_one("span[style*='font-size:26px']") or p.select_one(".text-center span.ng-binding")
                    if qty_el:
                        try:
                            m_q = re.search(r'\d+', qty_el.get_text())
                            if m_q:
                                qty = float(m_q.group(0))
                        except Exception:
                            pass

                    # 4. ราคาสุทธิ (Total Net)
                    total_net_el = None
                    for row in p.select("div.row"):
                        if "Total Net:" in row.get_text():
                            total_net_el = row.select_one("a[ng-click*='displayPrice']")
                            if total_net_el:
                                break
                    if not total_net_el:
                        price_links = p.select("a[ng-click*='displayPrice']")
                        if price_links:
                            total_net_el = price_links[-1]

                    price_val = 0.0
                    if total_net_el:
                        try:
                            price_val = float(total_net_el.get_text(strip=True).replace(",", ""))
                        except Exception:
                            pass

                    unit_net = round(price_val / qty, 2) if qty > 0 else price_val
                    formatted_sku = self.sku_formater(sku) if hasattr(self, "sku_formater") else sku
                    results.append({
                        "sku": formatted_sku,
                        "coupons": " ".join(coupons),
                        "total_net": price_val,
                        "unit_net": unit_net,
                        "qty": qty
                    })

                if results:
                    return results
        except Exception as soup_err:
            logger.debug(f"[scrape_pos_cart_items] BeautifulSoup scrape failed: {soup_err}")

        # วิธีที่ 2: Selenium Element Fallback
        try:
            panel_els = self.driver.find_elements(
                By.XPATH,
                "//div[@id='bodyOfSku']//div[contains(@class, 'panel-default')] | //div[@id='bodyOfSku']/div[contains(@ng-repeat, 'dataOfDetail')]"
            )
            for p_el in panel_els:
                try:
                    sku_els = p_el.find_elements(By.XPATH, ".//span[contains(@ng-click, 'productNameChangeChk')]//u")
                    if not sku_els:
                        continue
                    sku = sku_els[0].text.strip()
                    if not sku:
                        continue

                    # คูปอง
                    coupons = []
                    c_links = p_el.find_elements(By.XPATH, ".//div[contains(@ng-repeat, 'dataOfCoupon')]//a")
                    for cl in c_links:
                        c_text = cl.text.strip()
                        if c_text and c_text not in coupons:
                            coupons.append(c_text)

                    auto_spans = p_el.find_elements(By.XPATH, ".//div[contains(@ng-repeat, 'couponauto')]//span[contains(@class, 'font-color-base')]")
                    for asp in auto_spans:
                        m_cp = re.search(r'\b([A-Z]{2}\d{10})\b', asp.text)
                        if m_cp and m_cp.group(1) not in coupons:
                            coupons.append(m_cp.group(1))

                    # Qty
                    qty = 1.0
                    qty_spans = p_el.find_elements(By.XPATH, ".//div[contains(@class, 'text-center')]//span[contains(@style, 'font-size:26px')]")
                    if qty_spans:
                        m_q = re.search(r'\d+', qty_spans[0].text)
                        if m_q:
                            qty = float(m_q.group(0))

                    # Net Price
                    price_val = 0.0
                    price_els = p_el.find_elements(By.XPATH, ".//div[contains(., 'Total Net:')]//a[contains(@ng-click, 'displayPrice')] | .//a[contains(@ng-click, 'displayPrice')]")
                    displayed_price_els = [el for el in price_els if el.is_displayed()]
                    if displayed_price_els:
                        raw_p = displayed_price_els[-1].text.strip().replace(",", "")
                        try:
                            price_val = float(raw_p)
                        except Exception:
                            pass

                    unit_net = round(price_val / qty, 2) if qty > 0 else price_val
                    formatted_sku = self.sku_formater(sku) if hasattr(self, "sku_formater") else sku
                    results.append({
                        "sku": formatted_sku,
                        "coupons": " ".join(coupons),
                        "total_net": price_val,
                        "unit_net": unit_net,
                        "qty": qty
                    })
                except Exception as item_err:
                    logger.debug(f"[scrape_pos_cart_items] Error scraping panel element: {item_err}")
        except Exception as sel_err:
            logger.warning(f"[scrape_pos_cart_items] Selenium scrape failed: {sel_err}")

        return results

    def record_pos_cart_summary_to_excel(self, order_id: str = "") -> None:
        """
        บันทึกข้อมูลสรุปการออกบิล (SKU, คูปองที่ใช้จริง, ราคาขายสุทธิต่อหน่วย, รหัสออเดอร์, วันที่)
        ลงในไฟล์ cp_data.xlsx โดยไม่เขียนทับข้อมูลคูปองเดิมใน cp_name
        - last_order_id: รหัสคำสั่งซื้อ
        - last_used_cp: คูปองที่ใช้จริง (เช่น 'CP2609070007 CP2609070008 CP2609100001 DC2410010001')
        - last_actual_price: ราคาขายสุทธิสุทธิ/หน่วยบน POS (Unit Net Price)
        - last_updated: วันที่และเวลาที่บันทึก
        """
        try:
            if not order_id:
                order_id = str(
                    getattr(self.bot, 'cus_order', '') or getattr(self.app, 'cus_order', '')
                ).strip()

            excel_path = getattr(self.app, 'cp_table_location', '')
            if not excel_path or not os.path.exists(excel_path):
                base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                candidates = [
                    os.path.join(base_dir, "tables", "cp_data.xlsx"),
                    os.path.join(base_dir, "assets", "tables", "cp_data.xlsx")
                ]
                for c in candidates:
                    if os.path.exists(c):
                        excel_path = c
                        break

            if not excel_path or not os.path.exists(excel_path):
                logger.warning("[record_pos_cart_summary_to_excel] ไม่พบไฟล์ cp_data.xlsx สำหรับบันทึกข้อมูล")
                return

            cart_items = self.scrape_pos_cart_items()
            if not cart_items:
                logger.info("[record_pos_cart_summary_to_excel] ไม่พบรายการสินค้าในตะกร้าหน้าแรก POS ข้ามการบันทึก")
                return

            try:
                df = pd.read_excel(excel_path)
                df = df.loc[:, ~df.columns.duplicated(keep='first')]
                df = df.loc[:, [c for c in df.columns if not str(c).lower().startswith('unnamed')]]
                df = df.reset_index(drop=True)
            except Exception as read_err:
                print(f"[record_pos_cart_summary_to_excel] Error reading excel: {read_err}")
                return

            new_cols = [
                'cp_name', 'usage_start_date', 'usage_end_date', 'suggested_cp',
                'suggested_usage_start_date', 'suggested_usage_end_date', 'suggested_remark',
                'last_order_id', 'last_used_cp', 'last_adjustment_method', 'last_actual_price', 'last_updated'
            ]
            for col in new_cols:
                if col not in df.columns:
                    df[col] = ""
                else:
                    df[col] = df[col].astype(object)

            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # รวบรวมรายการสินค้าที่จะบันทึก โดยอิงตาม Order SKU (self.app.items) เป็นหลัก
            # หากเป็น Combo SKU ให้รวมราคาสุทธิและคูปองของ SKU ย่อยทั้งหมดเข้าด้วยกัน
            order_items = getattr(self.app, 'items', []) or []
            summary_items = []

            if order_items:
                for ord_it in order_items:
                    raw_sku = str(ord_it.get('เลขอ้างอิง SKU (SKU Reference No.)') or ord_it.get('sellerSku') or '').strip()
                    if not raw_sku:
                        continue
                    # ข้าม SKU ค่าจัดส่ง (เช่น SV0-000101) ไม่บันทึกลง cp_data
                    if raw_sku.upper().startswith('SV0-') or raw_sku.upper() == 'SV0-000101':
                        continue

                    # หา SKU ย่อยในชุด
                    if hasattr(self.app, 'correct_sku_pattern') and callable(getattr(self.app, 'correct_sku_pattern', None)):
                        try:
                            pattern_res = self.app.correct_sku_pattern(raw_sku)
                            if isinstance(pattern_res, (list, tuple, set)):
                                sub_skus = [str(s) for s in pattern_res if s]
                            else:
                                sub_skus = [s.strip() for s in raw_sku.replace(' ', '').split('+') if s.strip()]
                        except Exception:
                            sub_skus = [s.strip() for s in raw_sku.replace(' ', '').split('+') if s.strip()]
                    else:
                        sub_skus = [s.strip() for s in raw_sku.replace(' ', '').split('+') if s.strip()]

                    sub_skus_clean = [s.strip().upper() for s in sub_skus]
                    matched_cart = [
                        it for it in cart_items
                        if str(it.get('sku', '')).strip().upper() in sub_skus_clean
                    ]

                    if matched_cart:
                        act_price = sum(float(it.get('unit_net', 0.0)) for it in matched_cart)
                        used_cps = []
                        for it in matched_cart:
                            for cp in str(it.get('coupons', '')).split():
                                cp_str = cp.strip()
                                if cp_str and cp_str not in used_cps:
                                    used_cps.append(cp_str)
                        used_cp = " ".join(used_cps)
                    else:
                        try:
                            act_price = float(str(ord_it.get('ราคาขายสุทธิ') or ord_it.get('ราคาขาย') or 0).replace(',', ''))
                        except Exception:
                            act_price = 0.0
                        used_cp = ""

                    summary_items.append({
                        "sku": raw_sku,
                        "unit_net": act_price,
                        "coupons": used_cp
                    })
            else:
                # Fallback กรณีไม่มี self.app.items: ใช้ cart_items แต่กรองค่าจัดส่งออก
                for it in cart_items:
                    sku_clean = str(it.get('sku', '')).strip().upper()
                    if sku_clean.startswith('SV0-') or sku_clean == 'SV0-000101':
                        continue
                    summary_items.append(it)

            if not summary_items:
                logger.info("[record_pos_cart_summary_to_excel] ไม่มีรายการสินค้าที่ต้องบันทึก (ข้ามค่าจัดส่งแล้ว)")
                return

            for item in summary_items:
                sku_raw = item.get("sku", "")
                sku_clean = str(sku_raw).strip().upper()
                used_cp = str(item.get("coupons", "")).strip()
                act_price = float(item.get("unit_net", 0.0))

                # ตรวจสอบวิธีการปรับราคา (last_adjustment_method):
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

                bot_methods = set()
                if hasattr(self, '_applied_adjustments') and self._applied_adjustments:
                    bot_methods = self._applied_adjustments.get(sku_clean, set())
                    if not bot_methods:
                        for k, v in self._applied_adjustments.items():
                            if k in sku_clean or sku_clean in k:
                                bot_methods = v
                                break

                if bot_methods:
                    has_cp = "CP" in bot_methods
                    has_oc = "OC" in bot_methods
                    has_dc = "DC" in bot_methods
                    if has_cp and has_oc:
                        method_val = "CP + OC"
                    elif has_cp and has_dc:
                        method_val = "CP + DC"
                    elif has_oc:
                        method_val = "OC"
                    elif has_dc:
                        method_val = "DC"
                    elif has_cp:
                        method_val = "CP"
                    else:
                        method_val = "NONE"
                else:
                    # บอทไม่ได้เป็นผู้สั่งปรับราคา:
                    has_any_coupon = bool(used_cp and used_cp.strip() != "")
                    matched_base_prices = df[df['sku'].astype(str).str.strip().str.upper() == sku_clean]['sale_price'].tolist()
                    is_price_changed = False
                    if matched_base_prices:
                        is_price_changed = not any(
                            abs(bp - act_price) <= 0.05
                            for bp in matched_base_prices
                            if isinstance(bp, (int, float)) and not pd.isna(bp)
                        )

                    if is_auto_inv:
                        # ในโหมด Auto Invoice: หากมีคูปองติดมาอัตโนมัติและราคาตรงตั้งแต่แรกให้บันทึกเป็น AUTO_MATCH
                        if has_any_coupon:
                            method_val = "DEFAULT"
                        else:
                            method_val = "NONE"
                    else:
                        # ในโหมด Manual: หากมีคูปองหรือราคาเปลี่ยนให้บันทึกเป็น MANUAL
                        if has_any_coupon or is_price_changed:
                            method_val = "MANUAL"
                        else:
                            method_val = "NONE"

                # สกัดข้อมูลช่วงวันและ Remark ของคูปองที่ติดมา เพื่อเติมลงใน usage_start_date / usage_end_date
                auto_rem, auto_start_dt, auto_end_dt = "", None, None
                if used_cp:
                    auto_rem, auto_start_dt, auto_end_dt = self.resolve_multi_coupon_info(
                        used_cp, expected_price=act_price, sku=sku_clean
                    )
                auto_s_str = format_smart_datetime_str(auto_start_dt) if auto_start_dt else ""
                auto_e_str = format_smart_datetime_str(auto_end_dt) if auto_end_dt else ""

                # จับคู่แถวเดิม:
                # 1. เช็ค sku และ sale_price ตรงกับ act_price (ความคลาดเคลื่อน <= 0.05)
                # และหากมี used_cp ให้จับคู่เฉพาะแถวที่เป็นคูปอง/สูตรเดียวกัน เพื่อไม่เขียนทับแถวอื่นของ SKU เดียวกัน
                sku_price_mask = (df['sku'].astype(str).str.strip().str.upper() == sku_clean) & ((df['sale_price'] - act_price).abs() <= 0.05)
                mask = sku_price_mask
                if sku_price_mask.any() and used_cp:
                    used_cp_clean = str(used_cp).strip().upper()
                    cp_match_mask = sku_price_mask & (
                        (df['cp_name'].astype(str).str.strip().str.upper() == used_cp_clean) |
                        (df['suggested_cp'].astype(str).str.strip().str.upper() == used_cp_clean)
                    )
                    if cp_match_mask.any():
                        mask = cp_match_mask

                # 2. ถ้าไม่เจอ เช็ค sku และ sale_price ตรงกับ expected_price
                if not mask.any() and hasattr(self, 'last_expected_prices') and self.last_expected_prices:
                    exp_p = self.last_expected_prices.get(sku_clean) or self.last_expected_prices.get(sku_raw)
                    if exp_p is not None:
                        exp_sku_price_mask = (df['sku'].astype(str).str.strip().str.upper() == sku_clean) & ((df['sale_price'] - exp_p).abs() <= 0.05)
                        mask = exp_sku_price_mask
                        if exp_sku_price_mask.any() and used_cp:
                            used_cp_clean = str(used_cp).strip().upper()
                            cp_match_mask = exp_sku_price_mask & (
                                (df['cp_name'].astype(str).str.strip().str.upper() == used_cp_clean) |
                                (df['suggested_cp'].astype(str).str.strip().str.upper() == used_cp_clean)
                            )
                            if cp_match_mask.any():
                                mask = cp_match_mask

                # 3. ถ้ายังไม่เจอ เช็คเฉพาะ sku เดียวกัน
                if not mask.any():
                    sku_only = (df['sku'].astype(str).str.strip().str.upper() == sku_clean)
                    if sku_only.any():
                        matching_indices = df[sku_only].index
                        if len(matching_indices) == 1:
                            mask = sku_only
                        else:
                            closest_idx = (df.loc[matching_indices, 'sale_price'] - act_price).abs().idxmin()
                            mask = df.index == closest_idx

                if mask.any():
                    df.loc[mask, 'last_order_id'] = str(order_id)
                    df.loc[mask, 'last_used_cp'] = used_cp
                    df.loc[mask, 'last_adjustment_method'] = method_val
                    df.loc[mask, 'last_actual_price'] = act_price
                    df.loc[mask, 'last_updated'] = now_str

                    # ปรับ cp_name และเติมวันที่/Remark ในแถวแบบ Vectorial
                    if not used_cp:
                        empty_cp_mask = mask & (df['cp_name'].isna() | df['cp_name'].astype(str).str.strip().str.lower().isin(['', 'nan', '<na>', 'null', '-']))
                        df.loc[empty_cp_mask, 'cp_name'] = "NONE"
                    else:
                        empty_or_none_mask = mask & (df['cp_name'].isna() | df['cp_name'].astype(str).str.strip().str.lower().isin(['', 'nan', '<na>', 'null', '-', 'none']))
                        df.loc[empty_or_none_mask, 'cp_name'] = used_cp
                        if auto_s_str:
                            if auto_e_str:
                                df.loc[mask, 'usage_start_date'] = auto_s_str
                            else:
                                empty_s_mask = mask & (df['usage_start_date'].isna() | df['usage_start_date'].astype(str).str.strip().isin(['', '-', 'nan', '<na>']))
                                df.loc[empty_s_mask, 'usage_start_date'] = auto_s_str
                        if auto_e_str:
                            df.loc[mask, 'usage_end_date'] = auto_e_str

                    if auto_s_str:
                        if auto_e_str:
                            df.loc[mask, 'suggested_usage_start_date'] = auto_s_str
                        else:
                            empty_sugg_s = mask & (df['suggested_usage_start_date'].isna() | df['suggested_usage_start_date'].astype(str).str.strip().isin(['', '-', 'nan', '<na>']))
                            df.loc[empty_sugg_s, 'suggested_usage_start_date'] = auto_s_str
                    if auto_e_str:
                        df.loc[mask, 'suggested_usage_end_date'] = auto_e_str
                    if auto_rem:
                        empty_or_stale_rem = mask & (
                            df['suggested_remark'].isna()
                            | df['suggested_remark'].astype(str).str.strip().isin(['', '-', 'nan', '<na>'])
                            | df['suggested_remark'].astype(str).str.contains('ไม่มี pattern', na=False)
                        )
                        df.loc[empty_or_stale_rem, 'suggested_remark'] = auto_rem
                    else:
                        stale_no_pattern = mask & df['suggested_remark'].astype(str).str.contains('ไม่มี pattern', na=False)
                        df.loc[stale_no_pattern, 'suggested_remark'] = ""
                else:
                    new_row = {
                        'sku': sku_raw,
                        'sale_price': act_price,
                        'cp_name': used_cp if used_cp else 'NONE',
                        'suggested_cp': used_cp if used_cp else '',
                        'usage_start_date': auto_s_str,
                        'usage_end_date': auto_e_str,
                        'suggested_usage_start_date': auto_s_str,
                        'suggested_usage_end_date': auto_e_str,
                        'suggested_remark': auto_rem,
                        'last_order_id': str(order_id),
                        'last_used_cp': used_cp,
                        'last_adjustment_method': method_val,
                        'last_actual_price': act_price,
                        'last_updated': now_str
                    }
                    new_df = pd.DataFrame([new_row])
                    for c in df.columns:
                        if c not in new_df.columns:
                            new_df[c] = ""
                    new_df = new_df[df.columns]
                    df = pd.concat([df, new_df], ignore_index=True)

            # บันทึกลง Excel
            df.to_excel(excel_path, index=False)
            format_cp_excel(excel_path)

            if os.path.exists(excel_path):
                try:
                    self.app._cp_last_mtime = os.path.getmtime(excel_path)
                except Exception:
                    pass

            if getattr(self.app, 'cp_df', None) is not None:
                self.app.cp_df = df

            self._last_recorded_order_id = str(order_id)

            self.app.update_log(
                f"📝 [บันทึกประวัติออเดอร์] บันทึกข้อมูลคูปองและราคาขายลงใน CP Data เรียบร้อย ({len(summary_items)} รายการ)"
            )
            for it in summary_items:
                cp_display = it['coupons'] if it['coupons'] else "(ไม่มีคูปอง)"
                sku_clean = str(it.get('sku', '')).strip().upper()
                row_mask = (df['sku'].astype(str).str.strip().str.upper() == sku_clean)
                method_display = ""
                if row_mask.any() and 'last_adjustment_method' in df.columns:
                    method_display = str(df.loc[row_mask, 'last_adjustment_method'].iloc[0])
                method_text = f" | วิธีปรับ: {method_display}" if method_display else ""
                self.app.update_log(
                    f"   • {it['sku']} -> คูปอง: {cp_display}{method_text} | ราคาสุทธิ: {it['unit_net']:,.2f} บาท"
                )

            # ส่งข้อมูลสรุปการออกบิลและคูปองที่สำเร็จขึ้น Google Sheet (Pattern เดียวกับ Local cp_data.xlsx)
            try:
                if not hasattr(self, '_dual_cp_loader') or self._dual_cp_loader is None:
                    try:
                        from functions.pos.cp_data_loader import DualSourceCPLoader, DEFAULT_GAS_URL
                        self._dual_cp_loader = DualSourceCPLoader(
                            gas_url=getattr(self.app, 'cp_gas_url', None) or DEFAULT_GAS_URL,
                            local_excel_path=excel_path
                        )
                    except Exception:
                        self._dual_cp_loader = None
                elif excel_path and self._dual_cp_loader.local_excel_path != excel_path:
                    self._dual_cp_loader.local_excel_path = excel_path

                if self._dual_cp_loader:
                    for it in summary_items:
                        used_c = it.get('coupons', '').strip()
                        sku_c = str(it.get('sku', '')).strip().upper()
                        act_p = float(it.get('unit_net', 0.0))
                        
                        row_m = (df['sku'].astype(str).str.strip().str.upper() == sku_c) & ((df['sale_price'] - act_p).abs() <= 0.05)
                        if row_m.any() and used_c:
                            used_c_clean = str(used_c).strip().upper()
                            row_m_cp = row_m & (
                                (df['cp_name'].astype(str).str.strip().str.upper() == used_c_clean) |
                                (df['suggested_cp'].astype(str).str.strip().str.upper() == used_c_clean)
                            )
                            if row_m_cp.any():
                                row_m = row_m_cp
                        elif not row_m.any():
                            row_m = (df['sku'].astype(str).str.strip().str.upper() == sku_c)
                        m_val = str(df.loc[row_m, 'last_adjustment_method'].iloc[0]) if (row_m.any() and 'last_adjustment_method' in df.columns) else ""
                        
                        payload = {
                            "sku": sku_c,
                            "sale_price": act_p,
                            "expected_price": act_p,
                            "cp_name": used_c if used_c else "NONE",
                            "usage_start_date": auto_s_str,
                            "usage_end_date": auto_e_str,
                            "last_order_id": str(order_id),
                            "last_used_cp": used_c,
                            "last_adjustment_method": m_val,
                            "last_actual_price": act_p,
                            "last_updated": now_str,
                            "action": "AUTO_LEARN_SUCCESS"
                        }
                        if row_m.any():
                            m_row = df.loc[row_m].iloc[0]
                            for col in ['usage_start_date', 'usage_end_date', 'suggested_cp', 'suggested_usage_start_date', 'suggested_usage_end_date', 'suggested_remark', 'addtion_cp', 'oc_amount', 'dc_amount', 'couponDetailCash', 'couponDetailDisc']:
                                if col in m_row and pd.notna(m_row[col]) and str(m_row[col]).strip() and col not in payload:
                                    payload[col] = str(m_row[col]).strip()

                        # ตรวจสอบและ sanitize suggested_remark หากราคาที่ระบุใน remark ขัดแย้งกับราคาขายจริง
                        sugg_rem = payload.get('suggested_remark', '')
                        sugg_rem_price = extract_target_price_from_text(sugg_rem)
                        if sugg_rem_price is not None and abs(sugg_rem_price - act_p) > 1.0:
                            payload['suggested_remark'] = "-"
                            if row_m.any() and 'suggested_remark' in df.columns:
                                df.loc[row_m, 'suggested_remark'] = ""

                        self._dual_cp_loader.push_record_to_gas(payload)
            except Exception as gas_err:
                logger.debug(f"[record_pos_cart_summary_to_excel] Google Sheet sync skipped: {gas_err}")

        except PermissionError as perm_err:
            self.app.update_log(f"⚠️ ไม่สามารถบันทึก cp_data.xlsx ได้เนื่องจากไฟล์ถูกเปิดใช้งานอยู่: {perm_err}")
        except Exception as err:
            logger.error(f"[record_pos_cart_summary_to_excel] Error: {err}")

    def find_suggested_cp_for_discount(
        self,
        target_discount: float,
        require_seller_voucher: bool = False,
        order_date: Any = None,
        expected_price: Optional[float] = None,
        sku: Optional[str] = None
    ) -> Optional[dict]:
        """
        คำนวณหาคูปอง (ตัวเดียว หรือคู่ผสม) จากรายการคูปองที่สแกนได้บนหน้าเว็บ SMCO
        ที่มีมูลค่าส่วนลดตรงกับ target_discount หรือมี Remark ระบุราคาเป้าหมายตรงกับ expected_price (สำหรับสินค้า Combo Multi-SKU)
        หาก require_seller_voucher=True จะพิจารณาเฉพาะคูปองที่มีข้อความบ่งชี้ว่าเป็น Seller Voucher เท่านั้น
        โดยจะเปรียบเทียบตามกฎ:
        1. วันที่ของ Order ต้องอยู่ระหว่างวันเริ่มและวันสิ้นสุด (usage_start_date <= order_date <= usage_end_date)
        2. เลือกคูปองที่มีวันเริ่ม (start_date) ล่าสุด/ใหม่ที่สุด
        3. หากวันเริ่มเท่ากัน ให้เลือกอันที่สิ้นสุด (end_date) ไวที่สุด
        4. หากสิ้นสุดเท่ากัน ให้เลือกตาม recency_score ล่าสุด (คูปองที่ตรงตาม Remark ราคาเป้าหมายจะได้แต้มสูงสุด)
        """
        details = list(getattr(self, 'last_scanned_smco_coupon_details', []))
        
        # หาก details ว่างเปล่า หรือกรณีสินค้าเซ็ต ให้ดึง/ผสานจาก get_aggregated_combo_coupons ร่วมด้วย
        target_sku = sku or getattr(self, '_current_reconcile_sku', '')
        if target_sku and ('+' in str(target_sku) or isinstance(target_sku, list) or not details):
            try:
                agg = self.get_aggregated_combo_coupons(target_sku, order_date=order_date)
                if agg:
                    existing_codes = {d.get("code") for d in details}
                    for a in agg:
                        if a.get("code") not in existing_codes:
                            details.append(a)
                        else:
                            for idx_d, d_item in enumerate(details):
                                if d_item.get("code") == a.get("code"):
                                    details[idx_d]["discount"] = a["discount"]
                                    details[idx_d]["raw_discount"] = a["raw_discount"]
                                    if a.get("remark"):
                                        details[idx_d]["remark"] = a["remark"]
                                    if a.get("start_date"):
                                        details[idx_d]["start_date"] = a["start_date"]
                                    if a.get("end_date"):
                                        details[idx_d]["end_date"] = a["end_date"]
            except Exception as ex_agg:
                logger.debug(f"[find_suggested_cp_for_discount] Error aggregating for {target_sku}: {ex_agg}")

        if not details or (target_discount <= 0 and expected_price is None):
            return None

        parsed_order_date = parse_smart_date(order_date) if order_date else None

        def is_coupon_valid(c_dict: dict) -> bool:
            return is_coupon_valid_for_order(c_dict, parsed_order_date)

        # คูปองทั้งหมดที่พบบนหน้าเว็บ SMCO (ยกเว้น Payment / IS)
        all_cp_dc_coupons = [
            c for c in details
            if c.get("code") and not str(c["code"]).strip().upper().startswith("IS")
        ]
        cp_dc_count = len(all_cp_dc_coupons)

        valid_details = [c for c in all_cp_dc_coupons if is_coupon_valid(c)]

        valid_detail_codes = {d.get("code") for d in valid_details if d.get("code")}
        raw_preselected = getattr(self, 'last_preselected_smco_coupons', None) or []
        preselected = [p for p in raw_preselected if p in valid_detail_codes]

        if not preselected:
            for c in valid_details:
                if c.get("is_selected") and c.get("code") and c.get("code") not in preselected:
                    preselected.append(c.get("code"))

        code_disc_map = {str(d.get("code", "")).strip().upper(): float(d.get("discount", 0.0)) for d in valid_details if d.get("code")}
        pre_discount = sum(code_disc_map.get(p.strip().upper(), 0.0) for p in preselected)

        # คำนวณ Base Price และเป้าหมายส่วนลดที่เป็นไปได้
        possible_req_discounts = set()
        if target_discount > 0:
            possible_req_discounts.add(round(float(target_discount), 2))
            if pre_discount > 0:
                if expected_price is None or target_discount < pre_discount:
                    possible_req_discounts.add(round(float(target_discount) + float(pre_discount), 2))

        # ─── ค้นหาความน่าจะเป็นทุกรูปแบบ (Subset Combinations: 1, 2, 3, 4 ใบ) ───
        matching_combos = []
        import itertools

        max_combo_size = min(4, len(valid_details))
        seen_combos = set()

        for k in range(1, max_combo_size + 1):
            for combo_tuple in itertools.combinations(valid_details, k):
                if require_seller_voucher:
                    if not any(is_seller_voucher_desc(c.get("desc", "")) for c in combo_tuple):
                        continue

                sub_disc = sum(float(c.get('discount', 0.0)) for c in combo_tuple)
                if sub_disc <= 0:
                    continue

                sub_disc_round = round(sub_disc, 2)
                is_disc_match = any(abs(sub_disc - rd) <= 0.05 for rd in possible_req_discounts)

                # ตรวจสอบ Remark Target Price (เช่น 'ราคา 3890')
                is_remark_target_match = False
                matched_remark_text = ""
                has_conflicting_remark_price = False
                if expected_price is not None:
                    for c in combo_tuple:
                        rem_p = c.get("remark_target_price") or extract_target_price_from_text(c.get("remark", ""))
                        desc_p = extract_target_price_from_text(c.get("desc", ""))
                        if (desc_p is not None and abs(desc_p - float(expected_price)) <= 0.05):
                            is_remark_target_match = True
                            matched_remark_text = str(c.get("desc", "")).strip()
                            break
                        elif (rem_p is not None and abs(rem_p - float(expected_price)) <= 0.05):
                            is_remark_target_match = True
                            matched_remark_text = str(c.get("remark", "") or c.get("desc", "")).strip()
                            break
                        elif (rem_p is not None and abs(rem_p - float(expected_price)) > 0.05):
                            has_conflicting_remark_price = True

                if has_conflicting_remark_price and not is_remark_target_match:
                    continue

                if is_disc_match or is_remark_target_match:
                    c_codes = [c['code'].strip().upper() for c in combo_tuple]
                    new_tokens = [code for code in c_codes if code not in preselected]
                    pre_tokens = [code for code in c_codes if code in preselected]

                    expanded_codes = list(c_codes)
                    # ถ้า combo นี้เป็นคูปองใหม่ที่ลดได้ตรง target_discount และมี preselected อยู่บนหน้าจอ
                    if preselected and not pre_tokens and target_discount > 0:
                        should_combine_pre = False
                        if not is_remark_target_match:
                            # 1. ถ้า sub_disc เท่ากับ full discount (target_discount + pre_discount) ห้ามพ่วง เพราะ combo นี้ให้ส่วนลดเต็มจำนวนแล้ว
                            if pre_discount > 0 and abs(sub_disc - (target_discount + pre_discount)) <= 0.05:
                                should_combine_pre = False
                            # 2. ถ้า target_discount >= pre_discount แสดงว่า target_discount คือส่วนลดเต็มจำนวนจากราคาตั้งต้นแล้ว ห้ามพ่วง
                            elif expected_price is not None and pre_discount > 0 and abs(sub_disc - target_discount) <= 0.05 and target_discount >= pre_discount:
                                should_combine_pre = False
                            # 3. ถ้า sub_disc ลดได้ตรงกับ target_discount (ที่เป็นส่วนต่างเพิ่มเติม incremental) ให้พ่วง preselected
                            elif abs(sub_disc - target_discount) <= 0.05:
                                should_combine_pre = True

                        if should_combine_pre:
                            expanded_codes = [p for p in preselected if p not in expanded_codes] + expanded_codes

                    detail_code_order = {d['code'].strip().upper(): idx for idx, d in enumerate(valid_details) if d.get('code')}
                    sorted_codes = sorted(expanded_codes, key=lambda x: (0, preselected.index(x)) if x in preselected else (1, detail_code_order.get(x, 999)))
                    combo_key = " ".join(sorted_codes)
                    if combo_key in seen_combos:
                        continue
                    seen_combos.add(combo_key)

                    s_dates = [get_coupon_start_and_end_dates(c)[0] for c in combo_tuple]
                    e_dates = [get_coupon_start_and_end_dates(c)[1] for c in combo_tuple]
                    s_cmps = [to_comparable_datetime(sd) for sd in s_dates if sd]
                    e_cmps = [to_comparable_datetime(ed) for ed in e_dates if ed]

                    latest_start = max(s_cmps) if s_cmps else None
                    shortest_end = min(e_cmps) if e_cmps else None

                    s_val = latest_start.timestamp() if latest_start else 0
                    e_val = shortest_end.timestamp() if shortest_end else 9999999999

                    base_score = max(get_coupon_recency_score(c.get('code', ''), c.get('desc', '')) for c in combo_tuple)
                    if is_remark_target_match:
                        base_score += 100000000
                    if len(sorted_codes) == 1:
                        base_score += 10000000
                    elif all(p in sorted_codes for p in preselected) and preselected:
                        base_score += 5000000

                    remarks = [str(c.get("remark", "") or "").strip() for c in combo_tuple if str(c.get("remark", "") or "").strip()]
                    combo_remark = matched_remark_text if matched_remark_text else (", ".join(remarks) if remarks else "")

                    new_code_tokens = [c for c in sorted_codes if c not in preselected]
                    new_code_val = " ".join(new_code_tokens) or combo_key
                    new_code_disc = sum(code_disc_map.get(c, 0.0) for c in new_code_tokens) if new_code_tokens else sub_disc

                    matching_combos.append({
                        "suggested_code": combo_key,
                        "discount": new_code_disc if new_code_tokens else sub_disc,
                        "type": "single" if len(sorted_codes) == 1 else "combo",
                        "score": base_score,
                        "s_val": s_val,
                        "e_val": e_val,
                        "start_date": latest_start,
                        "end_date": shortest_end,
                        "remark": combo_remark,
                        "new_code": new_code_val,
                        "preselected_in_combo": [p for p in preselected if p in sorted_codes and p not in new_code_tokens]
                    })

        best = None
        if matching_combos:
            sort_key = lambda x: (-x["score"], len(x["suggested_code"].split()), -x["s_val"], x["e_val"])
            matching_combos.sort(key=sort_key)
            best = matching_combos[0]

        if not best:
            return None

        final_code = best["suggested_code"]
        new_code_val = best.get("new_code", final_code)
        pre_codes_list = [p for p in preselected if p in final_code.split() and p != new_code_val]

        # สำหรับกรณี SKU ที่มีค่า CP/DC หลายตัว (multi-code):
        final_remark, final_start, final_end = self.resolve_multi_coupon_info(
            final_code,
            expected_price=expected_price,
            default_remark=best.get("remark", ""),
            default_start=best.get("start_date"),
            default_end=best.get("end_date"),
            sku=target_sku
        )

        return {
            "suggested_code": final_code,
            "preselected_codes": pre_codes_list,
            "new_code": new_code_val,
            "discount": best["discount"],
            "type": best["type"],
            "start_date": final_start,
            "end_date": final_end,
            "remark": final_remark,
            "suggested_start_date": final_start,
            "suggested_end_date": final_end,
            "suggested_remark": final_remark
        }

    def find_all_matching_coupons_on_smco(
        self,
        target_discount: float,
        expected_price: Optional[float] = None,
        order_date: Any = None,
        sku: Optional[str] = None,
        require_seller_voucher: bool = False
    ) -> list[dict]:
        """
        สแกนหาคูปองทั้งหมด (ทั้งเดี่ยวและคอมโบ CP/DC ทุกรูปแบบ โดยไม่เอา OC/DC ปรับมือ)
        บนหน้าเว็บ SMCO ที่ตรงกับเงื่อนไข:
        1. วันที่ครอบคลุม order_date
        2. มีผลรวมส่วนลดตรงกับส่วนต่างที่ต้องลด หรือมี Remark ระบุราคาเป้าหมายตรงกับ expected_price
        ส่งกลับเป็น list of candidate dict ทุกวิธี เพื่อนำเข้า Conflict Resolver หากมีมากกว่า 1 วิธี
        """
        details = list(getattr(self, 'last_scanned_smco_coupon_details', []))

        target_sku = sku or getattr(self, '_current_reconcile_sku', '')
        if target_sku and ('+' in str(target_sku) or isinstance(target_sku, list)):
            try:
                agg = self.get_aggregated_combo_coupons(target_sku, order_date=order_date)
                if agg:
                    existing_codes = {d.get("code") for d in details}
                    for a in agg:
                        if a.get("code") not in existing_codes:
                            details.append(a)
                        else:
                            for idx_d, d_item in enumerate(details):
                                if d_item.get("code") == a.get("code"):
                                    details[idx_d]["discount"] = a["discount"]
                                    details[idx_d]["raw_discount"] = a["raw_discount"]
                                    if a.get("remark"):
                                        details[idx_d]["remark"] = a["remark"]
                                    if a.get("start_date"):
                                        details[idx_d]["start_date"] = a["start_date"]
                                    if a.get("end_date"):
                                        details[idx_d]["end_date"] = a["end_date"]
            except Exception as ex_agg:
                logger.debug(f"[find_all_matching_coupons_on_smco] Error aggregating for {target_sku}: {ex_agg}")

        if not details or (target_discount <= 0 and expected_price is None):
            return []

        parsed_order_date = parse_smart_date(order_date) if order_date else None

        def is_coupon_valid(c_dict: dict) -> bool:
            return is_coupon_valid_for_order(c_dict, parsed_order_date)

        all_cp_dc_coupons = [
            c for c in details
            if c.get("code") and not str(c["code"]).strip().upper().startswith("IS")
        ]
        valid_details = [c for c in all_cp_dc_coupons if is_coupon_valid(c)]

        if require_seller_voucher:
            valid_details = [c for c in valid_details if is_seller_voucher_desc(c.get("desc", ""))]

        valid_detail_codes = {d.get("code") for d in valid_details if d.get("code")}
        raw_preselected = getattr(self, 'last_preselected_smco_coupons', None) or []
        preselected = [p for p in raw_preselected if p in valid_detail_codes]

        if not preselected:
            for c in valid_details:
                if c.get("is_selected") and c.get("code") and c.get("code") not in preselected:
                    preselected.append(c.get("code"))

        code_disc_map = {str(d.get("code", "")).strip().upper(): float(d.get("discount", 0.0)) for d in valid_details if d.get("code")}
        pre_discount = sum(code_disc_map.get(p.strip().upper(), 0.0) for p in preselected)

        possible_req_discounts = set()
        if target_discount > 0:
            possible_req_discounts.add(round(float(target_discount), 2))
            if pre_discount > 0:
                if expected_price is None or target_discount < pre_discount:
                    possible_req_discounts.add(round(float(target_discount) + float(pre_discount), 2))

        results = []
        seen_codes = set()
        import itertools

        max_combo_size = min(4, len(valid_details))
        for k in range(1, max_combo_size + 1):
            for combo_tuple in itertools.combinations(valid_details, k):
                if require_seller_voucher:
                    if not any(is_seller_voucher_desc(c.get("desc", "")) for c in combo_tuple):
                        continue

                sub_disc = sum(float(c.get('discount', 0.0)) for c in combo_tuple)
                if sub_disc <= 0:
                    continue

                is_disc_match = any(abs(sub_disc - rd) <= 0.05 for rd in possible_req_discounts)

                is_remark_target_match = False
                matched_remark_text = ""
                has_conflicting_remark_price = False
                if expected_price is not None:
                    for c in combo_tuple:
                        rem_p = c.get("remark_target_price") or extract_target_price_from_text(c.get("remark", ""))
                        desc_p = extract_target_price_from_text(c.get("desc", ""))
                        if (desc_p is not None and abs(desc_p - float(expected_price)) <= 0.05):
                            is_remark_target_match = True
                            matched_remark_text = str(c.get("desc", "")).strip()
                            break
                        elif (rem_p is not None and abs(rem_p - float(expected_price)) <= 0.05):
                            is_remark_target_match = True
                            matched_remark_text = str(c.get("remark", "") or c.get("desc", "")).strip()
                            break
                        elif (rem_p is not None and abs(rem_p - float(expected_price)) > 0.05):
                            has_conflicting_remark_price = True

                if has_conflicting_remark_price and not is_remark_target_match:
                    continue

                if is_disc_match or is_remark_target_match:
                    c_codes = [c['code'].strip().upper() for c in combo_tuple]
                    new_tokens = [code for code in c_codes if code not in preselected]
                    pre_tokens = [code for code in c_codes if code in preselected]

                    expanded_codes = list(c_codes)
                    all_combo_items = list(combo_tuple)
                    # ถ้า combo นี้เป็นคูปองใหม่ที่ลดได้ตรง target_discount (ที่เป็นส่วนต่างเพิ่มเติม incremental) และมี preselected อยู่บนหน้าจอ
                    if preselected and not pre_tokens and target_discount > 0:
                        should_combine_pre = False
                        if not is_remark_target_match:
                            # 1. ถ้า sub_disc เท่ากับ full discount (target_discount + pre_discount) ห้ามพ่วง เพราะ combo นี้ให้ส่วนลดเต็มจำนวนแล้ว
                            if pre_discount > 0 and abs(sub_disc - (target_discount + pre_discount)) <= 0.05:
                                should_combine_pre = False
                            # 2. ถ้า target_discount >= pre_discount แสดงว่า target_discount คือส่วนลดเต็มจำนวนจากราคาตั้งต้นแล้ว ห้ามพ่วง
                            elif expected_price is not None and pre_discount > 0 and abs(sub_disc - target_discount) <= 0.05 and target_discount >= pre_discount:
                                should_combine_pre = False
                            # 3. ถ้า sub_disc ลดได้ตรงกับ target_discount (ที่เป็นส่วนต่างเพิ่มเติม incremental) ให้พ่วง preselected
                            elif abs(sub_disc - target_discount) <= 0.05:
                                should_combine_pre = True

                        if should_combine_pre:
                            expanded_codes = [p for p in preselected if p not in expanded_codes] + expanded_codes
                            for p in preselected:
                                if p not in c_codes:
                                    p_dict = next((d for d in valid_details if str(d.get("code", "")).strip().upper() == p), None)
                                    if p_dict and p_dict not in all_combo_items:
                                        all_combo_items.append(p_dict)

                    detail_code_order = {d['code'].strip().upper(): idx for idx, d in enumerate(valid_details) if d.get('code')}
                    sorted_codes = sorted(expanded_codes, key=lambda x: (0, preselected.index(x)) if x in preselected else (1, detail_code_order.get(x, 999)))
                    combo_code = " ".join(sorted_codes)
                    if combo_code in seen_codes:
                        continue
                    seen_codes.add(combo_code)

                    s_dates = [get_coupon_start_and_end_dates(c)[0] for c in all_combo_items]
                    e_dates = [get_coupon_start_and_end_dates(c)[1] for c in all_combo_items]
                    s_cmps = [to_comparable_datetime(sd) for sd in s_dates if sd]
                    e_cmps = [to_comparable_datetime(ed) for ed in e_dates if ed]

                    latest_start = max(s_cmps) if s_cmps else None
                    shortest_end = min(e_cmps) if e_cmps else None

                    remarks = [str(c.get("remark", "") or "").strip() for c in all_combo_items if str(c.get("remark", "") or "").strip()]
                    combo_remark = matched_remark_text if matched_remark_text else (", ".join(remarks) if remarks else "")

                    results.append({
                        "cp_name": combo_code,
                        "oc_amount": "",
                        "dc_amount": "",
                        "start_date": latest_start,
                        "end_date": shortest_end,
                        "remark": combo_remark,
                        "source": "SMCO"
                    })

        return results




    # ══════════════════════════════════════════════════════════════════════════
    # COUPON SELECTION & ADJUSTMENTS ON POS CART
    # ══════════════════════════════════════════════════════════════════════════
    def cp_sonic_blow_process(self, item_no: int, cp_no: str, mode: str = "auto_inv") -> bool:
        """
        เลือก coupon สำหรับสินค้าที่ระบุ รองรับ 2 รูปแบบการทำงาน:
        1. mode="auto_inv" (Default สำหรับระบบบอทอัตโนมัติ):
           - ทำงานตาม cp_data / candidate target แบบสมบูรณ์
           - คูปองเป้าหมายที่ยังไม่เลือก -> กดเลือก (Select)
           - คูปองที่ไม่ใช่เป้าหมายแต่ถูกระบบ POS ติ๊กไว้ล่วงหน้า (เช่น Auto Top-up) -> กดปลดออก (Deselect)
           - คูปองที่สถานะตรงอยู่แล้วจะไม่กดซ้ำ
        2. mode="manual" (สำหรับปุ่ม Demonic CP ใน GUI):
           - ทำงานแบบ Manual Toggle โดยตรง
           - กดเฉพาะคูปองที่ระบุใน cp_no และไม่แตะต้องคูปองตัวอื่น

        Args:
            item_no (int): เลขลำดับสินค้า (1-indexed)
            cp_no (str): ลำดับคูปอง (ตัวเลข) หรือ รหัสคูปอง (ข้อความ) แยกด้วยเว้นวรรคหรือเครื่องหมายจุลภาค
            mode (str): "auto_inv" หรือ "manual" (default: "auto_inv")
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
        logger.debug(f"[cp_sonic_blow_process] mode={mode}, demonic_ordered_items_list: {demonic_ordered_items_list}")
        logger.debug(f"[cp_sonic_blow_process] raw_tokens: {raw_tokens}")

        self.driver.switch_to.window(self.bot.merged_dict['SMCO :: เปิดการขาย'])
        green_agree_btn_xpath = 'button[ng-click="okCoupon()"]'

        any_success = False

        # * Loop ผ่านแต่ละ item ในรายการสินค้า (สำหรับ pattern ที่ 1 รายการมีหลาย SKU เช่น SP2-001610+SP2-001611+...)
        for idx, item in enumerate(demonic_ordered_items_list):
            item_position = idx + 1
            logger.debug(f"[cp_sonic_blow_process] item [{item_position}/{len(demonic_ordered_items_list)}]: {item}")

            # ดึงข้อมูลรายการสินค้าบนหน้าเว็บใหม่ทุกรอบของแต่ละสินค้า เพื่อรองรับความเปลี่ยนแปลงของหน้าเว็บและตำแหน่งที่อาจสลับได้เสมอ!
            try:
                item_texts = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('.col-sm-12.panel.panel-default.ng-scope')).map(el => el.innerText);
                """)
            except Exception as e:
                logger.debug(f"ไม่สามารถดึงข้อมูลรายการสินค้าจากหน้าเว็บได้: {e}")
                item_texts = []

            # สร้าง dict mapping ระหว่าง SKU -> Index สำหรับรอบนั้นๆ
            sku_to_index = {}
            for pos_idx, text in enumerate(item_texts):
                if item in text:
                    sku_to_index[item] = pos_idx
                    break

            if item not in sku_to_index:
                logger.debug(f"ไม่พบ SKU: {item} ในรายการขายหน้าเว็บ (ข้าม)")
                continue

            target_idx = sku_to_index[item]
            logger.debug(f"เจอสินค้า {item} ที่ตำแหน่ง Index: {target_idx}")

            try:
                # * คลิกปุ่ม coupon เพื่อเปิดหน้ารายการ coupon (มี retry ด้วย Selenium ปกติ)
                modal_opened = False
                for attempt in range(2):
                    try:
                        panels = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
                        target_panel = panels[target_idx] if (0 <= target_idx < len(panels)) else None
                        cp_btn_xpath = None

                        if target_panel is not None:
                            scoped_btns = target_panel.find_elements(
                                By.XPATH, ".//button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]"
                            )
                            if not scoped_btns:
                                scoped_btns = target_panel.find_elements(By.XPATH, ".//button[contains(@class,'btn-coupon')]")
                            if scoped_btns:
                                cp_btn_xpath = scoped_btns[0]

                        # Fallback สำหรับกรณีโครงสร้าง DOM พิเศษ
                        if cp_btn_xpath is None:
                            item_list_cp_btn_elements = self.driver.find_elements(
                                By.XPATH, "//button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]"
                            )
                            if target_idx < len(item_list_cp_btn_elements):
                                cp_btn_xpath = item_list_cp_btn_elements[target_idx]

                        if cp_btn_xpath is None:
                            logger.debug(f"ดึงปุ่ม coupon ของ {item} ไม่สำเร็จ (ไม่พบคอนเทนเนอร์ปุ่ม)")
                            break

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
                    logger.debug(f"ไม่สามารถเปิดหน้าต่างคูปองของ {item} ได้")
                    continue

                # ดึงข้อมูลชื่อคูปองและปุ่มบนหน้าจอสดๆ เสมอ
                cp_name_elements = self.driver.find_elements(By.XPATH, cp_name_loc)
                cp_btn_elements = self.driver.find_elements(By.XPATH, selected_cp_btn_loc)

                if not cp_name_elements or not cp_btn_elements:
                    logger.debug("ไม่พบรายการคูปองหรือปุ่มคูปองบนหน้าจอ")
                    continue

                if mode == "manual":
                    # ══════════════════════════════════════════════════════════════════
                    # 1. รูปแบบ MANUAL (TOGGLE): คลิกเฉพาะคูปองที่ผู้ใช้ระบุโดยไม่แตะต้องคูปองอื่น
                    # ══════════════════════════════════════════════════════════════════
                    for token in raw_tokens:
                        target_btn_idx = -1
                        if not token.isdigit():
                            token_clean = token.replace(" ", "").upper()
                            for r_idx in range(min(len(cp_name_elements), len(cp_btn_elements))):
                                row_cp_name = cp_name_elements[r_idx].text.replace(" ", "").upper()
                                if token_clean in row_cp_name:
                                    target_btn_idx = r_idx
                                    break
                        else:
                            original_idx = int(token) - 1
                            if 0 <= original_idx < len(cp_btn_elements):
                                target_btn_idx = original_idx

                        if 0 <= target_btn_idx < len(cp_btn_elements):
                            btn_el = cp_btn_elements[target_btn_idx]
                            row_name = cp_name_elements[target_btn_idx].text if target_btn_idx < len(cp_name_elements) else token
                            logger.info(f"🔘 [Manual Toggle] สลับสถานะคูปอง: [{row_name}] สำหรับ {item}")
                            self.app.update_log(f"🔘 [Manual] สลับคูปอง: [{row_name}] สำหรับ SKU: {item}")
                            try:
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", btn_el)
                            except Exception:
                                pass
                            btn_el.click()
                            time.sleep(0.1)
                            any_success = True
                        else:
                            logger.debug(f"[Manual Toggle] ไม่พบคูปอง: {token}")

                else:
                    # ══════════════════════════════════════════════════════════════════
                    # 2. รูปแบบ AUTO_INV: ปรับสถานะตาม cp_data / candidate target 100%
                    #    - เลือกคูปองเป้าหมายที่ยังไม่ถูกเลือก (Select)
                    #    - ปลดคูปองส่วนเกินหรือ Auto Top-up ออก (Deselect)
                    #    - ไม่คลิกซ้ำหากสถานะถูกต้องอยู่แล้ว
                    # ══════════════════════════════════════════════════════════════════
                    desired_target_names = set()
                    for token in raw_tokens:
                        if not token.isdigit():
                            desired_target_names.add(token.replace(" ", "").upper())
                        else:
                            num_idx = int(token) - 1
                            if 0 <= num_idx < len(cp_name_elements):
                                desired_target_names.add(cp_name_elements[num_idx].text.replace(" ", "").upper())

                    logger.debug(f"[{item}] [Auto-Inv] ชุดคูปองเป้าหมายที่ต้องการ: {desired_target_names}")

                    for r_idx in range(min(len(cp_name_elements), len(cp_btn_elements))):
                        name_el = cp_name_elements[r_idx]
                        btn_el = cp_btn_elements[r_idx]
                        row_cp_name = name_el.text.replace(" ", "").upper()

                        btn_class = str(btn_el.get_attribute("class") or "").lower()
                        btn_text = str(btn_el.text or "").strip().lower()
                        is_currently_selected = (
                            "btn-primary" in btn_class
                            or "btn-info" in btn_class
                            or "selected" in btn_text
                            or "เลือกแล้ว" in btn_text
                        )

                        should_be_selected = any(target in row_cp_name for target in desired_target_names)

                        if should_be_selected and not is_currently_selected:
                            logger.info(f"🔘 [Auto-Inv] กดเลือกคูปองเป้าหมาย: [{row_cp_name}] สำหรับ {item}")
                            self.app.update_log(f"🔘 เลือกคูปอง: [{row_cp_name}] สำหรับ SKU: {item}")
                            try:
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", btn_el)
                            except Exception:
                                pass
                            btn_el.click()
                            time.sleep(0.1)
                            any_success = True

                        elif not should_be_selected and is_currently_selected:
                            logger.info(f"🔄 [Auto-Inv] ปลดคูปองส่วนเกิน/Auto Top-up ออก: [{row_cp_name}] สำหรับ {item}")
                            self.app.update_log(f"🔄 ปลดคูปองส่วนเกิน/Auto Top-up: [{row_cp_name}] ออกสำหรับ SKU: {item}")
                            try:
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", btn_el)
                            except Exception:
                                pass
                            btn_el.click()
                            time.sleep(0.1)
                            any_success = True

                # * กดยืนยัน (ครั้งเดียวหลังจากปรับสถานะครบทุก coupon แล้วสำหรับ SKU นี้)
                logger.debug(f"click OK ในรอบของ: {item}, ชุดคูปองเป้าหมาย: {desired_target_names}")
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

        logger.debug(f"[cp_sonic_blow_process] Done selecting coupons: {cp_target_names}")
        if any_success:
            for it in demonic_ordered_items_list:
                self._track_adjustment(it, 'CP')
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

                # 2. จาก coupon label / badge elements เฉพาะ (ไม่ค้นหาจาก text ทั้ง panel ป้องกันดึงข้อความขยะ/SKU อื่น)
                badge_elements = target_panel.find_elements(
                    By.XPATH,
                    ".//span[contains(@class, 'label')] | .//span[contains(@class, 'badge')] | .//span[contains(@class, 'coupon')] | .//a[contains(@class, 'coupon')]"
                )
                for b_el in badge_elements:
                    b_text = (b_el.text or "").upper()
                    matches = re.findall(r'\b((?:CP|DC)\d+)\b', b_text)
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
        self.last_preselected_smco_coupons = []
        item_idx = int(item_no) - 1
        demonic_ordered_items_list: list = self.app.correct_sku_pattern(self.app.items[item_idx]['เลขอ้างอิง SKU (SKU Reference No.)'])
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

            panels = self.driver.find_elements(By.CSS_SELECTOR, '.col-sm-12.panel.panel-default.ng-scope')
            target_panel = panels[target_idx] if (0 <= target_idx < len(panels)) else None

            scan_btn = None
            if target_panel is not None:
                scoped_cp_btns = target_panel.find_elements(
                    By.XPATH, ".//button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]"
                )
                if not scoped_cp_btns:
                    scoped_cp_btns = target_panel.find_elements(By.XPATH, ".//button[contains(@class,'btn-coupon')]")
                if scoped_cp_btns:
                    scan_btn = scoped_cp_btns[0]

            if scan_btn is None:
                item_list_cp_btn_elements = self.driver.find_elements(
                    By.XPATH, "//button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]"
                )
                if target_idx < len(item_list_cp_btn_elements):
                    scan_btn = item_list_cp_btn_elements[target_idx]

            if scan_btn is None:
                return []

            #/ เปิด Modal ดูรายการคูปองที่มีบนหน้าเว็บ ###########################################################################################################
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", scan_btn)
            except Exception:
                pass
            scan_btn.click()

            # Dynamic Smart Wait สูงสุด 3.0 วินาที (30 * 0.1s) รองรับสินค้าเซ็ตหลาย SKU และ AngularJS render
            for _ in range(30):
                cp_name_elements = self.driver.find_elements(By.XPATH, cp_name_loc)
                if cp_name_elements and any(b.is_displayed() for b in cp_name_elements):
                    break
                modal_items = self.driver.find_elements(By.XPATH, "//div[contains(@class,'list-group-item')]")
                if modal_items and any(m.is_displayed() for m in modal_items):
                    break
                time.sleep(0.1)

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

                    # 2. ค้นหาคำอธิบาย, Remark, และช่วงวันที่ (Date Range)
                    c_desc = ""
                    c_remark = ""
                    c_start_date = None
                    c_end_date = None
                    is_expired = False

                    if item_text_str:
                        if "ส่วนลดหมดอายุ" in item_text_str:
                            is_expired = True
                        s_dt, e_dt = extract_coupon_date_range(item_text_str)
                        if s_dt and e_dt:
                            c_start_date, c_end_date = s_dt, e_dt

                    desc_spans = item_el.find_elements(
                        By.XPATH, ".//span[@ng-show='pmt.couponDesc !== undefined' or contains(@class,'font-color-secondary')]"
                    )
                    for ds in desc_spans:
                        t = ds.text.strip() if hasattr(ds, 'text') and isinstance(ds.text, str) else str(getattr(ds, 'text', ''))
                        if not t:
                            continue
                        if not c_start_date or not c_end_date:
                            s_dt, e_dt = extract_coupon_date_range(t)
                            if s_dt and e_dt:
                                c_start_date, c_end_date = s_dt, e_dt
                        if "ส่วนลดหมดอายุ" in t:
                            is_expired = True
                        if not c_desc or is_seller_voucher_desc(t):
                            c_desc = t
                            if is_seller_voucher_desc(t):
                                break

                    # ค้นหา Remark จาก couponDetailRemark หรือ fallback spans
                    fallback_desc_spans = item_el.find_elements(
                        By.XPATH, ".//span[contains(@ng-show, 'couponDetailRemark') or contains(@class, 'font-color')]"
                    )
                    for fb_el in fallback_desc_spans:
                        fb_text = fb_el.text.strip() if hasattr(fb_el, 'text') and isinstance(fb_el.text, str) else str(getattr(fb_el, 'text', ''))
                        if fb_text:
                            if not c_start_date or not c_end_date:
                                s_dt, e_dt = extract_coupon_date_range(fb_text)
                                if s_dt and e_dt:
                                    c_start_date, c_end_date = s_dt, e_dt
                            if "ส่วนลดหมดอายุ" in fb_text:
                                is_expired = True
                            if not c_remark and ("Remark" in fb_text or "ราคา" in fb_text or "Dynamic" in fb_text):
                                c_remark = fb_text
                            if not c_desc or is_seller_voucher_desc(fb_text):
                                c_desc = fb_text

                    # ตรวจสอบเพิ่มเติมจากบรรทัดทั้งหมดใน item_text_str (ดักจับคำว่า coupon voucher / seller voucher / remark)
                    if item_text_str:
                        for line_t in item_text_str.split('\n'):
                            line_clean = line_t.strip()
                            if is_seller_voucher_desc(line_clean) and not is_seller_voucher_desc(c_desc):
                                c_desc = line_clean
                            if ("Remark" in line_clean or "ราคา" in line_clean or "Dynamic" in line_clean) and not c_remark:
                                c_remark = line_clean

                    # สกัดราคาเป้าหมายจาก Remark หรือ Description (เช่น 'Dynamic ก.ย. Shp ราคา 9673')
                    remark_target_price = extract_target_price_from_text(f"{c_remark} {c_desc} {item_text_str}")

                    # 3. ค้นหามูลค่าส่วนลด (Discount Amount)
                    disc_val = 0.0
                    disc_text = ""

                    # วิธีที่ 1: ค้นหาจาก span หรือข้อความที่มีรูปแบบ "ตัวเลข.-" (เช่น 200.-, 400.-) ซึ่งเป็นรูปแบบเฉพาะของส่วนลด SMCO
                    amount_spans = item_el.find_elements(
                        By.XPATH, ".//span[contains(text(), '.-') or contains(@class, 'text-danger')]"
                    )
                    for asp in amount_spans:
                        t = asp.text.strip() if hasattr(asp, 'text') and isinstance(asp.text, str) else str(getattr(asp, 'text', ''))
                        if not c_start_date or not c_end_date:
                            s_dt, e_dt = extract_coupon_date_range(t)
                            if s_dt and e_dt:
                                c_start_date, c_end_date = s_dt, e_dt
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
                        c_name = c_name.strip().upper()
                        # 🛑 กรองไม่เอาคูปอง Payment / IS ผ่อนชำระ (รับเฉพาะ CP/DC เท่านั้น)
                        if c_name.startswith("IS") or not (c_name.startswith("CP") or c_name.startswith("DC")):
                            logger.debug(f"[scan_matching_cp_candidates_on_smco] Skipping non-CP/DC coupon: {c_name}")
                            continue
                        if "payment" in str(c_desc).lower() or "payment" in str(c_remark).lower() or "ผ่อน" in str(c_desc) or "ผ่อน" in str(c_remark):
                            logger.debug(f"[scan_matching_cp_candidates_on_smco] Skipping Payment/Installment coupon: {c_name}")
                            continue

                        scanned_details.append({
                            "code": c_name,
                            "discount": disc_val,
                            "desc": c_desc,
                            "remark": c_remark,
                            "remark_target_price": remark_target_price,
                            "raw_discount": disc_text,
                            "is_selected": is_sel,
                            "start_date": c_start_date,
                            "end_date": c_end_date,
                            "is_expired": is_expired
                        })
            except Exception as e:
                print(f"[scan_matching_cp_candidates_on_smco] Error scraping coupon details: {e}")

            # ผสานข้อมูลส่วนลดรวมของคูปองข้าม Sub-SKU (Aggregated Combo Coupons) จาก Network Response
            try:
                raw_sku_ref = ""
                if hasattr(self.app, 'items') and self.app.items and 0 <= item_idx < len(self.app.items):
                    item_dict = self.app.items[item_idx]
                    raw_sku_ref = (
                        item_dict.get('เลขอ้างอิง SKU (SKU Reference No.)')
                        or item_dict.get('เลขอ้างอิง SKU')
                        or item_dict.get('sku')
                        or ""
                    )
                if not raw_sku_ref and demonic_ordered_items_list:
                    raw_sku_ref = "+".join([str(s) for s in demonic_ordered_items_list])

                agg_coupons = self.get_aggregated_combo_coupons(raw_sku_ref or demonic_ordered_items_list)
                if agg_coupons:
                    logger.info(f"[scan_matching_cp_candidates_on_smco] Merging {len(agg_coupons)} aggregated combo coupons for {raw_sku_ref}: {[c.get('code') for c in agg_coupons]}")
                    agg_map = {c["code"]: c for c in agg_coupons}
                    for sc in scanned_details:
                        code = sc.get("code")
                        if code in agg_map:
                            sc["discount"] = agg_map[code]["discount"]
                            sc["raw_discount"] = agg_map[code]["raw_discount"]
                            sc["is_aggregated"] = True
                            if agg_map[code].get("remark"):
                                sc["remark"] = agg_map[code]["remark"]
                            if agg_map[code].get("remark_target_price"):
                                sc["remark_target_price"] = agg_map[code]["remark_target_price"]
                            if agg_map[code].get("start_date") and not sc.get("start_date"):
                                sc["start_date"] = agg_map[code]["start_date"]
                            if agg_map[code].get("end_date") and not sc.get("end_date"):
                                sc["end_date"] = agg_map[code]["end_date"]

                    sc_codes = {sc.get("code") for sc in scanned_details}
                    for code, agg_c in agg_map.items():
                        if code not in sc_codes:
                            scanned_details.append(agg_c)
            except Exception as ex_merge:
                logger.debug(f"[scan_matching_cp_candidates_on_smco] Error merging aggregated combo coupons: {ex_merge}")

            self.last_scanned_smco_coupon_details = scanned_details
            if scanned_details:
                logger.debug(f"[scan_matching_cp_candidates_on_smco] Scanned {len(scanned_details)} coupons on SMCO: {[c.get('code') for c in scanned_details]}")
            preselected = []
            for sc in scanned_details:
                if sc.get("is_selected") and sc.get("code") and sc.get("code") not in preselected:
                    preselected.append(sc.get("code"))

            # รวมคูปองเริ่มต้น (Default CP/DC) ที่ติดอยู่บน Item Panel ของสินค้าบนหน้า POS Cart (ต้องมีอยู่จริงใน scanned_details)
            scanned_code_set = {sc.get("code") for sc in scanned_details if sc.get("code")}
            for pc in panel_codes:
                if pc and pc in scanned_code_set and pc not in preselected:
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
            details = getattr(self, 'last_scanned_smco_coupon_details', [])
            if not details:
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
                            self._track_adjustment(item, 'OC')
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
                            self._track_adjustment(item, 'DC')
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

        # ตรวจสอบว่าคูปองที่มีอยู่บนแผงสินค้าตรงกับสูตรเป้าหมายพอดีเป๊ะหรือไม่ (ไม่มีคูปองขาด และไม่มีคูปองส่วนเกิน)
        all_targets_present = all(any(tok in ext for ext in existing_cps) for tok in target_tokens)
        no_unwanted_coupons = (len(existing_cps) == len(target_tokens))

        if all_targets_present and no_unwanted_coupons:
            self.app.update_log(f"✨ คูปอง [{cp_name}] สำหรับ SKU: {sku_key} ถูกเลือกไว้ตรงตามเป้าหมายแล้ว ข้ามการเลือกซ้ำ")
            return True

        self.app.update_log(f"🔧 ปรับปรุงคูปองสำหรับ SKU: {sku_key} ให้เป็น [{cp_name}] (ปลดคูปองส่วนเกิน/Auto และเลือกคูปองที่ต้องการ)...")
        return self.cp_sonic_blow_process(item_no_1indexed, cp_name)

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
            self._current_reconcile_sku = sku_key

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
                                seller_voucher, require_seller_voucher=True, order_date=purchased_date, expected_price=expected_price, sku=sku_key
                            )
                            suggested_cp_code = sugg_info["suggested_code"] if sugg_info else ((sv_chosen.get("code") if sv_chosen else ""))
                            has_entry = len(cp_candidates) > 0
                            self._record_missing_cp_with_dates(sku_key, expected_price, suggested_cp_code, sugg_info)

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
                    # ══════════════════════════════════════════════════════════
                    # ขั้นตอนที่ 2 (Phase 2): ปรับราคาตาม Pattern เดิมใน cp_data.xlsx หรือ SMCO
                    # ══════════════════════════════════════════════════════════
                    # กรณีที่ 1: marketplace_item_price > smco_item_price? (diff > 0)
                    # ถ้าราคาขายบน SMCO ต่ำกว่าราคาที่ลูกค้าซื้อ อาจเกิดจากมี Auto Top-up ติดอยู่
                    # ตรวจสอบว่ามีคูปอง CP/DC หรือ Remark ราคาที่ตรงกับ expected_price ก่อนปรับราคาขึ้น (Overcharge)
                    if diff_val > 0:
                        bypassed = False
                        oc_amount_to_apply = None
                        matched_cand = None
                        pure_cp_cand = None

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
                                elif cand.get("cp_name") and str(cand.get("cp_name", "")).strip():
                                    cand_cp_str = str(cand.get("cp_name", "")).strip()
                                    if cand_cp_str.upper() not in ["NONE", "BYPASS", "NO_CP", "NO CP", "PASSTHROUGH"] and "ไม่มี" not in cand_cp_str:
                                        pure_cp_cand = cand

                        if not bypassed:
                            # 1.1 ถ้าในตารางมี candidate ที่ระบุคูปอง (cp_name) โดยไม่มีการระบุ oc_amount
                            # แสดงว่าราคานี้ใช้คูปองตัวนี้และต้องปลด Auto Top-up ออก -> ให้ใส่คูปองก่อน ห้าม Overcharge ซ้อน
                            if pure_cp_cand is not None and oc_amount_to_apply is None:
                                cand_cp_name = str(pure_cp_cand.get("cp_name", "")).strip()
                                self.app.update_log(
                                    f"🔍 พบสูตรคูปอง [{cand_cp_name}] ในตารางสำหรับราคา {expected_price} (ราคาบน SMCO ต่ำกว่าอาจเกิดจาก Auto Top-up) -> ทำการเลือกคูปองและปลด Auto Top-up ออกแทนการ Overcharge..."
                                )
                                try:
                                    self.apply_candidate_coupons_if_missing(item_no_1indexed, sku_key, cand_cp_name)
                                except Exception as ex_cp:
                                    print(f"Error applying pure cp candidate in diff > 0: {ex_cp}")

                            # 1.2 ถ้า candidate มีการระบุ oc_amount ชัดเจนในตาราง -> ปรับราคาขึ้นตาม oc_amount และใส่คูปอง (ถ้ามี)
                            elif oc_amount_to_apply is not None:
                                self.smco_set_overcharge_product(sku_key, str(oc_amount_to_apply))
                                if matched_cand and matched_cand.get("cp_name"):
                                    cand_cp_name = str(matched_cand.get("cp_name", "")).strip()
                                    is_bp = cand_cp_name.upper() in ["NONE", "BYPASS", "NO_CP", "NO CP", "PASSTHROUGH"]
                                    if not is_bp and cand_cp_name:
                                        self.app.update_log(f"🔍 ตรวจสอบและเลือกคูปองที่เหลือ [{cand_cp_name}] สำหรับ SKU: {sku_key}...")
                                        try:
                                            self.apply_candidate_coupons_if_missing(item_no_1indexed, sku_key, cand_cp_name)
                                        except Exception as ex_cp:
                                            print(f"Error applying candidate coupons in diff > 0: {ex_cp}")

                            # 1.3 ถ้าไม่มี candidate ในตารางเลย ให้สแกนดูบน SMCO ก่อนว่ามีคูปองที่ Remark ระบุราคาตรงกับ expected_price หรือไม่
                            else:
                                direct_smco_cands = self.find_all_matching_coupons_on_smco(
                                    0, expected_price=expected_price, order_date=purchased_date, sku=sku_key
                                )
                                sugg_info = self.find_suggested_cp_for_discount(
                                    0, expected_price=expected_price, order_date=purchased_date, sku=sku_key
                                )
                                suggested_cp_code = sugg_info["suggested_code"] if sugg_info else ""

                                if direct_smco_cands or sugg_info:
                                    self._record_missing_cp_with_dates(sku_key, expected_price, suggested_cp_code, sugg_info)
                                    log_msg = (
                                        f"ℹ️ พบคูปองแนะนำ [{suggested_cp_code}] บน SMCO ที่ตรงกับราคา {expected_price} สำหรับ SKU: {sku_key} "
                                        f"(ราคาต่ำกว่าอาจเกิดจาก Auto Top-up) -> หยุดเพื่อให้ตรวจสอบก่อนทำการ Overcharge"
                                    )
                                    logger.info(log_msg)
                                    self.app.update_log(log_msg)
                                    self._raise_missing_cp_guide(
                                        item, sku_key, actual_price, expected_price, purchased_date,
                                        has_entry=False, suggested_cp_info=sugg_info
                                    )
                                elif seller_voucher > 0:
                                    self.app.update_log(
                                        f"ℹ️ ออเดอร์มี Seller Voucher แต่ไม่มีการระบุ oc_amount ใน cp_data.xlsx สำหรับ SKU: {sku_key} (ส่วนต่าง: +{diff_val:,.2f} บาท) -> ไม่ทำการ Overcharge อัตโนมัติ เพื่อความปลอดภัย"
                                    )
                                else:
                                    # ไม่มีคูปองใดๆ ที่ตรงกับราคานี้ทั้งในตารางและบน SMCO จึงทำการ Overcharge ตามส่วนต่าง
                                    self.app.update_log(f"⚡ ปรับราคาขึ้น (Overcharge) สำหรับ SKU: {sku_key} จำนวน {diff_val} บาท (คำนวณจากส่วนต่าง)")
                                    self.smco_set_overcharge_product(sku_key, str(diff_val))

                    # กรณีที่ 2: marketplace_item_price < smco_item_price? (diff < 0)
                    elif diff_val < 0:
                        self.app.update_log(f"🔍 กำลังหาคูปองลดราคาสำหรับ SKU: {sku_key} (พบ {len(cp_candidates)} รูปแบบใน CP Data)")

                        # สแกนดูว่าในบรรดา candidates จากตาราง มีกี่ชุดที่พบคูปองบนหน้าเว็บ SMCO จริง
                        available_candidates = self.scan_matching_cp_candidates_on_smco(
                            item_no_1indexed, cp_candidates or [], required_seller_voucher=0.0
                        )

                        target_discount = abs(float(diff_val))
                        sugg_info = self.find_suggested_cp_for_discount(
                            target_discount, require_seller_voucher=False, order_date=purchased_date, expected_price=expected_price, sku=sku_key
                        )
                        suggested_cp_code = sugg_info["suggested_code"] if sugg_info else ""

                        # สแกนหาคูปองตรงทั้งหมดที่ปรากฏบน SMCO ขณะนี้ (Realtime SMCO candidate discovery)
                        direct_smco_candidates = self.find_all_matching_coupons_on_smco(
                            target_discount, expected_price=expected_price, order_date=purchased_date, sku=sku_key, require_seller_voucher=False
                        )

                        # รวมชุดตัวเลือกทั้งหมด (จากตาราง CP Data + คูปองใหม่ที่พบสดๆ บน SMCO)
                        unified_candidates = list(available_candidates)

                        def candidate_matches_direct(table_cand: dict, direct_cand: dict) -> bool:
                            t_cp = str(table_cand.get("cp_name", "")).strip().upper()
                            d_cp = str(direct_cand.get("cp_name", "")).strip().upper()
                            t_tokens = set(t_cp.split())
                            d_tokens = set(d_cp.split())
                            has_adj = is_valid_adjustment(table_cand.get("oc_amount")) or is_valid_adjustment(table_cand.get("dc_amount"))
                            # ถ้าตารางมีปรับราคา OC/DC ร่วมด้วย ถือว่าเป็นคนละสูตรกับคูปองลดตรงๆ บน SMCO
                            if has_adj:
                                return False
                            return t_tokens == d_tokens

                        for dc in direct_smco_candidates:
                            already_in_table = any(candidate_matches_direct(tc, dc) for tc in available_candidates)
                            if not already_in_table:
                                unified_candidates.append(dc)

                        # ─── CASE 0: ไม่พบชุดใดที่ใช้ได้บน SMCO เลย ───
                        if len(unified_candidates) == 0:
                            has_entry = len(cp_candidates) > 0
                            self._record_missing_cp_with_dates(sku_key, expected_price, suggested_cp_code, sugg_info)
                            log_msg = f"❌ ไม่พบชุด CP/DC ใดที่ตรงกับในระบบ SMCO สำหรับ SKU: {sku_key} (วันที่: {purchased_date}, ราคาที่ต้องออก: {expected_price}) -> หยุดปรับราคาและสร้างคำถาม"

                            logger.warning(log_msg)
                            self.app.update_log(log_msg)
                            self._raise_missing_cp_guide(item, sku_key, actual_price, expected_price, purchased_date, has_entry=has_entry, cp_candidates=cp_candidates, suggested_cp_info=sugg_info)

                        # ─── CASE 1: พบชุดที่ตรงบน SMCO พอดี 1 ชุด ───
                        elif len(unified_candidates) == 1:
                            # หาก 1 ชุดนี้เป็นคูปองใหม่ที่พบเฉพาะบน SMCO แต่ยังไม่เคยระบุในตาราง cp_data.xlsx
                            if unified_candidates[0].get("source") == "SMCO" and len(available_candidates) == 0:
                                self._record_missing_cp_with_dates(sku_key, expected_price, suggested_cp_code, sugg_info)
                                log_msg = f"ℹ️ พบคูปองแนะนำ [{suggested_cp_code}] บน SMCO สำหรับ SKU: {sku_key} แต่ยังไม่ได้บันทึกใน cp_data.xlsx -> หยุดเพื่อให้ตรวจสอบก่อน"
                                logger.info(log_msg)
                                self.app.update_log(log_msg)
                                self._raise_missing_cp_guide(item, sku_key, actual_price, expected_price, purchased_date, has_entry=False, suggested_cp_info=sugg_info)

                            chosen_cand = unified_candidates[0]
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
                                self._record_missing_cp_with_dates(sku_key, expected_price, suggested_cp_code, sugg_info)
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

                        # ─── CASE 2: พบชุดที่ตรงบน SMCO มากกว่า 1 ชุด (Ambiguity Detected -> Conflict Resolver) ───
                        else:
                            ambiguous_details = []
                            for idx_a, ac in enumerate(unified_candidates, start=1):
                                src = " (คูปองใหม่บน SMCO)" if ac.get("source") == "SMCO" else " (จากตาราง CP Data)"
                                desc = f"ชุดที่ {idx_a}: CP='{ac.get('cp_name')}', OC='{ac.get('oc_amount') or '-'}', DC='{ac.get('dc_amount') or '-'}'{src}"
                                ambiguous_details.append(desc)

                            ambiguity_str = "\n".join(f"  • {d}" for d in ambiguous_details)
                            log_warn = (
                                f"⚠️ [Conflict Resolver] พบชุด CP/DC ที่ตรงเงื่อนไขบนหน้าเว็บ SMCO มากกว่า 1 ชุด ({len(unified_candidates)} ชุด) สำหรับ SKU: {sku_key}\n"
                                f"{ambiguity_str}"
                            )
                            logger.info(log_warn)
                            self.app.update_log(log_warn)

                            # 1. ตรวจสอบว่าในแท็บ conflict_resolver มีการอนุมัติ (Admin Selection) หรือยัง
                            admin_cand = None
                            if hasattr(self, '_dual_cp_loader') and self._dual_cp_loader:
                                try:
                                    df_conf = self._dual_cp_loader.load_conflict_resolver_df()
                                    if not df_conf.empty:
                                        sku_m = (df_conf['sku'].astype(str).str.strip().str.upper() == str(sku_key).strip().upper())
                                        price_m = ((pd.to_numeric(df_conf['sale_price'], errors='coerce') - float(expected_price)).abs() <= 0.05)
                                        matched_conf = df_conf[sku_m & price_m]
                                        if not matched_conf.empty:
                                            admin_pick = str(matched_conf['admin_selection'].iloc[0] or "").strip().upper()
                                            status_val = str(matched_conf['status'].iloc[0] or "").strip().upper()
                                            if admin_pick and status_val in ('APPROVED', 'RESOLVED', 'ACTIVE'):
                                                for uc in unified_candidates:
                                                    c_name_u = str(uc.get('cp_name', '') or '').strip().upper()
                                                    if c_name_u == admin_pick or admin_pick in c_name_u:
                                                        admin_cand = uc
                                                        break
                                except Exception as ex_conf:
                                    print(f"[Conflict Resolver] Error checking admin selection: {ex_conf}")

                            # 2. บันทึกทุก Pattern ที่พบลงใน cp_data เพื่อเก็บเป็นประวัติและทางเลือก
                            for cand in unified_candidates:
                                c_cp = str(cand.get("cp_name", "") or "").strip()
                                c_oc = str(cand.get("oc_amount", "") or "").strip()
                                c_dc = str(cand.get("dc_amount", "") or "").strip()
                                c_src = cand.get("source", "")
                                cand_sugg_info = sugg_info if (sugg_info and sugg_info.get("suggested_code") == c_cp) else None
                                cand_rem = cand.get("remark", "")
                                cand_start = cand.get("start_date") or cand.get("usage_start_date") or cand.get("suggested_usage_start_date")
                                cand_end = cand.get("end_date") or cand.get("usage_end_date") or cand.get("suggested_usage_end_date")

                                resolved_rem, resolved_start, resolved_end = self.resolve_multi_coupon_info(
                                    c_cp,
                                    expected_price=expected_price,
                                    default_remark=cand_rem,
                                    default_start=cand_start,
                                    default_end=cand_end,
                                    sku=sku_key
                                )

                                self._record_missing_cp_with_dates(
                                    sku_key=sku_key,
                                    expected_price=expected_price,
                                    suggested_cp_code=c_cp,
                                    sugg_info=cand_sugg_info,
                                    oc_amount=c_oc,
                                    dc_amount=c_dc,
                                    cp_name="",  # บันทึกเฉพาะฝั่ง suggest ก่อน ไม่แตะช่องใช้จริง (cp_name) จนกว่าจะมีการยิงผ่านจริง
                                    start_date=resolved_start,
                                    end_date=resolved_end,
                                    remark=resolved_rem
                                )

                            # 3. เลือกตัวที่จะนำไปใช้งาน: หากมี Admin Selection ให้ใช้ตาม Admin; หากยังไม่มี ให้ใช้ Smart Suggested Winner
                            if admin_cand is not None:
                                chosen_cand = admin_cand
                                self.app.update_log(f"🎯 [Conflict Resolver] ใช้สูตรตามที่ Admin อนุมัติ: [{chosen_cand.get('cp_name')}] สำหรับ SKU: {sku_key}")
                            else:
                                # Smart Tie-Breaker: คัดเลือกตัวที่ดีที่สุด (ไม่หมดอายุ + วันที่เริ่มใหม่สุด + ไม่มี OC/DC)
                                def score_candidate(c_item):
                                    sc = 0
                                    c_st = parse_smart_date(c_item.get("start_date") or c_item.get("usage_start_date") or c_item.get("suggested_usage_start_date"))
                                    c_en = parse_smart_date(c_item.get("end_date") or c_item.get("usage_end_date") or c_item.get("suggested_usage_end_date"))
                                    ord_d = parse_smart_date(purchased_date)
                                    if c_item.get("is_expired"):
                                        sc -= 100
                                    if ord_d and c_st and c_en:
                                        if c_st <= ord_d <= c_en:
                                            sc += 50
                                        elif ord_d > c_en:
                                            sc -= 80
                                    if not is_valid_adjustment(c_item.get("oc_amount")) and not is_valid_adjustment(c_item.get("dc_amount")):
                                        sc += 20
                                    if c_st:
                                        try:
                                            sc += (c_st - datetime.date(2026, 1, 1)).days * 0.1
                                        except Exception:
                                            pass
                                    return sc

                                sorted_candidates = sorted(unified_candidates, key=score_candidate, reverse=True)
                                chosen_cand = sorted_candidates[0]
                                suggested_winner_code = str(chosen_cand.get("cp_name") or "").strip()

                                # สร้าง Conflict Record ส่งขึ้นแท็บ conflict_resolver (รองรับ candidates ไม่จำกัดจำนวน)
                                cand_desc_list = []
                                for idx_c, c in enumerate(unified_candidates, start=1):
                                    c_name = c.get("cp_name") or "-"
                                    c_rem = f" ({c.get('remark')})" if c.get("remark") else ""
                                    cand_desc_list.append(f"{idx_c}) {c_name}{c_rem}")

                                candidates_multiline = "\n".join(cand_desc_list)
                                reason_str = f"ระบบแนะนำ {suggested_winner_code} เพราะวันที่ตรงกับช่วงโปรโมชันและสูตรเหมาะสมที่สุด"
                                conflict_payload = {
                                    "sku": str(sku_key).strip().upper(),
                                    "sale_price": float(expected_price),
                                    "candidates": candidates_multiline,
                                    "candidates_count": len(unified_candidates),
                                    # Legacy fallback columns สำหรับชีตเวอร์ชันเก่า
                                    "candidate_1": cand_desc_list[0] if len(cand_desc_list) > 0 else "",
                                    "candidate_2": cand_desc_list[1] if len(cand_desc_list) > 1 else "",
                                    "candidate_3": cand_desc_list[2] if len(cand_desc_list) > 2 else "",
                                    "suggested_winner": suggested_winner_code,
                                    "reason": reason_str,
                                    "admin_selection": "",
                                    "status": "PENDING",
                                    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                                if hasattr(self, '_dual_cp_loader') and self._dual_cp_loader:
                                    self._dual_cp_loader.push_conflict_record(conflict_payload)

                                self.app.update_log(
                                    f"💡 [Conflict Resolver] บันทึกข้อขัดแย้งเข้าแท็บ conflict_resolver เรียบร้อยแล้ว -> เลือกใช้สูตรแนะนำ [{suggested_winner_code}] ออกบิลต่ออัตโนมัติ"
                                )

                            # 4. ดำเนินการออกบิลต่อด้วย chosen_cand โดยไม่อุดตัน (Proceed Smoothly)
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

                            if has_valid_cp:
                                self.app.update_log(f"🔍 ตรวจสอบและเลือกคูปอง [{cp_name}] สำหรับ SKU: {sku_key}...")
                                try:
                                    cp_ok = self.apply_candidate_coupons_if_missing(item_no_1indexed, sku_key, cp_name)
                                    if not cp_ok:
                                        cp_ok = self.cp_sonic_blow_process(item_no_1indexed, cp_name)
                                    time.sleep(0.5)
                                except Exception as check_err:
                                    print(f"Error applying coupon in conflict resolver: {check_err}")
                                    self.cp_sonic_blow_process(item_no_1indexed, cp_name)
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
            src = " (พบคูปองใหม่บน SMCO)" if c.get("source") == "SMCO" else " (จากตาราง CP Data)"
            rem = f" [Remark: {c.get('remark')}]" if c.get('remark') else ""
            cand_lines.append(f"  {idx}) CP: {cp} | OC: {oc} | DC: {dc}{src}{rem}")

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

        # ดึงมูลค่า Seller Voucher ของ SKU นี้ (ถ้ามี)
        seller_voucher_val = 0.0
        try:
            if hasattr(self.app, 'financials') and self.app.financials:
                aggr = getattr(self.app.financials, 'aggregated_items', {})
                if sku_key in aggr:
                    seller_voucher_val = float(aggr[sku_key].get("total_seller_voucher", 0.0) or 0.0)
                if seller_voucher_val <= 0.0:
                    seller_voucher_val = float(getattr(self.app.financials, 'seller_voucher', 0.0) or 0.0)
            elif hasattr(self, 'seller_voucher'):
                seller_voucher_val = float(self.seller_voucher or 0.0)
        except Exception:
            seller_voucher_val = 0.0

        sv_suffix = f" (seller voucher {seller_voucher_val:,.2f} บาท)" if seller_voucher_val > 0 else ""

        pattern_msg = (
            f"\n{marketplace} เวลาสั่งซื้อ {purchase_time}\n"
            f"{sku_key} {product_name}\n"
            f"ยิงขายขึ้น {actual_formatted} บาท\n"
            f"ลูกค้าซื้อราคา {expected_formatted} บาท{sv_suffix}\n"
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

        # ดึงมูลค่า Seller Voucher ของ SKU นี้ (ถ้ามี)
        seller_voucher_val = 0.0
        try:
            if hasattr(self.app, 'financials') and self.app.financials:
                aggr = getattr(self.app.financials, 'aggregated_items', {})
                if sku_key in aggr:
                    seller_voucher_val = float(aggr[sku_key].get("total_seller_voucher", 0.0) or 0.0)
                if seller_voucher_val <= 0.0:
                    seller_voucher_val = float(getattr(self.app.financials, 'seller_voucher', 0.0) or 0.0)
            elif hasattr(self, 'seller_voucher'):
                seller_voucher_val = float(self.seller_voucher or 0.0)
        except Exception:
            seller_voucher_val = 0.0

        sv_suffix = f" (seller voucher {seller_voucher_val:,.2f} บาท)" if seller_voucher_val > 0 else ""

        excel_cp_names = [str(c.get('cp_name', '')).strip() for c in (cp_candidates or []) if str(c.get('cp_name', '')).strip()]
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
            sugg_str = (
                f"\n💡 [ระบบคำนวณแนะนำ] พบคูปองบน SMCO ที่ลดแล้วได้ราคา {expected_formatted} บาท พอดีเป๊ะ:\n"
                f"   • แนะนำ: '{s_code}' (ส่วนลด {s_disc:,.2f} บาท)\n"
                f"   • บันทึกใส่คอลัมน์ 'suggested_cp' ใน cp_data.xlsx เรียบร้อยแล้ว (เปิดตรวจสอบและคัดลอกได้)\n"
            )

        pattern_msg = (
            f"\n{marketplace} เวลาสั่งซื้อ {purchase_time}\n"
            f"{sku_key} {product_name}\n"
            f"ยิงขายขึ้น {actual_formatted} บาท\n"
            f"ลูกค้าซื้อราคา {expected_formatted} บาท{sv_suffix}\n"
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
            if hasattr(self, '_applied_adjustments') and self._applied_adjustments is not None:
                self._applied_adjustments.clear()
            self.last_scanned_smco_coupons = []
            self.last_scanned_smco_coupon_details = []
            self.last_preselected_smco_coupons = []
            if hasattr(self, 'app') and self.app:
                self.app.last_pricing_status = ""
                self.app.last_pricing_detail = ""
            self.bot.ProductManager.auto_add_all_items()
            self.bot.current_checkpoint = "กรอกสินค้าลง POS สำเร็จ"

            # รอบที่ 1: ตรวจสอบราคาและจำนวน
            verification_result = self.bot.ProductManager.verify_all()
            print("verification_result (Round 1): ", verification_result)
            self.bot.current_checkpoint = "ตรวจสอบราคาและจำนวนสำเร็จ"

            if isinstance(verification_result.get("price"), dict):
                self.last_expected_prices = {
                    str(k).strip().upper(): v.get("expected")
                    for k, v in verification_result.get("price", {}).items()
                    if isinstance(v.get("expected"), (int, float))
                }

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
                try:
                    order_id = str(getattr(self.bot, 'cus_order', '') or getattr(self.app, 'cus_order', '')).strip()
                    self.record_pos_cart_summary_to_excel(order_id)
                except Exception as rec_err:
                    logger.warning(f"[reconcile_and_verify] บันทึกสรุปรายการสินค้า/คูปองลง Excel ไม่สำเร็จ: {rec_err}")

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

                seller_voucher_val = 0.0
                try:
                    if hasattr(self.app, 'financials') and self.app.financials:
                        aggr = getattr(self.app.financials, 'aggregated_items', {})
                        if sku in aggr:
                            seller_voucher_val = float(aggr[sku].get("total_seller_voucher", 0.0) or 0.0)
                        if seller_voucher_val <= 0.0:
                            seller_voucher_val = float(getattr(self.app.financials, 'seller_voucher', 0.0) or 0.0)
                    elif hasattr(self, 'seller_voucher'):
                        seller_voucher_val = float(self.seller_voucher or 0.0)
                except Exception:
                    seller_voucher_val = 0.0

                sv_suffix = f" (seller voucher {seller_voucher_val:,.2f} บาท)" if seller_voucher_val > 0 else ""

                pattern_msg = (
                    f"\n{marketplace} เวลาสั่งซื้อ {purchase_time}\n"
                    f"{sku} {product_name}\n"
                    f"ยิงขายขึ้น {actual_formatted} บาท\n"
                    f"ลูกค้าซื้อราคา {expected_formatted} บาท{sv_suffix}\n"
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

