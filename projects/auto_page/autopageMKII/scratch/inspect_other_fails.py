import sys
import io
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

file1 = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode15-07-2026.xlsx"
file2 = r"C:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII\tables\Accel_mode16-07-2026.xlsx"

def load_failed():
    xl1 = pd.ExcelFile(file1)
    xl2 = pd.ExcelFile(file2)
    df_f1 = xl1.parse('Failed_Orders').assign(file='File 1')
    df_f2 = xl2.parse('Failed_Orders').assign(file='File 2')
    df_failed = pd.concat([df_f1, df_f2], ignore_index=True)
    df_failed['failed_reason'] = df_failed['failed_reason'].fillna('Unknown').astype(str).str.strip()
    return df_failed

df_failed = load_failed()

# Print detailed failed reasons for category 5
print("=== DETAILED INSPECTION OF ALL FAILED REASONS ===")
vc = df_failed['failed_reason'].value_counts()
for r, count in vc.items():
    print(f"[{count:2d}] {r[:150]}...")
