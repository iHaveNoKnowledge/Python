import pandas as pd

file_path = './test_pandas01/Order.toship.20230820_20230826.xlsx'
data_frame = pd.read_excel(file_path)
print(data_frame)
