# Test All Tools - Automated Tool Testing Script

## Overview

`test_all_tools.py` automatically discovers all tool configurations and tests them using the enhanced `test_new_tools.py` script. It generates a comprehensive markdown report with results, statistics, and actionable recommendations.

## Features

✅ **Automatic Discovery**: Scans `src/tooluniverse/data/` for all JSON config files

✅ **Pattern-Based Testing**: Groups tools by prefix (e.g., `fda`, `ncbi`, `cbioportal`)

✅ **Comprehensive Reporting**: Generates detailed markdown report with statistics

✅ **404 Detection**: Specifically tracks 404 errors (API endpoint issues)

✅ **Schema Validation**: Reports schema mismatches

✅ **Actionable Insights**: Provides next steps for fixing issues

## Quick Start

### Test All Tools

```bash
# Test ALL tool categories
python scripts/test_all_tools.py

# With verbose output
python scripts/test_all_tools.py -v

# Stop at first failure
python scripts/test_all_tools.py --fail-fast
```

### Test Specific Patterns

```bash
# Test only cBioPortal tools
python scripts/test_all_tools.py --pattern cbioportal

# Test FDA tools
python scripts/test_all_tools.py --pattern fda

# Test NCBI tools
python scripts/test_all_tools.py --pattern ncbi
```

### Custom Output

```bash
# Save report to custom file
python scripts/test_all_tools.py --output MY_REPORT.md
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Show detailed output for each test |
| `--fail-fast` | Stop testing after first failure |
| `--parallel` | Run tests in parallel (experimental) |
| `--output FILE` | Save report to specific file (default: `TOOL_TEST_REPORT.md`) |
| `--pattern PATTERN` | Test only patterns matching substring |

## Output

### Console Output

```
======================================================================
ToolUniverse - Comprehensive Tool Testing
======================================================================

🔍 Scanning for tool configurations...
✅ Found 166 configuration files
📊 Analyzing tool patterns...
✅ Found 45 unique tool patterns

🧪 Running tests...

[1/45] Testing cbioportal... ✅ 12 tests passed
[2/45] Testing fda... ✅ 8 tests passed
[3/45] Testing ncbi... ⚠️  2 schema issues
...

======================================================================
Generating report...
✅ Report saved to: TOOL_TEST_REPORT.md

======================================================================
SUMMARY
======================================================================
Patterns Tested:  45
Total Tests:      523
Passed:           515
Failed:           8
Duration:         45.23s
======================================================================
```

### Generated Report

The script generates a comprehensive markdown report (`TOOL_TEST_REPORT.md`) with:

#### 1. Executive Summary
- Total categories tested
- Pass rate
- Overall statistics

#### 2. Results by Tool Category
- Individual statistics per pattern
- Pass/fail status
- Schema validation results
- Duration

#### 3. Issues Requiring Attention
- **404 Errors**: APIs with endpoint issues
- **Schema Mismatches**: Tools needing schema updates
- **Other Failures**: Tools with execution errors

#### 4. Next Steps
- Actionable recommendations
- Links to documentation
- Debugging suggestions

### Example Report Section

```markdown
### ✅ cbioportal

**Config Files**: cbioportal_tools.json

| Metric | Value |
|--------|-------|
| Tools | 6 |
| Tests | 12 |
| Passed | 12 (100.0%) |
| Failed | 0 |
| Schema Valid | 12 |
| Schema Invalid | 0 |
| Duration | 0.88s |
```

## How It Works

### 1. Discovery Phase

```python
# Scans for JSON files
find_all_tool_configs(data_dir)
→ Finds: cbioportal_tools.json, fda_tools.json, ncbi_tools.json, etc.
```

### 2. Pattern Extraction

```python
# Groups by prefix
extract_tool_patterns(config_files)
→ Groups: 
   'cbioportal': [cbioportal_tools.json]
   'fda': [fda_tools.json]
   'ncbi': [ncbi_tools.json, ncbi_protein_tools.json]
