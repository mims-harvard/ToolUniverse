"""Example usage of MyNewTool.

This example follows the documentation pattern for contributing tools to the
repository. It demonstrates the multi-file structure:
- my_new_tool.py: Tool class definition
- my_new_tool_tools.json: Tool configuration
- my_new_tool_example.py: Example usage

This matches the structure shown in:
docs/expand_tooluniverse/contributing/local_tools.rst

Note: In a real contribution, these files would be placed in:
- src/tooluniverse/my_new_tool.py
- src/tooluniverse/data/my_new_tool_tools.json
- examples/my_new_tool_example.py

And you would need to modify __init__.py in 4 locations.
"""

import os
import sys

# Add src to path to ensure tooluniverse can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
# Add current directory to path to import the tool class
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the tool class to register it
from my_new_tool import MyNewTool  # noqa: E402, F401

from tooluniverse import ToolUniverse  # noqa: E402


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()

    # Load tools with the config file
    # In a real contribution, this would be in default_tool_files
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'my_new_tool_tools.json')
    tu.load_tools(tool_config_files={"my_new_tool": config_path})

    # Use the tool
    result = tu.run({
        "name": "my_new_tool",
        "arguments": {"input": "hello world"}
    })

    print(f"Result: {result}")

    # Test with different inputs
    test_inputs = ["hello", "world", "python"]
    for text in test_inputs:
        result = tu.run({
            "name": "my_new_tool",
            "arguments": {"input": text}
        })
        print(f"'{text}' -> '{result.get('result', 'ERROR')}'")


if __name__ == "__main__":
    main()

