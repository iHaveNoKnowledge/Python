"""
Mock SMCO server สำหรับ GUI verification ของ autopage_MKII_ver5.x.x.py
- ให้บริการหน้า POS (pos_page.html) จาก tests/mock_smco/assets/
- ตอบ endpoint /smartcore/... แบบ static เพื่อไม่ให้ request ใดพัง
รันสั้นๆ: python tests/mock_smco/mock_smco_server.py
"""

import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler, SimpleHTTPRequestHandler

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


class MockSmcoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def translate_path(self, path):
        # ทุก path ที่ลงท้าย .htm หรือ .html ให้เสิร์ฟ pos_page.html (หน้าเดียวเอา )
        if path.endswith(".htm") or path.endswith(".html") or path == "/":
            return os.path.join(ROOT, "pos_page.html")
        return super().translate_path(path)

    def do_POST(self):
        # ทุก POST (getCustomerSearchPOS/selectoption.htm, loginssoauthen.htm, ...)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "mock": true}')

    def log_message(self, format, *args):
        sys.stdout.write("[MOCK] " + format % args + "\n")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = HTTPServer(("127.0.0.1", port), MockSmcoHandler)
    print(f"Mock SMCO server listening on http://127.0.0.1:{port}")
    sys.stdout.flush()
    server.serve_forever()


if __name__ == "__main__":
    main()
