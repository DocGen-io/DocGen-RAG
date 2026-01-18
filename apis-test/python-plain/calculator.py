class Calculator:
    def __init__(self):
        self.result = 0

    def add(self, a, b):
        """Adds two numbers."""
        return a + b

    def subtract(self, a, b):
        """Subtracts b from a."""
        return a - b

    def multiply(self, a, b):
        """Multiplies two numbers."""
        return a * b

    def divide(self, a, b):
        """Divides a by b."""
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b
