# Skill Documentation Structure - General vs Implementation-Specific

**Date**: 2026-02-09
**Key Principle**: SKILL.md should be general; implementation details go in separate files

---

## The Problem

Skills were written with implementation-specific code (Python SDK) embedded in SKILL.md, making them less flexible for users who access ToolUniverse through different interfaces (MCP, Python SDK, future APIs).

## The Solution

**Separate general concepts from implementation:**

1. **SKILL.md** - General, implementation-agnostic
2. **Implementation files** - Python SDK, MCP, etc.

---

## File Structure

```
skills/[skill-name]/
├── SKILL.md                          # ✅ GENERAL - No implementation code
├── QUICK_START.md                    # ✅ Multi-implementation examples
├── python_implementation.py          # ✅ Python SDK implementation
├── mcp_examples.md                   # ✅ MCP examples (optional)
├── test_[skill].py                   # Python SDK test
└── [example]_report.md               # Example output
```

---

## SKILL.md Format (General)

### ✅ What to Include

**Conceptual information:**
- Workflow overview
- Which tools to use
- What parameters are needed
- What results to expect
- Decision logic
- Analysis steps

**Example - General format:**
```markdown
## Workflow

### Phase 1: Drug Identification

**Objective**: Resolve drug names to standardized identifiers

**Tools needed**:
- RxNorm drug name lookup
- DrugBank drug information

**Parameters required**:
- Drug name (string)
- Case sensitivity option (boolean)
- Exact match option (boolean)

**Expected results**:
- RxNorm concept ID
- DrugBank ID
- Generic/brand name pairs

**Decision logic**:
- If drug not found in RxNorm → try DrugBank
- If drug not found in DrugBank → mark as "novel compound"
- Continue analysis with available information

### Phase 2: Interaction Analysis

**Objective**: Identify known drug-drug interactions

**Tools needed**:
- DrugBank interactions lookup
- DailyMed FDA labels

**Parameters required**:
- Drug identifier (from Phase 1)
- Interaction severity threshold

**Expected results**:
- List of interacting drugs
- Severity levels
- Mechanism descriptions

**Decision logic**:
- Query both sources in parallel
- Merge results
- Grade by severity (CRITICAL > HIGH > MODERATE > MINOR)
```

### ❌ What NOT to Include

**Implementation-specific code:**
- `from tooluniverse import ToolUniverse` ❌
- `tu.tools.RxNorm_get_drug_names(...)` ❌
- `result = mcp.call_tool(...)` ❌
- Specific error handling code ❌
- Language-specific constructs ❌

---

## Implementation Files

### Python SDK Implementation

**File**: `python_implementation.py` or `[skill]_pipeline.py`

```python
#!/usr/bin/env python3
"""
Drug-Drug Interaction Analysis - Python SDK Implementation

This file shows how to implement the DDI skill workflow
using the ToolUniverse Python SDK.
"""

from tooluniverse import ToolUniverse

class DDIAnalyzer:
    """Python SDK implementation of DDI skill."""

    def __init__(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def analyze(self, drug_a, drug_b):
        """Implement Phase 1: Drug Identification (from SKILL.md)"""

        # Call tools using Python SDK
        result = self.tu.tools.RxNorm_get_drug_names(
            drug_name=drug_a
        )

        # ... implementation ...
```

### MCP Examples

**File**: `mcp_examples.md` or include in `QUICK_START.md`

```markdown
## MCP Implementation

### Phase 1: Drug Identification

Using MCP server with Claude Desktop or compatible client:

**Tool**: `RxNorm_get_drug_names`
**Parameters**:
\`\`\`json
{
  "drug_name": "warfarin"
}
\`\`\`

**Tool**: `drugbank_get_drug_basic_info_by_drug_name_or_id`
**Parameters**:
\`\`\`json
{
  "query": "warfarin",
  "case_sensitive": false,
  "exact_match": false,
  "limit": 1
}
\`\`\`
```

---

## QUICK_START.md Format (Multi-Implementation)

**File**: `QUICK_START.md`

