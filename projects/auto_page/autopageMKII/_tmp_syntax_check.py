import ast
import sys

filename = 'autopage_MKII_ver4_2_2LITE.py'
try:
    with open(filename, encoding='utf-8') as f:
        source = f.read()
    tree = ast.parse(source, filename=filename)
    print(f'Syntax OK! Total lines: {source.count(chr(10))}')
    # หา SmcoApiClient class
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'SmcoApiClient':
            methods = [n.name for n in ast.walk(node) if isinstance(n, ast.FunctionDef)]
            print(f'SmcoApiClient found at line {node.lineno}, methods: {methods}')
except SyntaxError as e:
    print(f'SyntaxError: {e}')
    sys.exit(1)
