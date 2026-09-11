import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from openpyxl import load_workbook
from functions.accel_mode import AccelMode, classify_failed_reason


def test_classify_failed_reason_sn_shortage():
    # 1. ข้อความ SN จาก accel_mode
    msg1 = "จำนวน SN ไม่พอ (SN ใน accel file น้อยกว่าจำนวนที่ลูกค้าสั่ง):\n  • SKU123: ลูกค้าสั่ง 2 แต่ยิง SN ได้ 1 (ขาด 1)"
    assert classify_failed_reason(msg1) == "SN_SHORTAGE"

    # 2. ข้อความ popup / alert SN
    msg2 = "กรุณากรอก serial: please input serial"
    assert classify_failed_reason(msg2) == "SN_SHORTAGE"

    # 3. ข้อความภาษาไทย
    msg3 = "ไม่มี SN สำหรับสินค้านี้ในสต็อก"
    assert classify_failed_reason(msg3) == "SN_SHORTAGE"

    msg4 = "ยิง SN ไม่สำเร็จ"
    assert classify_failed_reason(msg4) == "SN_SHORTAGE"


def test_classify_failed_reason_price_mismatch():
    # 1. ข้อความขอวิธีปรับราคา
    msg1 = "ขอวิธีปรับราคาครับ (มี SKU ใน CP_data แล้ว แต่ยังไม่มี CP/ส่วนลดให้เลือก)"
    assert classify_failed_reason(msg1) == "PRICE_MISMATCH"

    msg2 = "ขอวิธีปรับราคาครับ (พบคูปอง/ส่วนลดที่เข้าเงื่อนไข 2 ชุดบน SMCO)"
    assert classify_failed_reason(msg2) == "PRICE_MISMATCH"

    msg3 = "ราคา/จำนวนไม่ตรงหลังปรับราคา"
    assert classify_failed_reason(msg3) == "PRICE_MISMATCH"

    msg4 = "ไม่มีสินค้าให้ตรวจสอบและปรับราคา"
    assert classify_failed_reason(msg4) == "PRICE_MISMATCH"

    msg5 = "Price mismatch on POS"
    assert classify_failed_reason(msg5) == "PRICE_MISMATCH"


def test_classify_failed_reason_tracking_error():
    msg1 = "Tracking ไม่ครบ (ยังเป็นสถานะ นัดรับ)"
    assert classify_failed_reason(msg1) == "TRACKING_ERROR"

    msg2 = "ไม่พบ Package Card ของออเดอร์"
    assert classify_failed_reason(msg2) == "TRACKING_ERROR"

    msg3 = "ได้เลขไม่ครบจำนวนรายการ"
    assert classify_failed_reason(msg3) == "TRACKING_ERROR"


def test_classify_failed_reason_postal_not_found():
    msg1 = "Postal code 10250 cannot be found in dropdown"
    assert classify_failed_reason(msg1) == "POSTAL_NOT_FOUND"

    msg2 = "ไม่พบรหัสไปรษณีย์ใน dropdown"
    assert classify_failed_reason(msg2) == "POSTAL_NOT_FOUND"


def test_classify_failed_reason_order_not_found():
    msg1 = "ไม่พบออเดอร์ 240715ABCD123 ในระบบ Shopee"
    assert classify_failed_reason(msg1) == "ORDER_NOT_FOUND"

    msg2 = "order not found in excel sheet"
    assert classify_failed_reason(msg2) == "ORDER_NOT_FOUND"

    msg3 = "ไม่มีข้อมูลใน accel file"
    assert classify_failed_reason(msg3) == "ORDER_NOT_FOUND"


def test_classify_failed_reason_other():
    msg1 = "ไม่สามารถกด submit orderได้: เกิดข้อผิดพลาดไม่ทราบสาเหตุ"
    assert classify_failed_reason(msg1) == "OTHER"

    assert classify_failed_reason("") == "OTHER"
    assert classify_failed_reason(None) == "OTHER"


