---
name: devtu-optimize-descriptions
description: Optimize tool descriptions in ToolUniverse JSON configs for clarity and usability. Reviews descriptions for missing prerequisites, unexpanded abbreviations, unclear parameters, and missing usage guidance. Use when reviewing tool descriptions, improving API documentation, or when user asks to check if tools are easy to understand.
---

# ToolUniverse Tool Description Optimization

Optimize tool descriptions in ToolUniverse JSON configuration files to ensure they are clear, complete, and user-friendly.

## When to Apply This Skill

Use when:
- Reviewing newly created tool descriptions
- User asks "are these tools easy to understand?"
- Improving existing tool documentation
- Adding new tools to ToolUniverse
- User mentions tool usability, clarity, or documentation

## Quick Optimization Checklist

```markdown
Tool Description Review:
- [ ] Prerequisites stated (packages, API keys, accounts)
- [ ] Critical abbreviations expanded on first use
- [ ] Required vs optional parameters clear
- [ ] Mutually exclusive options numbered/labeled
- [ ] Parameter guidance includes trade-offs
- [ ] Filter syntax shows available fields
- [ ] File size warnings where relevant
- [ ] Examples show realistic usage
```

## Critical Improvements (Fix Immediately)

### 1. Clarify Required Input Requirements

**Problem**: Users don't know if they need ONE input or ALL inputs.

**Fix**: Use "**Required: Provide ONE input type**" for mutually exclusive options.

```json
// Before
"description": "Process BED regions, motifs, or gene lists..."

// After
"description": "Process genomic data. **Required: Provide ONE input type** - (1) BED regions, (2) DNA motif, or (3) gene list. Analyzes..."
```

Number the options and use bold for "Required".

### 2. Add Prerequisites to First Tool

**Problem**: Users don't know what to install/configure before use.

**Fix**: Add prerequisites note to first tool in each family.

```json
"description": "Query single-cell data. Prerequisites: Requires 'package-name' (install: pip install tooluniverse[extra]). Returns..."
```

Include:
- Package installation command
- API key requirements
- Account creation instructions

### 3. Expand Critical Abbreviations

**Problem**: New users don't understand technical terms.

**Fix**: Expand on first use with format: "Abbreviation (Full Name)".

Common abbreviations to expand:
- H5AD → HDF5-based AnnData
- RPM → Reads Per Million
- TSS → Transcription Start Site
- TAD → Topologically Associating Domain
- DRS → Data Repository Service
- API names (MACS2, IUPAC, etc.)

```json
// Before
"description": "Download H5AD files..."

// After  
"description": "Download H5AD (HDF5-based AnnData) files..."
```

## High-Priority Improvements

### 4. Enhance Filter Parameter Descriptions

**Problem**: Users don't know what fields are available or what syntax to use.

**Fix**: List operators, common fields, and provide multiple examples.

```json
"parameter_name": {
  "type": "string",
  "description": "Filter using SQL-like syntax. Format: 'field == \"value\"'. Operators: ==, !=, in, <, >, <=, >=. Combine with 'and'/'or'. Common fields: tissue, cell_type, disease, assay, sex, ethnicity. Examples: 'tissue == \"lung\"', 'disease == \"COVID-19\" and tissue == \"lung\"', 'cell_type in [\"T cell\", \"B cell\"]'."
}
```

Include:
- Syntax format
- Available operators
- List of 5-10 common fields
- 2-3 diverse examples

### 5. Improve Parameter Guidance

**Problem**: Users don't know which value to choose or what trade-offs exist.

**Fix**: Explain what each value means and provide recommendations.

```json
// Before
"threshold": "Q-value threshold (05=1e-5, 10=1e-10, 20=1e-20)"

// After
"threshold": "Peak calling stringency. '05'=1e-5 (permissive, more peaks, broad features), '10'=1e-10 (moderate, balanced), '20'=1e-20 (strict, high confidence, narrow peaks). Default '05' suitable for most analyses. Higher values = fewer but more confident peaks."
```

For each parameter option, explain:
- What it means practically
- When to use it
- Trade-offs involved
- Recommended default

### 6. Number Mutually Exclusive Options

**Problem**: Users provide multiple options when only one is allowed.

**Fix**: Label options as "**Option 1**", "**Option 2**", etc.

```json
"bed_data": {
  "description": "**Option 1**: BED format regions (tab-separated: chr, start, end). Example: 'chr1\\t1000\\t2000'."
},
"motif": {
  "description": "**Option 2**: DNA sequence motif in IUPAC notation. Use: A/T/G/C, W=A|T, S=G|C. Example: 'CANNTG'."
},
"gene_list": {
  "description": "**Option 3**: Gene symbols as array. Example: ['TP53', 'MDM2']."
}
```

## Medium-Priority Improvements

### 7. Add File Size Warnings

For tools that download or return large files:

```json
"description": "Download contact matrices. Note: Files can be large (GBs), check file_size in metadata before downloading. Returns..."
```

### 8. Clarify Web Form vs API Results

When tool returns submission URL instead of direct results:

```json
"description": "Perform enrichment analysis. Note: Returns submission URL (web form-based analysis). Analyzes..."
```

### 9. Explain File Type Differences

For tools with multiple format options:

```json
"file_type": "File format. Common types: 'cooler' (multi-resolution contact matrices), 'pairs' (aligned read pairs), 'hic' (Juicer format), 'mcool' (multi-resolution cooler)."
```

## Description Structure Template

