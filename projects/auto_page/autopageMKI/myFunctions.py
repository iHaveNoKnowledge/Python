def get_input(boolean, cb):
    # while True:
        # boolean = input("Please provide a boolean input: ")
        try:
            # boolean = eval(boolean) ##เป็นการเอา "ข้อความ" มาแปลงเป็น code python ถ้าแปลงไม่ได้จะ Error พอ error มันจะไปดำเนินการต่อจาก except แทน
            # print(boolean)

            if isinstance(boolean, bool): ##เป็นการตรวจสอบว่า parameter1(typeเป็นobject) เป็น instance ของ param2(type) หรือไม่ บรรทัดนี้ความหมายคือ user_input มีค่าเป็น bool  หรือไม่ 
                if  boolean:
                    cb()
                    # return boolean
                else:
                    print("False input! Please try again.")
            else:
                print("Invalid input, Please enter a boolean value2")
        except:
            print("Invalid input, Please enter a boolean value1")