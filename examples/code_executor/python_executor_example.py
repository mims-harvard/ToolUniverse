#!/usr/bin/env python3
"""
Python Executor Tools Example

This example demonstrates how to use the python_code_executor and python_script_runner tools
from ToolUniverse for safe Python code execution.

Features demonstrated:
1. Basic code execution with python_code_executor
2. Code execution with variable passing
3. Using allowed modules (math, json, etc.)
4. Error handling and security restrictions
5. Script file execution with python_script_runner
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tooluniverse import ToolUniverse


def create_test_script():
    """Create a temporary test script for demonstration."""
    script_content = '''#!/usr/bin/env python3
import sys
import json

def main():
    print("Hello from Python script!")
    print(f"Script arguments: {sys.argv[1:]}")
    
    # Create some data
    data = {
        "message": "Script executed successfully",
        "args_count": len(sys.argv) - 1,
        "python_version": sys.version.split()[0]
    }
    
    print(f"Data: {json.dumps(data, indent=2)}")
    
    # Return result via file (since we can't use return in main)
    with open("script_result.json", "w") as f:
        json.dump(data, f)
    
    print("Script completed!")

if __name__ == "__main__":
    main()
'''
    
    # Create temporary script file
    script_path = Path(tempfile.gettempdir()) / "test_script.py"
    with open(script_path, "w") as f:
        f.write(script_content)
    
    return str(script_path)


def demonstrate_code_executor(tu):
    """Demonstrate python_code_executor functionality."""
    print("=" * 60)
    print("python_code_executor Examples")
    print("=" * 60)
    
    # Example 1: Basic arithmetic
    print("\n1. Basic arithmetic calculation:")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "result = sum([1, 2, 3, 4, 5])",
            "timeout": 10
        }
    })
    print(f"Result: {result}")
    
    # Example 2: Using variables
    print("\n2. Calculation with variables:")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "result = x ** 2 + y ** 2",
            "arguments": {"x": 3, "y": 4},
            "timeout": 10
        }
    })
    print(f"Result: {result}")
    
    # Example 3: Using allowed modules
    print("\n3. Using math module:")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "import math\nresult = math.sqrt(16) + math.pi",
            "timeout": 10
        }
    })
    print(f"Result: {result}")
    
    # Example 4: JSON processing
    print("\n4. JSON data processing:")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": '''
import json
data = {"name": "Alice", "age": 30, "city": "New York"}
result = json.dumps(data, indent=2)
''',
            "timeout": 10
        }
    })
    print(f"Result: {result}")
    
    # Example 5: List comprehension and filtering
    print("\n5. List comprehension and filtering:")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": '''
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
even_squares = [x**2 for x in numbers if x % 2 == 0]
result = {"even_squares": even_squares, "count": len(even_squares)}
''',
            "timeout": 10
        }
    })
    print(f"Result: {result}")
    
    # Example 6: Error handling (forbidden operation)
    print("\n6. Security restriction example (trying to use 'open'):")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "result = open('test.txt', 'w')",
            "timeout": 10
        }
    })
    print(f"Result: {result}")
    
    # Example 7: Timeout example
    print("\n7. Timeout example (infinite loop):")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "while True: pass",
            "timeout": 2
        }
    })
    print(f"Result: {result}")


def demonstrate_script_runner(tu):
    """Demonstrate python_script_runner functionality."""
    print("\n" + "=" * 60)
    print("python_script_runner Examples")
    print("=" * 60)
    
    # Create test script
    script_path = create_test_script()
    print(f"\nCreated test script: {script_path}")
    
    try:
        # Example 1: Basic script execution
        print("\n1. Basic script execution:")
        result = tu.run({
            "name": "python_script_runner",
            "arguments": {
                "script_path": script_path,
                "timeout": 30
            }
        })
        print(f"Result: {result}")
        
        # Example 2: Script with arguments
        print("\n2. Script with command-line arguments:")
        result = tu.run({
            "name": "python_script_runner",
            "arguments": {
                "script_path": script_path,
                "script_args": ["--input", "data.csv", "--output", "result.csv"],
                "timeout": 30
            }
        })
        print(f"Result: {result}")
        
        # Example 3: Script with environment variables
        print("\n3. Script with environment variables:")
        result = tu.run({
            "name": "python_script_runner",
            "arguments": {
                "script_path": script_path,
                "env_vars": {"DEBUG": "true", "LOG_LEVEL": "info"},
                "timeout": 30
            }
        })
        print(f"Result: {result}")
        
        # Example 4: Non-existent script (error handling)
        print("\n4. Error handling (non-existent script):")
        result = tu.run({
            "name": "python_script_runner",
            "arguments": {
                "script_path": "/nonexistent/script.py",
                "timeout": 30
            }
        })
        print(f"Result: {result}")
        
    finally:
        # Clean up test script
        if os.path.exists(script_path):
            os.remove(script_path)
            print(f"\nCleaned up test script: {script_path}")


def demonstrate_advanced_features(tu):
    """Demonstrate advanced features and edge cases."""
    print("\n" + "=" * 60)
    print("Advanced Features and Edge Cases")
    print("=" * 60)
    
    # Example 1: Custom return variable name
    print("\n1. Custom return variable name:")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "my_result = 42 * 2",
            "return_variable": "my_result",
            "timeout": 10
        }
    })
    print(f"Result: {result}")
    
    # Example 2: Complex data structures
    print("\n2. Complex data structures:")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": '''
import json
from datetime import datetime

data = {
    "timestamp": datetime.now().isoformat(),
    "numbers": [i**2 for i in range(5)],
    "nested": {
        "key1": "value1",
        "key2": [1, 2, 3]
    }
}
result = json.dumps(data, indent=2)
''',
            "timeout": 10
        }
    })
    print(f"Result: {result}")
    
    # Example 3: Mathematical calculations
    print("\n3. Mathematical calculations:")
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": '''
import math
import statistics

numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
result = {
    "mean": statistics.mean(numbers),
    "median": statistics.median(numbers),
    "std": statistics.stdev(numbers),
    "sqrt_sum": math.sqrt(sum(numbers))
}
''',
            "timeout": 10
        }
    })
    print(f"Result: {result}")


def main():
    """Main demonstration function."""
    print("Python Executor Tools Demonstration")
    print("=" * 60)
    
    # Initialize ToolUniverse
    print("Initializing ToolUniverse...")
    tu = ToolUniverse()
    tu.load_tools()
    
    # Check if our tools are loaded
    available_tools = [tool.get('name', '') for tool in tu.all_tools]
    if 'python_code_executor' not in available_tools:
        print("ERROR: python_code_executor not found in loaded tools!")
        print(f"Available tools: {available_tools}")
        return
    
    if 'python_script_runner' not in available_tools:
        print("ERROR: python_script_runner not found in loaded tools!")
        print(f"Available tools: {available_tools}")
        return
    
    print("✓ Both Python executor tools loaded successfully!")
    
    # Run demonstrations
    try:
        demonstrate_code_executor(tu)
        demonstrate_script_runner(tu)
        demonstrate_advanced_features(tu)
        
        print("\n" + "=" * 60)
        print("Demonstration completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
