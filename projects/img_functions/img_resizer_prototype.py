import os
from PIL import Image
input_path = r"C:\Users\BCP_27\Documents\GitHub\Python\test\tkinter_test\imgs\kheedluang.ico"
output_path = r"C:\Users\BCP_27\Documents\GitHub\Python\test\tkinter_test\imgs\kheedluang_1024x1024.png"

try:
    # เปิดไฟล์ ICO
    with Image.open(input_path) as img:
        # ปรับขนาดเป็น 1024x1024
        resized_img = img.resize((1024, 1024), Image.Resampling.LANCZOS)

        # แปลงเป็น RGBA หากจำเป็น (สำหรับ PNG ที่รองรับความโปร่งใส)
        if resized_img.mode != 'RGBA':
            resized_img = resized_img.convert('RGBA')

        # บันทึกเป็นไฟล์ PNG
        resized_img.save(output_path, 'PNG')

        print(f"สำเร็จ! ไฟล์ถูกปรับขนาดและแปลงแล้ว:")
        print(f"Input: {input_path}")
        print(f"Output: {output_path}")
        print(f"ขนาดใหม่: {resized_img.size}")

except FileNotFoundError:
    print(f"ไม่พบไฟล์: {input_path}")
except Exception as e:
    print(f"เกิดข้อผิดพลาด: {e}")
