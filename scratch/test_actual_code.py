import sys
import os
import re

# Add the directory containing the script to sys.path
sys.path.append(r"c:\Users\hackd\OneDrive\เอกสาร\GitHub\Python\projects\auto_page\autopageMKII")

# Import the class
from autopage_MKII_ver5_1_5LITE import MyApp

# Test name formatter
print("=== TESTING ACTUAL tax_name_formatter CODE FROM FILE ===")

test_cases = [
    ("บริษัท เด็นทอลพลัส สไมล์รูม คลินิก จำกัด(สาขาศรีสะเกษ", "บริษัท เด็นทอลพลัส สไมล์รูม คลินิก จำกัด (สาขาศรีสะเกษ)"),
    ("บริษัท เทพซ่า (69) จำกัด (สาขาหมาแมว", "บริษัท เทพซ่า (69) จำกัด (สาขาหมาแมว)"),
    ("บริษัท เมมโมรี่ไอที (00000) จำกัด", "บริษัท เมมโมรี่ไอที จำกัด สำนักงานใหญ่"),
    (" บริษัท ไว โอ เดอะ โพสท์ แอคทีฟ จำกัดI", "บริษัท ไว โอ เดอะ โพสท์ แอคทีฟ จำกัด")
]

# We will also mock self and test the exact select_cus_name_from_lis cleaning logic from the file
def test_select_cus_name_cleaning(name_in):
    # This is a replica of select_cus_name_from_lis L4015-L4034
    pattern_prefix = r'^(บริษัท|บจก\.?|หจก\.?|หสม\.?|บมจ.\.?|ห้างหุ้นส่วนจำกัด|ห้างหุ้นส่วนสามัญ|บจ\.?|บ\.)\s*'
    pattern_branch = r'(สำนักงานใหญ่|สํานักงานใหญ่|สนญ\.?|\(สำนักงานใหญ่\)|\(สํานักงานใหญ่\)|\(สนญ\.?\)|\(00000\)|\s*\(?สาขา.*)$'
    pattern_suffix = r'จำกัด(\s*มหาชน)?\s*[A-Za-z0-9]*$'
    
    cus_desire_name = name_in.strip()
    cus_desire_name = re.sub(pattern_prefix, '', cus_desire_name)
    cus_desire_name = re.sub(pattern_branch, '', cus_desire_name).strip()
    cus_desire_name = re.sub(pattern_suffix, '', cus_desire_name).strip()

    cus_desire_name = cus_desire_name.replace(" ", "")
    cus_desire_name = cus_desire_name.replace("\n", "")
    cus_desire_name = cus_desire_name.replace("(", "")
    cus_desire_name = cus_desire_name.replace(")", "")
    return cus_desire_name

print("\n--- Running tax_name_formatter ---")
all_pass = True
for inp, exp in test_cases:
    res = MyApp.tax_name_formatter(None, inp)
    print(f"Input:    {inp}")
    print(f"Result:   {res}")
    print(f"Expected: {exp}")
    if res == exp:
        print("PASS")
    else:
        print("FAIL!")
        all_pass = False
    print()

print("\n--- Running select_cus_name_from_lis cleaning logic ---")
cleaned_cases = [
    ("บริษัท เด็นทอลพลัส สไมล์รูม คลินิก จำกัด(สาขาศรีสะเกษ", "เด็นทอลพลัสสไมล์รูมคลินิก"),
    ("บริษัท เทพซ่า (69) จำกัด (สาขาหมาแมว", "เทพซ่า69"),
    (" บริษัท ไว โอ เดอะ โพสท์ แอคทีฟ จำกัดI", "ไวโอเดอะโพสท์แอคทีฟ")
]

for inp, exp in cleaned_cases:
    res = test_select_cus_name_cleaning(inp)
    print(f"Input:    {inp}")
    print(f"Result:   {res}")
    print(f"Expected: {exp}")
    if res == exp:
        print("PASS")
    else:
        print("FAIL!")
        all_pass = False
    print()

if all_pass:
    print("✓ ALL TESTS PASSED!")
else:
    print("❌ SOME TESTS FAILED!")
