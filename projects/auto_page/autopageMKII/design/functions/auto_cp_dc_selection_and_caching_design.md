# System Design: Auto CP/DC Selection & Pre-Calculation Caching System
**Module / Feature:** Auto CP/DC Selection & Pre-Calculation Caching (Auto-page MKII)  
**Author:** Pair Programming Session  
**Date:** 2026-08-21  
**Target Path:** `projects/auto_page/autopageMKII/design/functions/auto_cp_dc_selection_and_caching_design.md`

---

## 📌 1. บทนำและวัตถุประสงค์ (Overview & Goals)

ในการยิงสร้างออเดอร์บนระบบ SMCO บ่อยครั้งราคาสินค้าตั้งต้นของ SKU บนระบบไม่ตรงกับราคาขายจริงบน Marketplace (เช่น Shopee / Lazada / TikTok) จำเป็นต้องเลือกใช้คูปองส่วนลด (**DC - Direct/Topup Coupon** และ **CP - Campaign/Add-on Coupon**) เข้ามาช่วยปรับลดราคาให้ตรงกับยอดบิลเป้าหมาย (`sale_price`)

### วัตถุประสงค์ของระบบ:
1. **Pre-Calculation (คำนวณจับคู่ราคาล่วงหน้า):** ดึงรายการคูปองที่ SKU นั้นๆ มีสิทธิ์ใช้ มาจำลองคำนวณ (Subset Sum Solver) ล่วงหน้า ว่าชุดคูปองใดให้ผลรวมส่วนลดที่ทำให้ราคาสุทธิเท่ากับ `sale_price`
2. **Smart Caching (ระบบแคชจำการจับคู่):** เนื่องจากระบบอาจค้นหาและยิง SKU ทีละตัว และสถิติพบว่ามี SKU ซ้ำกันในรอบการส่งถึง **77%** การเก็บ Cache จะช่วยให้เลือกชุดคูปองได้ทันทีใน $O(1)$ โดยไม่ต้องคำนวณซ้ำ
3. **ลดข้อผิดพลาดการออกบิล (Zero Mismatch):** ป้องกันปัญหาระบบเลือกคูปองตัวแรกสุดแบบสุ่มสี่สุ่มห้า จนทำให้ยอดท้ายบิลไม่ตรง

---

## 🧬 2. การวิเคราะห์ Data Structure & Business Rules ของ SMCO

จากการวิเคราะห์ข้อมูล API `productCouponDetail` และการทดสอบจริงบน SMCO สรุปกฎและโครงสร้างข้อมูลได้ดังนี้:

### 2.1 โครงสร้างฟิลด์คูปอง (Data Model)
| ฟิลด์หลัก | ชนิดข้อมูล | ความหมายและข้อควรระวัง |
| :--- | :--- | :--- |
| `couponCode` | `string` | รหัสคูปอง เช่น `DC2607300001`, `CP2608140021` *(ห้ามใช้ Prefix 2 ตัวหน้าเดา Type!)* |
| `couponType` | `int` | **Single Source of Truth**:<br>• `10520001` = **Topup**<br>• `10520005` = **Add-on** |
| `couponDetailDisc` | `float` | ส่วนลดตรง/ส่วนลดสินค้า (Product Discount) |
| `couponDetailCash` | `float` | ส่วนลดเงินสด (Cash Discount) |
| `basicFlag` | `boolean` | `true` = คูปองพื้นฐานทั่วไป, `false` = คูปองพิเศษ/มีเงื่อนไข |
| `conditionFlag` | `boolean` | `true` = มีเงื่อนไขผูกมัด (เช่น ต้องซื้อพ่วงกับ SKU อื่น) |
| `requirementFlag`| `boolean` | `true` = มีข้อกำหนดเพิ่มเติม |
| `couponCondition` | `object` | รายละเอียดเงื่อนไข เช่น ต้องซื้อคู่กับสินค้า Bundle ใด |

### 2.2 กฎเหล็ก: คูปองแบบใดที่ SMCO "ติดอัตโนมัติ" vs "ต้องกดเลือกเอง"
จากการทดสอบยิง SKU บนระบบ SMCO พบพฤติกรรมที่สอดคล้องกับ Data 100%:

$$\mathbf{ติดอัตโนมัติ (Auto\text{-}Applied)} \iff (\text{couponType} == 10520001) \ \mathbf{AND}\ (\text{basicFlag} == \text{true}) \ \mathbf{AND}\ (\text{conditionFlag} == \text{false})$$

