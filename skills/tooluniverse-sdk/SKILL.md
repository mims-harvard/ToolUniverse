---
name: tooluniverse-sdk
description: Build AI scientist systems using ToolUniverse Python SDK for scientific research. Use when users need to access 1000++ scientific tools through Python code, create scientific workflows, perform drug discovery, protein analysis, genomics analysis, literature research, or any computational biology task. Triggers include requests to use scientific tools programmatically, build research pipelines, analyze biological data, search literature, predict drug properties, or create AI-powered scientific workflows.
---

# ToolUniverse Python SDK

**3 calling patterns -- start with pattern 1:**
1. `tu.run({"name": ..., "arguments": ...})` -- single tool call, dict API (most portable)
2. `tu.tools.ToolName(param=value)` -- function API (recommended for interactive use)
3. Direct class instantiation -- advanced, bypasses caching/hooks

## Installation

```bash
pip install tooluniverse              # Standard
pip install tooluniverse[embedding]   # Embedding search (GPU)
pip install tooluniverse[all]         # All features
```

```bash
export OPENAI_API_KEY="sk-..."  # Required for LLM tool search
export NCBI_API_KEY="..."       # Optional
```

## Quick Start

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()  # REQUIRED before any tool call

# Find tools
tools = tu.run({"name": "Tool_Finder_Keyword", "arguments": {"description": "protein structure", "limit": 10}})

# Execute (dict API)
result = tu.run({"name": "UniProt_get_entry_by_accession", "arguments": {"accession": "P05067"}})

# Execute (function API)
result = tu.tools.UniProt_get_entry_by_accession(accession="P05067")
```

## Core Patterns

### Batch Execution

```python
calls = [
    {"name": "UniProt_get_entry_by_accession", "arguments": {"accession": "P05067"}},
    {"name": "UniProt_get_entry_by_accession", "arguments": {"accession": "P12345"}},
]
results = tu.run_batch(calls)
```

### Scientific Workflow

```python
def drug_discovery_pipeline(disease_id):
    tu = ToolUniverse(use_cache=True)
    tu.load_tools()
    try:
        targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=disease_id)
        compound_calls = [
            {"name": "ChEMBL_search_molecule_by_target",
             "arguments": {"target_id": t['id'], "limit": 10}}
            for t in targets['data'][:5]
        ]
        compounds = tu.run_batch(compound_calls)
        return {"targets": targets, "compounds": compounds}
    finally:
        tu.close()
```

## Configuration

```python
# Caching
tu = ToolUniverse(use_cache=True)
stats = tu.get_cache_stats()
tu.clear_cache()

# Hooks (auto-summarization of large outputs)
tu = ToolUniverse(hooks_enabled=True)

# Load specific categories
tu.load_tools(categories=["proteins", "drugs"])
```

## Critical Notes

1. **Always call `load_tools()`** before using any tools
2. **Tool Finder returns nested structure**: access via `tools['tools']` after `isinstance(tools, dict)` check
3. **Tool names are case-sensitive**: `UniProt_get_entry_by_accession` not `uniprot_get_...`
4. **Check required params**: `tu.all_tool_dict["ToolName"]['parameter'].get('required', [])`
5. **Cache deterministic calls** (ML predictions, DB queries); don't cache real-time data

## Error Handling

```python
from tooluniverse.exceptions import ToolError, ToolUnavailableError, ToolValidationError

try:
    result = tu.tools.some_tool(param="value")
except ToolUnavailableError:
    ...  # Tool service down
except ToolValidationError as e:
    tool_info = tu.all_tool_dict["some_tool"]
    print(f"Required: {tool_info['parameter'].get('required', [])}")
```

## Tool Categories

| Category | Tools | Use Cases |
|----------|-------|-----------|
| Proteins | UniProt, RCSB PDB, AlphaFold | Protein analysis, structure |
| Drugs | DrugBank, ChEMBL, PubChem | Drug discovery, compounds |
| Genomics | Ensembl, NCBI Gene, gnomAD | Gene analysis, variants |
| Diseases | OpenTargets, ClinVar | Disease-target associations |
| Literature | PubMed, Europe PMC | Literature search |
| ML Models | ADMET-AI, AlphaFold | Predictions, modeling |
| Pathways | KEGG, Reactome | Pathway analysis |

## Resources

- **Docs**: https://zitniklab.hms.harvard.edu/ToolUniverse/
- **GitHub**: https://github.com/mims-harvard/ToolUniverse
- See [REFERENCE.md](REFERENCE.md) for detailed guides.
