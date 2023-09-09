else:  # กรณีเท็จ จะออกลูกค้าปกติ
    # SMCOMain เอาชื่อลูกค้ามาใส่รอโหลดระหว่างแอดชื่อลูกค้า
    driver.switch_to.window(merged_dict['SMCO :: เปิดการขาย'])
    wait = WebDriverWait(driver, 50)
    element = wait.until(
        EC.visibility_of_element_located((By.XPATH, cusNameSpan)))
    element.click()
    # driver.find_element(By.XPATH,cusNameInput).clear() น่าจะไม่ต้องใช้
    driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[2]")
    time.sleep(1)
    driver.find_element(By.XPATH, cusNameInput).send_keys(cusName)