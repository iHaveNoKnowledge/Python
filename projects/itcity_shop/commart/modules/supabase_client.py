from supabase import create_client, Client
from dotenv import load_dotenv
import os
import traceback

# * โหลดค่าจากไฟล์ env
load_dotenv()


class Supabase_client:
    def __init__(self):
        self.url: str = os.getenv("SUPABASE_URL")
        self.key: str = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(self.url, self.key)

    def get_order(self, order_name: str = ""):
        self.column = """order_Name, customer_fname, customer_lname, want_full_tax, full_tax_id, is_headquarter, full_tax_id, customer_tel, com_Order_Items(com_Products(*)), com_Order_Premiums(com_Premiums(*))
"""
        self.response = self.supabase.table("orders").select(
            self.column).eq("order_Name", order_name).execute()

        self.result = ""
        if self.response.data:
            self.result = self.response.data[0]
            print(type(self.result))
            print(self.result)
            # * type ที่ return เป็น dict
            return self.result
        else:
            print()
            raise Exception(
                "error fetching from bot,  no data: ", self.response.data)


# # * example
# supabase_client = Supabase_client()
# supabase_client.get_order("Q43PHH")
