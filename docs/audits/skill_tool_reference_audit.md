# Skill audit: remaining tool references not in the registry

Harness Rounds 015-020. Resolved 105 references and built 5 gap-filling tools (HPO
phenotype->genes/diseases, GtoPdb diseases, OpenTargets target-info, UniProt features).
Every remaining item is NOT an actionable rename or buildable tool: they are non-tool
tokens (pipeline/function names, gene-set library values, dev-SDK references) or a
capability backed by bulk-download data rather than an API.

Remaining: 24

## Enrichr gene-set library name (a `library` argument value, not a tool)

- `Rare_Diseases_GeneRIF_Gene_Lists` (1x) — tooluniverse-gene-enrichment
- `DGIdb_Drug_Targets_2024` (1x) — tooluniverse-gene-enrichment
- `DepMap_CRISPR_GeneDependency_CellLines_2023` (1x) — tooluniverse-gene-enrichment

## SDK/meta reference in a developer skill (not a research tool)

- `getting_started` (3x) — devtu-docs-quality
- `list_built_in_tools` (2x) — devtu-docs-quality
- `get_tool_by_name` (2x) — devtu-docs-quality
- `MyAPI_search` (1x) — tooluniverse-custom-tool
- `run_one_function` (1x) — devtu-docs-quality
- `get_tool_types` (1x) — devtu-docs-quality
- `list_guidelines` (1x) — devtu-self-evolve

## capability absent from TU

- `FDA_get_drug_info` (1x) — devtu-create-tool
- `FDA_get_detailed_information_about_drug` (1x) — devtu-create-tool

## needs bulk data, not a REST API (GDSC drug sensitivity is download-only)

- `DepMap_get_drug_response` (3x) — tooluniverse-precision-oncology, tooluniverse-target-research

## pipeline-step / local-function name in a script (not a TU tool call)

- `chembl_target_id` (3x) — tooluniverse-binder-discovery
- `max_annotate` (2x) — tooluniverse-variant-analysis
- `MAP_dispersions` (2x) — tooluniverse-rnaseq-deseq2
- `annotate_peaks_to_genes` (1x) — tooluniverse-epigenomics
- `find_overlaps` (1x) — tooluniverse-epigenomics
- `map_uniprot_to_pathways` (1x) — create-tooluniverse-skill
- `use_fine_mapping` (1x) — tooluniverse-gwas-trait-to-gene
- `get_drug_details` (1x) — devtu-create-tool
- `predicted_velocities` (1x) — tooluniverse-enzyme-kinetics
- `analyze_gene_essentiality` (1x) — tooluniverse-crispr-screen-analysis
- `analyze_protein_network` (1x) — tooluniverse-protein-interactions

