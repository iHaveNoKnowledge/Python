"""
ทดสอบ: กด Start (start order) ซ้ำ ขณะ bot กำลังทำงานอยู่ -> thread ค้างหรือไม่?

สถานการณ์ที่ทดสอบ:
  A) กด Start รัวๆ 4 ครั้ง (เว้นช่วงสั้น) ขณะ order_search รอบก่อนยังค้นหาไม่เสร็จ
     -> thread เก่าต้องถูกยกเลิก, thread รอบล่าสุดต้องทำงานจนเสร็จ, ไม่มี thread ค้าง
  B) กด Start ซ้ำ ขณะ operation กำลังเปิดบิลอยู่ (mid-run)
     -> operation รอบเก่าต้องหยุด, ห้ามทำงานซ้อนกัน (max concurrency = 1),
        รอบใหม่ต้องเสร็จจริง และรายงานผล SUCCESS แค่รอบเดียว
  C) กด Start โดยช่อง Order ว่าง (ทั้งตอนว่างและตอนกำลังทำงาน)
     -> ต้อง return ทันที ไม่สร้าง thread ไม่ค้างสถานะ "กำลังทำงาน"
  D) กด Start ซ้ำแล้วกด Stop ระหว่าง operation ใหม่กำลังทำงาน
     -> ทุก thread ต้องตายภายในเวลาอันสั้น และสถานะต้องขึ้น "จบการทำงาน"

วิธีการ: ใช้ของจริง (REAL code path) คือ MyApp.search_order, MyApp.check_threads,
MyApp.order_search, MyApp.stop_operation และ Bot_POS.operation_task_thread ทั้งหมด
โดย mock เฉพาะส่วน GUI/WebDriver/Excel ผ่าน FakeApp (เทคนิคเดียวกับ test_thread_concurrency.py)

รัน: python -m pytest tests/test_start_repress_hang.py -v
 หรือ: python tests/test_start_repress_hang.py
"""

import os
import sys
import time
import threading
import unittest
import importlib.util
from unittest.mock import MagicMock

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

MODULE_PATH = os.path.join(PROJECT_DIR, "autopage_MKII_ver5.x.x.py")
spec = importlib.util.spec_from_file_location("autopage_v5_repress_test", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["autopage_v5_repress_test"] = mod
spec.loader.exec_module(mod)

MyApp = mod.MyApp
Bot_POS = mod.Bot_POS
StopEvent = mod.StopEvent

JOIN_TIMEOUT = 20.0  # วินาที - ถ้า thread ยังไม่ตายถือว่า "ค้าง"


class FakeVar:
    """จำลอง tkinter StringVar/BooleanVar"""

    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, v):
        self._value = v


class FakeRoot:
    """จำลอง root.after แบบ non-blocking ด้วย daemon Timer"""

    def after(self, delay_ms, fn, *args):
        t = threading.Timer(delay_ms / 1000.0, fn, args=args)
        t.daemon = True
        t.start()
        return t


class FakeApp:
    """จำลอง MyApp เฉพาะ attribute/method ที่โค้ดจริง (search_order /
    check_threads / operation_task_thread) ต้องใช้ ส่วนเมธอดของ MyApp ที่เกี่ยวกับ
    threading จะ delegate ไปที่ของจริง เพื่อให้ทดสอบ production logic จริงๆ"""

    def __init__(self):
        self.root = FakeRoot()
        self.is_bot_running = FakeVar(False)
        self.is_accel_mode = FakeVar(False)
        self.is_tax_required = FakeVar(False)
        self.is_bot_browser_busy = FakeVar(False)
        self.marketplace_target = FakeVar("SHOPEE")
        self.cus_name = FakeVar("")
        self.tax_num = FakeVar("")
        self.entered_order = FakeVar("")
        self.mimic_column_headers = []
        self.mp_products_list_frame = MagicMock()
        self.mp_products_list_frame.winfo_children.return_value = []
        self.report_log = MagicMock()
        self.display_bot_status_label = MagicMock()
        self.report_manager = MagicMock()
        self.items = [{"sku": "TEST-SKU", "price": 100, "qty": 1}]
        self.order = ""
        self.search_query = ""
        self.autofinal = False
        self.is_data_ready = False
        self._cycle_generation = 0
        self.logs = []
        self.operation_thread = threading.Event()
        self.order_Search_thread = threading.Event()
        self.longer_thread_cycle = None
        self.shorter_thread_cycle = None

        # bot จริง (สร้างแบบข้าม __init__ เพื่อไม่ให้ไปยุ่งกับ browser/logger)
        self.bot = Bot_POS.__new__(Bot_POS)
        self.bot.app = self
        self.bot._gen_lock = threading.Lock()
        self.bot._active_generation = 0
        self.bot.driver_lock = threading.Lock()
        self.bot.get_tabs = lambda *a, **k: None
        self.bot.operation_start = MagicMock()
        self.bot.record_failed_with_checkpoint = MagicMock()

    # --- delegate ไปยังโค้ดจริงของ MyApp ---
    def check_threads(self, longer_thread_cycle, shorter_thread_cycle, callback=None):
        return MyApp.check_threads(
            self, longer_thread_cycle, shorter_thread_cycle, callback)

    def order_search(self, order, on_complete):
        return MyApp.order_search(self, order, on_complete)

    def stop_operation(self):
        return MyApp.stop_operation(self)

    def update_log(self, txt):
        self.logs.append(str(txt))