```markdown
# [Skill Name] - Quick Start Guide

This guide shows how to use the [Skill Name] with different implementations.

---

## Option 1: Python SDK

\`\`\`python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Phase 1: Drug Identification (see SKILL.md)
result = tu.tools.RxNorm_get_drug_names(
    drug_name="warfarin"
)
\`\`\`

Or use the complete pipeline:

\`\`\`python
from ddi_pipeline import DDIAnalyzer

analyzer = DDIAnalyzer()
report = analyzer.analyze("warfarin", "aspirin")
\`\`\`

---

## Option 2: MCP (Claude Desktop)

Tell Claude:

> "Use ToolUniverse to analyze drug-drug interactions between warfarin and aspirin"

Claude will use the MCP server to access tools:
1. RxNorm_get_drug_names for identification
2. drugbank_get_drug_interactions for interaction data
3. FAERS_count_reactions for adverse events

---

## Option 3: MCP (Direct Tool Calls)

**Tool**: RxNorm_get_drug_names
\`\`\`json
{"drug_name": "warfarin"}
\`\`\`

**Tool**: drugbank_get_drug_basic_info_by_drug_name_or_id
\`\`\`json
{
  "query": "warfarin",
  "case_sensitive": false,
  "exact_match": false,
  "limit": 1
}
\`\`\`

---

## Tool Parameters Reference

| Tool | Parameter | Type | Required | Notes |
|------|-----------|------|----------|-------|
| RxNorm_get_drug_names | drug_name | string | ✅ | Not 'query' |
| drugbank_* | query | string | ✅ | All DrugBank tools |
| FAERS_count_reactions | medicinalproduct | string | ✅ | Not 'drug_name' |

This table applies to ALL implementations (Python, MCP, etc.)
```

---

## Comparison: General vs Implementation-Specific

### ✅ GENERAL (SKILL.md)

```markdown
## Phase 1: Drug Identification

**Objective**: Resolve drug names to standardized identifiers

**Tools**:
1. RxNorm drug name lookup
   - Input: drug name
   - Output: RxNorm concept ID, standard name

2. DrugBank drug information
   - Input: drug name or ID
   - Output: DrugBank ID, approval status, description

**Workflow**:
1. Query RxNorm with drug name
2. If found → extract concept ID and standard name
3. If not found → query DrugBank
4. If neither found → mark as "novel compound"
5. Continue with available identifiers

**Decision Points**:
- Case sensitivity: Use case-insensitive search for flexibility
- Exact match: Use fuzzy matching to handle typos
- Multiple results: Take first result, note ambiguity
```

### ❌ IMPLEMENTATION-SPECIFIC (Don't put in SKILL.md)

```python
# Don't put this in SKILL.md - put in python_implementation.py
def identify_drug(self, drug_name):
    """Phase 1 implementation."""
    try:
        result = self.tu.tools.RxNorm_get_drug_names(
            drug_name=drug_name
        )
        if result.get('status') == 'success':
            return result['data']
    except Exception as e:
        print(f"Error: {e}")
```

---

## Tool Specification Format (General)

### ✅ CORRECT - Implementation-Agnostic

```markdown
## Tools Used

### RxNorm_get_drug_names

**Purpose**: Resolve drug names to RxNorm concepts

**Inputs**:
- `drug_name` (string, required): Drug name to search

**Outputs**:
- Concept ID (rxcui)
- Standard drug name
- Name type (brand/generic)

**Notes**:
- Case-insensitive search
- Returns multiple matches if ambiguous
- May not find very new drugs

**Fallback**: If RxNorm fails, use DrugBank_get_drug_basic_info

---

### drugbank_get_drug_basic_info_by_drug_name_or_id

**Purpose**: Get comprehensive drug information

**Inputs**:
- `query` (string, required): Drug name or DrugBank ID
- `case_sensitive` (boolean, optional): Default false
- `exact_match` (boolean, optional): Default false
- `limit` (integer, optional): Max results, default 10

**Outputs**:
- DrugBank ID
- Drug name (generic and brand)
- Description
- Approval status
- Drug groups

**Notes**:
- Parameter is `query`, NOT `drug_name_or_id` (common mistake)
- All DrugBank tools use `query` parameter
- May return empty for novel compounds

**SOAP Tool**: No
```

