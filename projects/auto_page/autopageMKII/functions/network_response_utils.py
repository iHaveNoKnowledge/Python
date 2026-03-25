import json
import time


class NetworkResponseCapture:
    """
    Utility class for capturing network responses from performance logs.
    ใช้สำหรับดึง response จาก API โดยจับจาก Chrome DevTools Protocol performance logs
    """
    
    def __init__(self, driver):
        """
        Initialize NetworkResponseCapture
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
    
    def capture_response(self, target_url_part, max_attempts=20, wait_interval=1):
        """
        จับ network response จาก performance logs
        
        Args:
            target_url_part (str): ส่วนของ URL ที่ต้องการจับ เช่น '/getProductMasterInfoPOSV3.htm'
            max_attempts (int): จำนวนครั้งสูงสุดที่จะ poll (default: 20)
            wait_interval (float): ระยะเวลารอระหว่าง poll ในหน่วยวินาที (default: 0.1)
            
        Returns:
            list/dict: Response body ที่ parse เป็น JSON แล้ว หรือ None ถ้าไม่เจอ
            
        Example:
            >>> network_capture = NetworkResponseCapture(driver)
            >>> response = network_capture.capture_response('/api/districts')
            >>> if response:
            >>>     for item in response:
            >>>         print(item['districtNameTh'], item['districtNameEn'])
        """
        try:
            self.driver.execute_cdp_cmd('Network.enable', {})
        except Exception:
            pass
            
        request_ids = []
        request_methods = {}
        
        # * Poll for requestId AND try to fetch body immediately
        for attempt in range(max_attempts):
            logs = self.driver.get_log("performance")
            
            for entry in logs:
                try:
                    msg = json.loads(entry["message"])["message"]
                    
                    if msg["method"] == "Network.requestWillBeSent":
                        req_id = msg["params"]["requestId"]
                        method = msg["params"]["request"].get("method", "")
                        request_methods[req_id] = method
                        
                    elif msg["method"] == "Network.responseReceived":
                        req_id = msg["params"]["requestId"]
                        resp = msg["params"]["response"]
                        url = resp.get("url", "")
                        status = resp.get("status", 0)
                        req_type = msg["params"].get("type", "")
                        
                        if target_url_part in url:
                            method = request_methods.get(req_id, "")
                            # ข้าม preflight (OPTIONS) หรือ request ที่ไม่สำเร็จ
                            if method == "OPTIONS" or req_type == "Preflight":
                                continue
                                
                            # กรองเฉพาะประเภทที่มักจะมี JSON body และ status code 200
                            if req_type in ["XHR", "Fetch"] and status == 200:
                                if req_id not in request_ids:
                                    request_ids.append(req_id)
                                    print(f"Found target response ID: {req_id} (Method: {method}, Type: {req_type}, Status: {status})")
                except Exception:
                    continue
            
            # พยายามดึง body ของ requests ที่เก็บมาได้
            # ทำใน loop เดียวกัน เพื่อให้ยังคงดึง logs ใหม่ได้ถ้าตัวเก่าดึง body ไม่ได้ (เช่น -32000)
            for req_id in request_ids:
                try:
                    res = self.driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": req_id})
                    parsed_response = json.loads(res['body'])
                    print(f"Got response body for request ID: {req_id}")
                    return parsed_response
                except Exception as e:
                    # แสดง error แต่ไม่หยุดการทำงาน (อาจจะเป็น -32000 No resource with given identifier)
                    if "No resource with given identifier found" not in str(e):
                        print(f"capture_response() error for {req_id}: {e}")
                    pass
            
            time.sleep(wait_interval)
        
        if not request_ids:
            print(f"No valid response found for URL part: {target_url_part}")
        else:
            print(f"Could not get response body for request IDs: {request_ids}")
            
        return None
    
    def clear_logs(self):
        """
        Clear performance logs เพื่อลด RAM usage
        ควรเรียกก่อนและหลังการใช้ capture_response()
        """
        try:
            self.driver.get_log('performance')
            print("Cleared performance logs")
        except Exception as e:
            print(f"Could not clear logs: {e}")
            pass
