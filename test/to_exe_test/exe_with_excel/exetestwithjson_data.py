import json
import os
import sys

sys.path.insert(1, 'G://VSC//FreeRoam//freeroam2//Python//test//to_exe_test//exe_with_excel')
current_dir = os.getcwd()
print("ตอนนี้: ", current_dir)

json_file = r"thai_address_pattern.json"
with open(json_file,"r", encoding="utf-8") as file:
    data = json.load(file)
print(data[0:2])