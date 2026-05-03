# Tool Implementation Guide

Complete guidelines for adding and maintaining tools in ToolUniverse. This is the authoritative reference for tool structure, configuration conventions, and the development checklist.

## Guidelines for Adding Tools

Based on `docs/expand_tooluniverse/contributing/local_tools.rst` and the current codebase structure.

### File Structure & Location

- **Source Code**: `src/tooluniverse/xxx_tool.py`
- **Configuration**: `src/tooluniverse/data/xxx_tools.json`
- **Tests**: `tests/unit/test_xxx_tool.py`
- **DO NOT** manually create files in `src/tooluniverse/tools/` — these are auto-generated wrappers.

### Implementation Pattern

1. **Inheritance**: Tool class must inherit from `BaseTool`.
2. **Registration**: Use `@register_tool` decorator with the class name.

```python
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

@register_tool("MyNewTool")
class MyNewTool(BaseTool):
    """My new tool description."""
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {"result": "success"}
```

3. **Configuration**: Use external JSON file (do NOT embed large configs in the decorator).

```json
[
  {
    "name": "my_new_tool",
    "type": "MyNewTool",
    "description": "Convert text to uppercase",
    "parameter": {
      "type": "object",
      "properties": {
        "input": {
          "type": "string",
          "description": "Text to convert"
        }
      },
      "required": ["input"]
    },
    "return_schema": {
      "type": "object",
      "properties": {
        "result": {
          "type": "string",
          "description": "The converted text"
        }
      }
    },
    "test_examples": [
      {
        "input": "hello"
      }
    ]
  }
]
```

### JSON Configuration Conventions

- The `"type"` field must match the Python class name registered with `@register_tool`
- Include `return_schema` to define tool output structure
- Put example inputs in `test_examples` (and optionally short examples in `description`)
- **Avoid** adding JSON Schema `examples` blocks inside `parameter`/`return_schema` — they bloat configs and drift from reality
- For large allow-lists, prefer listing values in the tool `description` and enforcing in Python at runtime (instead of a huge schema `enum`)

### Auto-Discovery

Modern ToolUniverse uses automated discovery. You generally **do not** need to modify `src/tooluniverse/__init__.py` if you place your file correctly in `src/tooluniverse/`.

### Tool Naming Guidelines

- **Recommended**: ≤ 55 characters (fits in MCP with `mcp__tu__` prefix)
- **Maximum**: 64 characters (MCP hard limit without prefix)
- **Automatic shortening**: Long names are automatically shortened for MCP exposure
- **Best practice**: `FDA_get_drug_info` not `FDA_get_detailed_information_about_drug`

If your tool name exceeds 55 characters, it will be automatically shortened when exposed via MCP. See `docs/mcp_name_shortening.md` for details.

### Development Checklist

1. [ ] Create `src/tooluniverse/xxx_tool.py` with `@register_tool`
2. [ ] Create `src/tooluniverse/data/xxx_tools.json` including `return_schema`
3. [ ] Ensure tool names are ≤ 55 characters
4. [ ] Implement `run(arguments)` method
5. [ ] Implement `validate_parameters` (optional but recommended)
6. [ ] Write unit tests in `tests/unit/`
7. [ ] Verify tool load with `tu.load_tools()`
8. [ ] Run `python scripts/check_tool_name_lengths.py --test-shortening` to validate
9. [ ] Run `python scripts/test_new_tools.py your_tool -v` (MANDATORY)

---

## Tool Improvement and Maintenance Checklist

Systematic approach to improving and maintaining existing tools.

### Phase 1: Initial Assessment

#### Step 1.1: Identify Tool Files
- [ ] Locate tool class file: `src/tooluniverse/{category}_tool.py`
- [ ] Locate JSON config file: `src/tooluniverse/data/{category}_tools.json`
- [ ] List all tool function files: `src/tooluniverse/tools/{category}_*.py` (auto-generated wrappers)
- [ ] Check `default_config.py` for category registration
- [ ] Check `tools/__init__.py` for imports (auto-generated)

#### Step 1.2: Verify Basic Structure
- [ ] Tool class registration exists (`@register_tool`)
- [ ] Class name matches JSON config `"type"` field
- [ ] JSON file is valid
- [ ] Tool loads without errors
- [ ] Python syntax is valid

### Phase 2: Functionality Testing

#### Step 2.1: Test Tool Execution
- [ ] Load tools and test each tool with sample arguments
- [ ] Verify results contain data (not empty)
- [ ] Check response structure matches return_schema
- [ ] Test error handling with invalid inputs

#### Step 2.2: Test API Endpoints Directly
- [ ] Test REST/GraphQL endpoints respond correctly
- [ ] Verify status codes are 200 OK (not 404/502/503)
- [ ] Check response format matches tool expectations

### Phase 3: Description Improvement

#### Step 3.1: Review Tool Descriptions
- [ ] Description includes: purpose, input, output, use cases
- [ ] Description is clear to users unfamiliar with API
- [ ] Add usage guidance and example inputs (prefer `test_examples`; optionally include short examples in `description`, not in JSON Schema)

#### Step 3.2: Review Parameter Descriptions
For each parameter:
- [ ] Has clear description (include example values in the description text if helpful)
- [ ] Has default value if optional
- [ ] Has constraints (min/max/enum) if applicable
- [ ] Type is correct

#### Step 3.3: Review Return Schema
- [ ] `return_schema` field exists
- [ ] Schema matches actual tool output (test live responses; do not rely on docs alone)
- [ ] Schema is **meaningful** (avoid `data: { additionalProperties: true }` as the only definition)
- [ ] Model the common response shapes explicitly:
  - [ ] Paginated lists: `count`, `next`, `previous`, `results[]`
  - [ ] Detail objects: required identifiers + key domain fields
