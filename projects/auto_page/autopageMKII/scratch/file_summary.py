import sys
import io
import pandas as pd
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

file1 = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode15-07-2026.xlsx"
file2 = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode16-07-2026.xlsx"

def load_file(file_path, label):
    xl = pd.ExcelFile(file_path)
    df_failed = xl.parse('Failed_Orders').copy()
    df_completed = xl.parse('Completed_Orders').copy()
    
    df_failed['status_type'] = 'Failed'
    df_completed['status_type'] = 'Completed'
    
    df_failed['timestamp'] = pd.to_datetime(df_failed['timestamp'], format='mixed', errors='coerce')
    df_completed['timestamp'] = pd.to_datetime(df_completed['timestamp'], format='mixed', errors='coerce')
    
    df_failed['file_label'] = label
    df_completed['file_label'] = label
    
    combined = pd.concat([df_failed[['orders', 'timestamp', 'status_type', 'file_label']],
                          df_completed[['orders', 'timestamp', 'status_type', 'file_label']]], 
                         ignore_index=True)
    combined = combined.dropna(subset=['timestamp']).sort_values(by='timestamp').reset_index(drop=True)
    return combined

df1 = load_file(file1, "Accel_mode15-07-2026.xlsx")
df2 = load_file(file2, "Accel_mode16-07-2026.xlsx")

def get_stats(df, name=""):
    df = df.sort_values(by='timestamp').reset_index(drop=True).copy()
    df['intra_diff'] = df['timestamp'].diff().dt.total_seconds()
    
    # Exclude gaps > 10 mins (600s) when calculating continuous intra-order process time
    continuous_diffs = df[df['intra_diff'] <= 600]['intra_diff']
    
    total = len(df)
    comp = (df['status_type'] == 'Completed').sum()
    fail = (df['status_type'] == 'Failed').sum()
    succ_rate = (comp / total * 100) if total > 0 else 0
    
    start_t = df['timestamp'].min()
    end_t = df['timestamp'].max()
    span_sec = (end_t - start_t).total_seconds()
    span_min = span_sec / 60.0
    
    # Active duration = sum of continuous diffs (i.e. excluding idle gaps > 10 mins)
    active_sec = continuous_diffs.sum()
    active_min = active_sec / 60.0
    
    avg_sec = continuous_diffs.mean() if len(continuous_diffs) > 0 else np.nan
    median_sec = continuous_diffs.median() if len(continuous_diffs) > 0 else np.nan
    
    orders_per_hr_pace = (3600.0 / avg_sec) if (pd.notnull(avg_sec) and avg_sec > 0) else 0
    orders_per_hr_active = (total / (active_sec / 3600.0)) if active_sec > 0 else 0
    
    return {
        'name': name,
        'total': total,
        'completed': comp,
        'failed': fail,
        'succ_rate': round(succ_rate, 2),
        'start_t': start_t,
        'end_t': end_t,
        'span_min': round(span_min, 1),
        'active_min': round(active_min, 1),
        'avg_sec': round(avg_sec, 2) if pd.notnull(avg_sec) else None,
        'median_sec': round(median_sec, 2) if pd.notnull(median_sec) else None,
        'orders_per_hr_pace': round(orders_per_hr_pace, 1),
        'orders_per_hr_active': round(orders_per_hr_active, 1)
    }

print("=== FILE 1 OVERALL ===")
print(get_stats(df1, "File 1"))

print("\n=== FILE 2 OVERALL ===")
print(get_stats(df2, "File 2"))

combined_all = pd.concat([df1, df2], ignore_index=True).sort_values(by='timestamp').reset_index(drop=True)
print("\n=== COMBINED OVERALL ===")
print(get_stats(combined_all, "Combined"))
