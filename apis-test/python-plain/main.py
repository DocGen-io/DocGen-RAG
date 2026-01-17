import argparse
from calculator import Calculator

def main():
    parser = argparse.ArgumentParser(description="Simple CLI Calculator")
    parser.add_argument("operation", choices=["add", "sub", "mul", "div"], help="Operation to perform")
    parser.add_argument("a", type=float, help="First number")
    parser.add_argument("b", type=float, help="Second number")

    args = parser.parse_args()
    calc = Calculator()

    if args.operation == "add":
        print(calc.add(args.a, args.b))
    elif args.operation == "sub":
        print(calc.subtract(args.a, args.b))
    elif args.operation == "mul":
        print(calc.multiply(args.a, args.b))
    elif args.operation == "div":
        try:
            print(calc.divide(args.a, args.b))
        except ValueError as e:
            print(e)

if __name__ == "__main__":
    main()
