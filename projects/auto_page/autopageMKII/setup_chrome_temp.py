    def setup_chrome(self):
        self.opt = Options()
        # * ใช้เพื่อเก็บที่อยู่ของไฟล์ที่ถูก execute ด้วย Python ผ่าน command line arguments ในตัวแปร exepath ซึ่ง sys.argv[0] คือชื่อของไฟล์ Python script ที่ถูกเรียกใช้งาน
        exepath = sys.argv[0]

        # Dir_path = os.path.dirname(os.path.abspath(exepath))
        self.custom_path = r'D:\\bin\\'

        os.environ["WDM_LOCAL"] = self.custom_path
        # print("มีไรบ้างใน obj Options:", dir(self.opt))
        self.opt.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        self.opt.add_experimental_option("debuggerAddress", "localhost:8989")
        self.opt.add_argument("--disable-popup-blocking")
        # self.opt.add_experimental_option("prefs",{
        #     "download.default_directory" : Download_dir,
        #     "directory_upgrade": True
        # })

        #! อันเก่า
        # self.driver = webdriver.Chrome(
        #     service=Service(r'C:\bin\chromedriver.exe'),
        #     options=self.opt
        # )

        # ?? อันใหม่ทดลอง
        try:
            print("create driver")
            # * error มันจะเกิดแถวนี้
            driver = webdriver.Chrome(
                service=Service(r'C:\bin\chromedriver.exe'),
                options=self.opt
            )
            print("driver created")
            return driver

        except:
            traceback_str = traceback.format_exc()
            print("Cannot Create Driver")
            print(traceback_str)
            chrome_app_utils = ChromeAppUtils()
            chrome_app_version = chrome_app_utils.get_chrome_version()
            print("Chrome version: ", chrome_app_version)

            # * Target directory to store chromedriver
            driver_directory = 'C:/bin'

            # * Create an inst of WebDriverManager
            driver_manager = WebDriverManager(driver_directory)

            # * Call the main method to manage chromdriver
            try:
                driver_manager.main()
                # * check_driver() ใช้ปุ๊บมันจะทำการตรวจและโหลดเลย
                driver_manager.check_driver()
            except Exception as err:

                print('error from driver_manager.main()')
                print(err)
                raise

            driver = webdriver.Chrome(
                service=Service(r'C:\bin\chromedriver.exe'),
                options=self.opt
            )
            return driver
