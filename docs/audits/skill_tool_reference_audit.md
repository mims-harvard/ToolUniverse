# Skill audit: remaining tool references not in the registry

Harness Rounds 015-017. **94 references already fixed** (case mismatches +
verified renames). The remaining items below are NOT broken renames — they are,
by category, either not tool calls at all or capabilities TU genuinely lacks.
They are intentionally left as-is (renaming them would be wrong); listed here for
awareness / potential future tool-building.

Remaining: 39

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

## capability absent from TU (no equivalent tool to map to)

- `PubChem_get_drug_label_info_by_CID` (5x) — tooluniverse, tooluniverse-drug-research
- `DepMap_get_drug_response` (3x) — tooluniverse-precision-oncology, tooluniverse-target-research
- `OpenTargets_get_target` (3x) — tooluniverse-crispr-screen-analysis
- `Ensembl_get_gene_info` (2x) — tooluniverse-variant-interpretation
- `ChEMBL_get_bioactivity_by_chemblid` (2x) — tooluniverse
- `GtoPdb_list_diseases` (2x) — tooluniverse, tooluniverse-target-research
- `OpenTargets_get_associated_targets` (1x) — tooluniverse-drug-repurposing
- `FDA_get_drug_info` (1x) — devtu-create-tool
- `FDA_get_detailed_information_about_drug` (1x) — devtu-create-tool
- `GtoPdb_get_disease` (1x) — tooluniverse-target-research
- `ChEMBL_get_assays` (1x) — tooluniverse-drug-research
- `HPO_get_term_genes` (1x) — tooluniverse-rare-disease-diagnosis
- `HPO_get_term_diseases` (1x) — tooluniverse-rare-disease-diagnosis
- `UniProt_get_protein_features` (1x) — tooluniverse-rare-disease-diagnosis
- `OpenTargets_diseases` (1x) — tooluniverse-rare-disease-diagnosis
- `OpenTargets_pathways` (1x) — tooluniverse-rare-disease-diagnosis
- `FAERS_search_by_drug` (1x) — tooluniverse-pharmacovigilance
- `FDA_drug_search` (1x) — tooluniverse-pharmacovigilance

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

