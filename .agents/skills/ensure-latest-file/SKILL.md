---
description: "Selects only wildcard-version files (5.x.x, 6.x.x...n.x.x) and related function/util/helper files as editable. Files with full versions (5_1_5, 5_1_5LITE, 5.1.0, 5.2.5) are treated as frozen/deployed read-only."
---

# Ensure Latest File Version (Global Scope)

เมื่อได้รับคำสั่งให้แก้ไข อ่าน หรือประมวลผลไฟล์ ให้ปฏิบัติตามลำดับขั้นตอนดังต่อไปนี้เสมอ:

### 1. การค้นหาและรวบรวมไฟล์ (Discovery)
- **สแกนแบบครอบคลุมทั้ง Workspace (Recursive Search)**: ค้นหาไฟล์จากทุกโฟลเดอร์และโฟลเดอร์ย่อย ไม่จำกัดเฉพาะ Directory ราก (Root)
- รวบรวมไฟล์ที่มีชื่อฐาน (Base Name) เดียวกัน แต่มีความแตกต่างในด้าน:
  - **เลขเวอร์ชัน**: เช่น `autopage_MKII_ver5_x_x.py`, `autopage_MKII_ver5_1_5LITE.py`
  - **แท็กสถานะ**: เช่น `_current`, `_latest`, `_final`, `_backup`
  - **วันที่/เวลา**: เช่น `data_20260721.json`

---

### 2. การจำแนกไฟล์: งานเก่า (Frozen) vs งานปัจจุบัน (Active)

**A. งานเก่า - ห้ามแก้ไข (Frozen / Deployed - Read-Only):**
- ไฟล์ที่มีเลขเวอร์ชันครบทั้ง 3 หลัก `Major.Minor.Patch` ถือว่า deploy ไปแล้ว ห้ามแตะต้องโดยเด็ดขาด
- รูปแบบที่เข้าข่าย เช่น:
  - `5_1_5`, `5_1_5LITE`, `5_2_5`, `6_0_1`
  - `5.1.0`, `5.2.5`, `5.1.5`, `v5.1.5`
  - รวมถึงที่มี suffix ต่อท้ายเลขครบ เช่น `LITE`, `PRO`, `FIX`, `FINAL` (เช่น `ver5_1_5LITE.py` = Frozen เพราะเลขครบ 5.1.5 แล้ว)
- Regex ตรวจจับ: `\d+[_.\-]\d+[_.\-]\d+` (ถ้าตรง = Frozen ทันที ไม่สน suffix)
- อนุญาตให้ **อ่าน** เพื่ออ้างอิง/เปรียบเทียบได้ แต่ **ห้ามแก้ไข, ห้าม overwrite, ห้าม refactor**

**B. งานปัจจุบัน - แก้ไขได้ (Active - Editable):**
1. ไฟล์ wildcard ที่ระบุ Major แล้วใช้ `x` / `X` / `*` แทน Minor/Patch เช่น:
   - `autopage_MKII_ver5_x_x.py`, `autopage_MKII_ver6_x_x.py`
   - `v5.x.x`, `v6.X`, `n.x.x`
2. ไฟล์ `function / util / helper` ที่เกี่ยวข้องกับไฟล์ wildcard เท่านั้น เช่น:
   - ชื่อมีคำว่า `util`, `utils`, `helper`, `helpers`, `function`, `functions`, `common`, `shared`, `lib`, `tools`, `config`
   - หรือไฟล์ที่ถูก import โดยไฟล์ wildcard โดยตรง
   - ไฟล์กลุ่มนี้ไม่มีเลขเวอร์ชันกำกับ หรือกำกับแบบ wildcard เท่านั้น ถ้ามีเลขครบ 3 หลักให้ถือเป็น Frozen ตามข้อ A.

---

### 3. เกณฑ์การตัดสินใจ (Decision Tree - Exclusive Selection)

1. **Wildcard Major Version [แก้ไขได้ - ความสำคัญสูงสุด]**
   - หากพบไฟล์ wildcard (`5_x_x`, `5.x.x`, `6_x_x`, `6.x.x` ... `n.x.x`) ให้เลือกเฉพาะไฟล์ Major สูงสุดเพียงไฟล์เดียว (เช่น `6_x_x` > `5_x_x`)
   - **ข้อห้าม:** ห้ามแก้ไขไฟล์เลขครบ (Frozen) ควบคู่ไปด้วยโดยเด็ดขาด แม้ผู้ใช้จะสั่งว่า "แก้ตัวล่าสุด" ก็ให้ตีความว่าหมายถึง wildcard ตัวล่าสุดเท่านั้น

2. **ไฟล์ function / util / helper ที่เกี่ยวข้อง [แก้ไขได้แบบจำกัด]**
   - แก้ไขได้เฉพาะไฟล์ที่ถูกเรียกใช้โดยไฟล์ wildcard ที่เลือกในข้อ 1
   - ห้ามลามไปแก้ util/helper ของงานเก่า (Frozen)

3. **ห้าม fallback ไปไฟล์เลขครบ**
   - กรณีไม่พบไฟล์ wildcard: **ห้ามเลือกไฟล์เลขครบ (เช่น `5.2.5` > `5.1.0`) มาแก้ไขแทน**
   - ให้หยุด ถามผู้ใช้ และเสนอสร้างไฟล์ wildcard ใหม่ (เช่น `ver6_x_x`) หรือให้ผู้ใช้สั่งเจาะจงเป็นรายไฟล์ด้วย Path เต็มเท่านั้น

4. **Status Tags / Timestamp ใช้เฉพาะกลุ่ม Active**
   - `current`, `latest`, `final` หรือ Modified Date ใช้เปรียบเทียบเฉพาะในกลุ่มไฟล์ Active ด้วยกัน ห้ามใช้เป็นเหตุผลดึงไฟล์ Frozen กลับมาแก้ไข

---

### 4. ข้อปฏิบัติในการทำงาน (Execution Rules)

- **แจ้ง Path ก่อนเริ่มเสมอ**: ระบุ Path เต็มของไฟล์ Active ที่เลือก + ระบุชัดว่าไฟล์ Frozen ใดถูกข้ามไป (ไม่แก้ไข)
- **Frozen = Read-Only**: ไฟล์เลขครบทุกไฟล์ (`5_1_5`, `5_1_5LITE`, `5.1.0`, `5.2.5` ฯลฯ) + โฟลเดอร์ `backup`, `old`, `archive` + แท็ก `_backup` ห้ามแตะต้อง เว้นแต่ผู้ใช้ระบุ Path เต็มเจาะจงไฟล์นั้นเท่านั้น
- **การสร้างไฟล์ใหม่**: ให้สืบทอดชื่อ/โฟลเดอร์จากไฟล์ wildcard Active (เช่น สร้าง `ver6_x_x` ต่อจาก `ver5_x_x`) ห้ามสร้างเป็นเลขครบ (`ver5_2_6`) เพราะจะถูกตีความเป็นงานเก่าทันที