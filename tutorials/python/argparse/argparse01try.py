import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("num1", type=float)
    parser.add_argument("num2", type=float)
    
    args = parser.parse_args()
    
    result = args.num1 + args.num2
    
    print(f"{args.num1} บวก {args.num2} = {result}")
    
if __name__ == "__main__":
    main()