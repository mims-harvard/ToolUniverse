# Tool Improvement and Maintenance Checklist

This reference provides a systematic approach to improving and maintaining existing ToolUniverse tools.

## Phase 1: Initial Assessment

### Step 1.1: Identify Tool Files

Locate all relevant files for the tool category:

```bash
# Tool class file
src/tooluniverse/{category}_tool.py

# JSON configuration
src/tooluniverse/data/{category}_tools.json

# Auto-generated wrappers (DO NOT EDIT)
src/tooluniverse/tools/{category}_*.py

# Check registration
grep "@register_tool" src/tooluniverse/{category}_tool.py

# Check imports (auto-generated)
grep "{category}" src/tooluniverse/tools/__init__.py
```

### Step 1.2: Verify Basic Structure

- [ ] Tool class registration exists (`@register_tool`)
- [ ] Class name matches JSON config `"type"` field
- [ ] JSON file is valid: `python3 -m json.tool {file}.json`
- [ ] Tool loads without errors: `tu.load_tools()`
- [ ] Python syntax is valid: `python3 -m py_compile {file}.py`

## Phase 2: Functionality Testing

### Step 2.1: Test Tool Execution

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()

# List tools
tools = [t for t in tu.list_tools() if t.startswith('category_')]

# Test each tool
for tool_name in tools:
    print(f"\nTesting {tool_name}...")
    
    # Get test example from JSON
    result = tu.run_tool(tool_name, test_arguments)
    
    # Verify results
    assert result is not None, "Result is None"
    assert result != {}, "Result is empty"
    assert "error" not in result or result.get("status") != "error"
    
    print(f"✓ {tool_name} passed")
```

Checklist:
- [ ] Tool executes without errors
- [ ] Results contain data (not empty)
- [ ] Response structure matches return_schema
- [ ] Error handling works with invalid inputs

### Step 2.2: Test API Endpoints Directly

```python
import requests

