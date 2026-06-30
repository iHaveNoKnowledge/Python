import ast
import sys

with open('autopage_MKII_ver5_2_0LITE.py', 'r', encoding='utf-8') as f:
    content = f.read()

tree = ast.parse(content)

# Get all function names
funcs = []
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        funcs.append(node.name)

# Print unique sorted function names
for name in sorted(set(funcs)):
    print(name)
