# ToolUniverse Skill Development Guide

**Version**: 2.0 (Updated 2026-02-09)
**Based on**: Real-world experience fixing 4 non-functional skills
**Key Insight**: Documentation ≠ Working Code

---

## Executive Summary

This guide documents **critical lessons learned** from fixing 4 ToolUniverse skills that were 0-20% functional despite having excellent documentation (1,500+ lines each).

**Root cause**: Skills were created without testing actual ToolUniverse tool calls. All documentation showed usage that looked correct but failed when executed.

**Solution**: Test-driven development with working pipelines.

---

## The Golden Rule

### ✅ **ALWAYS TEST WITH REAL API CALLS**

**Before writing any documentation:**
1. Load ToolUniverse
2. Call every tool you plan to use
3. Verify parameters work
4. Check results are correct
5. Document what actually worked

**Not what you think should work. What actually works.**

---

## Quick Reference: Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| **SOAP tools** | "operation is required" error | Add `operation="method_name"` as first parameter |
| **Wrong parameters** | Empty results, no error | Test with `get_tool_info()`, verify actual schema |
| **API down** | Tool fails completely | Implement fallback hierarchy |
| **Empty data** | Pipeline crashes | Use `.get()`, check for None/empty |
| **No examples** | Users can't replicate | Create working pipeline with `QUICK_START.md` |

---

## Critical Principle: Implementation-Agnostic Documentation

### SKILL.md Must Be General

**IMPORTANT**: SKILL.md should NOT contain implementation-specific code (Python SDK, MCP, etc.)

Users access ToolUniverse through different interfaces:
- Python SDK (`from tooluniverse import ToolUniverse`)
- MCP (Model Context Protocol via Claude Desktop)
- Future APIs

**SKILL.md should describe**:
- ✅ WHAT to do (conceptual workflow)
- ✅ WHICH tools to use (tool names and purposes)
- ✅ WHAT parameters are needed (parameter descriptions)
- ✅ WHAT results to expect (expected outputs)
- ✅ Decision logic (when to do what)

**SKILL.md should NOT contain**:
- ❌ `from tooluniverse import ToolUniverse`
- ❌ `tu.tools.TOOL_NAME(...)`
- ❌ `result = mcp.call_tool(...)`
- ❌ Language-specific error handling code
- ❌ Implementation details

**Put implementation code in**:
- `python_implementation.py` - Python SDK implementation
- `mcp_examples.md` - MCP examples
- `QUICK_START.md` - Multi-implementation examples

See `SKILL_DOCUMENTATION_STRUCTURE.md` for complete guide.

---

## Skill Development Workflow

### Phase 1: Research & Testing (FIRST!)

```python
# Step 1: Create test script FIRST
# File: test_[skill_name].py

from tooluniverse import ToolUniverse

def test_tools():
    """Test ALL tools before writing any documentation."""
    tu = ToolUniverse()
    tu.load_tools()

    # Test Tool 1
    print("\n=== Testing Tool 1 ===")
    result = tu.tools.TOOL_NAME(
        param1="value1",  # Try different parameter names
        param2="value2"
    )
    print(f"Result: {result}")
    print(f"Status: {result.get('status')}")
    print(f"Data: {result.get('data')}")

    # Test Tool 2
    print("\n=== Testing Tool 2 ===")
    result = tu.tools.TOOL_NAME2(
        param_a="value_a",
        param_b="value_b"
    )
    print(f"Result: {result}")

    # Test Tool 3 (SOAP tool)
    print("\n=== Testing SOAP Tool ===")
    try:
        # Try without 'operation'
        result = tu.tools.SOAP_TOOL(param="value")
        print("❌ No error - may not be SOAP")
    except Exception as e:
        if "operation" in str(e):
            print("✅ SOAP tool - needs 'operation' parameter")

            # Try with 'operation'
            result = tu.tools.SOAP_TOOL(
                operation="method_name",
                param="value"
            )
            print(f"Result: {result}")

if __name__ == "__main__":
    test_tools()
```

**Run this test BEFORE writing ANY documentation.**

### Phase 2: Design General Workflow

**Create**: `SKILL.md` (implementation-agnostic)