# Test endpoint directly
url = "https://api.example.com/endpoint"
response = requests.get(url, params={"id": "test123"})

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")
```

Checklist:
- [ ] REST/GraphQL endpoints respond correctly
- [ ] Status codes are 200 OK (not 404/502/503)
- [ ] Response format matches tool expectations
- [ ] Authentication works if required

## Phase 3: Description Improvement

### Step 3.1: Review Tool Descriptions

Good description template:

```json
{
  "description": "[ACTION] [WHAT] from [SOURCE]. [INPUT DETAILS]. Returns [OUTPUT DETAILS] including [KEY FIELDS]. Use for: [USE CASE 1], [USE CASE 2], [USE CASE 3]. Example: [BRIEF EXAMPLE]."
}
```

Example:

```json
{
  "description": "Search for clinical trials by condition or intervention. Accepts disease names, drug names, or medical terms. Returns trial details including status, phase, locations, and eligibility criteria. Use for: drug development research, patient recruitment, competitive analysis. Example: Search 'diabetes' to find all diabetes-related trials."
}
```

Checklist:
- [ ] Description includes purpose
- [ ] Description explains inputs
- [ ] Description explains outputs
- [ ] Description lists use cases
- [ ] Description includes brief example
- [ ] Description is clear to users unfamiliar with API

### Step 3.2: Review Parameter Descriptions

For each parameter:

```json
{
  "parameter": {
    "properties": {
      "query": {
        "type": "string",
        "description": "Search term for drug name or condition. Examples: 'aspirin', 'hypertension', 'cancer therapy'. Case-insensitive, supports partial matches."
      },
      "max_results": {
        "type": "integer",
        "description": "Maximum number of results to return. Default: 20. Range: 1-100.",
        "default": 20
      },
      "sort_by": {
        "type": "string",
        "description": "Sort order for results. Options: 'relevance', 'date', 'name'. Default: 'relevance'.",
        "default": "relevance"
      }
    }
  }
}
```

Checklist:
- [ ] Has clear description with example values
- [ ] Has default value if optional
- [ ] Has constraints (min/max/enum) if applicable
- [ ] Type is correct (string, integer, boolean, array, object)
- [ ] Enums list all valid options (or describe in text if many)

### Step 3.3: Review Return Schema

**Anti-pattern** (avoid this):

```json
{
  "return_schema": {
    "type": "object",
    "properties": {
      "data": {
        "type": "object",
        "additionalProperties": true
      }
    }
  }
}
```

**Good pattern** (do this):

```json
{
  "return_schema": {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "description": "Request status: 'success' or 'error'"
      },
      "count": {
        "type": "integer",
        "description": "Total number of results"
      },
      "next": {
        "type": ["string", "null"],
        "description": "URL for next page of results, null if last page"
      },
      "previous": {
        "type": ["string", "null"],
        "description": "URL for previous page of results, null if first page"
      },
      "results": {
        "type": "array",
        "description": "Array of result objects",
        "items": {
          "type": "object",
          "properties": {
            "id": {
              "type": "string",
              "description": "Unique identifier"
            },
            "name": {
              "type": "string",
              "description": "Display name"
            },
            "description": {
              "type": "string",
              "description": "Detailed description"
            }
          },
          "additionalProperties": true
        }
      }
    }
  }
}
```

Checklist:
- [ ] return_schema field exists
- [ ] Schema matches actual tool output (test live responses)
- [ ] Schema is meaningful (not just `additionalProperties: true`)
- [ ] Common patterns modeled explicitly:
  - [ ] Paginated lists: `count`, `next`, `previous`, `results[]`
  - [ ] Detail objects: required identifiers + key domain fields
- [ ] Nested structures type important subfields
- [ ] Use `additionalProperties: true` for flexibility
- [ ] Handle type variability with unions: `["string", "number", "null"]`
- [ ] Wrapper fields included if tool adds them (`status`, `url`, `error`)

## Phase 4: Error Handling Improvement

### Step 4.1: Review Current Error Handling

Test error scenarios:

```python
# Test missing required parameter
result = tu.run_tool("tool_name", {})

# Test invalid parameter value
result = tu.run_tool("tool_name", {"id": "invalid"})

# Test network error (mock or use bad URL)
```

Checklist:
- [ ] Error messages are specific (not generic)
- [ ] Try/except blocks exist around risky operations
- [ ] Errors return dict with "error" key
- [ ] HTTP errors handled (404, 502, 503)

### Step 4.2: Improve Error Messages

**Bad error message**:
```python
return {"error": "Invalid input"}
```

**Good error message**:
```python
return {
    "status": "error",
    "error": "Invalid parameter: 'drug_name' must be a non-empty string",
    "detail": f"Received: {drug_name}",
    "suggestion": "Provide a valid drug name, e.g., 'aspirin'"
}
```

Error message checklist:
- [ ] Specific: States exactly what went wrong
- [ ] Actionable: Suggests how to fix the problem
- [ ] Context: Includes relevant details (status_code, endpoint, values)
- [ ] User-friendly: Written for end users, not developers
- [ ] Consistent: Uses same error envelope across tool family

### Step 4.3: Add Retry Logic

When to add retries:
- Network connection errors
- Timeout errors
- 502/503 service unavailable errors
- Rate limit errors (with longer backoff)

When NOT to retry:
- 400 Bad Request (client error)
- 401 Unauthorized (auth error)
- 404 Not Found (resource doesn't exist)
- Validation errors

Implementation:

```python
import time
import requests

