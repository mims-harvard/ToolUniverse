---
name: tooluniverse-metabolomics
description: Comprehensive metabolomics research skill for identifying metabolites, analyzing studies, and searching metabolomics databases. Integrates HMDB (220k+ metabolites), MetaboLights, Metabolomics Workbench, and PubChem. Use when asked to identify or annotate metabolites (HMDB IDs, chemical properties, pathways), retrieve metabolomics study information from MetaboLights (MTBLS*) or Metabolomics Workbench (ST*), search for studies by keywords or disease, or generate comprehensive metabolomics research reports.
---

# Metabolomics Research

Identify metabolites, analyze studies, and search metabolomics databases. Generates structured markdown reports.

## Databases

| Database | Coverage | Fallback |
|----------|----------|----------|
| **HMDB** | 220,000+ metabolites, pathways, biological roles | Primary |
| **MetaboLights** | Thousands of metabolomics studies | Primary |
| **Metabolomics Workbench** | NIH metabolomics data repository | Primary |
| **PubChem** | Chemical properties and bioactivity | Fallback for HMDB |

## Research Workflow

The skill executes a 4-phase analysis pipeline:

### Phase 1: Metabolite Identification & Annotation

```python
# Search HMDB for metabolite
result = tu.run({"name": "HMDB_search", "arguments": {"operation": "search", "query": "glucose"}})
# CHECKPOINT: Verify result contains HMDB ID before proceeding
if result and result.get("data"):
    hmdb_id = result["data"][0]["hmdb_id"]
    details = tu.run({"name": "HMDB_get_metabolite", "arguments": {"operation": "get_metabolite", "hmdb_id": hmdb_id}})
else:
    # Fallback to PubChem
    cid = tu.run({"name": "PubChem_get_CID_by_compound_name", "arguments": {"compound_name": "glucose"}})
```

### Phase 2: Study Details Retrieval

```python
# Detect database from prefix and retrieve
if study_id.startswith("MTBLS"):
    study = tu.run({"name": "metabolights_get_study", "arguments": {"study_id": "MTBLS1"}})
elif study_id.startswith("ST"):
    study = tu.run({"name": "MetabolomicsWorkbench_get_study", "arguments": {"study_id": "ST000001"}})
# CHECKPOINT: Verify study metadata is populated before writing to report
```

### Phase 3: Study Search

```python
results = tu.run({"name": "metabolights_search_studies", "arguments": {"query": "diabetes"}})
# CHECKPOINT: Verify results are not empty before generating report section
```

### Phase 4: Database Overview
Sample recent studies from MetaboLights via `metabolights_list_studies` and include database statistics.

## Usage Patterns

- **Metabolite Identification**: Pass a metabolite list (e.g., `["glucose", "lactate", "pyruvate"]`) to get HMDB IDs, formulas, pathways, and PubChem CIDs.
- **Study Retrieval**: Pass a study ID (`"MTBLS1"` or `"ST000001"`) to get study metadata and data availability.
- **Study Search**: Pass a search query (e.g., `"diabetes"`) with an optional organism filter to find matching studies.
- **Comprehensive Analysis**: Combine all of the above in a single request for a cross-referenced report.

## Input Parameters

### metabolite_list (optional)
List of metabolite names to identify and annotate.
- **Format**: List of strings
- **Examples**: `["glucose"]`, `["lactate", "pyruvate", "acetate"]`
- **Note**: Common names accepted; HMDB will find standard identifiers

### study_id (optional)
MetaboLights or Metabolomics Workbench study identifier.
- **Format**: String starting with "MTBLS" or "ST"
- **Examples**: `"MTBLS1"`, `"ST000001"`
- **Note**: Database auto-detected from prefix

### search_query (optional)
Keyword to search metabolomics studies.
- **Format**: String (disease, compound, organism, method)
- **Examples**: `"diabetes"`, `"glucose metabolism"`, `"LC-MS"`

### organism (optional)
Target organism for study filtering.
- **Format**: String (scientific name)
- **Default**: `"Homo sapiens"`

### output_file (optional)
Path for the generated markdown report.
- **Format**: String (filename with .md extension)
- **Default**: Auto-generated timestamp-based filename

## Implementation Notes

### SOAP Tool Handling
**HMDB tools are SOAP-based** and require special parameter handling:
- `HMDB_search`: Requires `operation="search"` parameter
- `HMDB_get_metabolite`: Requires `operation="get_metabolite"` parameter
- Do not use `endpoint` or `method` parameters (not applicable to SOAP)

### Response Format Variations
Tools return different response formats - handle all three:
1. **Standard format**: `{status: "success", data: [...], metadata: {...}}`
2. **Direct list**: `[...]` (e.g., metabolights_list_studies)
3. **Direct dict**: `{field1: ..., field2: ...}` (e.g., some detail endpoints)

Always check response type with `isinstance()` before accessing fields.

### Fallback Strategy
1. **Primary source**: Try main database first (HMDB for metabolites, MetaboLights for studies)
2. **Fallback source**: Use alternative database if primary fails (PubChem for chemical properties)
3. **Default behavior**: Show error message with context, continue with remaining phases

### Progressive Report Writing
Write report incrementally: create the output file early, append sections as each phase completes, and return the file path when done.

## Tool Parameter Reference

| Tool | Required Parameters | Notes |
|------|---------------------|-------|
| `HMDB_search` | `operation="search"`, `query` | SOAP tool |
| `HMDB_get_metabolite` | `operation="get_metabolite"`, `hmdb_id` | SOAP tool |
| `metabolights_list_studies` | (none; optional `size`) | May return direct list |
| `metabolights_search_studies` | `query` | Returns study IDs |
| `metabolights_get_study` | `study_id` | Full study metadata |
| `MetabolomicsWorkbench_get_study` | `study_id` | Optional `output_item` |
| `MetabolomicsWorkbench_search_compound_by_name` | `compound_name` | Compound info |
| `PubChem_get_CID_by_compound_name` | `compound_name` | Returns CID |
| `PubChem_get_compound_properties_by_CID` | `cid` | Chemical properties |

## Common Issues

- **HMDB returns "Error querying HMDB: 0"**: Expected for uncommon metabolites; PubChem fallback will be attempted automatically.
- **Study details show "N/A" for all fields**: Verify study ID format (MTBLS* or ST*) and that the study is public.
- **Tool not found errors**: Check `.env.template` and add required API keys to `.env` (most metabolomics tools work without keys).
- **Large metabolite lists run slowly**: Reports auto-limit to first 10 metabolites; batch larger lists.
