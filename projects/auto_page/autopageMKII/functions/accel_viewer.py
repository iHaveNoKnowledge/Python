"""หน้าต่างดูผลการออกบิลจากชีต Processed_Logs ของไฟล์ Accel (อ่านอย่างเดียว)

- ไม่เขียนไฟล์ อ่านด้วย pandas เท่านั้น จึงไม่มีความเสี่ยงไฟล์เสียจากหน้านี้
- โหลดใหม่อัตโนมัติเมื่อ mtime/ขนาดไฟล์เปลี่ยน (บอทบันทึกใหม่)
- ค้นหาได้ทุกคอลัมน์ และเรียงลำดับโดยคลิกหัวคอลัมน์
- ลากเลือกช่องแบบตาราง แล้ว Ctrl+C คัดลอกเป็นข้อความแยกด้วย tab (วางใน Excel แยกช่องได้)
- หน้าต่างไม่ใช้ grab_set / topmost เพื่อให้ใช้หน้าหลักได้ตามปกติ
"""
import bisect
import os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import messagebox

import customtkinter as ctk
import pandas as pd

SHEET_NAME = "Processed_Logs"
COLUMNS = ["timestamp", "tracking", "orders", "bill_no", "price",
           "sn", "status", "error_category", "remark"]
# ความกว้างการแสดงผลต่อคอลัมน์ (จำนวนตัวอักษร) — เฉพาะการแสดงผล ค่าที่ copy เป็นค่าเต็มเสมอ
DISPLAY_WIDTHS = [19, 16, 14, 14, 10, 30, 14, 18, 30]
POLL_MS = 1500

BG = "#ffffff"
HEADER_BG = "#eef2f6"
SEL_BG = "#cce5ff"
ERR_FG = "#b00020"
VK_C = 67  # keycode ของปุ่ม C บน Windows (ใช้ได้กับ layout ไทยด้วย)
VK_A = 65  # keycode ของปุ่ม A บน Windows


# ---------- ฟังก์ชันล้วน (ทดสอบได้โดยไม่ต้องเปิด GUI) ----------

def _cell(value) -> str:
    return "" if value is None else str(value)


def load_processed_logs(path: str):
    """อ่านชีต Processed_Logs คืน list ของแถว (list[str]) ตามลำดับ COLUMNS
    คอลัมน์ที่ไม่มีในไฟล์จะเป็นค่าว่าง ค่าว่างใน Excel เป็น '' (ไม่ใช่ 'nan')"""
    df = pd.read_excel(path, sheet_name=SHEET_NAME, dtype=str, keep_default_na=False)
    df.columns = [str(c).strip() for c in df.columns]
    return [[_cell(rec.get(col, "")) for col in COLUMNS] for rec in df.to_dict("records")]


def filter_rows(rows, query: str):
    """กรองแถวที่มี substring ของ query ในค่าคอลัมน์ใดก็ได้ (ไม่สนตัวพิมพ์)"""
    q = (query or "").strip().lower()
    if not q:
        return list(rows)
    return [r for r in rows if any(q in c.lower() for c in r)]


def _sort_key(text: str):
    s = text.strip()
    try:
        return (0, float(s.replace(",", "")), "")
    except ValueError:
        return (1, 0.0, s.lower())


def sort_rows(rows, col: int, asc: bool = True):
    """เรียงตามคอลัมน์ col; ค่าว่างอยู่ท้ายเสมอ; ตัวเลขเรียงเป็นตัวเลข"""
    filled = [r for r in rows if r[col].strip()]
    empty = [r for r in rows if not r[col].strip()]
    filled.sort(key=lambda r: _sort_key(r[col]), reverse=not asc)
    return filled + empty


