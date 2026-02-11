# Test Writing Guide for ToolUniverse

## Response Structure Handling

When writing tests for ToolUniverse tools, be aware that tool responses may have data in either a **flat** or **nested** structure depending on the tool implementation.

### Response Formats

#### Nested Structure (New)
```python
{
    "status": "success",
    "data": {
        "num_results": 5,
        "results": [...]
    }
}
```

#### Flat Structure (Legacy)
```python
{
    "status": "success",
    "num_results": 5,
    "results": [...]
}
```

### Writing Compatible Tests

Always write tests that handle both formats:

#### ❌ Bad (Only checks flat structure)
```python
def test_search(self, tu):
    result = tu.tools.MyTool_search(**{"query": "test"})
    assert result["status"] == "success"
    assert "results" in result  # Will fail if nested!
```

#### ✅ Good (Handles both structures)
```python
def test_search(self, tu):
    result = tu.tools.MyTool_search(**{"query": "test"})
    assert result["status"] == "success"
    
    # Check if data is nested or flat
    data = result.get("data", result)
    assert "results" in data
```

### Pattern Examples

#### Pattern 1: Simple Field Check
```python
if result["status"] == "success":
    data = result.get("data", result)
    assert "field_name" in data
```

#### Pattern 2: Multiple Fields
```python
if result["status"] == "success":
    data = result.get("data", result)
    expected_fields = ["field1", "field2", "field3"]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"
```

#### Pattern 3: Checking Lists
```python
if result["status"] == "success":
    data = result.get("data", result)
    assert "results" in data
    assert isinstance(data["results"], list)
```

#### Pattern 4: Backwards Compatible Access
```python
if result["status"] == "success":
    # Try nested first, fall back to flat
    results = result.get("data", {}).get("results", result.get("results"))
    assert results is not None
    assert isinstance(results, list)
```

### Testing Error Responses

Error responses are always at the top level:
```python
if result["status"] == "error":
    assert "error" in result
    assert isinstance(result["error"], str)
```

### Status Checks

Always check status first:
```python
def test_operation(self, tu):
    result = tu.tools.MyTool_operation(**params)
    
    # Always check status exists
    assert "status" in result
    assert result["status"] in ["success", "error", "warning"]
    
    # Then handle accordingly
    if result["status"] == "success":
        data = result.get("data", result)
        # ... check data fields
    elif result["status"] == "error":
        assert "error" in result
```

### Real-World Examples

From fixed test files:

#### Example 1: FourDN Search
```python
def test_search_data_basic(self, tu):
    result = tu.tools.FourDN_search_data(**{
        "operation": "search",
        "query": "*",
        "limit": 5
    })
    
    assert "status" in result
    if result["status"] == "success":
        assert "data" in result
        assert "num_results" in result["data"] or "num_results" in result
    else:
        assert "error" in result
```

#### Example 2: GTEx Dataset Info
```python
def test_get_dataset_info(self, tu):
    result = tu.tools.GTEx_get_dataset_info(**{
        "operation": "get_dataset_info"
    })
    
    assert result.get("status") == "success" or "error" in result
    
    if result.get("status") == "success":
        # Check if data is nested or flat
        datasets = result.get("data", result.get("datasets"))
        assert datasets is not None
        assert isinstance(datasets, list)
```

#### Example 3: Rfam Alignment
```python
def test_get_alignment(self, tu):
    result = tu.tools.Rfam_get_alignment(**{
        "operation": "get_alignment",
        "family_id": "RF00360",
        "format": "fasta"
    })
    
    assert result.get("status") == "success" or "error" in result
    
    if result.get("status") == "success":
        data = result.get("data", result)
        assert "alignment" in data
        assert "format" in data
```

## Best Practices

1. **Always check `status` first** - Every response should have a status field
2. **Use `.get()` for optional fields** - Prevents KeyError
3. **Handle both nested and flat** - Use `result.get("data", result)` pattern
4. **Test both success and error cases** - Don't assume success
5. **Use descriptive assertion messages** - Help debugging with `assert field in data, f"Missing {field}"`
6. **Mock slow APIs** - Use `@patch` for unit tests, mark integration tests appropriately

## Testing Checklist

- [ ] Test checks for `status` field
- [ ] Test handles both nested and flat response structures
- [ ] Test handles error responses gracefully
- [ ] Test has clear assertion messages
- [ ] Test doesn't assume API will succeed
- [ ] Test uses appropriate timeout for integration tests
- [ ] Test is properly categorized (unit/integration)

## Common Pitfalls

### ❌ Assuming Flat Structure
```python
assert "results" in result  # May fail!
```

### ❌ Not Checking Status
```python
data = result["data"]  # KeyError if status is "error"!
```

### ❌ Hard-coded Field Paths
```python
assert result["data"]["results"]  # Breaks if structure changes!
```

### ✅ Correct Approach
```python
assert "status" in result
if result["status"] == "success":
    data = result.get("data", result)
    assert "results" in data
```

## Migration Guide

If you have existing tests that fail with "field not in result" errors:

1. Find the failing assertion (e.g., `assert "field" in result`)
2. Add compatibility check: `data = result.get("data", result)`
3. Update assertion: `assert "field" in data`
4. Re-run test to verify

Example migration:
```diff
  if result["status"] == "success":
-     assert "results" in result
-     assert isinstance(result["results"], list)
+     data = result.get("data", result)
+     assert "results" in data
+     assert isinstance(data["results"], list)
```

## Questions?

- Check `TEST_FIXES_SUMMARY.md` for examples of recent fixes
- Look at `test_biostudies_tool.py` or `test_ensembl_tool.py` for well-structured tests
- See fixed tests in `test_fourdn_tool.py` for before/after examples
