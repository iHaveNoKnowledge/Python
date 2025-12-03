# แก้ปัญหา Thread ดับเมื่อกด auto_add_product

## ปัญหาที่พบ

เมื่อกดปุ่ม `auto_add_product` บน widget ที่แสดงผลบน UI จะทำให้ thread หลัก (`longer_thread_cycle` และ `shorter_thread_cycle`) ดับลง และ GUI แสดงสถานะเป็น "จบการทำงาน" ทันที

## สาเหตุ

1. **การเรียกใช้โดยตรงใน UI Thread**: ปุ่ม `auto_add_product` เรียก function `bot.AutoAddProduct.auto_add_product()` โดยตรงจาก UI thread (บรรทัด 500)

2. **การ Block ด้วย driver_lock**: Function `auto_add_product()` ใช้ `with self.driver_lock:` ซึ่งจะ lock และ block thread จนกว่าจะทำงานเสร็จ

3. **ไม่มี Thread แยก**: เนื่องจากไม่มี thread แยกสำหรับ `auto_add_product` จึงทำให้ UI freeze และรบกวนการทำงานของ threading cycle หลัก

4. **check_threads() ตรวจพบว่า threads ดับ**: เมื่อ `check_threads()` ตรวจสอบและพบว่า `longer_thread_cycle` และ `shorter_thread_cycle` ทำงานเสร็จแล้ว จะอัพเดท GUI เป็น "จบการทำงาน" ทันที

## วิธีแก้ไข

สร้าง **wrapper method** ชื่อ `auto_add_product_threaded()` ที่จะรัน `auto_add_product()` ใน **thread แยก** เพื่อไม่ให้รบกวน threading cycle หลัก

### การเปลี่ยนแปลง

#### 1. เพิ่ม Method ใหม่ (บรรทัด 2218-2237)

```python
def auto_add_product_threaded(self, skus, qty, **kwargs):
    """
    Wrapper method สำหรับเรียก auto_add_product ใน thread แยก
    เพื่อไม่ให้รบกวน threading cycle หลัก (longer_thread_cycle และ shorter_thread_cycle)
    
    Parameters:
        skus: list of SKU codes
        qty: quantity
        **kwargs: additional arguments to pass to auto_add_product
    """
    def run_auto_add():
        try:
            self.bot.AutoAddProduct.auto_add_product(skus, qty, **kwargs)
        except Exception as e:
            print(f"Error in auto_add_product_threaded: {e}")
    
    # สร้าง daemon thread เพื่อไม่ให้รบกวน main threads
    auto_add_thread = threading.Thread(target=run_auto_add, daemon=True, name="AutoAddProductThread")
    auto_add_thread.start()
    print(f"Started auto_add_product in separate thread: {auto_add_thread.name}")
```

**คุณสมบัติสำคัญ:**
- ใช้ `daemon=True` เพื่อให้ thread นี้ไม่ขัดขวางการปิดโปรแกรม
- มี error handling ด้วย try-except
- มีชื่อ thread ที่ชัดเจน (`AutoAddProductThread`) เพื่อง่ายต่อการ debug

#### 2. แก้ไข Button Command (บรรทัด 500)

**เดิม:**
```python
command=lambda idx=item_idx: self.bot.AutoAddProduct.auto_add_product(
    self.correct_sku_pattern(ordered_items[idx]['เลขอ้างอิง SKU (SKU Reference No.)']),
    ordered_items[idx]['จำนวน'],
    get_tabs=self.bot.get_tabs
)
```

**ใหม่:**
```python
command=lambda idx=item_idx: self.auto_add_product_threaded(
    self.correct_sku_pattern(ordered_items[idx]['เลขอ้างอิง SKU (SKU Reference No.)']),
    ordered_items[idx]['จำนวน'],
    get_tabs=self.bot.get_tabs
)
```

## ผลลัพธ์

✅ **Thread หลักไม่ดับอีกต่อไป**: `longer_thread_cycle` และ `shorter_thread_cycle` จะทำงานต่อไปได้ตามปกติ

✅ **UI ไม่ Freeze**: การรัน `auto_add_product` ใน thread แยกทำให้ UI ยังคงตอบสนองได้

✅ **ไม่รบกวน check_threads()**: Method `check_threads()` จะตรวจสอบเฉพาะ main threads เท่านั้น ไม่รวม `AutoAddProductThread`

✅ **ปลอดภัย**: ยังคงใช้ `driver_lock` เพื่อป้องกันการเข้าถึง driver พร้อมกัน

## การทดสอบ

1. รันโปรแกรมและเริ่มการทำงานของ bot
2. กดปุ่ม `auto_add_product` บน widget
3. ตรวจสอบว่า:
   - Thread หลักยังทำงานต่อไป (ไม่แสดง "จบการทำงาน" ทันที)
   - `auto_add_product` ทำงานได้ตามปกติ
   - Console แสดง `Started auto_add_product in separate thread: AutoAddProductThread`

## หมายเหตุเพิ่มเติม

- **Daemon Thread**: Thread ที่สร้างด้วย `daemon=True` จะถูกปิดอัตโนมัติเมื่อโปรแกรมหลักปิด ไม่ต้องรอให้ thread นี้ทำงานเสร็จ
- **Thread Safety**: `auto_add_product()` ยังคงใช้ `driver_lock` อยู่ ดังนั้นจึงปลอดภัยจากการเข้าถึง driver พร้อมกัน
- **Error Handling**: มี try-except ครอบ `auto_add_product()` เพื่อป้องกัน thread crash

## คำถามที่คุณถาม

> "เวลากด auto_add_product บน widget ที่แสดงผลบน ui มันทำให้ thread ดับ หรือฉันควรแยก thread อีก เพื่อให้มันดำเนินการ auto_add_product ถึง threading หลัก จะไม่ดับ"

**คำตอบ**: ใช่ครับ คุณควร**แยก thread** สำหรับ `auto_add_product` ซึ่งเป็นสิ่งที่เราได้ทำไปแล้วด้วย method `auto_add_product_threaded()` นี้ จะทำให้ threading หลักไม่ดับและทำงานต่อไปได้ตามปกติ
