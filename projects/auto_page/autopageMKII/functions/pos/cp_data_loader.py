import os
import time
import requests
import pandas as pd
from typing import Optional, Dict, Any

DEFAULT_GAS_URL = "https://script.google.com/macros/s/AKfycbwy2qAs1OhIkQZEeSiCR9QlHouxaJYbgwRI4hZiBM7_M3TLsII0cRLn5j-pG2tMVPsrkw/exec"

class DualSourceCPLoader:
    """
    Dual-Source CP Data Loader for Autopage MKII (5.x.x).
    Reads CP Data from both Google Apps Script Web App (Cloud) and Local cp_data.xlsx (Local).
    Provides TTL caching, deduplication guard, smart merging, and fallback safety.
    """
    def __init__(
        self,
        gas_url: str = DEFAULT_GAS_URL,
        local_excel_path: Optional[str] = None,
        cache_ttl_seconds: int = 120,
        request_timeout: int = 8
    ):
        self.gas_url = gas_url
        self.local_excel_path = local_excel_path
        self.cache_ttl_seconds = cache_ttl_seconds
        self.request_timeout = request_timeout
        
        self._cached_df: Optional[pd.DataFrame] = None
        self._last_fetch_time: float = 0
        self._last_local_mtime: float = 0

    def fetch_from_gas(self) -> pd.DataFrame:
        """Fetch CP data from Google Apps Script Web App (GET)"""
        if not self.gas_url:
            return pd.DataFrame()
            
        try:
            resp = requests.get(self.gas_url, timeout=self.request_timeout)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
                    return self._clean_dataframe(df)
            else:
                print(f"[GAS CP Loader] HTTP Status {resp.status_code} received from GAS Web App")
        except Exception as e:
            print(f"[GAS CP Loader Warning] Failed to fetch from Google Sheet API: {e} -> Falling back to Local Excel")
            
        return pd.DataFrame()

    def fetch_from_local_excel(self) -> pd.DataFrame:
        """Fetch CP data from local excel file (cp_data.xlsx)"""
        if not self.local_excel_path or not os.path.exists(self.local_excel_path):
            return pd.DataFrame()
            
        try:
            df = pd.read_excel(self.local_excel_path)
            self._last_local_mtime = os.path.getmtime(self.local_excel_path)
            return self._clean_dataframe(df)
        except Exception as e:
            print(f"[Local CP Loader Warning] Failed to read local excel: {e}")
            return pd.DataFrame()

    def _is_exact_duplicate(self, record_dict: Dict[str, Any]) -> bool:
        """
        ตรวจสอบว่าข้อมูลใน record_dict มีอยู่ใน DataFrame แล้วทุกประการหรือไม่
        (เปรียบเทียบ SKU, sale_price และฟิลด์ข้อมูลสำคัญทั้งหมด เช่น cp_name, suggested_cp, วันที่, remark)
        หากข้อมูลเดิมเหมือนเดิม 100% จะส่งกลับ True เพื่อข้ามการยิง POST ซ้ำซ้อน
        หากมีข้อมูลใหม่หรือมีการเปลี่ยนแปลงค่า จะส่งกลับ False เพื่อให้อัปเดตขึ้น Sheet
        """
        if self._cached_df is None or self._cached_df.empty:
            return False

        target_sku = str(record_dict.get('sku', '')).strip().upper()
        if not target_sku or 'sku' not in self._cached_df.columns:
            return False

        target_price = record_dict.get('sale_price')
        if target_price is None:
            target_price = record_dict.get('expected_price')

        if target_price is None:
            return False

        try:
            target_price = float(target_price)
        except Exception:
            return False

        price_col = 'sale_price' if 'sale_price' in self._cached_df.columns else ('expected_price' if 'expected_price' in self._cached_df.columns else None)
        if not price_col:
            return False

        # Filter by SKU and Price
        df = self._cached_df
        sku_mask = (df['sku'].astype(str).str.strip().str.upper() == target_sku)
        price_mask = (df[price_col] - target_price).abs() <= 0.05
        matched = df[sku_mask & price_mask]

        if matched.empty:
            return False

        # ตรวจสอบฟิลด์สำคัญที่ส่งมา หากมีฟิลด์ใดที่มีค่าใหม่หรือค่าไม่ตรงกับในแถว ให้ถือว่าไม่ใช่ duplicate
        fields_to_check = [
            'cp_name', 'suggested_cp', 'suggested_usage_start_date', 'suggested_usage_end_date',
            'suggested_remark', 'usage_start_date', 'usage_end_date', 'last_order_id',
            'last_used_cp', 'last_adjustment_method', 'last_actual_price'
        ]

        for _, row in matched.iterrows():
            is_match = True
            for field in fields_to_check:
                val = record_dict.get(field)
                if val is not None and str(val).strip() != "":
                    val_str = str(val).strip()
                    row_val = str(row.get(field, '')).strip() if pd.notna(row.get(field)) else ""
                    if val_str != row_val:
                        is_match = False
                        break
            if is_match:
                return True

        return False

    def push_record_to_gas(self, record_dict: Dict[str, Any]) -> bool:
        """
        Push new record to Google Sheet via Google Apps Script (POST)
        Includes client-side deduplication check to save API quota and latency.
        """
        if not self.gas_url:
            return False

        # 🔍 ข้ามการยิง POST หากข้อมูลตรงกับที่มีอยู่ในตารางแล้ว 100%
        if self._is_exact_duplicate(record_dict):
            print(f"[GAS CP Loader] Record already exists identically in cache (SKU: {record_dict.get('sku')}), skipping POST.")
            return True
            
        try:
            resp = requests.post(self.gas_url, json=record_dict, timeout=self.request_timeout)
            if resp.status_code == 200:
                res_data = resp.json()
                if isinstance(res_data, dict) and res_data.get("status") in ("success", "skipped"):
                    print(f"[GAS CP Loader] Successfully synced record to Google Sheet: {record_dict.get('sku')}")
                    # เคลียร์เวลา fetch แคช เพื่อให้รอบถัดไปดึงข้อมูลใหม่ที่เพิ่งซิงค์
                    self._last_fetch_time = 0
                    return True
                else:
                    print(f"[GAS CP Loader] GAS returned response: {res_data}")
            else:
                print(f"[GAS CP Loader] Push failed with HTTP Status {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"[GAS CP Loader] Failed to POST data to Google Sheet: {e}")
            
        return False

    def load_cp_df(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Load and merge CP Data from both sources (Google Sheet + Local Excel)
        """
        now = time.time()
        local_mtime_changed = False
        
        if self.local_excel_path and os.path.exists(self.local_excel_path):
            current_local_mtime = os.path.getmtime(self.local_excel_path)
            if current_local_mtime > self._last_local_mtime:
                local_mtime_changed = True

        if not force_refresh and not local_mtime_changed and self._cached_df is not None:
            if (now - self._last_fetch_time) < self.cache_ttl_seconds:
                return self._cached_df

        df_gas = self.fetch_from_gas()
        df_local = self.fetch_from_local_excel()

        merged_df = self._merge_dfs(df_gas, df_local)
        
        self._cached_df = merged_df
        self._last_fetch_time = now
        return merged_df

    def _merge_dfs(self, df_gas: pd.DataFrame, df_local: pd.DataFrame) -> pd.DataFrame:
        """
        Merge DataFrames from GAS and Local Excel. GAS takes priority.
        """
        if df_gas.empty and df_local.empty:
            return pd.DataFrame()
        if df_gas.empty:
            return df_local
        if df_local.empty:
            return df_gas

        df_gas.columns = [str(c).strip().lower() for c in df_gas.columns]
        df_local.columns = [str(c).strip().lower() for c in df_local.columns]

        # Normalise price column name
        if 'expected_price' in df_gas.columns and 'sale_price' not in df_gas.columns:
            df_gas['sale_price'] = df_gas['expected_price']
        if 'expected_price' in df_local.columns and 'sale_price' not in df_local.columns:
            df_local['sale_price'] = df_local['expected_price']

        combined = pd.concat([df_gas, df_local], ignore_index=True)
        
        if 'sku' in combined.columns:
            combined = combined[combined['sku'].astype(str).str.strip() != ""]
            
            dedup_subset = ['sku']
            if 'sale_price' in combined.columns:
                dedup_subset.append('sale_price')
            elif 'expected_price' in combined.columns:
                dedup_subset.append('expected_price')
            
            combined = combined.drop_duplicates(subset=dedup_subset, keep='first')

        return combined

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean dataframe columns, normalize prices, convert ISO/UTC dates to Bangkok time, and auto-correct inverted date pairs"""
        if df.empty:
            return df

        df = df.copy()
        df.columns = [str(c).strip().lower() for c in df.columns]

        if 'expected_price' in df.columns and 'sale_price' not in df.columns:
            df['sale_price'] = df['expected_price']

        # Normalize numeric columns to float
        for num_col in ['sale_price', 'expected_price', 'oc_amount', 'dc_amount', 'last_actual_price']:
            if num_col in df.columns:
                df.loc[:, num_col] = pd.to_numeric(df[num_col], errors='coerce')

        for date_col in ['usage_start_date', 'usage_end_date', 'suggested_usage_start_date', 'suggested_usage_end_date']:
            if date_col in df.columns:
                def _parse_ts(val):
                    if pd.isna(val) or val is None or str(val).strip() in ('', '-', 'None', 'nan', 'NaT'):
                        return pd.NaT
                    s = str(val).strip()
                    try:
                        # If ISO format with Z or timezone (e.g. from GAS Date object)
                        if 't' in s.lower() and 'z' in s.lower():
                            ts = pd.to_datetime(s, utc=True)
                            # Convert UTC to Asia/Bangkok (+7) and remove timezone info
                            ts = ts.tz_convert('Asia/Bangkok').tz_localize(None)
                            return ts
                        return pd.to_datetime(s, dayfirst=True, errors='coerce')
                    except Exception:
                        return pd.to_datetime(val, dayfirst=True, errors='coerce')

                parsed_series = [_parse_ts(v) for v in df[date_col]]
                df.loc[:, date_col] = parsed_series

        # Auto-correct inverted date pairs if start > end (due to US locale MM/DD vs DD/MM swap)
        def _swap_dt(dt_val):
            if pd.isna(dt_val):
                return dt_val
            try:
                if hasattr(dt_val, 'day') and hasattr(dt_val, 'month'):
                    if 1 <= dt_val.day <= 12 and 1 <= dt_val.month <= 12 and dt_val.day != dt_val.month:
                        return dt_val.replace(month=dt_val.day, day=dt_val.month)
            except Exception:
                pass
            return dt_val

        pair_cols = [
            ('usage_start_date', 'usage_end_date'),
            ('suggested_usage_start_date', 'suggested_usage_end_date')
        ]
        for s_col, e_col in pair_cols:
            if s_col in df.columns and e_col in df.columns:
                for idx in df.index:
                    s_val = df.loc[idx, s_col]
                    e_val = df.loc[idx, e_col]
                    if pd.notna(s_val) and pd.notna(e_val) and s_val > e_val:
                        e_swapped = _swap_dt(e_val)
                        s_swapped = _swap_dt(s_val)
                        if pd.notna(e_swapped) and s_val <= e_swapped:
                            df.loc[idx, e_col] = e_swapped
                        elif pd.notna(s_swapped) and s_swapped <= e_val:
                            df.loc[idx, s_col] = s_swapped
                        elif pd.notna(s_swapped) and pd.notna(e_swapped) and s_swapped <= e_swapped:
                            df.loc[idx, s_col] = s_swapped
                            df.loc[idx, e_col] = e_swapped

        if 'sku' in df.columns:
            df.loc[:, 'sku'] = [str(v).strip() for v in df['sku']]

        return df
