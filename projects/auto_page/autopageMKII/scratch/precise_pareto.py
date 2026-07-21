import sys
import io
import pandas as pd
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

file1 = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode15-07-2026.xlsx"
file2 = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode16-07-2026.xlsx"

def categorize_reason_precise(reason):
    r = str(reason)
    if 'please input serial' in r.lower():
        return '1. Require Serial Number (please input serial)'
    elif 'ราคา/จำนวนไม่ตรงหลังปรับราคา' in r or 'ขอวิธีปรับราคาครับ' in r or 'Price mismatch' in r:
        return '2. Price / Amount Mismatch (ราคา/ส่วนลดไม่ตรง)'
    elif 'ไม่มีสินค้าให้ตรวจสอบและปรับราคา' in r or 'CP/DC not found' in r:
        return '3. No Product / CP-DC Not Found (ไม่มีสินค้าใน Accel/บิล)'
    elif "'in <string>' requires string" in r or "'MyApp' object has no attribute" in r or "'NoneType' object has no attribute" in r:
        return '4. Script / Logic Exception (บั๊กในโค้ดโปรแกรม)'
    elif 'Postal code' in r and 'cannot be found in dropdown' in r:
        return '5. Postal Code Dropdown Not Found (ไม่พบรหัสไปรษณีย์)'
    elif 'ไม่พบออเดอร์' in r and 'ในระบบ Shopee' in r:
        return '6. Order Not Found in Shopee (ไม่พบออเดอร์)'
    elif 'พังระหว่างยืนยันบิล' in r:
        return '7. Selenium / Web Crash (พังระหว่างยืนยันบิล)'
    else:
        return '8. Other Uncategorized Errors'

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
    combined['category'] = combined['failed_reason'].apply(lambda x: categorize_reason_precise(x) if x else '')
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

df_failed = df[df['status'] == 'Failed'].copy()
total_failures = len(df_failed)

print("=== PARETO ANALYSIS (OVERALL 81 FAILURES) ===")
pareto_df = df_failed['category'].value_counts().reset_index()
pareto_df.columns = ['Failure Category', 'Count']
pareto_df['Pct (%)'] = (pareto_df['Count'] / total_failures) * 100
pareto_df['Cum Pct (%)'] = pareto_df['Pct (%)'].cumsum()

print(pareto_df.to_string(index=False))

print("\n=== CROSS TAB BY FILE ===")
ct_file = pd.crosstab(df_failed['category'], df_failed['file_label'], margins=True)
print(ct_file.to_string())

print("\n=== CROSS TAB BY SESSION ===")
ct_sess = pd.crosstab(df_failed['session_id'], df_failed['category'], margins=True)
print(ct_sess.to_string())
