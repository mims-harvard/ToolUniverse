# Skill Updates: Implementation-Agnostic Format

**Date**: 2026-02-09
**Status**: ✅ COMPLETE

---

## Overview

Updated **Antibody Engineering** and **CRISPR Screen Analysis** skills to follow implementation-agnostic format, supporting both Python SDK and MCP (Model Context Protocol) implementations.

---

## Files Updated/Created

### Antibody Engineering Skill
Location: `/Users/shgao/logs/25.05.28tooluniverse/codes/ToolUniverse-auto/skills/tooluniverse-antibody-engineering/`

1. **python_implementation.py** (NEW)
   - Copy of `antibody_pipeline.py` for consistency
   - Maintains backward compatibility
   - Size: 14KB

2. **QUICK_START.md** (UPDATED)
   - Added "Choose Your Implementation" section
   - Separated Python SDK and MCP sections
   - Added MCP direct tool call examples
   - Emphasized SOAP tool `operation` parameter requirement
   - Size: 10KB

### CRISPR Screen Analysis Skill
Location: `/Users/shgao/logs/25.05.28tooluniverse/codes/ToolUniverse-auto/skills/tooluniverse-crispr-screen-analysis/`

1. **QUICK_START.md** (NEW)
   - Complete implementation-agnostic guide
   - Python SDK and MCP examples
   - Documented Pharos fallback strategy (due to DepMap unavailability)
   - Evidence grading system for MCP users
   - Size: 11KB

---

## Key Changes

### 1. Structure Standardization

Both skills now follow consistent structure:

```markdown
# [Skill Name] - Quick Start Guide

## Choose Your Implementation

### Python SDK
  #### Option 1: Use the Working Pipeline (RECOMMENDED)
  #### Option 2: Use Individual Tools

### MCP (Model Context Protocol)
  #### Option 1: Conversational
  #### Option 2: Direct Tool Calls

## Tool Parameters (All Implementations)
  [Table showing parameters apply to both Python SDK and MCP]

## [Other sections...]
```

### 2. Python SDK Examples

**Antibody Engineering:**
```python
from python_implementation import AntibodyHumanizer
# or: from antibody_pipeline import AntibodyHumanizer

analyzer = AntibodyHumanizer()
report = analyzer.analyze(vh_sequence, vl_sequence, target_antigen)
```

**CRISPR Screen Analysis:**
```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Gene validation (Pharos fallback)
result = tu.tools.Pharos_get_target(gene="KRAS")
```

### 3. MCP Examples

**Option 1: Conversational**
- Tell Claude what you want
- Claude follows workflow from SKILL.md
- Examples provided for each skill

**Option 2: Direct Tool Calls**
- JSON format examples
- Step-by-step tool sequences
- Clear parameter specifications

### 4. SOAP Tool Documentation (Antibody Engineering)

**CRITICAL**: All SOAP tools (IMGT, SAbDab, TheraSAbDab) require `operation` parameter

**Python SDK:**
```python
result = tu.tools.IMGT_search_genes(
    operation="search_genes",  # ✅ Required!
    gene_type="IGHV",
    species="Homo sapiens"
)
```

**MCP:**
```json
{
  "operation": "search_genes",
  "gene_type": "IGHV",
  "species": "Homo sapiens"
}
```

### 5. Fallback Strategy Documentation (CRISPR Screen Analysis)

**DepMap Unavailability:**
- Primary: DepMap CRISPR dependency scores (unavailable)
- Fallback: Pharos TDL classification

**TDL as Proxy for Essentiality:**
- Tclin → ★★★ (high confidence)
- Tchem → ★★☆ (medium confidence)
- Tbio/Tdark → ★☆☆ (low confidence)

All findings labeled with data source

---

## Tool Parameter Tables

Both skills include comprehensive parameter tables noting:
> **Note**: Whether using Python SDK or MCP, the parameter names are the same

### Antibody Engineering Key Parameters

