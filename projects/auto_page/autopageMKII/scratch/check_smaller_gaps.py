import pandas as pd

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
gaps_2_to_5 = combined[(combined['time_diff'].dt.total_seconds() > 120) & (combined['time_diff'].dt.total_seconds() <= 300)]

print(f"Gaps between 2 and 5 minutes: {len(gaps_2_to_5)}")
for idx in gaps_2_to_5.index:
    prev = combined.iloc[idx - 1]
    curr = combined.iloc[idx]
    print(f"Gap: {curr['time_diff']} from {prev['timestamp'].strftime('%H:%M:%S')} to {curr['timestamp'].strftime('%H:%M:%S')}")
    print(f"  Prev: {prev['orders']} ({prev['event_status']})")
    print(f"  Curr: {curr['orders']} ({curr['event_status']}) - {curr['info'][:150]}")
