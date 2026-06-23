import re

# Mock classes or functions to test the exact regex logic

def tax_name_formatter_old(name: str) -> str:
    name_edited = name.replace('\u200b', '').strip()
    name_edited = re.sub(r'เลขประจำตัวผู้เสียภาษี\s*[\d-]*', '', name_edited).strip()
    name_edited = re.sub(r'TAX\s*ID:?\s*[\d-]*', '', name_edited, flags=re.IGNORECASE).strip()

    head_office_patterns = [
        r'\(สำนักงานใหญ่\)', r'สำนักงานใหญ่',
        r'\(สํานักงานใหญ่\)', r'สํานักงานใหญ่',
        r'\(สนญ\.?\)', r'สนญ\.?',
        r'\(00000\)',
    ]

    branch_patterns = [
        r'\(สาขา.*?\)',
        r'สาขา\s*\d+'
    ]

    extracted_suffix = ""
    for pattern in head_office_patterns + branch_patterns:
        match = re.search(pattern, name_edited)
        if match:
            extracted_suffix = match.group()
            if re.match(r'\(?สนญ\.?\)?|\(?00000\)?', extracted_suffix):
                extracted_suffix = "สำนักงานใหญ่"
            name_edited = re.sub(pattern, '', name_edited).strip()
            break

    name_edited = re.sub(r'(.{8,}?)\s*\1+', r'\1', name_edited)

    if name_edited.startswith(("บมจ", "บริษัท มหาชน จำกัด", "บมจ.")) or "มหาชน" in name_edited:
        name_edited = re.sub(r'^(บมจ\.?|บริษัท มหาชน จำกัด|บริษัท|บ\.)', '', name_edited).strip()
        name_edited = re.sub(r'(จำกัด\(มหาชน\)|มหาชน จำกัด|จำกัด)$', '', name_edited).strip()
        if not name_edited.startswith("บริษัท"):
            name_edited = f"บริษัท {name_edited}"
        if not name_edited.endswith("จำกัด (มหาชน)"):
            name_edited = f"{name_edited} จำกัด (มหาชน)"
    elif name_edited.startswith(("หจก", "ห้างหุ้นส่วนจำกัด", "ห.")):
        name_edited = re.sub(r'^(หจก\.?|ห้างหุ้นส่วนจำกัด|ห\.)', '', name_edited).strip()
        if not name_edited.startswith("ห้างหุ้นส่วนจำกัด"):
            name_edited = f"ห้างหุ้นส่วนจำกัด {name_edited}"
    elif name_edited.startswith(("บจก", "บริษัท", "บ.", "บจ.")):
        name_edited = re.sub(r'^(บจก\.?|บริษัท|บ\.|จก\.|บจ\.?)', '', name_edited).strip()
        name_edited = re.sub(r'จำกัด$', '', name_edited).strip()
        if not name_edited.startswith("บริษัท"):
            name_edited = f"บริษัท {name_edited}"
        if not name_edited.endswith("จำกัด"):
            name_edited = f"{name_edited} จำกัด"

    if extracted_suffix:
        name_edited = f"{name_edited} {extracted_suffix}"
    return re.sub(r"\s{2,}", ' ', name_edited).strip()


