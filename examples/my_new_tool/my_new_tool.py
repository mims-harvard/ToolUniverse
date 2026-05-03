"""Tool definition for MyNewTool.

This file demonstrates the tool class definition following the documentation
pattern for contributing tools to the repository.

Note: For contributions, the config is NOT in the decorator - it goes in a
separate JSON file (see my_new_tool_tools.json).
"""

from tooluniverse.tool_registry import register_tool
from tooluniverse.base_tool import BaseTool
from typing import Dict, Any


@register_tool('MyNewTool')  # Note: No config here for contributions
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

