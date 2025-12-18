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
    
    def capture_response(self, target_url_part, max_attempts=20, wait_interval=0.1):
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
        request_ids = []
        
        # * Poll for requestId
        for attempt in range(max_attempts):
            logs = self.driver.get_log("performance")
            for entry in logs:
                try:
                    msg = json.loads(entry["message"])["message"]
                    if msg["method"] == "Network.requestWillBeSent":
                        url = msg["params"]["request"]["url"]
                        if target_url_part in url:
                            request_ids.append(msg["params"]["requestId"])
                            print(f"Found request ID: {msg['params']['requestId']}")
                            break
                except:
                    continue
            
            if len(request_ids) > 0:
                print(f"Captured {len(request_ids)} request ID(s)")
                break
            
            time.sleep(wait_interval)
        
        if not request_ids:
            print(f"No request found for URL part: {target_url_part}")
            return None
        
        # * Poll for response
        for attempt in range(max_attempts):
            for req_id in request_ids:
                try:
                    res = self.driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": req_id})
                    parsed_response = json.loads(res['body'])
                    print(f"Got response for request ID: {req_id}")
                    return parsed_response
                except Exception as e:
                    # Response not ready yet
                    continue
            
            time.sleep(wait_interval)
        
        print(f"No response received for request IDs: {request_ids}")
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