def test_record_failed_order_and_excel_format():
    class DummyApp:
        def __init__(self):
            pass

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = os.path.join(tmp_dir, "test_accel.xlsx")

        # สร้างไฟล์ Excel เริ่มต้นที่มีชีต Orders
        df_orders = pd.DataFrame({"orders": ["ORD111", "ORD222"], "sku": ["SKU1", "SKU2"]})
        with pd.ExcelWriter(test_file, engine="openpyxl") as writer:
            df_orders.to_excel(writer, sheet_name="Orders", index=False)

        app = DummyApp()
        accel = AccelMode(app)
        accel.accel_file_dir = test_file

        # บันทึก Failed Orders ชนิดต่างๆ
        accel.record_failed_order("ORD111", "จำนวน SN ไม่พอ (SN ใน accel file น้อยกว่าจำนวนที่ลูกค้าสั่ง)")
        accel.record_failed_order("ORD222", "ขอวิธีปรับราคาครับ")
        accel.record_failed_order("ORD333", "Tracking ไม่ครบ")
        accel.record_failed_order("ORD444", "ระบบพังไม่ทราบสาเหตุ", category="CUSTOM_CATEGORY")

        # ตรวจสอบ DataFrame ที่บันทึกใน Failed_Orders
        with pd.ExcelFile(test_file) as xl:
            assert "Failed_Orders" in xl.sheet_names
            df_failed = xl.parse("Failed_Orders")

        # 1. ตรวจสอบลำดับคอลัมน์ [timestamp, failed_category, orders, failed_reason]
        expected_cols = ["timestamp", "failed_category", "orders", "failed_reason"]
        assert list(df_failed.columns) == expected_cols

        # 2. ตรวจสอบข้อมูลและการจัดหมวดหมู่
        row1 = df_failed[df_failed["orders"] == "ORD111"].iloc[0]
        assert row1["failed_category"] == "SN_SHORTAGE"

        row2 = df_failed[df_failed["orders"] == "ORD222"].iloc[0]
        assert row2["failed_category"] == "PRICE_MISMATCH"

        row3 = df_failed[df_failed["orders"] == "ORD333"].iloc[0]
        assert row3["failed_category"] == "TRACKING_ERROR"

        row4 = df_failed[df_failed["orders"] == "ORD444"].iloc[0]
        assert row4["failed_category"] == "CUSTOM_CATEGORY"

        # 3. ตรวจสอบ openpyxl formatting (AutoFilter, FreezePanes, Column widths)
        wb = load_workbook(test_file)
        ws = wb["Failed_Orders"]
        assert ws.freeze_panes == "A2"
        assert ws.auto_filter.ref is not None

        # ตรวจสอบความกว้างของคอลัมน์ orders (คอลัมน์ C)
        col_c_letter = "C"
        col_width = ws.column_dimensions[col_c_letter].width
        assert col_width is not None
        assert col_width >= 24  # ค่าขั้นต่ำของ orders ที่กำหนดไว้
        wb.close()


def test_backward_compatibility_old_failed_orders_sheet():
    class DummyApp:
        pass

    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = os.path.join(tmp_dir, "test_legacy_accel.xlsx")

        # สร้างไฟล์ Excel จำลองระบบเก่า (ไม่มี failed_category, ลำดับ [orders, failed_reason, timestamp])
        old_df = pd.DataFrame([
            {
                "orders": "OLD_ORD_1",
                "failed_reason": "จำนวน SN ไม่พอ",
                "timestamp": "2026-09-01 10:00:00"
            },
            {
                "orders": "OLD_ORD_2",
                "failed_reason": "ขอวิธีปรับราคาครับ",
                "timestamp": "2026-09-01 10:05:00"
            }
        ])
        with pd.ExcelWriter(test_file, engine="openpyxl") as writer:
            old_df.to_excel(writer, sheet_name="Failed_Orders", index=False)

        app = DummyApp()
        accel = AccelMode(app)
        accel.accel_file_dir = test_file

        # บันทึก Failed order ใหม่เข้าไป
        accel.record_failed_order("NEW_ORD_3", "Tracking ไม่พบบัตร")

        # ตรวจสอบว่าข้อมูลเก่าถูก backfill และ reorder อย่างถูกต้อง
        with pd.ExcelFile(test_file) as xl:
            df_failed = xl.parse("Failed_Orders")

        assert list(df_failed.columns) == ["timestamp", "failed_category", "orders", "failed_reason"]
        assert len(df_failed) == 3

        # เช็คข้อมูลเก่า
        old_row1 = df_failed[df_failed["orders"] == "OLD_ORD_1"].iloc[0]
        assert old_row1["failed_category"] == "SN_SHORTAGE"

        old_row2 = df_failed[df_failed["orders"] == "OLD_ORD_2"].iloc[0]
        assert old_row2["failed_category"] == "PRICE_MISMATCH"

        # เช็คข้อมูลใหม่
        new_row = df_failed[df_failed["orders"] == "NEW_ORD_3"].iloc[0]
        assert new_row["failed_category"] == "TRACKING_ERROR"


if __name__ == '__main__':
    test_classify_failed_reason_sn_shortage()
    print("test_classify_failed_reason_sn_shortage: PASSED")
    test_classify_failed_reason_price_mismatch()
    print("test_classify_failed_reason_price_mismatch: PASSED")
    test_classify_failed_reason_tracking_error()
    print("test_classify_failed_reason_tracking_error: PASSED")
    test_classify_failed_reason_postal_not_found()
    print("test_classify_failed_reason_postal_not_found: PASSED")
    test_classify_failed_reason_order_not_found()
    print("test_classify_failed_reason_order_not_found: PASSED")
    test_classify_failed_reason_other()
    print("test_classify_failed_reason_other: PASSED")
    test_record_failed_order_and_excel_format()
    print("test_record_failed_order_and_excel_format: PASSED")
    test_backward_compatibility_old_failed_orders_sheet()
    print("test_backward_compatibility_old_failed_orders_sheet: PASSED")
    print("\nALL TESTS PASSED SUCCESSFULLY! ✅")

