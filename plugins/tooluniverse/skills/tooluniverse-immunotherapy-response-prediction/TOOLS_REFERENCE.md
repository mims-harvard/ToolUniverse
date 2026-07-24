# Immunotherapy Response Prediction - Tools Reference

## Tools Used by Phase

### Phase 1: Input Standardization & Cancer Context
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `OpenTargets_get_disease_id_description_by_name` | `diseaseName` | `{data: {search: {hits: [{id, name, description}]}}}` | Resolve cancer to EFO ID |
| `MyGene_query_genes` | `query` | `{hits: [{_id, symbol, name, ensembl: {gene}}]}` | Resolve gene to Ensembl/Entrez IDs |
| `ensembl_lookup_gene` | `gene_id`, `species='homo_sapiens'` | `{data: {id, display_name, description, biotype}}` | Gene details |

### Phase 2: TMB Analysis
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `fda_pharmacogenomic_biomarkers` | `drug_name`, `biomarker`, `limit` | `{count, shown, results: [{Drug, Biomarker, TherapeuticArea, LabelingSection}]}` | FDA TMB-H approvals |

### Phase 3: Neoantigen Analysis
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `UniProt_get_function_by_accession` | `accession` | List of strings | Protein function for neoantigen assessment |
| `iedb_search_epitopes` | `organism_name`, `source_antigen_name` | `{status, data, count}` | Known epitopes |
| `EnsemblVEP_annotate_rsid` | `variant_id` | VEP annotation with SIFT/PolyPhen | Variant impact |

### Phase 4: MSI/MMR Status
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `fda_pharmacogenomic_biomarkers` | `biomarker='Microsatellite Instability'`, `limit` | FDA MSI-H approvals | MSI-H drug approvals |

### Phase 5: PD-L1 Expression
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `HPA_get_cancer_prognostics_by_gene` | `gene_name='CD274'` | Cancer prognostic data | PD-L1 prognostic context |
| `HPA_get_rna_expression_by_source` | `gene_name`, `source_type`, `source_name` (ALL 3 required) | Expression data | Baseline expression |

### Phase 6: Immune Microenvironment
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `HPA_get_cancer_prognostics_by_gene` | `gene_name` | Cancer prognostics | Immune gene prognostics |
| `enrichr_gene_enrichment_analysis` | `gene_list` (array), `libs` (array, REQUIRED) | Enrichment results | Immune pathway analysis |

### Phase 7: Mutation-Based Predictors
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `cBioPortal_get_mutations` | `study_id`, `gene_list` (string!) | `{data: [{proteinChange, mutationType, studyId, ...}]}` | Mutation prevalence |

### Phase 8: Clinical Evidence & ICI Options
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `FDA_get_indications_by_drug_name` | `drug_name`, `limit` | `{meta, results}` | FDA-approved indications |
| `FDA_get_mechanism_of_action_by_drug_name` | `drug_name`, `limit` | `{meta, results}` | Drug mechanism |
| `FDA_get_clinical_studies_info_by_drug_name` | `drug_name`, `limit` | `{meta, results}` | Clinical study data |
| `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | `chemblId` | `{data: {drug: {mechanismsOfAction: {rows}}}}` | Drug MOA |
| `OpenTargets_get_associated_drugs_by_disease_efoId` | `efoId`, `size` | `{data: {disease: {knownDrugs: {count, rows}}}}` | Drugs for cancer |
| `OpenTargets_get_approved_indications_by_drug_chemblId` | `chemblId` | Approved indications | Drug approvals |
| `drugbank_get_drug_basic_info_by_drug_name_or_id` | `query`, `case_sensitive`, `exact_match`, `limit` (ALL 4) | Drug info | Drug details |
| `drugbank_get_targets_by_drug_name_or_drugbank_id` | `query`, `case_sensitive`, `exact_match`, `limit` (ALL 4) | Drug targets | ICI targets |
| `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` | `query`, `case_sensitive`, `exact_match`, `limit` (ALL 4) | Pharmacology | Drug pharmacology |
| `search_clinical_trials` | `condition`, `intervention`, `query_term`, `pageSize` | `{total_count, studies}` | Active ICI trials |
| `PubMed_search_articles` | `query`, `limit` | `{status, data, metadata}` | Literature evidence |

### Phase 9: Resistance Risk Assessment
| Tool | Parameters | Response | Purpose |
|------|-----------|----------|---------|
| `civic_search_evidence_items` | `therapy_name`, `disease_name` | `{data: {evidenceItems: {nodes}}}` | Resistance evidence |
| `gnomad_get_gene_constraints` | `gene_symbol` | Gene constraint metrics | Gene essentiality |

## Key ICI Drug Reference

| Drug | ChEMBL ID | DrugBank ID | Target |
|------|-----------|-------------|--------|
| Pembrolizumab | CHEMBL3137343 | DB09037 | PD-1 (PDCD1) |
| Nivolumab | CHEMBL2108738 | DB09035 | PD-1 (PDCD1) |
| Atezolizumab | CHEMBL3707227 | DB11595 | PD-L1 (CD274) |
| Durvalumab | CHEMBL3301587 | DB11714 | PD-L1 (CD274) |
| Ipilimumab | CHEMBL1789844 | DB06186 | CTLA-4 |
| Avelumab | CHEMBL3833373 | DB11945 | PD-L1 (CD274) |
| Cemiplimab | CHEMBL4297723 | DB14716 | PD-1 (PDCD1) |

## Key Gene IDs

| Gene | Ensembl ID | Entrez ID | UniProt | Role |
|------|-----------|-----------|---------|------|
| PDCD1 (PD-1) | ENSG00000188389 | 5133 | Q15116 | ICI target |
| CD274 (PD-L1) | ENSG00000120217 | 29126 | Q9NZQ7 | ICI target |
| CTLA4 | ENSG00000163599 | 1493 | P16410 | ICI target |
| BRAF | ENSG00000157764 | 673 | P15056 | Driver mutation |
| STK11 | ENSG00000118046 | 6794 | Q15831 | Resistance |
| PTEN | ENSG00000284792 | 5728 | P60484 | Resistance |
| JAK1 | ENSG00000162434 | 3716 | P23458 | Resistance |
| JAK2 | ENSG00000096968 | 3717 | O60674 | Resistance |
| B2M | ENSG00000166710 | 567 | P61769 | Resistance |
| KEAP1 | ENSG00000079999 | 9817 | Q14145 | Resistance |
| POLE | ENSG00000177084 | 5426 | Q07864 | Sensitivity |
| MLH1 | ENSG00000076242 | 4292 | P40692 | MMR |
| MSH2 | ENSG00000095002 | 4436 | P43246 | MMR |
| MSH6 | ENSG00000116062 | 2956 | P52701 | MMR |
| PMS2 | ENSG00000122512 | 5395 | P54278 | MMR |

## Common Parameter Mistakes

| Wrong | Correct | Tool |
|-------|---------|------|
| `q` | `query` | `MyGene_query_genes` |
| `rsid` | `variant_id` | `EnsemblVEP_annotate_rsid` |
| `gene_list=['BRAF']` | `gene_list='BRAF'` | `cBioPortal_get_mutations` |
| 3 params | ALL 4 params required | All `drugbank_*` tools |
| no `species` | `species='homo_sapiens'` | `ensembl_lookup_gene` |
| `genericName` | `drugName` | `OpenTargets_get_drug_id_description_by_name` |