```

### 3. Testing

For each pattern:
```bash
# Runs existing test script
python scripts/test_new_tools.py {pattern}
```

### 4. Aggregation

- Parses output from each test run
- Aggregates statistics
- Identifies issues

### 5. Report Generation

- Creates markdown report
- Categorizes issues
- Provides recommendations

## Integration with Existing Tools

This script **complements** the existing testing infrastructure:

| Script | Purpose | Use Case |
|--------|---------|----------|
| `test_new_tools.py` | Test specific tools/patterns | Development, debugging |
| `test_all_tools.py` | Test all tools, generate report | CI/CD, validation, audits |

### Workflow

```
Developer fixes a tool
↓
python scripts/test_new_tools.py cbioportal  # Quick test
↓
python scripts/test_all_tools.py --pattern cbioportal  # Full validation
↓
python scripts/test_all_tools.py  # Comprehensive audit (optional)
```

## Use Cases

### 1. Continuous Integration

```yaml
# .github/workflows/test-tools.yml
- name: Test all tools
  run: python scripts/test_all_tools.py --fail-fast
  
- name: Upload report
  uses: actions/upload-artifact@v2
  with:
    name: tool-test-report
    path: TOOL_TEST_REPORT.md
```

### 2. Pre-Release Validation

```bash
# Before releasing
python scripts/test_all_tools.py
cat TOOL_TEST_REPORT.md  # Review
```

### 3. API Monitoring

```bash
# Weekly cron job to detect API changes
python scripts/test_all_tools.py --output weekly_report_$(date +%Y%m%d).md
```

### 4. Debugging Specific Tools

```bash
# When cBioPortal has issues
python scripts/test_all_tools.py --pattern cbioportal -v
```

## Statistics Tracked

For each tool category:

- ✅ **Passed**: Successfully executed tests
- ❌ **Failed**: Total failures
  - 🔍 **404 Errors**: API endpoint not found
  - ⚠️  **Other Errors**: Other execution errors
- ✓ **Schema Valid**: Data matches schema
- ✗ **Schema Invalid**: Schema mismatches
- ⏱️  **Duration**: Execution time

## Troubleshooting

### No Tests Found

```bash
❌ No patterns found matching 'xyz'
```

**Solution**: Check pattern name with:
```bash
ls src/tooluniverse/data/*xyz*.json
```

### Timeout Errors

```bash
ERROR: Timeout after 5 minutes
```

**Solution**: Some APIs are slow. This is expected for large test suites.

### Permission Errors

```bash
ERROR: Permission denied
```

**Solution**: Make script executable:
```bash
chmod +x scripts/test_all_tools.py
```

## Best Practices

### 1. Regular Testing

Run weekly to detect API changes early:
```bash
crontab -e
# Add: 0 9 * * 1 cd /path/to/repo && python scripts/test_all_tools.py
```

### 2. Focused Testing

Test specific areas during development:
```bash
python scripts/test_all_tools.py --pattern cbioportal -v
```

### 3. Review Reports

Always review generated reports:
```bash
python scripts/test_all_tools.py
less TOOL_TEST_REPORT.md
```

### 4. Version Control Reports

Track reports over time:
```bash
git add TOOL_TEST_REPORT.md
git commit -m "Tool validation report $(date +%Y-%m-%d)"
```

## Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed

Perfect for CI/CD:
```bash
python scripts/test_all_tools.py || exit 1
```

## Performance

- **Single pattern**: ~1-3 seconds
- **All patterns**: Depends on total tools (typically 1-2 minutes)
- **Parallel mode**: Experimental, faster but less stable

## Example Reports

### All Passing

```markdown
## Issues Requiring Attention

✨ **No issues found!** All tools are working correctly.

## Next Steps

✅ All tools validated successfully! No action needed.
```

### With Issues

```markdown
## Issues Requiring Attention

### 🔍 404 Errors Detected

- **old_api**: 3 404 error(s)

### ⚠️  Schema Validation Issues

- **legacy_tools**: 5 schema mismatch(es)

## Next Steps

1. **Fix 404 Errors**: Review API documentation
2. **Fix Schema Mismatches**: Update return_schema definitions
```

## Related Scripts

- `scripts/test_new_tools.py` - Core testing script (augmented with 404 detection)
- `scripts/analyze_all_tool_configs.py` - Configuration analysis
- `scripts/build_tools.py` - Tool building utilities

## Contributing

When adding new tools:

1. Add JSON configuration to `src/tooluniverse/data/`
2. Run `python scripts/test_all_tools.py --pattern your_tool`
3. Verify all tests pass
4. Commit with report

## License

Same as ToolUniverse project.