### ❌ WRONG - Implementation-Specific

```markdown
## Tools Used

### RxNorm_get_drug_names

\`\`\`python
result = tu.tools.RxNorm_get_drug_names(
    drug_name="warfarin"
)
\`\`\`

Returns:
\`\`\`python
{
    'status': 'success',
    'data': {...}
}
\`\`\`
```

---

## Updated Skill Development Workflow

### Phase 1: Design (General)

**Create**: `SKILL.md`

**Content**:
- Workflow overview (conceptual)
- Tool specifications (what they do, inputs/outputs)
- Decision logic (when to use what)
- Expected results (what data to expect)
- Fallback strategies (conceptual)

**Format**: Implementation-agnostic descriptions

---

### Phase 2: Test & Implement

**Create**: `test_[skill].py` (Python SDK)

```python
"""Test script to verify tool behavior."""
from tooluniverse import ToolUniverse

def test_tools():
    tu = ToolUniverse()
    tu.load_tools()

    # Test each tool mentioned in SKILL.md
    result = tu.tools.RxNorm_get_drug_names(drug_name="warfarin")
    print(result)

    result = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
        query="warfarin",
        case_sensitive=False
    )
    print(result)
```

---

### Phase 3: Create Implementation Files

**Create**: `python_implementation.py` (or `[skill]_pipeline.py`)

```python
"""Python SDK implementation of the skill workflow."""
from tooluniverse import ToolUniverse

class SkillAnalyzer:
    """Implements the workflow from SKILL.md using Python SDK."""

    def __init__(self):
        self.tu = ToolUniverse()
        self.tu.load_tools()

    def analyze(self, inputs):
        """Follow the workflow from SKILL.md."""
        # Phase 1 from SKILL.md
        result1 = self._phase1(inputs)

        # Phase 2 from SKILL.md
        result2 = self._phase2(result1)

        return result2
```

**Create**: `mcp_examples.md` (optional)

```markdown
# MCP Examples

## Using with Claude Desktop

Tell Claude:
> "Use [skill name] to analyze [inputs]"

## Direct Tool Calls

**Step 1**: Call RxNorm_get_drug_names
\`\`\`json
{"drug_name": "warfarin"}
\`\`\`

**Step 2**: Call drugbank_get_drug_basic_info
\`\`\`json
{
  "query": "warfarin",
  "case_sensitive": false
}
\`\`\`
```

---

### Phase 4: Create Quick Start (Multi-Implementation)

**Create**: `QUICK_START.md`

```markdown
# [Skill Name] - Quick Start

Choose your implementation:

## Python SDK
[Python examples with imports and code]

## MCP
[MCP examples with tool calls]

## Tool Parameters (All Implementations)
[Parameter reference table]
```

---

## Benefits of This Structure

### For Users

✅ **Flexibility**: Choose Python SDK, MCP, or future APIs
✅ **Clarity**: Conceptual workflow separate from implementation
✅ **Learning**: Understand WHAT to do before HOW to do it

### For Skill Developers

✅ **Maintainability**: Update one workflow, multiple implementations
✅ **Testability**: Test each implementation independently
✅ **Reusability**: Same workflow across different interfaces

### For Documentation

✅ **Longevity**: General docs don't break when APIs change
✅ **Completeness**: All implementations documented
✅ **Accessibility**: Users pick their preferred method

---

## Migration Guide: Updating Existing Skills

### Step 1: Extract General Content from SKILL.md

**Move to general format:**
- ❌ Remove: `from tooluniverse import ToolUniverse`
- ❌ Remove: `tu.tools.TOOL_NAME(...)`
- ❌ Remove: Python-specific error handling
- ✅ Keep: Tool names and purposes
- ✅ Keep: Parameter descriptions
- ✅ Keep: Workflow logic
- ✅ Keep: Decision points

### Step 2: Create Python Implementation File

**Create**: `python_implementation.py`

