# Tool Parameter Verification Guide

From devtu-optimize-skills -- CRITICAL for avoiding common mistakes.

## Common Parameter Mistakes to Avoid

| Pattern | Don't Assume | Always Verify |
|---------|--------------|---------------|
| Function name includes param name | `drugbank_get_drug_by_name(name=...)` | Test reveals uses `query` |
| Descriptive function name | `map_uniprot_to_pathways(uniprot_id=...)` | Test reveals uses `id` |
| Consistent naming | All similar functions use same param | Each tool may differ |

## SOAP Tools Detection

**Indicators**:
- Error: "Parameter validation failed: 'operation' is a required property"
- Tool name includes: IMGT, SAbDab, TheraSAbDab
- Tool config shows `operation` in schema

**Fix**: Add `operation` parameter as first argument with method name.

## Response Format Variations

**Standard**: `{status: "success", data: [...]}`
**Direct list**: Returns `[...]` without wrapper
**Direct dict**: Returns `{field1: ..., field2: ...}` without status

**Solution**: Handle all three in implementation with `isinstance()` checks.
