"""
Phase 1-3: read/edit SKU pattern list from cp_data (groupby sku).
Complete pattern = แถวที่ใส่ cp_name + usage_start_date + usage_end_date ครบ
Page 1 (SKU list) -> Page 2 (price list ของ SKU) -> Page 3 (รายละเอียด pattern ของราคานั้น, CRUD)
"""
import os
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import cast

import customtkinter as ctk
import pandas as pd
from openpyxl import load_workbook
from openpyxl.cell.cell import Cell

LINK_COLOR = "#1a6fd4"
BG = "#ffffff"
HEADER_BG = "#ececec"
LINE = "#dcdcdc"
OK_COLOR = "#1e7e34"
BAD_COLOR = "#b02a37"
INPUT_BORDER = "#94e61d"

_LINK_FONT = ("tahoma", 11, "underline")

EDITOR_COLS = [
    "sku", "sale_price",
    "cp_name", "usage_start_date", "usage_end_date", "oc_amount", "dc_amount",
    "suggested_cp", "suggested_usage_start_date", "suggested_usage_end_date",
    "suggested_oc_amount", "suggested_dc_amount", "suggested_remark",
]

_SHEET_NAME = "Sheet1"

_OPEN_WINDOWS: list[dict] = []
_VIEW_WINDOWS: dict[tuple, ctk.CTkToplevel] = {}
_SCROLL_BODIES: dict[str, ctk.CTkScrollableFrame] = {}


def _focus_existing_view(key: tuple) -> bool:
    win = _VIEW_WINDOWS.get(key)
    if win is None:
        return False
    try:
        if not win.winfo_exists():
            _VIEW_WINDOWS.pop(key, None)
            return False
        win.deiconify()
        win.lift()
        try:
            win.focus_force()
        except Exception:
            pass
        return True
    except Exception:
        _VIEW_WINDOWS.pop(key, None)
        return False


def _register_view(key: tuple, win):
    _VIEW_WINDOWS[key] = win

    def _on_destroy(e):
        if e.widget is win and _VIEW_WINDOWS.get(key) is win:
            _VIEW_WINDOWS.pop(key, None)

    win.bind("<Destroy>", _on_destroy, add="+")


def _tk_parent(widget):
    try:
        parent_path = widget.winfo_parent()
    except Exception:
        return None
    if not parent_path:
        return None
    try:
        return widget.nametowidget(parent_path)
    except Exception:
        return None


def _registered_top_level(widget):
    w = widget
    while w is not None:
        if str(w) in _SCROLL_BODIES:
            return w
        w = _tk_parent(w)
    return None


def _innermost_scroller(widget):
    w = widget
    while w is not None:
        if isinstance(w, ctk.CTkScrollableFrame):
            return w._parent_canvas
        if w.__class__.__name__ in ("Text", "Listbox"):
            return w
        w = _tk_parent(w)
    return None


def _bind_hover_scroll(win, body: ctk.CTkScrollableFrame):
    _SCROLL_BODIES[str(win)] = body

    def _on_wheel(event):
        try:
            hovered = win.winfo_containing(event.x_root, event.y_root)
        except Exception:
            hovered = None
        top = _registered_top_level(hovered) if hovered is not None else None
        if top is None:
            return None
        scroller = _innermost_scroller(hovered)
        if scroller is None:
            scroller = _SCROLL_BODIES[str(top)]._parent_canvas
        if scroller.__class__.__name__ not in ("Text", "Listbox"):
            units = -int(event.delta / 6)
            if units:
                try:
                    scroller.yview_scroll(units, "units")
                except Exception:
                    pass
        return "break"

    win.bind("<MouseWheel>", _on_wheel, add="+")

    def _on_destroy(e):
        if e.widget is win:
            _SCROLL_BODIES.pop(str(win), None)

    win.bind("<Destroy>", _on_destroy, add="+")


def _nonempty(v) -> bool:
    if v is None:
        return False
    try:
        if pd.isna(v):
            return False
    except (TypeError, ValueError):
        pass
    return str(v).strip().lower() not in ("", "nan", "nat", "none")


def _fmt_date(v) -> str:
    if not _nonempty(v):
        return "-"
    if isinstance(v, pd.Timestamp) or isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    return str(v).strip()


def _fmt_price(v) -> str:
    try:
        f = float(v)
        return f"{f:,.0f}"
    except (TypeError, ValueError):
        return str(v)


def _cell_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    try:
        f = float(v)
        if f == int(f):
            return str(int(f))
        return str(f)
    except (TypeError, ValueError):
        return str(v)


def _price_series(df: pd.DataFrame):
    if "sale_price" not in df.columns:
        return pd.Series([pd.NA] * len(df), index=df.index, dtype="float64")
    return pd.Series(pd.to_numeric(df["sale_price"], errors="coerce"), index=df.index, dtype="float64")


def _is_no_coupon(v) -> bool:
    if v is None:
        return False
    try:
        if pd.isna(v):
            return False
    except (TypeError, ValueError):
        pass
    return str(v).strip().upper() == "NONE"


def _has_value(v) -> bool:
    return _nonempty(v) or _is_no_coupon(v)


def _row_complete(row) -> bool:
    has_discount_method = (
        _has_value(row.get("cp_name"))
        or _nonempty(row.get("oc_amount"))
        or _nonempty(row.get("dc_amount"))
    )
    return (
        has_discount_method
        and _nonempty(row.get("usage_start_date"))
        and _nonempty(row.get("usage_end_date"))
    )


def _canonical_cp(v) -> str:
    if not _nonempty(v):
        return "NONE" if _is_no_coupon(v) else ""
    parts = str(v).replace(",", " ").split()
    return " ".join(sorted(p.upper() for p in parts))


def _canon_date(v) -> str:
    if not _nonempty(v):
        return ""
    if isinstance(v, (datetime, pd.Timestamp)):
        return v.strftime("%Y-%m-%d")
    return str(v).strip()


def _canon_num(v) -> str:
    if not _nonempty(v):
        return ""
    try:
        return str(float(v))
    except (TypeError, ValueError):
        return str(v).strip()


def pattern_key(rec) -> tuple:
    return (
        _canonical_cp(rec.get("cp_name")),
        _canon_date(rec.get("usage_start_date")),
        _canon_date(rec.get("usage_end_date")),
        _canon_num(rec.get("oc_amount")),
        _canon_num(rec.get("dc_amount")),
    )


