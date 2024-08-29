import subprocess
import os
import glob
import winreg
import psutil
import requests
from requests.adapters import HTTPAdapter, Retry


class CustomChrome:
    def __init__(self, port: int = None):
        self.port = port
        self.chrome_exe = self.find_chrome_exe_by_winreg()
        if not self.is_chrome_running():
            self.open_custom_browser()
        # raise RuntimeError("Stop class execution")

    def is_chrome_running(self):
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == 'chrome.exe':
                if self.is_chrome_debugging():
                    print(f"chrome.exe debugging port {self.port} is running")
                    return True
        print(f"chrome.exe debugging port {self.port} is not running")
        return False

    def is_chrome_debugging(self):
        self.s = requests.Session()
        self.retries = Retry(
            total=0,
            backoff_factor=0,
            status_forcelist=[500, 502, 503, 504],
            connect=0,
            read=0,
            redirect=0,
            status=0,
            raise_on_status=False,
        )
        self.adapter = HTTPAdapter(max_retries=self.retries)
        self.s.mount(f'http://', self.adapter)
        self.s.mount(f'https://', self.adapter)

        try:
            self.response = self.s.get(f'http://localhost:{self.port}', timeout=0.125, allow_redirects=False )
            self.response.raise_for_status()
            return self.response.status_code == 200
        except requests.exceptions.RequestException as err:
            print("request: ", err)
            return False
        
    def open_custom_browser(self):
        try:
            subprocess.Popen([
                f"{self.chrome_exe}",
                "--user-data-dir=C:/bin/chromeProfile",
                f"--remote-debugging-port={self.port}"
            ])
        except ValueError as err:
            raise ValueError("Error found:", err)

    def find_chrome_exe_common_path(self):
        search_paths = [
            "C:/Program Files/Google/Chrome/Application/",
            "C:/Program Files (x86)/Google/Chrome/Appplication/"
        ]

        for path in search_paths:
            files = glob.glob(os.path.join(path, "chrome.exe"))
            if files:
                print("เจอไฟล์: ", files)
                return files[0]  # * Return path

        return None  # * ถ้าไม่เจอก็ลงมานี่

    def find_chrome_exe_all_path(self):
        for root, dirs, files in os.walk("c:/"):
            if "chrome.exe" in files:
                return os.path.join(root, "chrome.exe")

    def find_chrome_exe_by_winreg(self):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
                print("key", key)  # * เก็บ key มา
                # * เอา key ไปดึงค่า value ซึ่งจะคืนค่าเป็น str ที่เป็น path ของ chrome.exe นี่เอง
                return winreg.QueryValue(key, None)
        except FileNotFoundError:
            return None

    def find_chrome_exe(self):
        chrome_path = self.find_chrome_exe_common_path()
        if chrome_path:
            return chrome_path
        else:
            self.find_chrome_exe_all_path()
            return None


# custom_chrome = CustomChrome(8989)
