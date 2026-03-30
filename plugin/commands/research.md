---
name: research
description: Answer a scientific research question using ToolUniverse databases. Automatically routes to the right tools, cross-validates findings, and reports with actual data. Use this for any biology, chemistry, medicine, or data science question.
argument-hint: "[your research question]"
---

Answer this scientific research question using ToolUniverse MCP tools: $ARGUMENTS

## Instructions

## Execution Strategy: CLI First, MCP for Discovery

**Use MCP** (`find_tools`, `get_tool_info`) only for:
- Discovering which tools exist for an unfamiliar topic
- Checking a tool's parameter schema before first use

**Use CLI** (`tu run` via Bash) for all actual data retrieval:
- Faster: one Python script replaces 10+ sequential MCP calls
- Batchable: loop over genes/drugs/variants in code
- Composable: pipe output, save to files, merge with pandas

**Rules:**
1. **Do NOT spawn subagents** — work directly in this conversation.
2. **Plan first**: List ALL tools you need, then write ONE Python script that calls them all.
3. **Use `tu run` in Python** for all execute_tool work:
   ```python
   import subprocess, json

   def tu_run(tool_name, args):
       """Call a ToolUniverse tool via CLI and return parsed result."""
       r = subprocess.run(["tu", "run", tool_name, json.dumps(args)],
                          capture_output=True, text=True, timeout=60)
       return json.loads(r.stdout) if r.returncode == 0 else {"error": r.stderr[:200]}

   # Example: batch query 5 genes in one script
   genes = ["TP53", "PIK3CA", "GATA3", "KMT2C", "CDH1"]
   for g in genes:
       result = tu_run("GDC_get_mutation_frequency", {"gene_symbol": g})
       print(f"{g}: {json.dumps(result.get('data', {}), indent=2)[:300]}")
   ```
4. **Cross-validate**: Check 2+ sources for key claims.
5. **Limit results**: Always pass `size=10` or `limit=5`.
6. **Check params first**: If unsure about a tool's parameters, use MCP `get_tool_info("tool_name")` once, then use CLI for execution.

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
