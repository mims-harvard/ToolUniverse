# Tool Testing Workflow

**CRITICAL**: Always test tools BEFORE writing documentation

## Why Test First?

**Lesson from real failures**: All 4 broken skills (DDI, Clinical Trial, Antibody, CRISPR) had excellent documentation but 0-20% functionality because tools were never tested.

**Problems testing prevents**:
- Parameter name mismatches (function name ≠ actual parameter)
- SOAP tools missing `operation` parameter
- Response format variations (standard, direct list, direct dict)
- Tools that don't work or return errors
- Incorrect assumptions about tool behavior

## Test-Driven Workflow

```
1. Read tool configs →
2. Create test script →
3. Run tests →
4. Document findings →
5. Fix issues →
6. Re-test →
7. THEN write skill documentation
```

## Test Script Template

```python
#!/usr/bin/env python3
"""
Test script for [Domain] tools
Following TDD: test ALL tools BEFORE creating skill documentation
"""

from tooluniverse import ToolUniverse
import json

def test_database_tools():
    """Test [Database] tools"""
    print("\n" + "="*80)
    print("TESTING [DATABASE] TOOLS")
    print("="*80)

    tu = ToolUniverse()
    tu.load_tools()

    # Test 1: [Tool purpose]
    print("\n1. Testing TOOL_NAME...")
    result = tu.tools.TOOL_NAME(param1="value1", param2="value2")

    # Check response format
    if isinstance(result, dict) and result.get('status') == 'success':
        print(f"Status: {result.get('status')}")
        data = result.get('data', [])
        print(f"Found {len(data)} results")
        if data:
            print(f"First result: {data[0]}")
    elif isinstance(result, list):
        print(f"Status: success (direct list response)")
        print(f"Found {len(result)} results")
    elif isinstance(result, dict) and 'field_name' in result:
        print(f"Status: success (direct dict response)")
        print(f"Keys: {result.keys()}")
    else:
        print(f"ERROR: Unexpected response format: {type(result)}")
        print(f"Response: {result}")

    return True

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("[DOMAIN] TOOLS TEST SUITE")
    print("Following TDD: Test tools FIRST before creating skill documentation")
    print("="*80)

    tests = [
        ("Database 1", test_database_tools),
    ]

    results = {}
    for name, test_func in tests:
        try:
            success = test_func()
            results[name] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            print(f"\n❌ EXCEPTION in {name}: {e}")
            results[name] = f"❌ EXCEPTION: {str(e)[:100]}"

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for name, result in results.items():
        print(f"{name:25} {result}")

    print("\n✅ All tests completed. Tool parameters verified.")
    print("Ready to create working pipeline → then documentation")

if __name__ == "__main__":
    main()
```

## What to Test

### 1. Tool Accessibility
- Tool loads in ToolUniverse
- Tool name is correct
- No import errors

### 2. Parameter Names
- Verify actual parameter names (don't assume from function name!)
- Check required vs optional parameters
- Note any special parameters (like `operation` for SOAP tools)

### 3. Response Format
Test returns:
- Standard: `{status: "success", data: [...]}`
- Direct list: `[...]`
- Direct dict: `{field1: ..., field2: ...}`

### 4. Data Structure
- Verify expected fields exist
- Check data types
- Note nested structures

### 5. Error Handling
- Test with invalid inputs
- Check error message format
- Verify graceful failure

## Documenting Test Results

Create parameter corrections table:

```markdown
| Tool | Common Mistake | Correct Parameter | Evidence |
|------|----------------|-------------------|----------|
| Reactome_map_uniprot_to_pathways | `uniprot_id` | `id` | Test output |
| drugbank_get_drug_info | `drug_name` | `query` | Test output |
```

Document response formats:

```markdown
**Response Format Notes**:
- **Reactome_list_top_pathways**: Returns list directly (not wrapped)
- **pc_search_pathways**: Returns dict with `total_hits` and `pathways`
- **enrichr_gene_enrichment**: Standard `{status, data}` format
```

## Example: Systems Biology Skill Testing

**Test file**: `test_pathway_tools.py`

**Discoveries**:
1. Reactome tools return lists directly (no status wrapper)
2. Pathway Commons returns dict with `total_hits` field
3. Parameter: `Reactome_map_uniprot_to_pathways` uses `id` not `uniprot_id`
4. Enrichr tool name: `enrichr_gene_enrichment_analysis` (not `enrichr_submit_genes`)
5. GO tools: Capital `GO_search_terms` (not lowercase `go_search_terms`)

**Result**: All issues caught before documentation, 100% functional skill created

## Red Flags in Testing

❌ **Tool returns empty consistently** - Wrong parameters
❌ **Error about 'operation' required** - SOAP tool missing operation parameter
❌ **Unexpected response type** - Response format different than assumed
❌ **Tool not found** - Tool name incorrect
❌ **Timeout or API errors** - Need fallback strategy

## After Testing

Only after 100% tool verification:
1. Create python_implementation.py with tested tools
2. Write SKILL.md documenting verified workflow
3. Create QUICK_START.md with working examples
4. Create test_skill.py for end-to-end testing

**Never reverse this order!**