* **คูปองที่ติดอัตโนมัติ:** คือ Topup พื้นฐานที่ไม่มีเงื่อนไขผูกสินค้า (เช่น `DC2607300001`, `DC2607310043`, หรือแม้แต่ `CP2608140003` ที่มี Type เป็น Topup)
* **คูปองที่ไม่ติด (ต้องกดเลือกเอง):**
  1. **กลุ่ม Add-on (`couponType: 10520005`):** เป็น Optional / Flash Sale / Campaign เฉพาะกิจ ต้องกดยืนยันเลือกเอง
  2. **กลุ่มมีเงื่อนไข (`conditionFlag: true`):** เป็นคูปอง Bundle ซื้อคู่ ต้องรอตรวจสอบเงื่อนไขก่อน

### 2.3 การคำนวณส่วนลดแบบผสม (Hybrid Discount)
คูปอง 1 ใบสามารถมีได้ทั้ง `couponDetailCash` และ `couponDetailDisc` พร้อมกัน:
$$\text{Total Discount of Coupon} = \text{couponDetailCash} + \text{couponDetailDisc}$$

---

## 📊 3. สถิติและพฤติกรรมจริงจากไฟล์คำสั่งซื้อ (`Sheet2` Analysis)

จากการวิเคราะห์ไฟล์จริง `Order.toship.20260814_20260821.xlsx` (Sheet2 ทั้งหมด 420 แถว):

### 3.1 สถิติการกระจายตัว
* **Unique SKUs:** 170 SKUs (โดย 106 SKUs ปรากฏซ้ำ รวมกันถึง **325 แถว หรือ 77%**)
* **การใช้คูปองต่อ 1 ออเดอร์:**
  * **ไม่มีคูปอง (0 ใบ):** 104 ครั้ง (24.8%)
  * **ใช้คูปองเดี่ยว (1 ใบ):** 244 ครั้ง (58.1%)
  * **ใช้คูปองคู่ (2 ใบ):** 67 ครั้ง (16.0%)
  * **ใช้คูปอง 3 ใบ (3 ใบ):** 5 ครั้ง (1.2%)

### 3.2 คูปองยอดนิยม (Top Usage)
* **Base Topup ยอดฮิต:** `DC2607300001` (ใช้ไปถึง **87 ครั้ง**) ทำหน้าที่เป็นคูปองฐาน
* **Top Add-on CPs:** `CP2608060026` (28 ครั้ง), `CP2608070014` (21 ครั้ง), `CP2608130029` (19 ครั้ง), `CP2607310031` (16 ครั้ง)
* **Top Combinations:**
  * `CP2607300021 + CP2607300035` (11 ครั้ง - แบรนด์เดียวกัน)
  * `DC2607300001 + CP2608140024` (7 ครั้ง - Base + Add-on)
  * `CP2607300045 + CP2608140026` (6 ครั้ง)
  * `DC2607300001 + CP2608140021` (5 ครั้ง)

---

## 🏗️ 4. สถาปัตยกรรมระบบ (System Architecture & Workflow)

```
[Order Row: SKU + Target Price (sale_price)]
                    │
                    ▼
       ┌─────────────────────────┐
       │ Check In-Memory Cache   │
       │ Key: (sku, sale_price)  │
       └────────────┬────────────┘
                    │
         ┌──────────┴──────────┐
         │ (Hit)               │ (Miss)
         ▼                     ▼
┌──────────────────┐   ┌────────────────────────────────────────┐
│ Return Cached    │   │ Fetch productCouponDetail from SMCO API│
│ Coupon Combo     │   └───────────────────┬────────────────────┘
└──────────────────┘                       │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │ 1. Identify Auto-Applied Coupons (Base)│
                       │ 2. Filter Active & Valid Coupons       │
                       │ 3. Subset Sum Matcher (0, 1, 2, 3 CPs) │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                       ┌────────────────────────────────────────┐
                       │ Target Price Matched?                  │
                       └─────────────┬──────────────────────────┘
                                     │
                         ┌───────────┴───────────┐
                         │ (Matched)             │ (Not Matched)
                         ▼                       ▼
             ┌───────────────────────┐   ┌───────────────────────┐
             │ 1. Save to Cache      │   │ 1. Log "No Match Plan"│
             │ 2. Apply CPs in UI/POS│   │ 2. Flag for Manual/PD │
             └───────────────────────┘   └───────────────────────┘
```

---

## ⚙️ 5. รายละเอียดการออกแบบอัลกอริทึม (Algorithm Details)

### 5.1 Caching Strategy
* **Cache Key:** Composite Key `(sku: str, target_price: float)`
  * *เหตุผล:* 1 SKU อาจมีหลายราคาเป้าหมายในแคมเปญต่างกัน เช่น SKU `MNL-001886` ที่ราคา 5,969 ใช้ Base ตัวเดียว แต่ที่ราคา 5,890 ต้องเพิ่ม `CP2608140024`
