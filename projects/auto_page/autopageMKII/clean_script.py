import tokenize
import io
import re

def remove_comments(source_code):
    io_obj = io.StringIO(source_code)
    out = ""
    last_lineno = -1
    last_col = 0
    for tok in tokenize.generate_tokens(io_obj.readline):
        token_type = tok[0]
        token_string = tok[1]
        start_line, start_col = tok[2]
        end_line, end_col = tok[3]
        
        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            out += (" " * (start_col - last_col))
            
        if token_type == tokenize.COMMENT:
            pass
        else:
            out += token_string
            
        last_col = end_col
        last_lineno = end_line
    return out

def clean_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    cleaned = remove_comments(source)
    
    # Clean up excess empty lines (e.g. more than 2 empty lines -> 2 empty lines)
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(cleaned)

if __name__ == "__main__":
    clean_file('autopage_MKII_ver4_2_1LITE.py')
