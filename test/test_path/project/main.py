import os

# folder structure หน้าตาเป็นงี้
# ตัวอย่างเช่นถ้าเรามีโฟลเดอร์ที่มีโครงสร้างดังนี้:
# project/
# │
# ├───subfolder/
# │   └───file.txt
# │
# └───main.py


# * รับที่อยู่ของไฟล์ main.py
exepath = os.path.abspath(__file__)
# *> exepath = c:\Users\CSH0041\Documents\GitHub\Python\test\test_path\project\main.py

# * ค้นหา directory path ของไฟล์
dir_path = os.path.dirname(exepath)
# *> dir_path = c:\Users\CSH0041\Documents\GitHub\Python\test\test_path\project

# แสดงผล
print("ที่อยู่ของไฟล์:", exepath)
print("Directory path:", dir_path)

# * สร้าง relative path และ absolute path ของไฟล์ "file.txt"
# todo tips เราแค่ดึง dir_path ของ main.py ให้ได้ ที่เหลือเราจะเติม folder อื่นอะไรใช้ os.path.join param ก็ยัดๆชื่อไฟล์ เป็น str ตามลำดับได้เลย
relative_path = os.path.join("subfolder", "file.txt")
absolute_path = os.path.join(dir_path, "subfolder", "file.txt")

print("Relative path ของไฟล์:", relative_path)
print("Absolute path ของไฟล์:", absolute_path)
