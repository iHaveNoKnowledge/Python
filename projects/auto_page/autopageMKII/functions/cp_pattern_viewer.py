"""
Phase 1-3: read/edit SKU pattern list from cp_data (groupby sku).
Complete pattern = แถวที่ใส่ cp_name + usage_start_date + usage_end_date ครบ
Page 1 (SKU list) -> Page 2 (price list ของ SKU) -> Page 3 (รายละเอียด pattern ของราคานั้น, CRUD)
"""
import os
import shutil
from datetime import datetime
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


def _row_complete(row) -> bool:
    return (
        _nonempty(row.get("cp_name"))
        and _nonempty(row.get("usage_start_date"))
        and _nonempty(row.get("usage_end_date"))
    )


def _canonical_cp(v) -> str:
    if not _nonempty(v):
        return ""
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

    win.bind("<Destroy>", _on_destroy)


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


def _make_entry(parent, width=120, placeholder=""):
    e = ctk.CTkEntry(parent, width=width, height=26, border_color=INPUT_BORDER,
                     border_width=1, fg_color="#ffffff", text_color="#111111",
                     placeholder_text=placeholder)
    return e


def open_cp_pattern_window(app):
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
    win.attributes("-topmost", True)
    win.grab_set()
    win.configure(fg_color=BG)

    header = ctk.CTkFrame(win, fg_color=HEADER_BG, corner_radius=0, height=40)
    header.pack(fill="x", side="top")
    header.grid_propagate(False)
    header.grid_columnconfigure(0, weight=1)
    header.grid_columnconfigure(1, weight=0)
    header.grid_columnconfigure(2, weight=0)
    header.grid_columnconfigure(3, weight=0)

    ctk.CTkLabel(header, text="no. of sku patterns", font=("tahoma", 12, "bold"),
                 anchor="w", fg_color="transparent", text_color="#111111").grid(row=0, column=0, padx=(10, 4), pady=8, sticky="w")
    ctk.CTkLabel(header, text="complete", font=("tahoma", 12, "bold"), width=90,
                 fg_color="transparent", text_color="#111111").grid(row=0, column=1, padx=2, pady=8)
    ctk.CTkLabel(header, text="prc patterns", font=("tahoma", 12, "bold"), width=90,
                 fg_color="transparent", text_color="#111111").grid(row=0, column=2, padx=2, pady=8)
    ctk.CTkButton(header, text="✕", width=34, height=28, fg_color="#e0e0e0",
                  hover_color="#cfcfcf", text_color="#333333",
                  command=win.destroy).grid(row=0, column=3, padx=(2, 8), pady=6)

    body = ctk.CTkScrollableFrame(win, fg_color=BG, corner_radius=0)
    body.pack(fill="both", expand=True)

    footer = ctk.CTkLabel(win, text="", fg_color=HEADER_BG, text_color="#444444",
                          corner_radius=0, font=("tahoma", 10))
    footer.pack(fill="x", side="bottom", ipady=4)

    def populate():
        _force_reload_cp(app)
        df_now = getattr(app, "cp_df", None)
        summary = summarize_cp_data(df_now) if df_now is not None else []
        for child in body.winfo_children():
            child.destroy()
        if not summary:
            ctk.CTkLabel(body, text="ไม่มีข้อมูล SKU ใน CP Data", fg_color="transparent",
                         text_color="#666666").pack(pady=30)
        else:
            for i, item in enumerate(summary):
                sku = item["sku"]
                show_detail = lambda s=sku: open_price_list_window(app, s)
                row_bg = BG if i % 2 == 0 else "#fafafa"
                row = ctk.CTkFrame(body, fg_color=row_bg, corner_radius=0)
                row.pack(fill="x")
                row.grid_columnconfigure(0, weight=1)
                _make_link(row, sku, show_detail).grid(row=0, column=0, padx=(10, 4), pady=3, sticky="w")
                _make_link(row, str(item["complete"]), show_detail, width=90, anchor="center").grid(
                    row=0, column=1, padx=2, pady=3)
                _make_link(row, str(item["prc_patterns"]), show_detail, width=90, anchor="center").grid(
                    row=0, column=2, padx=2, pady=3)
                ctk.CTkFrame(body, height=1, fg_color=LINE, corner_radius=0).pack(fill="x")
        total_patterns = sum(item["prc_patterns"] for item in summary)
        footer.configure(text=f"SKU ทั้งหมด: {len(summary)}  |  ราคาไม่ซ้ำรวม: {total_patterns} รูปแบบ")

    populate()
    _register(win, populate)


