def get_res_vatinfo(self, tax_num, tax_branch):
        tax_input = str(tax_num)
        branch = str(tax_branch)
        jsession_id = ''

        # เราจะไม่ใช้ cookies แต่จะใช้ค่าจาก class แรกสุด เพราะ
        # cookies = self.app.cookies['vatinfo']
        print("cookies for reqtaxinfo: ", self.app.cookies['vatinfo'])

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            # 'Cookie': 'JSESSIONID=0000afl1mgz_VGdxFmh7f5mQJqf:-1',
            'Origin': 'https://vsreg.rd.go.th',
            'Referer': 'https://vsreg.rd.go.th/VATINFOWSWeb/jsp/VATInfoWSServlet',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        params = ''

        data = {
            'operation': 'searchByTin',
            'goto_page': '',
            'tin': 'on',
            'txtTin': tax_input,
            'branotxt': '',
            'fname': 'null',
            'lname': 'null',
        }

        times = 1

        data2 = {
            'operation': 'GotoPage_Click',
            'goto_page': f'{times}',
            'tin': 'on',
            'txtTin': tax_input,
            'branotxt': '',
            'fname': 'null',
            'lname': 'null',
        }

        while not self.operation_thread.is_set():
            if times == 1:
                print("times = 1")
                response = session.post('https://vsreg.rd.go.th/VATINFOWSWeb/jsp/VATInfoWSServlet',
                                        cookies=self.app.cookies['vatinfo'], params=params, headers=headers, data=data)

                # Todo มันมีการตรวจสอบ cookies ตลอดเวลา แต่ครั้งแรกreqไปมันจะตรวจสอบก่อน ถ้าไม่มีมันจะ return มาให้  ครั้งถัดไปมันจะตรวจอีกถ้ามี"แล้วยังใช้ได้" มันจะไม่ return ให้ ถ้าใช้ไม่ได้มันจะ return ตัวใหม่ให้
                try:
                    # * กรณี ที่ มี cookies returns กลับมา เพราะอันเก่ามันหมดอายุแล้ว หรือไม่เคยมีมาก่อน
                    print("response cookies ไรมา", response.cookies)
                    # * > เก็บค่า cookies จาก response เข้าไปใน cookies ที่มีอยู่แล้ว
                    jsession_id = response.cookies['JSESSIONID']
                    print("we never have usable cookies before that why the response has cookies. We'll use it like a state in app.cookies")
                    self.app.cookies['vatinfo']['JSESSIONID'] = f"""{jsession_id}"""
                except Exception as err:
                    # * กรณี ที่ ไม่มี cookies returns กลับมา เพราะอันเก่าใช้ได้อยู่ ใช้ cookies เดิมได้เลย
                    print(
                        "if the response is '<RequestCookieJar[]>', it indicates that no cookies were returned. Therefore, we already have available cookies now.",
                        response)

            elif times > 1:
                print("jsession_id", jsession_id)
                # รอบสองเราเอา cookies มาประกอบ request โดย data ที่ใช้ request รอบนี้เป็นอีกแบบนึงจะต้องมี cookie เป็นตัวยืนยันว่าเคย login มาแล้ว ถ้าไม่มี cookie จะผ่านไม่ได้ เหมือนจะเป็น authen

                data2['goto_page'] = f'{times}'
                response = session.post(
                    'https://vsreg.rd.go.th/VATINFOWSWeb/jsp/VATInfoWSServlet?', params=params,
                    cookies=self.app.cookies['vatinfo'],
                    headers=headers, data=data2)

            try:
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                # print("ได้ไรออกมา", soup)
                # หาว่า response มี <tr> หรือไม่ มีเท่าไหร่
                menu_elements = soup.select('tr[class^="trMenu"]')
                is_many_page = soup.select("""span[onclick^="gotoPage('"]""")
                print("มีหลายหน้า?: ", bool(is_many_page))
                search_result = []
                output = ""

                # * ตรวจหา element รายการข้อมูลใบกำกับ ซึ่งมันจะมี class ชื่อ trmenu
                if len(menu_elements):
                    # * มี <tr>
                    for menu_element in menu_elements:
                        result_data = {
                            "no": "",
                            "tax_num": "",
                            "branch": "",
                            "name": "",
                            "address": "",
                            "postal_code": ""
                        }

                        # print(menu_element) <<หาทั้งหมด
                        # * tr = menu_element.find('tr')
                        # * ในแต่ละ <tr> มี <td> หลายอัน
                        tds = menu_element.find_all('td')
                        for idx, key in enumerate(result_data):
                            b = tds[idx].find('b')
                            result = b.find('font').text.strip()
                            result = re.sub(r"\s{2,}", " ", result)

                            # * ช่วงใบกำกับ จะตัดเอาค่า 13 หลักจากด้านหลัง เพราะไอ 10 หลักตอนแรกมันคือไรไม่รู้
                            if idx == 1 and len(result) > 13:
                                result = result[-13:]

                            print(result)
                            result_data[key] = result
                        print(" ")
                        search_result.append(result_data)

                    # * เอา search_result มาดูว่าตรงกับสาขาที่ต้องการหรือไม่
                    for item in search_result:
                        if item['branch'] == self.app.branch_type:
                            output = item
                            print("เกบค่าลง dict result ลง output", output)
                            break
                    if bool(output) == False:
                        print("ว่างต้องวนใหม่")
                        times += 1
                        continue
                    else:
                        print("ใช้ได้", output)
                        break

                elif bool(menu_elements) == False:
                    # ไม่มี <tr>
                    print("ไม่มีใบกำกับจาก request", output)
                    break

            except session.exceptions.HTTPError as e:
                print(f"HTTP Error occurred: {e}")
            except Exception as e:
                print(f"An error occured: {e}")
            break

        output = self.classify_vatinfo_address(output)
        print("output: ", output)
        return output