```markdown
---
name: skill-name
description: What the skill does (general)
---

# [Skill Name]

## Workflow Overview

High-level flow: Phase 1 → Phase 2 → Phase 3

## Phase 1: [Name]

**Objective**: What this phase achieves

**Tools needed**:
- Tool_A: Purpose and what it does
- Tool_B: Purpose and what it does (fallback)

**Parameters required**:
- `parameter_name` (type): Description
- `parameter_name2` (type): Description

**Expected results**:
- Data field 1: Description
- Data field 2: Description

**Decision logic**:
- When to use Tool_A vs Tool_B
- How to handle empty results
- When to continue vs stop

## Phase 2: [Name]

[Same structure]

## Tool Specifications

### Tool_Name

**Purpose**: What it does

**Inputs**:
- `param1` (string, required): Description
- `param2` (boolean, optional): Description

**Outputs**:
- field1: Description
- field2: Description

**Notes**:
- Important usage notes
- SOAP tool requirements (if applicable)
- Common mistakes

**Fallback**: Alternative tool if this fails
```

**Key**: No implementation code - describe WHAT to do, not HOW to code it

---

### Phase 3: Create Python Implementation

**Create**: `python_implementation.py` (or `[skill]_pipeline.py`)

```python
# File: python_implementation.py
# Implements the workflow from SKILL.md using Python SDK

from tooluniverse import ToolUniverse
from datetime import datetime


class [SkillName]Analyzer:
    """Working pipeline for [skill] analysis."""

    def __init__(self):
        print("Initializing ToolUniverse...")
        self.tu = ToolUniverse()
        self.tu.load_tools()
        print(f"✅ Loaded {len(self.tu.all_tool_dict)} tools\n")

    def analyze(self, inputs, output_file=None):
        """Complete analysis pipeline."""
        if output_file is None:
            output_file = f"{self.__class__.__name__}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        print("=" * 80)
        print(f"{self.__class__.__name__.upper()} ANALYSIS")
        print("=" * 80)

        # CRITICAL: Create report file FIRST
        self._create_report(output_file, inputs)

        report = {'timestamp': datetime.now().isoformat()}

        # Run analysis steps
        print("\n🔬 Running Analysis...")

        # Step 1
        result1 = self._step1(inputs)
        self._update_report(output_file, "## 1. Step Name", result1)
        report['step1'] = result1

        # Step 2
        result2 = self._step2(inputs)
        self._update_report(output_file, "## 2. Step Name", result2)
        report['step2'] = result2

        print(f"\n✅ Analysis complete! Report: {output_file}")
        return report

    def _create_report(self, filename, inputs):
        """Create initial report file."""
        with open(filename, 'w') as f:
            f.write(f"# {self.__class__.__name__} Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Input**: {inputs}\n\n")
            f.write("---\n\n")

    def _update_report(self, filename, section, data):
        """Update report progressively."""
        with open(filename, 'a') as f:
            f.write(f"\n{section}\n\n")
            if isinstance(data, dict):
                for key, value in data.items():
                    f.write(f"**{key}**: {value}\n\n")
            elif isinstance(data, list):
                for item in data:
                    f.write(f"- {item}\n")
                f.write("\n")
            else:
                f.write(f"{data}\n\n")

    def _step1(self, inputs):
        """First analysis step."""
        print("\n1️⃣ Step Name")
        results = {}

        try:
            # ✅ Use VERIFIED parameters from test script
            result = self.tu.tools.TOOL_NAME(
                param1="value1",  # ✅ Tested and working
                param2="value2"
            )

            # ✅ Defensive programming - handle empty data
            if result.get('status') == 'success' and result.get('data'):
                data = result['data']
                results['field1'] = data.get('field1', 'N/A')
                results['field2'] = data.get('field2', 'N/A')
                print(f"   ✅ Retrieved data")
            else:
                print(f"   ℹ️ No data found")
                results['note'] = 'Data not available'

        except Exception as e:
            print(f"   ⚠️ Error: {e}")
            results['error'] = str(e)

        return results

    def _step2(self, inputs):
        """Second analysis step with fallback."""
        print("\n2️⃣ Step Name")
        results = {}

        # PRIMARY: Try main tool
        try:
            result = self.tu.tools.PRIMARY_TOOL(param="value")
            if result.get('status') == 'success' and result.get('data'):
                results = result['data']
                results['source'] = 'primary'
                print(f"   ✅ Primary source")
                return results
        except Exception as e:
            print(f"   ⚠️ Primary failed: {e}")

        # FALLBACK: Try alternative
        try:
            result = self.tu.tools.FALLBACK_TOOL(param="value")
            if result.get('status') == 'success' and result.get('data'):
                results = result['data']
                results['source'] = 'fallback'
                print(f"   ✅ Fallback source")
                return results
        except Exception as e:
            print(f"   ⚠️ Fallback failed: {e}")

        # DEFAULT: Continue with limited info
        results = {
            'status': 'unavailable',
            'note': 'Both primary and fallback failed',
            'source': 'none'
        }
        print(f"   ℹ️ Using default values")
        return results


def main():
    """Test the pipeline."""
    print("=" * 80)
    print("PIPELINE TEST")
    print("=" * 80)

    analyzer = [SkillName]Analyzer()

    # Example 1
    print("\nExample 1:")
    report = analyzer.analyze(inputs="test_input_1")

    # Example 2
    print("\nExample 2:")
    report = analyzer.analyze(inputs="test_input_2")

    print("\n✅ All examples completed successfully")


if __name__ == "__main__":
    main()
```

