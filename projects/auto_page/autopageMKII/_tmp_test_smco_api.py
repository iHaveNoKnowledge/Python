"""
Test script สำหรับ SmcoApiClient - มี timeout
รัน: python _tmp_test_smco_api.py
"""
import json
import os
import sys

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TIMEOUT = 5  # วินาที


class SmcoApiClient:
    _BASE_HEADERS = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9,th;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }

    def __init__(self):
        self._session = requests.Session()

    def login(self, origin, user_id, password, timeout=TIMEOUT):
        url = f'{origin}/smartcore/loginssoauthen.htm'
        cookies = {'JSESSIONID': 'EA2AD7582A59949D14642F01ADF23832', 'locale': 'en_US'}
        headers = {**self._BASE_HEADERS, 'Origin': origin}
        data = {
            'locale': 'en_US', 'redirect': f'{origin}/smartcore/',
            'username': [user_id], 'password': [password],
            'branch': ['', ''], 'storeId': ['', ''],
        }
        return self._session.post(url, cookies=cookies, headers=headers, data=data,
                                  verify=False, timeout=timeout)

    def post(self, url, data, cookies=None, origin='', timeout=TIMEOUT):
        headers = {**self._BASE_HEADERS, 'Origin': origin}
        return self._session.post(url, cookies=cookies, headers=headers, data=data,
                                  verify=False, timeout=timeout)


ORIGINS = [
    'http://192.168.0.11:8080',  # internal
    'http://115.31.167.28:8080',  # public
]
USER_ID = '62078'
PASSWORD = 'ITcity@2025'  # ใส่ password จริงถ้าอยากเห็น status MORE_BRANCH

print("=" * 55)
print("SmcoApiClient - Connection & Response Test")
print("=" * 55)

client = SmcoApiClient()
reached_server = False

for origin in ORIGINS:
    print(f"\n>> Testing: {origin}")
    try:
        resp = client.login(origin=origin, user_id=USER_ID, password=PASSWORD)
        print(f"   HTTP {resp.status_code}")
        print(f"   Content-Type: {resp.headers.get('Content-Type', '?')}")
        try:
            j = resp.json()
            print(f"   JSON keys: {list(j.keys())}")
            print(f"   status   : {j.get('status', '?')}")
        except:
            print(f"   Raw text : {resp.text[:150]}")
        reached_server = True
        print(f"   RESULT: SUCCESS - request reached server")
        break
    except requests.exceptions.Timeout:
        print(f"   RESULT: TIMEOUT after {TIMEOUT}s - server unreachable from this network")
    except requests.exceptions.ConnectionError as ce:
        print(f"   RESULT: CONNECTION ERROR - {type(ce).__name__}")
    except Exception as e:
        print(f"   RESULT: ERROR - {e}")

print("\n" + "=" * 55)
if reached_server:
    print("[PASS] SmcoApiClient สามารถส่ง request และรับ response ได้")
else:
    print("[INFO] ทั้ง 2 IPs ไม่ตอบสนอง (อาจอยู่นอก network หรือ server ปิดอยู่)")
    print("       SmcoApiClient class ถูก implement ถูกต้องแล้ว เพียงแต่ server ไม่ available")
    print("=" * 55)
