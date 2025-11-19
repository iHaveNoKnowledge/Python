def auto_add_product(user_id:str, user_pw:str, skus:list[str], srp:int=None):
    try:
        skuInput_element = wait50.until(EC.visibility_of_element_located((By.XPATH, "//span[contains(@class, 'arFilterBox-')]//input[@name='svalue' and contains(@class, 'arFilterBox-search ')]")))
        # skuInput = driver.find_element(By.CSS_SELECTOR,'input.arFilterBox-search.ng-valid.ng-dirty.ng-empty.ng-touched')
        for sku in skus:
            skuInput_element.clear()
            skuInput_element.send_keys(sku)
            print(f"Placing SKU Input with {sku} success")
            
            skuInput_element.send_keys(Keys().ENTER)
            print("Pressed Enter to submit SKU")
        
        request_ids = []
        target_url_part = "/smartcore/smartpos/pointofsales/posmainv3/getProductMasterInfoPOSV3.htm"
        n = 0
        #* จับ requestId หลัง submit form: โดยเราจะดูว่า request ที่ browser ส่งออกไป มี url ตรงกับ request url ที่เราตั้งใจส่งและรอดูผลลัพหรือไม่ ซึ่งในที่นี้คือ target_url_part 
        for _ in range(50):  # poll 5 วิ
            logs = driver.get_log("performance")
            for entry in logs:
                print("entry: ", entry)
                msg = json.loads(entry["message"])["message"]
                if msg["method"] == "Network.requestWillBeSent": #* ตรวจดู เมื่อ browser กำลังจะส่ง request ออกไป
                    url = msg["params"]["request"]["url"]
                    if target_url_part in url:
                        request_ids.append(msg["params"]["requestId"])
                        print("msg from target url req:", msg)
                        break
                    
            #* ถ้าใช้ตรงนี้มันจะเร็วเกินไป ทำให้ response ยังไม่มา รอ 5 วิ พอเป็นพิธี
            if len(request_ids) > 0:
                print("request_ids: ", request_ids)
                break
            
            time.sleep(0.1)
            n += 1
            if n%10 == 0 and n >= 10:
                print("time: ", math.floor(n/10), "วินาที")
        
        product_from_response = None
        #* ดึง response จาก requestId: เป็นการดูว่า request ที่เราสนใจ มี response กลับมาแล้วหรือยัง มันจะส่งกลับมา 200 เสมอ ถ้ามีของกลับมา
        for _ in range(50):  # poll 10 วิ
            res = None
            for req_id in request_ids:
                try:
                    res = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": req_id})
                    print(f"Response for {req_id} = {res}")
                    try:
                        product_from_response = json.loads(res['body'])[0]['productCode']
                    except:
                        product_from_response = None
                        
                    break
                except Exception as e:
                    # print(f"Request {req_id} ยังไม่มี response: {e}")
                    continue
            
            print("resp: ", res)
            print("sku from res: ", product_from_response)
            if res:
                print("ได้ response แล้ว")
                break
            time.sleep(0.1)
        
        # # ดึง log network ออกมาดูได้ (แต่ต้องรู้ requestId ก่อน)
        # logs = driver.get_log("performance")
        # print("logs: ", logs)
        # for entry in logs:
        #     message = json.loads(entry["message"])
        #     msg = message["message"]
        #     if msg["method"] == "Network.responseReceived":
        #         url = msg["params"]["response"]["url"]
        #         status = msg["params"]["response"]["status"]
        #         # if "httpbin.org/get" in url:
        #         print(f"🎯 {url} -> status {status}")

        #! WIP ทดสอบ 1/2 หยุดเพื่อให้จบ if ก่อน แล้ว2/2 จะเป็นชั้นที่จบ scope จริงๆ รู้สึก return ตรนี้ใช้แล้วจะจบเลย ไม่ได้จบแค่ if งั้นเหรอ
        # logger.info(f"Order: {app.order} 1/2Finished!!")
        # return
        price_setter(user_id, user_pw, sku=product_from_response, srp=srp)

        
    except Exception as err:
        print("Shipment cost skipped")
        print(err)
 