def _tsv_clean(text: str) -> str:
    return text.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def cells_to_tsv(rows, r0: int, r1: int, c0: int, c1: int) -> str:
    """ข้อความของช่วงสี่เหลี่ยม (แถว r0..r1, คอลัมน์ c0..c1 รวมทั้งสองปลาย) แยกด้วย tab/ขึ้นบรรทัดใหม่"""
    return "\n".join(
        "\t".join(_tsv_clean(rows[r][c]) for c in range(c0, c1 + 1))
        for r in range(r0, r1 + 1))


def _display(text: str, width: int) -> str:
    """ตัดข้อความให้พอดีความกว้างคอลัมน์ (ต้องสั้นกว่า tab stop เสมอ ไม่งั้นคอลัมน์จะเลื่อน)"""
    text = _tsv_clean(text)
    limit = max(width - 2, 1)
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


# ---------- หน้าต่าง ----------

_window = None  # singleton: เปิดซ้ำจะยกหน้าต่างเดิมขึ้นมา


def _alive(win) -> bool:
    try:
        return bool(win.winfo_exists())
    except tk.TclError:
        return False


def _resolve_path(app) -> str:
    accel = getattr(app, "accel_mode", None)
    return getattr(accel, "accel_file_dir", "") or ""


def _save_failed(app) -> bool:
    accel = getattr(app, "accel_mode", None)
    return bool(getattr(accel, "excel_save_failed", False))


