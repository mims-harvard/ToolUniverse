# QUICK_START.md Template

Use this template when writing the QUICK_START.md for a new ToolUniverse skill.

**Key Rule**: Equal treatment of Python SDK and MCP. Concrete examples for both.

---

```markdown
## Quick Start: [Domain] Analysis

[One paragraph overview]

---

## Choose Your Implementation

### Python SDK

#### Option 1: Complete Pipeline (Recommended)

```python
from skills.tooluniverse_[domain].python_implementation import domain_pipeline

# Example 1
domain_pipeline(
    input_param="value",
    output_file="analysis.md"
)
```

#### Option 2: Individual Tools

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Tool 1
result = tu.tools.TOOL_NAME(param="value")

# Tool 2
result = tu.tools.TOOL_NAME2(param="value")
```

---

### MCP (Model Context Protocol)

#### Option 1: Conversational (Natural Language)

```
"Analyze [domain] for [input]"

"Find [data] related to [query]"
```

#### Option 2: Direct Tool Calls

```json
{
  "tool": "TOOL_NAME",
  "parameters": {
    "param": "value"
  }
}
```

---

## Tool Parameters (All Implementations)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `param1` | string | Yes | [Description] |
| `param2` | integer | No | [Description] |

---

## Common Recipes

### Recipe 1: [Use Case Name]

**Python SDK**:
```python
[Code example]
```

**MCP**:
```
[Conversational example]
```

### Recipe 2, 3... (similar)

---

## Expected Output

[Show example report structure]

---

## Troubleshooting

### Issue: [Problem]
**Solution**: [Fix]

---

## Next Steps

After running this skill:
1. [Follow-up action 1]
2. [Follow-up action 2]
```
