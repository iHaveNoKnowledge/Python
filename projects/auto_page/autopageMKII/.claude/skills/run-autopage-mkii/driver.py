"""
Driver for autopageMKII (Tkinter + Selenium bot) - agent-side harness.

What it does
  serve : starts the REAL GUI (autopage_MKII_ver5.x.x.py -> MyApp) in this process,
          against a mock SMCO site (127.0.0.1:8765) and a dedicated Chrome on
          remote-debugging port 8990. External calls (marketplace scrape, vatinfo)
          are stubbed. Then listens on a local control socket (127.0.0.1:8791)
          and runs every command on the Tk main thread.
  send  : one-shot client: `python driver.py send "<command>"` -> prints the reply.

Commands (send them with `send`):
  ss [path]          screenshot of the app window (raised to topmost first)
  ssfull [path]      full-desktop screenshot (includes popups like Login)
  state              JSON: order input, bot status, test mode, data rows, threads
  import [xlsx]      simulate the Import button (default: mock Shopee fixture)
  type <attr> <txt>  replace text of a CTk entry attribute, e.g. type inp1_order_input 2609032XS86R91
  click <attr>       invoke a button attribute, e.g. click inp1_search_btn (= Start)
  pump [seconds]     keep the Tk loop running for N seconds (default 2)
  eval <expr>        evaluate python in {app, root, mod}; prints repr
  dialogs            JSON list of messageboxes the driver auto-answered
  quit               destroy the window and stop the test Chrome this driver started

Safety
  * Refuses to start while 127.0.0.1:8989 (the LIVE bot's Chrome) is listening, unless
    --allow-live-bot. The driver never attaches to 8989.
  * setup_chrome is patched to 8990 BEFORE MyApp() is constructed (MyApp attaches to
    8989 by default otherwise).
  * The app's SMCO session lives in the Windows keyring under service AutoSamaticMKII.
    The driver points AccountManager at AutoSamaticMKII-driver so it cannot read or
    clear the production session.
  * messageboxes are auto-answered (askyesno-style -> No) and logged; see `dialogs`.
  * Tk thread watchdog: if the GUI thread is silent >10s, every thread's stack is
    written to %TEMP%\\autopage-driver\\stack_dump.txt.

Options
  serve --allow-live-bot       run while the live bot's Chrome is up
  serve --target-url <url>     use another SMCO base URL instead of the local mock
"""

import argparse
import importlib.util
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from http.server import HTTPServer

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
UNIT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))  # <unit>/.claude/skills/<name>/driver.py
APP_PATH = os.path.join(UNIT, "autopage_MKII_ver5.x.x.py")
TESTS_MOCK = os.path.join(UNIT, "tests", "mock_smco")
MOCK_SERVER_PY = os.path.join(TESTS_MOCK, "mock_smco_server.py")
DEFAULT_XLSX = os.path.join(TESTS_MOCK, "mock_smco", "fixtures", "mock_orders.xlsx")
SCRATCH = os.path.join(tempfile.gettempdir(), "autopage-driver")

MOCK_PORT = 8765
CHROME_PORT = 8990      # test Chrome. NEVER 8989 (live bot).
LIVE_BOT_PORT = 8989
CONTROL_PORT = 8791
PROFILE_DIR = os.path.join(SCRATCH, "chrome-profile")
KEYRING_SERVICE = "AutoSamaticMKII-driver"   # production uses "AutoSamaticMKII"; never share it
STACK_DUMP = os.path.join(SCRATCH, "stack_dump.txt")
DIALOG_LOG = []   # every auto-answered messagebox, read with `dialogs`


