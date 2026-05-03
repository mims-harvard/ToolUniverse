# Tool Creation Templates

## Python Tool Class Template

```python
from typing import Dict, Any
from tooluniverse.tool import BaseTool
from tooluniverse.tool_utils import register_tool
import requests
import os

@register_tool("[APIName]Tool")
class [APIName]Tool(BaseTool):
    """Tool for [API Name] - [brief description]."""

    BASE_URL = "[API base URL]"

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.api_key = os.environ.get("[API_KEY_NAME]", "")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        if operation == "operation1":
            return self._operation1(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _operation1(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        param1 = arguments.get("param1")
        if not param1:
            return {"status": "error", "error": "Missing required parameter: param1"}

        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.get(
                f"{self.BASE_URL}/endpoint",
                params={"param1": param1},
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            return {
                "status": "success",
                "data": data.get("results", []),
                "metadata": {"total": data.get("total", 0), "source": "[API Name]"}
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "API timeout after 30 seconds"}
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
```

## JSON Configuration Template

```json
[
  {
    "name": "[APIName]_operation1",
    "class": "[APIName]Tool",
    "description": "[What it does]. Returns [format]. [Input]. Example: [usage]. [Notes].",
    "parameter": {
      "type": "object",
      "required": ["operation", "param1"],
      "properties": {
        "operation": {"const": "operation1", "description": "Operation identifier (fixed)"},
        "param1": {"type": "string", "description": "Description with format/constraints"}
      }
    },
    "return_schema": {
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "data": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}}}},
            "metadata": {"type": "object", "properties": {"total": {"type": "integer"}, "source": {"type": "string"}}}
          }
        },
        {"type": "object", "properties": {"error": {"type": "string"}}, "required": ["error"]}
      ]
    },
    "test_examples": [{"operation": "operation1", "param1": "real_value_from_api_docs"}]
  }
]
```

## Authentication Patterns

**Public**: No special handling.

**API Key (Optional)**:
```python
self.api_key = os.environ.get("API_KEY_NAME", "")
# JSON: "optional_api_keys": ["API_KEY_NAME"]
```

**API Key (Required)**:
```python
self.api_key = os.environ.get("API_KEY_NAME")
if not self.api_key:
    raise ValueError("API_KEY_NAME environment variable required")
# JSON: "required_api_keys": ["API_KEY_NAME"]
```

## Advanced Patterns

### Async Polling (job-based APIs)
Submit → poll → retrieve. Max 60 attempts, 2s interval = 2min timeout.

### SOAP APIs
Require `operation` parameter (e.g., `"operation": "search_genes"`).

### Pagination
Fetch pages until empty or partial page. Track total_pages and total_items.

## File Naming
- Python: `src/tooluniverse/[api_name]_tool.py`
- JSON: `src/tooluniverse/data/[api_name]_tools.json`
- Register in: `src/tooluniverse/default_config.py`

## Critical Requirements
- return_schema MUST have oneOf (success + error)
- test_examples MUST use real IDs (NO placeholders)
- Tool name <= 55 characters
- Description 150-250 chars
- NEVER raise exceptions in run() — return error dict
- Set timeout on all HTTP requests (30s)
