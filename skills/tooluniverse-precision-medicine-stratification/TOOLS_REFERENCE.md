# Precision Medicine Stratification - Tools Reference

## Tools Used by Phase

### Phase 1: Disease Disambiguation & Profile Standardization
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `OpenTargets_get_disease_id_description_by_name` | `diseaseName` | `{data: {search: {hits: [{id, name, description}]}}}` | Resolve disease to EFO ID |
| `MyGene_query_genes` | `query` (NOT `q`) | `{hits: [{_id, symbol, name, ensembl: {gene}}]}` | Resolve gene to Ensembl/Entrez IDs |
| `ensembl_lookup_gene` | `gene_id`, `species='homo_sapiens'` | `{data: {id, display_name, description, biotype}}` | Gene details (REQUIRES species) |
| `ols_search_terms` | `query`, `ontology` | Ontology terms | Disease ontology resolution |
| `OpenTargets_get_disease_ids_by_name` | `diseaseName` | Disease cross-references | ICD-10, MONDO, OMIM mappings |

### Phase 2: Genetic Risk Assessment
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `clinvar_search_variants` | `gene`, `significance`, `limit` | Variant list with clinical significance | Pathogenic variant search |
| `clinvar_get_variant_details` | `variant_id` | Full variant details | Specific variant pathogenicity |
| `clinvar_get_clinical_significance` | `variant_id` | Clinical significance classification | Quick pathogenicity check |
| `EnsemblVEP_annotate_rsid` | `variant_id` (NOT `rsid`) | VEP annotation with SIFT/PolyPhen | Variant impact prediction |
| `EnsemblVEP_annotate_hgvs` | `hgvs_notation`, `species` | VEP annotation | HGVS variant annotation |
| `OpenTargets_target_disease_evidence` | `ensemblId`, `efoId`, `size` | Evidence items with scores | Gene-disease evidence strength |
| `gwas_get_associations_for_trait` | `trait` | GWAS associations | Disease-SNP associations |
| `gwas_search_associations` | `query` | GWAS associations | Broad GWAS search |
| `GWAS_search_associations_by_gene` | `gene_name` | Gene-trait associations | Gene-specific GWAS hits |
| `gwas_get_snps_for_gene` | `gene` | Associated SNPs | Gene GWAS variants |
| `OpenTargets_search_gwas_studies_by_disease` | `diseaseIds` (array), `size` | `{data: {studies: {count, rows}}}` | Disease GWAS studies |
| `gnomad_get_variant` | `variant_id` | Allele frequencies | Population frequency |
| `gnomad_get_gene_constraints` | `gene_symbol` | pLI, LOEUF scores | Gene constraint/intolerance |

### Phase 3: Disease-Specific Stratification

#### Cancer Tools
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `cBioPortal_get_mutations` | `study_id`, `gene_list` (STRING) | `{status, data: [...]}` | Somatic mutation landscape |
| `HPA_get_cancer_prognostics_by_gene` | `gene_name` | Prognostic data | Cancer prognosis markers |
| `fda_pharmacogenomic_biomarkers` | `drug_name`, `biomarker`, `limit` | `{count, shown, results}` | TMB-H, MSI-H FDA approvals |
| `civic_search_variants` | `name`, `gene_name` | `{data: {variants: {nodes}}}` | Variant clinical significance |
| `civic_search_evidence_items` | `therapy_name`, `disease_name` | `{data: {evidenceItems: {nodes}}}` | Biomarker-drug evidence |

#### Metabolic/CVD Tools
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `OpenTargets_get_associated_targets_by_disease_efoId` | `efoId`, `size` | Target associations | Disease genetic architecture |

#### Rare Disease Tools
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `UniProt_get_disease_variants_by_accession` | `accession` | Disease variants | Known pathogenic variants |
| `UniProt_get_function_by_accession` | `accession` | List of strings | Protein function |

### Phase 4: Pharmacogenomic Profiling
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `PharmGKB_get_clinical_annotations` | `query` | Clinical annotations | Drug-gene-phenotype PGx |
| `PharmGKB_get_dosing_guidelines` | `query` | Dosing guidelines | CPIC dosing recommendations |
| `PharmGKB_search_variants` | `query` | Variant PGx data | PGx variant annotations |
| `PharmGKB_get_gene_details` | `query` | Gene PGx details | PGx gene information |
| `PharmGKB_get_drug_details` | `query` | Drug PGx details | Drug PGx profile |
| `fda_pharmacogenomic_biomarkers` | `drug_name`, `biomarker`, `limit` | `{count, shown, results}` | FDA PGx biomarker labels |
| `FDA_get_pharmacogenomics_info_by_drug_name` | `drug_name`, `limit` | `{meta, results}` | FDA PGx label text |
| `OpenTargets_drug_pharmacogenomics_data` | `chemblId` | PGx data | OpenTargets PGx |

