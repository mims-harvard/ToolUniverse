# CRISPR Screen Analysis - Quick Start Guide

**Status**: ✅ **WORKING** - Uses Pharos fallback due to DepMap unavailability
**Last Updated**: 2026-02-09

---

## Choose Your Implementation

### Python SDK

#### Option 1: Conversational Analysis (RECOMMENDED)

The skill is designed for conversational use. Simply provide your gene list or ask about a cancer type:

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Example 1: Analyze gene list from your CRISPR screen
gene_list = ["KRAS", "EGFR", "WEE1", "PLK1", "AURKA", "CDK2", "CHEK1",
             "MCM2", "MCM3", "MCM4", "RPS6", "RPL5", "POLR2A", "E2F1",
             "RB1", "CCNE1", "CDC25A", "CDC6", "ORC1", "HDAC1"]

# The skill will create: CRISPR_screen_analysis_[CONTEXT].md report
# containing essentiality, pathway enrichment, druggability, and prioritization
```

#### Option 2: Use Individual Tools

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Gene validation (Pharos - fallback)
result = tu.tools.Pharos_get_target(gene="KRAS")

# Druggability assessment (Pharos)
result = tu.tools.Pharos_search_targets(query="KRAS", limit=1)

# Clinical trials
result = tu.tools.search_clinical_trials(
    intervention="KRAS inhibitor",
    recruitment_status="recruiting"
)

# Pathway enrichment (Enrichr)
result = tu.tools.enrichr_analyze_gene_list(
    gene_list=["KRAS", "EGFR", "BRAF"],
    library="KEGG_2021_Human"
)

# PPI networks (STRING)
result = tu.tools.STRING_get_interactions(
    identifiers="KRAS,EGFR,BRAF",
    species=9606
)

# Literature search (PubMed)
result = tu.tools.PubMed_search_articles(
    query='"KRAS" AND "CRISPR" AND "essential"',
    max_results=10
)
```

---

### MCP (Model Context Protocol)

#### Option 1: Conversational (Claude Desktop or Compatible Client)

Tell Claude:
> "I have CRISPR dropout screen hits from A549 lung cancer cells. Please analyze these genes: KRAS, EGFR, WEE1, PLK1, AURKA, CDK2, CHEK1, MCM2, MCM3, MCM4, RPS6, RPL5, POLR2A, E2F1, RB1, CCNE1, CDC25A, CDC6, ORC1, HDAC1"

Claude will follow the workflow from SKILL.md and use these tools:
1. Pharos_get_target - Gene validation (DepMap fallback)
2. Pharos_search_targets - Druggability assessment
3. enrichr_analyze_gene_list - Pathway enrichment
4. STRING_get_interactions - PPI network analysis
5. search_clinical_trials - Clinical relevance

#### Option 2: Direct Tool Calls

**Step 1: Gene Validation & Druggability (Pharos fallback)**
```json
Tool: Pharos_get_target
Parameters:
{
  "gene": "KRAS"
}

Returns:
- Gene name/symbol
- TDL (Target Development Level): Tclin, Tchem, Tbio, Tdark
- Known drugs
- Disease associations
```

**Step 2: Pathway Enrichment**
```json
Tool: enrichr_analyze_gene_list
Parameters:
{
  "gene_list": ["KRAS", "EGFR", "BRAF"],
  "library": "KEGG_2021_Human"
}

Alternative libraries:
- "WikiPathways_2021_Human"
- "Reactome_2022"
- "GO_Biological_Process_2021"
```

**Step 3: PPI Network Analysis**
```json
Tool: STRING_get_interactions
Parameters:
{
  "identifiers": "KRAS,EGFR,BRAF",
  "species": 9606,
  "required_score": 400
}
```

**Step 4: Clinical Trials**
```json
Tool: search_clinical_trials
Parameters:
{
  "intervention": "KRAS inhibitor",
  "recruitment_status": "recruiting"
}
```

**Step 5: Literature Evidence**
```json
Tool: PubMed_search_articles
Parameters:
{
  "query": "\"KRAS\" AND \"essential\" AND \"cancer\"",
  "max_results": 10
}
```

---

## ⚠️ Known Issue: DepMap Unavailability

### Current Status

