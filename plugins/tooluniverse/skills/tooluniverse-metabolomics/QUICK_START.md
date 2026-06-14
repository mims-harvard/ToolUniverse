# Metabolomics Research - Quick Start Guide

This guide shows how to use the Metabolomics Research skill with both Python SDK and MCP implementations.

## Table of Contents
- [Python SDK Usage](#python-sdk-usage)
- [MCP Integration](#mcp-integration)
- [Example Workflows](#example-workflows)
- [Troubleshooting](#troubleshooting)

---

## Python SDK Usage

### Installation

```bash
# Install ToolUniverse
pip install tooluniverse

# Or with uv (recommended)
uv pip install tooluniverse
```

### Basic Usage

```python
from tooluniverse import ToolUniverse

# Initialize ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Example 1: Search for metabolite information
result = tu.tools.HMDB_search(
    operation="search",  # SOAP tool - required parameter
    query="glucose"
)
print(result)
# Output: {status: "success", data: [{accession: "HMDB0000122", name: "Glucose", ...}]}

# Example 2: Get detailed metabolite information
result = tu.tools.HMDB_get_metabolite(
    operation="get_metabolite",  # SOAP tool - required parameter
    hmdb_id="HMDB0000122"
)
print(result['data']['chemical_formula'])  # C6H12O6

# Example 3: Search MetaboLights studies
result = tu.tools.metabolights_search_studies(query="diabetes")
print(f"Found {len(result['data'])} studies")

# Example 4: Get study details
result = tu.tools.metabolights_get_study(study_id="MTBLS1")
print(result['data']['title'])
```

### Using the Pipeline Function

The skill provides a complete pipeline function in `python_implementation.py`:

```python
from python_implementation import metabolomics_analysis_pipeline

# Example 1: Analyze metabolites only
metabolomics_analysis_pipeline(
    metabolite_list=["glucose", "lactate", "pyruvate"],
    output_file="metabolite_analysis.md"
)
# Creates: metabolite_analysis.md with HMDB IDs, formulas, pathways

# Example 2: Retrieve study information
metabolomics_analysis_pipeline(
    study_id="MTBLS1",
    output_file="study_report.md"
)
# Creates: study_report.md with study metadata and details

# Example 3: Search for studies
metabolomics_analysis_pipeline(
    search_query="diabetes",
    organism="Homo sapiens",
    output_file="diabetes_studies.md"
)
# Creates: diabetes_studies.md with matching studies

# Example 4: Comprehensive analysis
metabolomics_analysis_pipeline(
    metabolite_list=["glucose", "pyruvate"],
    study_id="MTBLS1",
    search_query="diabetes",
    organism="Homo sapiens",
    output_file="comprehensive_report.md"
)
# Creates: comprehensive_report.md with all phases
```

### Advanced: Custom Error Handling

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

metabolites = ["glucose", "lactate", "unknown_compound_xyz"]

for metabolite in metabolites:
    try:
        result = tu.tools.HMDB_search(
            operation="search",
            query=metabolite
        )

        if result.get('status') == 'success':
            data = result.get('data', [])
            if data:
                print(f"✓ {metabolite}: {data[0]['accession']}")
            else:
                print(f"✗ {metabolite}: Not found in HMDB")
        else:
            print(f"✗ {metabolite}: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"✗ {metabolite}: Exception - {e}")
```

---

## MCP Integration

### Setup with Claude Desktop

1. **Install ToolUniverse MCP server:**
```bash
uv tool install tooluniverse
```

2. **Configure Claude Desktop:**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["tooluniverse"]
    }
  }
}
```

3. **Restart Claude Desktop**

### Using with Claude Desktop

Once configured, you can use natural language:

**Example 1: Metabolite identification**
```
User: "What is the HMDB ID and chemical formula for glucose?"

Claude: Let me search the HMDB database for glucose.
[Uses HMDB_search and HMDB_get_metabolite tools]
Glucose has HMDB ID: HMDB0000122 and formula: C6H12O6
```

**Example 2: Study search**
```
User: "Find metabolomics studies about diabetes"

Claude: I'll search MetaboLights for diabetes studies.
[Uses metabolights_search_studies tool]
Found 2,665 studies related to diabetes. Here are the top results:
- MTBLS1: ...
- MTBLS2: ...
```

**Example 3: Comprehensive analysis**
```
User: "Analyze these metabolites: glucose, lactate, pyruvate.
       Also get details for study MTBLS1 and search for diabetes studies.
       Create a comprehensive report."

Claude: I'll execute a 4-phase analysis:
1. Identifying metabolites in HMDB
2. Retrieving MTBLS1 study details
3. Searching for diabetes studies
4. Compiling database overview

[Uses multiple tools and generates report]
Report created: comprehensive_analysis.md
```

### MCP with Other Clients

**Cursor IDE:**
```json
// .cursor/mcp_config.json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["tooluniverse"]
    }
  }
}
```

**Windsurf:**
```json
// settings.json
{
  "mcp.servers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["tooluniverse"]
    }
  }
}
```

---

## Example Workflows

### Workflow 1: Metabolite Profiling Pipeline

**Goal:** Annotate a list of metabolites from an LC-MS experiment

```python
from python_implementation import metabolomics_analysis_pipeline

# List of metabolites detected in your experiment
detected_metabolites = [
    "glucose",
    "lactate",
    "pyruvate",
    "acetate",
    "citrate",
    "succinate",
    "fumarate",
    "malate"
]

# Generate comprehensive annotation report
metabolomics_analysis_pipeline(
    metabolite_list=detected_metabolites,
    organism="Homo sapiens",
    output_file="lcms_metabolite_annotation.md"
)

# Output: lcms_metabolite_annotation.md with:
# - HMDB IDs for all metabolites
# - Chemical formulas and molecular weights
# - Biological pathways (e.g., TCA cycle, glycolysis)
# - PubChem CIDs for further analysis
```

### Workflow 2: Disease-Focused Study Discovery

**Goal:** Find all relevant metabolomics studies for a disease

```python
from python_implementation import metabolomics_analysis_pipeline

# Search for disease-related studies
diseases = ["diabetes", "obesity", "cardiovascular"]

for disease in diseases:
    metabolomics_analysis_pipeline(
        search_query=disease,
        organism="Homo sapiens",
        output_file=f"{disease}_studies.md"
    )

# Creates separate reports:
# - diabetes_studies.md
# - obesity_studies.md
# - cardiovascular_studies.md
```

### Workflow 3: Study Comparison

**Goal:** Compare metabolomics data from multiple studies

```python
from python_implementation import metabolomics_analysis_pipeline

# Compare studies
study_ids = ["MTBLS1", "MTBLS2", "MTBLS3"]

for study_id in study_ids:
    metabolomics_analysis_pipeline(
        study_id=study_id,
        output_file=f"study_{study_id}_report.md"
    )

# Creates detailed reports for each study
# - study_MTBLS1_report.md
# - study_MTBLS2_report.md
# - study_MTBLS3_report.md
```

### Workflow 4: Full Research Pipeline

**Goal:** Complete metabolomics research analysis from compounds to literature

```python
from python_implementation import metabolomics_analysis_pipeline
from tooluniverse import ToolUniverse

# Step 1: Identify metabolites
metabolites = ["glucose", "lactate"]
metabolomics_analysis_pipeline(
    metabolite_list=metabolites,
    output_file="step1_metabolites.md"
)

# Step 2: Search for related studies
metabolomics_analysis_pipeline(
    search_query="glucose metabolism",
    output_file="step2_studies.md"
)

# Step 3: Get specific study details
metabolomics_analysis_pipeline(
    study_id="MTBLS1",
    output_file="step3_study_details.md"
)

# Step 4: Comprehensive analysis
metabolomics_analysis_pipeline(
    metabolite_list=metabolites,
    study_id="MTBLS1",
    search_query="glucose metabolism",
    output_file="step4_comprehensive.md"
)
```

---

## Troubleshooting

### Problem: "Tool not found" errors

**Symptoms:**
```python
KeyError: 'HMDB_search'
```

**Solution:**
```python
# Verify tools are loaded
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Check available HMDB tools
hmdb_tools = [name for name in tu.all_tool_dict.keys() if 'HMDB' in name]
print(f"HMDB tools available: {hmdb_tools}")

# Expected: ['HMDB_search', 'HMDB_get_metabolite', ...]
```

### Problem: SOAP tool parameter errors

**Symptoms:**
```
Parameter validation failed: 'operation' is a required property
```

**Solution:**
```python
# ❌ WRONG - Missing operation parameter
result = tu.tools.HMDB_search(query="glucose")

# ✅ CORRECT - Include operation parameter
result = tu.tools.HMDB_search(
    operation="search",  # REQUIRED for SOAP tools
    query="glucose"
)
```

### Problem: Empty results or "Error querying HMDB: 0"

**Symptoms:**
```
*Error querying HMDB: 0*
```

**Cause:** HMDB search returned no results, or result list is empty

**Solution:**
```python
# Add defensive checks
result = tu.tools.HMDB_search(operation="search", query="metabolite_name")

if result.get('status') == 'success':
    data = result.get('data', [])
    if data and len(data) > 0:
        hmdb_id = data[0].get('accession', 'N/A')
        # Safe to access first result
    else:
        print("No results found - try different spelling or synonym")
```

### Problem: Missing API keys warning

**Symptoms:**
```
⚠️  Some tools will not be loaded due to missing API keys: OMIM_API_KEY, ...
```

**Solution:**
Most metabolomics tools work WITHOUT API keys. This warning is informational.

```bash
# Optional: Add API keys for extended functionality
cp .env.template .env
# Edit .env and add your API keys
```

### Problem: Response format variations

**Symptoms:**
```python
# Sometimes this works
result['data']

# Sometimes it doesn't - TypeError: list indices must be integers
```

**Solution:**
```python
# Handle all response formats
if isinstance(result, dict):
    if result.get('status') == 'success':
        data = result.get('data', [])  # Standard format
    else:
        print(f"Error: {result.get('error')}")
elif isinstance(result, list):
    data = result  # Direct list format
elif isinstance(result, dict):
    data = result  # Direct dict format
else:
    print(f"Unexpected format: {type(result)}")
```

### Problem: Large metabolite lists are slow

**Symptoms:**
Pipeline takes several minutes for >20 metabolites

**Solution:**
```python
# Reports auto-limit to 10 metabolites
# For >20, batch your analysis:

all_metabolites = ["compound1", "compound2", ..., "compound50"]
batch_size = 10

for i in range(0, len(all_metabolites), batch_size):
    batch = all_metabolites[i:i+batch_size]
    metabolomics_analysis_pipeline(
        metabolite_list=batch,
        output_file=f"batch_{i//batch_size + 1}.md"
    )
```

---

## Testing Your Setup

Run the included test suite to verify everything works:

```bash
cd skills/tooluniverse-metabolomics
python test_skill.py
```

Expected output:
```
================================================================================
METABOLOMICS SKILL TEST SUITE
================================================================================
✅ Test 1 PASSED: test1_metabolites.md
✅ Test 2 PASSED: test2_study.md
✅ Test 3 PASSED: test3_search.md
✅ Test 4 PASSED: test4_comprehensive.md

PASS RATE: 4/4 (100%)
✅ ALL TESTS PASSED - Skill is ready to use!
```

---

## Additional Resources

- **ToolUniverse Documentation**: https://github.com/mims-harvard/ToolUniverse
- **HMDB Database**: https://hmdb.ca
- **MetaboLights**: https://www.ebi.ac.uk/metabolights/
- **Metabolomics Workbench**: https://www.metabolomicsworkbench.org
- **PubChem**: https://pubchem.ncbi.nlm.nih.gov

For issues or questions, see the ToolUniverse GitHub repository.