| Tool | Parameter | Correct Name | Notes |
|------|-----------|--------------|-------|
| IMGT_search_genes | SOAP operation | `operation="search_genes"` | **CRITICAL** |
| TheraSAbDab_search_by_target | SOAP operation | `operation="search_by_target"` | **CRITICAL** |
| SAbDab_search_structures | SOAP operation | `operation="search_structures"` | **CRITICAL** |
| iedb_search_epitopes | Epitope name | `epitope_name` | NOT SOAP |

### CRISPR Screen Analysis Key Parameters

| Tool | Parameter | Correct Name | Notes |
|------|-----------|--------------|-------|
| Pharos_get_target | Gene symbol | `gene` | Fallback for DepMap |
| enrichr_analyze_gene_list | Gene list | `gene_list` | List of gene symbols |
| STRING_get_interactions | Gene list | `identifiers` | Comma-separated |
| search_clinical_trials | Intervention | `intervention` | Drug/target name |

---

## MCP Direct Tool Call Examples

### Antibody Engineering

**Step 1: Clinical Precedent Search**
```json
Tool: TheraSAbDab_search_by_target
Parameters:
{
  "operation": "search_by_target",
  "target": "PD-L1"
}
```

**Step 2: Germline Gene Search**
```json
Tool: IMGT_search_genes
Parameters:
{
  "operation": "search_genes",
  "gene_type": "IGHV",
  "species": "Homo sapiens"
}
```

**Step 3: Structural Precedent Search**
```json
Tool: SAbDab_search_structures
Parameters:
{
  "operation": "search_structures",
  "query": "PD-L1"
}
```

### CRISPR Screen Analysis

**Step 1: Gene Validation**
```json
Tool: Pharos_get_target
Parameters:
{
  "gene": "KRAS"
}
```

**Step 2: Pathway Enrichment**
```json
Tool: enrichr_analyze_gene_list
Parameters:
{
  "gene_list": ["KRAS", "EGFR", "BRAF"],
  "library": "KEGG_2021_Human"
}
```

**Step 3: PPI Network**
```json
Tool: STRING_get_interactions
Parameters:
{
  "identifiers": "KRAS,EGFR,BRAF",
  "species": 9606
}
```

---

## Conversational Prompts for MCP Users

### Antibody Engineering
```
"Analyze humanization feasibility for an anti-PD-L1 antibody using ToolUniverse.
VH: EVQLVESGGGLVQPGGSLRLSCAAS..., VL: DIQMTQSPSSLSASVGDRVTITCRAS..."
```

Claude will automatically:
1. Search TheraSAbDab for clinical precedents
2. Query IMGT for germline genes
3. Search SAbDab for structural precedents
4. Assess immunogenicity via IEDB
5. Generate comprehensive report

### CRISPR Screen Analysis
```
"I have CRISPR dropout screen hits from A549 lung cancer cells.
Please analyze these genes: KRAS, EGFR, WEE1, PLK1, AURKA, CDK2..."
```

Claude will automatically:
1. Validate genes via Pharos (fallback)
2. Assess druggability via TDL
3. Run pathway enrichment
4. Build PPI network
5. Search clinical trials
6. Generate comprehensive report

---

## Backward Compatibility

### Antibody Engineering
- ✅ `antibody_pipeline.py` still works
- ✅ `python_implementation.py` is identical copy
- ✅ Users can import from either file
- ✅ All existing code continues to work

### CRISPR Screen Analysis
- ✅ No existing pipeline to break
- ✅ SKILL.md workflow unchanged
- ✅ New QUICK_START.md adds clarity
- ✅ Pharos fallback transparently integrated

---

## Documentation Standards Applied

### 1. Clear Implementation Choice
- Top-level "Choose Your Implementation" section
- Separate Python SDK and MCP sections
- Equal emphasis on both approaches

### 2. Parameter Consistency
- Explicit note: "parameter names are the same for Python SDK and MCP"
- Tables show parameters apply to both
- Examples in both Python and JSON

### 3. SOAP Tool Warnings (Antibody Engineering)
- CRITICAL warnings for `operation` parameter
- Side-by-side Python and JSON examples
- Error message documentation

### 4. Fallback Strategy Documentation (CRISPR Screen Analysis)
- Clear explanation of DepMap unavailability
- Pharos fallback documented
- TDL classification as essentiality proxy
- Evidence grading adjusted for fallback

