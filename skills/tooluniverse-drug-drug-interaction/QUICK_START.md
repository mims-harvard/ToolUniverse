# DDI Skill - Quick Start Guide

**Status**: ✅ **WORKING** - Pipeline fixed and tested
**Last Updated**: 2026-02-09

---

## Choose Your Implementation

### Python SDK

#### Option 1: Use the Working Pipeline (RECOMMENDED)

```python
# Import from either file (both work)
from python_implementation import DDIAnalyzer
# or: from ddi_pipeline import DDIAnalyzer

# Initialize analyzer
analyzer = DDIAnalyzer()

# Analyze drug pair
report = analyzer.analyze("warfarin", "amoxicillin")

# Report automatically saved to: DDI_report_warfarin_amoxicillin.md
print(f"Risk Score: {report['risk_score']}/100")
print(f"Severity: {report['severity']}")
```

#### Option 2: Use Individual Tools

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Drug identification (RxNorm)
result = tu.tools.RxNorm_get_drug_names(drug_name="warfarin")  # ✅ Correct parameter

# Drug interactions (DrugBank)
result = tu.tools.drugbank_get_drug_interactions_by_drug_name_or_id(
    query="warfarin",      # ✅ Correct parameter
    case_sensitive=False,
    exact_match=False,
    limit=50
)

# Pharmacology (DrugBank)
result = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(
    query="warfarin",      # ✅ Correct parameter
    case_sensitive=False,
    exact_match=False,
    limit=1
)

# FDA Labels (DailyMed - 2 steps)
search = tu.tools.DailyMed_search_spls(query="warfarin")
setid = search['data']['spls'][0]['setid']
interactions = tu.tools.DailyMed_parse_drug_interactions(setid=setid)

# Literature (PubMed)
result = tu.tools.PubMed_search_articles(
    query='"warfarin" AND "drug interaction"',
    max_results=10
)

# Adverse events (FAERS)
result = tu.tools.FAERS_count_reactions_by_drug_event(
    medicinalproduct="warfarin",  # ✅ Correct parameter (not 'drug_name')
    event_name="drug interaction"
)
```

---

### MCP (Model Context Protocol)

#### Option 1: Conversational (Claude Desktop or Compatible Client)

Tell Claude:
> "Analyze drug-drug interactions between warfarin and amoxicillin using ToolUniverse"

Claude will follow the workflow from SKILL.md and use these tools:
1. RxNorm_get_drug_names - Drug identification
2. drugbank_get_drug_interactions - Interaction data
3. DailyMed_parse_drug_interactions - FDA labels
4. PubMed_search_articles - Literature evidence
5. FAERS_count_reactions - Adverse events

#### Option 2: Direct Tool Calls

**Step 1: Drug Identification**
```json
Tool: RxNorm_get_drug_names
Parameters:
{
  "drug_name": "warfarin"
}
```

**Step 2: Interaction Analysis**
```json
Tool: drugbank_get_drug_interactions_by_drug_name_or_id
Parameters:
{
  "query": "warfarin",
  "case_sensitive": false,
  "exact_match": false,
  "limit": 50
}
```

**Step 3: FDA Label Warnings**
```json
Tool: DailyMed_search_spls
Parameters:
{
  "query": "warfarin"
}

Then use the returned setid:

Tool: DailyMed_parse_drug_interactions
Parameters:
{
  "setid": "[setid from previous call]"
}
```

**Step 4: Literature Evidence**
```json
Tool: PubMed_search_articles
Parameters:
{
  "query": "\"warfarin\" AND \"drug interaction\"",
  "max_results": 10
}
```

**Step 5: Adverse Events**
```json
Tool: FAERS_count_reactions_by_drug_event
Parameters:
{
  "medicinalproduct": "warfarin",
  "event_name": "drug interaction"
}
```

---

## Run Examples (Python SDK)

```bash
# Run the working pipeline
python ddi_pipeline.py

# Generates reports:
#   - DDI_report_warfarin_amoxicillin.md
#   - DDI_report_simvastatin_ketoconazole.md
```

---

## What Works ✅

- ✅ Drug identification (RxNorm)
- ✅ DrugBank integration (correct parameters)
- ✅ DailyMed FDA labels
- ✅ PubMed literature search
- ✅ FAERS adverse events
- ✅ Report generation (markdown)
- ✅ Risk scoring algorithm
- ✅ Clinical recommendations

---

## Known Limitations

⚠️ **Data Availability**: Some tools return empty results:
- DrugBank interactions may not find all drug pairs
- FAERS data may be limited
- This is a data availability issue, not a code issue

⚠️ **Response Formats**: Some tools return lists instead of dicts:
- Pipeline handles this gracefully
- Reports still generate successfully

---

## Tool Parameters (All Implementations)

These parameter names apply to **both Python SDK and MCP**:

| Tool | Parameter | Correct Name | Notes |
|------|-----------|--------------|-------|
| RxNorm_get_drug_names | Drug name | `drug_name` | NOT `query` |
| drugbank_* | Drug query | `query` | All DrugBank tools use this |
| FAERS_count_reactions_by_drug_event | Drug name | `medicinalproduct` | NOT `drug_name` |
| DailyMed_search_spls | Search query | `query` | Step 1 of 2 |
| DailyMed_parse_drug_interactions | SetID | `setid` | Step 2 of 2 |

**Note**: Whether using Python SDK or MCP, the parameter names are the same

---

## Files

- `ddi_pipeline.py` - Complete working pipeline ✅
- `SKILL.md` - Skill documentation (framework)
- `EXAMPLES.md` - Clinical scenarios (documentation)
- `README.md` - Original readme
- `QUICK_START.md` - This file

---

*Fixed: 2026-02-09 - Pipeline now uses correct ToolUniverse tool parameters*
