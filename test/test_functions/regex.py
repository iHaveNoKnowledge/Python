import re


def test_regex(item):
    prog = re.search(r'[^-]-(.*)',item)
    result = prog.group(1)
    print(result)
    

item1 = "C6969-นายตชด"
item2 = "C6969-นายตชด-ประชดเชื้อ"
test_regex(item1)