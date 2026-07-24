# ToolUniverse Reference Guide

Detailed tool chains, fallback strategies, and examples for comprehensive scientific research.

## Complete Tool Chains by Use Case

### Use Case 1: Target/Protein Research

**Step 1: Resolve Target Identity**
- `UniProt_search` → Find UniProt entry for gene
- `MyGene_get_gene_annotation` → Get gene details and aliases
- `ensembl_lookup_gene` → Get Ensembl ID
- `UniProt_id_mapping` → Cross-map between ID types

**Step 2: Get Protein Details**
- `UniProt_get_entry_by_accession` → Full protein entry
- `UniProt_get_function_by_accession` → Function description
- `UniProt_get_subcellular_location_by_accession` → Localization
- `InterPro_get_protein_domains` → Domain architecture
- `UniProt_get_ptm_processing_by_accession` → Post-translational modifications

**Step 3: Get Structures**
- `alphafold_get_prediction` → AlphaFold predicted structure
- `get_protein_metadata_by_pdb_id` → Experimental PDB structures
- `pdbe_get_entry_summary` → PDB entry details

**Step 4: Get Function & Pathways**
- `GO_get_annotations_for_gene` → Gene Ontology terms
- `Reactome_map_uniprot_to_pathways` → Reactome pathways
- `kegg_get_gene_info` → KEGG pathways
- `OpenTargets_get_target_gene_ontology_by_ensemblID` → GO via Open Targets

**Step 5: Get Interactions**
- `STRING_get_protein_interactions` → Protein-protein interactions
- `intact_get_interactions` → IntAct experimental interactions
- `OpenTargets_get_target_interactions_by_ensemblID` → Open Targets PPI

**Step 6: Get Expression**
- `GTEx_get_median_gene_expression` → Tissue expression (GTEx)
- `HPA_get_rna_expression_by_source` → Human Protein Atlas RNA
- `HPA_get_subcellular_location` → HPA subcellular localization
- `HPA_get_comprehensive_gene_details_by_ensembl_id` → Full HPA data

**Step 7: Get Variants & Disease**
- `gnomad_get_gene_constraints` → Genetic constraint scores
- `gnomad_get_gene` → Population variants
- `ClinVar_search_variants` → Clinical variants
- `UniProt_get_disease_variants_by_accession` → Disease variants
- `OpenTargets_get_diseases_phenotypes_by_target_ensembl` → Disease associations

**Step 8: Get Drug Interactions**
- `OpenTargets_get_target_tractability_by_ensemblID` → Druggability assessment
- `DGIdb_get_gene_druggability` → DGIdb druggability
- `OpenTargets_get_associated_drugs_by_target_ensemblID` → Known drugs
- `ChEMBL_get_target_activities` → Bioactivity data
- `OpenTargets_get_target_safety_profile_by_ensemblID` → Safety liabilities

**Step 9: Get Literature**
- `PubMed_search_articles` → PubMed publications
- `OpenTargets_get_publications_by_target_ensemblID` → Target-specific papers

---

### Use Case 2: Drug/Compound Research

**Step 1: Resolve Compound Identity**
- `PubChem_get_CID_by_compound_name` → Get PubChem CID
- `ChEMBL_search_molecules` → Get ChEMBL ID
- `DailyMed_search_spls` → Check if approved drug
- `PharmGKB_search_drugs` → Get PharmGKB ID

**Step 2: Get Chemical Properties**
- `PubChem_get_compound_properties_by_CID` → Molecular properties
- `ADMETAI_predict_physicochemical_properties` → Predicted properties
- `ADMETAI_predict_solubility_lipophilicity_hydration` → Solubility data

**Step 3: Get Targets & Bioactivity**
- `ChEMBL_search_activities` → Bioactivity data
- `ChEMBL_get_target` → Target proteins
- `DGIdb_get_drug_info` → Drug-gene interactions
- `PubChem_get_compound_bioactivity` → PubChem bioactivity

**Step 4: Get ADMET Predictions**
- `ADMETAI_predict_bioavailability` → Absorption predictions
- `ADMETAI_predict_BBB_penetrance` → BBB penetration
- `ADMETAI_predict_CYP_interactions` → CYP metabolism
- `ADMETAI_predict_clearance_distribution` → Distribution/clearance
- `ADMETAI_predict_toxicity` → Toxicity predictions

**Step 5: Get Clinical Trials**
- `search_clinical_trials` → Find clinical trials
- `get_clinical_trial_conditions_and_interventions` → Trial details
- `extract_clinical_trial_outcomes` → Trial outcomes
- `extract_clinical_trial_adverse_events` → Safety data

**Step 6: Get Safety Data**
- `FAERS_count_reactions_by_drug_event` → Adverse events
- `FAERS_count_seriousness_by_drug_event` → Seriousness distribution
- `FAERS_count_outcomes_by_drug_event` → Outcome distribution
- `OpenTargets_get_drug_warnings_by_chemblId` → Drug warnings

**Step 7: Get Pharmacogenomics**
- `PharmGKB_get_drug_details` → PharmGKB drug info
- `PharmGKB_get_clinical_annotations` → Clinical annotations
- `PharmGKB_get_dosing_guidelines` → Dosing guidelines

