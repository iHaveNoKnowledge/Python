import pandas as pd
import sys

print("=" * 80)
print("COMPARING INPUT (Lazada) vs OUTPUT (Shopee format)")
print("=" * 80)

# Read input file
input_file = '8aa11b7072bf095b01f6ffc60a31e77e.xlsx'
output_file = 'output_test.xlsx'

try:
    df_input = pd.read_excel(input_file)
    print(f"\n✓ INPUT FILE: {input_file}")
    print(f"  Total rows: {len(df_input)}")
    print(f"  Total columns: {len(df_input.columns)}")
    
    # Find branch-related columns
    branch_cols = [col for col in df_input.columns if 'branch' in col.lower() or 'สาขา' in col.lower()]
    print(f"\n  Branch-related columns: {branch_cols}")
    
    # Show sample data
    if branch_cols:
        print(f"\n  Sample branch data (first 10 rows):")
        for col in branch_cols:
            print(f"\n  Column: {col}")
            print(df_input[col].head(10).to_string(index=True))
    
except Exception as e:
    print(f"\n✗ Error reading input file: {e}")
    sys.exit(1)

try:
    df_output = pd.read_excel(output_file)
    print(f"\n\n✓ OUTPUT FILE: {output_file}")
    print(f"  Total rows: {len(df_output)}")
    print(f"  Total columns: {len(df_output.columns)}")
    
    # Find branch-related columns
    branch_cols_out = [col for col in df_output.columns if 'branch' in col.lower() or 'สาขา' in col.lower()]
    print(f"\n  Branch-related columns: {branch_cols_out}")
    
    # Show sample data
    if branch_cols_out:
        print(f"\n  Sample branch data (first 10 rows):")
        for col in branch_cols_out:
            print(f"\n  Column: {col}")
            print(df_output[col].head(10).to_string(index=True))
    
    # Check ประเภทสาขา specifically
    if 'ประเภทสาขา' in df_output.columns:
        print(f"\n\n{'=' * 80}")
        print("BRANCH TYPE ANALYSIS (ประเภทสาขา)")
        print("=" * 80)
        print(f"\nValue counts:")
        print(df_output['ประเภทสาขา'].value_counts())
        
        # Show branch number and type together
        if 'รหัสประจำสาขา' in df_output.columns:
            print(f"\n\nBranch Number vs Branch Type (first 15 rows):")
            comparison = df_output[['รหัสประจำสาขา', 'ประเภทสาขา']].head(15)
            print(comparison.to_string(index=True))
            
            # Check for potential issues
            print(f"\n\n{'=' * 80}")
            print("VALIDATION CHECKS")
            print("=" * 80)
            
            # Check if any branch with number is marked as สำนักงานใหญ่
            has_number_but_hq = df_output[
                (df_output['รหัสประจำสาขา'].notna()) & 
                (df_output['รหัสประจำสาขา'] != '') & 
                (df_output['ประเภทสาขา'] == 'สำนักงานใหญ่')
            ]
            
            if len(has_number_but_hq) > 0:
                print(f"\n⚠ WARNING: Found {len(has_number_but_hq)} rows with branch number but marked as 'สำนักงานใหญ่':")
                print(has_number_but_hq[['รหัสประจำสาขา', 'ประเภทสาขา']].to_string())
            else:
                print(f"\n✓ PASS: No branches with numbers incorrectly marked as 'สำนักงานใหญ่'")
            
            # Check if branches without number are marked as สาขาย่อย
            no_number_but_branch = df_output[
                ((df_output['รหัสประจำสาขา'].isna()) | (df_output['รหัสประจำสาขา'] == '')) & 
                (df_output['ประเภทสาขา'] == 'สาขาย่อย')
            ]
            
            if len(no_number_but_branch) > 0:
                print(f"\n⚠ WARNING: Found {len(no_number_but_branch)} rows without branch number but marked as 'สาขาย่อย':")
                print(no_number_but_branch[['รหัสประจำสาขา', 'ประเภทสาขา']].head(10).to_string())
            else:
                print(f"\n✓ PASS: All 'สาขาย่อย' entries have branch numbers")
    
except Exception as e:
    print(f"\n✗ Error reading output file: {e}")
    sys.exit(1)

print(f"\n\n{'=' * 80}")
print("ANALYSIS COMPLETE")
print("=" * 80)
