# ToolUniverse Tool Fix - Quick Reference

Essential commands and patterns for quickly fixing ToolUniverse tools.

## Commands

### Testing
```bash
# Test specific category
python scripts/test_new_tools.py <pattern>

# Test with verbose output
python scripts/test_new_tools.py <pattern> -v

# Test and stop on first failure
python scripts/test_new_tools.py <pattern> --fail-fast

# Examples
python scripts/test_new_tools.py chembl -v
python scripts/test_new_tools.py pubmed
python scripts/test_new_tools.py alphafold --fail-fast
```

### Tool Regeneration
```bash
# Regenerate all tools
python -m tooluniverse.generate_tools

# Regenerate with verbose output
python -m tooluniverse.generate_tools --verbose

# Force regeneration
python -m tooluniverse.generate_tools --force
```

### Status Check
```bash
# Check modified files
git status --short | grep -E "(data|tools|.*_tool.py)"

# Show changes to tool configs
git diff src/tooluniverse/data/

# Show changes to tool classes
git diff src/tooluniverse/*_tool.py
```

## Quick Fixes

### Binary Response (Images, PDFs, Files)

**Tool class** (`src/tooluniverse/*_tool.py`):
```python
def run(self, arguments):
    is_binary = "download" in tool_name or "/file/" in url
    
    if is_binary:
        return {
            "status": "success",
            "data": f"Binary data at {response.url}",
            "url": response.url,
            "content_type": response.headers.get("Content-Type")
        }
    
    return {"status": "success", "data": response.json()}
```

**JSON config** (`src/tooluniverse/data/*_tools.json`):
```json
{"return_schema": {"type": "string"}}
```

### Schema Mismatch

**If data is string**:
```json
{"return_schema": {"type": "string"}}
```

**If data is object**:
```json
{"return_schema": {"type": "object"}}
```

**If data is array**:
```json
{"return_schema": {"type": "array", "items": {"type": "object"}}}
```

### 404 Error

Check endpoint in JSON config:
```json
{
  "fields": {
    "endpoint": "/correct/path/{param}"
  }
}
```

Verify test example uses valid ID:
```json
{
  "test_examples": [{"param": "valid_id_123"}]
}
```

### Parameter Type Error

Fix parameter schema:
```json
{
  "parameter": {
    "properties": {
      "limit": {"type": "integer"},     // not "string"
      "threshold": {"type": "number"},  // not "string"
      "flag": {"type": "boolean"}       // not "string"
    }
  }
}
```

## Direct Testing Snippet

Copy and modify this for quick testing:

```python
from tooluniverse import ToolUniverse
import json

tu = ToolUniverse()
tu.load_tools()

result = tu.run_one_function({
    'name': 'TOOL_NAME_HERE',
    'arguments': {
        'param1': 'value1',
        'param2': 'value2'
    }
})

print(json.dumps(result, indent=2))
print(f"\nStatus: {result.get('status')}")
print(f"Data type: {type(result.get('data'))}")
```

## Schema Validation Snippet

```python
from jsonschema import validate
import json

# Load schema
with open('src/tooluniverse/data/CATEGORY_tools.json') as f:
    tools = json.load(f)
    schema = [t for t in tools if t['name'] == 'TOOL_NAME'][0]['return_schema']

# Validate
data = result.get('data')
try:
    validate(instance=data, schema=schema)
    print("✅ Schema valid")
except Exception as e:
    print(f"❌ Schema invalid: {e}")
```

## Curl Testing Snippet

```bash
# Test API endpoint directly
curl -v https://api.example.com/endpoint

# Check response headers
curl -I https://api.example.com/endpoint

# Test with parameters
curl "https://api.example.com/endpoint?param=value"

# Test with JSON body
curl -X POST https://api.example.com/endpoint \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```

## File Locations Cheat Sheet

| What to Change | File Location |
|----------------|---------------|
| Tool endpoint URL | `src/tooluniverse/data/*_tools.json` → `fields.endpoint` |
| Return schema | `src/tooluniverse/data/*_tools.json` → `return_schema` |
| Parameter schema | `src/tooluniverse/data/*_tools.json` → `parameter` |
| Test examples | `src/tooluniverse/data/*_tools.json` → `test_examples` |
| Response handling | `src/tooluniverse/*_tool.py` → `run()` method |
| URL building | `src/tooluniverse/*_tool.py` → `_build_url()` |

## Error Message → Fix Mapping

| Error Message | Likely Cause | Fix Location |
|---------------|--------------|--------------|
| `Expecting value: line 1` | Binary response parsed as JSON | Tool class `run()` |
| `not of type 'object'` | Schema type mismatch | JSON config `return_schema` |
| `404 Not Found` | Wrong endpoint or invalid ID | JSON config `endpoint` or `test_examples` |
| `400 Bad Request` | Wrong parameters | JSON config `parameter` |
| `required property missing` | Missing required param | JSON config `parameter.required` |
| `invalid enum value` | Value not in allowed list | JSON config `enum` |

## Git Workflow

```bash
# 1. Check current changes
git status

# 2. Test the fix
python scripts/test_new_tools.py <pattern> -v

# 3. Review changes
git diff src/tooluniverse/

# 4. Stage files
git add src/tooluniverse/data/*.json
git add src/tooluniverse/*_tool.py
git add src/tooluniverse/tools/

# 5. Commit (if requested by user)
git commit -m "fix: resolve [tool] endpoint/schema/response issue"

# Note: Only commit when user explicitly asks
```

## Common Patterns

### REST Tool Response Pattern
```python
return {
    "status": "success",
    "data": data,           # Actual content
    "url": response.url,    # Optional: API URL
    "count": len(items)     # Optional: Result count
}
```

### Error Response Pattern
```python
return {
    "status": "error",
    "error": "Error message",
    "url": url,
    "status_code": 404
}
```

### Binary Response Pattern
```python
return {
    "status": "success",
    "data": "Binary data available at URL",
    "url": response.url,
    "content_type": "image/svg+xml",
    "size_bytes": len(response.content)
}
```

## Verification Checklist

Quick checklist after making changes:

```
□ Run test: python scripts/test_new_tools.py <pattern> -v
□ Check pass rate is 100%
□ Verify schema_valid equals tests run
□ Test direct execution with Python
□ Review git diff for unintended changes
□ Regenerate tools if config changed
□ Re-run tests after regeneration
□ Document fix in summary file
```

## One-Liners

```bash
# Find all failing tests
python scripts/test_new_tools.py | grep "❌"

# Count failures by category
python scripts/test_new_tools.py | grep -c "Failed"

# Show only schema mismatches
python scripts/test_new_tools.py -v | grep "Schema Mismatch"

# List all tool categories
ls src/tooluniverse/data/ | grep "_tools.json" | sed 's/_tools.json//'

# Find tools with binary endpoints
grep -r "image\|pdf\|download" src/tooluniverse/data/*.json

# Check which tools changed
git diff --name-only | grep "tools/"
```
