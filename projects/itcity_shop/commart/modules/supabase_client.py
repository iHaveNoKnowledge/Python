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
        self.column = ""
        self.response = self.supabase.table("orders").select(
            "*").eq("order_Name", order_name).execute()

        self.result = ""
        if self.response.data:
            self.result = self.response.data[0]
            print(type(self.result))
            # * type ที่ return เป็น dict
            return self.result
        else:
            print("error fetchData from bot,  no data: ", self.response.data)
            raise


# # * example
# supabase_client = Supabase_client()
# supabase_client.get_order("Q43PHH")
