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
    
    if 'failed_reason' in df_failed.columns:
        df_failed['detail'] = df_failed['failed_reason']
    else:
        df_failed['detail'] = ''
        
    if 'tracking' in df_completed.columns:
        df_completed['detail'] = df_completed['tracking']
    else:
        df_completed['detail'] = ''
        
    df_failed['file_label'] = label
    df_completed['file_label'] = label
    
    combined = pd.concat([df_failed[['orders', 'timestamp', 'status_type', 'detail', 'file_label']],
                          df_completed[['orders', 'timestamp', 'status_type', 'detail', 'file_label']]], 
                         ignore_index=True)
    combined = combined.dropna(subset=['timestamp']).sort_values(by='timestamp').reset_index(drop=True)
    return combined

df1 = load_file(file1, "15-07-2026 File")
df2 = load_file(file2, "16-07-2026 File")

# Let's combine both files into one master timeline
combined_all = pd.concat([df1, df2], ignore_index=True).sort_values(by='timestamp').reset_index(drop=True)

# Segment into sessions based on time gap > 15 minutes (900s) or > 10 minutes (600s) or > 5 minutes (300s)
# Let's test a gap threshold of 10 minutes (600 seconds)
GAP_THRESHOLD = 600 # 10 minutes

combined_all['time_diff_global'] = combined_all['timestamp'].diff().dt.total_seconds()
session_ids = []
curr_sess = 1
for i, r in combined_all.iterrows():
    if i == 0:
        session_ids.append(curr_sess)
    else:
        if r['time_diff_global'] > GAP_THRESHOLD:
            curr_sess += 1
        session_ids.append(curr_sess)

combined_all['session_id'] = session_ids

print(f"=== SUMMARY BY SESSION (GAP THRESHOLD = {GAP_THRESHOLD//60} MINS) ===")
summary_rows = []

for sess_id, group in combined_all.groupby('session_id'):
    group = group.sort_values(by='timestamp').reset_index(drop=True)
    
    # Calculate time diff within this session only
    group['intra_diff'] = group['timestamp'].diff().dt.total_seconds()
    
    start_t = group['timestamp'].min()
    end_t = group['timestamp'].max()
    date_str = start_t.strftime('%Y-%m-%d')
    time_range_str = f"{start_t.strftime('%H:%M:%S')} - {end_t.strftime('%H:%M:%S')}"
    
    total_ord = len(group)
    comp_ord = (group['status_type'] == 'Completed').sum()
    fail_ord = (group['status_type'] == 'Failed').sum()
    succ_rate = (comp_ord / total_ord * 100) if total_ord > 0 else 0
    
    duration_sec = (end_t - start_t).total_seconds()
    duration_min = duration_sec / 60.0
    
    # Intra-session order processing times (excluding the first order which has no previous order in session)
    intra_diffs = group['intra_diff'].dropna()
    avg_sec = intra_diffs.mean() if len(intra_diffs) > 0 else np.nan
    median_sec = intra_diffs.median() if len(intra_diffs) > 0 else np.nan
    min_sec = intra_diffs.min() if len(intra_diffs) > 0 else np.nan
    max_sec = intra_diffs.max() if len(intra_diffs) > 0 else np.nan
    
    # Orders per hour calculations:
    # 1. Effective rate = Total Orders / (Total Duration in Hours) -- valid when duration > 0
    # 2. Pace rate = 3600 / avg_sec -- average speed per order
    orders_per_hr_effective = (total_ord / (duration_sec / 3600.0)) if duration_sec > 0 else total_ord
    orders_per_hr_pace = (3600.0 / avg_sec) if (pd.notnull(avg_sec) and avg_sec > 0) else np.nan
    
    summary_rows.append({
        'session_id': sess_id,
        'date': date_str,
        'time_range': time_range_str,
        'duration_min': round(duration_min, 1),
        'total_orders': total_ord,
        'completed': comp_ord,
        'failed': fail_ord,
        'success_rate_pct': round(succ_rate, 2),
        'avg_sec_per_order': round(avg_sec, 2) if pd.notnull(avg_sec) else None,
        'median_sec_per_order': round(median_sec, 2) if pd.notnull(median_sec) else None,
        'min_sec': round(min_sec, 1) if pd.notnull(min_sec) else None,
        'max_sec': round(max_sec, 1) if pd.notnull(max_sec) else None,
        'orders_per_hr_effective': round(orders_per_hr_effective, 1),
        'orders_per_hr_pace': round(orders_per_hr_pace, 1) if pd.notnull(orders_per_hr_pace) else None,
        'files': ", ".join(group['file_label'].unique())
    })

df_summary = pd.DataFrame(summary_rows)
print(df_summary.to_string())

