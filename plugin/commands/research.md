---
name: research
description: Answer a scientific research question using ToolUniverse databases. Automatically routes to the right tools, cross-validates findings, and reports with actual data. Use this for any biology, chemistry, medicine, or data science question.
argument-hint: "[your research question]"
---

Answer this scientific research question using ToolUniverse MCP tools: $ARGUMENTS

## Instructions

1. **Do NOT spawn subagents** — use MCP tools directly in this conversation.
2. **Plan first**: List ALL tool calls you'll need BEFORE making any. Write them out as a numbered list.
3. **Call tools directly** — skip `find_tools` for common tools (see Quick Reference below). Only use `find_tools` for niche domains.
4. **BATCH queries via Python**: For multiple items (5 genes, 3 drugs), write a Python script — do NOT make them one-by-one:
   ```python
   # Run via Bash — this replaces 5 sequential execute_tool calls with 1 script
   import subprocess, json
   genes = ["TP53", "PIK3CA", "GATA3", "KMT2C", "CDH1"]
   for g in genes:
       r = subprocess.run(["tu", "run", "GDC_get_mutation_frequency", json.dumps({"gene_symbol": g})],
                          capture_output=True, text=True)
       print(f"{g}: {r.stdout[:200]}")
   ```
5. **Cross-validate**: Check 2+ sources for key claims. Flag any disagreements.
6. **Limit results**: Always pass `size=10` or `limit=5` to avoid truncation.
7. **Avoid trial-and-error**: Use `get_tool_info("tool_name")` ONCE to check parameters before calling, rather than guessing and retrying.

## Tool Quick Reference (with example parameters)

**Cancer/Genomics:**
- `IntOGen_get_drivers` — `{"cancer_type": "BRCA"}` → top driver genes
- `GDC_get_mutation_frequency` — `{"gene_symbol": "TP53"}` → pan-cancer frequency
- `GDC_get_ssm_by_gene` — `{"gene_symbol": "TP53", "project_id": "TCGA-BRCA", "size": 10}`
- `GDC_get_clinical_data` — `{"project_id": "TCGA-BRCA", "size": 10}`
- `GDC_get_survival` — `{"project_id": "TCGA-BRCA", "gene_symbol": "TP53"}`
- `OncoKB_annotate_variant` — `{"operation": "annotate_variant", "gene": "PIK3CA", "variant": "H1047R", "tumor_type": "Breast Cancer"}`

**Drugs:**
- `DGIdb_get_drug_gene_interactions` — `{"genes": ["TP53", "PIK3CA"]}` → batch multiple genes
- `OpenFDA_search_drug_approvals` — `{"operation": "search_approvals", "drug_name": "alpelisib", "limit": 3}`
- `OpenTargets_get_asso_drug_by_targ_ense` — `{"ensemblId": "ENSG00000121879", "size": 10}` (use Ensembl ID, not gene symbol)
- `ChEMBL_search_compounds` — `{"query": "metformin", "limit": 5}`

**Literature:**
- `PubMed_search_articles` — `{"query": "BRCA1 resistance therapy", "max_results": 10}`
- `EuropePMC_search_articles` — `{"query": "BRCA1 resistance", "limit": 10}`

**Genes/Proteins:**
- `UniProt_search` — `{"query": "BRCA1", "organism": "human", "limit": 5}`
- `NCBI_search_gene` — `{"query": "TP53", "organism": "human"}`
- `Ensembl_lookup_gene` — `{"gene_symbol": "TP53", "species": "homo_sapiens"}`

**Variants:**
- `ClinVar_search_variants` — `{"query": "BRCA1", "limit": 10}`
- `CIViC_search_variants` — `{"gene_symbol": "BRAF"}`
- `gnomAD_search_variants` — `{"gene_symbol": "BRCA1"}`

**Pharmacogenomics:**
- `CPIC_list_guidelines` — `{"gene": "CYP2D6"}` or `{"drug": "codeine"}`
- `PharmGKB_search_variants` — `{"query": "CYP2D6"}`

**Clinical/Epidemiology:**
- `search_clinical_trials` — `{"query": "metformin breast cancer", "status": "RECRUITING", "limit": 10}`
- `NHANES_download_and_parse` — `{"component": "Demographics", "cycle": "2017-2018", "variables": ["SEQN", "RIDAGEYR"]}`

**Pathways:**
- `KEGG_search` — `{"query": "PI3K signaling", "database": "pathway"}`
- `Reactome_search_pathways` — `{"query": "PI3K AKT"}`
- `STRING_get_interaction_partners` — `{"identifier": "TP53", "species": 9606, "limit": 10}`

For anything not listed: `find_tools("your topic")` or `get_tool_info("tool_name")` to check parameters.
