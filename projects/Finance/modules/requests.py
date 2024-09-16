import requests


class InvRequest:
    def __init__(self, inv_no, session_id, token):
        self.inv_no = inv_no
        self.session_id = session_id
        self.token = token
        
        cookies = {
            'JSESSIONID': self.session_id,
            'JWT-TOKEN': self.token,
        }

        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            # 'Cookie': 'JSESSIONID=BE5975F05D8C666F34CB203A852818AC; JWT-TOKEN=eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI2MjA3OCwxODAsMjA4LGVuX1VTLEMxIiwiaWF0IjoxNzI0MjEyMDUzfQ.nIrlhuxaj021RMkhb7Aae44MziF2Gj7hAxIsxCsdLDw',
            'Origin': 'http://192.168.0.11:8080',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }

        data = {
            'requestText': inv_no,
        }

        response = requests.post(
            'http://192.168.0.11:8080/smartcore/smartpos/getInvoiceNoByStoreId.htm',
            cookies=cookies,
            headers=headers,
            data=data,
            verify=False,
        )

        res_inv_data = response.json()
        print("response: ", res_inv_data)
