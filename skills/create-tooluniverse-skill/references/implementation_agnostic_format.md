# Implementation-Agnostic Documentation Format

**Principle**: Separate general workflow (SKILL.md) from implementation code

## Why Implementation-Agnostic?

Users access ToolUniverse via:
- **Python SDK**: Direct Python code
- **MCP (Model Context Protocol)**: Conversational or JSON tool calls
- **Future interfaces**: Other APIs or frameworks

Skills with implementation-specific code limit users to one interface.

## File Structure

```
skills/tooluniverse-[domain]/
├── SKILL.md                     # General workflow (NO Python/MCP code)
├── python_implementation.py     # Python SDK implementation
├── QUICK_START.md              # Multi-implementation examples
└── test_skill.py               # Test script
```

## SKILL.md: General Workflow

**What to include**:
✅ WHAT to do (conceptual workflow)
✅ WHICH tools to use (tool names)
✅ WHAT parameters are needed (descriptions)
✅ WHAT results to expect
✅ Decision logic and conditions
✅ Fallback strategies
✅ Tool parameter reference table

**What NOT to include**:
❌ `from tooluniverse import ToolUniverse`
❌ `tu.tools.TOOL_NAME(...)`
❌ Python-specific code or imports
❌ MCP-specific JSON or prompts
❌ Any language/framework syntax

### SKILL.md Structure

```markdown
---
name: tooluniverse-[domain]
description: [Complete description with triggers]
---

# [Domain] Analysis

[Overview paragraph]

## When to Use This Skill

[Trigger phrases and use cases]

## Workflow Overview

```
Input → Phase 1 → Phase 2 → Phase 3 → Report
```

---

## Phase 1: [Phase Name]

**Objective**: [What this phase achieves]

### Tools Used

**TOOL_NAME**:
- **Input**:
  - `parameter1` (type, required/optional): Description
  - `parameter2` (type, required/optional): Description
- **Output**: Description of returned data
- **Use**: What this tool provides

### Workflow

1. Query TOOL_NAME with [inputs]
2. Extract [specific data] from results
3. If no results → try FALLBACK_TOOL
4. Continue with available data

### Decision Logic

- **Condition 1**: Take action A
- **Empty results**: How to handle
- **Errors**: Fallback to alternative tool

---

## Tool Parameter Reference

**Critical Parameter Notes** (from testing):

| Tool | Parameter | CORRECT Name | Common Mistake |
|------|-----------|--------------|----------------|
| TOOL_1 | `param` | ✅ `actual_name` | ❌ `assumed_name` |

**Response Format Notes**:
- **TOOL_1**: Returns standard `{status, data}` format
- **TOOL_2**: Returns list directly (no wrapper)
```

## python_implementation.py: Python SDK

**What to include**:
- Complete working pipeline function
- Error handling
- Progress messages
- Example usage in `if __name__ == "__main__"`

```python
#!/usr/bin/env python3
"""
[Domain] - Python SDK Implementation
Tested implementation following TDD principles
"""

from tooluniverse import ToolUniverse
from datetime import datetime

def domain_pipeline(
    param1=None,
    param2=None,
    output_file=None
):
    """
    [Domain] analysis pipeline.

    Args:
        param1: Description
        param2: Description
        output_file: Output markdown file path

    Returns:
        Path to generated report file
    """

    tu = ToolUniverse()
    tu.load_tools()

    # Implementation with tested tools
    # Error handling for each phase
    # Progressive report writing

    return output_file

if __name__ == "__main__":
    # Example usage
    domain_pipeline(
        param1="example",
        output_file="example.md"
    )
```

## QUICK_START.md: Multi-Implementation

**What to include**:
- Equal treatment of Python SDK and MCP
- Concrete examples for both
- Tool parameter table noting "applies to both"
- Common recipes in both formats

```markdown
## Quick Start: [Domain] Analysis

[Overview]

---

## Choose Your Implementation

### Python SDK

#### Option 1: Complete Pipeline (Recommended)

```python
from skills.tooluniverse_[domain].python_implementation import pipeline

pipeline(param="value", output_file="output.md")
```

#### Option 2: Individual Tools

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

result = tu.tools.TOOL_NAME(param="value")
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

**Note**: Whether using Python SDK or MCP, parameter names are the same.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `param1` | string | Yes | Description |
| `param2` | integer | No | Description |

---

## Common Recipes

### Recipe 1: [Use Case]

**Python SDK**:
```python
[Code example]
```

**MCP**:
```
[Conversational example or JSON]
```
```

## Best Practices

### DO:
✅ Keep SKILL.md completely general
✅ Describe workflow conceptually
✅ List tool names and parameters
✅ Document decision logic
✅ Include fallback strategies
✅ Create separate implementation files
✅ Provide equal examples for both interfaces

### DON'T:
❌ Put Python code in SKILL.md
❌ Put MCP prompts in SKILL.md
❌ Favor one implementation over another
❌ Assume users know which interface to use
❌ Skip parameter documentation
❌ Forget to test both interfaces

## Examples

### Good: Implementation-Agnostic

```markdown
### Phase 1: Metabolite Identification

**Tools Used**:

**HMDB_search**:
- **Input**:
  - `operation` (string, required): "search"
  - `query` (string, required): Metabolite name
- **Output**: Array of matching metabolites with HMDB IDs
- **Use**: Find metabolite database IDs from names

**Workflow**:
1. Query HMDB_search with metabolite name
2. Extract HMDB ID from first result
3. If no results → try alternative name
4. Continue with available ID or note as unidentified
```

### Bad: Python-Specific

```markdown
### Phase 1: Metabolite Identification

```python
tu = ToolUniverse()
tu.load_tools()

result = tu.tools.HMDB_search(
    operation="search",
    query="glucose"
)
hmdb_id = result['data'][0]['hmdb_id']
```
```

## Validation

Check SKILL.md for implementation-specific content:

```bash
# Should return nothing
grep -E "(from|import|def |tu\.tools)" SKILL.md
grep -E "(json|mcp|conversational)" SKILL.md
```

If anything matches, revise SKILL.md to be general.
