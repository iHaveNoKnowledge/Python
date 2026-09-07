import sys, time, subprocess, os, re

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_KEY = "chrome_profile"  # ชื่อ profile dir ของการทดสอบเท่านั้น

os.system("taskkill /F /IM chromedriver.exe >nul 2>&1")


def kill_test_chromes():
    """kill เฉพาะ chrome.exe ที่โหลด --user-data-dir ของ profile ทดสอบ
    (ไม่แตะต้อง chrome ของ user ปกติที่ไม่มี flag นี้)"""
    killed = []
    try:
        import psutil
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if p.info["name"] and "chrome" not in p.info["name"].lower():
                    continue
                cl = " ".join(p.info["cmdline"] or [])
                if PROFILE_KEY in cl:
                    p.kill()
                    killed.append(p.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        # fallback: PowerShell (wmic ไม่มีแล้วบน Windows ใหม่)
        cmd = ("Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | "
               "Where-Object { $_.CommandLine -like '*" + PROFILE_KEY + "*' } | "
               "Select-Object -ExpandProperty ProcessId")
        out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                             capture_output=True, text=True, timeout=20).stdout
        for line in out.splitlines():
            if line.strip().isdigit():
                os.system(f"taskkill /F /PID {line.strip()} >nul 2>&1")
                killed.append(line.strip())
    print("killed test chromes:", killed or "none")


kill_test_chromes()
time.sleep(2)

DRIVER = os.path.expandvars(
    r"%USERPROFILE%\.cache\selenium\chromedriver\win64\152.0.7977.82\chromedriver.exe")
print("driver exists:", os.path.exists(DRIVER))

profile = os.path.join(TESTS_DIR, ".chrome_profile3")
proc = subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--remote-debugging-port=8989", f"--user-data-dir={profile}",
    "--no-first-run", "--no-default-browser-check", "--remote-allow-origins=*",
    "--disable-popup-blocking", "about:blank"])
time.sleep(6)

ok = False
for attempt in (1, 2, 3):
    try:
        opts = webdriver.ChromeOptions()
        opts.add_experimental_option("debuggerAddress", "localhost:8989")
        d = webdriver.Chrome(service=Service(DRIVER), options=opts)
        print("ATTACH OK with explicit 152.0.7977.82, title:", d.title)
        d.quit()
        ok = True
        break
    except Exception as e:
        print(f"attempt {attempt} FAILED: {str(e).splitlines()[0]}")
        time.sleep(3)
if not ok:
    print("ALL FAILED")
time.sleep(1)
proc.terminate()