def _sku_price_rows(app, sku: str) -> list[dict]:
    path = _cp_path(app)
    if not path or not os.path.exists(path):
        return []
    try:
        rows = read_cp_rows(path)
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
    win = ctk.CTkToplevel(app.root if hasattr(app, "root") else app)
    win.title(f"-/{sku}")
    win.geometry("560x480")
    win.attributes("-topmost", True)
    win.grab_set()
    win.configure(fg_color=BG)

    header = ctk.CTkFrame(win, fg_color=HEADER_BG, corner_radius=0, height=40)
    header.pack(fill="x", side="top")
    header.grid_propagate(False)
    header.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(header, text=f"-/{sku}", font=("tahoma", 12, "bold"), anchor="w",
                 fg_color="transparent", text_color="#111111").grid(row=0, column=0, padx=(10, 4), pady=8, sticky="w")
    ctk.CTkButton(header, text="+ Add new", width=90, height=28, fg_color="#2b5b84",
                  hover_color="#1e3f5c", text_color="#ffffff",
                  command=lambda: _add_new_price(app, sku, win)).grid(row=0, column=1, padx=2, pady=6)
    ctk.CTkButton(header, text="✕", width=34, height=28, fg_color="#e0e0e0",
                  hover_color="#cfcfcf", text_color="#333333",
                  command=win.destroy).grid(row=0, column=2, padx=(2, 8), pady=6)
    header.grid_columnconfigure(1, weight=0)
    header.grid_columnconfigure(2, weight=0)

    col_header = ctk.CTkFrame(win, fg_color="#f7f7f7", corner_radius=0, height=30)
    col_header.pack(fill="x", side="top")
    col_header.grid_propagate(False)
    col_header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(col_header, text="price list", font=("tahoma", 11, "bold"), anchor="w",
                 fg_color="transparent", text_color="#111111").grid(row=0, column=0, padx=(14, 4), pady=4, sticky="w")
    ctk.CTkLabel(col_header, text="complete", font=("tahoma", 11, "bold"), width=90,
                 fg_color="transparent", text_color="#111111").grid(row=0, column=1, padx=2, pady=4)
    ctk.CTkLabel(col_header, text="patterns", font=("tahoma", 11, "bold"), width=90,
                 fg_color="transparent", text_color="#111111").grid(row=0, column=2, padx=2, pady=4)

    body = ctk.CTkScrollableFrame(win, fg_color=BG, corner_radius=0)
    body.pack(fill="both", expand=True)

    footer = ctk.CTkLabel(win, text="", fg_color=HEADER_BG, text_color="#444444",
                          corner_radius=0, font=("tahoma", 10))
    footer.pack(fill="x", side="bottom", ipady=4)

    def populate():
        rows = _sku_price_rows(app, sku)
        groups = _price_groups(rows)
        for child in body.winfo_children():
            child.destroy()
        if not groups:
            ctk.CTkLabel(body, text="ยังไม่มีราคาสำหรับ SKU นี้", fg_color="transparent",
                         text_color="#666666").pack(pady=30)
        else:
            for i, (price, prows) in enumerate(groups.items()):
                complete = sum(1 for r in prows if _row_complete(r))
                patterns = len({pattern_key(r) for r in prows})
                show_detail = lambda p=price: open_pattern_detail_window(app, sku, p)
                row_bg = BG if i % 2 == 0 else "#fafafa"
                row = ctk.CTkFrame(body, fg_color=row_bg, corner_radius=0)
                row.pack(fill="x")
                row.grid_columnconfigure(0, weight=1)
                _make_link(row, _fmt_price(price), show_detail).grid(
                    row=0, column=0, padx=(14, 4), pady=4, sticky="w")
                ctk.CTkLabel(row, text=str(complete), width=90,
                             fg_color="transparent", text_color="#111111").grid(row=0, column=1, padx=2, pady=4)
                ctk.CTkLabel(row, text=str(patterns), width=90,
                             fg_color="transparent", text_color="#111111").grid(row=0, column=2, padx=2, pady=4)
                ctk.CTkFrame(body, height=1, fg_color=LINE, corner_radius=0).pack(fill="x")
        total_patterns = sum(len({pattern_key(r) for r in prows}) for prows in groups.values())
        footer.configure(text=f"ราคาทั้งหมด: {len(groups)} รูปแบบ  |  รวม patterns: {total_patterns}")

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
    price_str = _fmt_price(price)
    win = ctk.CTkToplevel(app.root if hasattr(app, "root") else app)
    win.title(f"-/{sku}/{price_str}")
    win.geometry("720x560")
    win.attributes("-topmost", True)
    win.grab_set()
    win.configure(fg_color=BG)

    header = ctk.CTkFrame(win, fg_color=HEADER_BG, corner_radius=0, height=40)
    header.pack(fill="x", side="top")
    header.grid_propagate(False)
    header.grid_columnconfigure(0, weight=1)

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
    ctk.CTkButton(header, text="✕", width=34, height=28, fg_color="#e0e0e0",
                  hover_color="#cfcfcf", text_color="#333333",
                  command=win.destroy).grid(row=0, column=3, padx=(2, 8), pady=6)
    header.grid_columnconfigure(1, weight=0)
    header.grid_columnconfigure(2, weight=0)
    header.grid_columnconfigure(3, weight=0)

    body = ctk.CTkScrollableFrame(win, fg_color=BG, corner_radius=0)
    body.pack(fill="both", expand=True)

    footer = ctk.CTkLabel(win, text="", fg_color=HEADER_BG, text_color="#444444",
                          corner_radius=0, font=("tahoma", 10))
    footer.pack(fill="x", side="bottom", ipady=4)

    def populate():
        path = _cp_path(app)
        rows = [r for r in _sku_price_rows(app, sku) if r["_price"] == float(price)]
        for child in body.winfo_children():
            child.destroy()
        if not rows:
            ctk.CTkLabel(body, text="ยังไม่มี pattern สำหรับราคานี้ — กด + Add pattern",
                         fg_color="transparent", text_color="#666666").pack(pady=30)
        for i, rec in enumerate(rows):
            _build_pattern_card(body, app, sku, price, rec, i, path)
        complete = sum(1 for r in rows if _row_complete(r))
        patterns = len({pattern_key(r) for r in rows})
        footer.configure(text=f"patterns: {patterns} (จาก {len(rows)} แถว)  |  complete: {complete}")

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


