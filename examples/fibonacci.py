"""Example script for debugging - calculates Fibonacci numbers."""


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number recursively."""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)


def fibonacci_iterative(n: int) -> int:
    """Calculate the nth Fibonacci number iteratively."""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    
    a, b = 0, 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b


def fibonacci_sequence(count: int) -> list[int]:
    """Generate a sequence of Fibonacci numbers."""
    sequence = []
    for i in range(count):
        value = fibonacci_iterative(i)
        sequence.append(value)
        print(f"fib({i}) = {value}")
    return sequence


def main():
    """Main entry point."""
    print("Fibonacci Calculator")
    print("=" * 40)
    
    # Calculate first 15 Fibonacci numbers
    count = 15
    sequence = fibonacci_sequence(count)
    
    print("=" * 40)
    print(f"Generated {len(sequence)} numbers")
    print(f"Sum: {sum(sequence)}")
    print(f"Max: {max(sequence)}")
    
    # Verify recursive matches iterative
    print("\nVerifying recursive vs iterative...")
    for i in range(10):
        recursive = fibonacci(i)
        iterative = fibonacci_iterative(i)
        status = "OK" if recursive == iterative else "MISMATCH"
        print(f"  fib({i}): recursive={recursive}, iterative={iterative} [{status}]")
    
    print("\nDone!")
    return sequence


if __name__ == "__main__":
    result = main()
