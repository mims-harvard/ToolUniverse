# Quick Reference Guide

Fast lookup for common ToolUniverse tool development tasks.

## File Locations

```
src/tooluniverse/{category}_tool.py          # Tool class
src/tooluniverse/data/{category}_tools.json  # Configuration
tests/unit/test_{category}_tool.py           # Unit tests
examples/{category}_tools_example.py         # Example usage
src/tooluniverse/tools/{category}_*.py       # Auto-generated (don't edit)
```

## Basic Tool Class

```python
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

@register_tool("ToolName")
class ToolName(BaseTool):
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Your logic here
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}
```

## Minimal JSON Config

```json
{
  "name": "tool_name",
  "type": "ToolClassName",
  "description": "What it does, inputs, outputs, use cases",
  "parameter": {
    "type": "object",
    "properties": {
      "param": {"type": "string", "description": "Parameter description"}
    },
    "required": ["param"]
  },
  "return_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "data": {"type": "object", "additionalProperties": true}
    }
  },
  "test_examples": [{"param": "value"}]
}
```

## Common Return Patterns

### Simple Success/Error

```python
# Success
return {"status": "success", "data": result}

# Error
return {"status": "error", "error": "Error message"}
```

### Paginated Results

```python
return {
    "status": "success",
    "count": len(results),
    "total": total_count,
    "next": next_url,
    "previous": prev_url,
    "results": results
}
```

### Detail Object

```python
return {
    "status": "success",
    "data": {
        "id": "123",
        "name": "Item name",
        "description": "Details...",
        # ... other fields
    }
}
```

### Error with Details

```python
return {
    "status": "error",
    "error": "Request failed",
    "detail": error_details,
    "suggestion": "Try this instead",
    "url": request_url,
    "status_code": 404
}
```

## HTTP Requests

### Basic GET Request

```python
import requests

response = requests.get(
    "https://api.example.com/endpoint",
    params={"param": "value"},
    timeout=30
)
response.raise_for_status()
data = response.json()
```

### GET with Headers

```python
response = requests.get(
    url,
    params=params,
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    timeout=30
)
```

### POST Request

```python
response = requests.post(
    url,
    json={"key": "value"},
    headers=headers,
    timeout=30
)
```

### With Retry Logic

```python
import time

for attempt in range(3):
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response
    except (requests.ConnectionError, requests.Timeout):
        if attempt == 2:
            raise
        time.sleep(2 ** attempt)
```

## Error Handling

### Comprehensive Try-Except

```python
try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return {"status": "success", "data": response.json()}

except requests.Timeout:
    return {
        "status": "error",
        "error": "Request timed out",
        "suggestion": "Try again or use more specific query"
    }

except requests.ConnectionError as e:
    return {
        "status": "error",
        "error": "Failed to connect to API",
        "detail": str(e)
    }

except requests.HTTPError as e:
    return {
        "status": "error",
        "error": f"API error: {e.response.status_code}",
        "detail": e.response.text,
        "url": e.response.url
    }

except Exception as e:
    return {
        "status": "error",
        "error": f"{type(e).__name__}: {str(e)}"
    }
```

## Validation

### Parameter Validation

```python
def validate_parameters(self, arguments: Dict[str, Any]) -> None:
    param = arguments.get('param', '')
    
    if not param:
        raise ValueError("param cannot be empty")
    
    if len(param) < 2:
        raise ValueError("param must be at least 2 characters")
    
    if not param.replace(' ', '').isalnum():
        raise ValueError("param contains invalid characters")
```

### In-Method Validation

```python
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    param = arguments.get('param')
    
    if not param:
        return {
            "status": "error",
            "error": "Missing required parameter: param"
        }
    
    # Continue with logic...
```

## Common Patterns

### Search Tool

```python
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    query = arguments.get('query')
    limit = arguments.get('limit', 20)
    
    response = requests.get(
        f"{self.base_url}/search",
        params={'q': query, 'limit': limit}
    )
    data = response.json()
    
    return {
        "status": "success",
        "count": len(data['results']),
        "results": data['results']
    }
```

### Detail Tool

```python
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    id_ = arguments.get('id')
    
    response = requests.get(f"{self.base_url}/items/{id_}")
    data = response.json()
    
    return {
        "status": "success",
        "data": data
    }
```

### List Tool with Pagination

```python
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    page = arguments.get('page', 1)
    page_size = arguments.get('page_size', 20)
    
    response = requests.get(
        f"{self.base_url}/items",
        params={'page': page, 'page_size': page_size}
    )
    data = response.json()
    
    return {
        "status": "success",
        "count": len(data['results']),
        "total": data['total'],
        "next": data.get('next'),
        "previous": data.get('previous'),
        "results": data['results']
    }
```

## Testing Commands

