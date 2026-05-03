#!/usr/bin/env python3
"""
Python Code Executor Tools - Basic Usage Examples

This example demonstrates how to use ToolUniverse's Python code
execution tools.
"""

import sys
from pathlib import Path

from tooluniverse import ToolUniverse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def basic_code_execution():
    """Basic code execution example"""
    print("=" * 60)
    print("1. Basic Code Execution")
    print("=" * 60)

    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    # Simple arithmetic
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "result = 2 + 2 * 3",
            "timeout": 10
        }
    })

    print("Code: result = 2 + 2 * 3")
    print(f"Result: {result['result']}")
    print(f"Execution time: {result['execution_time_ms']}ms")
    print(f"Success: {result['success']}")


def variable_passing():
    """Variable passing example"""
    print("\n" + "=" * 60)
    print("2. Variable Passing")
    print("=" * 60)

    tu = ToolUniverse()
    tu.load_tools()

    # Use passed variables
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "result = x ** 2 + y ** 2",
            "arguments": {"x": 3, "y": 4},
            "timeout": 10
        }
    })

    print("Code: result = x ** 2 + y ** 2")
    print("Variables: x=3, y=4")
    print(f"Result: {result['result']}")
    print(f"Success: {result['success']}")


def math_module_usage():
    """Math module usage example"""
    print("\n" + "=" * 60)
    print("3. Math Module Usage")
    print("=" * 60)

    tu = ToolUniverse()
    tu.load_tools()

    # Use math module
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": """
import math
result = {
    'sqrt_16': math.sqrt(16),
    'pi': math.pi,
    'sin_pi_2': math.sin(math.pi/2),
    'log_e': math.log(math.e)
}
""",
            "timeout": 10
        }
    })

    print("Code: Using math module for various calculations")
    print(f"Result: {result['result']}")
    print(f"Success: {result['success']}")


def json_processing():
    """JSON processing example"""
    print("\n" + "=" * 60)
    print("4. JSON Data Processing")
    print("=" * 60)

    tu = ToolUniverse()
    tu.load_tools()

    # JSON data processing
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": """
import json
from datetime import datetime

data = {
    "name": "John Doe",
    "age": 30,
    "skills": ["Python", "JavaScript", "SQL"],
    "timestamp": datetime.now().isoformat()
}

result = json.dumps(data, ensure_ascii=False, indent=2)
""",
            "timeout": 10
        }
    })

    print("Code: JSON data processing")
    print(f"Result:\n{result['result']}")
    print(f"Success: {result['success']}")


def list_comprehension():
    """List comprehension example"""
    print("\n" + "=" * 60)
    print("5. List Comprehension and Data Processing")
    print("=" * 60)

    tu = ToolUniverse()
    tu.load_tools()

    # Complex data processing
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": """
numbers = list(range(1, 21))
even_squares = [x**2 for x in numbers if x % 2 == 0]
odd_cubes = [x**3 for x in numbers if x % 2 == 1]

result = {
    'even_squares': even_squares,
    'odd_cubes': odd_cubes,
    'even_count': len(even_squares),
    'odd_count': len(odd_cubes),
    'even_sum': sum(even_squares),
    'odd_sum': sum(odd_cubes)
}
""",
            "timeout": 10
        }
    })

    print("Code: List comprehension and data processing")
    print(f"Result: {result['result']}")
    print(f"Success: {result['success']}")


def security_test():
    """Security test example"""
    print("\n" + "=" * 60)
    print("6. Security Restriction Test")
    print("=" * 60)

    tu = ToolUniverse()
    tu.load_tools()

    # Try to execute forbidden operations
    result = tu.run({
        "name": "python_code_executor",
        "arguments": {
            "code": "import os\nresult = os.listdir('.')",
            "timeout": 10
        }
    })

    print("Code: import os (forbidden operation)")
    print(f"Success: {result['success']}")
    print(f"Error type: {result['error_type']}")
    print(f"Error message: {result['error']}")


def script_runner_example():
    """Script runner example"""
    print("\n" + "=" * 60)
    print("7. Script File Execution")
    print("=" * 60)

    # Create temporary test script
    test_script = Path("/tmp/test_script.py")
    test_script.write_text("""
#!/usr/bin/env python3
import sys
import json
from datetime import datetime

print("Hello from Python script!")
print(f"Arguments: {sys.argv[1:]}")
print(f"Current time: {datetime.now().isoformat()}")

# Create some data
data = {
    "script_name": "test_script.py",
    "args": sys.argv[1:],
    "timestamp": datetime.now().isoformat(),
    "python_version": sys.version.split()[0]
}

print(f"Data: {json.dumps(data, indent=2)}")
""")

    try:
        tu = ToolUniverse()
        tu.load_tools()

        # Run script
        result = tu.run({
            "name": "python_script_runner",
            "arguments": {
                "script_path": str(test_script),
                "script_args": ["--input", "data.csv",
                                "--output", "result.csv"],
                "timeout": 30
            }
        })

        print(f"Script path: {test_script}")
        print(f"Success: {result['success']}")
        print(f"Output:\n{result['stdout']}")
        print(f"Execution time: {result['execution_time_ms']}ms")

    finally:
        # Clean up temporary file
        if test_script.exists():
            test_script.unlink()


def main():
    """Main function"""
    print("Python Code Executor Tools - Usage Examples")
    print("=" * 60)

    try:
        basic_code_execution()
        variable_passing()
        math_module_usage()
        json_processing()
        list_comprehension()
        security_test()
        script_runner_example()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError occurred during execution: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

