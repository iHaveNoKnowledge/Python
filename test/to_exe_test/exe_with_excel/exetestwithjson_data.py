import json
import os, sys



##* ฟังชั่นเทพทำให้ path ต่อกันแบบออโต้สะเมติก ############

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

file_path= 'thai_address_pattern.json'

try:
    with open(resource_path(file_path), "r", encoding="utf-8") as file:
        data = json.load(file)
 
    print("ก่อนใช้ print(data[0:2]) ")
 
    print(data[0:2])
  
    print("หลังจากใช้ print(data[0:2]) ")
   
except Exception as err:
    print("พัง", err)
input("Press Enter to end the script")

# ใช้ได้
# pyinstaller --onefile --add-data "thai_address_pattern.json;./" exetestwithjson_data.py  