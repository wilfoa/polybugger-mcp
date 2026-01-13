#!/usr/bin/env python3
"""
Demo script for the OpenCode Debug Relay Server.

This script demonstrates various debugging scenarios that can be explored
using the debug skill. Run this script through the debug server to practice:

1. Setting breakpoints on specific lines
2. Stepping through code (step-over, step-into, step-out)
3. Inspecting variables and data structures
4. Evaluating expressions in context
5. Conditional breakpoints
6. Debugging exceptions

Usage with debug server:
    1. Start the debug server: python -m opencode_debugger.main
    2. Create a session and set breakpoints
    3. Launch this script
    4. Explore the debugging features!

Suggested breakpoints:
    - Line 42: Start of calculate_statistics (inspect input data)
    - Line 58: Inside the loop (watch variables change)
    - Line 73: After processing (see final results)
    - Line 89: In process_order (step into from main)
    - Line 112: Conditional breakpoint (e.g., order.total > 100)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Order:
    """Represents a customer order."""
    id: int
    customer: str
    items: list[str]
    quantities: list[int]
    prices: list[float]
    discount: float = 0.0
    
    @property
    def subtotal(self) -> float:
        """Calculate order subtotal before discount."""
        return sum(q * p for q, p in zip(self.quantities, self.prices))
    
    @property
    def total(self) -> float:
        """Calculate order total after discount."""
        return self.subtotal * (1 - self.discount)


def calculate_statistics(orders: list[Order]) -> dict:
    """
    Calculate statistics for a list of orders.
    
    Try setting a breakpoint here (line 58) to inspect the orders list,
    then step through to watch the statistics being computed.
    """
    stats = {
        "count": 0,
        "total_revenue": 0.0,
        "average_order": 0.0,
        "largest_order": 0.0,
        "items_sold": 0,
    }
    
    # Breakpoint here to watch stats update each iteration
    for order in orders:
        stats["count"] += 1
        stats["total_revenue"] += order.total
        stats["items_sold"] += sum(order.quantities)
        
        if order.total > stats["largest_order"]:
            stats["largest_order"] = order.total
            largest_customer = order.customer  # Try evaluating this!
    
    # Breakpoint here to see final computed stats
    if stats["count"] > 0:
        stats["average_order"] = stats["total_revenue"] / stats["count"]
    
    return stats


def process_order(order: Order) -> dict:
    """
    Process a single order and return a receipt.
    
    Step into this function to see order processing details.
    Try evaluating expressions like:
        - order.subtotal
        - order.total
        - order.items[0]
    """
    receipt = {
        "order_id": order.id,
        "customer": order.customer,
        "timestamp": datetime.now().isoformat(),
        "items": [],
        "subtotal": 0.0,
        "discount": 0.0,
        "total": 0.0,
    }
    
    # Process each item - good place for conditional breakpoint
    for i, (item, qty, price) in enumerate(zip(order.items, order.quantities, order.prices)):
        line_total = qty * price
        receipt["items"].append({
            "name": item,
            "quantity": qty,
            "unit_price": price,
            "line_total": line_total,
        })
        receipt["subtotal"] += line_total
        
        # Debug tip: Set conditional breakpoint here with "line_total > 50"
        print(f"  {qty}x {item} @ ${price:.2f} = ${line_total:.2f}")
    
    receipt["discount"] = receipt["subtotal"] * order.discount
    receipt["total"] = receipt["subtotal"] - receipt["discount"]
    
    return receipt


def find_vip_customers(orders: list[Order], threshold: float = 100.0) -> list[str]:
    """
    Find customers whose orders exceed the VIP threshold.
    
    Good for practicing conditional breakpoints:
        Set breakpoint on line with condition "order.total > threshold"
    """
    vip_customers = []
    
    for order in orders:
        # Conditional breakpoint: order.total > threshold
        if order.total > threshold:
            if order.customer not in vip_customers:
                vip_customers.append(order.customer)
                print(f"  VIP: {order.customer} (${order.total:.2f})")
    
    return vip_customers


def demonstrate_exception():
    """
    Demonstrates debugging an exception.
    
    Enable "stop on exception" to catch the ZeroDivisionError.
    """
    numbers = [10, 20, 0, 30, 40]
    results = []
    
    for n in numbers:
        try:
            result = 100 / n  # Will raise ZeroDivisionError when n=0
            results.append(result)
        except ZeroDivisionError as e:
            print(f"  Caught exception: {e}")
            results.append(None)
    
    return results


def main():
    """
    Main entry point - demonstrates a complete order processing workflow.
    
    Suggested debugging workflow:
    1. Set breakpoint at line 165 (orders = [...])
    2. Launch and inspect the orders list
    3. Step over to line 183 and inspect stats
    4. Set breakpoint in process_order and step into it
    5. Try evaluating expressions like "orders[0].total"
    """
    print("=" * 60)
    print("OpenCode Debug Demo")
    print("=" * 60)
    
    # Sample orders - inspect this data structure
    orders = [
        Order(
            id=1001,
            customer="Alice",
            items=["Laptop", "Mouse", "Keyboard"],
            quantities=[1, 2, 1],
            prices=[999.99, 29.99, 79.99],
            discount=0.1,
        ),
        Order(
            id=1002,
            customer="Bob",
            items=["Monitor", "USB Hub"],
            quantities=[2, 1],
            prices=[299.99, 49.99],
            discount=0.0,
        ),
        Order(
            id=1003,
            customer="Charlie",
            items=["Headphones", "Webcam", "Mousepad"],
            quantities=[1, 1, 2],
            prices=[149.99, 89.99, 19.99],
            discount=0.05,
        ),
        Order(
            id=1004,
            customer="Alice",  # Repeat customer
            items=["Tablet"],
            quantities=[1],
            prices=[449.99],
            discount=0.15,
        ),
    ]
    
    # Step 1: Calculate statistics
    print("\n1. Calculating order statistics...")
    stats = calculate_statistics(orders)
    print(f"   Total orders: {stats['count']}")
    print(f"   Total revenue: ${stats['total_revenue']:.2f}")
    print(f"   Average order: ${stats['average_order']:.2f}")
    print(f"   Largest order: ${stats['largest_order']:.2f}")
    print(f"   Items sold: {stats['items_sold']}")
    
    # Step 2: Process each order
    print("\n2. Processing orders...")
    receipts = []
    for order in orders:
        print(f"\n   Order #{order.id} for {order.customer}:")
        receipt = process_order(order)
        receipts.append(receipt)
        print(f"   Subtotal: ${receipt['subtotal']:.2f}")
        if receipt['discount'] > 0:
            print(f"   Discount: -${receipt['discount']:.2f}")
        print(f"   Total: ${receipt['total']:.2f}")
    
    # Step 3: Find VIP customers
    print("\n3. Finding VIP customers (orders > $100)...")
    vips = find_vip_customers(orders, threshold=100.0)
    print(f"   VIP customers: {', '.join(vips)}")
    
    # Step 4: Demonstrate exception handling
    print("\n4. Demonstrating exception handling...")
    results = demonstrate_exception()
    print(f"   Results: {results}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Demo complete!")
    print(f"Processed {len(orders)} orders")
    print(f"Total revenue: ${stats['total_revenue']:.2f}")
    print(f"VIP customers: {len(vips)}")
    print("=" * 60)
    
    return {
        "orders": orders,
        "stats": stats,
        "receipts": receipts,
        "vips": vips,
    }


if __name__ == "__main__":
    result = main()
