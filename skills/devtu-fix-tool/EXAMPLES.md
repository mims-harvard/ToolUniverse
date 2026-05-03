# ToolUniverse Tool Fix Examples

Real-world examples of fixing ToolUniverse tools, including the complete ChEMBL image endpoint fix.

## Example 1: Binary Response Handling (ChEMBL Image)

### Initial Error
```bash
$ python scripts/test_new_tools.py chembl -v

Testing ChEMBL_get_molecule_image (1 examples)...
  ❌ ChEMBL_get_molecule_image Ex 1: Failed - 
     ChEMBL API request failed: Expecting value: line 1 column 1 (char 0)

Tests Run:        64
Passed:           63 (98.4%)
Failed:           1
```

### Diagnosis

**Step 1: Run direct test**
```python
from tooluniverse import ToolUniverse
import json

tu = ToolUniverse()
tu.load_tools()

result = tu.run_one_function({
    'name': 'ChEMBL_get_molecule_image',
    'arguments': {
        'chembl_id': 'CHEMBL25',
        'format': 'svg'
    }
})

print(json.dumps(result, indent=2))
```

**Output**: Same JSON parsing error

**Step 2: Check API directly**
```python
import requests

url = "https://www.ebi.ac.uk/chembl/api/data/image/CHEMBL25?format=svg"
response = requests.get(url)

print("Status:", response.status_code)              # 200
print("Content-Type:", response.headers.get("Content-Type"))  # image/svg+xml
print("Is JSON?:", response.text[:10])              # <?xml... (SVG content)
```

**Root cause**: API returns SVG image (binary), but tool tries to parse as JSON.

### Solution

**File 1: src/tooluniverse/chem_tool.py**

Located the issue in `ChEMBLRESTTool.run()` method:

```python
# BEFORE (line 146)
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    url = self._build_url(arguments)
    params = self._build_params(arguments)
    response = request_with_retry(...)
    response.raise_for_status()
    
    data = response.json()  # ❌ Fails for binary data
    
    return {
        "status": "success",
        "data": data,
        "url": response.url,
    }
```

Added binary detection:

```python
# AFTER
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    url = self._build_url(arguments)
    params = self._build_params(arguments)
    tool_name = self.tool_config.get("name", "")
    
    # Check if this is an image endpoint
    is_image_endpoint = "get_molecule_image" in tool_name.lower() or "/image/" in url
    
    response = request_with_retry(...)
    response.raise_for_status()

    # Handle image endpoints differently
    if is_image_endpoint:
        content_type = response.headers.get("Content-Type", "")
        if "image" in content_type or "svg" in content_type:
            return {
                "status": "success",
                "data": f"Image data available at URL (Content-Type: {content_type})",
                "url": response.url,
                "content_type": content_type,
                "image_size_bytes": len(response.content)
            }

    data = response.json()  # ✅ Only called for JSON endpoints
    
    return {
        "status": "success",
        "data": data,
        "url": response.url,
    }
```

**File 2: src/tooluniverse/data/chembl_tools.json**

Initially tried this schema (wrong):
```json
{
  "name": "ChEMBL_get_molecule_image",
  "return_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "data": {"type": "string"},
      "url": {"type": "string"}
    }
  }
}
```

Result: Still failed schema validation because test validates `data` field (a string) against entire schema (which says root type is "object").

**Correct schema**:
```json
{
  "name": "ChEMBL_get_molecule_image",
  "return_schema": {
    "type": "string",
    "description": "Description of image data availability and access information"
  }
}
```

**File 3: Regenerate tools**
```bash
python -m tooluniverse.generate_tools
```

### Verification

```bash
$ python scripts/test_new_tools.py chembl -v

Testing ChEMBL_get_molecule_image (1 examples)...
  ✅ Ex 1: Passed

Tests Run:        64
Passed:           64 (100.0%)
Failed:           0
Schema Valid:     64
Schema Invalid:   0
```

**Direct test**:
```python
result = tu.run_one_function({
    'name': 'ChEMBL_get_molecule_image',
    'arguments': {'chembl_id': 'CHEMBL25', 'format': 'svg'}
})

print(json.dumps(result, indent=2))
```

**Output**:
```json
{
  "status": "success",
  "data": "Image data available at URL (Content-Type: image/svg+xml)",
  "url": "https://www.ebi.ac.uk/chembl/api/data/image/CHEMBL25?format=svg",
  "content_type": "image/svg+xml",
  "image_size_bytes": 8476
}
```

### Key Learnings

1. **Content-Type detection is critical** - Check headers before parsing
2. **Schema describes data field only** - Not the full response structure
3. **jsonschema is permissive** - `{"type": "object"}` validates any dict
4. **Test both ways** - Use test script AND direct execution
5. **Binary data needs special handling** - Return metadata instead of content

---

## Example 2: Schema Validation Fix Pattern

### Problem
```
⚠️  Tool_search Ex 1: Schema Mismatch: 
   At root: 'result_string' is not of type 'object'
```

### Diagnosis

**Check what data field contains**:
```python
result = tu.run_one_function({'name': 'Tool_search', 'arguments': {...}})
print("Data type:", type(result.get('data')))  # <class 'str'>
print("Data value:", result.get('data'))       # "Found 5 results"
```

**Check schema**:
```json
{
  "return_schema": {
    "type": "object",
    "properties": {
      "results": {"type": "array"}
    }
  }
}
```

**Problem**: Data is string, but schema expects object.

### Solution

**Option A: Change tool to return object**
```python
# In tool class
return {
    "status": "success",
    "data": {
        "message": "Found 5 results",
        "count": 5
    }
}
```

