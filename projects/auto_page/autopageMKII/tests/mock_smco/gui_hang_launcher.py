"""
Launcher สำหรับทดสอบ GUI จริงของ autopage_MKII_ver5.x.x.py
------------------------------------------------------------
สิ่งที่เป็น "ของจริง":
  - Mock SMCO server ที่ 127.0.0.1:8765 (daemon thread)
  - Chrome จริง (remote debugging :8990 — พอร์ตทดสอบแยกจากบอทจริงที่ใช้ :8989)
    ชี้ไปหน้า POS จำลอง
  - CTk() + MyApp ตัวจริง (Bot_POS/BrowserManager/threads ทั้งหมดจริง)
  - กดปุ่ม Start ตัวจริง (inp1_search_btn.invoke()) ซ้ำๆ ขณะ bot กำลังทำงาน

⚠️ ความปลอดภัย: แยกพอร์ต 8990 ออกจากบอทจริง (:8989) เพื่อไม่ให้การทดสอบ
   เข้าไปยุ่งกับ Chrome ประจำของบอท / หน้า SMCO จริงในระหว่างที่ production กำลังรัน

สิ่งที่ stub (เฉพาะสิ่งที่ติดต่ออินเทอร์เน็ตภายนอก):
  - MarketplaceScraper.scrape_order -> MarketplaceOrderResult (ไม่ยิง Shopee/Lazada จริง)
  - get_vatinfo_data -> dict ปลอม (ไม่ยิง vsinter.rd.go.th)
  - BrowserManager.setup_chrome -> attach เข้า :8990 แทน :8989

ผลลัพธ์: พิมพ์สรุป THREAD SAMPLES + VERDICT ลง stdout
  exit 0 = ไม่ค้าง, exit 2 = setup ล้มเหลว, exit 3 = พบ thread ค้าง

รัน: python tests/mock_smco/gui_hang_launcher.py
"""

import os
import sys