```bash
# Validate JSON syntax
python3 -m json.tool src/tooluniverse/data/{category}_tools.json

# Check Python syntax
python3 -m py_compile src/tooluniverse/{category}_tool.py

# Run tests
pytest tests/unit/test_{category}_tool.py -v

# Check tool loads
python3 -c "from tooluniverse import ToolUniverse; tu = ToolUniverse(); print('Loaded:', len(tu.list_tools()), 'tools')"

# Check tool name lengths
python scripts/check_tool_name_lengths.py --test-shortening

# List auto-generated wrappers
ls src/tooluniverse/tools/{category}_*.py
```

## Quick Test Script

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()

# Test tool
result = tu.run_tool("tool_name", {"param": "value"})
print(result)

# List all tools
print(f"Total tools: {len(tu.list_tools())}")
```

## JSON Schema Types

```json
{
  "type": "string",           // Text
  "type": "integer",          // Whole numbers
  "type": "number",           // Decimals
  "type": "boolean",          // true/false
  "type": "array",            // Lists
  "type": "object",           // Dictionaries
  "type": ["string", "null"], // Union types
  "type": "object",
  "additionalProperties": true  // Allow extra fields
}
```

## Common Schema Patterns

### String Parameter

```json
{
  "param_name": {
    "type": "string",
    "description": "Description with examples: 'example1', 'example2'"
  }
}
```

### Integer with Constraints

```json
{
  "limit": {
    "type": "integer",
    "description": "Max results. Range: 1-100. Default: 20",
    "default": 20,
    "minimum": 1,
    "maximum": 100
  }
}
```

### Optional Boolean

```json
{
  "include_details": {
    "type": "boolean",
    "description": "Include detailed information. Default: false",
    "default": false
  }
}
```

### Enum

```json
{
  "sort_by": {
    "type": "string",
    "description": "Sort order. Options: 'relevance', 'date', 'name'",
    "enum": ["relevance", "date", "name"],
    "default": "relevance"
  }
}
```

### Array of Strings

```json
{
  "tags": {
    "type": "array",
    "description": "List of tags to filter by",
    "items": {
      "type": "string"
    }
  }
}
```

## Environment Variables

```python
import os

# Get with default
api_key = os.environ.get('API_KEY', 'default_key')

# Get required
api_key = os.environ['API_KEY']  # Raises KeyError if missing

# Check existence
if 'API_KEY' in os.environ:
    api_key = os.environ['API_KEY']
```

## URL Building

```python
# Simple concatenation
url = f"{base_url}/endpoint"

# With path parameter
url = f"{base_url}/items/{item_id}"

# With multiple segments
url = f"{base_url}/api/v1/items/{item_id}/details"

# Build with urllib
from urllib.parse import urljoin
url = urljoin(base_url, f"/items/{item_id}")
```

## Common Mistakes to Avoid

### ❌ Don't

```python
# Don't edit auto-generated files
src/tooluniverse/tools/category_tool_name.py

# Don't use bare except
except:
    pass

# Don't ignore errors
result = some_function()  # No error checking

# Don't hardcode URLs
response = requests.get("http://example.com/api")

# Don't forget timeouts
response = requests.get(url)  # No timeout

# Don't create tools longer than 55 chars
"very_long_tool_name_that_exceeds_the_mcp_compatibility_limit"
```

### ✅ Do

```python
# Do create tool class files
src/tooluniverse/category_tool.py

# Do catch specific exceptions
except ValueError as e:
    return {"error": str(e)}

# Do check errors
if not result:
    return {"error": "Failed"}

# Do use configurable URLs
self.base_url = "https://api.example.com"

# Do set timeouts
response = requests.get(url, timeout=30)

# Do keep names concise
"get_drug_info"  # 13 chars
```

## Debugging Tips

```python
# Print arguments
print(f"Arguments: {arguments}")

# Print response
print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")

# Check data type
print(f"Type: {type(data)}")

# Pretty print JSON
import json
print(json.dumps(data, indent=2))

# Log errors
import logging
logging.error(f"Failed: {str(e)}")
```

## Return Schema Anti-Patterns

### ❌ Bad (Too Vague)

```json
{
  "return_schema": {
    "type": "object",
    "properties": {
      "data": {"type": "object", "additionalProperties": true}
    }
  }
}
```

### ✅ Good (Specific)

```json
{
  "return_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "count": {"type": "integer"},
      "results": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"}
          },
          "additionalProperties": true
        }
      }
    }
  }
}
```

## Time Savers

```bash
# Create all files at once
mkdir -p src/tooluniverse/data tests/unit examples
touch src/tooluniverse/my_tool.py
touch src/tooluniverse/data/my_tools.json
touch tests/unit/test_my_tool.py

# Validate everything
python3 -m json.tool src/tooluniverse/data/*.json
python3 -m py_compile src/tooluniverse/*_tool.py

# Count tools
grep -c '"name":' src/tooluniverse/data/*_tools.json

# Find tool registration
grep -r "@register_tool" src/tooluniverse/

# Check for long names
python scripts/check_tool_name_lengths.py
```
