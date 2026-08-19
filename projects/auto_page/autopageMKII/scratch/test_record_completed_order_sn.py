import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from functions.accel_mode import AccelMode

class MockApp:
    def __init__(self):
        pass

def test_record_completed_order_with_sn():
    with tempfile.TemporaryDirectory() as tmpdir:
        excel_path = os.path.join(tmpdir, "test_accel.xlsx")
        
        # Create an initial accel excel file with Sheet1 and an older Completed_Orders sheet
        initial_completed = pd.DataFrame([
            {'orders': 'ORD001', 'tracking': 'TRACK001', 'bill_no': 'BILL001', 'price': '100', 'status': 'Completed', 'timestamp': '2026-08-19 10:00:00'}
        ])
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            pd.DataFrame({'orders': ['ORD001', 'ORD002']}).to_excel(writer, sheet_name='Sheet1', index=False)
            initial_completed.to_excel(writer, sheet_name='Completed_Orders', index=False)
            
        app = MockApp()
        accel = AccelMode(app)
        accel.accel_file_dir = excel_path
        
        # Test Case 1: used_serials from attribute (default)
        accel.used_serials = [{'sku': 'SKU_A', 'sn': 'SN12345'}, {'sku': 'SKU_B', 'sn': 'SN67890'}]
        accel.record_completed_order('ORD002', tracking='TRACK002', bill_no='BILL002', status='Completed', price='250')
        
        df = pd.read_excel(excel_path, sheet_name='Completed_Orders', dtype=str)
        print("Columns in Completed_Orders:", df.columns.tolist())
        print("Data:\n", df)
        
        assert 'sn' in df.columns, "Column 'sn' should exist in Completed_Orders"
        ord2_row = df[df['orders'] == 'ORD002'].iloc[0]
        assert ord2_row['sn'] == 'SN12345, SN67890', f"Expected 'SN12345, SN67890', got {ord2_row['sn']}"
        assert ord2_row['tracking'] == 'TRACK002'
        assert ord2_row['bill_no'] == 'BILL002'
        
        # Test Case 2: explicit serials passed as string
        accel.record_completed_order('ORD003', tracking='TRACK003', bill_no='BILL003', status='Completed', price='50', serials='SN99999')
        df2 = pd.read_excel(excel_path, sheet_name='Completed_Orders', dtype=str)
        ord3_row = df2[df2['orders'] == 'ORD003'].iloc[0]
        assert ord3_row['sn'] == 'SN99999'
        
        # Test Case 3: explicit serials passed as list of strings
        accel.record_completed_order('ORD004', tracking='TRACK004', bill_no='BILL004', status='Completed', price='50', serials=['SNA', 'SNB'])
        df3 = pd.read_excel(excel_path, sheet_name='Completed_Orders', dtype=str)
        ord4_row = df3[df3['orders'] == 'ORD004'].iloc[0]
        assert ord4_row['sn'] == 'SNA, SNB'
        
        print("All tests passed successfully!")

if __name__ == "__main__":
    test_record_completed_order_with_sn()
