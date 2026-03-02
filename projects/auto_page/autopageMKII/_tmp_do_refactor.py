# -*- coding: utf-8 -*-
"""Splice refactored tax_address_corrector code into both autopage files."""
import os

def splice_file(filepath, start_line, end_line, new_code_path):
    """Replace lines [start_line, end_line] (1-indexed, inclusive) with content from new_code_path."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Detect line ending
    line_ending = '\r\n' if (lines and lines[0].endswith('\r\n')) else '\n'

    with open(new_code_path, 'r', encoding='utf-8') as f:
        new_code = f.read()

    # Normalize line endings in new code to match target file
    new_code = new_code.replace('\r\n', '\n').replace('\n', line_ending)

    # Ensure new code ends with a line ending
    if not new_code.endswith(line_ending):
        new_code += line_ending

    new_lines = new_code.splitlines(True)

    # 0-indexed conversion
    start_idx = start_line - 1
    end_idx = end_line  # exclusive for slice

    old_count = end_idx - start_idx
    print(f"File: {os.path.basename(filepath)}")
    print(f"  Replacing lines {start_line}-{end_line} ({old_count} lines)")
    print(f"  With {len(new_lines)} new lines")

    lines[start_idx:end_idx] = new_lines

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"  Done! New total lines: {len(lines)}")
    print()


# Paths
base_dir = r'c:\Users\Satawad_Ta\Documents\GitHub\Python\projects\auto_page\autopageMKII'
new_code = os.path.join(base_dir, '_tmp_refactored_tax_addr.py')

main_file = os.path.join(base_dir, 'autopage_MKII_ver4_2_1.py')
lite_file = os.path.join(base_dir, 'autopage_MKII_ver4_2_1LITE.py')

# Main file: tax_address_corrector is at lines 6237-6478
splice_file(main_file, 6237, 6478, new_code)

# LITE file: tax_address_corrector is at lines 6254-6482
splice_file(lite_file, 6254, 6482, new_code)

print("All done!")