---

### Use Case 3: Disease Research

**Step 1: Resolve Disease Identity**
- `OSL_get_efo_id_by_disease_name` → Get EFO ID
- `OpenTargets_get_disease_id_description_by_name` → Disease info
- `ols_search_efo_terms` → Search EFO ontology
- `umls_search_concepts` → UMLS concept
- `icd_search_codes` → ICD-10 code
- `snomed_search_concepts` → SNOMED CT

**Step 2: Get Phenotypes**
- `OpenTargets_get_associated_phenotypes_by_disease_efoId` → Phenotypes
- `get_HPO_ID_by_phenotype` → HPO terms
- `MedlinePlus_search_topics_by_keyword` → Patient info
- `MedlinePlus_get_genetics_condition_by_name` → Genetics info

**Step 3: Get Associated Genes**
- `OpenTargets_get_associated_targets_by_disease_efoId` → Associated genes
- `OpenTargets_target_disease_evidence` → Evidence details
- `ClinVar_search_variants` → Pathogenic variants

**Step 4: Get GWAS Associations**
- `gwas_search_associations` → GWAS hits
- `gwas_get_variants_for_trait` → Associated variants
- `gwas_get_associations_for_trait` → Association details
- `gwas_get_studies_for_trait` → GWAS studies

**Step 5: Get Treatment Options**
- `OpenTargets_get_associated_drugs_by_disease_efoId` → Approved/trial drugs
- `search_clinical_trials` → Clinical trials
- `GtoPdb_search_diseases` → Guide to Pharmacology

**Step 6: Get Pathways**
- `Reactome_get_diseases` → Disease pathways
- `Reactome_map_uniprot_to_pathways` → Protein pathways
- `humanbase_ppi_analysis` → Tissue-specific networks
- `geo_search_datasets` → Expression datasets

**Step 7: Get Literature**
- `PubMed_search_articles` → Publications
- `OpenTargets_get_publications_by_disease_efoId` → Disease papers
- `openalex_search_works` → OpenAlex literature

**Step 8: Get Similar Diseases**
- `OpenTargets_get_similar_entities_by_disease_efoId` → Similar diseases

---

## Complete Fallback Chains

### Literature Tools
| Primary | Fallback 1 | Fallback 2 | Fallback 3 |
|---------|------------|------------|------------|
| `PubMed_search_articles` | `EuropePMC_search_articles` | `openalex_search_works` | `SemanticScholar_search_papers` |
| `PubMed_get_cited_by` | `EuropePMC_get_citations` | OpenAlex citations | Manual search |
| `PubMed_get_related` | `EuropePMC_get_references` | SemanticScholar | Keyword expansion |
| `PubMed_get_article` | `EuropePMC_search_articles` | `Crossref_get_work` | - |

### Protein/Gene Tools
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `UniProt_get_entry_by_accession` | `proteins_api_get_protein` | NCBI protein |
| `UniProt_search` | `proteins_api_search` | MyGene search |
| `GTEx_get_median_gene_expression` | `HPA_get_rna_expression_by_source` | Document unavailable |
| `alphafold_get_prediction` | `alphafold_get_summary` | PDB experimental |

### Drug/Compound Tools
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `PubChem_get_CID_by_compound_name` | `ChEMBL_search_molecules` + SMILES → CID | Manual search |
| `ChEMBL_search_activities` | `PubChem_get_compound_bioactivity` | - |
| `DailyMed_search_spls` | `FDA_get_drug_label` | FDA label search |
| `ADMETAI_predict_*` | Document "Predictions unavailable" | - |

### Disease Tools
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `OSL_get_efo_id_by_disease_name` | `ols_search_efo_terms` | `OpenTargets_get_disease_id_description_by_name` |
| `ClinVar_search_variants` | `gnomad_get_gene` | OpenTargets variants |
| `gwas_search_associations` | `gwas_get_variants_for_trait` | OpenTargets GWAS |

### Clinical Tools
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `search_clinical_trials` | EudraCT search | Document unavailable |
| `FAERS_count_reactions_by_drug_event` | Document "FAERS unavailable" | - |
| `PharmGKB_get_dosing_guidelines` | Document "No guideline" | - |

---

## ID Cross-Reference Matrix

### Gene/Protein ID Conversions

| From | To | Tool |
|------|-----|------|
| Gene Symbol → UniProt | `UniProt_search` with gene query |
| Gene Symbol → Ensembl | `ensembl_lookup_gene` |
| UniProt → Ensembl | `UniProt_id_mapping` |
| Ensembl → UniProt | `UniProt_id_mapping` |
| Symbol → NCBI Gene | `MyGene_get_gene_annotation` |
| UniProt → PDB | Extract from UniProt entry |
| Symbol → ChEMBL Target | `ChEMBL_search_targets` |

### Compound ID Conversions