### 5. Use Case Examples
- Conversational prompts for MCP
- Step-by-step tool sequences
- Expected outputs
- Clinical scenarios

---

## Testing Recommendations

### For Python SDK Users
1. **Antibody Engineering:**
   ```bash
   cd skills/tooluniverse-antibody-engineering
   python python_implementation.py
   # Should generate: Antibody_Humanization_PD-L1.md
   ```

2. **CRISPR Screen Analysis:**
   ```python
   from tooluniverse import ToolUniverse
   tu = ToolUniverse()
   tu.load_tools()
   result = tu.tools.Pharos_get_target(gene="KRAS")
   assert result['status'] == 'success'
   ```

### For MCP Users
1. **Antibody Engineering:**
   - Try conversational prompt with anti-PD-L1 example
   - Verify SOAP tools work with `operation` parameter
   - Check report generation

2. **CRISPR Screen Analysis:**
   - Try gene list analysis prompt
   - Verify Pharos fallback works
   - Check TDL classification appears in output

---

## Key Features of Updated Documentation

### Antibody Engineering
- ✅ Dual implementation support (Python SDK + MCP)
- ✅ SOAP tool parameter warnings prominent
- ✅ MCP JSON examples for all key tools
- ✅ Alternative target name strategies
- ✅ Backward compatibility maintained

### CRISPR Screen Analysis
- ✅ Dual implementation support (Python SDK + MCP)
- ✅ Pharos fallback documented comprehensively
- ✅ Evidence grading system for MCP users
- ✅ 7-path analysis workflow preserved
- ✅ TDL-based essentiality proxy explained

---

## Impact

### For Python SDK Users
- No breaking changes
- Additional import option (`python_implementation.py`)
- Clearer documentation of individual tools
- Better understanding of SOAP tool requirements

### For MCP Users
- **NEW**: Clear guidance on using skills via Claude
- **NEW**: Direct tool call examples in JSON
- **NEW**: Conversational prompts to get started
- **NEW**: Parameter tables showing JSON structure

### For Skill Maintainers
- Consistent documentation structure
- Easier to add new skills following this pattern
- Clear separation of concerns (Python vs MCP)
- Better user onboarding

---

## Files Summary

```
skills/tooluniverse-antibody-engineering/
├── antibody_pipeline.py        (original, unchanged)
├── python_implementation.py    (NEW - copy of above)
└── QUICK_START.md             (UPDATED - implementation-agnostic)

skills/tooluniverse-crispr-screen-analysis/
└── QUICK_START.md             (NEW - implementation-agnostic)
```

---

## Next Steps (Recommendations)

1. **Apply pattern to other skills:**
   - Drug-Drug Interaction (already done)
   - Clinical Trial Design
   - Structural Variant Analysis
   - Drug Repurposing

2. **Enhance MCP examples:**
   - Add error handling examples
   - Show multi-step workflows
   - Document common pitfalls

3. **Create MCP-specific guide:**
   - Common MCP patterns across all skills
   - SOAP tool handling in MCP
   - Async tool handling in MCP

4. **Video tutorials:**
   - Python SDK walkthrough
   - MCP/Claude Desktop walkthrough
   - Side-by-side comparison

---

## Validation Checklist

- [x] Antibody Engineering: python_implementation.py created
- [x] Antibody Engineering: QUICK_START.md updated with MCP section
- [x] Antibody Engineering: SOAP tool `operation` parameter documented
- [x] Antibody Engineering: MCP JSON examples provided
- [x] CRISPR Screen Analysis: QUICK_START.md created
- [x] CRISPR Screen Analysis: Pharos fallback documented
- [x] CRISPR Screen Analysis: MCP JSON examples provided
- [x] Both skills: "Choose Your Implementation" section
- [x] Both skills: Tool parameter tables note apply to both
- [x] Both skills: Conversational prompts provided
- [x] Both skills: Backward compatibility maintained
- [x] Documentation: Consistent structure across both skills

---

*Completed: 2026-02-09*
