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
df_failed_today['info'] = df_failed_today['failed_reason']

df_completed_today['event_status'] = 'Completed'
df_completed_today['info'] = df_completed_today.apply(
    lambda r: f"Status: {r['status']}", axis=1
)

cols = ['timestamp', 'orders', 'event_status', 'info']
combined = pd.concat([df_failed_today[cols], df_completed_today[cols]], ignore_index=True)
combined = combined.sort_values(by='timestamp').reset_index(drop=True)

combined['time_diff'] = combined['timestamp'].diff()

# Let's filter for events between 13:30:00 and 15:30:00
filtered = combined[(combined['timestamp'].dt.time >= pd.to_datetime('13:30:00').time()) & 
                    (combined['timestamp'].dt.time <= pd.to_datetime('15:30:00').time())]

print(f"Total events between 13:30 and 15:30: {len(filtered)}")
for idx, row in filtered.iterrows():
    diff_str = f" (+{row['time_diff'].total_seconds():.1f}s)" if pd.notna(row['time_diff']) else ""
    info_clean = str(row['info']).replace('\n', ' ')
    if len(info_clean) > 80:
        info_clean = info_clean[:77] + "..."
    print(f"{row['timestamp'].strftime('%H:%M:%S')}{diff_str} | {row['orders']} | {row['event_status']} | {info_clean}")
