import argparse

def main():
    parser = argparse.ArgumentParser(description="Calculator")
    parser.add_argument("number", type=float, help="เลขที่ต้องการบวก")
    
    args = parser.parse_args()
    
    result = args.number + 5
    print("ผลลัพธ์ของการบวก: ", result)
    
if __name__ == "__main__":
    main()