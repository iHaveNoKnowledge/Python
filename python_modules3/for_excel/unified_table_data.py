import pandas as pd
import numpy as np

class UnifyData:
    def __init__(self, path):
        self.dir = path
        self.excel_file = pd.ExcelFile(self.dir)
        self.sheet_names = self.excel_file.sheet_names
          
        # * อยากให้col ไหนเป็น int มาเติมที่ list 'must_be_int_cols'
        must_be_int_cols = ['qty']
        
        self.data_state = {}
        for sheet_name in self.sheet_names:
            self.df = pd.read_excel(self.dir, sheet_name=sheet_name, dtype=str)

            # * ปรับ dtype ของ column ตาม list 'must_be_int_cols' ที่กำหนดไว้ 
            if any(must_be_int_cols) in self.df.columns:
                for col in must_be_int_cols:
                    try:
                        self.df[col].astype(int)
                    except:
                        continue

            self.lowercase_columns = [column.lower() for column in self.df.columns]
            self.df.columns = self.lowercase_columns
            if 'spec' in self.lowercase_columns:
                print(f"ค่าของ Sheet {sheet_name} จะถูกจัดเก็บใน key items_list")
                self.data_state['items_list'] = self.df
            elif 'set' in self.lowercase_columns:
                print(f"Sheet: {sheet_name} จะถูกจัดเก็บใน key sn")
                self.data_state['sn'] = self.df

        # print(f"items_list: {self.data_state['items_list']}")
        # print(f"items_list type: {type(self.data_state['items_list'])}")
        # print(f"sn: {self.data_state['sn']}")
        # print(f"sn type: {type(self.data_state['sn'])}")
        # print(f"self.data_state: {self.data_state}")
        # print(f"self.data_state: {pd.DataFrame(self.data_state)['sn']}")
    def get_result(self, sku, barcode):
        barcode_receive = '758/001'
        find_dict = self.data_state['sn'][self.data_state['sn']['set'] == barcode_receive].iloc[0]
        print('all')
        print(find_dict)