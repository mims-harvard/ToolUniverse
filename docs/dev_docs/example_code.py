from tooluniverse.tool_registry import register_tool


@register_tool(
    "MyTool",
    config={
        "name": "my_tool",
        "type": "MyTool",
        "description": "Does something useful",
        "parameter": {
            "type": "object",
            "properties": {"input": {"type": "string", "description": "Your input"}},
            "required": ["input"],
        },
    },
)
class MyTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config

    def run(self, arguments):
        return {"result": f"Processed: {arguments['input']}", "success": True}


# Usage
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()
result = tu.run_one_function({"name": "my_tool", "arguments": {"input": "test"}})