```python
"""Python SDK implementation of [Skill] from SKILL.md"""

# Move all Python code here
from tooluniverse import ToolUniverse

class SkillAnalyzer:
    # Implementation code
    pass
```

### Step 3: Update QUICK_START.md

**Add sections**:
- Python SDK examples
- MCP examples (if applicable)
- Tool parameter reference (general)

### Step 4: Update SKILL.md

**Rewrite sections to be general**:
```markdown
## Workflow

### Phase 1: [Name]

**Objective**: [What this phase achieves]

**Tools**: [Which tools to use]

**Inputs**: [What parameters needed]

**Outputs**: [What to expect]

**Logic**: [Decision points and flow]
```

---

## Template: General SKILL.md

```markdown
---
name: skill-name
description: General description of what the skill does and when to use it
---

# [Skill Name]

General overview of the skill's purpose and capabilities.

## When to Use

- Trigger 1
- Trigger 2
- Trigger 3

## Workflow Overview

High-level description of the analysis workflow.

```
Phase 1: [Name] → Phase 2: [Name] → Phase 3: [Name]
```

## Required Tools

| Tool Name | Purpose | Critical? |
|-----------|---------|-----------|
| Tool_1 | What it does | Yes/No |
| Tool_2 | What it does | Yes/No |

## Detailed Workflow

### Phase 1: [Name]

**Objective**: What this phase achieves

**Tools needed**:
1. Tool_A
   - Purpose: What it does
   - Input: What parameters
   - Output: What results

2. Tool_B (fallback)
   - Purpose: Alternative if Tool_A fails
   - Input: What parameters
   - Output: What results

**Workflow Steps**:
1. Query Tool_A with [inputs]
2. Extract [specific data]
3. If no results → try Tool_B
4. If neither works → use default/continue
5. Pass results to Phase 2

**Decision Points**:
- When to use exact match vs fuzzy
- How to handle multiple results
- When to trigger fallback

**Expected Results**:
- Primary data: [description]
- Metadata: [description]
- Confidence level: High/Medium/Low

### Phase 2: [Name]

[Same structure as Phase 1]

## Tool Specifications

### Tool_Name

**Purpose**: One-line description

**Inputs**:
- `parameter_name` (type, required/optional): Description
- `parameter_name2` (type, required/optional): Description

**Outputs**:
- Field_1: Description
- Field_2: Description

**Notes**:
- Important usage notes
- Common mistakes
- Special requirements (e.g., SOAP tools need 'operation')

**Fallback**: What to use if this tool fails

---

### Tool_Name2

[Same structure]

## Implementation Notes

**For Python SDK**: See `python_implementation.py`
**For MCP**: See `mcp_examples.md` or `QUICK_START.md`

**Common Issues**:
- Issue 1 and how to handle
- Issue 2 and how to handle

**Testing**: See `test_[skill].py` for verification

---

## Output Structure

Description of what the skill produces (general format, not code).

**Report Sections**:
1. Section 1: What it contains
2. Section 2: What it contains
3. Section 3: What it contains

**File Outputs**:
- `report.md`: Main findings
- `data.json`: Structured data (optional)
```

---

## Summary

### Key Principles

1. ✅ **SKILL.md is general** - No implementation code
2. ✅ **Implementation files are separate** - Python, MCP, etc.
3. ✅ **QUICK_START has all implementations** - One-stop reference
4. ✅ **Tool specs are descriptive** - What they do, not how to call

### File Roles

| File | Content | Implementation-Specific? |
|------|---------|-------------------------|
| SKILL.md | Conceptual workflow | ❌ No |
| python_implementation.py | Python SDK code | ✅ Yes - Python |
| mcp_examples.md | MCP examples | ✅ Yes - MCP |
| QUICK_START.md | Multi-implementation examples | ⚠️ Both |
| test_*.py | Verification code | ✅ Yes - Python |

### Benefits

✅ **Flexibility** - Users choose their interface
✅ **Maintainability** - One workflow, many implementations
✅ **Longevity** - General docs survive API changes
✅ **Clarity** - Separate concepts from code

---

**Updated**: 2026-02-09
**Status**: New structure for all future skills