### Phase 5: Comorbidity & Drug Interaction Risk
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `drugbank_get_drug_interactions_by_drug_name_or_id` | `query`, `case_sensitive`, `exact_match`, `limit` | DDI data | Drug-drug interactions |
| `FDA_get_drug_interactions_by_drug_name` | `drug_name`, `limit` | `{meta, results}` | FDA DDI info |
| `FDA_get_contraindications_by_drug_name` | `drug_name`, `limit` | `{meta, results}` | Contraindications |
| `PubMed_search_articles` | `query`, `max_results` | List of dicts | Comorbidity literature |

### Phase 6: Molecular Pathway Analysis
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `enrichr_gene_enrichment_analysis` | `gene_list` (array), `libs` (array, REQUIRED) | Enrichment results | Pathway enrichment |
| `ReactomeAnalysis_pathway_enrichment` | `identifiers` (space-separated string) | `{data: {pathways: [...]}}` | Reactome enrichment |
| `Reactome_map_uniprot_to_pathways` | `id` (UniProt accession) | List of pathways | Gene-to-pathway mapping |
| `STRING_get_interaction_partners` | `protein_ids` (array), `species` (9606), `limit` | Interactions | PPI network |
| `STRING_functional_enrichment` | `protein_ids` (array), `species` (9606) | Functional enrichment | Network biology |
| `OpenTargets_get_target_tractability_by_ensemblID` | `ensemblId` | Tractability scores | Druggability assessment |

### Phase 7: Clinical Evidence & Guidelines
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `PubMed_Guidelines_Search` | `query`, `max_results` | List of guideline articles | Clinical guidelines |
| `PubMed_search_articles` | `query`, `max_results` | List of dicts | Literature evidence |
| `OpenTargets_get_associated_drugs_by_disease_efoId` | `efoId`, `size` | `{data: {disease: {knownDrugs: {count, rows}}}}` | Disease drug landscape |
| `FDA_get_indications_by_drug_name` | `drug_name`, `limit` | `{meta, results}` | FDA-approved indications |
| `FDA_get_mechanism_of_action_by_drug_name` | `drug_name`, `limit` | `{meta, results}` | Drug mechanism |
| `FDA_get_clinical_studies_info_by_drug_name` | `drug_name`, `limit` | `{meta, results}` | Clinical study data |
| `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | `chemblId` | `{data: {drug: {mechanismsOfAction: {rows}}}}` | Drug MOA |
| `drugbank_get_drug_basic_info_by_drug_name_or_id` | `query`, `case_sensitive`, `exact_match`, `limit` | Drug info | Drug details |
| `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` | `query`, `case_sensitive`, `exact_match`, `limit` | Pharmacology | Drug pharmacology |
| `civic_search_assertions` | `therapy_name`, `disease_name` | `{data: {assertions: {nodes}}}` | Clinical assertions |

### Phase 8: Clinical Trial Matching
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `clinical_trials_search` | `action='search_studies'`, `condition`, `intervention`, `limit` | `{total_count, studies}` | Trial search |
| `search_clinical_trials` | `query_term` (REQUIRED), `condition`, `intervention`, `pageSize` | `{studies, total_count}` | Alternative trial search |
| `clinical_trials_get_details` | `action='get_study_details'`, `nct_id` | Full study | Trial details |
| `get_clinical_trial_eligibility_criteria` | `nct_ids` (array), `eligibility_criteria='all'` | Eligibility criteria | Biomarker eligibility |

## Total Tool Count

| Phase | Tools | Category |
|-------|-------|----------|
| Phase 1: Disease Disambiguation | 5 | OpenTargets, MyGene, Ensembl, OLS |
| Phase 2: Genetic Risk | 13 | ClinVar, VEP, GWAS, gnomAD, OpenTargets |
| Phase 3: Disease Stratification | 5-8 | cBioPortal, HPA, FDA, CIViC, UniProt |
| Phase 4: Pharmacogenomics | 8 | PharmGKB, FDA PGx, OpenTargets |
| Phase 5: Comorbidity/DDI | 4 | DrugBank, FDA, PubMed |
| Phase 6: Pathways | 6 | Enrichr, Reactome, STRING, OpenTargets |
| Phase 7: Evidence/Guidelines | 10 | PubMed, OpenTargets, FDA, DrugBank, CIViC |
| Phase 8: Clinical Trials | 4 | ClinicalTrials.gov |
| **Total unique tools** | **~55** | **13 databases** |