def tax_name_formatter_new(name: str) -> str:
    name_edited = name.replace('\u200b', '').strip()
    name_edited = re.sub(r'เลขประจำตัวผู้เสียภาษี\s*[\d-]*', '', name_edited).strip()
    name_edited = re.sub(r'TAX\s*ID:?\s*[\d-]*', '', name_edited, flags=re.IGNORECASE).strip()

    head_office_patterns = [
        r'\(\s*สำนักงานใหญ่\s*\)?',
        r'สำนักงานใหญ่',
        r'\(\s*สํานักงานใหญ่\s*\)?',
        r'สํานักงานใหญ่',
        r'\(\s*สนญ\.?\s*\)?',
        r'สนญ\.?',
        r'\(\s*00000\s*\)?',
    ]

    branch_patterns = [
        r'\(\s*สาขา[^)]*\)?',
        r'สาขา\s*\d+'
    ]

    extracted_suffix = ""
    for pattern in head_office_patterns + branch_patterns:
        match = re.search(pattern, name_edited)
        if match:
            extracted_suffix = match.group()
            if re.match(r'\(?สนญ\.?\)?|\(?00000\)?', extracted_suffix):
                extracted_suffix = "สำนักงานใหญ่"
            name_edited = re.sub(pattern, '', name_edited).strip()
            break

    name_edited = re.sub(r'(.{8,}?)\s*\1+', r'\1', name_edited)

    if name_edited.startswith(("บมจ", "บริษัท มหาชน จำกัด", "บมจ.")) or "มหาชน" in name_edited:
        name_edited = re.sub(r'^(บมจ\.?|บริษัท มหาชน จำกัด|บริษัท|บ\.)', '', name_edited).strip()
        name_edited = re.sub(r'(จำกัด\(มหาชน\)|มหาชน จำกัด|จำกัด)$', '', name_edited).strip()
        if not name_edited.startswith("บริษัท"):
            name_edited = f"บริษัท {name_edited}"
        if not name_edited.endswith("จำกัด (มหาชน)"):
            name_edited = f"{name_edited} จำกัด (มหาชน)"
    elif name_edited.startswith(("หจก", "ห้างหุ้นส่วนจำกัด", "ห.")):
        name_edited = re.sub(r'^(หจก\.?|ห้างหุ้นส่วนจำกัด|ห\.)', '', name_edited).strip()
        if not name_edited.startswith("ห้างหุ้นส่วนจำกัด"):
            name_edited = f"ห้างหุ้นส่วนจำกัด {name_edited}"
    elif name_edited.startswith(("บจก", "บริษัท", "บ.", "บจ.")):
        name_edited = re.sub(r'^(บจก\.?|บริษัท|บ\.|จก\.|บจ\.?)', '', name_edited).strip()
        name_edited = re.sub(r'จำกัด\s*[A-Za-z0-9]*$', '', name_edited).strip()
        if not name_edited.startswith("บริษัท"):
            name_edited = f"บริษัท {name_edited}"
        if not name_edited.endswith("จำกัด"):
            name_edited = f"{name_edited} จำกัด"

    if extracted_suffix:
        if extracted_suffix.startswith('(') and not extracted_suffix.endswith(')'):
            extracted_suffix = extracted_suffix + ')'
        name_edited = f"{name_edited} {extracted_suffix}"
    return re.sub(r"\s{2,}", ' ', name_edited).strip()


def clean_desire_name_old(cus_desire_name: str) -> str:
    pattern_prefix = r'^(Base|บริษัท|บจก\.?|หจก\.?|หสม\.?|บมจ.\.?|ห้างหุ้นส่วนจำกัด|ห้างหุ้นส่วนสามัญ|บจ\.?|บ\.)\s*'
    pattern_branch = r'(สำนักงานใหญ่|สํานักงานใหญ่|สนญ\.?|\(สำนักงานใหญ่\)|\(สํานักงานใหญ่\)|\(สนญ\.?\)|\(00000\)|\s*\(?สาขา.*)$'
    pattern_suffix = r'จำกัด(\s*มหาชน)?$'

    cus_desire_name = re.sub(pattern_prefix, '', cus_desire_name)
    cus_desire_name = re.sub(pattern_branch, '', cus_desire_name).strip()
    cus_desire_name = re.sub(pattern_suffix, '', cus_desire_name).strip()

    cus_desire_name = cus_desire_name.replace(" ", "")
    cus_desire_name = cus_desire_name.replace("\n", "")
    cus_desire_name = cus_desire_name.replace("(", "")
    cus_desire_name = cus_desire_name.replace(")", "")
    return cus_desire_name


def clean_desire_name_new(cus_desire_name: str) -> str:
    pattern_prefix = r'^(บริษัท|บจก\.?|หจก\.?|หสม\.?|บมจ.\.?|ห้างหุ้นส่วนจำกัด|ห้างหุ้นส่วนสามัญ|บจ\.?|บ\.)\s*'
    pattern_branch = r'(สำนักงานใหญ่|สํานักงานใหญ่|สนญ\.?|\(สำนักงานใหญ่\)|\(สํานักงานใหญ่\)|\(สนญ\.?\)|\(00000\)|\s*\(?สาขา.*)$'
    pattern_suffix = r'จำกัด(\s*มหาชน)?\s*[A-Za-z0-9]*$'

    cus_desire_name = re.sub(pattern_prefix, '', cus_desire_name)
    cus_desire_name = re.sub(pattern_branch, '', cus_desire_name).strip()
    cus_desire_name = re.sub(pattern_suffix, '', cus_desire_name).strip()

    cus_desire_name = cus_desire_name.replace(" ", "")
    cus_desire_name = cus_desire_name.replace("\n", "")
    cus_desire_name = cus_desire_name.replace("(", "")
    cus_desire_name = cus_desire_name.replace(")", "")
    return cus_desire_name