def _port_open(port, host="127.0.0.1", timeout=0.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_port(port, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if _port_open(port):
            return True
        time.sleep(0.25)
    return False


# ----------------------------------------------------------------------
# serve
# ----------------------------------------------------------------------
def serve(args):
    global CHROME_PORT
    CHROME_PORT = args.chrome_port
    if CHROME_PORT == LIVE_BOT_PORT:
        # Attach to a browser the user already has open and logged in on 8989 (UAT).
        # The driver never launches or closes it.
        if not _port_open(LIVE_BOT_PORT):
            print("REFUSED: --chrome-port 8989 but nothing listens there. Open the browser with "
                  "remote debugging on 8989 first.")
            return 2
    elif _port_open(LIVE_BOT_PORT) and not args.allow_live_bot:
        print(f"REFUSED: 127.0.0.1:{LIVE_BOT_PORT} is listening (live bot Chrome). "
              "The driver never attaches to it, but the GUI start-up reads and can clear the "
              "shared keyring session (service AutoSamaticMKII). Stop the live bot, or re-run "
              "with --allow-live-bot if you accept that.")
        return 2
    if _port_open(CONTROL_PORT):
        print(f"REFUSED: control port {CONTROL_PORT} already in use - driver already running?")
        return 2

    os.makedirs(SCRATCH, exist_ok=True)
    os.makedirs(PROFILE_DIR, exist_ok=True)
    os.chdir(UNIT)                       # app loads assets/ with relative paths
    sys.path.insert(0, UNIT)

    # 1) SMCO site: a real test server if --target-url is given (e.g. UAT), else the local mock
    httpd = None
    if args.target_url:
        base_url = args.target_url.rstrip("/")
        print(f"[driver] target SMCO = {base_url} (no mock started)", flush=True)
    else:
        spec_m = importlib.util.spec_from_file_location("mock_smco_server", MOCK_SERVER_PY)
        mock_mod = importlib.util.module_from_spec(spec_m)
        spec_m.loader.exec_module(mock_mod)
        httpd = HTTPServer(("127.0.0.1", MOCK_PORT), mock_mod.MockSmcoHandler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base_url = MOCK_URL()
        print(f"[driver] mock SMCO on {base_url}", flush=True)

    # 2) dedicated Chrome on the test port
    chrome_proc = None
    if not _port_open(CHROME_PORT):
        if CHROME_PORT == LIVE_BOT_PORT:
            print("REFUSED: port 8989 closed while starting")
            return 2
        chrome = next((p for p in (
            shutil.which("chrome"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ) if p and os.path.exists(p)), None)
        if not chrome:
            print("ERROR: Chrome not found")
            return 2
        chrome_proc = subprocess.Popen([
            chrome, f"--remote-debugging-port={CHROME_PORT}",
            f"--user-data-dir={PROFILE_DIR}", "--no-first-run",
            "--no-default-browser-check", "--disable-popup-blocking",
            "--remote-allow-origins=*", f"{base_url}/smartcore/smartpos/pointofsales/posmainv3.htm",
        ])
        if not _wait_port(CHROME_PORT, 40):
            print(f"ERROR: Chrome debug port {CHROME_PORT} did not open")
            return 2
    print(f"[driver] attached to Chrome on :{CHROME_PORT}"
          + (" (user's browser, not launched by driver)" if CHROME_PORT == LIVE_BOT_PORT else ""),
          flush=True)

    # 3) patch BEFORE the app is constructed
    from selenium import webdriver
    from functions.browser_manager import BrowserManager
    from functions.marketplace_scraper import MarketplaceOrderResult

    def _attach_test_chrome(self):
        opt = webdriver.ChromeOptions()
        opt.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        opt.add_experimental_option("debuggerAddress", f"localhost:{CHROME_PORT}")
        opt.add_argument("--disable-popup-blocking")
        return webdriver.Chrome(options=opt)

    BrowserManager.setup_chrome = _attach_test_chrome

    # Modal messageboxes block the Tk thread forever (nobody clicks them), so answer them
    # here and log each one. askyesno-style questions default to NO: a harness run must
    # never confirm writes such as "เพิ่ม CP Data" into the real cp_data.xlsx.
    from tkinter import messagebox as _mb

    def _auto_dialog(kind, default):
        def _answer(title=None, message=None, **_kw):
            DIALOG_LOG.append({"kind": kind, "title": str(title),
                               "message": str(message)[:300], "answer": repr(default)})
            return default
        return _answer

    _mb.askyesno = _auto_dialog("askyesno", False)
    _mb.askokcancel = _auto_dialog("askokcancel", False)
    _mb.askyesnocancel = _auto_dialog("askyesnocancel", None)
    _mb.askretrycancel = _auto_dialog("askretrycancel", False)
    _mb.showinfo = _auto_dialog("showinfo", "ok")
    _mb.showwarning = _auto_dialog("showwarning", "ok")
    _mb.showerror = _auto_dialog("showerror", "ok")

    # Keyring isolation: the app keeps its SMCO session in the Windows keyring under
    # service "AutoSamaticMKII" (shared with the production bot). Point the default at a
    # driver-only service so start-up can never read or clear the real session.
    from functions.utils import crypto as _crypto
    _crypto.AccountManager.__init__.__defaults__ = (KEYRING_SERVICE,)

    # 4) load the real app module (same as `python autopage_MKII_ver5.x.x.py`,
    #    minus the __main__ block) and build the real MyApp
    spec = importlib.util.spec_from_file_location("autopage_gui", APP_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["autopage_gui"] = mod
    spec.loader.exec_module(mod)
    if not hasattr(mod, "_onKeyRelease"):   # defined only under __main__ in the app
        mod._onKeyRelease = lambda event: None

    root = mod.CTk()
    app = mod.MyApp(root)

    # 5) stub the only things that reach the internet
    def _fake_scrape(order_no, marketplace):
        return MarketplaceOrderResult(order_no=order_no, marketplace=marketplace,
                                      status="READY_TO_SHIP")

    app.bot.marketplace_scraper.scrape_order = _fake_scrape
    app.bot.get_vatinfo_data = lambda tax_num, branch: {
        "name": app.cus_name.get(), "brano": branch or "00000"}
    print("[driver] GUI built; stubs installed", flush=True)

    # 6) control socket -> Tk main thread
    cmd_q = queue.Queue()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", CONTROL_PORT))
    server.listen(4)

    def _conn_loop():
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            threading.Thread(target=_handle_conn, args=(conn,), daemon=True).start()

    def _handle_conn(conn):
        try:
            conn.settimeout(10)
            line = conn.makefile("r", encoding="utf-8").readline().strip()
            if not line:
                return
            box, done = [], threading.Event()
            cmd_q.put((line, box, done))
            done.wait(120)
            conn.sendall(((box[0] if box else "TIMEOUT: no reply from Tk thread") + "\n").encode("utf-8"))
        except Exception as e:
            try:
                conn.sendall(f"ERROR: {e}\n".encode("utf-8"))
            except Exception:
                pass
        finally:
            conn.close()

    threading.Thread(target=_conn_loop, daemon=True).start()

    # 7) command dispatcher on the Tk thread
    def _shot(bbox_mode, path):
        # ImageGrab copies screen pixels, not the window: raise the app above whatever is
        # on top of it (editor, browser...) or the PNG shows the wrong window.
        from PIL import ImageGrab
        root.attributes("-topmost", True)
        root.lift()
        try:
            root.focus_force()
        except Exception:
            pass
        end = time.time() + 0.6          # let the window manager repaint
        while time.time() < end:
            root.update()
            time.sleep(0.05)
        try:
            if bbox_mode == "full":
                img = ImageGrab.grab()
            else:
                x, y = root.winfo_rootx(), root.winfo_rooty()
                img = ImageGrab.grab(bbox=(x, y, x + root.winfo_width(), y + root.winfo_height()))
            img.save(path)
        finally:
            root.attributes("-topmost", False)
        return path

    def _state():
        def _safe(fn):
            try:
                return fn()
            except Exception as e:
                return f"<{type(e).__name__}: {e}>"
        return {
            "order_input": _safe(lambda: app.inp1_order_input.get()),
            "bot_status": _safe(lambda: app.display_bot_status_label.cget("text")),
            "is_testing": _safe(lambda: bool(app.is_testing)),
            "test_checkpoint": _safe(lambda: app.test_checkpoint.get()),
            "result": _safe(lambda: app.result),
            "table_location": _safe(lambda: os.path.basename(str(app.table_location))),
            "data_rows": _safe(lambda: len(app.data_frame)),
            "threads": sorted(t.name for t in threading.enumerate()),
        }

    def _dispatch(line):
        verb, _, rest = line.partition(" ")
        rest = rest.strip()
        if verb == "ss":
            return _shot("window", rest or os.path.join(SCRATCH, "app.png"))
        if verb == "ssfull":
            return _shot("full", rest or os.path.join(SCRATCH, "desktop.png"))
        if verb == "state":
            return json.dumps(_state(), ensure_ascii=False, indent=2)
        if verb == "dialogs":
            return json.dumps(DIALOG_LOG, ensure_ascii=False, indent=2) or "[]"
        if verb == "import":
            path = rest or DEFAULT_XLSX
            app.result = "Excel"
            app.table_location = path
            app.marketplace_target.set("SHOPEE")
            app.get_data_frame()
            return f"imported {os.path.basename(path)} rows={len(app.data_frame)}"
        if verb == "type":
            attr, _, text = rest.partition(" ")
            w = getattr(app, attr)
            w.delete(0, "end")
            w.insert(0, text)
            return f"typed into {attr}"
        if verb == "click":
            getattr(app, rest).invoke()
            return f"invoked {rest}"
        if verb == "pump":
            end = time.time() + float(rest or 2)
            while time.time() < end:
                root.update()
                time.sleep(0.05)
            return "pumped"
        if verb == "eval":
            return repr(eval(rest, {"app": app, "root": root, "mod": mod}))
        if verb == "exec":
            # multi-statement python on the Tk thread; put the reply in `result`
            ns = {"app": app, "root": root, "mod": mod, "time": time, "result": None}
            exec(rest, ns)
            return repr(ns.get("result"))
        if verb == "quit":
            root.after(50, root.destroy)
            return "bye"
        return f"unknown command: {verb!r}"

    # Watchdog: if the Tk thread stops calling _poll for >10s it is blocked (modal dialog,
    # long loop, deadlock). Dump every thread's stack to STACK_DUMP so the hang can be read.
    heartbeat = {"t": time.time()}

    def _watchdog():
        dumped = False
        while True:
            time.sleep(2)
            stale = time.time() - heartbeat["t"]
            if stale > 10 and not dumped:
                with open(STACK_DUMP, "w", encoding="utf-8") as f:
                    f.write(f"Tk thread silent for {stale:.0f}s. Thread stacks:\n")
                    for tid, frame in sys._current_frames().items():
                        f.write(f"\n--- thread {tid} ---\n")
                        f.write("".join(traceback.format_stack(frame)))
                dumped = True
            elif stale <= 10:
                dumped = False

    threading.Thread(target=_watchdog, daemon=True).start()

    def _poll():
        heartbeat["t"] = time.time()
        try:
            while True:
                line, box, done = cmd_q.get_nowait()
                try:
                    box.append(_dispatch(line))
                except Exception as e:
                    tb = traceback.format_exc().strip().splitlines()[-1]
                    box.append(f"ERROR: {type(e).__name__}: {e} ({tb})")
                done.set()
        except queue.Empty:
            pass
        root.after(100, _poll)

    root.after(100, _poll)
    print(f"[driver] control socket on 127.0.0.1:{CONTROL_PORT} - use: python driver.py send \"state\"", flush=True)
    try:
        root.mainloop()
    finally:
        try:
            server.close()
        except Exception:
            pass
        if chrome_proc and chrome_proc.poll() is None:
            chrome_proc.terminate()
        if httpd:
            httpd.shutdown()
    print("[driver] stopped", flush=True)
    return 0


def MOCK_URL():
    return f"http://127.0.0.1:{MOCK_PORT}"


# ----------------------------------------------------------------------
# send
# ----------------------------------------------------------------------
def send(args):
    try:
        s = socket.create_connection(("127.0.0.1", CONTROL_PORT), timeout=3)
    except OSError:
        print("driver not reachable on 127.0.0.1:%d. Not started, OR its Tk thread is busy and "
              "the accept backlog is full. Check %s, then start it with: "
              "python driver.py serve" % (CONTROL_PORT, STACK_DUMP))
        return 2
    s.settimeout(150)
    s.sendall((args.command + "\n").encode("utf-8"))
    buf = b""
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
    s.close()
    sys.stdout.buffer.write(buf)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    svp = sub.add_parser("serve", help="start the GUI + control socket (blocks)")
    svp.add_argument("--allow-live-bot", action="store_true",
                     help="run even though 127.0.0.1:8989 (live bot Chrome) is listening")
    svp.add_argument("--chrome-port", type=int, default=CHROME_PORT,
                     help="Chrome debug port to attach to. 8990 (default) = driver-launched test "
                          "Chrome. 8989 = a browser the user already has open and logged in (UAT); "
                          "the driver attaches but never launches or closes it.")
    svp.add_argument("--target-url", default=None,
                     help="test SMCO base URL (e.g. http://192.168.0.142:9099 = UAT). "
                          "Default: local mock on 127.0.0.1:8765")
    sp = sub.add_parser("send", help="send one command to a running driver")
    sp.add_argument("command")
    args = p.parse_args()
    if args.cmd == "serve":
        return serve(args)
    return send(args)


if __name__ == "__main__":
    sys.exit(main())