# / กัน UnicodeEncodeError (cp1252) เมื่อ run แบบ redirect output บน Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import time
import socket
import shutil
import threading
import subprocess
import importlib.util
import faulthandler

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(TESTS_DIR, "..", ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

MOCK_PORT = 8765
MOCK_URL = f"http://127.0.0.1:{MOCK_PORT}"
TEST_DEBUG_PORT = 8990  # ⚠️ ห้ามใช้ 8989 (พอร์ตบอทจริง)
MONITOR_SECONDS = 90
JOIN_TIMEOUT = 40.0
LOG_DIR = TESTS_DIR  # / stack dump จะถูกเขียนไว้นี่


def log(*args):
    print("[LAUNCHER]", *args, flush=True)


# ----------------------------------------------------------------------
# 1) เริ่ม Mock SMCO server (in-process, daemon)
# ----------------------------------------------------------------------
mock_spec = importlib.util.spec_from_file_location(
    "mock_smco_server", os.path.join(TESTS_DIR, "mock_smco_server.py"))
mock_mod = importlib.util.module_from_spec(mock_spec)
sys.modules["mock_smco_server"] = mock_mod
mock_spec.loader.exec_module(mock_mod)

_old_argv = sys.argv
sys.argv = [sys.argv[0], str(MOCK_PORT)]
threading.Thread(target=mock_mod.main, daemon=True).start()
sys.argv = _old_argv


def wait_port(port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


if not wait_port(MOCK_PORT):
    log("❌ Mock server ไม่ขึ้น")
    sys.exit(2)
log(f"✅ Mock SMCO server ready at {MOCK_URL}")

# ----------------------------------------------------------------------
# 2) เปิด Chrome จริงด้วย remote debugging ที่ 8990 (แยกจากบอทจริง :8989)
# ----------------------------------------------------------------------
chrome_candidates = [
    shutil.which("chrome"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]
chrome_exe = next((p for p in chrome_candidates if p and os.path.exists(p)), None)
if not chrome_exe:
    log("❌ ไม่พบ Chrome")
    sys.exit(2)

user_data_dir = os.path.join(TESTS_DIR, "mock_smco", ".chrome_profile")
os.makedirs(user_data_dir, exist_ok=True)
chrome_proc = subprocess.Popen([
    chrome_exe,
    f"--remote-debugging-port={TEST_DEBUG_PORT}",
    f"--user-data-dir={user_data_dir}",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-popup-blocking",
    "--remote-allow-origins=*",
    "about:blank",
])
log(f"✅ Chrome started (pid={chrome_proc.pid}), waiting for debug port {TEST_DEBUG_PORT}...")

if not wait_port(TEST_DEBUG_PORT, timeout=40):
    log(f"❌ Chrome debug port {TEST_DEBUG_PORT} ไม่ขึ้น")
    chrome_proc.terminate()
    sys.exit(2)

# ทดสอบ attach ผ่าน chromedriver ก่อน (เหมือน BrowserManager.setup_chrome) + โหลดหน้า POS
from selenium import webdriver

probe = None
for attempt in range(1, 4):
    _probe_opts = webdriver.ChromeOptions()
    _probe_opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    _probe_opts.add_experimental_option(
        "debuggerAddress", f"localhost:{TEST_DEBUG_PORT}")
    _probe_opts.add_argument("--disable-popup-blocking")
    try:
        probe = webdriver.Chrome(options=_probe_opts)
        probe.get(f"{MOCK_URL}/smartcore/smartpos/pointofsales/posmainv3.htm")
        log(f"✅ chromedriver attach OK (attempt {attempt}), title =", probe.title)
        probe.quit()
        break
    except Exception as e:
        log(f"⚠️ attach attempt {attempt} ไม่สำเร็จ: {type(e).__name__}: {str(e).splitlines()[0]}")
        time.sleep(3)
else:
    log("❌ attach chromedriver ไม่สำเร็จหลัง retry 3 ครั้ง")
    chrome_proc.terminate()
    sys.exit(2)

# ----------------------------------------------------------------------
# 3) โหลดโมดูลแอปตัวจริง + สร้าง MyApp ตัวจริง
# ----------------------------------------------------------------------
MODULE_PATH = os.path.join(PROJECT_DIR, "autopage_MKII_ver5.x.x.py")
spec = importlib.util.spec_from_file_location("autopage_v5_gui", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules["autopage_v5_gui"] = mod
spec.loader.exec_module(mod)

# / _onKeyRelease define ภายใต้ if __name__ == "__main__" เท่านั้น
#   ตอน import ต้อง stub ให้ UserAccount.create_subwindow (ที่ bind <Key>) ทำงานได้
if not hasattr(mod, "_onKeyRelease"):
    mod._onKeyRelease = lambda event: None

from functions.marketplace_scraper import MarketplaceOrderResult

import customtkinter as ctk

root = mod.CTk()

log(f"กำลังสร้าง MyApp (Bot_POS + BrowserManager จะ attach ไปที่ Chrome :{TEST_DEBUG_PORT})...")
app = mod.MyApp(root)


# ----------------------------------------------------------------------
# 4) Stub เฉพาะจุดที่ยิงออกอินเทอร์เน็ตจริง
# ----------------------------------------------------------------------
def fake_scrape_order(order_no, marketplace):
    log(f"[STUB] scrape_order({order_no!r}, {marketplace!r}) -> READY")
    return MarketplaceOrderResult(
        order_no=order_no, marketplace=marketplace, status="READY_TO_SHIP")


app.bot.marketplace_scraper.scrape_order = fake_scrape_order
app.bot.get_vatinfo_data = lambda tax_num, branch: {
    "name": app.cus_name.get(), "brano": branch or "00000"}

# / BrowserManager ใช้พอร์ตทดสอบ 8990 (ไม่แตะ :8989 ของบอทจริง)
from functions.browser_manager import BrowserManager

_orig_setup_chrome = BrowserManager.setup_chrome


def _test_setup_chrome(self):
    from selenium import webdriver as _wd
    opt = _wd.ChromeOptions()
    opt.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    opt.add_experimental_option(
        "debuggerAddress", f"localhost:{TEST_DEBUG_PORT}")
    opt.add_argument("--disable-popup-blocking")
    return _wd.Chrome(options=opt)


BrowserManager.setup_chrome = _test_setup_chrome
log(f"✅ stubbed: scrape_order, get_vatinfo_data, "
    f"BrowserManager.setup_chrome -> :{TEST_DEBUG_PORT}")

# ----------------------------------------------------------------------
# 5) สร้าง Excel fixture (Shopee export จำลอง) + simulate import
# ----------------------------------------------------------------------
import pandas as pd

tmp_dir = os.path.join(TESTS_DIR, "mock_smco", "fixtures")
os.makedirs(tmp_dir, exist_ok=True)
excel_path = os.path.join(tmp_dir, "mock_orders.xlsx")

ROWS = [
    {
        "หมายเลขคำสั่งซื้อ": "2609032XS86R91",
        "สถานะการสั่งซื้อ": "READY_TO_SHIP",
        "โค้ดส่วนลดชำระโดยผู้ขาย": "0",
        "ค่าจัดส่งที่ชำระโดยผู้ซื้อ": 20.0,
        "ประเภทใบกำกับภาษี": "",
        "ชื่อ": "สมชาย ใจดี",
        "ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป": "",
        "แขวง/ตำบล": "คลองเตย",
        "เขต/อำเภอ.1": "คลองเตย",
        "จังหวัด.1": "กรุงเทพมหานคร",
        "รหัสไปรษณีย์.1": "10110",
        "หมายเลขประจำตัวผู้เสียภาษี": "",
        "หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี": "",
        "อีเมลสำหรับรับใบกำกับภาษี": "",
        "ชื่อผู้ใช้ (ผู้ซื้อ)": "somchai_jaidee",
        "จำนวนเงินทั้งหมด": 100.0,
        "วันที่ทำการสั่งซื้อ": "2026-09-07 10:00",
        "โค้ดส่วนลดชำระโดย Shopee (เช่น โค้ดจากโปรแกรม ร้านโค้ดคุ้ม, โค้ดส่วนลด Shopee, โค้ดส่วนลด Shopee Mall)": "",
        "รายละเอียดที่อยู่": "1/1 ถนนสุขุมวิท",
        "ประเภทสาขา": "สำนักงานใหญ่",
        "รหัสประจำสาขา": "",
        "หมายเหตุจากผู้ซื้อ": "",
        "บันทึก": "",
        "ชื่อผู้รับ": "สมชาย ใจดี",
        "หมายเลขโทรศัพท์": "0812345678",
        "เลขอ้างอิง SKU (SKU Reference No.)": "ABC-000001",
        "ชื่อสินค้า": "Mock Product A",
        "ราคาขาย": 100.0,
        "จำนวน": 1,
        "ราคาขายสุทธิ": 100.0,
        "ส่วนลดจาก Shopee": 0.0,
        "ชื่อตัวเลือก": "",
        "*หมายเลขติดตามพัสดุ": "",
    },
    {
        "หมายเลขคำสั่งซื้อ": "2609032XS86R92",
        "สถานะการสั่งซื้อ": "READY_TO_SHIP",
        "โค้ดส่วนลดชำระโดยผู้ขาย": "0",
        "ค่าจัดส่งที่ชำระโดยผู้ซื้อ": 20.0,
        "ประเภทใบกำกับภาษี": "",
        "ชื่อ": "สมหญิง รักไทย",
        "ที่อยู่สำหรับออกใบกำกับภาษีแบบเต็มรูป": "",
        "แขวง/ตำบล": "คลองเตย",
        "เขต/อำเภอ.1": "คลองเตย",
        "จังหวัด.1": "กรุงเทพมหานคร",
        "รหัสไปรษณีย์.1": "10110",
        "หมายเลขประจำตัวผู้เสียภาษี": "",
        "หมายเลขโทรศัพท์สำหรับออกใบกำกับภาษี": "",
        "อีเมลสำหรับรับใบกำกับภาษี": "",
        "ชื่อผู้ใช้ (ผู้ซื้อ)": "somying_raktai",
        "จำนวนเงินทั้งหมด": 250.0,
        "วันที่ทำการสั่งซื้อ": "2026-09-07 10:05",
        "โค้ดส่วนลดชำระโดย Shopee (เช่น โค้ดจากโปรแกรม ร้านโค้ดคุ้ม, โค้ดส่วนลด Shopee, โค้ดส่วนลด Shopee Mall)": "",
        "รายละเอียดที่อยู่": "2/2 ถนนสุขุมวิท",
        "ประเภทสาขา": "สำนักงานใหญ่",
        "รหัสประจำสาขา": "",
        "หมายเหตุจากผู้ซื้อ": "",
        "บันทึก": "",
        "ชื่อผู้รับ": "สมหญิง รักไทย",
        "หมายเลขโทรศัพท์": "0898765432",
        "เลขอ้างอิง SKU (SKU Reference No.)": "ABC-000001",
        "ชื่อสินค้า": "Mock Product A",
        "ราคาขาย": 125.0,
        "จำนวน": 2,
        "ราคาขายสุทธิ": 250.0,
        "ส่วนลดจาก Shopee": 0.0,
        "ชื่อตัวเลือก": "",
        "*หมายเลขติดตามพัสดุ": "",
    },
]

df = pd.DataFrame(ROWS)
df["จำนวน"] = df["จำนวน"].astype(int)
df["ค่าจัดส่งที่ชำระโดยผู้ซื้อ"] = df["ค่าจัดส่งที่ชำระโดยผู้ซื้อ"].astype(float)
df["โค้ดส่วนลดชำระโดยผู้ขาย"] = df["โค้ดส่วนลดชำระโดยผู้ขาย"].astype(float)
df["หมายเลขประจำตัวผู้เสียภาษี"] = df["หมายเลขประจำตัวผู้เสียภาษี"].astype(str)
df.to_excel(excel_path, index=False)
log(f"✅ fixture excel -> {excel_path}")

# simulate import (สิ่งที่ปุ่ม Import ปกติทำ)
app.result = "Excel"
app.table_location = excel_path
app.marketplace_target.set("SHOPEE")
app.get_data_frame()
log(f"✅ data_frame loaded: rows={len(getattr(app, 'data_frame', []))}")

# / เปิด Test Mode + checkpoint 3 (หลังยิงสินค้า/คูปองหน้าแรก)
#   เพื่อให้ operation จบสะอาดที่หน้าแรก POS ใน mock ที่ไม่มีหน้าท้ายให้ทำงาน
app.is_testing = True
app.test_checkpoint.set("3. หลังยิงสินค้า/คูปองหน้าแรก")
log("✅ Test Mode ON (checkpoint 3: หยุดหลังยิงสินค้าหน้าแรก)")

# ----------------------------------------------------------------------
# 6) Thread monitor (ถ้า thread set ค้างนิ่ง > 25s -> dump stack ทุก thread)
# ----------------------------------------------------------------------
MONITOR_PERIOD = 2.0
HANG_SUSPECT_SECONDS = 25.0
stop_monitor = threading.Event()
thread_samples = []
status_samples = []
_hang_state = {"sig": None, "since": None, "dumped": False}


def worker_threads():
    names = ("Thread-",)
    return [t for t in threading.enumerate()
            if t.name.startswith(names) and not t.daemon
            and t is not threading.current_thread()]


def dump_all_stacks(reason):
    log(f"⚠️ [STACKDUMP] {reason} -> dump python stack ทุก thread:")
    try:
        # / faulthandler.dump_traceback ต้องการ file ที่มี fileno (StringIO ใช้ไม่ได้)
        dump_path = os.path.join(LOG_DIR, "thread_stacks_dump.txt")
        with open(dump_path, "w", encoding="utf-8") as f:
            faulthandler.dump_traceback(file=f)
        log(f"stack dump saved -> {dump_path}")
        with open(dump_path, "r", encoding="utf-8") as f:
            for line in f.read().splitlines():
                print("[STACK] " + line, flush=True)
    except Exception as e:
        log("dump_traceback failed:", e)


def monitor():
    while not stop_monitor.is_set():
        ws = worker_threads()
        try:
            status = app.display_bot_status_label.cget("text")
        except Exception:
            status = "<n/a>"
        now = time.time()
        thread_samples.append((now, len(ws), [t.name for t in ws]))
        status_samples.append((now, str(status)))
        log(f"[MONITOR] workers={len(ws)} {status}")

        # / ตรวจ "ค้างนิ่ง": worker set เดิมซ้ำๆ นานเกิน HANG_SUSPECT_SECONDS
        sig = tuple(sorted(t.name for t in ws))
        if sig:
            if sig == _hang_state["sig"]:
                if (_hang_state["since"] is not None
                        and now - _hang_state["since"] > HANG_SUSPECT_SECONDS
                        and not _hang_state["dumped"]):
                    dump_all_stacks(
                        f"worker set {sig} นิ่งมากว่า {HANG_SUSPECT_SECONDS:.0f}s")
                    _hang_state["dumped"] = True
            else:
                _hang_state["sig"] = sig
                _hang_state["since"] = now
                _hang_state["dumped"] = False
        else:
            _hang_state["sig"] = None
            _hang_state["since"] = None
            _hang_state["dumped"] = False

        stop_monitor.wait(MONITOR_PERIOD)


threading.Thread(target=monitor, daemon=True, name="GuiTestMonitor").start()

# ----------------------------------------------------------------------
# 7) กด Start (ปุ่มจริง) ซ้ำๆ ขณะกำลังทำงาน
# ----------------------------------------------------------------------
press_log = []


def press_start(order_no):
    def _do():
        app.entered_order.set(order_no)
        t0 = time.time()
        app.inp1_search_btn.invoke()
        dur = time.time() - t0
        press_log.append((order_no, dur))
        log(f"[PRESS] Start '{order_no}' invoke() กลับมาใน {dur:.2f}s"
            + ("  ⚠️ GUI freeze!" if dur > 2.0 else ""))
    return _do


ORDERS = ["2609032XS86R91", "2609032XS86R91", "2609032XS86R92"]

# press 1: ทันที
root.after(800, press_start(ORDERS[0]))

# press 2: เมื่อเห็นสถานะ "กำลังทำงาน" (search รอบแรกยังลากอยู่/เพิ่งเริ่ม operation)


def press2_when_running():
    try:
        status = app.display_bot_status_label.cget("text")
    except Exception:
        status = ""
    if "กำลังทำงาน" in str(status):
        press_start(ORDERS[1])()
    else:
        root.after(500, press2_when_running)


root.after(2500, press2_when_running)

# press 3: ระหว่าง operation ทำงานแน่นอน (mid-run)
root.after(12000, press_start(ORDERS[2]))

# จบ monitor + ปิด GUI หลังเงียบพอ
root.after(int(MONITOR_SECONDS * 1000), stop_monitor.set)
root.after(int(MONITOR_SECONDS * 1000) + 500, root.destroy)

log("🚀 เริ่ม mainloop - เฝ้าดู GUI และ thread ได้ที่หน้าจอตอนนี้")
exit_code = 0
try:
    root.mainloop()
except Exception as e:
    log("mainloop error:", e)
finally:
    stop_monitor.set()
    time.sleep(1)

    # ------------------------------------------------------------------
    # 8) สรุปผล: thread ค้างไหม?
    # ------------------------------------------------------------------
    log("=" * 60)
    log("PRESS LOG:")
    for order_no, dur in press_log:
        flag = "  ⚠️ FREEZE" if dur > 2.0 else ""
        log(f"  Start '{order_no}': {dur:.2f}s{flag}")

    log("THREAD SAMPLES (last 10):")
    for ts, n, names in thread_samples[-10:]:
        log(f"  t={ts - thread_samples[0][0]:6.1f}s workers={n} {names}")

    # join worker ที่เหลือด้วย deadline
    t0 = time.time()
    stuck = []
    for t in worker_threads():
        t.join(timeout=max(0.5, JOIN_TIMEOUT - (time.time() - t0)))
        if t.is_alive():
            stuck.append(t.name)

    log("THREAD JOIN:", "OK ทุก thread ตายหมด"
        if not stuck else f"❌ ค้าง: {stuck}")

    # สถานะ GUI สุดท้าย
    try:
        final_status = str(app.display_bot_status_label.cget("text"))
    except Exception:
        final_status = "<n/a>"
    log(f"FINAL STATUS: {final_status}")

    if thread_samples:
        counts = [n for _, n, _ in thread_samples]
        log(f"worker count: min={min(counts)} max={max(counts)} "
            f"(สุดท้าย {counts[-1]})")

    hang = bool(stuck)
    frozen = any(dur > 2.0 for _, dur in press_log)

    log("-" * 60)
    if hang or frozen:
        log("❌ VERDICT: พบปัญหา - "
            + ("thread ค้าง: " + str(stuck) if hang else "")
            + (" GUI freeze" if frozen else ""))
        exit_code = 3
    else:
        log("✅ VERDICT: กด Start ซ้ำขณะทำงาน ไม่มี thread ค้าง ไม่มี GUI freeze")
        exit_code = 0

    # เก็บสะสาง: ปิด chrome ที่เปิดไว้ (เฉพาะของเทส)
    try:
        chrome_proc.terminate()
    except Exception:
        pass

    # / บังคับออกจริงๆ กัน thread ที่ยัง non-daemon ค้างทำให้ process ไม่ตาย
    log(f"EXIT CODE: {exit_code}")
    sys.stdout.flush()
    os._exit(exit_code)
log("=" * 60)
log("PRESS LOG:")
for order_no, dur in press_log:
    flag = "  ⚠️ FREEZE" if dur > 2.0 else ""
    log(f"  Start '{order_no}': {dur:.2f}s{flag}")

log("THREAD SAMPLES (last 10):")
for ts, n, names in thread_samples[-10:]:
    log(f"  t={ts - thread_samples[0][0]:6.1f}s workers={n} {names}")


