import json
import os


current_dir = os.getcwd()
print("ตอนนี้: ", current_dir)


with open('thai_address_pattern.json',"r", encoding="utf-8") as file:
    data = json.load(file)
print(data[0:2])