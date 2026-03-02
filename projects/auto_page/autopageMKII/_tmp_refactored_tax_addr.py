    def _normalize_address_for_comparison(self, address):
        """Normalize Thai address variations and strip whitespace for fair comparison."""
        # Normalize 'Moo' (หมู่ที่/ม. → หมู่) — avoid matching "หมู่บ้าน"
        address = re.sub(r'(?:หมู่ที่|หมู่|ม\.)\s*(\d+)', r'หมู่\1', address)
        # Normalize 'Soi' (ซ. → ซอย)
        address = re.sub(r'(?:ซอย|ซ\.)\s*(\d+)', r'ซอย\1', address)
        # Normalize 'Road' (ถ. → ถนน)
        address = re.sub(r'(?:ถนน|ถ\.)\s*(\d+)', r'ถนน\1', address)
        return address.replace(' ', '').replace('เลขที่', '')

    def _build_desired_addresses(self):
        """Build and clean the desired address strings from app data for comparison."""
        self.desired_address = re.sub(
            r'\n', " ", f"""{self.app.get_pure_address(self.app.address)}""".replace('\u200b', ''))
        self.desired_address = re.sub(r'\s{2,}', ' ', self.desired_address)

        self.desired_full_address = re.sub(
            r'\n', " ", f"""{self.app.get_pure_address(self.app.address)}  {self.app.nondistortedData['แขวง/ตำบล']}
            {self.app.nondistortedData['เขต/อำเภอ.1']}  {self.app.nondistortedData['จังหวัด.1']}
            {self.app.nondistortedData['รหัสไปรษณีย์.1']} """.replace('\u200b', ''))

        for prefix in ["อำเภอ", "เขต", "อ.", "ตำบล", "แขวง", "ต.", "จังหวัด", "จ.", "เลขที่"]:
            self.desired_full_address = self.desired_full_address.replace(prefix, "")

    def _fill_address_revision_form(self):
        """Open the SMCO customer edit page and fill in the corrected address fields."""
        self.get_tabs()
        if 'SMCO :: ลูกค้า' not in self.merged_dict:
            self.open_customer_edit_page()

        self.direct_to_customer_info()

        address_revise_btn = self.driver.find_element(
            By.XPATH, '/html/body/div[2]/div[2]/div/div[4]/div[2]/div[1]/div/div[6]/a')
        address_revise_btn.click()

        addr_textarea_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[1]/div[2]/textarea'
        self.wait_element(addr_textarea_xpath)
        address_revise_input = self.driver.find_element(By.XPATH, addr_textarea_xpath)

        tel_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[13]/div[4]/input'
        country_dropdown_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[2]/div/span/span[1]/span/span[1]'
        country_li_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[2]/ul/li[2]'
        province_dropdown_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[4]/div/span/span[1]/span/span[1]'
        dropdown_input_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/span/span/span[1]/input'
        district_dropdown_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[6]/div/span/span[1]/span/span[1]'
        subdistrict_dropdown_xpath = '/html/body/div[2]/div[2]/div/div[4]/div[3]/div/div/div[2]/div/form/div/div[2]/div[2]/div[8]/div/span/span[1]/span/span[1]'

        while True:
            try:
                # * กรอก Address
                address_revise_input.clear()
                self.desired_address = self.app.get_pure_address(self.desired_address)
                address_revise_input.send_keys(self.desired_address)

                # * Telephone
                self.driver.find_element(By.XPATH, tel_xpath).clear()
                self.driver.find_element(By.XPATH, tel_xpath).send_keys(self.app.cus_tel.get())

                # * Country → Thailand
                self.driver.find_element(By.XPATH, country_dropdown_xpath).click()
                time.sleep(1.55)
                self.driver.find_element(By.XPATH, country_li_xpath).click()

                # * Province
                self.driver.find_element(By.XPATH, province_dropdown_xpath).click()
                self.driver.find_element(By.XPATH, dropdown_input_xpath).clear()
                self.driver.find_element(By.XPATH, dropdown_input_xpath).send_keys(
                    self.app.cus_province.get().replace("จังหวัด", ""))
                time.sleep(1.75)
                self.driver.find_element(By.XPATH, dropdown_input_xpath).send_keys(Keys().ENTER)

                # * District
                self.driver.find_element(By.XPATH, district_dropdown_xpath).click()
                district_input = self.driver.find_element(By.XPATH, dropdown_input_xpath)
                self.select_li_from_dropdown(
                    input_element=district_input,
                    search_value=self.app.cus_district.get().replace("อำเภอ", "").replace("เขต", "").replace("ต.", ""),
                    th_field='districtNameTh',
                    en_field='districtNameEn',
                    place_type='district'
                )

                # * SubDistrict (click 3 ครั้งเพื่อให้แน่ใจว่า dropdown เปิด)
                subdistrict_btn = self.driver.find_element(By.XPATH, subdistrict_dropdown_xpath)
                subdistrict_btn.click()
                subdistrict_btn.click()
                subdistrict_btn.click()
                subdistrict_input = self.driver.find_element(By.XPATH, dropdown_input_xpath)
                self.select_li_from_dropdown(
                    input_element=subdistrict_input,
                    search_value=self.app.cus_sub_district.get().replace("ตำบล", "").replace("แขวง", "").replace("ต.", ""),
                    th_field='subdistrictNameTh',
                    en_field='subdistrictNameEn',
                    place_type='subdistrict'
                )

                print(f"""{self.app.cus_order.get()}: Address Revise Complete""")
                break
            except Exception as err:
                print(f"Address Revise Error1 : {traceback.format_exc()}")
                print(f"Address Revise Error2 : {err}")
                logger.info(f"""{self.app.cus_order.get()}: Address Revise Error1 : {traceback.format_exc()}""")
                logger.info(f"""{self.app.cus_order.get()}: Address Revise Error2 : {err}""")
                continue

        # * Wait for success popup
        self.app.is_bot_browser_busy.set(False)
        while not self.operation_thread.is_set():
            time.sleep(0.25)
            try:
                success_popup = self.driver.find_element(By.CSS_SELECTOR, '.swal2-icon.swal2-success')
                if success_popup.is_displayed():
                    self.app.is_bot_browser_busy.set(True)
                    break
            except:
                continue

        # * กลับไปหน้าการขาย
        self.driver.switch_to.window(self.merged_dict['SMCO :: เปิดการขาย'])

    def tax_address_corrector(self, cus_name):
        print("cus_name: ", cus_name)

        # random จะเป็นการที่ user เลือกเองฉะนั้นไม่ต้องตรวจซ้ำ
        if self.should_skip_address_correction():
            print("Random subdistrict used, skipping address correction")
            return

        match = re.search(r'^C\d{1,}(?=-)', cus_name)  # * for customer code
        self.cus_code = match.group()

        customer_id = self.smco_req_find_customer_id(self.cus_code)
        if customer_id:
            cus_address = self.smco_req_find_cus_address(customer_id)
        else:
            cus_address = {
                'address': '', 'subdistrict': '', 'district': '',
                'provice': '', 'zip_code': ''
            }

        if not any(cus_address.values()):
            print("Address not matched")

        self.current_address = "".join(cus_address.values())
        self._build_desired_addresses()

        print("compare self.current_address & self.desired_full_address")
        print(self.current_address.replace(' ', ''))
        print(self.desired_full_address.replace(' ', ''))

        current_normalized = self._normalize_address_for_comparison(self.current_address)
        desired_normalized = self._normalize_address_for_comparison(self.desired_full_address)

        if current_normalized != desired_normalized:
            logger.info(f"{self.app.cus_order.get()}: compare self.current_address & self.desired_full_address")
            logger.info(self.current_address.replace(' ', ''))
            logger.info(self.desired_full_address.replace(' ', ''))
            print("Customer Address is not correct")

            self._fill_address_revision_form()
        else:
            print("Customer address has already corrected")

        print("tax_address_corrector done!")