def _request_with_retry(self, url: str, params: dict, max_retries: int = 3):
    """Make request with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response
            
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait_time)
            
        except requests.HTTPError as e:
            # Don't retry 4xx client errors
            if 400 <= e.response.status_code < 500:
                raise
            # Retry 5xx server errors
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

Checklist:
- [ ] Identify transient failures (ConnectionError, Timeout, 5xx)
- [ ] Implement exponential backoff (1s, 2s, 4s, ...)
- [ ] Set max retries (typically 2-3)
- [ ] Don't retry 4xx client errors
- [ ] Handle final failure appropriately
- [ ] Use shared retry helper if available in codebase

## Phase 5: Finding Missing Tools

### Step 5.1: Research API Capabilities

Methods to discover all API capabilities:

**1. Read Official API Documentation**

```bash
# Search for API docs
https://example.com/api/docs
https://example.com/developers
https://docs.example.com
```

**2. GraphQL Introspection**

```python
import requests

query = """
query {
  __schema {
    queryType {
      fields {
        name
        description
      }
    }
  }
}
"""

response = requests.post(
    'https://api.example.com/graphql',
    json={'query': query}
)
print(response.json())
```

**3. Test Endpoint Patterns**

```python
# Try common patterns
endpoints = [
    "/search",
    "/list",
    "/get/{id}",
    "/details/{id}",
    "/query",
    "/find"
]

for endpoint in endpoints:
    url = f"https://api.example.com{endpoint}"
    response = requests.get(url)
    print(f"{endpoint}: {response.status_code}")
```

**4. Check Related Packages**

```bash
# R/Bioconductor packages
https://bioconductor.org/packages/

# Python packages
https://pypi.org/search/?q=example

# Look at package source code for API calls
```

**5. Web Search**

```
"{API_NAME} API documentation"
"{API_NAME} API endpoints"
"{API_NAME} API reference"
site:github.com "{API_NAME} API"
```

### Step 5.2: Create Gap Analysis Matrix

Create a comparison table:

| API Capability | Implemented? | Priority | Notes |
|----------------|--------------|----------|-------|
| Search drugs | ✓ | - | `search_drugs` |
| Get drug details | ✓ | - | `get_drug_details` |
| List adverse events | ✗ | HIGH | Common use case |
| Get recall information | ✗ | HIGH | Safety critical |
| Search clinical trials | ✗ | MEDIUM | Related functionality |
| Get approval history | ✗ | LOW | Niche use case |

Prioritization criteria:
- **HIGH**: Common use case, core functionality, fills major gap
- **MEDIUM**: Useful but not critical, nice-to-have
- **LOW**: Niche use case, edge functionality

### Step 5.3: Identify Subset Extraction Opportunities

When full responses are large/complex, create focused subset tools:

**Example**: Large drug object with many fields

```python
# Main tool returns everything
def get_drug_details(drug_id):
    return {
        "id": "...",
        "name": "...",
        "manufacturer": "...",
        "approval_date": "...",
        "ingredients": [...],
        "adverse_events": [...],
        "clinical_trials": [...],
        # ... 50+ more fields
    }

# Subset tools extract specific data
def get_drug_adverse_events(drug_id):
    """Extract only adverse events from drug data."""
    full_data = get_drug_details(drug_id)
    return {
        "drug_id": drug_id,
        "drug_name": full_data["name"],
        "adverse_events": full_data["adverse_events"]
    }

def get_drug_ingredients(drug_id):
    """Extract only ingredients from drug data."""
    full_data = get_drug_details(drug_id)
    return {
        "drug_id": drug_id,
        "drug_name": full_data["name"],
        "ingredients": full_data["ingredients"]
    }
```

Checklist:
- [ ] Check if full response is large (>1000 lines) or complex (>5 nested levels)
- [ ] Identify common subsets users need (diseases, pathways, events, etc.)
- [ ] Create focused tools that extract specific data types
- [ ] Implement helper method: `_extract_subset()`
- [ ] Add field selection parameter when supported upstream
- [ ] Document allowed fields in description (not schema enum if many)

## Phase 6: Fix Common Issues

### Issue 6.1: Tool Class Name Mismatch

**Symptoms**:
- Tool doesn't load
- "Tool not found" errors
- Registration errors

**Check**:

```bash
# Check Python class name
grep "class.*BaseTool" src/tooluniverse/{category}_tool.py

# Check registration
grep "@register_tool" src/tooluniverse/{category}_tool.py

# Check JSON type
grep '"type":' src/tooluniverse/data/{category}_tools.json
```

**Fix**: Ensure exact match (case-sensitive):

```python
@register_tool("DrugSearchTool")  # Must match exactly
class DrugSearchTool(BaseTool):
    ...
```

```json
{
  "type": "DrugSearchTool"  // Must match exactly
}
```

### Issue 6.2: Response Format Mismatch

**Symptoms**:
- `'list' object has no attribute 'get'`
- `TypeError: 'NoneType' object is not subscriptable`
- Unexpected data structure errors

**Check**:

```python
# Test API response directly
import requests
response = requests.get(url)
data = response.json()
print(f"Type: {type(data)}")
print(f"Data: {data}")
```

**Fix**: Convert as needed:

```python
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.get(url)
    data = response.json()
    
    # API returns list, but tool expects dict
    if isinstance(data, list):
        return {
            "status": "success",
            "count": len(data),
            "results": data
        }
    
    # API returns None
    if data is None:
        return {
            "status": "error",
            "error": "No data returned from API"
        }
    
    # API returns dict as expected
    return {
        "status": "success",
        "data": data
    }
```

### Issue 6.3: Endpoint URL Issues

**Symptoms**:
- 404 Not Found errors
- "Endpoint does not exist" errors

**Check**:

```python
# Test endpoint directly
import requests

url = "https://api.example.com/v1/drugs/search"
response = requests.get(url, params={"query": "aspirin"})
print(f"Status: {response.status_code}")
print(f"URL: {response.url}")
print(f"Response: {response.text}")
```

**Common URL issues**:

```python
# Wrong: Missing API version
url = "https://api.example.com/drugs"  # 404

# Right: Include API version
url = "https://api.example.com/v1/drugs"  # 200

# Wrong: Incorrect placeholder replacement
url = f"https://api.example.com/drugs/{drug_id}"  # drug_id = None

# Right: Validate before replacing
if not drug_id:
    return {"error": "drug_id is required"}
url = f"https://api.example.com/drugs/{drug_id}"

# Wrong: Missing trailing slash
url = "https://api.example.com/drugs"  # Some APIs require this

# Right: Check API documentation
url = "https://api.example.com/drugs/"
```

### Issue 6.4: Missing Error Handling

**Symptoms**:
- Tool crashes on API errors
- Unhandled exceptions
- No error messages returned

**Fix**: Add comprehensive error handling:

```python
def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Validate parameters
        if 'query' not in arguments:
            return {
                "status": "error",
                "error": "Missing required parameter: query"
            }
        
        # Make API request
        response = requests.get(url, params=arguments, timeout=30)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        return {
            "status": "success",
            "data": data
        }
        
    except requests.Timeout:
        return {
            "status": "error",
            "error": "Request timed out after 30 seconds",
            "suggestion": "Try again or use a more specific query"
        }
    
    except requests.ConnectionError as e:
        return {
            "status": "error",
            "error": "Failed to connect to API",
            "detail": str(e),
            "suggestion": "Check network connection and API availability"
        }
    
    except requests.HTTPError as e:
        return {
            "status": "error",
            "error": f"API request failed: {e.response.status_code}",
            "detail": e.response.text,
            "url": e.response.url
        }
    
    except ValueError as e:
        return {
            "status": "error",
            "error": "Invalid response from API",
            "detail": str(e)
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {type(e).__name__}",
            "detail": str(e)
        }
```

## Phase 7: Final Verification

### Step 7.1: Comprehensive Testing

Test matrix:

| Test Case | Expected Result | Status |
|-----------|----------------|--------|
| Valid input | Success response with data | ✓ |
| Missing required param | Error message | ✓ |
| Invalid param type | Error message | ✓ |
| Empty string | Error or empty results | ✓ |
| Special characters | Handled correctly | ✓ |
| Large input | Handles gracefully | ✓ |
| Network error | Error message | ✓ |
| API error (404) | Error message | ✓ |
| API error (500) | Error message | ✓ |

### Step 7.2: Validation Checks

```bash
# Validate JSON
python3 -m json.tool src/tooluniverse/data/{category}_tools.json

# Check Python syntax
python3 -m py_compile src/tooluniverse/{category}_tool.py

# Check linting
pylint src/tooluniverse/{category}_tool.py

# Verify tool loads
python3 -c "from tooluniverse import ToolUniverse; tu = ToolUniverse(); print(tu.list_tools())"

# Check auto-generated wrappers exist
ls src/tooluniverse/tools/{category}_*.py

# Check tool name lengths
python scripts/check_tool_name_lengths.py --test-shortening
```

Checklist:
- [ ] JSON files are valid
- [ ] Python syntax is valid
- [ ] No linting errors
- [ ] All tools load without errors
- [ ] Tool functions exist in `tools/` directory (auto-generated)
- [ ] Category registered if needed

### Step 7.3: Documentation

Create example script in `examples/{category}_tools_example.py`:

```python
"""
Example usage of {category} tools.
"""

from tooluniverse import ToolUniverse

def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    
    # Example 1: Search for drugs
    print("Searching for aspirin...")
    result = tu.run_tool("search_drugs", {"query": "aspirin"})
    print(f"Found {result['count']} results")
    
    # Example 2: Get drug details
    if result['results']:
        drug_id = result['results'][0]['id']
        print(f"\nGetting details for drug {drug_id}...")
        details = tu.run_tool("get_drug_details", {"drug_id": drug_id})
        print(f"Name: {details['name']}")
        print(f"Manufacturer: {details['manufacturer']}")
    
    # Example 3: Error handling
    print("\nTesting error handling...")
    error_result = tu.run_tool("get_drug_details", {"drug_id": "invalid"})
    print(f"Error: {error_result.get('error')}")

if __name__ == "__main__":
    main()
```

Documentation checklist:
- [ ] Tool descriptions are clear and complete
- [ ] Parameter descriptions include examples
- [ ] Return schemas match actual output
- [ ] Example script created in `examples/`
- [ ] Document findings and fixes in commit message

## Summary Checklist

Quick reference for complete tool improvement:

**✓ Phase 1: Initial Assessment**
- Identify all tool files
- Verify basic structure

**✓ Phase 2: Functionality Testing**
- Test tool execution
- Test API endpoints directly

**✓ Phase 3: Description Improvement**
- Review tool descriptions
- Review parameter descriptions
- Review return schemas

**✓ Phase 4: Error Handling**
- Review current error handling
- Improve error messages
- Add retry logic if needed

**✓ Phase 5: Finding Missing Tools**
- Research API capabilities
- Create gap analysis matrix
- Identify subset extraction opportunities

**✓ Phase 6: Fix Common Issues**
- Fix tool class name mismatches
- Fix response format mismatches
- Fix endpoint URL issues
- Add missing error handling

**✓ Phase 7: Final Verification**
- Comprehensive testing
- Validation checks
- Documentation updates

**For large API expansions (many endpoints in one category):**
- [ ] Use a generic REST tool + JSON configs to cover multiple endpoints
- [ ] Verify real API behavior with live requests (prefer working patterns over docs)
- [ ] Make `return_schema` match the tool's wrapper and validate upstream payload structure at a useful depth (paging shapes, required IDs, important nested fields)
- [ ] Use real IDs from search/list endpoints in `test_examples`
- [ ] Remove tools for endpoints that have no working or replacement API
- [ ] Design "research-first": include discovery tools (search/list), detail tools (get by ID), and version/release tools for reproducibility
- [ ] Keep schemas and parameter surfaces LLM-friendly: avoid enormous enums; keep descriptions explicit; enforce strict validation in code
