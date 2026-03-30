---
name: find-tools
description: Search ToolUniverse for scientific research tools by topic or keyword. Use when you need to discover which tools are available for a research task.
argument-hint: "[search query, e.g. 'protein structure', 'GWAS variants', 'drug interactions']"
---

Search ToolUniverse for tools matching: $ARGUMENTS

Use the `find_tools` MCP tool with the query. Present results as a concise table: tool name, one-line description.

After finding tools, use the **CLI** to actually call them (more efficient than MCP execute_tool):
```bash
tu run <tool_name> '{"param": "value"}'
```

Or in Python for batch operations:
```python
import subprocess, json
result = subprocess.run(["tu", "run", "tool_name", json.dumps({"param": "value"})],
                        capture_output=True, text=True)
print(result.stdout)
```

**Common tools you can skip discovery for:**
- Cancer: `IntOGen_get_drivers`, `GDC_get_mutation_frequency`, `GDC_get_ssm_by_gene`
- Drugs: `DGIdb_get_drug_gene_interactions`, `OpenFDA_search_drug_approvals`
- Literature: `PubMed_search_articles`, `EuropePMC_search_articles`
- Genes: `UniProt_search`, `NCBI_search_gene`, `Ensembl_lookup_gene`
- Variants: `ClinVar_search_variants`, `OncoKB_annotate_variant`
- Pathways: `KEGG_search`, `Reactome_search_pathways`, `STRING_get_interaction_partners`
