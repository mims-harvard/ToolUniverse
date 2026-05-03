# Testing Guide for New Tools

## Three-Level Testing (MANDATORY)

### Level 1: Direct Class Testing
```python
import json
from tooluniverse.your_tool_module import YourToolClass

with open("src/tooluniverse/data/your_tools.json") as f:
    tools = json.load(f)
    config = next(t for t in tools if t["name"] == "YourTool_operation1")

tool = YourToolClass(config)
result = tool.run({"operation": "operation1", "param": "value"})
assert result["status"] == "success"
```

### Level 2: ToolUniverse Interface Testing
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Verify registration
assert hasattr(tu.tools, 'YourTool_operation1')

# Test execution
result = tu.tools.YourTool_operation1(operation="operation1", param="value")
assert result["status"] == "success"

# Test error handling
result = tu.tools.YourTool_operation1(operation="operation1")  # Missing required param
assert result["status"] == "error"
```

### Level 3: Real API Testing
```python
result = tu.tools.YourTool_operation1(operation="operation1", param="real_value_from_docs")
if result["status"] == "success":
    assert "data" in result
else:
    print(f"API error (may be down): {result['error']}")
```

## Mandatory: test_new_tools.py

```bash
python scripts/test_new_tools.py your_tool_name -v
python scripts/test_new_tools.py your_tool_name --fail-fast
```

Validates: execution succeeds, response matches return_schema, 404s indicate bad test_examples.

## Systematic Testing for Multiple Tools

1. **Sample test** 1-2 tools per API to catch common issues
2. **Identify patterns**: group errors by type (param validation, API errors, schema errors)
3. **Fix systematically**: fix all tools with same issue together
4. **Verify all**: `python scripts/test_new_tools.py MyAPI -v`
5. **Verify parameters**: print param names from JSON, don't assume

## Common Failures

| Failure | Cause | Fix |
|---------|-------|-----|
| 404 ERROR | Invalid ID in test_examples | Use real IDs from API docs |
| Schema Mismatch | Response doesn't match return_schema | Update schema |
| "None is not of type 'integer'" | Non-nullable mutually exclusive param | Use `["integer", "null"]` |
| Exception | Code bug | Check error, fix implementation |
| Tool not found | Missing default_config.py entry | Add category to TOOLS_CONFIGS |

## Verification Script

```python
import sys
sys.path.insert(0, 'src')

# Step 1: Class registered
from tooluniverse.tool_registry import get_tool_registry
import tooluniverse.your_tool_module
assert "YourToolClass" in get_tool_registry()

# Step 2: Config registered
from tooluniverse.default_config import TOOLS_CONFIGS
assert "your_category" in TOOLS_CONFIGS

# Step 3: Wrappers generated
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
assert hasattr(tu.tools, 'YourCategory_operation1')

print("All 3 registration steps verified!")
```
