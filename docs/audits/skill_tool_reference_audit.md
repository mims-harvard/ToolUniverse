# Skill audit: tool references not found in the registry

Harness Rounds 015-016. Case mismatches and unambiguous renames already fixed.
What remains is a mix of genuinely-absent tools, semantic-shift renames, and
illustrative pseudo-names that need per-skill human judgment (a wrong guess maps
a skill onto the wrong real tool, which is worse than an obviously-fake name).

Remaining distinct: 89

| count | reference | example skills |
|---|---|---|
| 8 | `clinical_trials_search` | tooluniverse-clinical-trial-matching, tooluniverse-precision-medicine-stratification, tooluniverse-spatial-omics-analysis |
| 6 | `PubChem_get_bioactivity_summary_by_CID` | tooluniverse, tooluniverse-drug-research |
| 5 | `emdb_search` | tooluniverse-binder-discovery, tooluniverse-protein-therapeutic-design |
| 5 | `PubChem_get_drug_label_info_by_CID` | tooluniverse, tooluniverse-drug-research |
| 4 | `NCBI_Taxonomy_search` | tooluniverse-infectious-disease |
| 4 | `Reactome_search_pathway` | tooluniverse-infectious-disease, tooluniverse-pharmacovigilance |
| 4 | `gnomAD_get_variant_frequencies` | tooluniverse-rare-disease-diagnosis |
| 3 | `UniProt_get_protein_sequence` | tooluniverse-infectious-disease, tooluniverse-precision-oncology, tooluniverse-protein-therapeutic-design |
| 3 | `chembl_target_id` | tooluniverse-binder-discovery |
| 3 | `getting_started` | devtu-docs-quality |
| 3 | `drugbank_get_drug_by_name` | create-tooluniverse-skill |
| 3 | `get_clinical_trial_by_nct_id` | tooluniverse-infectious-disease, tooluniverse-pharmacovigilance, tooluniverse-precision-oncology |
| 3 | `DepMap_get_drug_response` | tooluniverse-precision-oncology, tooluniverse-target-research |
| 3 | `clinical_trials_get_details` | tooluniverse-clinical-trial-matching, tooluniverse-precision-medicine-stratification |
| 3 | `FDA_get_drug_approval_history` | tooluniverse-clinical-trial-design |
| 3 | `OpenTargets_get_target` | tooluniverse-crispr-screen-analysis |
| 2 | `emdb_get_entry` | tooluniverse-protein-therapeutic-design |
| 2 | `Ensembl_get_gene_info` | tooluniverse-variant-interpretation |
| 2 | `ChEMBL_get_bioactivity_by_chemblid` | tooluniverse |
| 2 | `GtoPdb_list_diseases` | tooluniverse, tooluniverse-target-research |
| 2 | `list_built_in_tools` | devtu-docs-quality |
| 2 | `get_tool_by_name` | devtu-docs-quality |
| 2 | `MyGene_get_gene_by_id` | tooluniverse-precision-oncology, tooluniverse-rare-disease-diagnosis |
| 2 | `HPA_get_gene_expression` | tooluniverse-rare-disease-diagnosis |
| 2 | `reactome_search_pathways` | tooluniverse-rare-disease-diagnosis |
| 2 | `Pfam_get_domains` | tooluniverse-rare-disease-diagnosis |
| 2 | `Gene_Ontology_get_term_info` | tooluniverse-structural-variant-analysis |
| 2 | `FAERS_get_event_details` | tooluniverse-pharmacovigilance |
| 2 | `max_annotate` | tooluniverse-variant-analysis |
| 2 | `MAP_dispersions` | tooluniverse-rnaseq-deseq2 |
| 1 | `pdbe_get_experiment_info` | tooluniverse-protein-structure-retrieval |
| 1 | `PubMed_get_abstract` | tooluniverse-variant-interpretation |
| 1 | `EuropePMC_get_article` | tooluniverse |
| 1 | `annotate_peaks_to_genes` | tooluniverse-epigenomics |
| 1 | `find_overlaps` | tooluniverse-epigenomics |
| 1 | `MyAPI_search` | tooluniverse-custom-tool |
| 1 | `run_one_function` | devtu-docs-quality |
| 1 | `get_tool_types` | devtu-docs-quality |
| 1 | `list_guidelines` | devtu-self-evolve |
| 1 | `map_uniprot_to_pathways` | create-tooluniverse-skill |
| 1 | `enrichr_submit_genes` | create-tooluniverse-skill |
| 1 | `OpenTargets_get_associated_targets` | tooluniverse-drug-repurposing |
| 1 | `miRBase_get_mature_mirna` | tooluniverse-noncoding-rna |
| 1 | `use_fine_mapping` | tooluniverse-gwas-trait-to-gene |
| 1 | `get_drug_details` | devtu-create-tool |
| 1 | `FDA_get_drug_info` | devtu-create-tool |
| 1 | `FDA_get_detailed_information_about_drug` | devtu-create-tool |
| 1 | `predicted_velocities` | tooluniverse-enzyme-kinetics |
| 1 | `NCBI_Taxonomy_get_by_id` | tooluniverse-infectious-disease |
| 1 | `NCBI_Taxonomy_get_lineage` | tooluniverse-infectious-disease |
| 1 | `DrugBank_get_drug` | tooluniverse-infectious-disease |
| 1 | `DrugBank_get_targets` | tooluniverse-infectious-disease |
| 1 | `gnomad_search_variants_genes` | tooluniverse-target-research |
| 1 | `GtoPdb_get_target` | tooluniverse-target-research |
| 1 | `GtoPdb_get_targets` | tooluniverse-target-research |
| 1 | `GtoPdb_search_interactions` | tooluniverse-target-research |
| 1 | `GtoPdb_get_disease` | tooluniverse-target-research |
| 1 | `ChEMBL_get_assays` | tooluniverse-drug-research |
| 1 | `gnomAD_search_gene_variants` | tooluniverse-clinical-trial-design |
| 1 | `gnomAD_get_variant_details` | tooluniverse-clinical-trial-design |
| 1 | `HPO_get_term_genes` | tooluniverse-rare-disease-diagnosis |
| 1 | `HPO_get_term_diseases` | tooluniverse-rare-disease-diagnosis |
| 1 | `OpenTargets_get_disease_info_by_efoId` | tooluniverse-rare-disease-diagnosis |
| 1 | `OpenTargets_get_associated_diseases_by_target_ensemblId` | tooluniverse-rare-disease-diagnosis |
| 1 | `ExAC_get_constraint_metrics` | tooluniverse-rare-disease-diagnosis |
| 1 | `ClinVar_get_variant_classifications` | tooluniverse-rare-disease-diagnosis |
| 1 | `gnomAD_get_variant_annotations` | tooluniverse-rare-disease-diagnosis |
| 1 | `UniProt_get_protein_features` | tooluniverse-rare-disease-diagnosis |
| 1 | `OpenTargets_diseases` | tooluniverse-rare-disease-diagnosis |
| 1 | `OpenTargets_pathways` | tooluniverse-rare-disease-diagnosis |
| 1 | `DailyMed_get_drug_interactions` | tooluniverse-pharmacovigilance |
| 1 | `FAERS_search_by_drug` | tooluniverse-pharmacovigilance |
| 1 | `FAERS_get_demographics` | tooluniverse-pharmacovigilance |
| 1 | `OpenFDA_get_drug_recalls` | tooluniverse-pharmacovigilance |
| 1 | `OpenFDA_get_enforcement` | tooluniverse-pharmacovigilance |
| 1 | `PharmGKB_get_drug_labels` | tooluniverse-pharmacovigilance |
| 1 | `get_clinical_trial_results` | tooluniverse-pharmacovigilance |
| 1 | `OpenFDA_get_drug_labels` | tooluniverse-pharmacovigilance |
| 1 | `FDA_drug_search` | tooluniverse-pharmacovigilance |
| 1 | `cBioPortal_get_sample_clinical_data` | tooluniverse-precision-oncology |
| 1 | `cBioPortal_get_patient_clinical_data` | tooluniverse-precision-oncology |
| 1 | `Rare_Diseases_GeneRIF_Gene_Lists` | tooluniverse-gene-enrichment |
| 1 | `DGIdb_Drug_Targets_2024` | tooluniverse-gene-enrichment |
| 1 | `DepMap_CRISPR_GeneDependency_CellLines_2023` | tooluniverse-gene-enrichment |
| 1 | `analyze_gene_essentiality` | tooluniverse-crispr-screen-analysis |
| 1 | `uniprot_search_proteins` | tooluniverse-proteomics-analysis |
| 1 | `SASBDB_get_models` | tooluniverse-protein-interactions |
| 1 | `SASBDB_get_scattering_profile` | tooluniverse-protein-interactions |
| 1 | `analyze_protein_network` | tooluniverse-protein-interactions |