| From | To | Tool |
|------|-----|------|
| Name → PubChem CID | `PubChem_get_CID_by_compound_name` |
| SMILES → PubChem CID | `PubChem_get_CID_by_SMILES` |
| Name → ChEMBL ID | `ChEMBL_search_molecules` |
| CID → Properties | `PubChem_get_compound_properties_by_CID` |
| Name → PharmGKB ID | `PharmGKB_search_drugs` |

### Disease ID Conversions

| From | To | Tool |
|------|-----|------|
| Name → EFO ID | `OSL_get_efo_id_by_disease_name` |
| Name → UMLS CUI | `umls_search_concepts` |
| Name → ICD-10 | `icd_search_codes` |
| EFO → Children | `ols_get_efo_term_children` |

---

## Example Research Workflows

### Example 1: "Tell me about EGFR"

1. **Disambiguate**: Find UniProt ID (P00533), Ensembl ID (ENSG00000146648)
2. **Parallel queries**:
   - Get UniProt entry
   - Get domain architecture (InterPro)
   - Get AlphaFold structure
   - Get protein interactions (STRING)
   - Get tissue expression (GTEx)
   - Get genetic constraints (gnomAD)
   - Get druggability (OpenTargets)
   - Get known drugs (OpenTargets)
3. **Deep dive**: Get PDB structures for drug-bound forms
4. **Literature**: Search PubMed for "EGFR AND cancer"
5. **Synthesize**: Create comprehensive report with all findings

### Example 2: "What drugs target TP53?"

1. **Get target info**: Ensembl ID ENSG00000141510
2. **Get drug associations**: OpenTargets drugs, DGIdb interactions
3. **For each drug**:
   - Get ChEMBL compound details
   - Get bioactivity data
   - Get clinical trials
4. **Check tractability**: Is TP53 druggable?
5. **Synthesize**: Report on drug landscape with evidence

### Example 3: "Research Alzheimer's disease"

1. **Disambiguate**: EFO_0000249
2. **Get ontology**: Disease subtypes, synonyms
3. **Get targets**: Top 50 associated genes
4. **For top targets**: Get evidence details
5. **Get phenotypes**: HPO terms
6. **Get drugs**: Approved and trial drugs
7. **Get clinical trials**: Current studies
8. **Get variants**: ClinVar pathogenic variants
9. **Get GWAS**: Associated loci
10. **Get literature**: Recent publications
11. **Synthesize**: Comprehensive disease report

---

## Database Coverage Summary

| Database | Tool Prefix | Data Types |
|----------|-------------|------------|
| **UniProt** | `UniProt_*` | Protein sequences, function, variants |
| **Ensembl** | `ensembl_*` | Gene annotations, coordinates |
| **NCBI** | `NCBI_*`, `PubMed_*` | Sequences, literature, genes |
| **ChEMBL** | `ChEMBL_*` | Compounds, bioactivity, targets |
| **PubChem** | `PubChem_*` | Compounds, properties, assays |
| **OpenTargets** | `OpenTargets_*` | Target-disease associations |
| **GTEx** | `GTEx_*` | Tissue expression |
| **HPA** | `HPA_*` | Protein expression, localization |
| **gnomAD** | `gnomad_*` | Population variants |
| **ClinVar** | `clinvar_*` | Clinical variants |
| **GWAS Catalog** | `gwas_*` | GWAS associations |
| **Reactome** | `Reactome_*` | Pathways |
| **KEGG** | `kegg_*` | Pathways, compounds |
| **STRING** | `STRING_*` | Protein interactions |
| **RCSB PDB** | PDB tools | Protein structures |
| **AlphaFold** | `alphafold_*` | Predicted structures |
| **InterPro** | `InterPro_*` | Protein domains |
| **ClinicalTrials.gov** | `*clinical_trial*` | Clinical trials |
| **FAERS** | `FAERS_*` | Adverse events |
| **PharmGKB** | `PharmGKB_*` | Pharmacogenomics |
| **DGIdb** | `DGIdb_*` | Drug-gene interactions |
| **ADMET-AI** | `ADMETAI_*` | ADMET predictions |

---

## Report Section Templates

### Target Report Sections
1. Executive Summary
2. Target Identifiers
3. Basic Information (name, function, localization)
4. Structural Biology (PDB, AlphaFold, domains)
5. Function & Pathways (GO, Reactome, KEGG)
6. Protein-Protein Interactions
7. Expression Profile
8. Genetic Variation & Disease
9. Druggability & Pharmacology
10. Safety Profile
11. Literature & Research Landscape
12. Competitive Landscape
13. Summary & Recommendations
14. Data Sources & Methodology

### Drug Report Sections
1. Executive Summary
2. Compound Identity
3. Chemical Properties
4. Mechanism & Targets
5. ADMET Properties
6. Clinical Development
7. Safety Profile
8. Pharmacogenomics
9. Regulatory & Labeling
10. Literature & Research
11. Conclusions
12. Data Sources

### Disease Report Sections
1. Executive Summary
2. Disease Identity & Classification
3. Clinical Presentation
4. Genetic & Molecular Basis
5. Treatment Landscape
6. Biological Pathways
7. Epidemiology & Risk Factors
8. Literature & Research Activity
9. Similar Diseases & Comorbidities
10. Data Sources