def make_fake_search_internal(app, duration, log):
    """จำลอง _order_search_internal (ส่วนหาข้อมูล order จาก Excel/API ที่หนัก)
    - duration <= 0: เสร็จทันที
    - duration > 0: ทำงานนานตาม duration โดยเช็คจุดยกเลิกทุก 50ms
      (ถ้า on_complete ถูก set จากรอบใหม่ = ถูกยกเลิก จะบันทึก cancelled)"""

    def fake_internal(order, on_complete, my_gen=None):
        on_complete.clear()
        if order is None or str(order).strip() == "":
            on_complete.set()
            return
        order = str(order).strip()
        app.order = order
        if duration <= 0:
            log.append(("completed", order, my_gen))
            on_complete.set()
            return
        deadline = time.time() + duration
        while time.time() < deadline:
            if on_complete.is_set():
                log.append(("cancelled", order, my_gen))
                return
            time.sleep(0.05)
        log.append(("completed", order, my_gen))
        on_complete.set()

    return fake_internal


class OperationTracker:
    """นับจำนวน operation ที่ทำงานซ้อนกันพร้อมม + ผลลัพธ์ของแต่ละรอบ"""

    def __init__(self):
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.completed = []
        self.aborted = []

    def make_slow_operation_start(self, bot, duration):
        """จำลอง operation_start (เปิดบิลบน SMCO) ที่ใช้เวลานาน
        เช็ค stop flag ทุก 50ms เหมือนจุดเช็คจริงใน operation_start
        ถ้าถูกสั่งหยุดกลางทาง -> raise RuntimeError (เหมือน abort กลางงานจริง)"""

        def slow_operation_start():
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            try:
                deadline = time.time() + duration
                while time.time() < deadline:
                    if bot.operation_thread.is_set():
                        self.aborted.append(bot.app.order)
                        raise RuntimeError("SimulatedAbort: stop detected mid-operation")
                    time.sleep(0.05)
                self.completed.append(bot.app.order)
            finally:
                with self.lock:
                    self.active -= 1

        return slow_operation_start


def snapshot_workers(app):
    """ดึง reference ของ worker thread ของ cycle ปัจจุบัน (เรียกทันทีหลังกด Start)"""
    return [t for t in (app.longer_thread_cycle, app.shorter_thread_cycle)
            if isinstance(t, threading.Thread)]


def join_all(threads, timeout=JOIN_TIMEOUT):
    """join ทุก thread ด้วย deadline รวม คืนชื่อ thread ที่ยังไม่ตาย (= ค้าง)"""
    deadline = time.time() + timeout
    stuck = []
    for t in threads:
        t.join(timeout=max(0.01, deadline - time.time()))
        if t.is_alive():
            stuck.append(t.name)
    return stuck


def new_non_daemon_threads(baseline_names):
    cur = threading.current_thread()
    return [t for t in threading.enumerate()
            if t is not cur and not t.daemon and t.name not in baseline_names]


def count_finish_status(report_manager, status):
    return sum(1 for c in report_manager.finish_order.call_args_list
               if c.kwargs.get("overall_status") == status)