- [ ] For nested structures, type the important subfields but allow extra fields with `additionalProperties: true`
- [ ] Handle real-world type variability (e.g., values sometimes returned as string vs number): use union types like `["string","number","null"]`
- [ ] If the tool wraps upstream responses (e.g., adds `status`, `url`, `error`), ensure `return_schema` reflects the wrapper shape consistently

### Phase 4: Error Handling Improvement

#### Step 4.1: Review Current Error Handling
- [ ] Test error messages with invalid inputs
- [ ] Test HTTP error handling (404, 502, 503)
- [ ] Verify try/except blocks exist
- [ ] Errors return dict with "error" key

#### Step 4.2: Improve Error Messages
- [ ] Error messages are specific (not generic)
- [ ] Errors suggest actionable solutions
- [ ] Errors include context (status_code, endpoint)
- [ ] Errors are user-friendly
- [ ] If introducing a standardized error envelope, apply it consistently within that tool family

#### Step 4.3: Add Retry Logic (if needed)
- [ ] Identify transient failures (ConnectionError, Timeout)
- [ ] Implement retry with exponential backoff
- [ ] Set max retries (typically 2-3)
- [ ] Handle final failure appropriately
- [ ] Prefer using a shared retry helper if one exists in the codebase

### Phase 5: Finding Missing Tools

#### Step 5.1: Research API Capabilities
- [ ] **Read API Docs**: Check official documentation for all endpoints/operations
- [ ] **GraphQL Introspection**: Use schema introspection to find all queries
- [ ] **Test Endpoints**: Try different endpoint patterns
- [ ] **Check Related Packages**: Look at R/Bioconductor or Python packages
- [ ] **Web Search**: Search for "{API_NAME} API documentation"

#### Step 5.2: Create Gap Analysis Matrix
- [ ] List current tools from JSON config
- [ ] List all API capabilities
- [ ] Create comparison table (implemented vs available)
- [ ] Prioritize missing tools (HIGH/MEDIUM/LOW)
- [ ] Document findings

#### Step 5.3: Identify Subset Extraction Opportunities
- [ ] **Check Data Size**: If full response is large/complex
- [ ] **Identify Subsets**: Common fields users need (diseases, pathways, etc.)
- [ ] **Add Subset Tools**: Create tools that extract specific data types
- [ ] **Implement Method**: Create `_extract_subset()` helper if needed
- [ ] **Add field selection / projection** when supported upstream
- [ ] If projection fields are many: document the allowed values in `description` and enforce in code (avoid giant schema enums)

### Phase 6: Fix Common Issues

#### Issue 6.1: Tool Class Name Mismatch
- Check: Python class name matches `@register_tool("ClassName")`
- Check: JSON config `"type"` field matches class name exactly
- Fix: Ensure exact match (case-sensitive)

#### Issue 6.2: Response Format Mismatch
- Check: Test API response format directly (list vs dict)
- Fix: Check API response format and convert if needed

#### Issue 6.3: Endpoint URL Issues
- Check: Test endpoint directly, verify URL pattern in API documentation
- Fix: Verify URL building logic and placeholder replacement

#### Issue 6.4: Missing Error Handling
- Check: Test with invalid inputs and network failures
- Fix: Add try/except blocks with specific error handling

### Phase 7: Final Verification

#### Step 7.1: Comprehensive Testing
- [ ] Test all tools with valid inputs
- [ ] Test error cases with invalid inputs
- [ ] Test edge cases (empty results, null values)
- [ ] Verify results contain meaningful data
- [ ] Check performance is reasonable

#### Step 7.2: Validation Checks
- [ ] JSON files are valid
- [ ] Python syntax is valid
- [ ] No linting errors
- [ ] All tools load without errors
- [ ] Tool functions imported in `tools/__init__.py` (auto-generated, verify they exist)
- [ ] Category registered in `default_config.py`

```bash
python3 -m json.tool src/tooluniverse/data/{category}_tools.json
python3 -m py_compile src/tooluniverse/{category}_tool.py
```

#### Step 7.3: Documentation
- [ ] Tool descriptions are clear and complete
- [ ] Parameter descriptions include examples
- [ ] Return schemas match actual output
- [ ] Create example script in `examples/`
- [ ] Document findings and fixes

### Guidance for Large API Expansions

When covering many endpoints in one category:
- [ ] Use a generic REST tool + JSON configs to cover multiple endpoints
- [ ] Verify real API behavior with live requests (prefer working patterns over docs)
- [ ] Make `return_schema` match the tool's wrapper and validate upstream payload structure at a useful depth
- [ ] Use real IDs from search/list endpoints in `test_examples`
- [ ] Remove tools for endpoints that have no working or replacement API
- [ ] Design "research-first": include discovery tools (search/list), detail tools (get by ID), and version/release tools for reproducibility
- [ ] Keep schemas and parameter surfaces LLM-friendly: avoid enormous enums; keep descriptions explicit; enforce strict validation in code

---

## Quick Reference: Common Commands

### Validation
```bash
python3 -m json.tool src/tooluniverse/data/{category}_tools.json
python3 -m py_compile src/tooluniverse/{category}_tool.py
```

### Testing
```bash
python3 examples/{category}_tools_example.py
python scripts/test_new_tools.py {tool_name} -v
```

### Finding Tools
```bash
ls src/tooluniverse/tools/{category}_*.py
grep -c "\"name\":" src/tooluniverse/data/{category}_tools.json
grep "@register_tool" src/tooluniverse/{category}_tool.py
```
