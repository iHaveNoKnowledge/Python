# 📋 AutoPage MKII - Project Changelog & Dev Notes

> **คู่มือการบันทึก**:
>
> - 📌 **ปัญหาที่เจอใหม่ / ฟีเจอร์ที่ต้องทำ**: เพิ่มในส่วน [1. งานที่ต้องทำและปัญหาที่รอแก้](#-1-งานที่ต้องทำและปัญหาที่รอแก้-active-backlog--issues)
> - 💡 **เกร็ดความรู้ / ข้อจำกัดระบบ**: บันทึกในส่วน [2. ข้อควรระวังและ Reference ประจำระบบ](#-2-ข้อควรระวังและ-reference-ประจำระบบ-developer-notes)
> - ✅ **เมื่อแก้เสร็จแล้ว**: ติ๊ก `[x]` และย้ายประวัติลงในส่วน [3. ประวัติการแก้ไขแต่ละเวอร์ชัน](#-3-ประวัติการแก้ไขแต่ละเวอร์ชัน-changelog)

---

## 📌 1. งานที่ต้องทำและปัญหาที่รอแก้ (Active Backlog & Issues)

### 🐛 บัค & การปรับปรุงที่กำลังติดตาม (In Progress / Issues)

- [ ] **[Shopee]** เพิ่มตรรกะแยกเงื่อนไขระหว่าง Shopee ปกติ กับ Shopee Mobile ในหน้าท้าย (เลือกว่าจะจ่ายช่องทางไหนแยกกัน)
- [ ] **[UI / Selenium]** Last pop-up มีตัวรอ event ที่เป็น `driver.wait` ทำให้รอนาน ให้เปลี่ยนเป็น `while loop` ดัก element เพื่อให้จบเร็วกว่า
- [X] **[Address / SMCO]** ตรวจสอบการเลือก อำเภอ/เขต จาก enum บน SMCO คำภาษาไทยบางคำไม่ตรงกับระบบ อาจนำ `PyThaiNLP` (Tokenize) มาใช้คู่กับ `FuzzyWuzzy`
- [X] **[AccelMode / SN]** แก้ไขปัญหา SN เสียเมื่อ SKU มี QTY > 1: ปรับไปใช้ Red Serial Button + Modal Flow สำหรับ Multi-QTY, ทำ Combo Aggregation รวมจำนวนข้ามแถว, Dynamic Wait ตรวจสอบสถานะ, ลบเฉพาะ SN ที่เสียด้วย `_deleteInsertSerial` โดยไม่ลบแถวสินค้าบนตะกร้า และคืนสิทธิ์ SN ในหน่วยความจำหากออเดอร์ไม่สำเร็จ
- [X] **[Logging]** ทำ Log Rotation ให้กับไฟล์ Log เพื่อไม่ให้ขนาดไฟล์ใหญ่เกินไป และสามารถเก็บย้อนหลังแยกรายวันได้
- [X] **[Performance]** ปรับตัวดึง Tracking ให้ Dynamic ขึ้น เช่น ตอนเริ่มค้นหาออเดอร์ถ้ามี Tracking อยู่แล้ว ให้ดึงใส่ Stage ไว้ล่วงหน้าทันที
- [X] **[AccelMode / Modal Speed]** Modal Serial Number เปิดช้าในบางจังหวะ กำลังรอปรับปรุงความเร็วในการค้นหาปุ่มและเปิด Modal
- [X] **[UI / TKINTER]** ในโหมด manual (ไม่ใช้ auto_inv) ตอนจังหวะรอหน้าท้าย เพิ่มระบบ Pop-up แจ้งเตือนเมื่อราคาที่ทำจากหน้าแรกไม่ตรงกับยอดที่ลูกค้าต้องจ่าย พร้อมระบุราคาที่ต้องออกบิล, ราคาบน POS และส่วนต่างอย่างชัดเจน พร้อมปุ่มยืนยันย้อนกลับไปหน้าแรกเพื่อแก้ไขราคา
- [X] **[Auto_inv / CP_data]** หลังจากจัดการเพิ่ม SN ของ order ที่เป็น 1 รายการหลาย sku มันก็ควรบันทึกเป็น 1 รายการหลาย sku แต่นี้มันบันทึก หลายรายการต่อ 1 sku แทน (เอาชุดมา ซอยย่อยแล้วเติม CP ซึ่งมันผิด!!)

### 🚀 ฟีเจอร์ในอนาคต (Planned Features)

- [X] **[Auto CP SAGA]** ระบบตัดสินใจเลือกคูปองอัตโนมัติ (เปรียบเทียบราคา -> ดูช่วงเวลาโปรโมชั่น -> เลือกรุ่นที่ตรงที่สุดตาม Store)
- [ ] **[Auto Export Data]** ระบบดึง Exported Data จาก Marketplace อัตโนมัติด้วย Automation Workflow
- [X] **[Price Memorizer]** ระบบจดจำ Pattern การตัดสินใจปรับราคา/คูปองของแต่ละ SKU เพื่อนำมาใช้อัตโนมัติในครั้งถัดไป

---

## 💡 2. ข้อควรระวังและ Reference ประจำระบบ (Developer Notes)

### 🏢 ข้อมูลระบบภาษี & ลูกค้า (Tax & Customer Rules)

1. **การค้นหาข้อมูลนิติบุคคล**:
   - ค้นหาผ่าน DataForThai: `https://www.dataforthai.com/business/search/{เลข13หลัก}`
2. **SMCO Interface กับใบกำกับภาษี**:
   - หน้าเว็บแสดงผลด้วยภาษาไทย แต่ตอน Search หาในระบบต้องใช้ชื่อภาษาอังกฤษ
   - ลูกค้าที่ขอสำนักงานใหญ่ อาจมีคำว่า `สนญ.` หรือ `(00000)` อยู่ในชื่อ ต้องผ่าน `tax_name_formatter()`
3. **การแก้ไขที่อยู่ (Re-address)**:
   - หลัง Edit ที่อยู่ลูกค้าในระบบ SMCO แล้ว ไม่จำเป็นต้องโหลดลูกค้าใหม่ ระบบจะดึงที่อยู่ล่าสุดมาลงบิลจริง

### 🖨️ ระบบการพิมพ์ & Background Worker (Printing & Subprocess)

1. **SumatraPDF Silence Print**:
   - ต้องใช้ `subprocess.Popen` (Non-blocking) ห้ามใช้ `subprocess.run` แบบ Synchronous เพื่อป้องกัน Tkinter GUI ค้าง (Not Responding)
   - ใช้ Flag `-silent` เพื่อป้องกันหน้าต่าง Popup แจ้งเตือนของ SumatraPDF

### 🛡️ ความปลอดภัยของ State ข้อมูลคำสั่งซื้อ (Order State Isolation & Leak Prevention)

1. **การรีเซ็ต State เมื่อเริ่มค้นหาออเดอร์ใหม่**:
   - ฟังก์ชัน `reset_all_display()` ต้องเคลียร์ `self.items = []`, `self.nondistortedData = {}`, `self.tracking_from_data = []` และ `self.financials.items = []` เสมอ ห้ามให้มีข้อมูลของออเดอร์ก่อนหน้าหลงเหลือ
2. **กรณีค้นหาออเดอร์ไม่พบในไฟล์นำเข้า (Export File Not Found)**:
   - ต้องล้าง `self.items = []`, หยุดการทำงานของ `operation_thread` ทันที และโยน `ValueError` เพื่อบันทึกลง `Failed_Orders` **ห้ามปล่อยให้ Thread หลุดไปเข้าขั้นตอนเปิดบิลเด็ดขาด**
3. **Safeguard หน้าประตูก่อนเปิดบิล (`operation_task_thread`)**:
   - ก่อนสั่ง `operation_start()` ต้องตรวจสอบเสมอว่า `self.app.items` ต้องไม่เป็นค่าว่างเปล่า หากว่างเปล่าต้องยกเลิกออเดอร์ทันที ห้ามแตะต้องหน้า POS
4. **การทดสอบความปลอดภัย (Regression Testing & Logic Integrity)**:
   - ทุกครั้งที่มีการแก้ไข/ปรับปรุงฟังก์ชันใดๆ (เช่น Pricing Engine, Payment, Customer, Order Guard) จะต้องรัน Test Suites ที่เกี่ยวข้องใน `tests/` เสมอ เช่น:
     - `python -m unittest tests/test_seller_voucher_pricing.py` (ตรวจสอบการหัก Seller Voucher และค้นหา CP ที่ตรงกับราคาลด)
     - `python -m unittest tests/test_sonic_blow_cp_selector.py` (ตรวจสอบความถูกต้องของ Sonic Blow CP Selector และ XPath)
     - `pytest tests/test_order_leak_guard.py` (ตรวจสอบความปลอดภัยของ Order State Isolation)
     - `python -m unittest tests/test_final_page_validator.py` (ตรวจสอบความถูกต้องของหน้าชำระเงินสุดท้าย)
   - เพื่อป้องกันไม่ให้ logic เดิมหลุด ถดถอย หรือกระทบ flow อื่นเด็ดขาด
5. **การจัดการ Seller Voucher กับ Campaign Coupon (CP) & Final Payment**:
   - ปัจจุบันส่วนลดจากผู้ขาย (`โค้ดส่วนลดชำระโดยผู้ขาย` / `ส่วนลดจากร้านค้า`) ถูกนำมาผูกเป็น Campaign Coupon (CP) บน SMCO POS
   - ใน `OrderFinancials.recalculate()` จะคำนวณ `item_expected_prices` โดยหัก Seller Voucher ออกจากราคา SKU เป้าหมาย ทำให้กระบวนการจับคู่ CP ใน `cp_data.xlsx` และตรวจเช็คราคาบน POS ตะกร้าสินค้าตรงกับราคาที่ได้รับส่วนลดจริง
   - ยอดเงินหน้าสุดท้าย (`#ripCash00` ใน `POSPaymentHandler`) คิดจาก `final_price = sum_price - seller_voucher` ซึ่งตัดยอดพอดีกับยอดรวมตะกร้าบน POS (Grand Total) ทำให้ยอดคงเหลือ (`wrimagecard-lightGray`) เท่ากับ `0.00` บาทอย่างสมบูรณ์

---

## 📦 3. ประวัติการแก้ไขแต่ละเวอร์ชัน (Changelog)

### [ver5.x.x] - 2026-10-10

- [X] **[Standalone Coupon Separation & Universal SMCO Live Fetch Fix]**:
  - **Standalone vs Combined Preselected Resolution (`MNL-002358`)**: ปรับปรุงเงื่อนไขใน `find_suggested_cp_for_discount()` ไม่ให้พ่วง `preselected` (เช่น `CP2609290086`) เข้ามาอัตโนมัติ เมื่อคูปองที่ค้นพบ (เช่น `CP2610090037`) ให้ส่วนลดเต็มจำนวนจากราคาตั้งต้น (`abs(sub_disc - (target_discount + pre_discount)) <= 0.05`) หรือเป็นคูปองที่มี Remark ระบุราคาขายเป้าหมายตรงกับ `expected_price` (`is_remark_target_match = True`) ระบบจะแนะนำคูปองเดี่ยวๆ พร้อมสั่ง Deselect คูปอง Auto Top-up ส่วนเกินออก ทำให้ราคาจบตรง 2,157 บาทพอดี ไม่ลดซ้ำซ้อน
  - **Universal Live SMCO POS Fetch (`MNL-002120`)**: เพิ่มเมธอด `fetch_product_master_info(sku)` และปรับปรุง `resolve_multi_coupon_info(sku=...)` ให้ยิงดึงข้อมูลสดผ่าน POS API `/getProductMasterInfoPOSV3.htm` อัตโนมัติเมื่อคูปองที่ใช้ยังไม่มีข้อมูลในแคช (ครอบคลุมทั้ง Single SKU ที่ไม่ได้ผ่าน `auto_add_product` และ Combo SKU) ทำให้ได้ช่วงวันที่โปรโมชั่นจริง (`01/10/2026 - 31/10/2026`) ครบทั้ง Start และ End Date แทนที่จะตกไปใช้ Fallback จากตัวเลขรหัสคูปอง
  - **Partial Fallback Guard in Cart Summary**: เพิ่ม Guard ใน `record_pos_cart_summary_to_excel()` หากวันที่ได้มาเป็นเพียง Fallback ที่ไม่มี End Date จะไม่อนุญาตให้เขียนทับ `usage_start_date` เดิมที่มีอยู่แล้ว

- [X] **[Separate Suggestion Isolation & Empty Placeholder Update (`cp_data`)]**:
  - **Isolated Suggestion Update**: เมื่อได้รับ Suggestion สำหรับ SKU และราคาเป้าหมายที่มีแถวเดิมใน `cp_data.xlsx` แต่ `cp_name` ยังว่างอยู่ ระบบจะทำการอัปเดตข้อมูลลงเฉพาะกลุ่มคอลัมน์แนะนำ (`suggested_cp`, `suggested_usage_start_date`, `suggested_usage_end_date`, `suggested_remark`) โดยคงช่องใช้จริง (`cp_name`, `usage_start_date`, `usage_end_date`) ไว้เป็นค่าว่างเพื่อรอการยิงผ่านจริงหรือการยืนยัน
  - **Non-Conflicting Multi-Pattern Split**: หากระบบค้นพบหลาย Pattern สำหรับ SKU และราคาเดียวกัน (เช่น Pattern 1 เป็น Single CP, Pattern 2 เป็น Combo CP+DC) ระบบจะนำ Pattern แรกหยอดลงในแถวเดิมที่ว่าง และทำการแตกแถวใหม่ (Insert New Row) สำหรับ Pattern ที่ 2, 3... โดยทุกแถวยังคงมี `cp_name` ว่างไว้ทั้งหมด ทำให้ตาราง `cp_data` ทำหน้าที่เป็นกระดานรวบรวมตัวเลือก (Suggestion Board) ได้อย่างสมบูรณ์ และไม่เกิดความขัดแย้งของข้อมูล
- [X] **[No-Coupon `cp_name = "NONE"` & Multi-Source Auto-Population of `usage_start_date` / `usage_end_date`]**:
  - **No-Coupon `cp_name = "NONE"`**: กำหนดค่า `cp_name = "NONE"` อัตโนมัติสำหรับรายการสินค้าที่ไม่มีการใช้คูปอง CP/DC (ซึ่ง `last_adjustment_method == "NONE"`) ทั้งใน Local Excel (`cp_data.xlsx`) และ Payload ของ Google Sheets Web App ช่วยให้ผู้ใช้ตรวจสอบสถานะได้ทันทีจากคอลัมน์ C (`cp_name`) โดยไม่ต้องเลื่อนสายตาไปดูคอลัมน์ `last_adjustment_method` ทางขวาสุด
  - **Multi-Source Auto-Population of `usage_start_date` & `usage_end_date`**: ปรับปรุงการดึงวันที่ของคูปองใน `get_coupon_start_and_end_dates()` และ `resolve_multi_coupon_info()` ให้ดึงข้อมูลจากหลายแหล่ง:
    1. ข้อมูลสดจาก Modal (`last_scanned_smco_coupon_details`)
    2. แคชของ SMCO Product Master API (`_product_master_cache`) รองรับทั้ง `startDate` และ `endDate`
    3. ข้อมูลประวัติจาก `cp_df` / `cp_data.xlsx`
    4. Fallback ดึงวันเริ่มต้นจากรหัสคูปองโดยตรง เช่น `DC2609280008` -> `28/09/2026`
    - ทำให้กรณีออเดอร์ที่เป็น `AUTO_MATCH` (ราคาตรงตั้งแต่แรกบน POS โดยไม่ต้องเปิด Modal สแกน) สามารถบันทึกค่า `usage_start_date` และ `usage_end_date` ลงตารางได้อย่างครบถ้วน
  - **Multi-Coupon Date Hierarchy**: สำหรับรายการที่มีคูปองหลายใบ (เช่น `CP... DC...`) จะเลือกคูปองที่มี `usage_start_date` ใหม่ที่สุด และหาก `usage_start_date` เท่ากัน จะเลือกคูปองที่มี `usage_end_date` สั้นที่สุด/สิ้นสุดไวที่สุดเสมอ
- [X] **[CP Sonic Blow Dual-Mode Architecture (`manual` vs `auto_inv`)]** แยกโหมดการทำงานของ `cp_sonic_blow_process()` ใน [pricing_engine.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/functions/pos/pricing_engine.py) ออกเป็น 2 โหมดอิสระตามบริบทการใช้งาน:
  - **Manual Mode (`mode="manual"`)**: ทำงานเป็น Toggle บริสุทธิ์สำหรับการกดคลิกผ่านปุ่มลัดหรือ UI ของผู้ใช้
  - **Auto Invoice Mode (`mode="auto_inv"`)**: ทำงานเป็น Bidirectional Exact State Sync เพื่อจับคู่และปรับสถานะคูปองให้ตรงกับ Master Data (`cp_data`) 100% โดยจะสั่งเลือกคูปองเป้าหมาย และสั่งยกเลิกติ๊ก (Deselect) คูปองที่ไม่ต้องการหรือคูปอง Auto Top-up ที่ระบบ POS ติ๊กติดมาให้เองโดยอัตโนมัติ
- [X] **[Full CP/DC Combinations (1–4 Tokens) & Preselected Auto Top-Up Pairing & No-Pattern Remark]**:
  - **Full Subset Combinations Search (1–4 CP/DC)**: ปรับปรุง `find_suggested_cp_for_discount()` และ `find_all_matching_coupons_on_smco()` ใน [pricing_engine.py](file:///c:/Users/ONLINE_MIS/Desktop/Trans-am%2031-01-2022/Projects/python/Python/projects/auto_page/autopageMKII/functions/pos/pricing_engine.py) ให้ค้นหาความน่าจะเป็นทุกรูปแบบของชุดคูปอง (Pure CP/DC coupons) 1–4 ใบอย่างครอบคลุม โดยไม่พึ่งพาสูตรปรับราคา OC/DC
  - **Preselected (Auto Top-Up) Pairing Preservation**: แก้ไขกรณีที่สินค้ามีคูปอง Auto Top-up ติดมาตั้งแต่ต้น (เช่น ยิง SKU `MNL-002535` ติด `DC2609280008` ลด 100 บาท แล้วบอทกดเพิ่ม `CP2610100002` ลด 57 บาท เพื่อให้ได้ราคาเป้าหมาย 3,890 บาท) ให้บันทึกรหัสคูปองที่ใช้จริงครบทุกตัวเป็น `"DC2609280008 CP2610100002"` โดยรักษาลำดับของคูปองที่เลือกไว้ก่อนหน้าและคูปองใหม่ได้อย่างถูกต้อง
  - **Fallback No-Pattern Remark Format**: เมื่อระบบทดลองจับคู่ทุก Combination แล้วไม่พบ Pattern ที่ตรงกับราคาเป้าหมาย จะสร้าง Remark ในรูปแบบ `"ไม่มี pattern, cp/dcที่พบ: {cp_dc_count} อัน"` (นับจำนวนคูปอง CP/DC ทั้งหมดที่สแกนพบบนหน้า Modal SMCO POS) และบันทึกลงชีต/Excel เพื่อแจ้งให้ผู้ใช้ทราบสถานะอย่างชัดเจน
- [X] **[Preselected Auto Top-Up Conflict & Pre-Overcharge Candidate Check (`diff > 0`)]** แก้ไขปัญหาตรรกะการปรับราคาเมื่อราคาบน POS ต่ำกว่าราคาเป้าหมาย (`diff_val > 0`):
  - สำหรับกรณีสินค้าชุด (เช่น เซ็ตหมึก `SP2-001414 + SP2-001415 + SP2-001416 + SP2-001417` ที่ราคาซื้อคือ 1,128 บาท แต่บน POS ติด Auto Top-up จนราคาลดลงเหลือ 1,000 บาท):
  - ระบบจะตรวจสอบค้นหาคูปองแคมเปญที่ระบุราคาเป้าหมายใน Remark หรือสแกนพบ candidate คูปองที่ตรงกับราคาซื้อก่อนเสมอ ก่อนที่จะตัดสินใจทำ Overcharge
  - เมื่อสั่งเลือกคูปองแคมเปญดังกล่าว ระบบ SMCO POS จะปลดคูปอง Auto Top-up เดิมออกโดยอัตโนมัติ ทำให้ราคาสุทธิปรับตรงกับ 1,128 บาทพอดี โดยไม่ต้องใช้วิธี Overcharge
- [X] **[Payment / Installment Promotions Strict Filtering]** เพิ่มตัวกรองคัดทิ้งคูปองประเภทผ่อนชำระและโปรโมชันช่องทางชำระเงิน:
  - ตัดคูปองที่มี `couponTypeEn == "Payment"`, `couponTypeTh == "Payment"`, หรือรหัสขึ้นต้นด้วย `IS` (เช่น `IS2604170001` ใน `PR5-000673`) ออกจาก `get_aggregated_combo_coupons()` และ `scan_matching_cp_candidates_on_smco()` ทั้งหมด
  - บังคับยอมรับเฉพาะคูปองประเภท `Topup` และ `Add-on` ที่ขึ้นต้นด้วย `CP` หรือ `DC` เท่านั้น ป้องกันการหยิบคูปองผิดประเภทมาออกบิลเงินสดออนไลน์
- [X] **[Auto-Match Adjustment Method & Dynamic Coupon Date Metadata Auto-Extraction]** ปรับปรุงการบันทึกประวัติการปรับราคาและข้อมูลวันที่สำหรับสินค้าที่ราคาตรงเป้าหมายทันที:
  - สำหรับ SKU ที่ยิงลงตะกร้าแล้วราคาตรงกับราคาขายจริงทันทีโดยมีคูปองแคมเปญติดมา: บันทึก `last_adjustment_method = "AUTO_MATCH"` (แทนคำว่า `CP` เดิม) เพื่อให้ทราบชัดเจนว่าเป็นออเดอร์ที่ราคาตรงเองตั้งแต่ต้น
  - ดึงข้อมูล `usage_start_date`, `usage_end_date` และ `suggested_remark` จาก Coupon Details ของคูปองที่ติดมา บันทึกลงตาราง `cp_data` อัตโนมัติผ่าน `resolve_multi_coupon_info()`
- [X] **[Dynamic Conflict Resolver Payload & Multi-User Concurrency Hardening]** ปรับปรุงโครงสร้างตารางและการทำงานของ `conflict_resolver`:
  - ปรับ Payload และโครงสร้างข้อมูลให้รองรับ Candidate จำนวนไม่จำกัด ($N$ Candidates) ผ่านฟิลด์ `candidates` (ข้อความ Multi-line) และ `candidates_count` ควบคู่กับ legacy fields `candidate_1` ถึง `candidate_3`
  - ปรับปรุง Google Apps Script Backend ให้รองรับการทำงานพร้อมกันหลายเครื่อง (Multi-User) โดยใช้ `LockService.getScriptLock()`, บังคับ `SpreadsheetApp.flush()`, และแปลงตัวเลขอย่างปลอดภัยด้วย `parseSafeFloat` ป้องกันปัญหาเครื่องหมายจุลภาค (Comma) ทำให้ข้อมูลไม่ชนกันและไม่เกิดแถวซ้ำซ้อน
- [X] **[Conflict Resolver Tab & Live SMCO Active Candidate Filtering & Dual-Month Date Auto-Correction]** เพิ่มระบบจัดการความขัดแย้งผ่านแท็บ `conflict_resolver` ร่วมกับระบบคัดกรองคูปองสดจาก SMCO และป้องกันความคลาดเคลื่อนของวันที่:
  - **Conflict Resolver Multi-Sheet Architecture**: เพิ่มแท็บ `conflict_resolver` บน Google Sheets และ Local Excel (`cp_data.xlsx`) สำหรับรวบรวมเคสที่ SKU และราคาเป้าหมายมีตัวเลือกโปรโมชันซ้ำซ้อนกัน โดยมีคอลัมน์ `sku`, `sale_price`, `candidate_1`, `candidate_2`, `candidate_3`, `suggested_winner`, `reason`, `admin_selection`, `status`, `last_updated`
  - **Smart Tie-Breaking Auto-Proceed**: เมื่อเกิดความขัดแย้งและยังไม่มีการตัดสินใจจาก Admin ระบบจะไม่หยุดข้ามออเดอร์ให้คิวสะดุด แต่จะใช้การประเมินคะแนนอัจฉริยะ (Date Validity + Date Recency + Simplicity No OC) เลือกตัวที่ดีที่สุด (`suggested_winner`) ไปออกบิลต่อทันที พร้อมส่งบันทึกเข้า `conflict_resolver`
  - **Admin Selection Priority**: หาก Admin เข้าไประบุรหัสคูปองใน `admin_selection` และตั้ง `status = APPROVED` บอทจะล็อกใช้ตามที่ Admin สั่ง 100% ทันที
  - **Used CP Mask Isolation**: ปรับปรุง `record_pos_cart_summary_to_excel()` ใน [pricing_engine.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/functions/pos/pricing_engine.py) ให้แมตช์แถวด้วย `used_cp` ป้องกันไม่ให้ออเดอร์ที่สำเร็จไปอัปเดตทับแถวคูปองอื่นของ SKU เดียวกัน จนเกิดแถวเบิ้ลหรือวันที่ปนเปื้อน
  - **Dual-Month US Locale Auto-Correction**: ปรับปรุง `_clean_dataframe()` ใน [cp_data_loader.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/functions/pos/cp_data_loader.py) ตรวจจับการสลับวัน/เดือนของโปรโมชัน (เช่น `04/09` เพี้ยนเป็น 9 เม.ย. และ `08/10` เพี้ยนเป็น 10 ส.ค.) และแปลงกลับเป็น `04 ก.ย.` และ `08 ต.ค.` อย่างแม่นยำ
  - เพิ่มชุดทดสอบ Unit Test ครอบคลุมใน [test_conflict_resolver_and_live_filter.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/tests/test_conflict_resolver_and_live_filter.py) (ผ่าน 100%)

- [X] **[Auto-Record Ambiguous Recipe Patterns & Multi-CP/DC Comma-Separated Remark & Date Hierarchy Rules]** บันทึกสูตร Pattern อัตโนมัติเมื่อพบความคลุมเครือ พร้อมจัดรูปแบบ Remark และลำดับความสำคัญของวันที่สำหรับ Multi-CP/DC:
  - **Auto-Record Patterns on Ambiguity Alert**: เมื่อระบบตรวจพบทางเลือก CP/DC มากกว่า 1 ชุดบนหน้าเว็บ SMCO (Ambiguity Alert) และหยุดข้ามออเดอร์ (`Order skipped, multiple ambiguous CP/DC options found`) ระบบจะใช้โอกาสนี้บันทึกข้อมูลทุกชุด Pattern ที่ตรวจพบ (โดยเฉพาะสูตร/คูปองใหม่ที่พบบน SMCO) ลงใน `cp_data.xlsx` และซิงค์ไปยัง Google Sheet พร้อมข้อมูลข้อเสนอแนะ (`suggested_cp`, `suggested_usage_start_date`, `suggested_usage_end_date`, `suggested_remark`) โดยไม่ทับสูตรเดิมที่มีอยู่ เพื่อให้ Admin ตรวจสอบและเลือกใช้ได้ทันที
  - **Multi-Coupon Comma-Separated Remark Order**: กรณี SKU มีการใช้ CP/DC หลายตัว (เช่น Combo หรือมีทั้งคูปองและส่วนลด) ใน [pricing_engine.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/functions/pos/pricing_engine.py) ฟังก์ชัน `resolve_multi_coupon_info()` จะรวบรวมข้อความ Remark ของคูปองแต่ละตัวมาเรียงต่อกันตามลำดับของรหัส CP/DC และคั่นด้วยเครื่องหมาย `", "` ในคอลัมน์ `suggested_remark` เดียวกัน
  - **Smart Date Preference Hierarchy**: สำหรับช่วงเวลาการใช้งานของชุดคูปองหลายตัว:
    1. เปรียบเทียบ `suggested_usage_start_date`: เลือกคูปองที่มีวันเริ่มต้นใหม่กว่า (ล่าสุดกว่า)
    2. หากวันเริ่มต้นเท่ากัน: เลือกคูปองที่มี `suggested_usage_end_date` สั้นกว่า (หมดอายุไวกว่า) เพื่อความถูกต้องและปลอดภัยของระยะเวลาโปรโมชั่น
  - เพิ่มการทดสอบครอบคลุมใน `tests/test_realtime_ambiguity_and_remark.py` (ผ่าน 100%)

- [X] **[Combo Coupon Description Preference & Remark Conflict Resolution]** แก้ไขปัญหาคูปองสินค้าเซ็ต (Combo SKU) ที่ Remark ถูกเคลียร์เป็น `"-"` หรือค่าว่างเนื่องจากความขัดแย้งของราคาย่อย:
  - **Campaign Description Prioritization**: สำหรับสินค้าประเภทเซ็ต (เช่น `SP2-001753+SP2-001755`) คูปองแคมเปญระดับเซ็ต เช่น `CP2609300040` มักมีรายละเอียดแคมเปญ (`desc`) ระบุราคาเซ็ตไว้ชัดเจน (เช่น `"Shp/TT เดือน ต.ค. ราคาเซ็ทละ 1056"`) แต่ SKU ย่อย (เช่น `SP2-001753`) อาจส่ง Remark ย่อยของตัวเองเข้ามาแทน (เช่น `"Shp/TT เดือน ต.ค. ราคา 409"`) ทำให้เดิมถูกระบบตรวจจับว่าราคา 409 ไม่ตรงกับ 1,056 บาท แล้วทำการล้างค่าทิ้งเป็น `""` / `"-"`
  - **Dynamic Price-Matching Remark Selection**: ปรับปรุง `get_aggregated_combo_coupons()`, `find_suggested_cp_for_discount()` และ `find_all_matching_coupons_on_smco()` ใน [pricing_engine.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/functions/pos/pricing_engine.py) ให้ตรวจสอบและให้ลำดับความสำคัญสูงสุดแก่ข้อความ (ไม่ว่าจะเป็น `desc` หรือ `remark`) ที่ระบุราคาเป้าหมายตรงกับราคาขายของเซ็ต (`expected_price` = 1,056 บาท) ช่วยให้ดึงข้อความ `"Shp/TT เดือน ต.ค. ราคาเซ็ทละ 1056"` มาใช้งานได้อย่างแม่นยำ ไม่ถูกตัดสิทธิ์หรือถูกเคลียร์ทิ้ง
  - อัปเดตข้อมูลบน Google Sheets และ local `tables/cp_data.xlsx` ให้แถว 1,056 บาท มี `suggested_remark = "Shp/TT เดือน ต.ค. ราคาเซ็ทละ 1056"` เรียบร้อย

- [X] **[CP/DC Distinct Recipe Pattern Separation & Cross-Contamination Prevention]** ป้องกันการเขียนทับสูตรคูปองและแยกแถวสำหรับแต่ละ Pattern อย่างเด็ดขาด:
  - **Recipe Pattern Identity Separation**: ปรับปรุง `add_missing_cp_to_excel()` ใน [pricing_engine.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/functions/pos/pricing_engine.py) ให้แยกแยะเอกลักษณ์ของแต่ละสูตร (Pattern Identity) จากทั้ง `sku`, `sale_price`, `cp_name`, `suggested_cp`, `oc_amount`, และ `dc_amount` โดยจะไม่อัปเดตทับแถวเดิมหากเป็นคนละคูปอง หรือมีการปรับราคาต่างกัน (เช่น สูตรเดิม `CP2609140012 + OC 5 4` กับสูตรใหม่ `CP2610050027` ที่ไม่มี OC) แต่จะแยกบันทึกเป็นอีกแถวหนึ่งอย่างชัดเจน
  - **Zero OC/DC Contamination**: ป้องกันค่า `oc_amount` หรือ `dc_amount` จากสูตรเดิมรั่วไหลมาติดกับสูตรคูปองใหม่ โดยรับค่าและส่งต่อค่า adjustments เฉพาะของสูตรนั้นๆ ทั้งใน Local Excel และ Payload ไปยัง Google Sheets
  - **Multi-Recipe Loader Deduplication Fix**: ปรับปรุง `_merge_dfs()` และ `_is_exact_duplicate()` ใน [cp_data_loader.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/functions/pos/cp_data_loader.py) ให้รวมคอลัมน์คูปองและการปรับราคาลงใน Subset การ Deduplicate เพื่อไม่ให้สูตรทางเลือกที่สองใน SKU และราคาเดียวกันถูกตัดทิ้ง ทำให้ทั้งสองสูตรคงอยู่ใน Memory และทำงานร่วมกับ Ambiguity Detection ได้อย่างสมบูรณ์
  - **Data Separation & Cleanup**: ทำการแยกแถวใน `tables/cp_data.xlsx` และปรับปรุงข้อมูลแถวเดิมบน Google Sheets ให้ทั้งสูตรเดิม (`CP2609140012 + OC 5 4`) และสูตรใหม่ (`CP2610050027` ไม่ปรับราคา) แยกกันอย่างถูกต้อง

- [X] **[DualSource CP Loader Real-Time Google Sheet & Local Sync & Remark Conflict Sanitization]** แก้ไขปัญหาคอลัมน์ `suggested_remark` และ `suggested_cp` ไม่อัปเดตบน Google Sheets และ local `cp_data.xlsx`:
  - **Local Path Fallback & Guaranteed Loader**: เพิ่มการค้นหาพาธสำรอง `tables/cp_data.xlsx` ใน `POSPricingReconciler.__init__`, `add_missing_cp_to_excel()` และ `record_pos_cart_summary_to_excel()` ป้องกันการหยุดทำงานเมื่อ `cp_table_location` ยังไม่ได้ถูกเซ็ตใน Session
  - **Remark Conflict Sanitization**: ตรวจสอบความสอดคล้องระหว่างราคาที่ระบุในข้อความ Remark กับราคาขายจริง (`act_price` / `expected_price`) เช่น กรณีสินค้าเซ็ต 1,056 บาท แต่ Remark ติดข้อความ "ราคา 409" มาจาก SKU ย่อย ระบบจะเคลียร์ค่าใน Local Excel เป็นค่าว่าง และส่ง `"-"` ไปยัง Google Apps Script เพื่อบังคับเขียนทับลบค่าเดิมทิ้งทันที
  - **Deduplication Logic Fix (`_is_exact_duplicate`)**: ปรับปรุงการตรวจสอบใน `DualSourceCPLoader` ให้ตรวจจับเมื่อมีการเคลียร์ฟิลด์ (เช่น ค่าเดิมมี แต่ค่าใหม่ส่ง `""` หรือ `"-"`) เพื่อไม่ให้เข้าใจผิดว่าเป็นแถวซ้ำซ้อน และส่ง POST อัปเดตไปยัง Google Sheet ได้สำเร็จ พร้อมเคลียร์ Cache ทันที
  - **Cloud-to-Local Auto Sync (`sync_to_local_excel`)**: เพิ่มระบบซิงค์ข้อมูลจาก Google Sheets กลับลงมายัง Local Excel (`cp_data.xlsx`) อัตโนมัติเมื่อมีการโหลดข้อมูลผ่าน `load_cp_df()` ทำให้ข้อมูลฝั่ง Local เป็นปัจจุบันตรงกับบนคลาวด์เสมอ
  - เพิ่มชุดทดสอบ Unit Test ครอบคลุมใน [test_realtime_ambiguity_and_remark.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/tests/test_realtime_ambiguity_and_remark.py)

### [ver5.x.x] - 2026-10-10

- [X] **[Manual Invoice Mode Accel Processed_Logs & SN Deduction Support]** รองรับการตัด SN และบันทึกผลการออกบิลลงชีต `Processed_Logs` ของไฟล์ Accel สำหรับการออกบิลแบบ Manual:
  - แก้ไขเงื่อนไขใน `autopage_MKII_ver5.x.x.py` ที่ฟังก์ชัน `_update_accel_on_complete`, จุดดักจับข้อผิดพลาดระหว่างยืนยันบิล (Final popup), จุด submit retry, จุดยกเลิกคำสั่งซื้อ และจุดค้นหาออเดอร์ (`order_search`)
  - เปลี่ยนจากการตรวจสอบ `is_accel_mode_activated.get()` (สวิตช์ Auto Run) เพียงอย่างเดียว เป็นการตรวจสอบการมีอยู่จริงของไฟล์ Accel (`self.app.accel_mode.accel_file_dir`)
  - เมื่อออกบิลแบบ Manual โดยที่โหลดไฟล์ Accel ไว้อยู่ในระบบ ระบบจะตัด SN ที่ถูกใช้งาน (`deduct_accel_file_data`) และบันทึกข้อมูล `Completed` พร้อมเลขบิล (`bill_no`), `tracking`, และราคาลงในชีต `Processed_Logs` ของไฟล์ Accel เสมอ
  - เพิ่มชุดทดสอบ Unit Test `test_manual_mode_records_to_processed_logs_when_accel_file_present` ใน `tests/test_accel_unified_processed_logs.py`
- [X] **[Pricing Engine Seller Voucher Detail & Combo Coupon Calculation]** ปรับปรุงระบบคำนวณและรายงานราคาส่วนลดคูปอง:
  - ปรับปรุงข้อความถามราคาเป้าหมายในโหมดรันให้แสดงมูลค่า Seller Voucher สุทธิอย่างชัดเจน เช่น `(seller voucher 200.00 บาท)`
  - ปรับปรุง `find_all_matching_coupons_on_smco()` ให้คำนวณและรวมคูปอง Preselected (เช่น `DC...`) กับคูปองเสริม (เช่น `CP...`) เป็นชุดคอมโบเดี่ยวที่ได้ราคาสุทธิถูกต้อง
  - เคลียร์ข้อความ Remark "ไม่มี pattern..." ออกจากตาราง `cp_data` เมื่อยิงสินค้าสำเร็จ เพื่อไม่ให้มีข้อความเตือนตกค้างในระบบ

### [ver5.x.x] - 2026-10-05


- [X] **[Pricing Engine Real-Time SMCO Candidate Discovery & Multi-Recipe Ambiguity Protection (Strict Safety)]** เพิ่มระบบตรวจจับโปรโมชั่น/คูปองใหม่บนเว็บ SMCO แบบ Real-time และระบบป้องกันความคลุมเครือของสูตรคูปอง:
  - พัฒนาระบบ `find_all_matching_coupons_on_smco()` ใน [pricing_engine.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/functions/pos/pricing_engine.py) สแกนหาคูปอง/คอมโบใหม่ที่เปิดใช้งานสดๆ บนหน้าเว็บ SMCO (เช่น คูปองเดี่ยวตัวใหม่ `CP2610050027` ที่ตรงกับราคาสุทธิของเซ็ตสินค้า เช่น 993) แม้ใน `cp_data.xlsx` จะเคยมีสูตรผสมเดิมบันทึกไว้ (เช่น `CP2609140012 + OC 5 4`)
  - **Real-time Ambiguity Guard (Strict Safety)**: เมื่อพบว่ามีทางเลือกคูปอง/สูตรผสมที่ทำราคาได้ตรงเป้าหมายมากกว่า 1 ทางเลือก (ทั้งจากตารางและจากหน้าเว็บสด) บอทจะหยุดทำงานทันที ไม่สุ่มเลือก เพื่อความปลอดภัยสูงสุด:
    1. ยกเลิกออเดอร์พร้อมส่งคำเตือน `_raise_ambiguous_cp_guide`
    2. รวบรวมสูตรคูปองที่เป็นไปได้ทั้งหมดบันทึกลงในคอลัมน์ `suggested_cp` ของชีต `Processed_Logs`
    3. ระบุข้อความชัดเจนเพื่อให้ Admin ตัดสินใจและอัปเดตตาราง Master Data
  - ปรับปรุง `is_coupon_valid_for_order()` ให้แปลงวันที่ด้วย `parse_smart_date()` ป้องกันข้อผิดพลาด `TypeError` ระหว่าง `str` และ `datetime.date`
- [X] **[Payment Handler Foreground & Focus-Force Price Mismatch Alert Dialog]** ปรับปรุงหน้าต่าง Pop-up แจ้งเตือนยอดเงินไม่ตรงกันในโหมด Manual ให้แสดงแทรกหน้าจอและส่งเสียงเตือน:
  - เพิ่ม `winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)` เพื่อส่งเสียงเตือนระดับ System Alert ของ Windows
  - บังคับให้หน้าต่าง Dialog โผล่ขึ้นมาหน้าสุดของ Desktop เสมอ ไม่โดนโปรแกรมอื่น (เช่น Google Chrome หรือ Excel) บดบัง โดยใช้ `parent.attributes('-topmost', True)`, `parent.lift()`, `parent.focus_force()` ร่วมกับ Windows Win32 API (`ctypes.windll.user32.SetForegroundWindow` และ `BringWindowToTop`)
- [X] **[Persistent 1-Hour Local Session, Path Memory & Dynamic Login/Logout UI]** พัฒนาระบบบันทึก Session การ Login แบบ Local ชั่วคราว 1 ชั่วโมง จดจำพาธไฟล์สำคัญ และปรับหน้าต่างบัญชีผู้ใช้:
  - `AccountManager` ใน `functions/utils/crypto.py`: บันทึก Credential (`user_id`, `password`) รวมถึงพาธโฟลเดอร์ Accel (`accel_file_dir`) และพาธไฟล์คูปอง CP (`cp_table_location`) ลงใน Keyring
  - **Sliding Session Heartbeat**: เพิ่มตัวนับเวลา Heartbeat ทุก 5 นาทีขณะบอทเปิดทำงาน และเรียก `touch_session()` ตอนปิดโปรแกรม เพื่อเริ่มนับเวลาหมดอายุ 1 ชั่วโมงจากวินาทีที่ปิดบอทจริง ๆ ป้องกันปัญหารหัสผ่านหายระหว่างการใช้งานต่อเนื่อง
  - **Auto-Restore & Startup Non-Intrusive**: ตอนเปิดโปรแกรม หากมี Active Session อยู่ จะโหลด Credential, โหลดข้อมูล Accel File และโหลด CP Data File ขึ้นมาพร้อมทำงานทันที โดยไม่เด้งหน้าต่าง Login ขึ้นมาขวาง
  - **Dynamic UserAccount Window**:
    - หากยังไม่ Login: แสดงปุ่ม **Submit** ปุ่มเดียว (ซ่อนปุ่ม Logout)
    - หาก Login อยู่แล้ว: แสดง 2 ปุ่มคู่ **Submit** (สำหรับแก้ไขข้อมูล) และ **Logout** (สีแดง สำหรับล้าง Session และเคลียร์พาธทั้งหมด)
    - รองรับการปิดหน้าต่างด้วยปุ่ม `[X]` โดยไม่กระทบ Session ที่ใช้งานอยู่
  - เพิ่มชุดทดสอบ Unit Test ครอบคลุมใน `tests/test_crypto_session.py` (ผ่าน 100%)
- [X] **[Manual Mode Final Page Price Mismatch Pop-up Warning & Return-to-Page-1 Guard]** เพิ่มระบบ Pop-up แจ้งเตือนและป้องกันการออกบิลผิดพลาดในโหมด Manual (`not is_auto_invoice_mode`):
  - เมื่อเข้าสู่หน้าชำระเงิน (Payment Page) และกรอกยอดเงินลงใน `#ripCash00` ระบบจะตรวจสอบยอดคงเหลือ (`wrimagecard-lightGray`)
  - หากพบว่าราคาที่ทำมาจากหน้าแรก (POS Cart) ไม่ตรงกับราคาที่ลูกค้าต้องจ่ายจริง (`abs(balance_val) >= 0.01`):
    - แสดง Pop-up Dialog แจ้งรายละเอียดราคาที่ต้องออกบิล, ราคาบน POS, และส่วนต่าง พร้อมถามความประสงค์ว่าจะย้อนกลับไปหน้าแรกเพื่อแก้ไขราคาหรือไม่
    - หากผู้ใช้เลือก "Yes": บอทจะเรียก `return_to_first_page()` กดย้อนกลับไปหน้าเปิดการขายอัตโนมัติ และวนลูปรอให้ผู้ใช้ปรับแก้ราคาแล้วเข้าสู่หน้าชำระเงินใหม่อีกครั้ง
    - หากผู้ใช้เลือก "No": บอทจะคงสถานะไว้บนหน้าชำระเงิน และระบบจะบล็อกไม่ให้กดปุ่มชำระเงินเขียว (`#btnPayment`) ผ่านปุ่ม Finish Order ใน GUI จนกว่ายอดเงินจะถูกต้อง
  - เพิ่ม Unit Test ครอบคลุม 4 กรณีใน `tests/test_final_page_validator.py`

### [ver5.x.x] - 2026-10-02

- [X] **[Pricing Engine Preselected Coupon Isolation & Panel Scrape Guard]** แก้ไขปัญหาคูปองจาก SKU อื่นหรือออเดอร์ก่อนหน้า (เช่น `CP2609290081`) หลุดมารายงานเป็น "คูปองเริ่มต้นที่ติดมากับสินค้า" และติดไปในคำแนะนำ `suggested_cp`:
  - ปรับปรุง `find_suggested_cp_for_discount()` ให้ตรวจสอบและกรอง `preselected_codes` เทียบกับ `valid_detail_codes` ของ SKU ปัจจุบันเสมอ หากคูปองไม่ได้มีอยู่ในรายการของ SKU นั้นจริง จะถูกตัดทิ้งทันที
  - ปรับปรุง `get_existing_panel_coupons()` ให้ค้นหาเฉพาะจาก Element ที่เป็น Badge/Label/Tooltip ของคูปองโดยตรง แทนการค้นหาจากข้อความรวมทั้ง Panel ซึ่งอาจเผลอหยิบรหัสคูปองจากข้อความอื่น
  - เพิ่มการล้างค่า `self.last_preselected_smco_coupons = []` ใน `reconcile_and_verify()` และตอนเริ่ม `scan_matching_cp_candidates_on_smco()` เพื่อป้องกัน State คูปองตกค้างข้าม SKU หรือข้ามออเดอร์
  - เพิ่ม Unit Test `test_stale_preselected_coupon_not_in_sku_details_is_ignored` ใน `tests/test_preselected_coupon_recommendation.py` (ผ่าน 100%)
- [X] **[DualSourceCPLoader `oc_amount` & `dc_amount` Multi-Value String Preservation]** แก้ไขปัญหาบอทดึงข้อมูล `oc_amount` และ `dc_amount` ที่มีหลายค่า (เช่น `"5 4"` สำหรับสินค้าเซ็ต Multi-SKU Combo) จาก Google Sheets แล้วกลายเป็น `NaN`:
  - ปรับปรุงฟังก์ชัน `_clean_dataframe()` ใน [functions/pos/cp_data_loader.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/functions/pos/cp_data_loader.py) โดยแยกการแปลง `pd.to_numeric` เฉพาะคอลัมน์ที่เป็นตัวเลขเดี่ยว (`sale_price`, `expected_price`, `last_actual_price`)
  - สำหรับ `oc_amount` และ `dc_amount` ให้คงสถานะเป็น `str` เพื่อรักษาค่าที่คั่นด้วยช่องว่าง (เช่น `"5 4"`, `"10 20"`) ไม่ให้ถูกแปลงเป็น `NaN`
  - ทำให้ `POSPricingReconciler` และ `smco_set_overcharge_product` สามารถแยกตัวเลขแต่ละตัวไปปรับราคา Overcharge/Discount ให้กับแต่ละ SKU ในชุดสินค้าได้อย่างแม่นยำ 100%
  - เพิ่ม Unit Test `test_space_separated_oc_amount_preserved_and_matched` ใน `tests/test_cp_date_auto_correction.py` (ผ่าน 100%)
- [X] **[Accel Mode & Pricing Engine Duplicate Failed Orders Fix]** แก้ไขปัญหาชีต `Failed_Orders` บันทึกรายการล้มเหลวเบิ้ล 2 แถวติดกันสำหรับออเดอร์เดียวกัน:
  - นำการเรียก `record_failed_with_checkpoint` ซ้ำซ้อนก่อนคำสั่ง `raise err` ออกจาก `reconcile_and_verify()` ใน `functions/pos/pricing_engine.py` เพื่อให้ Exception ถูกจัดการและบันทึกเพียงจุดเดียวที่ลูปหลัก `operation_task_thread`
  - เพิ่มกลไก Debounce Guard (4 วินาที) ใน `record_failed_order()` ที่ `functions/accel_mode.py` ป้องกันการบันทึกซ้ำซ้อนในกรณีที่มีการเรียกฟังก์ชันติดต่อกันอย่างรวดเร็ว
  - เพิ่มชุดทดสอบ Unit Test `test_record_failed_order_debounces_rapid_duplicate_calls` ใน `tests/test_accel_unified_processed_logs.py`
- [X] **[CP Data Auto-Learn `last_adjustment_method` Auto Invoice Fix]** ปรับปรุงเงื่อนไขการบันทึก `last_adjustment_method` ใน `record_pos_cart_summary_to_excel()`:
  - ในโหมด Auto Invoice (`is_auto_invoice_mode == True`): หากในตะกร้า POS มีคูปองติดมาโดยอัตโนมัติจากระบบ SMCO ให้บันทึกเป็น `CP` แทนที่จะเป็น `MANUAL`
  - บันทึกเป็น `MANUAL` เฉพาะเมื่อรันในโหมด Manual ที่ผู้ใช้เป็นผู้ปรับราคาหรือเลือกคูปองด้วยตนเองบนหน้าเว็บ
- [X] **[Accel Mode Processed_Logs Auto-Hide Past Date Rows]** เพิ่มการซ่อนแถวที่อยู่นอกเหนือจากวันที่ปัจจุบัน (`datetime.datetime.now().strftime("%Y-%m-%d")`) ในชีต `Processed_Logs` อัตโนมัติ:
  - ในฟังก์ชัน `_apply_excel_formatting()` ตรวจสอบค่าคอลัมน์ `timestamp` ในชีต `Processed_Logs` และตั้งค่า `ws.row_dimensions[row].hidden = True` สำหรับแถวของวันก่อนหน้า
  - เมื่อผู้ใช้เปิดไฟล์ Excel ขึ้นมาอ่าน จะมองเห็นเฉพาะข้อมูลของวันปัจจุบันทันทีโดยไม่ต้องเสียเวลากด Filter วันที่เอง โดยที่ข้อมูลในอดีตทั้งหมดยังคงถูกบันทึกไว้อย่างครบถ้วน 100%
- [X] **[Accel Mode Failed_Orders Append-Only History Log]** ปรับปรุงชีต `Failed_Orders` ให้ทำหน้าที่เป็น Timeline Audit History อย่างแท้จริง:
  - ยกเลิกการลบแถวออกจากชีต `Failed_Orders` เมื่อออเดอร์ถูก Retry จนสำเร็จ เพื่อให้ผู้ใช้สามารถย้อนดูประวัติข้อผิดพลาดในอดีตได้ครบถ้วน 100% แม้ทุกออเดอร์จะเสร็จสิ้นแล้ว
  - ปรับการบันทึกใน `record_failed_order()` ให้เป็นแบบ Append-Only เก็บทุกครั้งที่เกิดข้อผิดพลาดโดยไม่ทับของเดิม
  - ให้ชีต `Processed_Logs` รับหน้าที่เป็น Current State ล่าสุด (อัปเดตสถานะ Failed -> Completed เพียงแถวเดียว) อย่างชัดเจน
- [X] **[Pricing Engine Scoped CP Button & Scanned State Leak Isolation]** แก้ไขปัญหา Index Mismatch ในการเปิด Modal คูปอง และล้าง State ตกค้างข้ามคำสั่งซื้อ:
  - ปรับการค้นหาปุ่มเปิดคูปอง (`btn-coupon`) ใน `scan_matching_cp_candidates_on_smco()` และ `cp_sonic_blow_process()` ให้ค้นหาแบบ Scoped ภายใน DOM Panel ของ SKU นั้นโดยตรง (`target_panel.find_elements(...)`) แทนการใช้ Global Button Array Index ซึ่งอาจหยิบปุ่มผิดตัวหากมีสินค้าบางรายการไม่มีปุ่มคูปอง
  - เพิ่มการล้างค่า `self.last_scanned_smco_coupons = []` และ `self.last_scanned_smco_coupon_details = []` ใน `reconcile_and_verify()` และ `reset_all_display()` ป้องกันข้อมูลคูปองจาก SKU ของออเดอร์ก่อนหน้าหลุดมารายงานใน Remark ของออเดอร์ถัดไป
- [X] **[Accel Mode Completed_Orders Lean Execution Audit Columns]** ปรับลดคอลัมน์ในชีต `Completed_Orders` ให้เหลือเฉพาะ Execution Checklist:
  - กำหนด 3 คอลัมน์หลัก: `['timestamp', 'orders', 'status']` บันทึก 1 แถวต่อ 1 Order อย่างกระชับ สะอาดตา และไม่ซ้ำซ้อนกับ `Processed_Logs`
  - ย้ายรายละเอียดธุรกรรมทั้งหมด (Tracking, บิล, ราคา, Serial Number, รายละเอียดส่วนลด/การปรับราคา) ไปไว้ในชีต `Processed_Logs` ซึ่งทำหน้าที่เป็น Full Transaction Ledger แทน
- [X] **[Accel Mode Processed_Logs Column Reordering & Orders Column Freeze]** ปรับลำดับคอลัมน์ในชีต `Processed_Logs` และตรึงแนว (Freeze Panes) อัตโนมัติ:
  - จัดเรียงลำดับคอลัมน์ใหม่ตามข้อกำหนด: `['timestamp', 'tracking', 'orders', 'bill_no', 'price', 'sn', 'status', 'error_category', 'remark']`
  - ตรึงแนว (Freeze Panes) ไว้ที่คอลัมน์ `orders` (เซลล์ `D2` ตรึง Header และคอลัมน์ A, B, C: `timestamp`, `tracking`, `orders`) ทุกครั้งที่มีการเปิด/อ่านไฟล์ Excel เข้าสู่ State (`_read_accel_file_to_state`) และทุกครั้งที่มีการบันทึกผลลัพธ์
  - ปรับปรุงฟังก์ชัน `_apply_excel_formatting()` ให้คำนวณตำแหน่งคอลัมน์ `orders` แบบ Dynamic และเซ็ต `freeze_panes` อย่างแม่นยำ

### [ver5.x.x] - 2026-10-01

- [X] **[Accel Mode Unified Result Sheet - `Processed_Logs` & Retry Auto-Resolve]** ปรับปรุงโครงสร้างชีตผลลัพธ์ของ Accel Mode ให้ยุบรวม `Completed_Orders` และ `Failed_Orders` เข้าด้วยกันเป็นชีตเดียว `Processed_Logs` แบบ Single Source of Truth:
  - กำหนด 9 คอลัมน์มาตรฐาน: `['timestamp', 'tracking', 'orders', 'status', 'bill_no', 'price', 'sn', 'error_category', 'remark']`
  - แก้ไขปัญหาเลขออเดอร์ซ้ำซ้อนเวลาทำ Retry:
    - เมื่อออเดอร์ไม่ผ่าน บันทึกสถานะเป็น `Failed` พร้อม `error_category` และข้อความ `remark`
    - เมื่อนำออเดอร์กลับมารันใหม่จนผ่าน (`Completed`) ระบบจะอัปเดตแถวเดิมใน `Processed_Logs` จาก `Failed` เป็น `Completed` พร้อมใส่ `bill_no`, `price`, `sn` และแสตมป์เวลาล่าสุด โดยไม่สร้างแถวซ้ำ
    - ลบเลขออเดอร์ที่สำเร็จแล้วออกจากชีต `Failed_Orders` เก่าอัตโนมัติ เพื่อไม่ให้มีรายการที่แก้ผ่านแล้วตกค้างในชีต Failed
  - รักษา Backward Compatibility 100% กับชีต `Completed_Orders` และ `Failed_Orders` เดิม รวมถึงรองรับการปรับ AutoFilter, FreezePanes และ Column Widths ครบถ้วน
- [X] **[Accel Mode Completed_Orders Column Reordering]** ย้ายคอลัมน์ `timestamp` ไปไว้คอลัมน์แรกสุด (Column A / Index 0) ในชีท `Completed_Orders` เพื่อความสะดวกในการตรวจสอบประวัติและเรียงลำดับเวลาการทำงาน:
  - ปรับลำดับคอลัมน์มาตรฐานเป็น `['timestamp', 'tracking', 'orders', 'bill_no', 'price', 'pricing_detail', 'status', 'sn']`
  - ปรับปรุงฟังก์ชัน `record_completed_order()` ใน `functions/accel_mode.py` ให้บันทึกตามโครงสร้างใหม่
  - อัปเดตและจัดโครงสร้างคอลัมน์ในไฟล์ Excel `tables/Accel_mode_uat.xlsx` รวมถึงไฟล์ชุดตัวอย่างใน `assets/tables/` ทั้งหมด
- [X] **[CP Date Auto-Correction & Timezone Normalization]** เพิ่มระบบ Auto-Correction สำหรับวันที่โปรโมชันใน `cp_data_loader.py` และ `pricing_engine.py`:
  - ดักจับกรณี `usage_start_date > usage_end_date` จาก Google Sheets / Excel ที่ติด Locale US (`MM/DD/YYYY`) แล้วทำการ Auto-Swap วันกับเดือนกลับเป็นวันที่ถูกต้อง (เช่น 10 ก.ย. สลับกลับเป็น 9 ต.ค.) ให้อัตโนมัติ
  - แปลงวันที่และเวลาในรูปแบบ ISO UTC (เช่น `"2026-09-10T16:59:59.000Z"`) ให้เป็นเวลาท้องถิ่น Bangkok (UTC+7: `23:59:59`) อัตโนมัติ ป้องกันวันที่ขยับผิดพลาด
  - เพิ่มฟังก์ชัน `swap_day_month()` และ `correct_cp_date_range()` ใน `pricing_engine.py` ครอบคลุมทั้งฝั่ง Cloud GAS และ Local Excel
- [X] **[Google Apps Script & CP Data Dual-Source Sync]** ปรับปรุงระบบซิงค์ข้อมูล CP ระหว่าง Local Excel (`cp_data.xlsx`) และ Google Apps Script Web App ให้รองรับโครงสร้าง 19 คอลัมน์อย่างสมบูรณ์:
  - เพิ่มการส่งฟิลด์คำแนะนำคูปอง (`suggested_cp`, `suggested_usage_start_date`, `suggested_usage_end_date`, `suggested_remark`)
  - อัปเดตคอลัมน์ `last_updated` ด้วยเวลาปัจจุบันเสมอทั้งกรณีเพิ่มแถวใหม่ (Insert) และแก้ไขแถวเดิม (Update)
  - ปรับปรุง `_is_exact_duplicate()` ใน `DualSourceCPLoader` ให้ตรวจสอบทุกฟิลด์เพื่อป้องกันการ skip บันทึกเมื่อมีข้อมูล suggestion ใหม่
- [X] **[Pricing Engine Two-Phase Reconciliation & Safety Verification]** ยืนยันและตรวจสอบความถูกต้องของระบบการปรับราคา (Overcharge / Discount) 2 ขั้นตอน:
  - **Phase 1 (Seller Voucher)**: หากคำสั่งซื้อมีส่วนลดจากผู้ขาย ระบบจะหักยอดส่วนลดจากราคาสินค้าเป้าหมายก่อนเข้าสู่การจับคู่คูปอง
  - **Phase 2 (Price Reconciliation)**:
    - *กรณีราคาเริ่มต้นต่ำกว่าราคาซื้อ (`diff > 0`)*: ปรับเพิ่มราคา (Overcharge) ได้ทันทีตามส่วนต่าง
    - *กรณีราคาเริ่มต้นสูงกว่าราคาซื้อ (`diff < 0`)*: บังคับค้นหาและเลือก Campaign Coupon (CP) พร้อมตรวจสอบ `oc_amount`/`dc_amount` อย่างเข้มงวด หากราคาหลังหักล้างยังไม่ตรงกับราคาเป้าหมาย ระบบจะปฏิเสธการแก้ราคาอัตโนมัติและแจ้งเตือนส่งต่อให้ทีม Production ทันทีเพื่อความถูกต้องของบัญชี

### [ver5.x.x] - 2026-09-24

- [X] **[Accel Mode Multi-SKU Modal Two-Loop Refactoring]** ปรับปรุงโครงสร้างของ `_fill_multi_sku_modal()` ใน `accel_mode.py` ให้แยกเป็น 2 Loops อิสระอย่างชัดเจน (Loop กรอก และ Loop ตรวจสอบ/Reject):
  - **Loop 1 (ลูปการกรอก Serial)**: วนลูปกรอก SN ลงในช่องว่าง (`ng-empty`) จนกระทั่งไม่มีช่องว่างเหลือ (`if not empty_inputs: break`) โดยตัดการยุ่งเกี่ยวกับ Checkbox ออกจากกระบวนการกรอก เพื่อเตรียมพร้อมเข้าสู่ขั้นตอนตรวจสอบ
  - **Loop 2 (ลูปตรวจสอบ ยืนยัน หรือ Reject/Void)**:
    - **Verify Trigger**: รอจนปุ่ม Verify (`_verifyInsertSerial`) หลุดจากสถานะ `disabled` แล้วกดคลิก
    - **ตรวจเช็ค 2 ทางเลือก**:
      - **ทางเลือกที่ 1 (ผ่านทั้งหมด)**: รอจนปุ่ม OK (`_okInsertSerial`) ปลดล็อค -> คลิกปุ่ม OK บันทึก SN ที่ผ่านลง `used_serials` และตัดจากหน่วยความจำ แล้วจบการทำงานทันที (Return True)
      - **ทางเลือกที่ 2 (พบข้อผิดพลาด / Reject)**: เมื่อมีแถวที่เป็นสีแดง (`font-color-secondary-red`):
        - ดึงค่า SN จากแถวแดงโดยตรง (`td[serialNo] -> p` หรือ `input`) เพื่อความแม่นยำ 100% ในการลบ
        - ติ๊ก Checkbox (`input[@ng-model='element.checkBox']`) เฉพาะแถวสีแดงนั้น
        - ลบ SN เสียออกจากหน่วยความจำและตัดออกจาก Excel
        - กดปุ่ม Void โดยระบุ XPath เจาะจง `//div[@class='pull-right']/button[@id='_deleteInsertSerial']` (และคลิกที่ `span`) เพื่อป้องกันการชนกับปุ่มซ้ำที่ซ่อนอยู่ใน DOM ของโมดูลอื่น
        - หน่วงเวลา 1.0 วินาที เพื่อให้ระบบเคลียร์แถวเสียและแสดงช่องว่างใหม่ แล้วหลุดจาก Loop 2 วนกลับไปเข้า **Loop 1** เพื่อกรอก SN ตัวใหม่แทนที่

### [ver5.x.x] - 2026-09-29

- [X] **[Dual-Source CP Loader & Google Apps Script Sync]** เพิ่มโมดูล `DualSourceCPLoader` (`functions/pos/cp_data_loader.py`) รองรับการอ่านและเขียนข้อมูลคูปอง/ส่วนต่างราคาแบบ Real-time ระหว่าง Cloud Google Sheets (ผ่าน Google Apps Script Web App) และ Local Excel (`cp_data.xlsx`):
  - ระบบ In-Memory TTL Cache (120s) และ Fallback ใช้งาน Local Excel อัตโนมัติเมื่อ Offline
  - Client-side & Server-side Deduplication ป้องกันการส่งข้อมูลซ้ำซ้อน ช่วยประหยัดโควตาและลดความหน่วง
  - ระบบ Auto-Learn ส่งข้อมูลการออกบิลที่สำเร็จ (`AUTO_LEARN_SUCCESS`) พร้อมประวัติ `last_used_cp`, `last_order_id`, `last_adjustment_method`, `last_actual_price` ขึ้น Google Sheets ให้ทีมงานใช้งานร่วมกันได้ทันที
  - เพิ่มระบบ Action List "Move to Bottom" เลื่อนแถวที่ไม่มี CP หรือปรับราคาไม่ได้ไปไว้ล่างสุดของตาราง Excel เพื่อให้จัดการต่อง่าย
- [X] **[Early SN Sufficiency Pre-Check]** เพิ่มฟังก์ชัน `check_sn_sufficiency()` ใน `functions/accel_mode.py` และ `autopage_MKII_ver5.x.x.py` ตรวจสอบความพร้อมของ Serial Number ล่วงหน้าก่อนเริ่มยิงข้อมูลเข้าระบบ SMCO POS:
  - ตัดข้ามออเดอร์และบันทึกลง `Failed_Orders` ทันทีหากจำนวน SN ไม่เพียงพอกับ QTY ในคำสั่งซื้อ ประหยัดเวลาและป้องกันการค้างหน้า POS
- [X] **[Accel Multi-QTY Modal Fill Loop Fix]** แก้ไขลูปการกรอก Serial Number ในหน้าต่าง Modal (`_fill_multi_sku_modal`) ให้วนกรอกครบทุกแถวจนถึง `target_qty` โดยกด `ENTER` ให้ AngularJS สร้างแถวใหม่อย่างต่อเนื่องก่อนเข้าสู่ลูปตรวจสอบสถานะความถูกต้อง (เขียว/แดง)

### [ver5.x.x] - 2026-09-16

- [X] **[Accel Mode Multi-QTY Serial Number Modal Flow & Combo Aggregation]** ปรับปรุงระบบกรอก Serial Number (SN) บน SMCO POS ใน Accel Mode ให้รองรับ SKU ที่มี QTY > 1 และสินค้าชุด Combo อย่างสมบูรณ์ แก้ไขปัญหา SN ถูกล้างทิ้งฟรีเมื่อมี SN เสีย:
  - **ปัญหาเดิม**: เมื่อ SKU ต้องการกรอก SN มากกว่า 1 ตัว บอทใช้วิธียิง SN ทีละตัวผ่านช่องค้นหาบนหัวเว็บ SMCO หากตัวแรกผ่านแต่ตัวที่สองไม่ผ่าน กลไกจัดการข้อผิดพลาดเดิมจะไปกดปุ่มถังขยะสีแดง (`btn-danger`) บนตารางตะกร้าสินค้า ซึ่งลบสินค้าทั้งแถวทิ้ง ทำให้ SN ตัวแรกที่ถูกต้องถูกระบบ SMCO ล้างทิ้งไปด้วย และเสียโควตา SN ไปฟรี
  - **ตรรกะใหม่ Multi-QTY (QTY > 1)**:
    - เปลี่ยนไปใช้ **Red Serial Button (`btn-serial` / `ng-redalert`)** เพื่อเปิด Modal จัดการ SN ของสินค้านั้น
    - กรอก SN จากคิวลงในช่องของ Modal ทีเดียวตามจำนวน QTY แล้วกดปุ่มตรวจสอบความถูกต้อง (`_testInsertSerial`)
    - ใช้ **Dynamic Waiting** วนลูปตรวจสอบสถานะปุ่มยืนยัน (`_okInsertSerial`) และแถวที่ผิดพลาด (`.font-color-secondary-red`) พร้อม Safe Buffer Delay ป้องกันปัญหา Timing ช้า-เร็วบนเว็บ SMCO
    - **การจัดการ SN เสียเฉพาะตัว**: หากมีบางแถวใน Modal ขึ้นสีแดง (Serial ไม่ถูกต้อง/ไม่มีในสต็อก) ระบบจะคลิกเลือก Checkbox และกดปุ่มลบเฉพาะตัวที่เสียผ่าน `_deleteInsertSerial` โดยที่แถวสินค้าและ SN ตัวที่ถูกต้องใน Modal ยังคงอยู่ครบถ้วน ไม่กระทบตะกร้าสินค้า
    - บันทึกตัดทอนเฉพาะ SN ตัวที่เสียออกจากข้อมูลคิว พร้อมดึง SN ตัวสำรองตัวใหม่มาเติมใส่ Modal แล้วตรวจสอบซ้ำจนครบ
  - **การจัดการกรณี SN สำรองไม่เพียงพอ (Shortage Handling)**:
    - **โหมด Manual**: ปิดการทำงานอัตโนมัติ ไม่ปิด Modal ทิ้ง และสลับสถานะเป็น `Bot Status: Your Turn (Serial Shortage)` พร้อมแจ้งเตือนใน Log เพื่อให้ผู้ใช้ตัดสินใจหรือหยิบ SN นอกระบบมาเติมเอง
    - **โหมด Auto Invoice**: ปิด Modal อย่างปลอดภัย (`_safe_close_modal`), คืนสิทธิ์ SN ที่ผ่านแล้วแต่ยังไม่ถูกบันทึกกลับเข้าคิวในหน่วยความจำ (`restore_uncommitted_serials`), สั่งบันทึกลงชีต `Failed_Orders` พร้อมระบุสาเหตุ `Serial Shortage`, ล้างตะกร้าสินค้า และกดย้อนกลับไปหน้าแรกเพื่อเริ่มออเดอร์ถัดไป
  - **รองรับ SKU แบบ Combo (สินค้าชุดที่มีเครื่องหมาย `+`)**:
    - ใน `ProductManager.auto_add_all_items`: แตก Combo SKU ออกเป็นสินค้าย่อย หากตัวใดไม่ต้องการ SN จะยิงเข้าตะกร้าสินค้าตามปกติ ส่วนสินค้าย่อยที่ต้องการ SN จะถูกส่งต่อให้ Accel Mode
    - ใน `AccelMode._aggregate_order_skus`: รวมยอด QTY สุทธิของ SKU เดียวกันที่กระจายอยู่หลายบรรทัดหรือใน Combo ชุดต่างๆ ให้เป็นก้อนเดียว ก่อนส่งเข้ากระบวนการเติม SN เพื่อให้ยอดตรงกับแถวบนตะกร้า POS ของ SMCO
  - **Uncommitted Serial Restoration Guard**:
    - เพิ่ม `restore_uncommitted_serials()` ใน `AccelMode` และผูกเข้ากับ `record_failed_with_checkpoint` เพื่อคืน Serial Number ที่บอทดึงไปทดสอบแล้วแต่เกิดเหตุการณ์ Order ล้มเหลวกลางคัน ให้กลับมาอยู่ในคิวพร้อมใช้สำหรับออเดอร์ถัดไปเสมอ ไม่สูญหาย
  - เพิ่มชุดทดสอบอัตโนมัติใน [test_accel_multi_qty_sn.py](<file:///c:/Users/ONLINE_MIS/Desktop/Trans-am%2031-01-2022/Projects/python/Python/projects/auto_page/autopageMKII/tests/test_accel_multi_qty_sn.py>) ผ่านฉลุย 100% (6/6 tests)
- [X] **[Tracking Error Handling: Manual vs Auto Inv Mode]** ปรับปรุงพฤติกรรมเมื่อไม่พบเลข Tracking หรือ Tracking ไม่ครบในขั้นตอน Phase 2 (Payment Page) ให้แยกการทำงานตามโหมดอย่างถูกต้อง:
  - **โหมด Manual (ไม่มีการเปิด `auto_inv`)**:
    - หากหา Tracking ไม่พบ ไม่สั่งย้อนกลับไปหน้าแรก (`self.return_to_first_page()` ถูกยกเลิกสำหรับโหมด Manual)
    - คงสถานะหน้าจออยู่ที่ Phase 2 (หน้าชำระเงิน) ต่อไป โดยบอทจะกรอกข้อมูลส่วนที่เหลือให้ครบถ้วน (เลข Order ใน Remark, ช่องทางการชำระเงิน, PO No., ชื่อลูกค้า, ราคาสุทธิ)
    - แจ้งเตือนใน Log เพื่อให้ผู้ใช้ทราบว่ากรอกข้อมูลอื่นเสร็จแล้ว และรอให้ผู้ใช้ตรวจสอบ/ระบุเลข Tracking เอง แล้วกดปุ่มชำระเงิน (ปุ่มเขียว) ต่อไปได้ทันที
  - **โหมด Auto Invoice (`is_auto_invoice_mode == True`)**:
    - หากหา Tracking ไม่พบ จะตัดรอบส่งเป็น `FAILED` ทันทีโดยเรียก `_handle_auto_inv_accel_abort`
    - บันทึกประวัติข้อผิดพลาดลงชีต `Failed_Orders` ในไฟล์ Excel (`.xlsx`) และตัดออเดอร์ออกจาก Sheet1
    - รายงานสถานะ `FAILED` ลง `report_manager`
    - กดย้อนกลับไปหน้าแรกและสั่งล้างตะกร้า POS (`clean_pos_cart`) ทันทีเพื่อเตรียมเริ่มรอบออเดอร์ถัดไปโดยอัตโนมัติ
  - ปรับปรุงเงื่อนไขใน [payment_handler.py](<file:///c:/Users/ONLINE_MIS/Desktop/Trans-am%2031-01-2022/Projects/python/Python/projects/auto_page/autopageMKII/functions/pos/payment_handler.py>) และ [autopage_MKII_ver5.x.x.py](<file:///c:/Users/ONLINE_MIS/Desktop/Trans-am%2031-01-2022/Projects/python/Python/projects/auto_page/autopageMKII/autopage_MKII_ver5.x.x.py>) (`record_failed_with_checkpoint`)
  - เพิ่มชุดทดสอบใน [test_shopee_tracking_mismatch_accel.py](<file:///c:/Users/ONLINE_MIS/Desktop/Trans-am%2031-01-2022/Projects/python/Python/projects/auto_page/autopageMKII/tests/test_shopee_tracking_mismatch_accel.py>) ครอบคลุมทั้งโหมด Manual และ Auto Invoice ผ่านฉลุย 100%

### [ver5.x.x] - 2026-10-10

- [X] **[Auto Add SKU Network Interception & Coupon Dates Auto-Sync]** ดักจับข้อมูลช่วงวันและคูปองจริง (`startDate`, `endDate`) จาก Network Response `/getProductMasterInfoPOSV3.htm` เมื่อยิงสินค้า (Auto Add SKU):
  - เพิ่มเมธอด `sync_product_master_coupon_dates_to_excel` ใน `functions/pos/pricing_engine.py` สกัด `startDate`, `endDate`, `couponCode`, `remark` จาก `productCouponDetail` ใน response ที่ดักจับได้ทันที
  - อัปเดต `usage_start_date`, `usage_end_date`, `suggested_usage_start_date`, `suggested_usage_end_date` ลง `self.app.cp_df`, `tables/cp_data.xlsx` และ push ขึ้น Google Sheets (GAS) ทันทีที่มีการยิง SKU
  - ปรับปรุง `accel_fill_sku` ใน `functions/accel_mode.py`: สำหรับสินค้าที่ไม่มีใน `accel_file` (สินค้าที่ไม่มี SN เช่น จอภาพ, อุปกรณ์เสริม) ระบบจะทำการแอดสินค้าลงตะกร้า POS ด้วย `AutoAddProduct.auto_add_product` อัตโนมัติ แทนการข้าม
  - ปรับปรุง `record_pos_cart_summary_to_excel`: ให้เขียนทับ `suggested_usage_start_date` และ `suggested_usage_end_date` ด้วยช่วงวันจริงจาก Network Response เสมอ เพื่อขจัดปัญหาวันที่ค้างจากการเดา Regex เดิม
  - เพิ่มชุดทดสอบอัตโนมัติใน `tests/test_coupon_date_suggestion.py` ผ่านครบ 23 ข้อ 100%

### [ver5.x.x] - 2026-09-30

- [X] **[Suggested CP DateTime, Remark & 1-to-1 Column Alignment]** ปรับปรุงระบบบันทึกคูปองแนะนำ (`suggested_cp`) ให้รองรับการเก็บเวลา (Time), Remark และจัดลำดับคอลัมน์ตรงกับคอลัมน์ใช้งานจริง:
  - เพิ่ม `parse_smart_datetime` และ `format_smart_datetime_str` รักษาข้อมูลเวลา (Time เช่น `17/09/2026 00:00:01`, `30/09/2026 23:59:59`) จาก SMCO API และข้อความคูปอง
  - ปรับปรุงตรรกะการเลือกคูปองแนะนำ (`find_suggested_cp_for_discount`):
    - หากมีหลายคูปอง ให้เลือกคูปองที่วันเริ่มใช้งานใหม่สุด (`max(start_date)`)
    - หากวันเริ่มเท่ากัน ให้เลือกคูปองที่สิ้นสุด/หมดอายุไวกว่า (`min(end_date)`)
    - ดึงข้อความ `couponDetailRemark` เก็บเข้า `suggested_remark`
  - แยกและจัดลำดับคอลัมน์ใน `cp_data.xlsx` เป็น 4 คอลัมน์ติดกัน:
    `suggested_cp` | `suggested_usage_start_date` | `suggested_usage_end_date` | `suggested_remark`
    ตรงตามลำดับคอลัมน์ใช้งานจริง (`cp_name` | `usage_start_date` | `usage_end_date` | `remark`) เพื่อให้ผู้ใช้สามารถ Copy-Paste ทั้งบล็อก 4 คอลัมน์ได้ทันทีโดยไม่ต้องจัดเรียงใหม่
  - เพิ่มชุดทดสอบอัตโนมัติใน [test_coupon_date_suggestion.py](file:///c:/Users/Satawad_Ta/Documents/GitHub/Python/projects/auto_page/autopageMKII/tests/test_coupon_date_suggestion.py) ครอบคลุมกฎการเลือกวันที่, เวลา, Remark และโครงสร้างคอลัมน์ ผ่าน 100%
- [X] **[Network Interception & Multi-SKU Combo Coupon Mathematical Aggregation]** เพิ่มระบบดักจับข้อมูลคูปองจาก Network Response และรวมมูลค่าส่วนลดข้าม Sub-SKU ของสินค้าชุด (Combo Set) ทางคณิตศาสตร์:
  - บันทึก Response จาก Network API `/smartcore/smartpos/pointofsales/posmainv3/getProductMasterInfoPOSV3.htm` เมื่อยิงสินค้าแต่ละ SKU ใน `functions/auto_add_product.py` ผ่าน `record_product_master_response`
  - เพิ่ม `get_smco_session_context` ใน `functions/pos/pricing_engine.py` สกัดข้อมูลผู้ใช้และสาขา (`emp_id`, `branch_id`, `store_id`) จาก JWT Token (`sub`) ใน Cookie/Storage อัตโนมัติ เพื่อใช้กรองคูปองเฉพาะสาขาที่ล็อกอิน (`couponBranchs`)
  - เพิ่ม `get_aggregated_combo_coupons` คำนวณผลรวมส่วนลดจริงของแต่ละ Coupon Code (`couponDetailCash + couponDetailDisc`) จากทุก Sub-SKU ในเซ็ต (เช่น `SP1-001420+SP1-001421+...`)
  - ผสานรายการคูปองที่คำนวณส่วนลดรวมแล้วเข้าสู่ `scan_matching_cp_candidates_on_smco` และ `find_suggested_cp_for_discount` ทำให้ระบบสามารถจับคู่และแนะนำ `suggested_cp` สำหรับสินค้าชุดได้แม่นยำ 100% แม้ใน Remark จะไม่ได้ระบุราคาเป้าหมายไว้
  - เพิ่มชุดทดสอบอัตโนมัติใน `tests/test_coupon_date_suggestion.py` ผ่านฉลุย 100%

### [ver5.x.x] - 2026-09-15

- [X] **[Address Dropdown Exact Match Priority]** แก้ไขปัญหาการเลือก อำเภอ/เขต/จังหวัด ใน `select_li_from_dropdown` ผิดพลาดเมื่อคำค้นหาเป็นคำย่อยของคำอื่น (เช่น ค้นหา "วัฒนา" แต่ระบบไปเลือก "ทวีวัฒนา"):
  - ปรับปรุงตรรกะใน [autopage_MKII_ver5.x.x.py](<file:///c:/Users/ONLINE_MIS/Desktop/Trans-am%2031-01-2022/Projects/python/Python/projects/auto_page/autopageMKII/autopage_MKII_ver5.x.x.py>) ให้ตรวจสอบและคลิกรายการที่เป็น Exact Match (`txt == th_val or txt == en_val`) ก่อนเสมอในรอบแรก เพื่อป้องกันปัญหา Substring Match ที่ทำให้คำค้นหาสั้นไปจับคู่โดนคำยาวที่อยู่ลำดับก่อนหน้า
  - หากไม่พบ Exact Match จะเลือกตาม Index จาก API (`matched_item_idx`) ซึ่งตรงกับลำดับรายการที่แสดงใน Select2 Dropdown ของ SMCO
  - คง Fallback ด้วย Partial Match และ `Keys.ENTER` ไว้เฉพาะกรณีที่ Index เกินขอบเขตของตัวเลือกใน DOM

### [ver5.x.x] - 2026-09-11

- [X] **[Test Mode Accel Auto-Advance on Pass]** เพิ่มระบบข้ามไปออเดอร์ถัดไปอัตโนมัติใน Test Mode เมื่อเปิดรันคู่กับ Accel Mode + Auto Invoice:
  - หาก `is_testing == True` และรันบน `is_accel_mode == True` คู่กับ `is_auto_invoice_mode == True`:
    - **กรณี Test ผ่าน (All OK)**: บันทึกข้อมูลออเดอร์ที่ทดสอบสำเร็จลงไฟล์ Accel (`deduct_accel_file_data`, `record_completed_order`), รายงานผลลง `report_manager.finish_order("SUCCESS")`, กดย้อนกลับไปหน้าแรก (`return_to_first_page`), ล้างตะกร้าสินค้า (`clean_pos_cart`), และส่งสัญญาณให้คิวของ Accel Mode ดำเนินการออเดอร์ถัดไปได้ทันทีอย่างต่อเนื่องโดยไม่ติดค้างที่หน้าจอ
    - **กรณี Test ไม่ผ่าน (Fail)**: บอทจะหยุดการทำงานทันที, ปิด Accel Mode (`is_accel_mode_activated = False`), ปรับสถานะป้ายเป็น `Bot Status: Your Turn (Test Failed)` และค้างหน้าจอไว้เพื่อให้ผู้ใช้เข้ามาตรวจสอบสาเหตุได้อย่างแม่นยำ
    - **กรณีทดสอบแบบ Manual ออเดอร์เดี่ยว (ไม่ใช่ Accel Mode)**: คงพฤติกรรมเดิมไว้ทุกประการ โดยบอทจะหยุดที่ Checkpoint ตามที่เลือกเพื่อให้ผู้ใช้ตรวจสอบและดำเนินการต่อเอง
- [X] **[Pre-selected Default CP Pairing Recommendation]** เพิ่มระบบแนะนำคูปองแบบคู่ผสม (คูปองเริ่มต้น + คูปองที่ต้องเพิ่ม) เมื่อตรวจพบคูปองที่ถูกเลือกเป็นค่าเริ่มต้น (`btn-primary`) บนหน้าต่างคูปองของ SMCO:
  - ใน `scan_matching_cp_candidates_on_smco` ตรวจสอบสถานะปุ่ม `btn-primary` เพื่อดึงรหัสคูปองที่ถูกเลือกอยู่แล้ว (รวมทั้ง Default CP และ Seller Voucher) เก็บเข้า `last_preselected_smco_coupons`
  - ใน `find_suggested_cp_for_discount` คำนวณคูปองแนะนำใหม่แล้วนำมาเชื่อมคู่กับคูปองเริ่มต้น เช่น `'CP2608280058 CP2608310072'`
  - ใน `_raise_missing_cp_guide` แจ้งเตือนแจกแจงชัดเจนว่าสินค้ามีคูปองเริ่มต้นใด และต้องเพิ่มคูปองใด พร้อมบันทึกรหัสคู่ผสมลงในคอลัมน์ `suggested_cp` ของ `cp_data.xlsx` ทันที เพื่อให้ผู้ใช้คัดลอกไปใช้ใน `cp_name` ได้โดยไม่ต้องเปิดดูหน้าเว็บเอง
  - เพิ่มชุดทดสอบอัตโนมัติ 7 ข้อใน `tests/test_preselected_coupon_recommendation.py` ผ่านฉลุย 100%
- [X] **[Dynamic Smart Wait & Flexible Regex for Coupon Suggestion]** ปรับปรุงระบบสแกนคูปองบน SMCO (`scan_matching_cp_candidates_on_smco`) และการแกะวันที่:
  - อัปเกรดการรอเปิด Modal จากเดิม 0.4 วินาที (8 * 0.05s) เป็น **Dynamic Smart Wait สูงสุด 3.0 วินาที** (30 * 0.1s) เพื่อรองรับสินค้าชุดหลาย SKU (Combo Pack) ที่ AngularJS ใช้เวลาเรนเดอร์ Modal นานกว่าปกติ แก้ปัญหารายการคูปองว่างเปล่าจนไม่เกิด `suggested_cp`
  - ปรับปรุง `extract_coupon_date_range` ให้รองรับรูปแบบวันที่หลากหลายทั้ง พ.ศ./ค.ศ., ปี 2 หลัก (`26`), ตัวคั่นขีด/ทับ/จุด (`/`, `-`, `.`) และคำเชื่อม (`-`, `to`, `ถึง`, `~`)
  - อัปเดตชุดทดสอบ `tests/test_coupon_date_suggestion.py` ครอบคลุมรูปแบบวันที่ใหม่ทั้งหมด ผ่านฉลุย 100%
- [X] **[Multi-SKU Combo Set Remark Target Price Suggestion]** เพิ่มระบบตรวจจับราคาเป้าหมายจาก Remark ของคูปองสำหรับสินค้าเซ็ต (1 รายการ มีหลาย SKU):
  - สำหรับสินค้าที่เป็นเซ็ตหลาย SKU บนหน้า POS จะถูกแยกเป็นหลายแถว ทำให้ส่วนลดรายชิ้นที่แสดงใน Popup (เช่น `321.-`) ไม่ตรงกับส่วนต่างราคารวมของทั้งชุด (เช่น `1,827.-`)
  - เพิ่มฟังก์ชัน `extract_target_price_from_text` ดึงราคาเป้าหมายจากช่อง `couponDetailRemark` และ Description ของคูปอง เช่น `'Dynamic ก.ย. Shp ราคา 9673'` -> ได้ราคาเป้าหมาย `9673.0`
  - ปรับปรุง `find_suggested_cp_for_discount` ให้รับพารามิเตอร์ `expected_price` และจับคู่คูปองจากราคาใน Remark ร่วมกับการตรวจวันที่ ทำให้ระบบสามารถแนะนำ `suggested_cp` (เช่น `CP2609090005`) ให้กับสินค้าเซ็ตได้อย่างแม่นยำ 100% แม้ส่วนลดต่อชิ้นจะไม่ตรงกับส่วนต่างราคารวม
  - เพิ่มชุดทดสอบอัตโนมัติใน `tests/test_coupon_date_suggestion.py` ผ่านฉลุย 100%

### [5.2.5] - 2026-09-09

- [X] **[Seller Voucher CP Integration & SSOT Pricing Guard]** ปรับปรุงระบบคำนวณราคาเพื่อรองรับการเปลี่ยนผ่านของ Seller Voucher ไปเป็น Campaign Coupon (CP) บน SMCO POS:
  - ปรับปรุง `OrderFinancials.recalculate()` ใน `functions/pos/pricing_engine.py` ให้อ่านค่า `โค้ดส่วนลดชำระโดยผู้ขาย` / `ส่วนลดจากร้านค้า` ทั้งในระดับแถวสินค้าและระดับออเดอร์ นำไปหักออกจากราคาคาดหวัง (`item_expected_prices`) ของ SKU เป้าหมาย เพื่อให้บอทค้นหาและเลือก CP ใน `cp_data.xlsx` ที่มีมูลค่าส่วนลดตรงกับ Seller Voucher
  - ปรับปรุง `ProductManager.verify_item_price()` และ `verify_total_price()` ใน `functions/product_manager.py` ให้ใช้ `OrderFinancials` เป็น Single Source of Truth (SSOT) ในการเปรียบเทียบราคาต่อชิ้นและยอดรวมตะกร้าสินค้าบน POS แทนการคำนวณราคาแบบเดิม
  - ป้องกันข้อผิดพลาด `KeyError: 'เลขอ้างอิง SKU'` ใน `verify_item_price()` เมื่อมีค่าจัดส่งหรือไม่มีคอลัมน์ SKU ในแถวเสริม
  - เพิ่มชุดทดสอบอัตโนมัติ `tests/test_seller_voucher_pricing.py` ครอบคลุมการคำนวณของ OrderFinancials, การจับคู่ CP ของ PricingReconciler และการตรวจราคาของ ProductManager ผ่านฉลุย 100%
- [X] **[Accel Mode Queue Skipping & Shifting Fix]** แก้ไขปัญหา Accel Mode ข้ามออเดอร์เว้นออเดอร์ (1 -> 3 -> 5) ที่เกิดจากการลบแถวออเดอร์ที่สำเร็จออกจาก Excel แล้ว Index ของแถวที่เหลือถอยร่นขึ้นมา 1 ตำแหน่งแต่ตัวนับวนลูปส่งค่า `count + 1` โดยเปลี่ยนสถาปัตยกรรมลูปเป็น **Processed Queue Tracker** ตรวจจับและหยิบออเดอร์แรกในรายการที่ยังไม่ถูกเริ่มรันในรอบนั้นเสมอ (`processed_orders`) พร้อมรองรับกรณีออเดอร์ Failed หรือถูกข้าม (ไม่ลบแถวออกจาก Sheet1 แต่ไม่วนซ้ำออเดอร์เดิม) และเพิ่มชุดทดสอบอัตโนมัติ 3 เคสใน `tests/test_accel_mode_queue.py`
- [X] **[CP Sonic Blow Multi-Item Modal Fix]** แก้ไขปัญหา `Demonic CP Bot inner Exception Error: Message: element not interactable` ใน `functions/pos/pricing_engine.py` (`cp_sonic_blow_process` และ `scan_matching_cp_candidates_on_smco`) ซึ่งทำให้บอทเลือกคูปองได้ไม่ครบทุก SKU เมื่อมีหลายรายการ:
  - เพิ่มระบบตรวจเช็คและรอให้ modal backdrop (`.modal-backdrop`, `.modal.in`) ปิดสนิทก่อนคลิกปุ่มคูปองของ SKU ถัดไป
  - เพิ่ม `scrollIntoView` เลื่อนปุ่มคูปองให้อยู่กึ่งกลางหน้าจอก่อนคลิก
  - ใช้การคลิกด้วย Selenium ปกติ (`.click()`) ร่วมกับจังหวะพักรอ (`0.35s`) ให้ AngularJS digest cycle และ DOM เรนเดอร์เสร็จสมบูรณ์ เพื่อเลี่ยงการถูกตรวจจับจากการคลิกด้วย JavaScript
- [X] **[POS Fast Cart Clear Optimization]** ปรับปรุงระบบล้างสินค้าตกค้างบนตะกร้า POS (`Cart Sanitation Guard`) ก่อนเริ่มออเดอร์ใหม่ ให้ใช้ Fast Clear โดยคลิกปุ่มเคลียร์ `//span[@id='select2-memberSearch-container']//span[@class='select2-selection__clear']` พร้อมตรวจจับและกดยืนยัน Pop-up SweetAlert2 (`OK`/`ตกลง`) อัตโนมัติ แทนการรีโหลดหน้า `posmainv3.htm` แบบเดิม ช่วยลดเวลาการทำงานได้อย่างมาก พร้อมคง Fallback รีโหลดหน้าเว็บหากไม่พบปุ่มเคลียร์
- [X] **[Final Page Payment Loop]** ปรับปรุงลูป `process_final_payment()` ใน `functions/pos/payment_handler.py` ไม่ให้ข้ามหรือหลุดการทำงานก่อนเวลา โดยสั่งกรอกข้อมูลหน้าท้าย (PO No, Customer Name, Cash, CN Remark) ให้ครบถ้วน แล้วรอในลูปจนกว่าบอทจะชำระเงินสำเร็จ (ตรวจพบหน้าต่างปิดลง) หรือผู้ใช้กดย้อนกลับไปหน้าที่ 1
- [X] **[Accel Mode Excel Integrity & Sheet Isolation]** แก้ไขปัญหาไฟล์ Accel Excel เสียหายและชีตหาย รวมถึงบัค `ValueError: ไม่พบออเดอร์ ... ในไฟล์นำเข้า` ใน `functions/accel_mode.py`:
  - เพิ่ม `_get_main_sheet_name()` ตรวจหาชีตข้อมูลหลักอัตโนมัติ (ไม่หยิบชีต `Completed_Orders` หรือ `Failed_Orders`)
  - บังคับระบุ `sheet_name` ในการอ่าน `pd.read_excel()` ให้ตรงกับชีตหลักทุกจุด
  - ปรับปรุง `_save_df_to_excel()` ให้บันทึกข้อมูลแบบแยกชีตด้วย `openpyxl` โดยไม่ลบชีตอื่นทิ้ง
  - ป้องกัน `KeyError: 'cp'` กรณีไฟล์ Excel นำเข้าไม่มีคอลัมน์ `cp`
- [X] **[Address Tokenization]** นำ `PyThaiNLP` (`word_tokenize`) และ `RapidFuzz` เข้ามาช่วยตัดคำและทำความสะอาดที่อยู่ (`clean_address`) รองรับที่อยู่ที่พิมพ์ติดกันเป็นพรืดและคำย่อการปกครองซ้ำซ้อน
- [X] **[Test / Batch Report System]** เพิ่มโมดูล `TestReportManager` (`functions/utils/report_manager.py`) บันทึกและสรุปสถานะการสร้างลูกค้า (`customer_status`) และการแก้ไขที่อยู่ (`address_status`) พร้อมระบบ Export รายงานออกมาเป็นไฟล์ Excel อัตโนมัติในโฟลเดอร์ `reports/`
- [X] **[Final Page Element Verification Guard]** เพิ่มฟังก์ชัน `verify_final_page_elements()` และระบบ Auto-recovery ใน `functions/pos/payment_handler.py` ตรวจสอบความครบถ้วนของ PO No. (`#textbox81037000102`), Customer Name (`#textbox81037000101`), ยอดเงิน Cash (`#ripCash00`), หมายเหตุ (`cnRemark`) และยอดคงเหลือ (`wrimagecard-lightGray == 0.00`) ก่อนกดปุ่มเขียว (`#btnPayment`) พร้อมชุดทดสอบอัตโนมัติ 6 ข้อใน `tests/test_final_page_validator.py`
- [X] **[Test Mode Segmented Checkpoints]** เพิ่มระบบเลือกจุดหยุดใน Test Mode (`test_mode_frame`) ด้วย `CTkOptionMenu` แบบไดนามิก (แสดงเฉพาะเมื่อกด `Ctrl+Alt+T`) รองรับ 5 ระดับจุดหยุด: [1] หลังเลือกลูกค้า [2] หลังตรวจที่อยู่ [3] หลังยิงสินค้า/คูปองหน้าแรก [4] หลังกรอกหน้าท้าย (ก่อนกดปุ่มเขียว) [5] ไม่หยุด-รันจนจบวงรอบ พร้อมระบบส่งมอบหน้าจอ (`Your Turn`) และชุดทดสอบใน `tests/test_test_mode_checkpoints.py`
- [X] **[Add Customer Test Shortcut & Validation System]** เพิ่มโมดูล `CustomerModalTestHandler` (`functions/pos/customer_test_handler.py`) พร้อมปุ่มลัด `[🧪 Test Add Customer]` บน UI (และคีย์ลัด `Ctrl+Alt+C`) สำหรับทดสอบเปิดหน้าต่างสร้างลูกค้า กรอก `memNameTh`/`memNameEn` (ค่าเดียวกันเสมอ), `identity` (Tax ID), `addressCustomer` และตรวจสอบ dropdowns 4 ตัว (Province, District, SubDistrict, Zip) ทั้งภาษาไทย/อังกฤษ และตรวจสอบสถานะปุ่ม `//button[@ng-click='saveNewMember()']` ว่า attribute `disabled="disabled"` หลุดหายไปเมื่อกรอกครบ พร้อมระบบบันทึกรายงานผลการทดสอบลงไฟล์ Excel ในโฟลเดอร์ `reports/` อัตโนมัติ และชุดทดสอบครบ 5 เคสใน `tests/test_customer_modal_test_handler.py`

### [5.2.4LITE / 5.2.5] - 2026-08-27

#### Fixed & Improved

- [X] **[Print]** ปรับ `print_pdf_silence_sumatra` ในทั้ง `ver5.x.x.py` และ `ver5.2.4LITE.py` เป็นแบบ Non-blocking (`subprocess.Popen`) แก้ปัญหา Tkinter Not Responding
- [X] **[Payment]** ปรับปรุง XPath ปุ่มชำระเงินเป็น `//div[contains(@class,'wrimagecard')]//a[@id='btnPayment']` พร้อมระบบ Retry และแก้ปัญหา Popup LockAcquisitionException
- [X] **[Pricing Engine]** แยกโมดูล `functions/pos/pricing_engine.py` (OrderFinancials & POSPricingReconciler) เป็น Single Source of Truth ป้องกันคำนวณซ้ำซ้อน
- [X] **[Safety Net]** เพิ่มระบบ Auto-retry กดปุ่มชำระเงินซ้ำอัตโนมัติทุก 3 วินาที หากค้างหน้าชำระเงินโดยไม่มี Popup
- [X] **[Tracking]** เพิ่มระบบตรวจเช็ค Package Card และ Tracking Number ก่อนออกบิล หากไม่ครบจะยกเลิกออเดอร์เข้า Failed_Orders ทันที
- [X] **[CP/DC Multi-Candidate]** เพิ่มระบบ Ambiguity Guard หากพบคูปองตรงกันมากกว่า 1 ตัวบน SMCO จะหยุดปรับราคาและแจ้งเตือน User เพื่อความปลอดภัย
- [X] **[Logging / Error Handling]** ปรับปรุง order_search ให้บันทึกเลข Order, ประเภท Exception, ข้อความ Error และ Stacktrace ลง Log พร้อมบันทึกลง Failed_Orders ของ Accel file
- [X] **[Log Rotation & Retention]** ตั้งค่า Loguru จำกัดขนาดไฟล์ Log ที่ 10 MB พร้อมหมุนไฟล์อัตโนมัติ (Rotation), บีบอัดไฟล์เก่าเป็น .zip (Compression), เก็บย้อนหลัง 15 วัน (Retention) และบังคับ UTF-8
- [X] **[Completed_Orders Multi-Tracking]** ปรับ `record_completed_order` ใน Accel mode ให้แยกบันทึก 1 Row ต่อ 1 Tracking Number พร้อมจับคู่ SKU และ SN ของแต่ละ Tracking อัตโนมัติ
- [X] **[Cancelled Order SN Guard]** ป้องกันค่า SN ตกค้างใน Order ที่ถูกยกเลิก/ข้าม โดยล้าง `used_serials` ก่อนเริ่มรอบค้นหาและหลังบันทึกทุกครั้ง พร้อมบล็อกไม่ให้เขียน SN ลงแถวที่ถูกยกเลิก
- [X] **[In-Memory SN Recovery]** แก้ปัญหา SN หายจาก Memory เมื่อรอบก่อนหน้า Abort/Fail กลางคัน (เช่น ติดปรับราคา) โดยสั่งซิงค์ `obj_data_from_accel_file` จาก `accel_df_state` ก่อนเริ่มยิง SN ทุกครั้ง ทำให้สามารถยิง SN ได้ตามปกติเมื่อวนกลับมารันใหม่
- [X] **[Order State Leak Guard]** ป้องกันการนำข้อมูลสินค้าของออเดอร์ก่อนหน้ามาออกบิลซ้ำ เมื่อค้นหาออเดอร์ใหม่ไม่พบในไฟล์นำเข้า โดยรีเซ็ต `self.items = []`, สั่งตัดการทำงานของ `operation_thread` ทันที, บันทึกลง `Failed_Orders`, และเพิ่ม Safeguard บล็อกไม่ให้เริ่มรันถ้า `self.items` ว่างเปล่า
- [X] **[Real-time Self-Verification & Cart Sanitation]** เพิ่มระบบตรวจสอบตัวเองแบบ Real-Time (1) เช็คความถูกต้องกับตาราง Marketplace โดยตรงใน `verify_item_qty` (2) ตรวจสอบแบบสองทิศทาง (Bidirectional Check) ดักจับสินค้าแปลกปลอม/สินค้าตกค้างบน POS ทันที (3) ระบบ Cart Sanitation รีโหลดหน้า POS อัตโนมัติหากพบสินค้าตกค้างบนตะกร้าก่อนเริ่มออเดอร์ใหม่ พร้อมชุด Automated Test 7 ข้อ
- [X] **[Sonic Blow CP Selector Optimization]** ปรับปรุง Locator ปุ่ม Coupon บน SMCO POS เป็น XPath `//button[contains(@class,'btn-coupon') and contains(@ng-click,'display')]` ทั้งใน `sonic_blow_cp_selector` และ `scan_matching_cp_candidates_on_smco` แก้ปัญหาตรวจพบ element แฝง (8 elements แทนที่จะเป็น 4) ซึ่งทำให้เกิดข้อผิดพลาด `element not interactable` สลับเว้นตัว พร้อมทั้งตัด Delays ที่หน่วงเวลาออก คืนความเร็วในการทำงานสูงสุดโดยยังคง Retry และ Backdrop Clearance Logic ไว้อย่างสมบูรณ์

### [5.2.0LITE - 5.2.3LITE]

#### Added & Fixed

- [X] **[CP Data Sync]** เพิ่มระบบ `scan_and_sync_missing_cp_data()` ซิงค์ราคาที่ต้องออกบิลได้ทันทีที่อัปเดตไฟล์ `cp_data.xlsx`
- [X] **[Accel Mode]** ย้าย Order ที่สำเร็จเข้าชีต `Completed_Orders` และตัด Serial ที่ใช้แล้วออกจากไฟล์ Excel ทันที
- [X] **[SN Modal Support]** รองรับการกรอก Serial Number ผ่าน Modal กรณีปุ่ม Checkbox ปกติไม่แสดง
- [X] **[Hotkeys]** เพิ่มคีย์ลัด `Ctrl + Alt + T` สำหรับเปิด Test Mode

### [5.0.0LITE - 5.1.5LITE]

#### Added & Fixed

- [X] **[CustomTkinter]** ย้าย UI มาใช้ `customtkinter` เพื่อให้รองรับ Responsive Scaling ตามความละเอียดหน้าจอ
- [X] **[Address Corrector]** ปรับปรุงการตรวจสอบ Address รองรับภาษาไทย-อังกฤษ และตัดอักขระพิเศษ (เช่น `\u200B`, `\u00A0`, `·`)
- [X] **[Tax Name Formatter]** จัดมาตรฐานชื่อนิติบุคคล แปลงคำย่อ (บมจ., หจก., สนญ.) ให้อยู่ในฟอร์แมตที่ถูกต้อง
- [X] **[Auto Inv Mode]** เพิ่มโหมดกรอกสินค้าและคำนวณส่วนต่างราคาอัตโนมัติ

### [4.0.0 - 4.2.2]

#### Added & Fixed

- [X] **[SMCO v8.0]** ปรับปรุง Locator XPath ให้รองรับระบบ Smart Core เวอร์ชันใหม่
- [X] **[Finish Button]** เพิ่มปุ่ม Finish (ปุ่มซิ่ง) สำหรับปิดจ็อบออเดอร์อย่างรวดเร็ว
- [X] **[Pricing Logic]** เพิ่มฟังก์ชัน Overcharge (OC) และ Discount (DC)

### [3.0.0 - 3.2.2]

#### Added & Fixed

- [X] **[SumatraPDF]** เริ่มใช้งาน SumatraPDF สำหรับ Silent Printing
- [X] **[Stop Button]** เพิ่มปุ่มหยุดการทำงาน (Stop Button) รองรับการขัดจังหวะในลูป
- [X] **[Serial State]** ปรับปรุง State การตัด Serial Number ป้องกันการดึงเลขเดิมซ้ำ
