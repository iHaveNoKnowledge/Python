import requests
import json
import pandas as pd
from IPython.display import display

cookies = {
    'JSESSIONID': '51BB6F67D532315FB0130CF12AFD1D82',
    'locale': 'en_US',
    'JWT-TOKEN': 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI2MjA3OCwxODAsMjA4LGVuX1VTLEMxIiwiaWF0IjoxNjk4MzkxNjc4fQ.2Wxb1Yg6MBVc6mAMMrF_SH5gMtFDirE8tbAm6CiTR7Q',
}

headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8;',
    # 'Cookie': 'JSESSIONID=51BB6F67D532315FB0130CF12AFD1D82; locale=en_US; JWT-TOKEN=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI2MjA3OCwxODAsMjA4LGVuX1VTLEMxIiwiaWF0IjoxNjk4MzkxNjc4fQ.2Wxb1Yg6MBVc6mAMMrF_SH5gMtFDirE8tbAm6CiTR7Q',
    'Origin': 'http://192.168.0.11:8080',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
}

data = {
    'activeFlag': 'true',
    'requestText': 'MS6-000168',
    'start': '1',
    'length': '1',
    'order[0][column]': '0',
    'order[0][dir]': 'asc',
    'productId': '',
    'modeScan': 'Y',
}

response = requests.post(
    'http://192.168.0.11:8080/smartcore/smartbook/getProductMongoAutoSearch.htm',
    cookies=cookies,
    headers=headers,
    data=data,
    verify=False,
)

print("Response Status: ",response)
data = response.json()
data = data[0]
file_name = "Output.json"
data_required_props = ["productCode", "productCouponDetail"]

usable_data = {}
for prop in data_required_props:
    usable_data[prop] = data[prop]
# print("usable_data: ", usable_data)

productCode, productCouponDetail = usable_data.values()
print("productCode: ", productCode)
print("productCouponDetail: ", productCouponDetail)

with open(file_name, "w", encoding="utf-8") as json_file:
    json.dump(usable_data, json_file, ensure_ascii=False)
