# 📋 AutoPage MKII - Project Changelog & Dev Notes

> **คู่มือการบันทึก**:
> - 📌 **ปัญหาที่เจอใหม่ / ฟีเจอร์ที่ต้องทำ**: เพิ่มในส่วน [1. งานที่ต้องทำและปัญหาที่รอแก้](#-1-งานที่ต้องทำและปัญหาที่รอแก้-active-backlog--issues)
> - 💡 **เกร็ดความรู้ / ข้อจำกัดระบบ**: บันทึกในส่วน [2. ข้อควรระวังและ Reference ประจำระบบ](#-2-ข้อควรระวังและ-reference-ประจำระบบ-developer-notes)
> - ✅ **เมื่อแก้เสร็จแล้ว**: ติ๊ก `[x]` และย้ายประวัติลงในส่วน [3. ประวัติการแก้ไขแต่ละเวอร์ชัน](#-3-ประวัติการแก้ไขแต่ละเวอร์ชัน-changelog)

---

## 📌 1. งานที่ต้องทำและปัญหาที่รอแก้ (Active Backlog & Issues)

### 🐛 บัค & การปรับปรุงที่กำลังติดตาม (In Progress / Issues)
- [ ] **[Shopee]** เพิ่มตรรกะแยกเงื่อนไขระหว่าง Shopee ปกติ กับ Shopee Mobile ในหน้าท้าย (เลือกว่าจะจ่ายช่องทางไหนแยกกัน)
- [ ] **[UI / Selenium]** Last pop-up มีตัวรอ event ที่เป็น `driver.wait` ทำให้รอนาน ให้เปลี่ยนเป็น `while loop` ดัก element เพื่อให้จบเร็วกว่า
- [ ] **[Address / SMCO]** ตรวจสอบการเลือก อำเภอ/เขต จาก enum บน SMCO คำภาษาไทยบางคำไม่ตรงกับระบบ อาจนำ `PyThaiNLP` (Tokenize) มาใช้คู่กับ `FuzzyWuzzy`
- [ ] **[AccelMode / SN]** ปรับปรุง `deduct_accel_file_data` ตรวจสอบความถูกต้องของ SN หลังกรอก และตรวจสอบ SN เมื่อมีหลาย SKU ที่ไม่มีใน Transfer
- [x] **[Logging]** ทำ Log Rotation ให้กับไฟล์ Log เพื่อไม่ให้ขนาดไฟล์ใหญ่เกินไป และสามารถเก็บย้อนหลังแยกรายวันได้
- [ ] **[Performance]** ปรับตัวดึง Tracking ให้ Dynamic ขึ้น เช่น ตอนเริ่มค้นหาออเดอร์ถ้ามี Tracking อยู่แล้ว ให้ดึงใส่ Stage ไว้ล่วงหน้าทันที

### 🚀 ฟีเจอร์ในอนาคต (Planned Features)
- [ ] **[Auto CP SAGA]** ระบบตัดสินใจเลือกคูปองอัตโนมัติ (เปรียบเทียบราคา -> ดูช่วงเวลาโปรโมชั่น -> เลือกรุ่นที่ตรงที่สุดตาม Store)
- [ ] **[Auto Export Data]** ระบบดึง Exported Data จาก Marketplace อัตโนมัติด้วย Automation Workflow
- [ ] **[Price Memorizer]** ระบบจดจำ Pattern การตัดสินใจปรับราคา/คูปองของแต่ละ SKU เพื่อนำมาใช้อัตโนมัติในครั้งถัดไป

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
4. **การทดสอบความปลอดภัย (Regression Testing)**:
   - รัน `pytest tests/test_order_leak_guard.py` ทุกครั้งหลังมีการ Refactor โค้ดที่เกี่ยวข้องกับ Order Search หรือ State

---

## 📦 3. ประวัติการแก้ไขแต่ละเวอร์ชัน (Changelog)

### [5.2.5 / ver5.x.x] - 2026-09-01
#### Added & Improved
- [x] **[Address Tokenization]** นำ `PyThaiNLP` (`word_tokenize`) และ `RapidFuzz` เข้ามาช่วยตัดคำและทำความสะอาดที่อยู่ (`clean_address`) รองรับที่อยู่ที่พิมพ์ติดกันเป็นพรืดและคำย่อการปกครองซ้ำซ้อน
- [x] **[Test / Batch Report System]** เพิ่มโมดูล `TestReportManager` (`functions/utils/report_manager.py`) บันทึกและสรุปสถานะการสร้างลูกค้า (`customer_status`) และการแก้ไขที่อยู่ (`address_status`) พร้อมระบบ Export รายงานออกมาเป็นไฟล์ Excel อัตโนมัติในโฟลเดอร์ `reports/`
- [x] **[Final Page Element Verification Guard]** เพิ่มฟังก์ชัน `verify_final_page_elements()` และระบบ Auto-recovery ใน `functions/pos/payment_handler.py` ตรวจสอบความครบถ้วนของ PO No. (`#textbox81037000102`), Customer Name (`#textbox81037000101`), ยอดเงิน Cash (`#ripCash00`), หมายเหตุ (`cnRemark`) และยอดคงเหลือ (`wrimagecard-lightGray == 0.00`) ก่อนกดปุ่มเขียว (`#btnPayment`) พร้อมชุดทดสอบอัตโนมัติ 6 ข้อใน `tests/test_final_page_validator.py`
- [x] **[Test Mode Segmented Checkpoints]** เพิ่มระบบเลือกจุดหยุดใน Test Mode (`test_mode_frame`) ด้วย `CTkOptionMenu` แบบไดนามิก (แสดงเฉพาะเมื่อกด `Ctrl+Alt+T`) รองรับ 5 ระดับจุดหยุด: [1] หลังเลือกลูกค้า [2] หลังตรวจที่อยู่ [3] หลังยิงสินค้า/คูปองหน้าแรก [4] หลังกรอกหน้าท้าย (ก่อนกดปุ่มเขียว) [5] ไม่หยุด-รันจนจบวงรอบ พร้อมระบบส่งมอบหน้าจอ (`Your Turn`) และชุดทดสอบใน `tests/test_test_mode_checkpoints.py`

### [5.2.4LITE / 5.2.5] - 2026-08-27
#### Fixed & Improved
- [x] **[Print]** ปรับ `print_pdf_silence_sumatra` ในทั้ง `ver5.x.x.py` และ `ver5.2.4LITE.py` เป็นแบบ Non-blocking (`subprocess.Popen`) แก้ปัญหา Tkinter Not Responding
- [x] **[Payment]** ปรับปรุง XPath ปุ่มชำระเงินเป็น `//div[contains(@class,'wrimagecard')]//a[@id='btnPayment']` พร้อมระบบ Retry และแก้ปัญหา Popup LockAcquisitionException
- [x] **[Pricing Engine]** แยกโมดูล `functions/pos/pricing_engine.py` (OrderFinancials & POSPricingReconciler) เป็น Single Source of Truth ป้องกันคำนวณซ้ำซ้อน
- [x] **[Safety Net]** เพิ่มระบบ Auto-retry กดปุ่มชำระเงินซ้ำอัตโนมัติทุก 3 วินาที หากค้างหน้าชำระเงินโดยไม่มี Popup
- [x] **[Tracking]** เพิ่มระบบตรวจเช็ค Package Card และ Tracking Number ก่อนออกบิล หากไม่ครบจะยกเลิกออเดอร์เข้า Failed_Orders ทันที
- [x] **[CP/DC Multi-Candidate]** เพิ่มระบบ Ambiguity Guard หากพบคูปองตรงกันมากกว่า 1 ตัวบน SMCO จะหยุดปรับราคาและแจ้งเตือน User เพื่อความปลอดภัย
- [x] **[Logging / Error Handling]** ปรับปรุง order_search ให้บันทึกเลข Order, ประเภท Exception, ข้อความ Error และ Stacktrace ลง Log พร้อมบันทึกลง Failed_Orders ของ Accel file
- [x] **[Log Rotation & Retention]** ตั้งค่า Loguru จำกัดขนาดไฟล์ Log ที่ 10 MB พร้อมหมุนไฟล์อัตโนมัติ (Rotation), บีบอัดไฟล์เก่าเป็น .zip (Compression), เก็บย้อนหลัง 15 วัน (Retention) และบังคับ UTF-8
- [x] **[Completed_Orders Multi-Tracking]** ปรับ `record_completed_order` ใน Accel mode ให้แยกบันทึก 1 Row ต่อ 1 Tracking Number พร้อมจับคู่ SKU และ SN ของแต่ละ Tracking อัตโนมัติ
- [x] **[Cancelled Order SN Guard]** ป้องกันค่า SN ตกค้างใน Order ที่ถูกยกเลิก/ข้าม โดยล้าง `used_serials` ก่อนเริ่มรอบค้นหาและหลังบันทึกทุกครั้ง พร้อมบล็อกไม่ให้เขียน SN ลงแถวที่ถูกยกเลิก
- [x] **[In-Memory SN Recovery]** แก้ปัญหา SN หายจาก Memory เมื่อรอบก่อนหน้า Abort/Fail กลางคัน (เช่น ติดปรับราคา) โดยสั่งซิงค์ `obj_data_from_accel_file` จาก `accel_df_state` ก่อนเริ่มยิง SN ทุกครั้ง ทำให้สามารถยิง SN ได้ตามปกติเมื่อวนกลับมารันใหม่
- [x] **[Order State Leak Guard]** ป้องกันการนำข้อมูลสินค้าของออเดอร์ก่อนหน้ามาออกบิลซ้ำ เมื่อค้นหาออเดอร์ใหม่ไม่พบในไฟล์นำเข้า โดยรีเซ็ต `self.items = []`, สั่งตัดการทำงานของ `operation_thread` ทันที, บันทึกลง `Failed_Orders`, และเพิ่ม Safeguard บล็อกไม่ให้เริ่มรันถ้า `self.items` ว่างเปล่า
- [x] **[Real-time Self-Verification & Cart Sanitation]** เพิ่มระบบตรวจสอบตัวเองแบบ Real-Time (1) เช็คความถูกต้องกับตาราง Marketplace โดยตรงใน `verify_item_qty` (2) ตรวจสอบแบบสองทิศทาง (Bidirectional Check) ดักจับสินค้าแปลกปลอม/สินค้าตกค้างบน POS ทันที (3) ระบบ Cart Sanitation รีโหลดหน้า POS อัตโนมัติหากพบสินค้าตกค้างบนตะกร้าก่อนเริ่มออเดอร์ใหม่ พร้อมชุด Automated Test 7 ข้อ

### [5.2.0LITE - 5.2.3LITE]
#### Added & Fixed
- [x] **[CP Data Sync]** เพิ่มระบบ `scan_and_sync_missing_cp_data()` ซิงค์ราคาที่ต้องออกบิลได้ทันทีที่อัปเดตไฟล์ `cp_data.xlsx`
- [x] **[Accel Mode]** ย้าย Order ที่สำเร็จเข้าชีต `Completed_Orders` และตัด Serial ที่ใช้แล้วออกจากไฟล์ Excel ทันที
- [x] **[SN Modal Support]** รองรับการกรอก Serial Number ผ่าน Modal กรณีปุ่ม Checkbox ปกติไม่แสดง
- [x] **[Hotkeys]** เพิ่มคีย์ลัด `Ctrl + Alt + T` สำหรับเปิด Test Mode

### [5.0.0LITE - 5.1.5LITE]
#### Added & Fixed
- [x] **[CustomTkinter]** ย้าย UI มาใช้ `customtkinter` เพื่อให้รองรับ Responsive Scaling ตามความละเอียดหน้าจอ
- [x] **[Address Corrector]** ปรับปรุงการตรวจสอบ Address รองรับภาษาไทย-อังกฤษ และตัดอักขระพิเศษ (เช่น `\u200B`, `\u00A0`, `·`)
- [x] **[Tax Name Formatter]** จัดมาตรฐานชื่อนิติบุคคล แปลงคำย่อ (บมจ., หจก., สนญ.) ให้อยู่ในฟอร์แมตที่ถูกต้อง
- [x] **[Auto Inv Mode]** เพิ่มโหมดกรอกสินค้าและคำนวณส่วนต่างราคาอัตโนมัติ

### [4.0.0 - 4.2.2]
#### Added & Fixed
- [x] **[SMCO v8.0]** ปรับปรุง Locator XPath ให้รองรับระบบ Smart Core เวอร์ชันใหม่
- [x] **[Finish Button]** เพิ่มปุ่ม Finish (ปุ่มซิ่ง) สำหรับปิดจ็อบออเดอร์อย่างรวดเร็ว
- [x] **[Pricing Logic]** เพิ่มฟังก์ชัน Overcharge (OC) และ Discount (DC)

### [3.0.0 - 3.2.2]
#### Added & Fixed
- [x] **[SumatraPDF]** เริ่มใช้งาน SumatraPDF สำหรับ Silent Printing
- [x] **[Stop Button]** เพิ่มปุ่มหยุดการทำงาน (Stop Button) รองรับการขัดจังหวะในลูป
- [x] **[Serial State]** ปรับปรุง State การตัด Serial Number ป้องกันการดึงเลขเดิมซ้ำ