**Option B: Change schema to match string** (if tool design is correct)
```json
{
  "return_schema": {
    "type": "string",
    "description": "Search result message"
  }
}
```

Choose based on:
- Tool's intended design
- Consistency with similar tools
- User expectations

---

## Example 3: Endpoint URL Fix

### Problem
```
❌ Tool_get_data Ex 1: Failed - ChEMBL API returned HTTP 404
```

### Diagnosis

**Check endpoint configuration**:
```json
{
  "name": "Tool_get_data",
  "fields": {
    "endpoint": "/data/{id}.json"
  },
  "test_examples": [
    {"id": "12345"}
  ]
}
```

**Test endpoint manually**:
```bash
curl https://api.example.com/data/12345.json
# Returns 404
```

**Find correct endpoint**:
```bash
curl https://api.example.com/records/12345.json
# Returns 200 ✓
```

### Solution

```json
{
  "name": "Tool_get_data",
  "fields": {
    "endpoint": "/records/{id}.json"  // ✅ Fixed
  }
}
```

---

## Example 4: Parameter Schema Fix

### Problem
```
❌ Tool_search Ex 1: Failed - 400 Bad Request: 
   Parameter 'limit' must be integer
```

### Diagnosis

**Check parameter schema**:
```json
{
  "parameter": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "limit": {"type": "string"}  // ❌ Wrong type
    }
  }
}
```

**Check test example**:
```json
{
  "test_examples": [
    {"query": "test", "limit": "10"}  // String passed
  ]
}
```

### Solution

```json
{
  "parameter": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "limit": {
        "type": "integer",           // ✅ Fixed type
        "default": 20,
        "minimum": 1,
        "maximum": 1000
      }
    }
  },
  "test_examples": [
    {"query": "test", "limit": 10}   // ✅ Integer
  ]
}
```

---

## Example 5: Complex Response Handling

### Problem
Tool returns nested structure but schema is too simple.

### Original Schema
```json
{
  "return_schema": {
    "type": "object"
  }
}
```

### Better Schema
```json
{
  "return_schema": {
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "score": {"type": "number"}
          }
        }
      },
      "total": {"type": "integer"},
      "page": {"type": "integer"}
    }
  }
}
```

**Trade-off**: More specific schema provides better validation but requires maintenance if API changes.

**Recommendation**: Use detailed schemas for critical tools, simple schemas for exploratory tools.

---

## Debugging Workflow Example

Complete debugging session for a failing tool:

```bash
# 1. Identify failure
$ python scripts/test_new_tools.py category -v
# Note: Tool_name failed with error X

# 2. Test directly with Python
$ python -c "
from tooluniverse import ToolUniverse
import json

tu = ToolUniverse()
tu.load_tools()

result = tu.run_one_function({
    'name': 'Tool_name',
    'arguments': {'param': 'value'}
})

print(json.dumps(result, indent=2))
"

# 3. Check API directly
$ curl -v https://api.example.com/endpoint

# 4. Compare with working tool
$ grep -A 20 "Working_tool" src/tooluniverse/data/category_tools.json

# 5. Implement fix
$ vim src/tooluniverse/category_tool.py
$ vim src/tooluniverse/data/category_tools.json

# 6. Regenerate
$ python -m tooluniverse.generate_tools

# 7. Verify
$ python scripts/test_new_tools.py category -v

# 8. Document
$ vim TOOL_FIX_SUMMARY.md
```

---

## Testing Patterns

### Test Individual Tool
```python
from tooluniverse import ToolUniverse
import json

def test_tool(tool_name, arguments):
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run_one_function({
        'name': tool_name,
        'arguments': arguments
    })
    
    print(f"\n{'='*50}")
    print(f"Testing: {tool_name}")
    print('='*50)
    print(json.dumps(result, indent=2))
    
    # Check status
    status = result.get('status')
    print(f"\nStatus: {status}")
    
    if status == 'error':
        print(f"Error: {result.get('error')}")
        return False
    
    return True

# Usage
test_tool('ChEMBL_get_molecule_image', {
    'chembl_id': 'CHEMBL25',
    'format': 'svg'
})
```

### Test Schema Validation
```python
from jsonschema import validate, ValidationError
import json

def test_schema(tool_name):
    # Load config
    with open('src/tooluniverse/data/chembl_tools.json') as f:
        tools = json.load(f)
        tool = next(t for t in tools if t['name'] == tool_name)
        schema = tool['return_schema']
    
    # Run tool
    tu = ToolUniverse()
    tu.load_tools()
    result = tu.run_one_function({
        'name': tool_name,
        'arguments': tool['test_examples'][0]
    })
    
    # Validate
    data = result.get('data')
    try:
        validate(instance=data, schema=schema)
        print(f"✅ Schema validation passed for {tool_name}")
        return True
    except ValidationError as e:
        print(f"❌ Schema validation failed: {e.message}")
        return False
```

### Test Multiple Examples
```python
def test_all_examples(tool_name):
    # Load config
    with open('src/tooluniverse/data/chembl_tools.json') as f:
        tools = json.load(f)
        tool = next(t for t in tools if t['name'] == tool_name)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    examples = tool.get('test_examples', [])
    passed = 0
    
    for i, example in enumerate(examples, 1):
        try:
            result = tu.run_one_function({
                'name': tool_name,
                'arguments': example
            })
            
            if result.get('status') == 'success':
                print(f"✅ Example {i} passed")
                passed += 1
            else:
                print(f"❌ Example {i} failed: {result.get('error')}")
        except Exception as e:
            print(f"🔥 Example {i} exception: {e}")
    
    print(f"\nResults: {passed}/{len(examples)} passed")
    return passed == len(examples)
```
