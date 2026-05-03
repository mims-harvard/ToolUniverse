"""Example: Adding and Using a Local Tool (Without Contributing)

This example demonstrates how to create and use a local tool WITHOUT
modifying the core ToolUniverse files (default_config.py, __init__.py,
data/ directory).

DIFFERENCE from documentation example:
- Documentation (docs/expand_tooluniverse/contributing/local_tools.rst):
  Shows how to CONTRIBUTE a tool to the repository (requires modifying
  __init__.py, default_config.py, and adding files to data/ directory)

- This example:
  Shows how to use a tool LOCALLY in your own project (all code in one
  file, no modifications to core ToolUniverse files needed)

To use a local tool:
1. Create your tool class with @register_tool decorator and config
2. Import the tool class to register it (config auto-loaded)
3. Call tu.load_tools() - the tool will be available automatically

All code is in this single file for easy reference.
"""

import os
import sys

# Import ToolUniverse components (after sys.path is set)
from tooluniverse.tool_registry import register_tool  # noqa: E402
from tooluniverse.base_tool import BaseTool  # noqa: E402
from tooluniverse import ToolUniverse  # noqa: E402
from typing import Dict, Any  # noqa: E402


# ============================================================================
# TOOL DEFINITION
# ============================================================================

@register_tool('MyNewTool', config={
    "name": "my_new_tool",
    "type": "MyNewTool",
    "description": "Convert text to uppercase",
    "parameter": {
        "type": "object",
        "properties": {
            "input": {
                "type": "string",
                "description": "Text to convert to uppercase"
            }
        },
        "required": ["input"]
    },
    "examples": [
        {
            "description": "Convert text to uppercase",
            "arguments": {"input": "hello world"}
        }
    ],
    "tags": ["text", "utility"],
    "author": "ToolUniverse Contributor",
    "version": "1.0.0"
})
class MyNewTool(BaseTool):
    """My new tool for ToolUniverse."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool."""
        # Your tool logic here
        input_value = arguments.get('input', '')
        return {
            "result": input_value.upper(),
            "success": True
        }

    def validate_input(self, **kwargs) -> None:
        """Validate input parameters."""
        input_val = kwargs.get('input')
        if not input_val:
            raise ValueError("Input is required")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()

    # Load tools - the tool config is automatically loaded from the decorator
    # No need for a separate JSON file or tool_config_files parameter
    tu.load_tools()

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

