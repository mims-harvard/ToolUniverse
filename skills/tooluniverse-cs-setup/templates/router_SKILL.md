---
name: tooluniverse-research
description: Biomedical and scientific research via ToolUniverse's 2500+ tools across 133 structured workflows — drug research, disease research, gene and variant interpretation, cancer genomics, clinical trials, ADMET prediction, pharmacovigilance and adverse events, CRISPR screens, protein and structure analysis, epidemiology, and graded literature reviews. Use for "tell me about drug/gene/disease/variant X", multi-database investigations, cross-validating biomedical claims, ID translation, or any structured scientific lookup spanning FDA, ChEMBL, PubChem, ClinicalTrials.gov, UniProt, Ensembl, PubMed, and 200+ other databases.
---

# ToolUniverse Research

Brings ToolUniverse's 2500+ scientific tools and 133 structured research workflows into Claude Science. The `tooluniverse` PyPI package supplies the tools; this skill bundles the workflows and a kernel sidecar that wires them up.

## Setup

Run all cells in the **`tooluniverse`** conda environment. Loading this skill auto-defines these helpers in the kernel:

- `get_tu()` → a loaded `ToolUniverse` instance (cache redirected to the workspace, since `~/.tooluniverse` is read-only here).
- `tu_workflows()` → list all 133 workflows (`name` + `description`).
- `find_tu_workflow(query)` → rank workflows by relevance to a question.
- `tu_workflow(name)` → the full step-by-step procedure for one workflow.
- `tu_tool_info(tu, name)` → a tool's JSON spec, including its argument schema.

## Answering a research question

1. **Route** to a workflow: `find_tu_workflow("tell me about metformin")` returns ranked names. (Or browse `tu_workflows()`.)
2. **Load** its procedure: `print(tu_workflow("tooluniverse-drug-research"))` and follow the steps.
3. **Execute** the tools the workflow names. Every `ToolName(args)` reference maps to:
   ```python
   tu = get_tu()
   tu.run({"name": "PubChem_get_CID_by_compound_name",
           "arguments": {"name": "metformin"}})
   ```
4. **Confirm argument names** before a call if unsure — `tu_tool_info(tu, "PubChem_get_CID_by_compound_name")` shows the exact schema. Workflow prose abbreviates arguments; the schema is authoritative.
5. **Discover tools** at runtime when no workflow fits:
   ```python
   tu.run({"name": "Tool_Finder_Keyword",
           "arguments": {"description": "drug adverse events", "limit": 10}})
   ```

## Notes

- Most tools work without API keys. A few (NCBI, OncoKB, NVIDIA, …) unlock enhanced access when keys are set in the env — add under Customize → Credentials, then expose them in the `tooluniverse` env.
- Workflows are self-contained: report templates, checklists, and tool references are appended to each as appendices.
- These workflows emphasize *looking things up* over recalling them — when a workflow says query a database, run the tool rather than answering from memory.
