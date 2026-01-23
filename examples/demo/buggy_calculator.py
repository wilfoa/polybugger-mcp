"""A buggy calculator module for demo purposes."""

def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    total = 0
    for num in numbers:
        total += num
    # Bug: doesn't handle empty list!
    return total / len(numbers)

def process_data(data_groups):
    """Process multiple groups of data."""
    results = []
    for group in data_groups:
        avg = calculate_average(group)
        results.append(avg)
    return results

if __name__ == "__main__":
    # This will crash on the empty list
    groups = [[1, 2, 3], [4, 5, 6], [], [7, 8, 9]]
    print("Processing groups:", groups)
    averages = process_data(groups)
    print("Averages:", averages)
