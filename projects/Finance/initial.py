import json
import os
import sys
from pathlib import Path

if hasattr(sys, '_MEIPASS'):
    base_path = Path(sys._MEIPASS)
    print("อันบน")
else:
    base_path = Path(__file__).parent
    print("อันล่าง")

cache_file_path = base_path / 'cache/cache.json'

with cache_file_path.open('r', encoding='utf-8') as file:
    cache_data = json.load(file)

print(cache_data)