**DepMap APIs are currently unavailable** (as of 2026-02-09). This affects:
- Gene essentiality scoring (CRISPR dependency data)
- Pan-cancer vs selective essentiality analysis
- Cell line-specific dependency data

### Workaround: Pharos Fallback

The skill automatically uses **Pharos** (druggability database) as fallback:

**What Pharos Provides:**
- ✅ Gene validation (100% success rate)
- ✅ Druggability assessment (TDL classification)
- ✅ Known drug information
- ✅ Disease associations

**TDL as Proxy for Essentiality:**
- **Tclin** (clinical target) → Often essential genes (★★★)
- **Tchem** (chemical probe available) → Potentially essential (★★☆)
- **Tbio** (biological target) → Lower confidence (★☆☆)
- **Tdark** (unknown) → No druggability data (☆☆☆)

**What's Missing:**
- ⚠️ Quantitative essentiality scores (DepMap gene effect)
- ⚠️ Pan-cancer vs selective dependency analysis
- ⚠️ Cell line-specific CRISPR data

**All findings are labeled with data source** (Pharos vs DepMap)

---

## Tool Parameters (All Implementations)

These parameter names apply to **both Python SDK and MCP**:

| Tool | Parameter | Correct Name | Notes |
|------|-----------|--------------|-------|
| Pharos_get_target | Gene symbol | `gene` | Fallback for DepMap |
| Pharos_search_targets | Query | `query` | Search by gene/drug |
| enrichr_analyze_gene_list | Gene list | `gene_list` | List of gene symbols |
| enrichr_analyze_gene_list | Library | `library` | Pathway database name |
| STRING_get_interactions | Gene list | `identifiers` | Comma-separated |
| STRING_get_interactions | Species | `species` | 9606 for human |
| search_clinical_trials | Intervention | `intervention` | Drug/target name |
| PubMed_search_articles | Query | `query` | Search string |

**Note**: Whether using Python SDK or MCP, the parameter names are the same

---

## Analysis Workflow

The skill follows a 7-path analysis strategy:

### PATH 0: Input Processing & Validation
- Validate gene symbols (Pharos fallback)
- Determine analysis mode (gene list/cancer type/single gene)
- Set context parameters

### PATH 1: Gene Essentiality Analysis
- **Primary**: DepMap CRISPR dependency scores (when available)
- **Fallback**: Pharos TDL classification (current)
- Pan-cancer vs selective essentiality
- Rank genes by dependency strength

### PATH 2: Pathway & Functional Enrichment
- GO enrichment (biological process, molecular function)
- Pathway enrichment (Reactome, WikiPathways, KEGG)
- Identify pathway-level vulnerabilities

### PATH 3: Protein-Protein Interaction Networks
- Build PPI network for hit genes (STRING)
- Identify protein complexes
- Find synthetic lethal candidates
- Hub gene analysis

### PATH 4: Druggability & Target Assessment
- Check existing drugs (Pharos, DGIdb, ChEMBL)
- Assess chemical tractability (Pharos TDL)
- Find chemical probes
- Clinical trial status

### PATH 5: Disease Association & Clinical Relevance
- Gene-disease associations (Open Targets, Pharos)
- Somatic mutations in cancer (COSMIC, cBioPortal)
- Expression in patient samples
- Prognostic/predictive biomarker status

### PATH 6: Hit Prioritization & Validation Guidance
- Integrate all evidence dimensions
- Calculate priority score (essentiality + druggability + clinical relevance)
- Recommend validation experiments
- Identify top 5-10 targets for follow-up

---

## Evidence Grading System

All findings are graded by confidence level:

| Level | Symbol | Criteria | Examples |
|-------|--------|----------|----------|
| **HIGH** | ★★★ | Strong data from multiple sources | Tclin + clinical trials + literature |
| **MEDIUM** | ★★☆ | Moderate data, pathway coherence | Tchem + pathway enrichment |
| **LOW** | ★☆☆ | Limited data, weak validation | Tbio/Tdark, single source |

**Current grading with Pharos fallback:**
- Tclin targets → ★★★ (often essential, validated)
- Tchem targets → ★★☆ (chemical probes available)
- Tbio/Tdark → ★☆☆ (limited druggability)

---

## Output Format

The skill generates a comprehensive markdown report:

