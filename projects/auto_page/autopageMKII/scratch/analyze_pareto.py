import sys
import io
import pandas as pd
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

file1 = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode15-07-2026.xlsx"
file2 = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode16-07-2026.xlsx"

def load_data():
    xl1 = pd.ExcelFile(file1)
    xl2 = pd.ExcelFile(file2)
    
    df_f1 = xl1.parse('Failed_Orders').copy()
    df_c1 = xl1.parse('Completed_Orders').copy()
    df_f1['file_label'] = 'File 1 (15-07)'
    df_c1['file_label'] = 'File 1 (15-07)'
    
    df_f2 = xl2.parse('Failed_Orders').copy()
    df_c2 = xl2.parse('Completed_Orders').copy()
    df_f2['file_label'] = 'File 2 (16-07)'
    df_c2['file_label'] = 'File 2 (16-07)'
    
    df_f1['status'] = 'Failed'
    df_c1['status'] = 'Completed'
    df_f2['status'] = 'Failed'
    df_c2['status'] = 'Completed'
    
    df_f1['failed_reason'] = df_f1['failed_reason'].fillna('Unknown').astype(str).str.strip()
    df_f2['failed_reason'] = df_f2['failed_reason'].fillna('Unknown').astype(str).str.strip()
    df_c1['failed_reason'] = ''
    df_c2['failed_reason'] = ''
    
    df1 = pd.concat([df_f1, df_c1], ignore_index=True)
    df2 = pd.concat([df_f2, df_c2], ignore_index=True)
    
    df1['timestamp'] = pd.to_datetime(df1['timestamp'], format='mixed', errors='coerce')
    df2['timestamp'] = pd.to_datetime(df2['timestamp'], format='mixed', errors='coerce')
    
    combined = pd.concat([df1[['orders', 'timestamp', 'status', 'failed_reason', 'file_label']],
                          df2[['orders', 'timestamp', 'status', 'failed_reason', 'file_label']]],
                         ignore_index=True)
    combined = combined.dropna(subset=['timestamp']).sort_values(by='timestamp').reset_index(drop=True)
    return combined

df = load_data()

# Segment into Sessions using 600s gap
df['time_diff'] = df['timestamp'].diff().dt.total_seconds()
session_ids = []
curr_sess = 1
for i, r in df.iterrows():
    if i == 0:
        session_ids.append(curr_sess)
    else:
        if r['time_diff'] > 600:
            curr_sess += 1
        session_ids.append(curr_sess)
df['session_id'] = session_ids

print("=== OVERALL PARETO ANALYSIS OF FAILED REASONS ===")
df_failed = df[df['status'] == 'Failed'].copy()
total_failures = len(df_failed)

pareto_df = df_failed['failed_reason'].value_counts().reset_index()
pareto_df.columns = ['failed_reason', 'count']
pareto_df['pct'] = (pareto_df['count'] / total_failures) * 100
pareto_df['cum_pct'] = pareto_df['pct'].cumsum()

print(f"Total Failures: {total_failures}")
print(pareto_df.to_string())

print("\n=== FAILED REASONS BY SESSION ===")
for sess_id, group in df.groupby('session_id'):
    start_t = group['timestamp'].min()
    end_t = group['timestamp'].max()
    tot = len(group)
    comp = (group['status'] == 'Completed').sum()
    fail = (group['status'] == 'Failed').sum()
    succ = (comp / tot * 100) if tot > 0 else 0
    
    print(f"\n--- Session {sess_id} | {start_t.strftime('%Y-%m-%d %H:%M:%S')} - {end_t.strftime('%H:%M:%S')} ---")
    print(f"Total: {tot} | Completed: {comp} | Failed: {fail} | Success Rate: {succ:.2f}%")
    if fail > 0:
        sess_fails = group[group['status'] == 'Failed']['failed_reason'].value_counts()
        for r, c in sess_fails.items():
            r_pct = (c / fail) * 100
            print(f"   - {r}: {c} times ({r_pct:.1f}% of session fails)")

print("\n=== FAILED REASONS BY DATE ===")
df['date'] = df['timestamp'].dt.date
for d, group in df.groupby('date'):
    tot = len(group)
    comp = (group['status'] == 'Completed').sum()
    fail = (group['status'] == 'Failed').sum()
    succ = (comp / tot * 100) if tot > 0 else 0
    print(f"\nDate {d} | Total: {tot} | Completed: {comp} | Failed: {fail} | Success Rate: {succ:.2f}%")
    if fail > 0:
        date_fails = group[group['status'] == 'Failed']['failed_reason'].value_counts()
        for r, c in date_fails.items():
            print(f"   - {r}: {c} times ({(c/fail)*100:.1f}% of day fails, {(c/tot)*100:.1f}% of day total)")
