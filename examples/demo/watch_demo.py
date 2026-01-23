"""Demo script for watch expressions feature.

This script demonstrates tracking variable changes through a loop,
which is ideal for showcasing watch expressions in the debugger.
"""


class DataProcessor:
    """Process data with running statistics."""

    def __init__(self):
        self.total = 0
        self.count = 0
        self.average = 0.0
        self.history = []

    def add(self, value):
        """Add a value and update statistics."""
        self.total += value
        self.count += 1
        self.average = self.total / self.count
        self.history.append(value)
        return self.average


def process_data(data_points):
    """Process a series of data points with running average.

    Great for watching: processor.total, processor.average, processor.count
    """
    processor = DataProcessor()
    results = []

    for i, value in enumerate(data_points):
        # Watch expressions shine here - track changes per iteration
        current_avg = processor.add(value)  # Breakpoint here
        status = "high" if current_avg > 50 else "low"
        results.append({
            "iteration": i,
            "value": value,
            "running_avg": current_avg,
            "status": status
        })

    return results, processor


def main():
    """Entry point with sample data."""
    sample_data = [10, 25, 60, 45, 80, 35, 90, 55]

    print("Processing data with watch expressions demo...")
    results, final_processor = process_data(sample_data)

    print(f"\nFinal statistics:")
    print(f"  Total: {final_processor.total}")
    print(f"  Count: {final_processor.count}")
    print(f"  Average: {final_processor.average:.2f}")

    return results


if __name__ == "__main__":
    main()
