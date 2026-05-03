## Quick Start: [Domain] Analysis

[One paragraph overview of what this skill does and what outputs it provides.]

---

## Choose Your Implementation

### Python SDK

####Option 1: Complete Pipeline (Recommended)

Use the ready-made pipeline function for comprehensive analysis:

```python
from skills.tooluniverse_[domain].python_implementation import domain_analysis_pipeline

# Example 1: Basic usage
domain_analysis_pipeline(
    input_param_1="example_value",
    output_file="analysis.md"
)

# Example 2: Multiple inputs
domain_analysis_pipeline(
    input_param_1="value1",
    input_param_2="value2",
    input_param_3="value3",
    organism="Homo sapiens",
    output_file="comprehensive_analysis.md"
)
```

#### Option 2: Individual Tools

Use specific tools for targeted queries:

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# 1. Tool from Database 1
result = tu.tools.TOOL_NAME_1(
    parameter1="value1",
    parameter2="value2"
)

# 2. Tool from Database 2
result = tu.tools.TOOL_NAME_2(
    parameter="value"
)

# 3. SOAP tool (if applicable) - note operation parameter
result = tu.tools.SOAP_TOOL_NAME(
    operation="method_name",  # CRITICAL for SOAP tools
    parameter="value"
)
```

---

### MCP (Model Context Protocol)

#### Option 1: Conversational (Natural Language)

Ask Claude to perform analysis directly:

```
"Analyze [domain] for [input_description]"

"Find [data_type] related to [query]"

"[Domain-specific request phrase]"

"Perform comprehensive [domain] analysis for [input] in [organism]"
```

#### Option 2: Direct Tool Calls

Use specific tools via JSON (for programmatic MCP usage):

**1. Tool from Database 1**:
```json
{
  "tool": "TOOL_NAME_1",
  "parameters": {
    "parameter1": "value1",
    "parameter2": "value2"
  }
}
```

**2. Tool from Database 2**:
```json
{
  "tool": "TOOL_NAME_2",
  "parameters": {
    "parameter": "value"
  }
}
```

**3. SOAP Tool** (if applicable):
```json
{
  "tool": "SOAP_TOOL_NAME",
  "parameters": {
    "operation": "method_name",
    "parameter": "value"
  }
}
```

---

## Tool Parameters (All Implementations)

**Note**: Whether using Python SDK or MCP, the parameter names are the same.

### TOOL_NAME_1
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `parameter1` | string | Yes | [Description] |
| `parameter2` | integer | No | [Description] |
| `parameter3` | boolean | No | [Description] (default: false) |

### TOOL_NAME_2
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `parameter` | string | Yes | [Description] |
| `limit` | integer | No | Max results (default: 10) |

### SOAP_TOOL_NAME (if applicable)
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `operation` | string | Yes | ⚠️ **CRITICAL**: SOAP method name (e.g., "search") |
| `parameter` | string | Yes | [Description] |

**CRITICAL**: SOAP tools MUST include `operation` parameter or they will fail.

---

## Common Recipes

### Recipe 1: [Use Case Name]

**Scenario**: [Description of when to use this]

**Python SDK**:
```python
domain_analysis_pipeline(
    input_param_1="specific_value",
    output_file="recipe1_output.md"
)
```

**MCP**:
```
"[Conversational request matching this use case]"
```

### Recipe 2: [Use Case Name]

**Scenario**: [Description]

**Python SDK**:
```python
# More complex example with multiple parameters
domain_analysis_pipeline(
    input_param_1="value1",
    input_param_2="value2",
    organism="Mus musculus",  # Mouse
    output_file="recipe2_output.md"
)
```

**MCP**:
```
"[Conversational request for this scenario]"
```

### Recipe 3: [Multi-Database Comparison]

**Scenario**: Compare results across multiple databases

**Python SDK**:
```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

query = "example_query"

# Query all databases
result1 = tu.tools.DATABASE1_TOOL(param=query)
result2 = tu.tools.DATABASE2_TOOL(param=query)
result3 = tu.tools.DATABASE3_TOOL(param=query)

# Compare coverage
print(f"Database 1: {len(result1.get('data', []))} results")
print(f"Database 2: {len(result2.get('data', []))} results")
print(f"Database 3: {len(result3.get('data', []))} results")
```

**MCP**:
```
"Search for [query] across [Database 1], [Database 2], and [Database 3].
Compare the coverage across databases."
```

---

## CRITICAL: SOAP Tool Parameters (if applicable)

**Only for skills using SOAP tools like IMGT, SAbDab, TheraSAbDab**

### Python SDK Example
```python
# CORRECT - includes operation parameter
result = tu.tools.SOAP_TOOL_NAME(
    operation="method_name",  # Required!
    parameter="value"
)

# WRONG - missing operation
result = tu.tools.SOAP_TOOL_NAME(
    parameter="value"  # Will fail!
)
```

### MCP Example
```json
{
  "operation": "method_name",
  "parameter": "value"
}
```

**Error if missing**: "Parameter validation failed: 'operation' is a required property"

---

## Expected Output

### Report Structure

The skill generates a markdown report with these sections:

1. **Header**: Analysis parameters and metadata
2. **Phase 1: [Name]** (if input_param_1 provided)
   - Table of results from Database 1
   - Fallback results from Database 2 if needed
3. **Phase 2: [Name]** (if input_param_2 provided)
   - Results from Database 3
4. **Phase 3: [Name]** (if input_param_3 provided)
   - Results from Databases 4 and 5
5. **Phase 4: [Summary/Context]** (always included)
   - Contextual information

### Example Output Snippet

```markdown
# [Domain] Analysis Report

**Generated**: 2026-02-09 14:30:00
**Input 1**: example_value
**Organism**: Homo sapiens

---

## 1. [Phase 1 Name]

### Database 1 Results (15 entries)

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| ...      | ...      | ...      |

## 2. [Phase 2 Name]

### Database 3 Results (8 entries)

...
```

---

## Troubleshooting

### Issue: Empty results from all databases
**Solution**: Check that input values are valid. Try alternative input formats or synonyms.

### Issue: Tool returns "operation is a required property" error
**Solution**: You're using a SOAP tool. Add `operation="method_name"` parameter.

### Issue: Different result counts across databases
**Expected**: Different databases have different coverage. Cross-reference to validate findings.

### Issue: Timeout or API errors
**Solution**: Check internet connection. If persistent, database may be down - check fallback options.

### Issue: "Tool not found" error
**Solution**: Ensure ToolUniverse is properly loaded: `tu = ToolUniverse(); tu.load_tools()`

---

## Next Steps

After running this skill:

1. **Follow-up Analysis**: Use IDs from report to get detailed information
2. **Visualization**: [Suggestions for visualizing results]
3. **Validation**: Cross-reference key findings across databases
4. **Export**: Convert tables to CSV/Excel for further analysis
5. **Literature Search**: Use [domain] names/IDs for literature searches

---

## Additional Resources

- **Database 1**: [URL]
- **Database 2**: [URL]
- **Database 3**: [URL]
- **[Domain] Documentation**: [URL]
- **ToolUniverse Docs**: https://github.com/mims-harvard/ToolUniverse

---

## Performance Notes

- **Typical runtime**: 30-60 seconds for basic queries
- **Complex queries**: 2-5 minutes with multiple inputs
- **Large datasets**: May take longer, progress shown during execution

**Optimization tips**:
- Start with single input to test
- Use specific rather than broad queries
- Consider organism-specific searches
