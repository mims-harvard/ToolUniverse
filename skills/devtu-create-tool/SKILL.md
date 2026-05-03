---
name: devtu-create-tool
description: Create new scientific tools for ToolUniverse framework with proper structure, validation, and testing. Use when users need to add tools to ToolUniverse, implement new API integrations, create tool wrappers for scientific databases/services, expand ToolUniverse capabilities, or follow ToolUniverse contribution guidelines. Supports creating tool classes, JSON configurations, validation, error handling, and test examples.
---

# ToolUniverse Tool Creator

Create new scientific tools following established patterns.

## Top 7 Mistakes (90% of Failures)

1. **Missing `default_config.py` Entry** — tools silently won't load
2. **Non-nullable Mutually Exclusive Parameters** — validation errors (#1 issue in 2026)
3. **Fake test_examples** — tests fail, agents get bad examples
4. **Single-level Testing** — misses registration bugs
5. **Skipping `test_new_tools.py`** — misses schema/API issues
6. **Tool Names > 55 chars** — breaks MCP compatibility
7. **Raising Exceptions** — should return error dicts instead

---

## Two-Stage Architecture

```
Stage 1: Tool Class              Stage 2: Wrappers (Auto-Generated)
@register_tool("MyTool")         MyAPI_list_items()
class MyTool(BaseTool):          MyAPI_search()
    def run(arguments):          MyAPI_get_details()
```

One class handles multiple operations. JSON defines individual wrappers. Need BOTH.

## Three-Step Registration

**Step 1**: Class registration via `@register_tool("MyAPITool")`

**Step 2** (MOST COMMONLY MISSED): Config registration in `default_config.py`:
```python
TOOLS_CONFIGS = {
    "my_category": os.path.join(current_dir, "data", "my_category_tools.json"),
}
```

**Step 3**: Automatic wrapper generation on `tu.load_tools()`

---

## Implementation Guide

### Files to Create
- `src/tooluniverse/my_api_tool.py` — implementation
- `src/tooluniverse/data/my_api_tools.json` — tool definitions
- `tests/tools/test_my_api_tool.py` — tests

### Python Tool Class (Multi-Operation Pattern)

```python
from typing import Dict, Any
from tooluniverse.tool import BaseTool
from tooluniverse.tool_utils import register_tool
import requests

@register_tool("MyAPITool")
class MyAPITool(BaseTool):
    BASE_URL = "https://api.example.com/v1"

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing: operation"}
        if operation == "search":
            return self._search(arguments)
        return {"status": "error", "error": f"Unknown: {operation}"}

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query")
        if not query:
            return {"status": "error", "error": "Missing: query"}
        try:
            response = requests.get(
                f"{self.BASE_URL}/search",
                params={"q": query}, timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "data": data.get("results", [])}
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Timeout after 30s"}
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

### JSON Configuration

```json
[
  {
    "name": "MyAPI_search",
    "class": "MyAPITool",
    "description": "Search items. Returns array of results. Supports Boolean operators. Example: 'protein AND membrane'.",
    "parameter": {
      "type": "object",
      "required": ["operation", "query"],
      "properties": {
        "operation": {"const": "search", "description": "Operation (fixed)"},
        "query": {"type": "string", "description": "Search term"},
        "limit": {"type": ["integer", "null"], "description": "Max results (1-100)"}
      }
    },
    "return_schema": {
      "oneOf": [
        {"type": "object", "properties": {"data": {"type": "array"}}},
        {"type": "object", "properties": {"error": {"type": "string"}}, "required": ["error"]}
      ]
    },
    "test_examples": [{"operation": "search", "query": "protein", "limit": 10}]
  }
]
```

### Critical Requirements

- **return_schema MUST have oneOf**: success + error schemas
- **test_examples MUST use real IDs**: NO "TEST", "DUMMY", "PLACEHOLDER"
- **Tool name <= 55 chars**: `{API}_{action}_{target}` template
- **Description 150-250 chars**: what, format, example, notes
- **NEVER raise in run()**: return `{"status": "error", "error": "..."}`
- **Set timeout** on all HTTP requests (30s)
- **Standard response**: `{"status": "success|error", "data": {...}}`

---

## Parameter Design

### Mutually Exclusive Parameters (CRITICAL — #1 issue)

When tool accepts EITHER `id` OR `name`, BOTH must be nullable:

```json
{
  "id": {"type": ["integer", "null"], "description": "Numeric ID"},
  "name": {"type": ["string", "null"], "description": "Name (alternative to id)"}
}
```

Without `"null"`, validation fails when user provides only one parameter.

Common cases: `id` OR `name`, `gene_id` OR `gene_symbol`, any optional filters.

### API Key Configuration

**Optional keys** (tool works without, better with):
```json
{"optional_api_keys": ["NCBI_API_KEY"]}
```
```python
self.api_key = os.environ.get("NCBI_API_KEY", "")  # Read from env only
```

**Required keys** (tool won't work without):
```json
{"required_api_keys": ["NVIDIA_API_KEY"]}
```

Rules: Never add `api_key` as tool parameter for optional keys. Use env vars only.

---

## Testing (MANDATORY)

Full guide: [references/testing-guide.md](references/testing-guide.md)

### Quick Testing Checklist

1. **Level 1** — Direct class test: import class, call `run()`, check response
2. **Level 2** — ToolUniverse test: `tu.tools.YourTool_op1(...)`, check registration
3. **Level 3** — Real API test: use real IDs, verify actual responses
4. **MANDATORY** — Run `python scripts/test_new_tools.py your_tool -v` → 0 failures

### Verification Script

```bash
# Check all 3 registration steps
python3 -c "
import sys; sys.path.insert(0, 'src')
from tooluniverse.tool_registry import get_tool_registry
import tooluniverse.your_tool_module
assert 'YourToolClass' in get_tool_registry(), 'Step 1 FAILED'
from tooluniverse.default_config import TOOLS_CONFIGS
assert 'your_category' in TOOLS_CONFIGS, 'Step 2 FAILED'
from tooluniverse import ToolUniverse
tu = ToolUniverse(); tu.load_tools()
assert hasattr(tu.tools, 'YourCategory_op1'), 'Step 3 FAILED'
print('All 3 steps verified!')
"
```

---

## Quick Commands

```bash
python3 -m json.tool src/tooluniverse/data/your_tools.json     # Validate JSON
python3 -m py_compile src/tooluniverse/your_tool.py             # Check syntax
grep "your_category" src/tooluniverse/default_config.py         # Verify config
python scripts/test_new_tools.py your_tool -v                   # MANDATORY test
```

## References

- **Testing guide**: [references/testing-guide.md](references/testing-guide.md)
- **Advanced patterns** (async, SOAP, pagination): [references/advanced-patterns.md](references/advanced-patterns.md)
- **Implementation guide** (full checklist): [references/implementation-guide.md](references/implementation-guide.md)
- **Tool improvement checklist**: [references/tool-improvement-checklist.md](references/tool-improvement-checklist.md)