* **Cache Value Object:**
  ```python
  {
      "sku": "MNL-001886",
      "target_price": 5890.0,
      "base_price": 6390.0,
      "auto_coupons": ["DC2607300001"],        # ติดให้อัตโนมัติ
      "manual_coupons": ["CP2608140024"],      # ต้องสั่งคลิกเลือกเพิ่ม
      "total_discount": 500.0,
      "calculated_price": 5890.0,
      "verified": True
  }
  ```

### 5.2 Subset Sum Combination Solver
```python
def solve_coupon_combination(base_price: float, target_price: float, coupon_list: list) -> list:
    """
    ค้นหาชุดคูปองที่ทำให้ (base_price - total_discount) == target_price
    """
    target_discount = round(base_price - target_price, 2)
    if target_discount <= 0:
        return [] # ไม่ต้องลด หรือราคาตั้งต้นถูกกว่า/เท่ากับเป้าหมาย

    # 1. แยกคูปอง Auto vs Manual
    auto_coupons = []
    manual_candidates = []
    
    for cp in coupon_list:
        disc_val = cp.get('couponDetailCash', 0.0) + cp.get('couponDetailDisc', 0.0)
        cp_info = {
            'code': cp['couponCode'],
            'id': cp['couponId'],
            'detail_id': cp['couponDetailId'],
            'value': disc_val,
            'is_auto': (cp['couponType'] == 10520001 and cp.get('basicFlag') and not cp.get('conditionFlag'))
        }
        if cp_info['is_auto']:
            auto_coupons.append(cp_info)
        else:
            manual_candidates.append(cp_info)

    auto_discount = sum(c['value'] for c in auto_coupons)
    
    # ถ้าแค่ Auto ติดก็ตรงราคาเป้าหมายทันที
    if round(auto_discount, 2) == target_discount:
        return {"auto": auto_coupons, "manual": []}

    remaining_discount = round(target_discount - auto_discount, 2)

    # 2. ค้นหา combinations จาก manual candidates (ลอง 1 ใบ, 2 ใบ, 3 ใบ)
    from itertools import combinations
    for r in range(1, min(4, len(manual_candidates) + 1)):
        for combo in combinations(manual_candidates, r):
            combo_val = sum(c['value'] for c in combo)
            if round(combo_val, 2) == remaining_discount:
                return {
                    "auto": auto_coupons,
                    "manual": list(combo)
                }

    # ไม่พบคู่ที่ลงตัวเป๊ะ
    return None
```

---

## 🛡️ 6. แผนการรับมือ Edge Cases & Safety Fallback

1. **กรณีราคาไม่ตรง (No Combination Match):**
   * บันทึก Log ระบุชัดเจนว่า `"SKU {sku} ราคาเป้าหมาย {target_price} ไม่มีชุด CP/DC ที่ลดได้ตรง"` แทนการสุ่มเลือก
   * พ่นข้อมูลคูปองทั้งหมดที่มีของ SKU นั้นออกมาใน Log เพื่อให้ทีมนำไปเพิ่มใน Master / Excel ได้ทันที
2. **กรณีคูปองหมดอายุหรือถูกปิดใช้งาน:**
   * ตรวจสอบ `startDate` และ `endDate` เทียบกับเวลาปัจจุบัน/เวลาสั่งซื้อของออเดอร์ก่อนนำเข้า Solver
3. **กรณีมีคูปอง Bundle / เงื่อนไขคู่ (`conditionFlag: true`):**
   * ข้ามการนำมาคำนวณใน SKU เดี่ยว เว้นแต่ออเดอร์นั้นจะมี SKU คู่ตรงตาม `couponCondition.conditionDetial` ครบถ้วน

---

## 📈 7. สรุปประโยชน์ที่จะได้รับ (Expected Outcomes)
* **ความเร็วสูงขึ้นอย่างมีนัยสำคัญ:** Cache Hit Rate คาดการณ์สูงถึง **~75-80%** ช่วยลดการยิง API เช็คคูปองซ้ำซ้อน
* **บิลถูกต้อง 100%:** ระบบจะกดเฉพาะคูปองที่ผ่านการคำนวณและยืนยันยอดสุทธิแล้วเท่านั้น
* **รองรับขยายผลเป็น Auto Sync:** สามารถนำโมเดล Solver นี้ไปรัน Batch สร้างตาราง `cp_data` ล่วงหน้าแบบอัตโนมัติได้
