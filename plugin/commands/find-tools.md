---
name: find-tools
description: Search ToolUniverse for scientific research tools by topic or keyword. Use when you need to discover which tools are available for a research task.
argument-hint: "[search query, e.g. 'protein structure', 'GWAS variants', 'drug interactions']"
---

Search ToolUniverse for tools matching: $ARGUMENTS

Use the `find_tools` MCP tool with the query. Present results as a concise table: tool name, one-line description.

**Efficiency tip**: For common domains, you can skip this command and call tools directly:
- Cancer mutations: `IntOGen_get_drivers`, `GDC_get_mutation_frequency`, `GDC_get_ssm_by_gene`
- Drug lookups: `DGIdb_get_drug_gene_interactions`, `OpenFDA_search_drug_approvals`, `ChEMBL_search_compounds`
- Literature: `PubMed_search_articles`, `EuropePMC_search_articles`
- Genes/Proteins: `UniProt_search`, `NCBI_search_gene`, `Ensembl_lookup_gene`
- Variants: `ClinVar_search_variants`, `OncoKB_annotate_variant`, `CIViC_search_variants`
- Clinical trials: `search_clinical_trials`
- Pathways: `KEGG_search`, `Reactome_search_pathways`, `STRING_get_interaction_partners`

Only use `find_tools` when you need a tool outside these common ones.
