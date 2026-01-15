import pandas as pd

# Read both files
input_path = r'c:\Users\Satawad_Ta\Documents\GitHub\Python\8aa11b7072bf095b01f6ffc60a31e77e.xlsx'
output_path = r'c:\Users\Satawad_Ta\Documents\GitHub\Python\output_test.xlsx'

df_input = pd.read_excel(input_path)
df_output = pd.read_excel(output_path)

with open('comparison_result.txt', 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("BRANCH CLASSIFICATION VERIFICATION\n")
    f.write("="*80 + "\n\n")
    
    # Output file analysis
    f.write(f"OUTPUT FILE: output_test.xlsx\n")
    f.write(f"Total rows: {len(df_output)}\n\n")
    
    if 'ประเภทสาขา' in df_output.columns and 'รหัสประจำสาขา' in df_output.columns:
        f.write("Branch Type Distribution:\n")
        f.write(str(df_output['ประเภทสาขา'].value_counts()) + "\n\n")
        
        f.write("Sample Data (first 20 rows):\n")
        f.write("="*80 + "\n")
        sample = df_output[['รหัสประจำสาขา', 'ประเภทสาขา']].head(20)
        f.write(sample.to_string() + "\n\n")
        
        # Validation checks
        f.write("="*80 + "\n")
        f.write("VALIDATION CHECKS\n")
        f.write("="*80 + "\n\n")
        
        # Check 1: Branches with numbers marked as HQ
        has_number_but_hq = df_output[
            (df_output['รหัสประจำสาขา'].notna()) & 
            (df_output['รหัสประจำสาขา'] != '') & 
            (df_output['ประเภทสาขา'] == 'สำนักงานใหญ่')
        ]
        
        if len(has_number_but_hq) > 0:
            f.write(f"❌ FAIL: Found {len(has_number_but_hq)} branches with numbers marked as 'สำนักงานใหญ่'\n")
            f.write(has_number_but_hq[['รหัสประจำสาขา', 'ประเภทสาขา']].to_string() + "\n\n")
        else:
            f.write("✓ PASS: No branches with numbers incorrectly marked as 'สำนักงานใหญ่'\n\n")
        
        # Check 2: Branches without numbers marked as sub-branch
        no_number_but_branch = df_output[
            ((df_output['รหัสประจำสาขา'].isna()) | (df_output['รหัสประจำสาขา'] == '')) & 
            (df_output['ประเภทสาขา'] == 'สาขาย่อย')
        ]
        
        if len(no_number_but_branch) > 0:
            f.write(f"⚠ WARNING: Found {len(no_number_but_branch)} rows without branch number but marked as 'สาขาย่อย'\n")
            f.write(no_number_but_branch[['รหัสประจำสาขา', 'ประเภทสาขา']].head(10).to_string() + "\n\n")
        else:
            f.write("✓ PASS: All 'สาขาย่อย' entries have branch numbers\n\n")
        
        # Check 3: HQ entries should have empty branch numbers
        hq_with_number = df_output[
            (df_output['ประเภทสาขา'] == 'สำนักงานใหญ่') &
            (df_output['รหัสประจำสาขา'].notna()) &
            (df_output['รหัสประจำสาขา'] != '')
        ]
        
        if len(hq_with_number) > 0:
            f.write(f"❌ FAIL: Found {len(hq_with_number)} HQ entries with branch numbers\n")
            f.write(hq_with_number[['รหัสประจำสาขา', 'ประเภทสาขา']].to_string() + "\n\n")
        else:
            f.write("✓ PASS: All 'สำนักงานใหญ่' entries have empty branch numbers\n\n")

print("Analysis complete! Check comparison_result.txt")