def open_accel_viewer_window(app):
    global _window
    if _window is not None and _alive(_window):
        _window.lift()
        return

    path = _resolve_path(app)
    if not path:
        messagebox.showwarning("Accel", "ยังไม่ได้เลือกไฟล์ Accel")
        return
    if not os.path.exists(path):
        messagebox.showerror("Accel", f"ไม่พบไฟล์ Accel: {path}")
        return
    try:
        rows = load_processed_logs(path)
    except Exception as e:
        messagebox.showerror("Accel", f"อ่านชีต {SHEET_NAME} ไม่ได้ (อาจกำลังถูกเขียนหรือเปิดค้าง): {e}")
        return

    win = ctk.CTkToplevel(app.root if hasattr(app, "root") else app)
    win.title(f"Accel - {SHEET_NAME} (ดูอย่างเดียว)")
    win.geometry("1180x600")
    win.configure(fg_color=BG)
    _window = win

    state = {
        "all_rows": rows,
        "view": [],
        "sort_col": None,
        "asc": True,
        "anchor": None,
        "focus": None,
        "mtime_key": None,
        "offsets": [],   # offsets[view_row] = [(start, end)] ต่อคอลัมน์ ในข้อความของ Text
        "header_starts": [],
        "status": "",
    }
    _remember_mtime(path, state)

    banner = ctk.CTkLabel(win, text="", text_color=ERR_FG, font=("tahoma", 11, "bold"), anchor="w")
    banner.pack(fill="x", padx=10, pady=(6, 0))

    search_var = tk.StringVar(master=win)
    search_entry = ctk.CTkEntry(win, textvariable=search_var, placeholder_text="ค้นหาทุกคอลัมน์…")
    search_entry.pack(fill="x", padx=10, pady=6)

    mono = tkfont.Font(family="Consolas", size=10)
    bold = tkfont.Font(family="Consolas", size=10, weight="bold")
    char_px = mono.measure("0")
    tab_stops = []
    total = 0
    for w in DISPLAY_WIDTHS:
        total += w
        tab_stops.append(total * char_px)

    body_frame = tk.Frame(win, bg=BG)
    body_frame.pack(fill="both", expand=True, padx=10)
    yscroll = tk.Scrollbar(body_frame, orient="vertical")
    xscroll = tk.Scrollbar(body_frame, orient="horizontal")
    text = tk.Text(body_frame, font=mono, wrap="none", bg=BG, bd=0, highlightthickness=0,
                   tabs=tab_stops, cursor="arrow", state="disabled", takefocus=0,
                   yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
    yscroll.config(command=text.yview)
    xscroll.config(command=text.xview)
    yscroll.pack(side="right", fill="y")
    xscroll.pack(side="bottom", fill="x")
    text.pack(side="left", fill="both", expand=True)
    text.tag_configure("hdr", font=bold, background=HEADER_BG)
    text.tag_configure("sel", background=SEL_BG)

    footer = ctk.CTkLabel(win, text="", text_color="#444444", font=("tahoma", 10), anchor="w")
    footer.pack(fill="x", padx=10, pady=4)

    def _cell_at(event):
        """คืน (view_row, col) ของตำแหน่งเมาส์ หรือ None ถ้าไม่ใช่ช่องข้อมูล"""
        idx = text.index(f"@{event.x},{event.y}")
        line, ch = (int(p) for p in idx.split("."))
        row = line - 2
        if row < 0 or row >= len(state["view"]):
            return None
        spans = state["offsets"][row]
        starts = [s for s, _ in spans]
        col = bisect.bisect_right(starts, ch) - 1
        return (row, max(0, min(col, len(COLUMNS) - 1)))

    def _header_col_at(event):
        idx = text.index(f"@{event.x},{event.y}")
        line, ch = (int(p) for p in idx.split("."))
        if line != 1:
            return None
        # offset จริงของแต่ละหัวคอลัมน์ในบรรทัดที่ 1 (ความยาวหัวไม่เท่ากันจึงคำนวณจากความกว้างไม่ได้)
        starts = state["header_starts"]
        return max(0, min(bisect.bisect_right(starts, ch) - 1, len(COLUMNS) - 1))

    def _draw_selection():
        text.tag_remove("sel", "1.0", "end")
        a, f = state["anchor"], state["focus"]
        if a is None or f is None or not state["view"]:
            return
        r0, r1 = sorted((a[0], f[0]))
        c0, c1 = sorted((a[1], f[1]))
        for r in range(r0, r1 + 1):
            s = state["offsets"][r][c0][0]
            e = state["offsets"][r][c1][1]
            text.tag_add("sel", f"{r + 2}.{s}", f"{r + 2}.{e}")

    def _render():
        filtered = filter_rows(state["all_rows"], search_var.get())
        if state["sort_col"] is not None:
            filtered = sort_rows(filtered, state["sort_col"], state["asc"])
        state["view"] = filtered
        state["anchor"] = state["focus"] = None

        header_parts = []
        for i, name in enumerate(COLUMNS):
            label = name
            if state["sort_col"] == i:
                label += " ▲" if state["asc"] else " ▼"
            header_parts.append(_display(label, DISPLAY_WIDTHS[i]))

        lines = ["\t".join(header_parts)]
        header_starts, pos = [], 0
        for part in header_parts:
            header_starts.append(pos)
            pos += len(part) + 1  # +1 สำหรับ tab
        state["header_starts"] = header_starts
        state["offsets"] = []
        for r in filtered:
            parts = []
            spans = []
            pos = 0
            for i, value in enumerate(r):
                shown = _display(value, DISPLAY_WIDTHS[i])
                spans.append((pos, pos + len(shown)))
                parts.append(shown)
                pos += len(shown) + 1  # +1 สำหรับ tab
            state["offsets"].append(spans)
            lines.append("\t".join(parts))
        if not filtered:
            lines.append("ไม่พบข้อมูลที่ค้นหา" if state["all_rows"] else "ไม่มีข้อมูลในชีต")

        text.config(state="normal")
        text.delete("1.0", "end")
        text.insert("1.0", "\n".join(lines))
        text.tag_add("hdr", "1.0", "1.end")
        text.config(state="disabled")

        banner.configure(text=(
            "⚠ ข้อมูลล่าสุดยังไม่ถูกบันทึกลงไฟล์ (ปิดไฟล์ Accel ใน Excel แล้วระบบจะบันทึกรอบถัดไป)"
            if _save_failed(app) else ""))
        footer.configure(text=(
            f"แสดง {len(filtered)}/{len(state['all_rows'])} แถว  |  {state['status']}  |  "
            f"{os.path.basename(_resolve_path(app))}"))

    def _on_header_click(event):
        col = _header_col_at(event)
        if col is None:
            return "break"
        if state["sort_col"] == col:
            state["asc"] = not state["asc"]
        else:
            state["sort_col"], state["asc"] = col, True
        _render()
        return "break"

    def _on_press(event):
        text.focus_set()
        if _header_col_at(event) is not None:
            # บรรทัดหัวตาราง: คลิก = เรียง (ต้องจัดการที่นี่ เพราะ "break" จะตัด tag binding)
            return _on_header_click(event)
        cell = _cell_at(event)
        if cell is None:
            return "break"
        state["anchor"] = state["focus"] = cell
        _draw_selection()
        return "break"

    def _on_drag(event):
        cell = _cell_at(event)
        if cell is not None and state["anchor"] is not None:
            state["focus"] = cell
            _draw_selection()
        return "break"

    def _copy_selection(_event=None):
        a, f = state["anchor"], state["focus"]
        if a is None or f is None:
            return "break"
        r0, r1 = sorted((a[0], f[0]))
        c0, c1 = sorted((a[1], f[1]))
        tsv = cells_to_tsv(state["view"], r0, r1, c0, c1)
        win.clipboard_clear()
        win.clipboard_append(tsv)
        state["status"] = f"คัดลอกแล้ว {r1 - r0 + 1} แถว × {c1 - c0 + 1} คอลัมน์"
        footer.configure(text=(
            f"แสดง {len(state['view'])}/{len(state['all_rows'])} แถว  |  {state['status']}  |  "
            f"{os.path.basename(_resolve_path(app))}"))
        return "break"

    def _select_all(_event=None):
        if not state["view"]:
            return "break"
        state["anchor"] = (0, 0)
        state["focus"] = (len(state["view"]) - 1, len(COLUMNS) - 1)
        _draw_selection()
        return "break"

    def _on_key(event):
        # ใช้ keycode แทน keysym เพื่อให้ Ctrl+C / Ctrl+A ทำงานกับ layout ไทยด้วย
        if event.keycode == VK_C:
            return _copy_selection()
        if event.keycode == VK_A:
            return _select_all()
        return None

    text.bind("<Button-1>", _on_press)
    text.bind("<B1-Motion>", _on_drag)
    text.bind("<Control-KeyPress>", _on_key)
    search_var.trace_add("write", lambda *_: _render())

    def _reload_if_changed():
        if not win.winfo_exists():
            return
        current = _resolve_path(app)
        key = _file_key(current)
        if key is not None and key != state["mtime_key"]:
            try:
                state["all_rows"] = load_processed_logs(current)
                state["mtime_key"] = key
                state["status"] = "โหลดข้อมูลใหม่แล้ว"
                _render()
            except Exception as e:
                state["status"] = f"อ่านข้อมูลใหม่ไม่ได้ ใช้ข้อมูลเดิม ({e.__class__.__name__})"
                _render()
        else:
            # อัปเดตแถบเตือนการบันทึกแม้ไฟล์ไม่เปลี่ยน
            banner.configure(text=(
                "⚠ ข้อมูลล่าสุดยังไม่ถูกบันทึกลงไฟล์ (ปิดไฟล์ Accel ใน Excel แล้วระบบจะบันทึกรอบถัดไป)"
                if _save_failed(app) else ""))
        state["after_id"] = win.after(POLL_MS, _reload_if_changed)

    def _close():
        global _window
        _window = None
        if state.get("after_id"):
            win.after_cancel(state["after_id"])
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", _close)
    _render()
    state["after_id"] = win.after(POLL_MS, _reload_if_changed)
    text.focus_set()


def _file_key(path: str):
    try:
        st = os.stat(path)
        return (st.st_mtime, st.st_size)
    except OSError:
        return None


def _remember_mtime(path: str, state: dict) -> None:
    state["mtime_key"] = _file_key(path)
