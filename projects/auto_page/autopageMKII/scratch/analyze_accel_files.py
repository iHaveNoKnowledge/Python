import sys
import io
import pandas as pd
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

file1 = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode15-07-2026.xlsx"
file2 = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode16-07-2026.xlsx"

def load_and_prepare(file_path):
    xl = pd.ExcelFile(file_path)
    df_failed = xl.parse('Failed_Orders').copy()
    df_completed = xl.parse('Completed_Orders').copy()
    
    df_failed['status_type'] = 'Failed'
    df_completed['status_type'] = 'Completed'
    
    df_failed['timestamp'] = pd.to_datetime(df_failed['timestamp'], format='mixed', errors='coerce')
    df_completed['timestamp'] = pd.to_datetime(df_completed['timestamp'], format='mixed', errors='coerce')
    
    cols = ['orders', 'timestamp', 'status_type']
    if 'failed_reason' in df_failed.columns:
        df_failed['info'] = df_failed['failed_reason']
    else:
        df_failed['info'] = ''
        
    if 'tracking' in df_completed.columns:
        df_completed['info'] = df_completed['tracking']
    else:
        df_completed['info'] = ''
        
    cols_all = ['orders', 'timestamp', 'status_type', 'info']
    combined = pd.concat([df_failed[cols_all], df_completed[cols_all]], ignore_index=True)
    combined = combined.dropna(subset=['timestamp'])
    combined = combined.sort_values(by='timestamp').reset_index(drop=True)
    return combined

df1 = load_and_prepare(file1)
df2 = load_and_prepare(file2)

print(f"File 1 Total rows: {len(df1)}")
print(f"File 1 Date min/max: {df1['timestamp'].min()} to {df1['timestamp'].max()}")

print(f"\nFile 2 Total rows: {len(df2)}")
print(f"File 2 Date min/max: {df2['timestamp'].min()} to {df2['timestamp'].max()}")

# Let's inspect time differences in df1
print("\n--- File 1 Timeline Gaps ---")
df1['time_diff'] = df1['timestamp'].diff().dt.total_seconds()
gaps1 = df1[df1['time_diff'] > 300] # > 5 minutes
for idx, row in gaps1.iterrows():
    prev_r = df1.iloc[idx-1]
    sec = row['time_diff']
    print(f"Gap: {prev_r['timestamp']} -> {row['timestamp']} | Duration: {sec/60:.2f} mins ({sec} s)")

print("\n--- File 2 Timeline Gaps ---")
df2['time_diff'] = df2['timestamp'].diff().dt.total_seconds()
gaps2 = df2[df2['time_diff'] > 300]
for idx, row in gaps2.iterrows():
    prev_r = df2.iloc[idx-1]
    sec = row['time_diff']
    print(f"Gap: {prev_r['timestamp']} -> {row['timestamp']} | Duration: {sec/60:.2f} mins ({sec} s)")