def summarize_cp_data(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty or "sku" not in df.columns:
        return []
    work = df.copy()
    work = work.assign(_price=_price_series(work), _sku=work["sku"].astype(str).str.strip())
    out = []
    for sku_str in sorted({s for s in work["_sku"] if s}):
        sub = cast(pd.DataFrame, work[work["_sku"] == sku_str])
        price_col = cast(pd.Series, sub["_price"])
        priced = sub[price_col.notna()]
        prc_patterns = int(cast(pd.Series, priced["_price"]).drop_duplicates().shape[0])
        complete = 0
        for _, psub in priced.groupby("_price"):
            if any(_row_complete(r) for r in cast(pd.DataFrame, psub).to_dict("records")):
                complete += 1
        out.append({"sku": sku_str, "complete": complete, "prc_patterns": prc_patterns})
    return out


_SUMMARY_CACHE: dict = {"df": None, "path": None, "mtime": None, "summary": None}


def _summarize_cached(df, path: str) -> list[dict]:
    """summarize_cp_data แบบ cache — คำนวณซ้ำเฉพาะเมื่อ df object เปลี่ยน หรือ mtime ไฟล์เปลี่ยน
    (เก็บ df ไว้ใน cache กัน id ถูก reuse หลัง gc)"""
    if df is None:
        return []
    try:
        mtime = os.path.getmtime(path) if path else None
    except OSError:
        mtime = None
    c = _SUMMARY_CACHE
    if (c["df"] is df and c["path"] == path
            and c["mtime"] == mtime and c["summary"] is not None):
        return c["summary"]
    out = summarize_cp_data(df)
    c.update(df=df, path=path, mtime=mtime, summary=out)
    return out


def read_cp_rows(path: str) -> list[dict]:
    wb = load_workbook(path, read_only=True)
    try:
        ws = wb[_SHEET_NAME] if _SHEET_NAME in wb.sheetnames else wb[wb.sheetnames[0]]
        rows_iter = ws.iter_rows(values_only=True)
        header_row = next(rows_iter, ())
        header = {}
        for i, name in enumerate(header_row):
            if name is not None:
                header[str(name).strip()] = i
        rows = []
        for excel_row, values in enumerate(rows_iter, start=2):
            rec: dict = {"_excel_row": excel_row}
            for col in EDITOR_COLS:
                idx = header.get(col)
                rec[col] = values[idx] if (idx is not None and idx < len(values)) else None
            if all(rec[c] is None for c in EDITOR_COLS):
                continue
            rows.append(rec)
        return rows
    finally:
        wb.close()


_ROWS_CACHE: dict[str, dict] = {}


def _read_rows_cached(path: str) -> list[dict]:
    """อ่าน rows จาก xlsx แบบ cache — reuse จนกว่า mtime/size ของไฟล์จะเปลี่ยน
    (พิมพ์ค้นหา/คลิกเรียงทุก keystroke ไม่ต้องยิง openpyxl อ่านทั้งไฟล์ซ้ำ)"""
    st = os.stat(path)
    ent = _ROWS_CACHE.get(path)
    if (ent is not None and ent["mtime"] == st.st_mtime
            and ent["size"] == st.st_size):
        return ent["rows"]
    rows = read_cp_rows(path)
    _ROWS_CACHE[path] = {"mtime": st.st_mtime, "size": st.st_size, "rows": rows}
    return rows


def _backup(path: str):
    try:
        shutil.copy2(path, path + ".bak")
    except Exception as e:
        print(f"[cp_pattern_viewer] backup failed: {e}")


def _load_editable(path: str):
    wb = load_workbook(path)
    ws = wb[_SHEET_NAME] if _SHEET_NAME in wb.sheetnames else wb[wb.sheetnames[0]]
    header = {}
    for c in ws[1]:
        if c.value is not None:
            header[str(c.value).strip()] = c.column
    return wb, ws, header


_DATE_IN_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%y", "%d-%m-%y")


def _parse_date_input(s):
    if s is None or isinstance(s, datetime):
        return s
    s = str(s).strip()
    if not s:
        return None
    for fmt in _DATE_IN_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        ts = pd.to_datetime(s, dayfirst=True)
        if pd.notna(ts):
            return ts.to_pydatetime()
    except Exception:
        pass
    return s


def _parse_num_input(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return s
    s = str(s).strip()
    if not s:
        return None
    try:
        f = float(s.replace(",", ""))
        return int(f) if f == int(f) else f
    except ValueError:
        return s


def _parse_text_input(s):
    if s is None:
        return None
    s = str(s).strip()
    return s if s else None


def update_cp_row(path: str, excel_row: int, values: dict):
    _backup(path)
    wb, ws, header = _load_editable(path)
    try:
        for col, raw in values.items():
            idx = header.get(col)
            if idx is None:
                continue
            if col in ("usage_start_date", "usage_end_date",
                       "suggested_usage_start_date", "suggested_usage_end_date"):
                cell_val = _parse_date_input(raw)
            elif col in ("oc_amount", "dc_amount", "suggested_oc_amount", "suggested_dc_amount", "sale_price"):
                cell_val = _parse_num_input(raw)
            else:
                cell_val = _parse_text_input(raw)
            cast(Cell, ws.cell(row=excel_row, column=idx)).value = cell_val
        wb.save(path)
    finally:
        wb.close()


def delete_cp_rows(path: str, excel_rows: list[int]):
    _backup(path)
    wb, ws, _ = _load_editable(path)
    try:
        for r in sorted(set(excel_rows), reverse=True):
            ws.delete_rows(r, 1)
        wb.save(path)
    finally:
        wb.close()


def append_cp_row(path: str, values: dict):
    _backup(path)
    wb, ws, header = _load_editable(path)
    try:
        new_row = ws.max_row + 1
        for col, raw in values.items():
            idx = header.get(col)
            if idx is None:
                continue
            if col in ("usage_start_date", "usage_end_date",
                       "suggested_usage_start_date", "suggested_usage_end_date"):
                cell_val = _parse_date_input(raw)
            elif col in ("oc_amount", "dc_amount", "suggested_oc_amount", "suggested_dc_amount", "sale_price"):
                cell_val = _parse_num_input(raw)
            else:
                cell_val = _parse_text_input(raw)
            cast(Cell, ws.cell(row=new_row, column=idx)).value = cell_val
        wb.save(path)
        return new_row
    finally:
        wb.close()


def _force_reload_cp(app):
    app.cp_df = None
    app._cp_last_mtime = 0
    _ROWS_CACHE.clear()
    _SUMMARY_CACHE.update(df=None, path=None, mtime=None, summary=None)
    try:
        app.reload_cp_df_if_modified()
    except Exception:
        pass


def _cp_path(app) -> str:
    return getattr(app, "cp_table_location", "") or ""


def _register(win, refresh):
    entry = {"win": win, "refresh": refresh}
    _OPEN_WINDOWS.append(entry)

    def _on_destroy(e):
        if e.widget is win and entry in _OPEN_WINDOWS:
            _OPEN_WINDOWS.remove(entry)

    win.bind("<Destroy>", _on_destroy, add="+")


def _refresh_all(except_win=None):
    for entry in list(_OPEN_WINDOWS):
        if entry["win"] is except_win:
            continue
        try:
            if entry["win"].winfo_exists():
                entry["refresh"]()
        except Exception:
            pass


def _make_link(parent, text, command, width=None, anchor="w"):
    lbl = ctk.CTkLabel(parent, text=text, text_color=LINK_COLOR, font=_LINK_FONT,
                       cursor="hand2", anchor=anchor, fg_color="transparent")
    if width:
        lbl.configure(width=width)
    lbl.bind("<Button-1>", lambda _e: command())
    return lbl


def _tk_cell(parent, w, text, fg, bg, command=None, anchor="center", font=None):
    """ช่องข้อความแบบ tk (เร็วกว่า CTkLabel มากเมื่อต้องสร้าง/จัดวางหลายร้อยตัว)
    w = ความกว้างพิกเซลคงที่ หรือ None ให้ยืดตามคอลัมน์"""
    f = tk.Frame(parent, bg=bg, width=w or 0, height=26) if w else tk.Frame(parent, bg=bg)
    if w:
        f.pack_propagate(False)
    lbl = tk.Label(f, text=text, fg=fg, bg=bg, anchor=anchor, font=font or ("tahoma", 11))
    lbl.pack(fill="both", expand=True, padx=(6, 0) if anchor == "w" else 0)
    if command is not None:
        lbl.configure(cursor="hand2")
        lbl.bind("<Button-1>", lambda _e: command())
    return f


def _cancel_pending_debounce(entry):
    aid = getattr(entry, "_debounce_after_id", None)
    if aid is not None:
        try:
            entry.after_cancel(aid)
        except Exception:
            pass
        entry._debounce_after_id = None


def _make_entry(parent, width=120, placeholder=""):
    e = ctk.CTkEntry(parent, width=width, height=26, border_color=INPUT_BORDER,
                     border_width=1, fg_color="#ffffff", text_color="#111111",
                     placeholder_text=placeholder)
    return e


def _paint_tk(widget, color):
    """เปลี่ยนสีพื้นของแถว tk (Frame/Label) รวมลูกทั้งหมด"""
    widget.configure(bg=color)
    for c in widget.winfo_children():
        if isinstance(c, (tk.Frame, tk.Label)):
            _paint_tk(c, color)


class _CachedRows:
    """แสดงรายการแบบ cache เพื่อให้การค้นหาไม่ค้าง

    สร้าง widget ของแถวครั้งเดียว (แถวจะยังคงอยู่ระหว่างค้นหา) แล้วค้นหาด้วย pack / pack_forget
    sig = ค่าที่บอกว่าข้อมูลต้นทางเปลี่ยนหรือไม่ ถ้าเปลี่ยนจะสร้างแถวใหม่ทั้งหมด
    """

    def __init__(self, body):
        self.body = body
        self.sig = None
        self.rows = {}
        self.msgs = {}
        self.colors = {}
        self.shown = []

    def show(self, sig, items, key_of, build, empty_msg, paint=None, color_of=None,
             pack_kw=None, on_shown=None):
        if sig != self.sig:
            for w in self.body.winfo_children():
                w.destroy()
            self.rows.clear()
            self.msgs.clear()
            self.colors.clear()
            self.shown = []
            self.sig = sig
        for w in self.shown:
            w.pack_forget()
        self.shown = []
        if not items:
            lbl = self.msgs.get(empty_msg)
            if lbl is None:
                lbl = ctk.CTkLabel(self.body, text=empty_msg, fg_color="transparent",
                                   text_color="#666666")
                self.msgs[empty_msg] = lbl
            lbl.pack(pady=30)
            self.shown = [lbl]
            return
        for i, it in enumerate(items):
            k = key_of(it)
            parts = self.rows.get(k)
            if parts is None:
                parts = build(self.body, it)
                self.rows[k] = parts
            row, sep = parts
            if paint is not None and color_of is not None:
                color = color_of(k)
                if self.colors.get(k) != color:
                    paint(row, color)
                    self.colors[k] = color
            row.pack(**(pack_kw or {"fill": "x"}))
            self.shown.append(row)
            if sep is not None:
                sep.pack(fill="x")
                self.shown.append(sep)
            if on_shown is not None:
                on_shown(k, it, i)


def _make_search_bar(parent, on_change, placeholder: str):
    """แถบค้นหาใต้หัวตาราง — debounce ~150ms ก่อนเรียก on_change() เพื่อไม่ให้ render ชนกับการพิมพ์"""
    bar = ctk.CTkFrame(parent, fg_color="#f7f7f7", corner_radius=0, height=34)
    bar.pack(fill="x", side="top")
    bar.pack_propagate(False)
    entry = ctk.CTkEntry(bar, height=26, border_color=INPUT_BORDER, border_width=1,
                         fg_color="#ffffff", text_color="#111111",
                         placeholder_text=placeholder, font=("tahoma", 11))
    entry.pack(side="left", fill="x", expand=True, padx=(10, 10), pady=4)

    entry._debounce_after_id = None

    def fire():
        entry._debounce_after_id = None
        try:
            on_change()
        except Exception:
            pass

    def schedule(_e=None):
        aid = entry._debounce_after_id
        if aid is not None:
            try:
                entry.after_cancel(aid)
            except Exception:
                pass
            entry._debounce_after_id = None
        entry._debounce_after_id = entry.after(150, fire)

    def flush(_e=None):
        aid = entry._debounce_after_id
        if aid is not None:
            try:
                entry.after_cancel(aid)
            except Exception:
                pass
            entry._debounce_after_id = None
        try:
            on_change()
        except Exception:
            pass
        return "break"

    entry.bind("<KeyRelease>", schedule)
    entry.bind("<<Paste>>", schedule)
    entry.bind("<<Cut>>", schedule)
    entry.bind("<Return>", flush)
    return entry


def _attach_sort(parent, spec, sort_state, refresh, font, pady=8):
    """หัวตารางที่คลิกได้: คลิก = เรียง asc, คลิกซ้ำ = desc, คลิกคอลัมน์อื่น = คอลัมน์ใหม่ asc
    ลูกศร ▲/▼ แสดงบนคอลัมน์ที่ active — spec: [{"col", "text", "column",
    "width"?, "anchor"?, "padx"?, "pady"?, "sticky"?}, ...]
    sort_state: {"col", "asc"} mutable dict ที่แชร์กับ populate"""
    labels: dict = {}
    bases: dict = {}

    def paint():
        for key, lbl in labels.items():
            arrow = ""
            if sort_state.get("col") == key:
                arrow = " ▲" if sort_state.get("asc", True) else " ▼"
            lbl.configure(text=bases[key] + arrow)

    def on_click(key):
        if sort_state.get("col") == key:
            sort_state["asc"] = not sort_state.get("asc", True)
        else:
            sort_state["col"] = key
            sort_state["asc"] = True
        paint()
        refresh()

    for item in spec:
        key = item["col"]
        kwargs = dict(text=item["text"], font=font, fg_color="transparent",
                      text_color="#111111", cursor="hand2")
        if item.get("width") is not None:
            kwargs["width"] = item["width"]
        if item.get("anchor") is not None:
            kwargs["anchor"] = item["anchor"]
        lbl = ctk.CTkLabel(parent, **kwargs)
        lbl.grid(row=0, column=item["column"], padx=item.get("padx", 2),
                 pady=item.get("pady", pady), sticky=item.get("sticky", ""))
        lbl.bind("<Button-1>", lambda _e, k=key: on_click(k))
        labels[key] = lbl
        bases[key] = item["text"]
    paint()
    return labels


def filter_sort_sku_items(summary: list, query: str, col: str, asc: bool) -> list:
    """กรอง + เรียงรายการหน้า SKU — ค้น substring ใน sku/complete/prc_patterns
    เรียง sku (text) หรือ complete/prc_patterns (ตัวเลข), default = sku"""
    items = list(summary)
    q = (query or "").strip().lower()
    if q:
        items = [
            it for it in items
            if q in str(it.get("sku") or "").lower()
            or q in str(it.get("complete") or "").lower()
            or q in str(it.get("prc_patterns") or "").lower()
        ]
    if col == "complete":
        keyfn = lambda it: int(it.get("complete") or 0)
    elif col == "prc_patterns":
        keyfn = lambda it: int(it.get("prc_patterns") or 0)
    else:
        keyfn = lambda it: str(it.get("sku") or "").lower()
    return sorted(items, key=keyfn, reverse=not asc)


def filter_sort_price_items(items: list, query: str, col: str, asc: bool) -> list:
    """กรอง + เรียงรายการหน้าราคา — ค้น substring จาก ราคา (มี/ไม่มี comma) + complete + patterns
    เรียง price/complete/patterns เชิงตัวเลข (ไม่ใช่ lexical), default = price
    items: [{"price": float, "complete": int, "patterns": int}, ...]"""
    out = list(items)
    q = (query or "").strip().lower()
    if q:
        def _hay(it):
            p = it.get("price")
            try:
                ptxt = f"{float(p):g}"
            except (TypeError, ValueError):
                ptxt = str(p or "")
            return f"{_fmt_price(p)} {ptxt} {it.get('complete', 0)} {it.get('patterns', 0)}".lower()
        out = [it for it in out if q in _hay(it)]
    if col == "complete":
        keyfn = lambda it: int(it.get("complete") or 0)
    elif col == "patterns":
        keyfn = lambda it: int(it.get("patterns") or 0)
    else:
        keyfn = lambda it: float(it.get("price") or 0)
    return sorted(out, key=keyfn, reverse=not asc)


def filter_pattern_rows(rows: list, query: str) -> list:
    """กรองแถว pattern ตาม substring ในค่าใดก็ได้ของ EDITOR_COLS (ข้อความ/ตัวเลข/วันที่ dd/mm/yyyy)"""
    q = (query or "").strip().lower()
    if not q:
        return list(rows)
    out = []
    for r in rows:
        hay = " ".join(_cell_text(r.get(c)) for c in EDITOR_COLS).lower()
        if q in hay:
            out.append(r)
    return out


def _date_sort_val(v) -> float:
    if isinstance(v, datetime):
        return v.timestamp()
    d = _parse_date_input(v)
    if isinstance(d, datetime):
        return d.timestamp()
    return float("inf")


def _num_sort_val(v) -> tuple:
    n = _parse_num_input(v)
    if isinstance(n, bool):
        return (1, 0.0, str(v or "").lower())
    if isinstance(n, (int, float)):
        return (0, float(n), "")
    return (1, 0.0, str(v or "").lower())


def sort_pattern_rows(rows: list, col: str, asc: bool) -> list:
    """เรียงแถว pattern: no. (ตามตำแหน่งไฟล์), cp, start, end, oc, dc
    วันที่/ตัวเลข: ค่าว่าง = ท้ายสุดทั้ง asc/desc — no./คอลัมน์ที่ไม่รู้จัก = ตามไฟล์"""
    if col in (None, "", "no."):
        return sorted(rows, key=lambda r: int(r.get("_excel_row") or 0), reverse=not asc)

    if col == "cp":
        keyfn = lambda r: _cell_text(r.get("cp_name")).lower()
        emptyfn = lambda r: not _has_value(r.get("cp_name"))
    elif col == "start":
        keyfn = lambda r: _date_sort_val(r.get("usage_start_date"))
        emptyfn = lambda r: not _nonempty(r.get("usage_start_date"))
    elif col == "end":
        keyfn = lambda r: _date_sort_val(r.get("usage_end_date"))
        emptyfn = lambda r: not _nonempty(r.get("usage_end_date"))
    elif col == "oc":
        keyfn = lambda r: _num_sort_val(r.get("oc_amount"))
        emptyfn = lambda r: not _nonempty(r.get("oc_amount"))
    elif col == "dc":
        keyfn = lambda r: _num_sort_val(r.get("dc_amount"))
        emptyfn = lambda r: not _nonempty(r.get("dc_amount"))
    else:
        return sorted(rows, key=lambda r: int(r.get("_excel_row") or 0), reverse=not asc)

    filled = [r for r in rows if not emptyfn(r)]
    empty = [r for r in rows if emptyfn(r)]
    filled.sort(key=keyfn, reverse=not asc)
    return filled + empty


def open_cp_pattern_window(app):
    if _focus_existing_view(("sku_list",)):
        return
    try:
        app.reload_cp_df_if_modified()
    except Exception as e:
        messagebox.showerror("CP Data", f"โหลด CP Data ไม่สำเร็จ: {e}")
        return
    df = getattr(app, "cp_df", None)
    path = _cp_path(app)
    if df is None:
        if path and os.path.exists(path):
            messagebox.showerror("CP Data", "อ่านไฟล์ CP Data ไม่ได้ (อาจถูกเปิดค้างในโปรแกรมอื่น)")
        else:
            messagebox.showwarning("CP Data", "ยังไม่ได้เลือกไฟล์ CP Data")
        return

    win = ctk.CTkToplevel(app.root if hasattr(app, "root") else app)
    win.title("CP Data - SKU Patterns")
    win.geometry("560x520")
    # ไม่ใช้ grab_set / topmost: หน้าต่างนี้ต้องให้ใช้หน้าหลักได้ตามปกติ
    win.configure(fg_color=BG)

    header = ctk.CTkFrame(win, fg_color=HEADER_BG, corner_radius=0, height=40)
    header.pack(fill="x", side="top")
    header.grid_propagate(False)
    header.grid_columnconfigure(0, weight=1)
    header.grid_columnconfigure(1, weight=0)
    header.grid_columnconfigure(2, weight=0)

    sort_state = {"col": "sku", "asc": True}
    _attach_sort(header, [
        {"col": "sku", "text": "no. of sku patterns", "column": 0,
         "anchor": "w", "padx": (10, 4), "sticky": "w"},
        {"col": "complete", "text": "complete", "column": 1, "width": 90},
        {"col": "prc_patterns", "text": "prc patterns", "column": 2, "width": 90},
    ], sort_state, lambda: populate(), font=("tahoma", 12, "bold"), pady=8)

    search_entry = _make_search_bar(win, lambda: populate(),
                                    "ค้นหารุ่น (SKU) หรือค่าในคอลัมน์…")

    body = ctk.CTkScrollableFrame(win, fg_color=BG, corner_radius=0)
    body.pack(fill="both", expand=True)
    _bind_hover_scroll(win, body)
    _register_view(("sku_list",), win)
    cache = _CachedRows(body)

    def _build_sku_row(parent, item):
        sku = item["sku"]
        show_detail = lambda s=sku: open_price_list_window(app, s)
        row = tk.Frame(parent, bg=BG)
        row.grid_columnconfigure(0, weight=1)
        _tk_cell(row, None, sku, LINK_COLOR, BG, show_detail, anchor="w", font=_LINK_FONT).grid(
            row=0, column=0, sticky="ew", padx=(4, 4), pady=3)
        _tk_cell(row, 90, str(item["complete"]), LINK_COLOR, BG, show_detail).grid(
            row=0, column=1, padx=2, pady=3)
        _tk_cell(row, 90, str(item["prc_patterns"]), LINK_COLOR, BG, show_detail).grid(
            row=0, column=2, padx=2, pady=3)
        sep = tk.Frame(parent, height=1, bg=LINE)
        return row, sep

    footer = ctk.CTkLabel(win, text="", fg_color=HEADER_BG, text_color="#444444",
                          corner_radius=0, font=("tahoma", 10))
    footer.pack(fill="x", side="bottom", ipady=4)

    def populate():
        # * ยกเลิก pending debounce จากการพิมพ์ (ถ้ามี) เพื่อไม่ให้ render ซ้ำ
        _cancel_pending_debounce(search_entry)
        path = _cp_path(app)
        if path and os.path.exists(path):
            try:
                app.reload_cp_df_if_modified()
            except Exception:
                pass
            df_now = getattr(app, "cp_df", None)
        else:
            df_now = None
        summary = _summarize_cached(df_now, path)
        items = filter_sort_sku_items(summary, search_entry.get(),
                                      sort_state.get("col", "sku"), sort_state.get("asc", True))
        sig = tuple((s["sku"], s["complete"], s["prc_patterns"]) for s in summary)
        pos = {s["sku"]: i for i, s in enumerate(summary)}
        cache.show(sig, items, key_of=lambda it: it["sku"], build=_build_sku_row,
                   paint=_paint_tk, color_of=lambda k: BG if pos[k] % 2 == 0 else "#fafafa",
                   empty_msg="ไม่พบรายการที่ค้นหา" if summary else "ไม่มีข้อมูล SKU ใน CP Data")
        total_patterns = sum(item["prc_patterns"] for item in items)
        q = search_entry.get().strip()
        shown = f" (แสดง {len(items)}/{len(summary)})" if q else ""
        footer.configure(text=f"SKU ทั้งหมด: {len(summary)}{shown}  |  ราคาไม่ซ้ำรวม: {total_patterns} รูปแบบ")

    populate()
    _register(win, populate)


def _sku_price_rows(app, sku: str) -> list[dict]:
    path = _cp_path(app)
    if not path or not os.path.exists(path):
        return []
    try:
        rows = _read_rows_cached(path)
    except PermissionError:
        messagebox.showerror("CP Data", "อ่านไฟล์ CP Data ไม่ได้ (อาจถูกเปิดค้างในโปรแกรมอื่น)")
        return []
    except Exception as e:
        messagebox.showerror("CP Data", f"อ่านไฟล์ CP Data ไม่สำเร็จ: {e}")
        return []
    sku_s = str(sku).strip().upper()

    def _price_of(r):
        try:
            return float(r["sale_price"])
        except (TypeError, ValueError):
            return None

    out = []
    for r in rows:
        if str(r.get("sku") or "").strip().upper() != sku_s:
            continue
        p = _price_of(r)
        if p is None:
            continue
        r = dict(r)
        r["_price"] = p
        out.append(r)
    return out


def _price_groups(rows: list[dict]) -> dict:
    groups: dict[float, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["_price"], []).append(r)
    return dict(sorted(groups.items()))


def open_price_list_window(app, sku: str):
    key = ("price_list", str(sku).strip().upper())
    if _focus_existing_view(key):
        return
    win = ctk.CTkToplevel(app.root if hasattr(app, "root") else app)
    win.title(f"-/{sku}")
    win.geometry("560x480")
    # ไม่ใช้ grab_set / topmost: หน้าต่างนี้ต้องให้ใช้หน้าหลักได้ตามปกติ
    win.configure(fg_color=BG)

    header = ctk.CTkFrame(win, fg_color=HEADER_BG, corner_radius=0, height=40)
    header.pack(fill="x", side="top")
    header.grid_propagate(False)
    header.grid_columnconfigure(0, weight=1)
    header.grid_columnconfigure(1, weight=0)

    ctk.CTkLabel(header, text=f"-/{sku}", font=("tahoma", 12, "bold"), anchor="w",
                 fg_color="transparent", text_color="#111111").grid(row=0, column=0, padx=(10, 4), pady=8, sticky="w")
    ctk.CTkButton(header, text="+ Add new", width=90, height=28, fg_color="#2b5b84",
                  hover_color="#1e3f5c", text_color="#ffffff",
                  command=lambda: _add_new_price(app, sku, win)).grid(row=0, column=1, padx=2, pady=6)

    col_header = ctk.CTkFrame(win, fg_color="#f7f7f7", corner_radius=0, height=30)
    col_header.pack(fill="x", side="top")
    col_header.grid_propagate(False)
    col_header.grid_columnconfigure(0, weight=1)

    sort_state = {"col": "price", "asc": True}
    _attach_sort(col_header, [
        {"col": "price", "text": "price list", "column": 0,
         "anchor": "w", "padx": (14, 4), "sticky": "w"},
        {"col": "complete", "text": "complete", "column": 1, "width": 90},
        {"col": "patterns", "text": "patterns", "column": 2, "width": 90},
    ], sort_state, lambda: populate(), font=("tahoma", 11, "bold"), pady=4)

    search_entry = _make_search_bar(win, lambda: populate(),
                                    "ค้นหาราคาหรือค่าในคอลัมน์…")

    body = ctk.CTkScrollableFrame(win, fg_color=BG, corner_radius=0)
    body.pack(fill="both", expand=True)
    _bind_hover_scroll(win, body)
    _register_view(key, win)
    cache = _CachedRows(body)

    def _build_price_row(parent, it):
        price = it["price"]
        show_detail = lambda p=price: open_pattern_detail_window(app, sku, p)
        row = tk.Frame(parent, bg=BG)
        row.grid_columnconfigure(0, weight=1)
        _tk_cell(row, None, _fmt_price(price), LINK_COLOR, BG, show_detail, anchor="w", font=_LINK_FONT).grid(
            row=0, column=0, sticky="ew", padx=(10, 4), pady=4)
        _tk_cell(row, 90, str(it["complete"]), "#111111", BG).grid(row=0, column=1, padx=2, pady=4)
        _tk_cell(row, 90, str(it["patterns"]), "#111111", BG).grid(row=0, column=2, padx=2, pady=4)
        sep = tk.Frame(parent, height=1, bg=LINE)
        return row, sep

    footer = ctk.CTkLabel(win, text="", fg_color=HEADER_BG, text_color="#444444",
                          corner_radius=0, font=("tahoma", 10))
    footer.pack(fill="x", side="bottom", ipady=4)

    def populate():
        _cancel_pending_debounce(search_entry)
        rows = _sku_price_rows(app, sku)
        groups = _price_groups(rows)
        all_items = [
            {"price": p,
             "complete": sum(1 for r in prows if _row_complete(r)),
             "patterns": len({pattern_key(r) for r in prows})}
            for p, prows in groups.items()
        ]
        items = filter_sort_price_items(all_items, search_entry.get(),
                                        sort_state.get("col", "price"), sort_state.get("asc", True))
        sig = tuple((it["price"], it["complete"], it["patterns"]) for it in all_items)
        pos = {it["price"]: i for i, it in enumerate(all_items)}
        cache.show(sig, items, key_of=lambda it: it["price"], build=_build_price_row,
                   paint=_paint_tk, color_of=lambda k: BG if pos[k] % 2 == 0 else "#fafafa",
                   empty_msg="ไม่พบรายการที่ค้นหา" if groups else "ยังไม่มีราคาสำหรับ SKU นี้")
        total_patterns = sum(it["patterns"] for it in items)
        q = search_entry.get().strip()
        shown = f" (แสดง {len(items)}/{len(groups)})" if q else ""
        footer.configure(text=f"ราคาทั้งหมด: {len(groups)}{shown} รูปแบบ  |  รวม patterns: {total_patterns}")

    populate()
    _register(win, populate)


def _add_new_price(app, sku: str, parent_win=None):
    path = _cp_path(app)
    if not path or not os.path.exists(path):
        messagebox.showwarning("CP Data", "ยังไม่ได้เลือกไฟล์ CP Data")
        return
    price = simpledialog.askfloat("Add new price", f"ราคาใหม่ของ {sku}:", minvalue=0, parent=parent_win)
    if price is None:
        return
    try:
        append_cp_row(path, {"sku": sku, "sale_price": price})
    except PermissionError:
        messagebox.showerror("CP Data", "เขียนไฟล์ CP Data ไม่ได้ (อาจถูกเปิดค้างในโปรแกรมอื่น)")
        return
    except Exception as e:
        messagebox.showerror("CP Data", f"เพิ่มราคาไม่สำเร็จ: {e}")
        return
    _force_reload_cp(app)
    _refresh_all()
    open_pattern_detail_window(app, sku, float(price))


def open_pattern_detail_window(app, sku: str, price: float):
    key = ("pattern", str(sku).strip().upper(), round(float(price), 2))
    if _focus_existing_view(key):
        return
    price_str = _fmt_price(price)
    win = ctk.CTkToplevel(app.root if hasattr(app, "root") else app)
    win.title(f"-/{sku}/{price_str}")
    win.geometry("720x560")
    # ไม่ใช้ grab_set / topmost: หน้าต่างนี้ต้องให้ใช้หน้าหลักได้ตามปกติ
    win.configure(fg_color=BG)

    header = ctk.CTkFrame(win, fg_color=HEADER_BG, corner_radius=0, height=40)
    header.pack(fill="x", side="top")
    header.grid_propagate(False)
    header.grid_columnconfigure(0, weight=1)
    header.grid_columnconfigure(1, weight=0)
    header.grid_columnconfigure(2, weight=0)

    ctk.CTkLabel(header, text="price list", font=("tahoma", 12, "bold"),
                 fg_color="transparent", text_color="#111111").grid(row=0, column=0, padx=(12, 4), pady=6, sticky="w")
    price_entry = ctk.CTkEntry(header, width=120, height=28, state="readonly")
    price_entry.grid(row=0, column=1, padx=2, pady=6)
    price_entry.configure(state="normal")
    price_entry.insert(0, price_str)
    price_entry.configure(state="readonly")
    ctk.CTkButton(header, text="+ Add pattern", width=110, height=28, fg_color="#2b5b84",
                  hover_color="#1e3f5c", text_color="#ffffff",
                  command=lambda: _add_pattern(app, sku, price)).grid(row=0, column=2, padx=2, pady=6)

    search_entry = _make_search_bar(win, lambda: populate(),
                                    "ค้นหาค่าใน pattern (CP/DC, วันที่, oc/dc, remark)…")

    sort_strip = ctk.CTkFrame(win, fg_color="#f7f7f7", corner_radius=0, height=26)
    sort_strip.pack(fill="x", side="top")
    sort_strip.grid_propagate(False)
    sort_strip.grid_columnconfigure(6, weight=1)

    sort_state = {"col": "no.", "asc": True}
    _attach_sort(sort_strip, [
        {"col": "no.", "text": "no.", "column": 0, "width": 60, "anchor": "w", "padx": (12, 2)},
        {"col": "cp", "text": "CP/DC", "column": 1, "width": 220, "anchor": "w"},
        {"col": "start", "text": "start date", "column": 2, "width": 95, "anchor": "w"},
        {"col": "end", "text": "end date", "column": 3, "width": 95, "anchor": "w"},
        {"col": "oc", "text": "oc amount", "column": 4, "width": 80, "anchor": "w"},
        {"col": "dc", "text": "dc amount", "column": 5, "width": 80, "anchor": "w"},
    ], sort_state, lambda: populate(), font=("tahoma", 9, "bold"), pady=5)

    body = ctk.CTkScrollableFrame(win, fg_color=BG, corner_radius=0)
    body.pack(fill="both", expand=True)
    _bind_hover_scroll(win, body)
    _register_view(key, win)
    cache = _CachedRows(body)
    numboxes = {}   # excel_row -> {"n": ลำดับที่แสดง, "lbl": CTkLabel ของ "No. n"}

    footer = ctk.CTkLabel(win, text="", fg_color=HEADER_BG, text_color="#444444",
                          corner_radius=0, font=("tahoma", 10))
    footer.pack(fill="x", side="bottom", ipady=4)

    def populate():
        # * ยกเลิก pending debounce จากการพิมพ์ (ถ้ามี) เพื่อไม่ให้ render ซ้ำ
        _cancel_pending_debounce(search_entry)
        path = _cp_path(app)
        all_rows = [r for r in _sku_price_rows(app, sku) if r["_price"] == float(price)]
        rows = filter_pattern_rows(all_rows, search_entry.get())
        rows = sort_pattern_rows(rows, sort_state.get("col", "no."), sort_state.get("asc", True))
        # sig: การ์ดจะถูกสร้างใหม่เฉพาะเมื่อข้อมูลเปลี่ยน (ไม่ใช่ทุกครั้งที่พิมพ์ค้นหา)
        sig = (path, tuple(
            (r["_excel_row"], tuple(sorted((k, str(v)) for k, v in r.items())))
            for r in all_rows))

        def _build(parent, rec):
            box = numboxes.setdefault(rec["_excel_row"], {"n": 0, "lbl": None})
            card = _build_pattern_card(parent, app, sku, price, rec, path, box)
            return card, None

        def _on_shown(k, rec, i):
            box = numboxes[rec["_excel_row"]]
            box["n"] = i + 1
            if box["lbl"] is not None:
                box["lbl"].configure(text=f"No. {i + 1}")

        empty = ("ไม่พบแถวที่ค้นหา" if (all_rows and search_entry.get().strip())
                 else "ยังไม่มี pattern สำหรับราคานี้ — กด + Add pattern")
        cache.show(sig, rows, key_of=lambda r: r["_excel_row"], build=_build,
                   empty_msg=empty, pack_kw={"fill": "x", "padx": 6, "pady": 5},
                   on_shown=_on_shown)
        complete = sum(1 for r in rows if _row_complete(r))
        patterns = len({pattern_key(r) for r in rows})
        q = search_entry.get().strip()
        row_txt = f"จาก {len(rows)}/{len(all_rows)} แถว" if q else f"จาก {len(rows)} แถว"
        footer.configure(text=f"patterns: {patterns} ({row_txt})  |  complete: {complete}")

    populate()
    _register(win, populate)


def _add_pattern(app, sku: str, price: float):
    path = _cp_path(app)
    if not path or not os.path.exists(path):
        messagebox.showwarning("CP Data", "ยังไม่ได้เลือกไฟล์ CP Data")
        return
    try:
        append_cp_row(path, {"sku": sku, "sale_price": price})
    except PermissionError:
        messagebox.showerror("CP Data", "เขียนไฟล์ CP Data ไม่ได้ (อาจถูกเปิดค้างในโปรแกรมอื่น)")
        return
    except Exception as e:
        messagebox.showerror("CP Data", f"เพิ่ม pattern ไม่สำเร็จ: {e}")
        return
    _force_reload_cp(app)
    _refresh_all()


def _delete_pattern(app, sku: str, price: float, rec: dict, no: int):
    path = _cp_path(app)
    if not path or not os.path.exists(path):
        messagebox.showwarning("CP Data", "ยังไม่ได้เลือกไฟล์ CP Data")
        return
    price_str = _fmt_price(price)
    ok = messagebox.askyesno(
        "ยืนยันการลบ",
        f"ลบ pattern No.{no} ({sku} / {price_str}) ออกจาก cp_data.xlsx ?\n\n"
        f"cp/dc: {_cell_text(rec.get('cp_name')) or '-'}\n"
        "ระบบจะสำรองไฟล์เป็น cp_data.xlsx.bak ก่อนลบ")
    if not ok:
        return
    try:
        delete_cp_rows(path, [rec["_excel_row"]])
    except PermissionError:
        messagebox.showerror("CP Data", "เขียนไฟล์ CP Data ไม่ได้ (อาจถูกเปิดค้างในโปรแกรมอื่น)")
        return
    except Exception as e:
        messagebox.showerror("CP Data", f"ลบ pattern ไม่สำเร็จ: {e}")
        return
    _force_reload_cp(app)
    _refresh_all()


def _save_pattern_with_remark(app, path, excel_row, entries: dict, remark_box, status_lbl, except_win=None, state_lbl=None):
    if not path or not os.path.exists(path):
        messagebox.showwarning("CP Data", "ยังไม่ได้เลือกไฟล์ CP Data")
        return
    values = {col: e.get() for col, e in entries.items()}
    values["suggested_remark"] = remark_box.get("0.0", "end").strip()
    try:
        update_cp_row(path, excel_row, values)
    except PermissionError:
        status_lbl.configure(text="เขียนไฟล์ไม่ได้ (เปิดค้างในโปรแกรมอื่น?)", text_color=BAD_COLOR)
        return
    except Exception as e:
        status_lbl.configure(text=f"บันทึกไม่สำเร็จ: {e}", text_color=BAD_COLOR)
        return
    _force_reload_cp(app)
    _refresh_all(except_win=except_win)
    status_lbl.configure(text="บันทึกแล้ว", text_color=OK_COLOR)
    if state_lbl is not None:
        done = _row_complete(values)
        state_lbl.configure(text="complete" if done else "incomplete",
                            text_color=OK_COLOR if done else BAD_COLOR)


def _build_pattern_card(body, app, sku: str, price: float, rec: dict, path: str, numbox: dict):
    excel_row = rec["_excel_row"]
    card = ctk.CTkFrame(body, fg_color="#ffffff", corner_radius=6, border_width=1, border_color=LINE)

    top = ctk.CTkFrame(card, fg_color="#f7f7f7", corner_radius=6, height=30)
    top.pack(fill="x", padx=6, pady=(6, 2))
    top.pack_propagate(False)
    numbox["lbl"] = ctk.CTkLabel(top, text="No. -", font=("tahoma", 11, "bold"),
                                 fg_color="transparent", text_color="#111111")
    numbox["lbl"].pack(side="left", padx=8)
    state = "complete" if _row_complete(rec) else "incomplete"
    state_lbl = ctk.CTkLabel(top, text=state, font=("tahoma", 9),
                             text_color=OK_COLOR if _row_complete(rec) else BAD_COLOR,
                             fg_color="transparent")
    state_lbl.pack(side="left", padx=4)
    ctk.CTkButton(top, text="ลบ", width=50, height=24, fg_color="#c94f4f",
                  hover_color="#a83e3e", text_color="#ffffff",
                  command=lambda r=rec: _delete_pattern(app, sku, price, r, numbox.get("n", 0))).pack(side="right", padx=8, pady=3)

    grid = ctk.CTkFrame(card, fg_color="#ffffff")
    grid.pack(fill="x", padx=8, pady=(2, 2))
    labels = [("CP/DC", 220), ("start date", 95), ("end date", 95), ("oc amount", 80), ("dc amount", 80)]
    for c, (text, w) in enumerate(labels):
        ctk.CTkLabel(grid, text=text, font=("tahoma", 9, "bold"), width=w, anchor="w",
                     fg_color="transparent", text_color="#555555").grid(row=0, column=c, padx=2, pady=(2, 0), sticky="w")

    entries = {}
    src = [("cp_name", _cell_text(rec.get("cp_name")), 220),
           ("usage_start_date", _cell_text(rec.get("usage_start_date")), 95),
           ("usage_end_date", _cell_text(rec.get("usage_end_date")), 95),
           ("oc_amount", _cell_text(rec.get("oc_amount")), 80),
           ("dc_amount", _cell_text(rec.get("dc_amount")), 80)]
    for c, (col, val, w) in enumerate(src):
        e = _make_entry(grid, width=w)
        if val:
            e.insert(0, val)
        e.grid(row=1, column=c, padx=2, pady=(0, 4))
        entries[col] = e

    sug = ctk.CTkFrame(card, fg_color="#fbfbfb", corner_radius=6)
    sug.pack(fill="x", padx=8, pady=(0, 4))
    sug_head = ctk.CTkFrame(sug, fg_color="transparent", height=26)
    sug_head.pack(fill="x", padx=4, pady=(4, 0))
    sug_head.pack_propagate(False)
    ctk.CTkLabel(sug_head, text="suggested", font=("tahoma", 9, "bold"),
                 fg_color="transparent", text_color="#555555").pack(side="left", padx=4)

    sug_grid = ctk.CTkFrame(sug, fg_color="transparent")
    sug_grid.pack(fill="x", padx=4)
    sug_labels = [("cp/dc", 220), ("start", 95), ("end", 95), ("oc", 80), ("dc", 80)]
    for c, (text, w) in enumerate(sug_labels):
        ctk.CTkLabel(sug_grid, text=text, font=("tahoma", 9, "bold"), width=w, anchor="w",
                     fg_color="transparent", text_color="#555555").grid(row=0, column=c, padx=2, pady=(2, 0), sticky="w")

    sug_entries = {}
    sug_src = [("suggested_cp", _cell_text(rec.get("suggested_cp")), 220),
               ("suggested_usage_start_date", _cell_text(rec.get("suggested_usage_start_date")), 95),
               ("suggested_usage_end_date", _cell_text(rec.get("suggested_usage_end_date")), 95),
               ("suggested_oc_amount", _cell_text(rec.get("suggested_oc_amount")), 80),
               ("suggested_dc_amount", _cell_text(rec.get("suggested_dc_amount")), 80)]
    for c, (col, val, w) in enumerate(sug_src):
        e = _make_entry(sug_grid, width=w)
        if val:
            e.insert(0, val)
        e.grid(row=1, column=c, padx=2, pady=(0, 4))
        sug_entries[col] = e

    ctk.CTkLabel(sug, text="remark", font=("tahoma", 9, "bold"), anchor="w",
                 fg_color="transparent", text_color="#555555").pack(fill="x", padx=8, pady=(2, 0))
    remark_box = ctk.CTkTextbox(sug, height=55, border_color=INPUT_BORDER, border_width=1,
                                fg_color="#ffffff", text_color="#111111", font=("tahoma", 9))
    remark_box.pack(fill="x", padx=8, pady=(0, 6))
    remark = rec.get("suggested_remark")
    if _nonempty(remark):
        remark_box.insert("0.0", str(remark).strip())

    foot = ctk.CTkFrame(card, fg_color="#ffffff")
    foot.pack(fill="x", padx=8, pady=(0, 6))
    status_lbl = ctk.CTkLabel(foot, text="", font=("tahoma", 9),
                              fg_color="transparent", text_color=OK_COLOR)
    status_lbl.pack(side="left", padx=4)
    all_entries = {**entries, **sug_entries}
    ctk.CTkButton(foot, text="บันทึก", width=80, height=26, fg_color="#2b5b84",
                  hover_color="#1e3f5c", text_color="#ffffff",
                  command=lambda: _save_pattern_with_remark(app, path, excel_row, all_entries,
                                                            remark_box, status_lbl,
                                                            except_win=card.winfo_toplevel(),
                                                            state_lbl=state_lbl)).pack(side="right", padx=4)
    return card