def _save_pattern_with_remark(app, path, excel_row, entries: dict, remark_box, status_lbl, except_win=None):
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


def _build_pattern_card(body, app, sku: str, price: float, rec: dict, index: int, path: str):
    excel_row = rec["_excel_row"]
    card = ctk.CTkFrame(body, fg_color="#ffffff", corner_radius=6, border_width=1, border_color=LINE)
    card.pack(fill="x", padx=6, pady=5)

    top = ctk.CTkFrame(card, fg_color="#f7f7f7", corner_radius=6, height=30)
    top.pack(fill="x", padx=6, pady=(6, 2))
    top.pack_propagate(False)
    ctk.CTkLabel(top, text=f"No. {index + 1}", font=("tahoma", 11, "bold"),
                 fg_color="transparent", text_color="#111111").pack(side="left", padx=8)
    state = "complete" if _row_complete(rec) else "incomplete"
    ctk.CTkLabel(top, text=state, font=("tahoma", 9),
                 text_color=OK_COLOR if _row_complete(rec) else BAD_COLOR,
                 fg_color="transparent").pack(side="left", padx=4)
    ctk.CTkButton(top, text="ลบ", width=50, height=24, fg_color="#c94f4f",
                  hover_color="#a83e3e", text_color="#ffffff",
                  command=lambda r=rec, n=index + 1: _delete_pattern(app, sku, price, r, n)).pack(side="right", padx=8, pady=3)

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
                                                            except_win=card.winfo_toplevel())).pack(side="right", padx=4)
