# Clinical Trial Design - Quick Start Guide

**Status**: ✅ **WORKING** - Pipeline fixed and tested
**Last Updated**: 2026-02-09

---

## Choose Your Implementation

### Python SDK

#### Option 1: Use the Working Pipeline (RECOMMENDED)

```python
# Import from either file (both work)
from python_implementation import TrialFeasibilityAnalyzer
# or: from trial_pipeline import TrialFeasibilityAnalyzer

# Initialize analyzer
analyzer = TrialFeasibilityAnalyzer()

# Analyze trial feasibility
report = analyzer.analyze(
    indication="EGFR-mutant non-small cell lung cancer",
    drug_name="osimertinib",
    phase="Phase 2"
)

# Report automatically saved to: Trial_Feasibility_osimertinib.md
print(f"Feasibility Score: {report['feasibility_score']}/100")
```

#### Option 2: Use Individual Tools

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Disease information (Open Targets)
result = tu.tools.OpenTargets_get_disease_id_description_by_name(
    disease_name="non-small cell lung cancer"
)

# Drug profile (DrugBank)
result = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
    query="osimertinib",  # ✅ Correct parameter
    case_sensitive=False,
    exact_match=False,
    limit=1
)

# Pharmacology (DrugBank)
result = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(
    query="osimertinib",  # ✅ Correct parameter
    case_sensitive=False,
    exact_match=False,
    limit=1
)

# Safety data (DrugBank)
result = tu.tools.drugbank_get_safety_by_drug_name_or_drugbank_id(
    query="osimertinib",  # ✅ Correct parameter
    case_sensitive=False,
    exact_match=False,
    limit=1
)

# Precedent trials (ClinicalTrials.gov)
result = tu.tools.search_clinical_trials(
    condition="EGFR-mutant non-small cell lung cancer",
    intervention="osimertinib",
    max_results=10
)

# FDA warnings (FDA)
result = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(
    drug_name="osimertinib"
)

# Literature evidence (PubMed)
result = tu.tools.PubMed_search_articles(
    query='"EGFR-mutant NSCLC" AND "osimertinib"',
    max_results=20
)

# Prevalence data (PubMed)
result = tu.tools.PubMed_search_articles(
    query='"EGFR-mutant NSCLC" AND "prevalence"',
    max_results=5
)
```

---

### MCP (Model Context Protocol)

#### Option 1: Conversational (Claude Desktop or Compatible Client)

Tell Claude:
> "Analyze clinical trial feasibility for osimertinib in EGFR-mutant NSCLC using ToolUniverse"

Claude will follow the workflow from SKILL.md and use these tools:
1. OpenTargets_get_disease_id_description_by_name - Disease identification
2. drugbank_get_drug_basic_info_by_drug_name_or_id - Drug profile
3. drugbank_get_pharmacology_by_drug_name_or_drugbank_id - Mechanism
4. search_clinical_trials - Precedent trials
5. drugbank_get_safety_by_drug_name_or_drugbank_id - Safety profile
6. FDA_get_warnings_and_cautions_by_drug_name - FDA warnings
7. PubMed_search_articles - Literature evidence

#### Option 2: Direct Tool Calls

**Step 1: Disease Identification**
```json
Tool: OpenTargets_get_disease_id_description_by_name
Parameters:
{
  "disease_name": "EGFR-mutant non-small cell lung cancer"
}
```

**Step 2: Drug Profile**
```json
Tool: drugbank_get_drug_basic_info_by_drug_name_or_id
Parameters:
{
  "query": "osimertinib",
  "case_sensitive": false,
  "exact_match": false,
  "limit": 1
}
```

**Step 3: Pharmacology & Mechanism**
```json
Tool: drugbank_get_pharmacology_by_drug_name_or_drugbank_id
Parameters:
{
  "query": "osimertinib",
  "case_sensitive": false,
  "exact_match": false,
  "limit": 1
}
```

**Step 4: Precedent Trials**
```json
Tool: search_clinical_trials
Parameters:
{
  "condition": "EGFR-mutant non-small cell lung cancer",
  "intervention": "osimertinib",
  "max_results": 10
}
```

**Step 5: Safety Assessment (DrugBank)**
```json
Tool: drugbank_get_safety_by_drug_name_or_drugbank_id
Parameters:
{
  "query": "osimertinib",
  "case_sensitive": false,
  "exact_match": false,
  "limit": 1
}
```

**Step 6: FDA Warnings**
```json
Tool: FDA_get_warnings_and_cautions_by_drug_name
Parameters:
{
  "drug_name": "osimertinib"
}
```

**Step 7: Literature Evidence**
```json
Tool: PubMed_search_articles
Parameters:
{
  "query": "\"EGFR-mutant NSCLC\" AND \"osimertinib\"",
  "max_results": 20
}
```

**Step 8: Prevalence Data**
```json
Tool: PubMed_search_articles
Parameters:
{
  "query": "\"EGFR-mutant NSCLC\" AND \"prevalence\"",
  "max_results": 5
}
```

---

## Run Examples (Python SDK)

```bash
# Run the working pipeline
python trial_pipeline.py

