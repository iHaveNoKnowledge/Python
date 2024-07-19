from supabase import create_client, Client
from dotenv import load_dotenv
import os
import traceback

# * โหลดค่าจากไฟล์ env
load_dotenv()


class Supabase_client:
    def __init__(self, app=None, parent=None):
        self.app = app
        self.parent = parent
        self.url: str = os.getenv("SUPABASE_URL")
        self.key: str = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(self.url, self.key)

    def get_order(self, order_name: str = ""):
        self.column = """order_Name, customer_fname, customer_lname, company_name_of_tax, full_tax_type, full_tax_branch_no, want_full_tax, full_tax_id, is_headquarter, full_tax_id, re_mark, customer_tel, com_Order_Items(com_Products(*)), com_Order_Premiums(com_Premiums(*))"""
        try:
            self.app.update_bot_status(True, "กำลังดึงข้อมูล")
        except:
            pass
        self.response = self.supabase.table("orders").select(
            self.column).eq("order_Name", order_name).execute()
        try:
            self.app.is_fetching.set(False)
        except:
            pass
        self.result = ""
        if self.response.data:
            self.result = self.response.data[0]
            print(type(self.result))
            print(self.result)
            try:
                self.app.update_bot_status(True)
            except:
                pass
            # * type ที่ return เป็น dict

            return self.result
        else:

            self.app.PopUp("Warning", "ไม่มีข้อมูล", self.parent, "form")
            raise Exception(
                "error fetching from bot,  no data found: ", self.response.data)


# # * example
# supabase_client = Supabase_client()
# supabase_client.get_order("83PT8D")