**Run pipeline with 2-3 examples to ensure it works.**

### Phase 4: Document Multi-Implementation Usage

**Create**: `QUICK_START.md` (supports both Python SDK and MCP)

```markdown
# [Skill Name] - Quick Start Guide

**Status**: ✅ **WORKING** - Tested with Python SDK and MCP
**Last Updated**: [DATE]

---

## Choose Your Implementation

### Option 1: Python SDK

**Using the complete pipeline:**
\`\`\`python
from python_implementation import [SkillName]Analyzer

analyzer = [SkillName]Analyzer()
report = analyzer.analyze(inputs="your_input")
\`\`\`

**Using individual tools:**
\`\`\`python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Phase 1 from SKILL.md
result = tu.tools.TOOL_NAME(
    param1="value1",  # ✅ Verified working
    param2="value2"   # ✅ Verified working
)
\`\`\`

### Option 2: MCP (Claude Desktop)

**Using the skill conversationally:**

Tell Claude:
> "Use [skill name] to analyze [your inputs]"

Claude will follow the workflow from SKILL.md using MCP tools.

**Direct tool calls:**

**Step 1**: Tool_Name
\`\`\`json
{
  "param1": "value1",
  "param2": "value2"
}
\`\`\`

**Step 2**: Tool_Name2
\`\`\`json
{
  "param_a": "value_a"
}
\`\`\`

### Option 3: MCP (Other Clients)

See `mcp_examples.md` for client-specific examples

---

## Correct Tool Parameters (VERIFIED)

| Tool | Parameter | Correct Name | Verified Date |
|------|-----------|--------------|---------------|
| TOOL_NAME | Param 1 | \`param1\` | 2026-02-09 |
| TOOL_NAME | Param 2 | \`param2\` | 2026-02-09 |

**IMPORTANT**: These parameters were tested and verified working. If they stop working, the API may have changed.

---

## Known Limitations

⚠️ **SOAP Tools**: Tools with names like `IMGT_*`, `SAbDab_*`, `TheraSAbDab_*` require `operation="method_name"` parameter

⚠️ **Data Availability**: Some tools may return empty results for:
- New/novel compounds not yet in databases
- Rare targets with limited literature
- During API maintenance

⚠️ **API Dependencies**: Requires internet connection and working APIs

---

*Tested: [DATE] - All tool calls verified in ToolUniverse instance*
```

### Phase 4: Validate in Fresh Environment

```bash
# Open NEW terminal (fresh environment)
cd /path/to/skill

# Test the QUICK_START examples
python -c "
from [skill]_pipeline import [SkillName]Analyzer
analyzer = [SkillName]Analyzer()
report = analyzer.analyze(inputs='test')
print('✅ Example works')
"

# Test the pipeline
python [skill]_pipeline.py

# If any errors → FIX THEM before releasing
```

---

## Critical Issues & Solutions

### Issue 1: SOAP Tools Require 'operation' Parameter

**Affected tools**: All `IMGT_*`, `SAbDab_*`, `TheraSAbDab_*` tools

**Symptoms**:
```
Error: "Parameter validation failed for 'root': 'operation' is a required property"
```