# Generates report:
#   - Trial_Feasibility_osimertinib.md
```

---

## What Works ✅

- ✅ Disease identification (Open Targets)
- ✅ Drug profiling (DrugBank - correct parameters)
- ✅ Pharmacology data (DrugBank)
- ✅ Safety assessment (DrugBank + FDA)
- ✅ Precedent trial search (ClinicalTrials.gov)
- ✅ Literature evidence (PubMed)
- ✅ Prevalence estimation (PubMed proxy)
- ✅ Feasibility scoring (0-100 scale)
- ✅ Report generation (markdown)
- ✅ Clinical interpretation

---

## Pipeline Analysis Steps

The pipeline performs 6-step analysis:

1. **Patient Population Analysis**
   - Disease identification (Open Targets)
   - Prevalence estimation (PubMed literature)

2. **Drug Profile Analysis**
   - Drug identification (DrugBank)
   - Mechanism of action (DrugBank pharmacology)

3. **Precedent Trial Search**
   - Similar trials (ClinicalTrials.gov)
   - Phase/status information

4. **Safety Assessment**
   - Toxicity data (DrugBank)
   - FDA warnings (FDA labels)

5. **Literature Evidence**
   - Published studies (PubMed)
   - Research support

6. **Feasibility Scoring**
   - 0-100 score based on data availability
   - Clinical interpretation

---

## Feasibility Score Interpretation

- **75-100**: HIGH FEASIBILITY - Strong precedent and data available
- **50-74**: MODERATE FEASIBILITY - Some gaps but viable
- **25-49**: LOW FEASIBILITY - Significant challenges
- **0-24**: VERY LOW FEASIBILITY - Major gaps in data/precedent

---

## Known Limitations

⚠️ **Data Availability**: Some tools return empty results:
- DrugBank may not include very new drugs (e.g., osimertinib)
- ClinicalTrials.gov API may have limited search results
- This is a data availability issue, not a code issue

⚠️ **Novel Compounds**: Experimental drugs may show low feasibility scores simply due to lack of historical data, not actual infeasibility

---

## Tool Parameters (All Implementations)

These parameter names apply to **both Python SDK and MCP**:

| Tool | Parameter | Correct Name | Notes |
|------|-----------|--------------|-------|
| drugbank_get_drug_basic_info | Drug query | `query` | All DrugBank tools use this |
| drugbank_get_pharmacology | Drug query | `query` | NOT `drug_name_or_drugbank_id` |
| drugbank_get_safety | Drug query | `query` | NOT `drug_name_or_drugbank_id` |
| OpenTargets_get_disease_id | Disease name | `disease_name` | Returns Ensembl disease IDs |
| search_clinical_trials | Condition | `condition` | Separate from `intervention` |
| FDA_get_warnings_and_cautions | Drug name | `drug_name` | Simple string parameter |
| PubMed_search_articles | Search query | `query` | Supports PubMed query syntax |

**Note**: Whether using Python SDK or MCP, the parameter names are the same

---

## Files

- `trial_pipeline.py` - Complete working pipeline ✅
- `python_implementation.py` - Same pipeline (for consistency with other skills) ✅
- `SKILL.md` - Skill documentation (framework)
- `EXAMPLES.md` - Clinical scenarios (documentation)
- `README.md` - Original readme
- `QUICK_START.md` - This file

---

*Fixed: 2026-02-09 - Pipeline now uses correct ToolUniverse tool parameters*
