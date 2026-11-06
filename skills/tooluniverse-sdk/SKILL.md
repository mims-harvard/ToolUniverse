---
name: tooluniverse-sdk
description: Build AI scientist systems with the ToolUniverse Python SDK for scientific research. Covers the 3 calling patterns (`tu.run` portable dict API, `tu.tools.X` function API, direct class instantiation), tool loading, batch execution, MCP server integration, and embedding-based tool search. Use for SDK programming, custom tool composition, benchmarking pipelines, and integrating ToolUniverse into research workflows.
disable-model-invocation: true
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
    tu = ToolUniverse()
    tu.load_tools()
    try:
        targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=disease_id)
        # ChEMBL takes ChEMBL target IDs, not the Ensembl IDs in `targets`;
        # map them first (e.g. via ChEMBL_search_targets). Example IDs: EGFR, COX-2
        chembl_target_ids = ["CHEMBL203", "CHEMBL230"]
        compound_calls = [
            {"name": "ChEMBL_search_activities",
             "arguments": {"target_chembl_id": tid, "limit": 10}}
            for tid in chembl_target_ids
        ]
        compounds = tu.run_batch(compound_calls)
        return {"targets": targets, "compounds": compounds}
    finally:
        tu.close()
```

## Configuration

```python
# Caching: opt in per call (use_cache is a framework option on tools.X(...),
# not an argument to ToolUniverse() or to the tool itself)
tu = ToolUniverse()
result = tu.tools.some_tool(param="value", use_cache=True)
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

A failed call **returns** its error; it does not raise. The classes in
`tooluniverse.exceptions` never reach the caller — every calling pattern
(`tu.run`, `tu.tools.X`, the generated wrappers, and their `await` forms)
converts them into the dict below. Wrapping a call in
`except ToolValidationError` catches nothing and the error is then used as if
it were data.

```python
result = tu.tools.some_tool(param="value")

if isinstance(result, dict) and result.get("status") == "error":
    details = result.get("error_details", {})
    kind = details.get("type")          # e.g. "ToolValidationError"
    print(result["error"])
    print(details.get("next_steps"))    # suggested actions
    if details.get("retriable"):
        ...                             # worth another attempt
    if kind == "ToolValidationError":
        tool_info = tu.all_tool_dict["some_tool"]
        print(f"Required: {tool_info['parameter'].get('required', [])}")
```

The one exception that does reach you is `AttributeError`, raised by `tu.tools`
for a tool name that does not exist — not by the call itself.

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
