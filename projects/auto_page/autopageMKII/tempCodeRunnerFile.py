except Exception as e:
            err_type = type(e).__name__
            err_msg = str(e)
            logger.error(
                f"Order: {order} - Error in order_search ({err_type}): {err_msg}",
                exc_info=True
            )
            traceback.print_exc()
            self.update_log(
                f"🛑 Error [Order: {order}]: ข้อมูลในไฟล์ไม่ถูกต้อง ({err_type}: {err_msg})")
            
            # บันทึกลง Accel file (Failed_Orders) หากเปิดโหมด Accel
            if hasattr(self, 'accel_mode') and hasattr(self, 'is_accel_mode_activated') and self.is_accel_mode_activated.get():
                try:
                    self.accel_mode.record_failed_order(
                        order, f"Error in order_search ({err_type}): {err_msg}")
                except Exception as xl_err:
                    logger.error(f"Failed to record failed order to accel file: {xl_err}")

            self.root.after(0, lambda: messagebox.showerror(
                "ข้อมูลไม่ครบถ้วน",
                f"มีค่าใน Import File ไม่ครบ หรือรูปแบบข้อมูลไม่ถูกต้อง\n\nOrder: {order}\nสาเหตุ: {err_type} - {err_msg}"
            ))
            if on_complete is not None:
                on_complete.set()
            # * หยุด operation เฉพาะเมื่อ cycle นี้ยังเป็น cycle ปัจจุบัน (กัน thread เก่าฆ่า thread ใหม่)
            if my_gen == getattr(
                    self, '_cycle_generation', 0) and hasattr(
                    self, 'operation_thread') and self.operation_thread is not None:
                self.operation_thread.set()