class TestStartRepressHang(unittest.TestCase):
    """ทดสอบกด Start order ซ้ำขณะกำลังทำงาน - ตรวจว่า thread ค้าง / ซ้อน / รั่วไหลหรือไม่"""

    def setUp(self):
        self.baseline_thread_names = set(
            t.name for t in threading.enumerate())

    def tearDown(self):
        leaks = new_non_daemon_threads(self.baseline_thread_names)
        self.assertEqual(
            [], leaks,
            f"Thread หลุดรอด (ยัง alive แบบ non-daemon) หลังจบเทส: {[t.name for t in leaks]}")

    # ------------------------------------------------------------------
    # A) กด Start รัวๆ ขณะ order_search ยังค้นหาไม่เสร็จ
    # ------------------------------------------------------------------
    def test_a_rapid_start_presses_during_search_no_hang(self):
        app = FakeApp()
        search_log = []
        app._order_search_internal = make_fake_search_internal(
            app, duration=0.8, log=search_log)  # search รอบละ 0.8 วินาที

        n_presses = 4
        all_workers = []
        cycle_events = []
        press_durations = []
        orders = [f"2609032XS86R9{k}" for k in range(1, n_presses + 1)]

        t_start = time.time()
        for k, order in enumerate(orders):
            app.entered_order.set(order)
            t0 = time.time()
            MyApp.search_order(app)  # เหมือนกดปุ่ม Start บน main thread
            press_durations.append(time.time() - t0)
            cycle_events.append(app.order_Search_thread)
            all_workers.extend(snapshot_workers(app))
            if k < n_presses - 1:
                time.sleep(0.12)  # กดซ้ำขณะ search รอบก่อนยังลากอยู่แน่นอน

        # ปุ่ม Start ทุกครั้งต้อง return ทันที (ไม่ block GUI thread)
        for i, dur in enumerate(press_durations):
            self.assertLess(
                dur, 2.0,
                f"การกด Start ครั้งที่ {i+1} block เมน thread นานเกินไป ({dur:.2f}s)")

        # ทุก worker thread (search + operation ของทุก cycle) ต้องตายภายใน timeout
        stuck = join_all(all_workers, timeout=JOIN_TIMEOUT)
        self.assertEqual(
            [], stuck,
            f"พบ thread ค้าง (ไม่จบภายใน {JOIN_TIMEOUT}s): {stuck}")

        elapsed = time.time() - t_start
        self.assertLess(
            elapsed, 15.0,
            f"ระบบใช้เวลานานผิดปกติ ({elapsed:.1f}s) สงสัยมี thread ค้าง")

        # generation ต้องเดินครบทุกครั้งที่กด
        self.assertEqual(n_presses, app._cycle_generation)
        self.assertEqual(n_presses, app.bot._active_generation)

        # search รอบที่ 1..3 ต้องถูกยกเลิก (stale), รอบสุดท้ายต้องเสร็จเอง
        cancelled = [e for e in search_log if e[0] == "cancelled"]
        completed = [e for e in search_log if e[0] == "completed"]
        self.assertEqual(
            n_presses - 1, len(cancelled),
            f"search รอบเก่าต้องถูกยกเลิก {n_presses - 1} รอบ แต่ได้ {cancelled}")
        self.assertEqual(
            1, len(completed),
            f"ต้องมี search เสร็จจริงแค่รอบสุดท้ายรอบเดียว แต่ได้ {completed}")
        self.assertEqual(orders[-1], completed[0][1],
                         "รอบที่เสร็จต้องเป็น order ล่าสุดที่กด (ข้อมูลต้องไม่ปนกัน)")

        # event ของทุก cycle ต้องถูก set ในที่สุด (ไม่มี deadlock รอ event)
        for i, ev in enumerate(cycle_events):
            self.assertTrue(
                ev.is_set(),
                f"order_Search_thread ของ cycle {i+1} ยังไม่ถูก set -> รอค้าง")

    # ------------------------------------------------------------------
    # B) กด Start ซ้ำ ขณะ operation กำลังเปิดบิลอยู่ (กลางงาน)
    # ------------------------------------------------------------------
    def test_b_repress_while_operation_running_no_overlap(self):
        app = FakeApp()
        search_log = []
        app._order_search_internal = make_fake_search_internal(
            app, duration=0.15, log=search_log)  # search เร็ว เพื่อโฟกัสที่ operation

        tracker = OperationTracker()
        app.bot.operation_start = tracker.make_slow_operation_start(
            app.bot, duration=1.5)

        order = "2609032XS86R91"

        # กดครั้งที่ 1 -> operation เริ่มเปิดบิล (ใช้เวลา 1.5s)
        app.entered_order.set(order)
        t0 = time.time()
        MyApp.search_order(app)
        press1_duration = time.time() - t0
        workers1 = snapshot_workers(app)

        # รอให้ operation รอบแรกลงมือทำงานจริง (search 0.15s + รอ event <=0.5s)
        time.sleep(1.0)

        # กดครั้งที่ 2 ขณะ operation รอบแรกกำลังเปิดบิลอยู่
        app.entered_order.set(order)
        t0 = time.time()
        MyApp.search_order(app)
        press2_duration = time.time() - t0
        workers2 = snapshot_workers(app)

        self.assertLess(press1_duration, 2.0, "กด Start ครั้งที่ 1 block GUI")
        self.assertLess(press2_duration, 2.0,
                        "กด Start ซ้ำขณะทำงาน block GUI นานเกินไป (สัญญาณ freeze)")

        # ทุก thread ต้องจบ (รอบเก่าถูก abort, รอบใหม่ทำจนเสร็จ)
        stuck = join_all(workers1 + workers2, timeout=JOIN_TIMEOUT)
        self.assertEqual([], stuck, f"พบ thread ค้างหลังกด Start ซ้ำ: {stuck}")

        # ห้าม operation ทำงานซ้อนกันเด็ดขาด (บั๊ก threadซ้อน ตาม updatenote #341)
        self.assertEqual(
            1, tracker.max_active,
            f"พบ operation ทำงานซ้อนกัน {tracker.max_active} thread พร้อมกัน!")

        # operation รอบเก่าต้องถูก abort กลางงาน และรอบใหม่ต้องเสร็จจริง 1 รอบ
        self.assertEqual(1, len(tracker.aborted),
                         f"operation รอบเก่าต้องถูก abort 1 ครั้ง ได้ {tracker.aborted}")
        self.assertEqual([order], tracker.completed,
                         "operation รอบใหม่ต้องเสร็จเป็นรอบเดียว")

        # รายงานผล: SUCCESS ต้องมีแค่รอบใหม่รอบเดียว, FAILED 1 (จากรอบที่ถูก abort)
        self.assertEqual(1, count_finish_status(app.report_manager, "SUCCESS"),
                         "ต้องปิด order ด้วย SUCCESS แค่ครั้งเดียว")
        self.assertEqual(1, count_finish_status(app.report_manager, "FAILED"))
        self.assertEqual(1, app.bot.record_failed_with_checkpoint.call_count)

        # generation ต้องเดินเป็น 2 พอดี
        self.assertEqual(2, app._cycle_generation)
        self.assertEqual(2, app.bot._active_generation)

    # ------------------------------------------------------------------
    # C) กด Start โดย Order ว่าง ต้องไม่สร้าง thread และไม่ค้าง
    # ------------------------------------------------------------------
    def test_c_start_with_empty_order_spawns_no_thread(self):
        app = FakeApp()
        search_log = []
        app._order_search_internal = make_fake_search_internal(
            app, duration=0.0, log=search_log)

        app.entered_order.set("   ")  # ว่าง/ช่องว่างเท่านั้น
        t0 = time.time()
        MyApp.search_order(app)
        dur = time.time() - t0

        self.assertLess(dur, 0.5, "กด Start ตอน order ว่าง ต้อง return ทันที")
        self.assertIsNone(
            app.longer_thread_cycle, "ห้ามสร้าง operation thread เมื่อ order ว่าง")
        self.assertIsNone(
            app.shorter_thread_cycle, "ห้ามสร้าง search thread เมื่อ order ว่าง")
        self.assertEqual(0, app._cycle_generation, "ห้ามเปลี่ยน generation")
        self.assertEqual([], search_log, "ห้ามเริ่มค้นหาเมื่อ order ว่าง")
        self.assertIn("ไม่ได้กรอกเลข Order", " ".join(app.logs))

    # ------------------------------------------------------------------
    # D) กด Start ซ้ำแล้วกด Stop ระหว่าง operation ใหม่ทำงานอยู่
    # ------------------------------------------------------------------
    def test_d_repress_then_stop_kills_all_threads_quickly(self):
        app = FakeApp()
        search_log = []
        app._order_search_internal = make_fake_search_internal(
            app, duration=0.15, log=search_log)

        tracker = OperationTracker()
        app.bot.operation_start = tracker.make_slow_operation_start(
            app.bot, duration=3.0)

        order = "2609032XS86R91"

        app.entered_order.set(order)
        MyApp.search_order(app)
        workers1 = snapshot_workers(app)
        time.sleep(1.0)

        # กดซ้ำขณะกำลังทำงาน
        app.entered_order.set(order)
        MyApp.search_order(app)
        workers2 = snapshot_workers(app)
        time.sleep(0.5)  # ให้ operation รอบใหม่ลงมือทำก่อน

        # กด Stop
        MyApp.stop_operation(app)

        t0 = time.time()
        stuck = join_all(workers1 + workers2, timeout=10.0)
        stop_elapsed = time.time() - t0

        self.assertEqual([], stuck, f"หลังกด Stop ยังมี thread ค้าง: {stuck}")
        self.assertLess(stop_elapsed, 5.0,
                        f"หลังกด Stop thread ต้องตายใน ~ทันที แต่ใช้ {stop_elapsed:.1f}s")
        self.assertEqual(1, tracker.max_active, "ห้าม operation ซ้อนกัน")
        self.assertEqual([], tracker.completed,
                         "หลังกด Stop ห้ามมี operation ไหนรันจนเสร็จ")

        # สถานะบน GUI ต้องขึ้น "จบการทำงาน"
        status_texts = [
            str(c.kwargs.get("text", ""))
            for c in app.display_bot_status_label.configure.call_args_list
            if isinstance(c.kwargs, dict)
        ]
        self.assertTrue(
            any("จบการทำงาน" in txt for txt in status_texts),
            f"สถานะ GUI ต้องขึ้น 'จบการทำงาน' แต่ได้ {status_texts}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
