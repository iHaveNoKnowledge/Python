import datetime
import os
from typing import Any, Dict, List, Optional
import pandas as pd
from loguru import logger


class TestReportManager:
    """
    ระบบจัดการและบันทึกรายงานสรุปผลการทดสอบ / การรัน Batch
    ติดตามความสำเร็จในการสร้างชื่อลูกค้าและแก้ไขที่อยู่ลูกค้า
    """
    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.output_dir = os.path.join(base_dir, "reports")
        else:
            self.output_dir = os.path.abspath(output_dir)
        self.records: Dict[str, Dict[str, Any]] = {}
        self.session_start_time = datetime.datetime.now()

    def start_order(
        self,
        order_id: str,
        marketplace: str = "",
        customer_name: str = "",
        tax_id: str = ""
    ) -> Dict[str, Any]:
        """เริ่มบันทึกข้อมูลสำหรับ Order ใหม่"""
        order_id = str(order_id).strip()
        record = {
            "order_id": order_id,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "marketplace": marketplace,
            "customer_name": customer_name,
            "tax_id": str(tax_id) if tax_id else "",
            "customer_code": "",
            "customer_status": "PENDING",  # SUCCESS, FAILED, EXISTING, SKIPPED
            "customer_error": "",
            "address_status": "SKIPPED",   # CORRECTED, ALREADY_CORRECT, FAILED, SKIPPED, CAUTION
            "current_address": "",
            "desired_address": "",
            "address_error": "",
            "overall_status": "IN_PROGRESS",  # SUCCESS, WARNING, FAILED
            "note": ""
        }
        self.records[order_id] = record
        return record

    def record_customer_result(
        self,
        order_id: str,
        status: str,
        error: str = "",
        customer_code: str = ""
    ):
        """
        บันทึกผลการสร้าง / ค้นหาชื่อลูกค้า
        status: SUCCESS | FAILED | EXISTING | SKIPPED
        """
        order_id = str(order_id).strip()
        if order_id not in self.records:
            self.start_order(order_id)

        record = self.records[order_id]
        record["customer_status"] = status
        record["customer_error"] = str(error) if error else ""
        if customer_code:
            record["customer_code"] = str(customer_code)

        if status == "FAILED":
            record["overall_status"] = "FAILED"
            logger.error(f"[Report] Order {order_id} - สร้างลูกค้าไม่สำเร็จ: {error}")
        else:
            logger.info(f"[Report] Order {order_id} - สถานะลูกค้า: {status} ({customer_code})")

    def record_address_result(
        self,
        order_id: str,
        status: str,
        current_address: str = "",
        desired_address: str = "",
        error: str = ""
    ):
        """
        บันทึกผลการตรวจสอบ / แก้ไขที่อยู่
        status: CORRECTED | ALREADY_CORRECT | FAILED | SKIPPED | CAUTION
        """
        order_id = str(order_id).strip()
        if order_id not in self.records:
            self.start_order(order_id)

        record = self.records[order_id]
        record["address_status"] = status
        record["current_address"] = str(current_address)
        record["desired_address"] = str(desired_address)
        record["address_error"] = str(error) if error else ""

        if status == "FAILED":
            if record["overall_status"] != "FAILED":
                record["overall_status"] = "FAILED"
            logger.error(f"[Report] Order {order_id} - แก้ไขที่อยู่ไม่สำเร็จ: {error}")
        elif status == "CAUTION":
            if record["overall_status"] == "IN_PROGRESS" or record["overall_status"] == "SUCCESS":
                record["overall_status"] = "WARNING"
            logger.warning(f"[Report] Order {order_id} - ที่อยู่มีข้อควรระวัง: {error}")
        else:
            logger.info(f"[Report] Order {order_id} - สถานะที่อยู่: {status}")

    def finish_order(
        self,
        order_id: str,
        overall_status: Optional[str] = None,
        note: str = ""
    ):
        """เสร็จสิ้นการประมวลผล Order"""
        order_id = str(order_id).strip()
        if order_id not in self.records:
            self.start_order(order_id)

        record = self.records[order_id]
        if note:
            record["note"] = note

        if overall_status:
            record["overall_status"] = overall_status
        elif record["overall_status"] == "IN_PROGRESS":
            if record["customer_status"] == "FAILED" or record["address_status"] == "FAILED":
                record["overall_status"] = "FAILED"
            elif record["address_status"] == "CAUTION":
                record["overall_status"] = "WARNING"
            else:
                record["overall_status"] = "SUCCESS"

    def get_summary(self) -> Dict[str, Any]:
        """คำนวณสถิติภาพรวม"""
        total = len(self.records)
        if total == 0:
            return {
                "total_orders": 0,
                "overall_success": 0,
                "overall_failed": 0,
                "overall_warning": 0,
                "customer_success": 0,
                "customer_failed": 0,
                "customer_existing": 0,
                "address_corrected": 0,
                "address_already_correct": 0,
                "address_failed": 0,
                "address_caution": 0,
            }

        records_list = list(self.records.values())
        return {
            "total_orders": total,
            "overall_success": sum(1 for r in records_list if r["overall_status"] == "SUCCESS"),
            "overall_failed": sum(1 for r in records_list if r["overall_status"] == "FAILED"),
            "overall_warning": sum(1 for r in records_list if r["overall_status"] == "WARNING"),
            "customer_success": sum(1 for r in records_list if r["customer_status"] == "SUCCESS"),
            "customer_failed": sum(1 for r in records_list if r["customer_status"] == "FAILED"),
            "customer_existing": sum(1 for r in records_list if r["customer_status"] == "EXISTING"),
            "address_corrected": sum(1 for r in records_list if r["address_status"] == "CORRECTED"),
            "address_already_correct": sum(1 for r in records_list if r["address_status"] == "ALREADY_CORRECT"),
            "address_failed": sum(1 for r in records_list if r["address_status"] == "FAILED"),
            "address_caution": sum(1 for r in records_list if r["address_status"] == "CAUTION"),
        }

    def get_summary_text(self) -> str:
        """สร้างข้อความสรุปรายงานสรุปผล"""
        s = self.get_summary()
        if s["total_orders"] == 0:
            return "ไม่มีข้อมูลการทดสอบในรอบนี้"

        lines = [
            "========================================",
            "📊 สรุปผลรายงานการประมวลผล (Test Report)",
            "========================================",
            f"📦 จำนวนออเดอร์ทั้งหมด: {s['total_orders']} รายการ",
            f"✅ สำเร็จสมบูรณ์: {s['overall_success']} รายการ",
            f"⚠️ มีข้อควรระวัง/เตือน: {s['overall_warning']} รายการ",
            f"❌ ล้มเหลว: {s['overall_failed']} รายการ",
            "----------------------------------------",
            "👤 รายละเอียดสถานะลูกค้า (Customer):",
            f"  - สร้างใหม่สำเร็จ: {s['customer_success']}",
            f"  - มีในระบบอยู่แล้ว: {s['customer_existing']}",
            f"  - สร้างไม่สำเร็จ: {s['customer_failed']}",
            "----------------------------------------",
            "🏠 รายละเอียดสถานะที่อยู่ (Address):",
            f"  - แก้ไขสำเร็จ: {s['address_corrected']}",
            f"  - ถูกต้องอยู่แล้ว: {s['address_already_correct']}",
            f"  - มีข้อควรระวัง (เช่น สุ่มตำบล): {s['address_caution']}",
            f"  - แก้ไขไม่สำเร็จ: {s['address_failed']}",
            "========================================"
        ]
        return "\n".join(lines)

    def export_to_excel(
        self,
        filepath: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> Optional[str]:
        """ส่งออกรายงานผลลัพธ์เป็นไฟล์ Excel"""
        if not self.records:
            logger.info("No records to export in TestReportManager")
            return None

        target_dir = output_dir or self.output_dir
        os.makedirs(target_dir, exist_ok=True)

        if not filepath:
            timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_summary_report_{timestamp_str}.xlsx"
            filepath = os.path.join(target_dir, filename)

        try:
            df = pd.DataFrame(list(self.records.values()))
            
            # แปลงชื่อ Column เป็นภาษาไทยให้อ่านง่าย
            column_mapping = {
                "order_id": "หมายเลขคำสั่งซื้อ",
                "timestamp": "วันเวลาที่ดำเนินการ",
                "marketplace": "แพลตฟอร์ม",
                "customer_name": "ชื่อลูกค้า",
                "tax_id": "เลขประจำตัวผู้เสียภาษี",
                "customer_code": "รหัสลูกค้า (SMCO)",
                "customer_status": "สถานะลูกค้า",
                "customer_error": "ข้อผิดพลาดลูกค้า",
                "address_status": "สถานะการแก้ที่อยู่",
                "current_address": "ที่อยู่เดิมบน SMCO",
                "desired_address": "ที่อยู่ที่ต้องการแก้ไข",
                "address_error": "ข้อผิดพลาดที่อยู่",
                "overall_status": "สถานะภาพรวม",
                "note": "หมายเหตุ"
            }
            
            df.rename(columns=column_mapping, inplace=True)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Orders_Detail', index=False)
                
                # เพิ่ม Sheet Summary
                summary_data = [
                    {"หัวข้อ": k, "จำนวน": v}
                    for k, v in self.get_summary().items()
                ]
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Summary_Stats', index=False)

            logger.info(f"Test summary report saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to export test report to Excel: {e}")
            return None

    def clear(self):
        """ล้างประวัติการบันทึกเพื่อเริ่มรอบใหม่"""
        self.records.clear()
        self.session_start_time = datetime.datetime.now()
