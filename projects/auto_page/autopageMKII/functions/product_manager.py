"""
ProductManager
==============
จัดการการ Add สินค้าลง POS และตรวจสอบจำนวน/ราคาหลัง add
ใช้แทน logic ที่เคยอยู่ใน Bot_POS.fn() โดยตรง

Roadmap:
  [x]  auto_add_all_items  — ใส่ของอัตโนมัติ (ย้ายมาจาก Bot_POS)
  [!]  verify_item_qty     — เช็คจำนวนบน POS ตรงกับ input data ไหม
  [!]  verify_item_price   — เช็คราคาขายบน POS ตรงกับ input data ไหม
  [!]  verify_total_price  — เช็คยอดรวมทั้งหมดบน POS
"""

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class ProductManager:
    """
    จัดการการ add สินค้า และตรวจสอบสินค้าบน POS หลัง add เสร็จ

    Parameters
    ----------
    driver      : Selenium WebDriver
    wait        : WebDriverWait instance (ใช้ wait เดียวกับ bot หลัก)
    app         : MyApp instance  (เข้าถึง self.app.items, self.app.correct_sku_pattern ฯลฯ)
    bot         : Bot_POS instance (เพื่อเข้าถึง self.bot.AutoAddProduct)
    """

    # ─── XPaths (ปรับตามหน้า POS จริง) ────────────────────────────────────────
    # SKU text ที่แสดงในแต่ละแถวสินค้า
    XPATH_SKU_TEXTS = (
        "//span[(contains(@ng-click, 'productNameChangeChk(x)'))"
        " and not(contains(@class, 'ng-hide'))]//u"
    )
    # จำนวนที่แสดงในแต่ละแถวสินค้า  (ปรับ selector ตามหน้าจริง)
    XPATH_QTY_DISPLAY = (
        "//span[@class='col-sm-4 ng-binding'"
        " and not(contains(@class, 'ng-hide'))]"
    )
    # ราคาขาย (ปรับ selector ตามหน้าจริง)
    XPATH_UNIT_PRICE = (
        "//div[@class='row']//div"
        "//a[@class='col-sm-6 text-right font-color-base ng-binding']"
    )
    # ยอดรวมทั้งหมด (ปรับ selector ตามหน้าจริง)
    XPATH_TOTAL_PRICE = "//PLACEHOLDER_TOTAL_PRICE_SELECTOR"

    # Column names ใน input data (ปรับชื่อ column ตามไฟล์จริง)
    COL_SKU = "เลขอ้างอิง SKU (SKU Reference No.)"
    COL_QTY = "จำนวน"
    COL_PRICE = "ราคาขาย"  # * ปรับแล้ว # TODO: ปรับชื่อ column
    COL_SUBTOTAL = "ยอดชำระเงิน"  # * ปรับแล้ว  # TODO: ปรับชื่อ column

    def __init__(self, driver, wait, app, bot):
        self.driver = driver
        self.wait = wait
        self.app = app
        self.bot = bot

    # ══════════════════════════════════════════════════════════════════════════
    # [x]  AUTO ADD ALL ITEMS  (ย้ายมาจาก Bot_POS.fn())
    # ══════════════════════════════════════════════════════════════════════════
    def auto_add_all_items(self):
        """
        วน loop ใส่สินค้าทุกรายการจาก self.app.items ลงบน POS
        เทียบเท่า logic เดิมที่อยู่ใน Bot_POS ตรง is_auto_invoice_mode block
        """
        if not self.app.is_auto_invoice_mode.get():
            print("[ProductManager] auto_invoice_mode ปิดอยู่ — ข้ามการ add สินค้า")
            return

        print("[ProductManager] Auto Invoice Mode is activated — เริ่ม add สินค้า")
        for i, item in enumerate(self.app.items):
            print(f"[ProductManager] Item {i}: {item}")
            sku = self.app.correct_sku_pattern(item[self.COL_SKU])
            qty = item[self.COL_QTY]
            self.bot.AutoAddProduct.auto_add_product(sku, qty)

    # ══════════════════════════════════════════════════════════════════════════
    # [!]  VERIFY ITEM QTY  — เช็คจำนวนบน POS vs input data
    # ══════════════════════════════════════════════════════════════════════════
    def verify_item_qty(self) -> dict[str, dict]:
        """
        เปรียบเทียบจำนวนสินค้าที่แสดงบน POS กับจำนวนที่ส่งมาใน input data

        Returns
        -------
        dict  —  { sku: { "expected": int, "actual": int/"NOT_FOUND", "ok": bool } }

        ตัวอย่าง
        --------
        {
          "PR2-000123": {"expected": 2, "actual": 2,           "ok": True },
          "PR2-000456": {"expected": 1, "actual": "NOT_FOUND", "ok": False},
        }
        """
        time.sleep(0.5)  # รอ DOM settle หลัง add

        # * 1) ดึง SKU ทั้งหมดที่แสดงบนหน้า POS
        sku_elements = self.driver.find_elements(By.XPATH, self.XPATH_SKU_TEXTS)
        qty_elements = self.driver.find_elements(By.XPATH, self.XPATH_QTY_DISPLAY)
        pos_data: dict[str, int] = {}
        for sku_el, qty_el in zip(sku_elements, qty_elements):
            try:
                sku_text = sku_el.text.strip()
                qty_text = qty_el.text.strip()
                pos_data[sku_text] = int(qty_text)
            except Exception as e:
                print(f"[ProductManager.verify_item_qty] parse error: {e}")

        # * 2) เปรียบเทียบกับ input data
        result: dict[str, dict] = {}
        # * รวมค่าขนส่งที่อาจจะมีอยู่ใน input data ด้วย (ถ้ามี) เพราะในหน้าย pos มันยิงค่าขนส่งลงไปด้วยต้องเทียบหมดอยู่ละ
        all_items = self.app.items + [self.app.cus_ship_cost.get()] if self.app.cus_ship_cost.get() else self.app.items
        for item in all_items:
            skus = self.app.correct_sku_pattern(item[self.COL_SKU])
            print("verify_item_qty(): checking SKU:", skus)
            expected = int(item[self.COL_QTY])
            for sku in skus:
                actual = pos_data.get(sku, "NOT_FOUND")
                ok = (actual == expected)
                result[sku] = {"expected": expected, "actual": actual, "ok": ok}

                status_icon = "✅" if ok else "❌"
                print(
                    f"[ProductManager.verify_item_qty] {status_icon} "
                    f"SKU={sku}  expected={expected}  actual={actual}"
                )

        return result

    # ══════════════════════════════════════════════════════════════════════════
    # [!]  VERIFY ITEM PRICE  — เช็คราคาขายบน POS vs input data
    # ══════════════════════════════════════════════════════════════════════════
    def verify_item_price(self) -> dict[str, dict]:
        """
        เปรียบเทียบราคาขายบน POS กับ input data

        Returns
        -------
        dict  —  { sku: { "expected": float, "actual": float/"NOT_FOUND", "ok": bool } }

        TODO: ปรับ XPATH_UNIT_PRICE และ COL_PRICE ให้ตรงกับหน้า POS จริง
        """
        time.sleep(0.5)

        sku_elements = self.driver.find_elements(By.XPATH, self.XPATH_SKU_TEXTS)
        price_elements = self.driver.find_elements(By.XPATH, self.XPATH_UNIT_PRICE)

        pos_prices: dict[str, float] = {}
        for sku_el, price_el in zip(sku_elements, price_elements):
            try:
                sku_text = sku_el.text.strip()
                price_text = price_el.text.strip()
                # ลบ comma และ symbol ก่อน parse  เช่น "1,500.00" → 1500.0
                price_val = float(price_text.replace(",", "").replace("฿", "").strip())
                pos_prices[sku_text] = price_val
            except Exception as e:
                print(f"[ProductManager.verify_item_price] parse error: {e}")

        result: dict[str, dict] = {}
        for item in self.app.items:
            sku = self.app.correct_sku_pattern(item[self.COL_SKU])
            # TODO: ถ้าไม่มี column ราคาใน data ให้ skip หรือ set expected = None
            expected = float(str(item.get(self.COL_PRICE, 0)).replace(",", ""))
            actual = pos_prices.get(sku, "NOT_FOUND")
            ok = (actual == expected) if actual != "NOT_FOUND" else False
            result[sku] = {"expected": expected, "actual": actual, "ok": ok}

            status_icon = "✅" if ok else "❌"
            print(
                f"[ProductManager.verify_item_price] {status_icon} "
                f"SKU={sku}  expected={expected}  actual={actual}"
            )

        return result

    # ══════════════════════════════════════════════════════════════════════════
    # [!]  VERIFY TOTAL PRICE  — เช็คยอดรวมทั้งหมด
    # ══════════════════════════════════════════════════════════════════════════
    def verify_total_price(self) -> dict:
        """
        เปรียบเทียบ Grand Total ที่แสดงบน POS กับผลรวมที่คำนวณจาก input data

        Returns
        -------
        dict  —  { "expected": float, "actual": float/"NOT_FOUND", "ok": bool }

        TODO: ปรับ XPATH_TOTAL_PRICE ให้ตรงกับหน้า POS จริง
              และปรับ COL_SUBTOTAL / COL_PRICE ให้ถูกต้อง
        """
        # คำนวณ expected จาก input data
        expected_total = 0.0
        for item in self.app.items:
            try:
                subtotal = float(str(item.get(self.COL_SUBTOTAL, 0)).replace(",", ""))
                expected_total += subtotal
            except Exception as e:
                print(f"[ProductManager.verify_total_price] calc error: {e}")

        # ดึง grand total จากหน้า POS
        actual_total: float | str = "NOT_FOUND"
        try:
            total_el = self.driver.find_element(By.XPATH, self.XPATH_TOTAL_PRICE)
            total_text = total_el.text.strip()
            actual_total = float(total_text.replace(",", "").replace("฿", "").strip())
        except Exception as e:
            print(f"[ProductManager.verify_total_price] cannot read total: {e}")

        ok = (actual_total == expected_total) if actual_total != "NOT_FOUND" else False

        status_icon = "✅" if ok else "❌"
        print(
            f"[ProductManager.verify_total_price] {status_icon} "
            f"expected={expected_total}  actual={actual_total}"
        )

        return {"expected": expected_total, "actual": actual_total, "ok": ok}

    # ══════════════════════════════════════════════════════════════════════════
    # Convenience: รัน verify ทั้งหมดพร้อมกัน
    # ══════════════════════════════════════════════════════════════════════════
    def verify_all(self) -> dict:
        """
        รัน verify_item_qty, verify_item_price, verify_total_price พร้อมกัน
        แล้ว return ผลรวม

        Returns
        -------
        {
          "qty"   : { sku: {...} },
          "price" : { sku: {...} },
          "total" : { ... },
          "all_ok": bool
        }
        """
        qty_result = self.verify_item_qty()
        price_result = self.verify_item_price()
        total_result = self.verify_total_price()

        all_ok = (
            all(v["ok"] for v in qty_result.values())
            and all(v["ok"] for v in price_result.values())
            and total_result["ok"]
        )

        return {
            "qty": qty_result,
            "price": price_result,
            "total": total_result,
            "all_ok": all_ok,
        }
