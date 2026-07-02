import sys
import pandas as pd
import os

file_path = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode.xlsx"
report_path = r"C:\Users\Satawad_Ta\.gemini\antigravity-ide\brain\51dee9ae-acdb-4ae2-9948-5586be4bddbb\analysis_report.md"

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
    lambda r: f"Tracking: {r['tracking']}, Bill: {r['bill_no']}, Status: {r['status']}", axis=1
)

cols = ['timestamp', 'orders', 'event_status', 'info']
combined = pd.concat([df_failed_today[cols], df_completed_today[cols]], ignore_index=True)
combined = combined.sort_values(by='timestamp').reset_index(drop=True)

with open(report_path, "w", encoding="utf-8") as f:
    f.write(f"# Analysis Report for {target_date}\n\n")
    
    total_ops = len(combined)
    failed_ops = len(df_failed_today)
    completed_ops = len(df_completed_today)
    
    f.write("## Overview\n")
    f.write(f"- **Target Date**: {target_date}\n")
    f.write(f"- **Total Operations**: {total_ops}\n")
    f.write(f"- **Completed (Success)**: {completed_ops}\n")
    f.write(f"- **Failed**: {failed_ops}\n\n")
    
    if combined.empty:
        f.write("No operations found on this date.\n")
        sys.exit(0)
        
    combined['time_diff'] = combined['timestamp'].diff()
    diffs_in_seconds = combined['time_diff'].dt.total_seconds().dropna()
    
    f.write("## Time Gap Statistics (seconds)\n")
    f.write("```\n")
    f.write(str(diffs_in_seconds.describe()) + "\n")
    f.write("```\n\n")
    
    # 5-minute threshold
    threshold_seconds = 300
    large_gaps = combined[combined['time_diff'].dt.total_seconds() > threshold_seconds]
    
    f.write(f"## Gaps Greater than {threshold_seconds/60:.1f} Minutes\n")
    if large_gaps.empty:
        f.write("No gaps larger than 5 minutes found.\n\n")
    else:
        f.write("| Gap Duration | Start Time | End Time | Last Order (Before Gap) | Next Order (After Gap) |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for idx in large_gaps.index:
            prev_row = combined.iloc[idx - 1]
            curr_row = combined.iloc[idx]
            duration = curr_row['time_diff']
            
            # format duration
            tot_sec = int(duration.total_seconds())
            h = tot_sec // 3600
            m = (tot_sec % 3600) // 60
            s = tot_sec % 60
            dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            
            prev_str = f"{prev_row['orders']} ({prev_row['event_status']})"
            curr_str = f"{curr_row['orders']} ({curr_row['event_status']})"
            
            f.write(f"| **{dur_str}** | {prev_row['timestamp'].strftime('%H:%M:%S')} | {curr_row['timestamp'].strftime('%H:%M:%S')} | {prev_str} | {curr_str} |\n")
        f.write("\n")
        
    # Detail on what happened before/after each gap
    f.write("## Detailed Context for Large Gaps\n")
    if not large_gaps.empty:
        for idx in large_gaps.index:
            prev_row = combined.iloc[idx - 1]
            curr_row = combined.iloc[idx]
            duration = curr_row['time_diff']
            f.write(f"### Gap of {duration} (from {prev_row['timestamp'].strftime('%H:%M:%S')} to {curr_row['timestamp'].strftime('%H:%M:%S')})\n")
            f.write(f"- **Before Gap**:\n")
            f.write(f"  - Order: `{prev_row['orders']}`\n")
            f.write(f"  - Status: `{prev_row['event_status']}`\n")
            f.write(f"  - Info: {prev_row['info']}\n")
            f.write(f"- **After Gap**:\n")
            f.write(f"  - Order: `{curr_row['orders']}`\n")
            f.write(f"  - Status: `{curr_row['event_status']}`\n")
            f.write(f"  - Info: {curr_row['info']}\n\n")
            
    # List of Failed Reasons today
    f.write("## Failed Reasons on this Day\n")
    if not df_failed_today.empty:
        fail_summary = df_failed_today['info'].value_counts()
        f.write("| Count | Reason |\n")
        f.write("| --- | --- |\n")
        for reason, count in fail_summary.items():
            # Clean up reason strings from newlines/tabs to keep table neat
            clean_reason = str(reason).replace('\n', '<br>').replace('\r', '')
            f.write(f"| {count} | {clean_reason} |\n")
    else:
        f.write("No failed orders on this day.\n")

print("Analysis report generated at:", report_path)
