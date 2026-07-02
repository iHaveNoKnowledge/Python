import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

file_path = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode.xlsx"
xl = pd.ExcelFile(file_path)

df_failed = xl.parse('Failed_Orders')
df_completed = xl.parse('Completed_Orders')

df_failed['timestamp'] = pd.to_datetime(df_failed['timestamp'])
df_completed['timestamp'] = pd.to_datetime(df_completed['timestamp'])

target_date = '2026-07-02'
df_failed_today = df_failed[df_failed['timestamp'].dt.date == pd.to_datetime(target_date).date()].copy()
df_completed_today = df_completed[df_completed['timestamp'].dt.date == pd.to_datetime(target_date).date()].copy()

df_failed_today['event_status'] = 'Failed'
df_completed_today['event_status'] = 'Completed'

cols = ['timestamp', 'orders', 'event_status']
combined = pd.concat([df_failed_today[cols], df_completed_today[cols]], ignore_index=True)
combined = combined.sort_values(by='timestamp').reset_index(drop=True)

# Count events per hour/10 minutes
combined.set_index('timestamp', inplace=True)
resampled_10m = combined.resample('10min').size()

print("--- Operations count per 10-minute interval on 2026-07-02 ---")
for dt, val in resampled_10m.items():
    if val > 0:
        print(f"Time: {dt.strftime('%H:%M')} - {(dt + pd.Timedelta(minutes=10)).strftime('%H:%M')} | Count: {val}")