```
CRISPR_screen_analysis_[CONTEXT].md

Sections:
1. Executive Summary
2. Gene Validation Results
3. Essentiality Classification
4. Pathway Enrichment Analysis
5. PPI Network Analysis
6. Druggability Assessment
7. Clinical Relevance
8. Target Prioritization
9. Validation Recommendations
```

---

## Example Use Cases

### Example 1: Analyze Gene List from Lung Cancer Screen

**Input:**
```python
gene_list = ["KRAS", "EGFR", "WEE1", "PLK1", "AURKA", "CDK2", "CHEK1"]
```

**Expected Output:**
- Essentiality classification using Pharos TDL
- Pathway enrichment (Cell Cycle Checkpoints, DNA Replication)
- Top priorities: KRAS (Tclin), EGFR (Tclin), WEE1 (Tchem)
- Validation recommendations

### Example 2: Find Essential Genes for Pancreatic Cancer

**Input:**
```
"What are the top essential genes for pancreatic cancer?"
```

**Expected Output:**
- Top druggable targets for pancreatic cancer
- KRAS appears as #1 (Tclin, 90% mutation rate)
- CDK4/6, WEE1, ATR (all Tclin/Tchem)
- Clinical trial landscape

### Example 3: Validate Single Gene Target

**Input:**
```
"Is WEE1 a good therapeutic target for TP53-mutant cancers?"
```

**Expected Output:**
- WEE1 druggability assessment (Tchem)
- Known inhibitors (adavosertib)
- Clinical trials (15 trials, Phase 2)
- Validation recommendations

---

## Common Enrichr Libraries

For pathway enrichment analysis:

| Library | Description | Use Case |
|---------|-------------|----------|
| KEGG_2021_Human | KEGG pathways | Standard pathway enrichment |
| WikiPathways_2021_Human | WikiPathways | Comprehensive pathway coverage |
| Reactome_2022 | Reactome pathways | Detailed pathway reactions |
| GO_Biological_Process_2021 | GO BP | Functional annotation |
| GO_Molecular_Function_2021 | GO MF | Molecular activity |
| MSigDB_Hallmark_2020 | Cancer hallmarks | Cancer-specific processes |

---

## Files

- `SKILL.md` - Complete workflow documentation
- `EXAMPLES.md` - Clinical scenarios and use cases
- `FALLBACK_PATCH.md` - DepMap fallback implementation details
- `README.md` - Overview
- `QUICK_START.md` - This file (for Python & MCP)

---

## Key Features

### ✅ What Works
- ✅ Gene validation (Pharos fallback)
- ✅ Druggability assessment (TDL classification)
- ✅ Pathway enrichment (Enrichr)
- ✅ PPI network analysis (STRING)
- ✅ Clinical trials search
- ✅ Literature evidence (PubMed)
- ✅ Report generation (markdown)
- ✅ Evidence grading system

### ⚠️ Current Limitations
- ⚠️ No quantitative essentiality scores (DepMap unavailable)
- ⚠️ TDL used as proxy for essentiality (not direct CRISPR data)
- ⚠️ Pan-cancer analysis limited to druggability

### 🔧 Planned Improvements
- 🔧 DepMap CSV download fallback (1-2 weeks)
- 🔧 Enhanced essentiality scoring when DepMap restored
- 🔧 Cell line-specific dependency analysis

---

## Tips for Best Results

### For Python SDK Users
1. Provide gene lists with 10-20 genes for meaningful enrichment
2. Include cancer type context for better interpretation
3. Check report file for complete analysis
4. Use Pharos TDL as initial druggability filter

### For MCP Users
1. Clearly state your analysis goal (gene list, cancer type, or single gene)
2. Provide cancer context when possible (e.g., "lung cancer screen")
3. Ask Claude to "create comprehensive CRISPR screen analysis report"
4. Request specific sections if needed (e.g., "focus on druggability")

### General Tips
1. **Start broad, narrow down**: Begin with pathway enrichment, then focus on top targets
2. **Consider TDL classification**: Prioritize Tclin/Tchem targets for validation
3. **Check clinical trials**: Existing trials indicate target validation
4. **Literature validation**: Use PubMed to support findings

---

*Updated: 2026-02-09 - Now supports both Python SDK and MCP implementations with Pharos fallback*