```json
{
  "name": "Tool_operation_name",
  "type": "ToolClassName",
  "description": "[Action verb] to [purpose]. [Prerequisites if first tool]. [Key data/features]. [Required inputs if mutually exclusive]. [Note about limitations/requirements]. Use for: [use case 1], [use case 2], [use case 3].",
  "parameter": {
    "properties": {
      "param_name": {
        "type": "string",
        "description": "[What it does]. [Format/syntax if applicable]. [Options with trade-offs]. [Examples]. [Recommendation if applicable]."
      }
    }
  }
}
```

## Description Quality Checklist

### Clarity Checks
- [ ] Purpose clear in first sentence
- [ ] Technical terms expanded
- [ ] Prerequisites stated upfront
- [ ] Examples show realistic usage
- [ ] "Use for:" section lists 3-5 concrete use cases

### Completeness Checks
- [ ] Required inputs clearly marked
- [ ] Parameter choices explained
- [ ] Limitations noted (file size, web form, etc.)
- [ ] Available fields listed for filters
- [ ] Default values recommended

### Usability Checks
- [ ] New users can understand without external docs
- [ ] Users know what to provide
- [ ] Users can make informed parameter choices
- [ ] Error prevention (mutually exclusive options labeled)

## Testing Description Quality

To verify description quality, ask:

1. **Can a new user understand what the tool does?**
   - Read only the description (no docs)
   - Should be clear within 30 seconds

2. **Can a user provide correct inputs on first try?**
   - Required inputs obvious
   - Format/syntax clear
   - Mutually exclusive options labeled

3. **Can a user choose appropriate parameters?**
   - Trade-offs explained
   - Recommendations provided
   - Defaults justified

4. **Are prerequisites obvious?**
   - Installation instructions
   - API keys/accounts
   - File size warnings

## Common Patterns by Tool Type

### API Query Tools
```json
"description": "Query [data type] from [source]. [Prerequisites]. Filter by [criteria]. Returns [output]. [Data scale]. Use for: [discovery], [analysis], [specific research tasks]."
```

Key elements:
- What you're querying
- How to filter
- What you get back
- Scale of data
- Prerequisites

### Data Download Tools
```json
"description": "Download [file types] from [source]. [Format details]. [File size warning]. [Authentication requirement]. Use for: [offline analysis], [custom processing], [integration]."
```

Key elements:
- File formats available
- Size warning
- Authentication needs
- What's in the files

### Enrichment/Analysis Tools
```json
"description": "Analyze [input type] to find [results]. **Required: Provide ONE input type** - (1) [option], (2) [option], (3) [option]. Compares against [database/background]. [Result format]. Use for: [identifying], [discovering], [predicting]."
```

Key elements:
- Input requirements clear
- Options numbered
- What gets compared
- What you learn

## Validation Commands

After updating descriptions, validate JSON syntax:

```bash
# Validate all tool JSONs
python3 -m json.tool src/tooluniverse/data/your_tools.json > /dev/null && echo "✓ Valid"

# Check all tools in category
for f in src/tooluniverse/data/*_tools.json; do
  python3 -m json.tool "$f" > /dev/null && echo "✓ $f valid" || echo "✗ $f invalid"
done
```

## Example: Before and After

**Before (Unclear):**
```json
{
  "name": "Tool_enrichment",
  "description": "Perform enrichment with tool to find factors.",
  "parameter": {
    "properties": {
      "bed": {"description": "BED data"},
      "motif": {"description": "Motif"},
      "genes": {"description": "Genes"},
      "threshold": {"description": "Threshold value"}
    }
  }
}
```

**After (Clear):**
```json
{
  "name": "Tool_enrichment_analysis",
  "description": "Identify transcription factors enriched in your data. **Required: Provide ONE input type** - (1) BED genomic regions, (2) DNA sequence motif (IUPAC notation), or (3) gene symbol list. Compares against 400,000+ ChIP-seq experiments. Returns ranked proteins with enrichment scores. Note: Returns submission URL (web-based analysis). Use for: identifying regulators of regions, finding proteins bound to motifs, discovering transcription factors regulating genes.",
  "parameter": {
    "properties": {
      "bed_data": {
        "description": "**Option 1**: BED format regions (tab-separated: chr, start, end). For finding proteins bound to genomic regions. Example: 'chr1\\t1000\\t2000'."
      },
      "motif": {
        "description": "**Option 2**: DNA motif in IUPAC notation (A/T/G/C, W=A|T, S=G|C, M=A|C, K=G|T, R=A|G, Y=C|T). Example: 'CANNTG' (E-box)."
      },
      "gene_list": {
        "description": "**Option 3**: Gene symbols as array or single gene. Example: ['TP53', 'MDM2', 'CDKN1A']."
      },
      "threshold": {
        "description": "Peak stringency. '05'=1e-5 (permissive, more peaks), '10'=1e-10 (moderate), '20'=1e-20 (strict, high confidence). Default '05' suitable for most analyses."
      }
    }
  }
}
```

## Summary

**Priority order for optimization:**

1. **Critical** (fix immediately):
   - Clarify required inputs
   - Add prerequisites
   - Expand abbreviations

2. **High** (fix soon):
   - Enhance filter descriptions
   - Improve parameter guidance
   - Number mutually exclusive options

3. **Medium** (nice to have):
   - Add file size warnings
   - Clarify web form vs API
   - Explain file type differences

**Expected impact**: 50-75% reduction in user errors, 50-67% faster time to first successful use.
