"""Example script for debugging - processes data with various transformations."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class Record:
    """A simple data record."""
    id: int
    name: str
    value: float
    category: str


def load_sample_data() -> list[Record]:
    """Load sample records for processing."""
    return [
        Record(1, "alpha", 10.5, "A"),
        Record(2, "beta", 20.3, "B"),
        Record(3, "gamma", 15.7, "A"),
        Record(4, "delta", 30.1, "C"),
        Record(5, "epsilon", 25.9, "B"),
        Record(6, "zeta", 12.4, "A"),
        Record(7, "eta", 18.8, "C"),
        Record(8, "theta", 22.2, "B"),
        Record(9, "iota", 8.6, "A"),
        Record(10, "kappa", 35.0, "C"),
    ]


def filter_records(
    records: list[Record], 
    predicate: Callable[[Record], bool]
) -> list[Record]:
    """Filter records based on a predicate function."""
    result = []
    for record in records:
        if predicate(record):
            result.append(record)
            print(f"  Included: {record.name} (value={record.value})")
        else:
            print(f"  Excluded: {record.name}")
    return result


def transform_values(
    records: list[Record], 
    transformer: Callable[[float], float]
) -> list[Record]:
    """Transform the value field of each record."""
    result = []
    for record in records:
        old_value = record.value
        new_value = transformer(old_value)
        new_record = Record(
            id=record.id,
            name=record.name,
            value=new_value,
            category=record.category,
        )
        result.append(new_record)
        print(f"  {record.name}: {old_value:.2f} -> {new_value:.2f}")
    return result


def group_by_category(records: list[Record]) -> dict[str, list[Record]]:
    """Group records by their category."""
    groups: dict[str, list[Record]] = {}
    for record in records:
        if record.category not in groups:
            groups[record.category] = []
        groups[record.category].append(record)
    return groups


def calculate_statistics(records: list[Record]) -> dict[str, float]:
    """Calculate statistics for a list of records."""
    if not records:
        return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}
    
    values = [r.value for r in records]
    return {
        "count": len(values),
        "sum": sum(values),
        "avg": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }


def main():
    """Main processing pipeline."""
    print("Data Processor")
    print("=" * 50)
    
    # Load data
    print("\n1. Loading data...")
    records = load_sample_data()
    print(f"   Loaded {len(records)} records")
    
    # Filter: only records with value > 15
    print("\n2. Filtering (value > 15)...")
    filtered = filter_records(records, lambda r: r.value > 15)
    print(f"   Kept {len(filtered)} records")
    
    # Transform: apply 10% increase
    print("\n3. Transforming (10% increase)...")
    transformed = transform_values(filtered, lambda v: v * 1.1)
    
    # Group by category
    print("\n4. Grouping by category...")
    groups = group_by_category(transformed)
    for category, group_records in sorted(groups.items()):
        names = [r.name for r in group_records]
        print(f"   Category {category}: {names}")
    
    # Calculate statistics per category
    print("\n5. Statistics by category:")
    for category, group_records in sorted(groups.items()):
        stats = calculate_statistics(group_records)
        print(f"   Category {category}:")
        print(f"      Count: {stats['count']}")
        print(f"      Sum:   {stats['sum']:.2f}")
        print(f"      Avg:   {stats['avg']:.2f}")
        print(f"      Range: {stats['min']:.2f} - {stats['max']:.2f}")
    
    # Overall statistics
    print("\n6. Overall statistics:")
    overall = calculate_statistics(transformed)
    print(f"   Total records: {overall['count']}")
    print(f"   Total value:   {overall['sum']:.2f}")
    print(f"   Average value: {overall['avg']:.2f}")
    
    print("\n" + "=" * 50)
    print("Processing complete!")
    
    return transformed


if __name__ == "__main__":
    result = main()
