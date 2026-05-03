# Tool Generation Guide

## Overview

The `build_tools.py` script automatically detects changes in tool configurations and only regenerates modified tools, avoiding unnecessary regeneration. This document explains how to ensure all changes are properly detected.

## Change Detection Mechanism

### How It Works

1. **Hash Calculation**: The system calculates an MD5 hash for each tool configuration
   - Excludes timestamp fields (`timestamp`, `last_updated`, `created_at`)
   - Recursively normalizes nested structures (dictionaries, lists, etc.)
   - Uses sorted JSON serialization to ensure consistency

2. **Metadata Storage**: Hash values are stored in `src/tooluniverse/tools/.tool_metadata.json`
   - On first run, all tools are marked as "new tools"
   - Subsequent runs compare old and new hash values

3. **Change Identification**: 
   - **New Tools**: Exist in configuration files but not in metadata
   - **Changed Tools**: Hash values have changed
   - **Unchanged Tools**: Hash values are identical

### Detection Scope

The system detects changes in the following configuration fields:
- `name` - Tool name
- `description` - Tool description
- `parameter` - Parameter definitions (including added/removed/modified parameters)
- `return_schema` - Return type definition
- `type` - Tool type
- All other configuration fields (except timestamps)

## Usage

### Basic Usage

```bash
# Normal build (only generate changed tools)
python scripts/build_tools.py
```

### Force Regenerate All Tools

If you suspect there's an issue with change detection, you can force regeneration of all tools:

```bash
# Using command line argument
python scripts/build_tools.py --force

# Or using environment variable
TOOLUNIVERSE_FORCE_REGENERATE=1 python scripts/build_tools.py
```

### Verbose Output Mode

View detailed change information:

```bash
# Show detailed information for each changed tool
python scripts/build_tools.py --verbose

# Or combine with force
python scripts/build_tools.py --force --verbose
```

### Skip Formatting

If you only want to generate code without formatting:

```bash
python scripts/build_tools.py --no-format
```

## Validation Features

After generating code, the system automatically validates:

1. ✅ Whether function names match tool names
2. ✅ Whether all required parameters appear in function signatures
3. ✅ Whether all parameters in configuration appear in generated code

If issues are found, warning messages will be displayed in the output.

## Common Questions

### Q: Modified tool configuration but not detected?

**A:** Try the following steps:

1. **Check if configuration actually changed**:
   ```bash
   # Use verbose mode to view
   python scripts/build_tools.py --verbose
   ```

2. **Force regeneration**:
   ```bash
   python scripts/build_tools.py --force
   ```

3. **Check metadata file**: 
   View `src/tooluniverse/tools/.tool_metadata.json` to confirm hash values are updated

4. **Manually delete metadata file**: 
   Deleting `.tool_metadata.json` will force re-detection of all tools

### Q: How to ensure old tools are properly deleted?

**A:** The system automatically cleans up orphaned files:
- If a tool is removed from configuration, the corresponding `.py` file will be automatically deleted
- Cleanup information is displayed in output: `🧹 Removed X orphaned tool files`

### Q: How to ensure parameter changes are detected?

**A:** Hash calculation detects the following parameter-related changes:
- Added parameters
- Removed parameters
- Modified parameter types
- Modified parameter descriptions
- Modified parameter default values
- Modified required/optional status

### Q: Performance Optimization

**A:** The system is already optimized:
- Only regenerates changed tools
- Uses hash values instead of full configuration comparison
- Supports parallel processing (if configured)

## Environment Variables

| Variable Name | Description | Default Value |
|---------------|-------------|---------------|
| `TOOLUNIVERSE_FORCE_REGENERATE` | Force regenerate all tools | `0` (don't force) |
| `TOOLUNIVERSE_VERBOSE` | Show detailed change information | `0` (don't show) |
| `TOOLUNIVERSE_SKIP_FORMAT` | Skip code formatting | `0` (format) |

## Best Practices

1. **Regular Force Rebuild**: Use `--force` after important updates to ensure consistency
   ```bash
   python scripts/build_tools.py --force
   ```

2. **Use Version Control**: Include `.tool_metadata.json` in version control to track changes

3. **Verify Generation Results**: Use `--verbose` to view detailed output and ensure all tools are processed correctly

4. **Cleanup Testing**: Run build after modifying tool configurations to confirm orphaned files are properly cleaned up

## Troubleshooting Steps

If you encounter problems, troubleshoot in the following order:

1. ✅ Check if configuration file format is correct (valid JSON)
2. ✅ Use `--verbose` to view detailed output
3. ✅ Use `--force` to force regeneration
4. ✅ Check if `.tool_metadata.json` file is corrupted
5. ✅ Delete `.tool_metadata.json` to start fresh
6. ✅ Check generated code validation error messages

## Technical Details

### Hash Calculation Algorithm

```python
# Pseudocode
def calculate_hash(tool_config):
    # 1. Exclude timestamp fields
    normalized = {k: v for k, v in config.items() 
                  if k not in excluded_fields}
    
    # 2. Recursively normalize nested structures
    normalized = normalize_recursive(normalized)
    
    # 3. Serialize to JSON with sorted keys
    json_str = json.dumps(normalized, sort_keys=True)
    
    # 4. Calculate MD5 hash
    return md5(json_str)
```

### Change Detection Flow

```
Load tool configurations
    ↓
Calculate hash for each tool
    ↓
Load old metadata (.tool_metadata.json)
    ↓
Compare old and new hash values
    ↓
Categorize: new tools / changed / unchanged
    ↓
Only generate new tools and changed tools
    ↓
Update metadata file
```

---

**Tip**: If you encounter any issues during use, you can use the `--force --verbose` options to get more diagnostic information.