def add_customer_name_old(name: str, branch_type: str, tax_branch_num: str) -> str:
    name = re.sub(r'\s*\(?(?:สำนักงานใหญ่|สํานักงานใหญ่|สนญ\.?|00000)\)?\s*$', '', name)
    name = re.sub(r'\s*\(?สาขา[^)]*\)?\s*$', '', name)
    name = name.strip()

    if branch_type == 'สำนักงานใหญ่':
        name = f"{name} ({branch_type})"
    elif branch_type == "สาขาย่อย":
        name = f"{name} (สาขา{tax_branch_num})"
    return name


def add_customer_name_new(name: str, branch_type: str, tax_branch_num: str) -> str:
    name = re.sub(r'\s*\(?(?:สำนักงานใหญ่|สํานักงานใหญ่|สนญ\.?|00000)\)?\s*$', '', name)
    name = re.sub(r'\s*\(?สาขา[^)]*\)?\s*$', '', name)
    name = name.strip()

    if branch_type == 'สำนักงานใหญ่':
        name = f"{name} ({branch_type})"
    elif branch_type == "สาขาย่อย":
        name = f"{name} (สาขา{tax_branch_num})"
    return name


# Test cases
test_cases = [
    {
        "input": "บริษัท เด็นทอลพลัส สไมล์รูม คลินิก จำกัด(สาขาศรีสะเกษ",
        "branch_type": "สาขาย่อย",
        "tax_branch_num": "00001",
        "expected_formatted": "บริษัท เด็นทอลพลัส สไมล์รูม คลินิก จำกัด (สาขาศรีสะเกษ)",
        "expected_clean": "เด็นทอลพลัสสไมล์รูมคลินิก",
        "expected_added": "บริษัท เด็นทอลพลัส สไมล์รูม คลินิก จำกัด (สาขา00001)"
    },
    {
        "input": "บริษัท เทพซ่า (69) จำกัด (สาขาหมาแมว",
        "branch_type": "สาขาย่อย",
        "tax_branch_num": "00002",
        "expected_formatted": "บริษัท เทพซ่า (69) จำกัด (สาขาหมาแมว)",
        "expected_clean": "เทพซ่า69",
        "expected_added": "บริษัท เทพซ่า (69) จำกัด (สาขา00002)"
    },
    {
        "input": "บริษัท เมมโมรี่ไอที (00000) จำกัด",
        "branch_type": "สำนักงานใหญ่",
        "tax_branch_num": "",
        "expected_formatted": "บริษัท เมมโมรี่ไอที จำกัด สำนักงานใหญ่",
        "expected_clean": "เมมโมรี่ไอที",
        "expected_added": "บริษัท เมมโมรี่ไอที จำกัด (สำนักงานใหญ่)"
    },
    {
        "input": " บริษัท ไว โอ เดอะ โพสท์ แอคทีฟ จำกัดI",
        "branch_type": "สำนักงานใหญ่",
        "tax_branch_num": "",
        "expected_formatted": "บริษัท ไว โอ เดอะ โพสท์ แอคทีฟ จำกัด",
        "expected_clean": "ไวโอเดอะโพสท์แอคทีฟ",
        "expected_added": "บริษัท ไว โอ เดอะ โพสท์ แอคทีฟ จำกัด (สำนักงานใหญ่)"
    }
]

print("=== RUNNING REGEX TEST COMPARISONS ===")
all_pass = True
for idx, tc in enumerate(test_cases):
    print(f"\nTest Case #{idx+1}: {tc['input']}")
    
    # Old logic
    f_old = tax_name_formatter_old(tc['input'])
    c_old = clean_desire_name_old(f_old)
    a_old = add_customer_name_old(f_old, tc['branch_type'], tc['tax_branch_num'])
    
    # New logic
    f_new = tax_name_formatter_new(tc['input'])
    c_new = clean_desire_name_new(f_new)
    a_new = add_customer_name_new(f_new, tc['branch_type'], tc['tax_branch_num'])
    
    print("  OLD:")
    print(f"    Formatted: {f_old}")
    print(f"    Cleaned:   {c_old}")
    print(f"    Added:     {a_old}")
    
    print("  NEW:")
    print(f"    Formatted: {f_new}")
    print(f"    Cleaned:   {c_new}")
    print(f"    Added:     {a_new}")
    
    if f_new != tc['expected_formatted'] or c_new != tc['expected_clean'] or a_new != tc['expected_added']:
        print("  FAIL!")
        all_pass = False
    else:
        print("  PASS!")

if all_pass:
    print("\n✓ ALL TESTS PASSED SUCCESSFULLY!")
else:
    print("\n❌ SOME TESTS FAILED!")
