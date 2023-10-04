import json
import os

import os
# file_path = os.path.join('test', 'to_exe_test', 'exe_with_excel', 'thai_address_pattern.json')

# file_path = 'test/to_exe_test/exe_with_excel/thai_address_pattern.json'
file_path= 'thai_address_pattern.json'
try:
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
 
    print("ก่อนใช้ print(data[0:2]) ")
 
    print(data[0:2])
  
    print("หลังจากใช้ print(data[0:2]) ")
   
except Exception as err:
    print("พัง", err)
input("Press Enter to end the script")