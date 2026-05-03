#!/usr/bin/env python3
"""
Python Code Executor Tools - Quick Start

This file provides the simplest usage examples to help you get started quickly.
"""

import sys
from pathlib import Path

from tooluniverse import ToolUniverse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def quick_example():
    """Quick example"""
    print("🚀 Python Code Executor Tools - Quick Start")
    print("=" * 50)

    # 1. Initialize
    print("1. Initializing ToolUniverse...")
    tu = ToolUniverse()
    tu.load_tools()
    print("✅ Initialization complete")

    # 2. Simple calculation
    print("\n2. Executing simple calculation...")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "result = 10 + 20 * 3",
            "timeout": 10
        }
    })
    print("   Code: result = 10 + 20 * 3")
    print(f"   Result: {result['result']}")
    print(f"   Success: {result['success']}")

    # 3. Use variables
    print("\n3. Using passed variables...")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "result = a + b * c",
            "arguments": {"a": 5, "b": 3, "c": 4},
            "timeout": 10
        }
    })
    print("   Code: result = a + b * c")
    print("   Variables: a=5, b=3, c=4")
    print(f"   Result: {result['result']}")

    # 4. Use math module
    print("\n4. Using math module...")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "import math\nresult = math.sqrt(144) + math.pi",
            "timeout": 10
        }
    })
    print("   Code: import math; result = math.sqrt(144) + math.pi")
    print(f"   Result: {result['result']}")
    print(f"   Success: {result['success']}")

    # 5. Data processing
    print("\n5. Data processing example...")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": """
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
even_squares = [x**2 for x in numbers if x % 2 == 0]
result = {
    'even_squares': even_squares,
    'count': len(even_squares),
    'sum': sum(even_squares)
}
""",
            "timeout": 10
        }
    })
    print("   Code: Calculate squares of even numbers")
    print(f"   Result: {result['result']}")
    print(f"   Success: {result['success']}")

    # 6. Security test
    print("\n6. Security restriction test...")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "import os",
            "timeout": 10
        }
    })
    print("   Code: import os (forbidden)")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result['error_type']}")

    print("\n" + "=" * 50)
    print("🎉 Quick start example completed!")
    print("📖 Check README.md for more usage")
    print("🔧 Check basic_usage.py for more examples")


if __name__ == "__main__":
    try:
        quick_example()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("💡 Tip: Make sure ToolUniverse is properly installed")
