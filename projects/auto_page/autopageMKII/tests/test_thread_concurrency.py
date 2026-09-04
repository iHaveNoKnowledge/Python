import os
import sys
import time
import threading
import unittest
import importlib.util
from unittest.mock import MagicMock, patch

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

MODULE_PATH = os.path.join(PROJECT_DIR, "autopage_MKII_ver5.x.x.py")
spec = importlib.util.spec_from_file_location("autopage_v5_thread_test", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["autopage_v5_thread_test"] = mod
spec.loader.exec_module(mod)

StopEvent = mod.StopEvent
Bot_POS = mod.Bot_POS


class TestThreadConcurrency(unittest.TestCase):
    """ทดสอบพฤติกรรมของ Thread ในระบบ:
    1. ตรวจสอบว่าระบบมีกลไกป้องกัน Thread ทำงานซ้อนกัน (Race Condition / Concurrency Guard)
    2. ตรวจสอบว่าเมื่อมี Thread ใหม่ออกมา Thread เก่าจะถูกระงับ (Stale Abort) ทันที
    3. ตรวจสอบ StopEvent proxy ที่คอยตัดการทำงานอัตโนมัติเมื่อ generation เปลี่ยน
    """

    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_driver = MagicMock()
        self.mock_browser = MagicMock()
        self.mock_browser.driver = self.mock_driver

        self.mock_app._cycle_generation = 1
        self.mock_app.order = "TEST_ORDER_001"
        self.mock_app.items = [{"sku": "TEST-SKU", "price": 100}]
        self.mock_app.order_Search_thread = threading.Event()
        self.mock_app.order_Search_thread.set()

    def test_stop_event_generation_guard(self):
        """ทดสอบ StopEvent: เมื่อ generation เปลี่ยน is_set() ต้องกลายเป็น True ทันที
        แม้จะไม่ได้สั่ง event.set() โดยตรง เพื่อหยุด loop เก่าอัตโนมัติ"""
        mock_bot = MagicMock()
        mock_bot._active_generation = 1

        underlying_event = threading.Event()
        stop_event_gen1 = StopEvent(underlying_event, mock_bot, generation=1)

        # ขณะอยู่ที่ generation 1 และยังไม่ set -> is_set() ต้องเป็น False
        self.assertFalse(stop_event_gen1.is_set())

        # เมื่อรอบใหม่เริ่ม mock_bot._active_generation เปลี่ยนเป็น 2
        mock_bot._active_generation = 2

        # stop_event ของ generation 1 ต้องมองว่าตัวเองถูก set (stale) ทันที!
        self.assertTrue(stop_event_gen1.is_set())

    def test_stale_thread_aborts_immediately_without_running_operation(self):
        """ทดสอบว่า Thread รอบเก่าที่มี gen < _cycle_generation จะยอมแพ้และออกทันที (Stale exit)
        ไม่เข้าไปรัน operation_start() ซ้อนกับรอบใหม่"""
        bot = Bot_POS.__new__(Bot_POS)
        bot.app = self.mock_app
        bot.browser = self.mock_browser
        bot._gen_lock = threading.Lock()
        bot._active_generation = 2
        bot.operation_start = MagicMock()
        bot.record_failed_with_checkpoint = MagicMock()

        # สมมุติแอพวิ่งไปรอบที่ 2 แล้ว
        self.mock_app._cycle_generation = 2

        # Thread รอบเก่า (gen=1) พยายามจะทำงาน
        event = threading.Event()
        bot.operation_task_thread(event=event, gen=1)

        # ต้องไม่ถูกสั่ง operation_start เด็ดขาด
        bot.operation_start.assert_not_called()

    def test_overlapping_thread_prevention_simulation(self):
        """จำลองการยิง 2 Thread พร้อมกัน:
        Thread 1 กำลังทำงานวนลูปอยู่ -> Thread 2 เริ่มทำงาน
        Thread 1 จะต้องหยุดทันที และมีเพียง Thread 2 เท่านั้นที่ได้ทำงานต่อ (ไม่ซ้อนกัน)"""
        bot = Bot_POS.__new__(Bot_POS)
        bot.app = self.mock_app
        bot.browser = self.mock_browser
        bot._gen_lock = threading.Lock()
        bot._active_generation = 1
        self.mock_app._cycle_generation = 1

        thread1_loop_count = 0
        thread1_finished = threading.Event()
        thread1_started = threading.Event()

        def mock_long_operation_loop():
            nonlocal thread1_loop_count
            thread1_started.set()
            # จำลอง loop ใน operation_task_thread หรือใน method ต่างๆ ของ bot
            while not bot.operation_thread.is_set():
                thread1_loop_count += 1
                time.sleep(0.02)
                if thread1_loop_count > 100:  # safety timeout
                    break
            thread1_finished.set()

        # เริ่ม Thread 1 ที่ Generation 1
        event1 = threading.Event()
        bot.operation_thread = StopEvent(event1, bot, generation=1)

        t1 = threading.Thread(target=mock_long_operation_loop)
        t1.daemon = True
        t1.start()

        # รอให้ Thread 1 เริ่มวนลูป
        self.assertTrue(thread1_started.wait(timeout=2.0))
        time.sleep(0.05)
        self.assertGreater(thread1_loop_count, 0)
        self.assertFalse(thread1_finished.is_set())

        # ตอนนี้เริ่มรอบใหม่ (Thread 2): Generation เพิ่มเป็น 2
        with bot._gen_lock:
            bot._active_generation = 2
            self.mock_app._cycle_generation = 2

        # Thread 1 ต้องเห็นว่า is_set() == True และหยุดลูปทันที
        self.assertTrue(thread1_finished.wait(timeout=1.0))
        final_count_t1 = thread1_loop_count

        # รออีกระยะเพื่อพิสูจน์ว่า Thread 1 ไม่มีการวนลูปเพิ่มอีกต่อไป (หยุดสนิทแล้ว)
        time.sleep(0.08)
        self.assertEqual(thread1_loop_count, final_count_t1)
        self.assertFalse(t1.is_alive())

    def test_guarded_callback_drops_stale_cycle(self):
        """ทดสอบ callback guard: callback รอบเก่าจะไม่ถูกเรียกหาก cycle_generation เปลี่ยนไปแล้ว"""
        my_gen = 1
        callback_called = False

        def my_callback():
            nonlocal callback_called
            callback_called = True

        def guarded_callback():
            if getattr(self.mock_app, "_cycle_generation", 0) == my_gen and my_callback:
                my_callback()

        # กรณี generation ยังตรงกัน -> callback ต้องถูกเรียก
        self.mock_app._cycle_generation = 1
        guarded_callback()
        self.assertTrue(callback_called)

        # รีเซ็ตและเปลี่ยน generation เป็น 2
        callback_called = False
        self.mock_app._cycle_generation = 2
        guarded_callback()
        # callback รอบที่ 1 ต้องไม่ถูกเรียก
        self.assertFalse(callback_called)


if __name__ == "__main__":
    unittest.main()