**Solution**:
```python
# ❌ WRONG
tu.tools.IMGT_search_genes(
    gene_type="IGHV",
    species="Homo sapiens"
)

# ✅ CORRECT
tu.tools.IMGT_search_genes(
    operation="search_genes",  # Add this!
    gene_type="IGHV",
    species="Homo sapiens"
)
```

**How to identify SOAP tools**:
1. Error message mentions "operation is a required property"
2. Tool name contains IMGT/SAbDab/TheraSAbDab
3. Tool configuration has `soap: true`

### Issue 2: Parameter Names Don't Match Function Names

**Problem**: Tool function names don't predict parameter names

**Examples**:
```python
# ❌ WRONG: Guessed from function name
tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
    drug_name_or_drugbank_id="warfarin"  # Doesn't exist!
)

# ✅ CORRECT: Verified actual parameter
tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
    query="warfarin",  # Actual parameter
    case_sensitive=False,
    exact_match=False,
    limit=10
)
```

**Solution**: Always verify parameters via:
1. `tu.tools.get_tool_info("tool_name")`
2. Inspect tool JSON config
3. Test with trial and error

### Issue 3: External APIs Fail

**Problem**: Primary API down → skill fails completely

**Solution**: Implement fallback hierarchy

```python
def get_data_with_fallback(primary_func, fallback_func, default):
    """Try primary, fallback to alternative, return default if both fail."""

    # Try primary
    try:
        result = primary_func()
        if result and result.get('status') == 'success':
            return (result['data'], 'primary', '★★★')
    except Exception as e:
        print(f"Primary failed: {e}")

    # Try fallback
    try:
        result = fallback_func()
        if result and result.get('status') == 'success':
            return (result['data'], 'fallback', '★★☆')
    except Exception as e:
        print(f"Fallback failed: {e}")

    # Return default
    return (default, 'default', '☆☆☆')
```

**Fallback strategy table**:
```markdown
| Primary | Fallback 1 | Fallback 2 | Default |
|---------|------------|------------|---------|
| DepMap_search_genes | Pharos_get_target | MyGene_info | Continue with unvalidated |
| DrugBank_get_drug | PubChem_get_compound | FDA_search | Note "novel compound" |
| GTEx_expression | HPA_expression | None | Note "no data available" |
```

### Issue 4: Crashes on Empty Data

**Problem**: Tools return empty results → code crashes

**Common scenarios**:
- New drugs not in DrugBank
- Novel targets with no literature
- Exact name matching required
- API rate limits

**Solution**: Defensive programming

```python
# ❌ WRONG: Crashes if empty
drugs = result['data']['drugs']
name = drugs[0]['name']

# ✅ CORRECT: Handles all cases
drugs = result.get('data', {}).get('drugs', [])
if drugs and len(drugs) > 0:
    name = drugs[0].get('name', 'Unknown')
else:
    name = 'Not found (may be novel compound)'
    # Continue pipeline anyway
```

**Pattern**: Always use `.get()` with defaults

```python
# Safe access pattern
value = (result
         .get('data', {})
         .get('field1', {})
         .get('field2', 'DEFAULT'))
```

---

## Skill Release Checklist

Before marking a skill as "ready":

### Testing ✅
- [ ] All tool calls tested in ToolUniverse instance
- [ ] Test script (`test_[skill].py`) passes
- [ ] Pipeline (`[skill]_pipeline.py`) runs without errors
- [ ] 2-3 complete examples tested
- [ ] Error cases handled (empty data, API failures)
- [ ] SOAP tools have 'operation' parameter (if applicable)
- [ ] Fallback strategies implemented

### Documentation ✅
- [ ] `QUICK_START.md` with tested examples
- [ ] Tool parameter verification table
- [ ] Known limitations documented
- [ ] Example reports generated
- [ ] Working pipeline script included

### Code Quality ✅
- [ ] Defensive programming (handle None, [], {})
- [ ] Report-first architecture
- [ ] Progress indicators
- [ ] Informative error messages
- [ ] No debug output in final reports

### User Testing ✅
- [ ] Fresh terminal test passes
- [ ] Examples from QUICK_START work without modification
- [ ] Reports are readable (not debug logs)
- [ ] Completes in reasonable time (<5 min)

---

## File Structure

