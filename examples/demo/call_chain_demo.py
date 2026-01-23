"""Demo script for call chain visualization."""


def level_3(data):
    """Innermost function - processes data."""
    result = []
    for item in data:
        processed = item * 2  # Breakpoint here to see full call chain
        result.append(processed)
    return result


def level_2(items):
    """Middle function - filters and delegates."""
    filtered = [x for x in items if x > 0]
    return level_3(filtered)


def level_1(raw_input):
    """Outer function - validates input."""
    if not raw_input:
        raise ValueError("Empty input")
    return level_2(raw_input)


def main():
    """Entry point demonstrating deep call chain."""
    test_data = [1, -2, 3, -4, 5]
    result = level_1(test_data)
    print(f"Result: {result}")
    return result


if __name__ == "__main__":
    main()
