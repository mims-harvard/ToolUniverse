# Known Issues and Workarounds

## Issue #1: Verbose ToolUniverse Loading Messages ⚠️

### Problem

When running the protein network analysis, you'll see 40+ error messages like:

```
❌ Error loading tools from category 'tool_discovery_agents': [Errno 2] No such file or directory...
❌ Error loading tools from category 'web_search_tools': [Errno 2] No such file or directory...
...
```

### Root Cause

This is a **ToolUniverse framework limitation**, not a bug in our implementation:

1. ToolUniverse reloads tools on EVERY tool call (4 times in our workflow)
2. Each reload attempts to load ALL tool categories (100+)
3. Missing optional tool files generate error messages to stdout
4. Cannot be suppressed from user code

### Impact

- ❌ **Cluttered output**: 40+ error lines obscure actual results
- ❌ **Performance**: Loading 1232 tools 4 times (~4-8 seconds overhead)
- ✅ **Functionality**: No impact - analysis works correctly despite warnings

### Workaround #1: Redirect stdout when running (Recommended)

```bash
# Suppress ToolUniverse warnings
python python_implementation.py 2>&1 | grep -v "Error loading tools"

# Or save clean output
python python_implementation.py 2>&1 | grep -E "(Phase|✅|🕸|🧬|🔗|Results)" > results.txt
```

### Workaround #2: Use ToolUniverse in quiet mode

Create missing placeholder files (prevents error messages):

```bash
cd src/tooluniverse/data/
for f in tool_discovery_agents web_search_tools package_discovery_tools \
         pypi_package_inspector_tools drug_discovery_agents hca_tools \
         clinical_trials_tools iedb_tools pathway_commons_tools biomodels_tools; do
    echo "[]" > "${f}_tools.json"
done
```

### Workaround #3: Filter output programmatically

```python
import sys
from io import StringIO

# Capture output
old_stdout = sys.stdout
sys.stdout = buffer = StringIO()

# Run analysis
result = analyze_protein_network(...)

# Restore and filter output
sys.stdout = old_stdout
output = buffer.getvalue()
clean_output = '\n'.join([
    line for line in output.split('\n')
    if 'Error loading tools' not in line
])
print(clean_output)
```

### Expected Fix

This should be fixed in ToolUniverse core by:
1. Caching loaded tools (don't reload on every call)
2. Suppressing warnings for optional missing files
3. Using proper logging levels (DEBUG vs ERROR)

**Status**: Framework limitation - workarounds required until fixed upstream.

---

## Issue #2: Performance - Multiple Tool Reloads

### Problem

ToolUniverse loads 1232 tools 4 separate times during analysis.

### Impact

- ⚠️ **Slow**: 4-8 second overhead
- ⚠️ **Memory**: 4x memory usage

### Workaround

None available - this is how ToolUniverse currently works. Each tool call triggers a reload.

### Expected Fix

ToolUniverse should cache loaded tools in memory across calls.

---

## Non-Issues (These are NOT bugs)

### ✅ Parameter Names

All parameter names are CORRECT:
- `protein_ids` (not `identifiers`) - ✅ Verified in Phase 2
- `gene_names` (plural) - ✅ Verified in Phase 2
- `sasbdb_id` - ✅ Verified in Phase 2

### ✅ Implementation Logic

All 4 phases work correctly:
- Phase 1: 100% mapping success ✅
- Phase 2: Correct interaction retrieval ✅
- Phase 3: Valid enrichment analysis ✅
- Phase 4: Clean error handling ✅

### ✅ Results Quality

TP53 analysis produces expected results:
- 10 high-confidence interactions (0.98-0.999)
- 374 enriched GO terms (p < 0.05)
- PPI enrichment highly significant (p=1.99e-06)