```
skills/[skill-name]/
├── SKILL.md                        # ✅ REQUIRED: General workflow (NO implementation code)
├── python_implementation.py        # ✅ REQUIRED: Python SDK implementation
├── QUICK_START.md                  # ✅ REQUIRED: Multi-implementation examples
├── test_[skill].py                 # ✅ REQUIRED: Test script (Python)
├── mcp_examples.md                 # Optional: MCP-specific examples
├── EXAMPLES.md                     # Optional: Use cases
├── README.md                       # Optional: Overview
└── [example]_report.md             # ✅ REQUIRED: Example output
```

**File Roles**:
- **SKILL.md**: General workflow, tool descriptions (implementation-agnostic)
- **python_implementation.py**: Python SDK code (`from tooluniverse import ToolUniverse`)
- **QUICK_START.md**: Examples for both Python SDK and MCP
- **test_[skill].py**: Verification script
- **mcp_examples.md**: MCP-specific usage (optional)

**Minimum required files**: SKILL.md (general), python_implementation.py, QUICK_START.md (multi-impl), test script, example report

---

## Common Anti-Patterns

### ❌ Anti-Pattern 1: Documentation-Only Skills

**Problem**: 1,500 lines of documentation, zero working code

**Fix**: Create working pipeline FIRST, then document

### ❌ Anti-Pattern 2: Untested Tool Calls

**Problem**: Documentation shows tool usage that looks correct but was never tested

**Fix**: Test EVERY tool call before documenting

### ❌ Anti-Pattern 3: No Error Handling

**Problem**: Pipeline crashes when tools return empty data

**Fix**: Use defensive programming, `.get()` with defaults

### ❌ Anti-Pattern 4: No Fallbacks

**Problem**: Skill fails completely when primary API is down

**Fix**: Implement fallback hierarchy for critical tools

### ❌ Anti-Pattern 5: SOAP Tools Without 'operation'

**Problem**: IMGT/SAbDab/TheraSAbDab tools fail with parameter error

**Fix**: Add `operation="method_name"` as first parameter

### ❌ Anti-Pattern 6: Wrong Parameter Names

**Problem**: Guessed parameter names based on function name

**Fix**: Verify actual parameters via testing or `get_tool_info()`

### ❌ Anti-Pattern 7: No Examples

**Problem**: Users can't replicate skill usage

**Fix**: Include working pipeline and QUICK_START with tested examples

---

## Success Metrics

A **working skill** has:

1. ✅ **>80% functionality** - Most features work as expected
2. ✅ **Tested examples** - All QUICK_START examples run successfully
3. ✅ **Error resilience** - Handles empty data and API failures gracefully
4. ✅ **Clear documentation** - Users can replicate without guessing
5. ✅ **Working pipeline** - End-to-end script that completes successfully

---

## Resources

### Files in This Repository

- **`SKILL_FIXES_COMPLETE.md`** - Detailed fixes for 4 broken skills
- **`READY_TO_USE.md`** - User guide for fixed skills
- **`skills/devtu-optimize-skills/SKILL_CREATION_BEST_PRACTICES.md`** - Detailed best practices
- **`skills/devtu-optimize-skills/SKILL.md`** - Updated with critical lessons

### Example Working Pipelines

- `skills/tooluniverse-drug-drug-interaction/ddi_pipeline.py` ✅
- `skills/tooluniverse-clinical-trial-design/trial_pipeline.py` ✅
- `skills/tooluniverse-antibody-engineering/antibody_pipeline.py` ✅
- `skills/tooluniverse-crispr-screen-analysis/test_crispr_fallback_v2.py` ✅

### Test Reports

- `TEST_REPORT_DDI.md` - DDI skill testing
- `TEST_REPORT_TRIAL.md` - Clinical trial skill testing
- `TEST_REPORT_ANTIBODY.md` - Antibody skill testing
- `TEST_REPORT_CRISPR.md` - CRISPR skill testing

---

## Summary

**The #1 lesson**: Test with real API calls BEFORE writing documentation.

**The 7 critical rules**:
1. ✅ Test with real API calls
2. ✅ SOAP tools need 'operation'
3. ✅ Verify parameter schemas
4. ✅ Create working pipelines
5. ✅ Implement fallback strategies
6. ✅ Handle empty data gracefully
7. ✅ Test-driven documentation

Follow these rules and your skills will work the first time.

---

**Version**: 2.0
**Updated**: 2026-02-09
**Based on**: Real fixes of 4 skills (CRISPR, DDI, Clinical Trial, Antibody)
**Average improvement**: +64% functionality
