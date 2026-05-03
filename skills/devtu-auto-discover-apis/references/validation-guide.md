# Validation & Integration Guide

## Phase 3: Validation

### Schema Validation
Check return_schema structure for each tool:
- Must have `oneOf` with 2 schemas (success + error)
- Success schema must have `data` field
- No placeholder values in test_examples

### Tool Loading Verification (3-Step)

```python
# Step 1: Class registered
from tooluniverse.tool_registry import get_tool_registry
registry = get_tool_registry()
assert "APINameTool" in registry

# Step 2: Config registered
from tooluniverse.default_config import TOOLS_CONFIGS
assert "api_category" in TOOLS_CONFIGS

# Step 3: Wrappers generated
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()
assert hasattr(tu.tools, 'APIName_operation1')
```

### Integration Tests
```bash
python scripts/test_new_tools.py [api_name] -v
# Expect: 100% pass rate
```

Handle failures:
- 404: Invalid test example ID → find real ID
- Schema mismatch: fix return_schema to match actual response
- Timeout: increase timeout or add retry
- Parameter error: verify with API docs

## Phase 4: Integration

### Git Workflow
```bash
git checkout -b feature/add-[api-name]-tools
git add src/tooluniverse/[api_name]_tool.py
git add src/tooluniverse/data/[api_name]_tools.json
git add src/tooluniverse/default_config.py
git commit -m "Add [API Name] tools for [domain]"
git push -u origin feature/add-[api-name]-tools
gh pr create --title "Add [API Name] tools" --body-file pr_description.md
```

## Quality Gates

| Gate | Review | Approve if |
|------|--------|-----------|
| Post-Discovery | discovery_report.md | Prioritization looks good |
| Post-Creation | .py and .json files | Implementation looks good |
| Post-Validation | validation_report.md | All tests passing |
| Pre-PR | PR description | Ready for merge |

## Troubleshooting

| Issue | Solution |
|-------|---------|
| API docs not found | Check /api/docs, /openapi.json, GitHub SDKs |
| Auth too complex | Document OAuth setup, use env vars for tokens |
| No real test examples | Use List endpoint, check API docs/GitHub |
| Tools won't load | Check default_config.py, JSON syntax, @register_tool |
| Schema mismatch | Call API directly, inspect raw response, fix schema |
| Rate limits | Add time.sleep(1), use API key, exponential backoff |

## Success Criteria

- All tools load into ToolUniverse
- 100% test pass rate
- No schema validation errors
- No placeholder values
- PR created with full documentation
