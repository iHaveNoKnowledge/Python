import json
json_file = r"thai_address_pattern.json"
with open(json_file,"r", encoding="utf-8") as file:
    data = json.load(file)
print(data[0:2])