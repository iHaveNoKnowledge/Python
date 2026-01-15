import pandas as pd
import numpy as np

# Simulate the splitting function
def split_lazada_address_special_char(row):
    addr = str(row['รายละเอียดที่อยู่'])
    current_sub_district = row['billingAddr2']
    
    if '\u00B7' in addr:
        parts = addr.split('\u00B7')
        if len(parts) >= 2:
            main_addr = parts[0].strip()
            sub_part = parts[1].strip()
            
            # Clean English part from sub_part
            if '/' in sub_part:
                sub_part = sub_part.split('/')[0].strip()
                
            return main_addr, sub_part
    
    return addr, current_sub_district

# Create test data
data = {
    'รายละเอียดที่อยู่': [
        '108 ม.12 · สระตะเคียน/ Sa Takhian',
        '99/9 หมู่ 1 · บางพลีใหญ่/ Bang Phli Yai',
        'Normal Address 123',
        '123/45 · ตำบลในเมือง/ Nai Mueang'
    ],
    'billingAddr2': [
        'Old SubDistrict',
        '',
        'Existing SubDistrict',
        'Should be Overwritten'
    ]
}

df = pd.DataFrame(data)

print("="*60)
print("BEFORE PROCESSING")
print("="*60)
print(df)
print("\n")

# Apply logic
address_split_result = df.apply(split_lazada_address_special_char, axis=1, result_type='expand')
df['รายละเอียดที่อยู่'] = address_split_result[0]
df['billingAddr2'] = address_split_result[1]

print("="*60)
print("AFTER PROCESSING")
print("="*60)
print(df)

# Verification checks
print("\n" + "="*60)
print("VERIFICATION RESULTS")
print("="*60)

# Check 1: 108 ม.12 · สระตะเคียน/ Sa Takhian
row0 = df.iloc[0]
if row0['รายละเอียดที่อยู่'] == '108 ม.12' and row0['billingAddr2'] == 'สระตะเคียน':
    print("✓ Test Case 1: PASS (Split and clean English)")
else:
    print(f"❌ Test Case 1: FAIL - Got '{row0['รายละเอียดที่อยู่']}' | '{row0['billingAddr2']}'")

# Check 2: 99/9 หมู่ 1 · บางพลีใหญ่/ Bang Phli Yai
row1 = df.iloc[1]
if row1['รายละเอียดที่อยู่'] == '99/9 หมู่ 1' and row1['billingAddr2'] == 'บางพลีใหญ่':
    print("✓ Test Case 2: PASS (Split and clean English with empty initial subdistrict)")
else:
    print(f"❌ Test Case 2: FAIL - Got '{row1['รายละเอียดที่อยู่']}' | '{row1['billingAddr2']}'")

# Check 3: Normal Address
row2 = df.iloc[2]
if row2['รายละเอียดที่อยู่'] == 'Normal Address 123' and row2['billingAddr2'] == 'Existing SubDistrict':
    print("✓ Test Case 3: PASS (No change for normal address)")
else:
    print(f"❌ Test Case 3: FAIL - Got '{row2['รายละเอียดที่อยู่']}' | '{row2['billingAddr2']}'")
