# Disease Research Report Examples

Sample reports demonstrating the report-first approach with full citations.

---

## Example 1: Alzheimer's Disease Research Report

This is a condensed example. Actual reports are much more detailed.

```markdown
# Disease Research Report: Alzheimer's Disease

**Report Generated**: 2026-02-04 14:30
**Disease Identifiers**: EFO_0000249 | ICD-10: G30 | UMLS: C0002395

---

## Executive Summary

Alzheimer's disease is a progressive neurodegenerative disorder characterized by 
cognitive decline and memory impairment. Research has identified 245+ associated 
genes with APOE, APP, and PSEN1/2 showing strongest associations. Currently, 2 
disease-modifying therapies (aducanumab, lecanemab) are FDA-approved, with 120+ 
active clinical trials. The disease affects approximately 6.5 million Americans, 
with research activity increasing 20% annually.

---

## 1. Disease Identity & Classification

### Ontology Identifiers
| System | ID | Name | Source |
|--------|-----|------|--------|
| EFO | EFO_0000249 | Alzheimer's disease | OSL_get_efo_id_by_disease_name |
| ICD-10 | G30 | Alzheimer's disease | icd_search_codes |
| ICD-10 | G30.0 | Early onset | icd_search_codes |
| ICD-10 | G30.1 | Late onset | icd_search_codes |
| ICD-10 | G30.9 | Unspecified | icd_search_codes |
| UMLS CUI | C0002395 | Alzheimer's Disease | umls_search_concepts |
| SNOMED CT | 26929004 | Alzheimer's disease | snomed_search_concepts |
| MONDO | MONDO:0004975 | Alzheimer disease | ols_search_efo_terms |

### Synonyms & Alternative Names
| Synonym | Source |
|---------|--------|
| Alzheimer disease | ols_get_efo_term |
| Alzheimer's | ols_get_efo_term |
| AD | ols_get_efo_term |
| Presenile dementia | ols_get_efo_term |
| Senile dementia of Alzheimer type | ols_get_efo_term |
| SDAT | ols_get_efo_term |
| Primary degenerative dementia | umls_get_concept_details |

### Disease Hierarchy
**Parent Disease**: Dementia (EFO:0001360) [Source: ols_get_efo_term]

**Subtypes** [Source: ols_get_efo_term_children]:
| Subtype | EFO ID |
|---------|--------|
| Early-onset Alzheimer disease | EFO:0004718 |
| Late-onset Alzheimer disease | EFO:0004719 |
| Familial Alzheimer disease | EFO:0005244 |
| Sporadic Alzheimer disease | EFO:0005245 |

**Sources Used**: OSL_get_efo_id_by_disease_name, ols_get_efo_term, ols_get_efo_term_children, 
umls_search_concepts, umls_get_concept_details, icd_search_codes, snomed_search_concepts

---

## 2. Clinical Presentation

### Phenotypes (HPO)
| HPO ID | Phenotype | Frequency | Source |
|--------|-----------|-----------|--------|
| HP:0002354 | Memory impairment | Very frequent | OpenTargets_get_associated_phenotypes_by_disease_efoId |
| HP:0001268 | Mental deterioration | Very frequent | OpenTargets_get_associated_phenotypes_by_disease_efoId |
| HP:0000726 | Dementia | Very frequent | OpenTargets_get_associated_phenotypes_by_disease_efoId |
| HP:0002145 | Frontotemporal dementia | Frequent | OpenTargets_get_associated_phenotypes_by_disease_efoId |
| HP:0002185 | Neurofibrillary tangles | Frequent | OpenTargets_get_associated_phenotypes_by_disease_efoId |
| HP:0100256 | Senile plaques | Frequent | OpenTargets_get_associated_phenotypes_by_disease_efoId |
| HP:0002067 | Bradykinesia | Occasional | OpenTargets_get_associated_phenotypes_by_disease_efoId |
| HP:0000708 | Behavioral abnormality | Frequent | OpenTargets_get_associated_phenotypes_by_disease_efoId |
| HP:0007302 | Biparietal thinning | Occasional | OpenTargets_get_associated_phenotypes_by_disease_efoId |
| HP:0001289 | Confusion | Frequent | OpenTargets_get_associated_phenotypes_by_disease_efoId |

### Clinical Features
[Source: MedlinePlus_get_genetics_condition_by_name, condition="alzheimer-disease"]

**Early Symptoms**:
- Memory problems, especially remembering recent events
- Difficulty concentrating, planning, or problem-solving
- Trouble completing familiar tasks

**Progressive Symptoms**:
- Confusion about time and place
- Mood and personality changes
- Increased memory loss
- Difficulty recognizing family and friends
- Language problems
- Impaired judgment

### Diagnostic Criteria
[Source: PubMed_search_articles, query="Alzheimer disease diagnostic criteria"]

- NIA-AA criteria (2011, updated 2018)
- Clinical assessment of cognitive decline
- Biomarker confirmation (amyloid PET, CSF biomarkers)
- MRI showing characteristic atrophy

**Sources Used**: OpenTargets_get_associated_phenotypes_by_disease_efoId, 
MedlinePlus_get_genetics_condition_by_name, MedlinePlus_search_topics_by_keyword,
get_HPO_ID_by_phenotype, PubMed_search_articles

---

## 3. Genetic & Molecular Basis

### Top Associated Genes
[Source: OpenTargets_get_associated_targets_by_disease_efoId, efoId="EFO_0000249"]

| Rank | Gene | Ensembl ID | Score | Evidence Types | Source |
|------|------|------------|-------|----------------|--------|
| 1 | APOE | ENSG00000130203 | 0.92 | Genetic, Literature | OpenTargets |
| 2 | APP | ENSG00000142192 | 0.88 | Genetic, Pathways | OpenTargets |
| 3 | PSEN1 | ENSG00000080815 | 0.85 | Genetic | OpenTargets |
| 4 | PSEN2 | ENSG00000143801 | 0.82 | Genetic | OpenTargets |
| 5 | TREM2 | ENSG00000095970 | 0.78 | Genetic | OpenTargets |
| 6 | CLU | ENSG00000120885 | 0.75 | Genetic | OpenTargets |
| 7 | ABCA7 | ENSG00000064687 | 0.72 | Genetic | OpenTargets |
| 8 | BIN1 | ENSG00000024048 | 0.70 | Genetic | OpenTargets |
| 9 | SORL1 | ENSG00000137642 | 0.68 | Genetic | OpenTargets |
| 10 | CR1 | ENSG00000203710 | 0.65 | Genetic | OpenTargets |

### GWAS Associations
[Source: gwas_get_associations_for_trait, disease_trait="Alzheimer disease"]

| SNP | P-value | OR | Mapped Gene | Study | Source |
|-----|---------|-----|-------------|-------|--------|
| rs429358 | 1.0E-300 | 3.68 | APOE | GCST000678 | GWAS Catalog |
| rs7412 | 1.5E-250 | 0.28 | APOE | GCST000678 | GWAS Catalog |
| rs6656401 | 2.3E-45 | 1.18 | CR1 | GCST007320 | GWAS Catalog |
| rs11218343 | 4.5E-32 | 0.91 | SORL1 | GCST007320 | GWAS Catalog |
| rs9331896 | 8.2E-28 | 0.92 | CLU | GCST002305 | GWAS Catalog |

### GWAS Studies
[Source: gwas_get_studies_for_trait, disease_trait="Alzheimer disease"]

| Study ID | Title | Sample Size | Year | Source |
|----------|-------|-------------|------|--------|
| GCST90027158 | Late-onset AD GWAS | 788,989 | 2022 | GWAS Catalog |
| GCST007320 | AD GWAS meta-analysis | 455,258 | 2019 | GWAS Catalog |
| GCST002305 | IGAP Stage 1 | 74,046 | 2013 | GWAS Catalog |

### ClinVar Variants
[Source: clinvar_search_variants, condition="Alzheimer"]

| Variant | Gene | Clinical Significance | Review Status | Source |
|---------|------|----------------------|---------------|--------|
| NM_000484.4:c.2149G>T | APP | Pathogenic | Reviewed by expert panel | ClinVar |
| NM_000021.4:c.428T>C | PSEN1 | Pathogenic | Reviewed by expert panel | ClinVar |
| NM_000447.3:c.529A>G | PSEN2 | Pathogenic | Criteria provided | ClinVar |

**Total pathogenic variants**: 487 [Source: clinvar_search_variants]

**Sources Used**: OpenTargets_get_associated_targets_by_disease_efoId, 
OpenTargets_target_disease_evidence, gwas_get_associations_for_trait, 
gwas_get_variants_for_trait, gwas_get_studies_for_trait, clinvar_search_variants,
clinvar_get_variant_details, clinvar_get_clinical_significance

---

## 4. Treatment Landscape

### Approved Drugs
[Source: OpenTargets_get_associated_drugs_by_disease_efoId, efoId="EFO_0000249"]

| Drug | ChEMBL ID | Mechanism | Phase | Target | Source |
|------|-----------|-----------|-------|--------|--------|
| Lecanemab | CHEMBL4650319 | Anti-amyloid antibody | Approved | Amyloid beta | OpenTargets |
| Aducanumab | CHEMBL4303257 | Anti-amyloid antibody | Approved | Amyloid beta | OpenTargets |
| Donepezil | CHEMBL502 | AChE inhibitor | Approved | ACHE | OpenTargets |
| Rivastigmine | CHEMBL95 | AChE inhibitor | Approved | ACHE/BCHE | OpenTargets |
| Galantamine | CHEMBL659 | AChE inhibitor | Approved | ACHE | OpenTargets |
| Memantine | CHEMBL807 | NMDA antagonist | Approved | GRIN1/2A/2B | OpenTargets |

### Drug Mechanisms
[Source: OpenTargets_get_drug_mechanisms_of_action_by_chemblId]

**Lecanemab (CHEMBL4650319)**:
- Action type: Binding agent
- Target: Amyloid beta A4 protein (APP)
- Mechanism: Binds to soluble amyloid beta protofibrils

**Donepezil (CHEMBL502)**:
- Action type: Inhibitor
- Target: Acetylcholinesterase (ACHE)
- Mechanism: Reversible inhibition of acetylcholinesterase

### Clinical Trials
[Source: search_clinical_trials, condition="Alzheimer disease"]

**Summary**:
- Total trials: 2,847
- Active/Recruiting: 342
- Phase III: 127
- Phase II: 215

**Top Active Phase III Trials**:
| NCT ID | Title | Intervention | Status | Source |
|--------|-------|--------------|--------|--------|
| NCT04468659 | TRAILBLAZER-ALZ 2 | Donanemab | Active | ClinicalTrials.gov |
| NCT05108922 | EVOKE/EVOKE+ | Semaglutide | Recruiting | ClinicalTrials.gov |
| NCT04381468 | GRADUATE I/II | Gantenerumab | Completed | ClinicalTrials.gov |

[Source: get_clinical_trial_descriptions, extract_clinical_trial_outcomes]

**Sources Used**: OpenTargets_get_associated_drugs_by_disease_efoId, 
OpenTargets_get_drug_chembId_by_generic_name, OpenTargets_get_drug_mechanisms_of_action_by_chemblId,
search_clinical_trials, get_clinical_trial_descriptions, get_clinical_trial_outcome_measures,
extract_clinical_trial_outcomes, GtoPdb_list_diseases, GtoPdb_get_disease

---

## 5. Biological Pathways & Mechanisms

### Key Pathways
[Source: Reactome_map_uniprot_to_pathways for top disease genes]

| Pathway | Reactome ID | Key Genes | Source |
|---------|-------------|-----------|--------|
| Amyloid fiber formation | R-HSA-977225 | APP, PSEN1, PSEN2 | Reactome |
| BACE1 processing of APP | R-HSA-418457 | APP, BACE1, PSEN1 | Reactome |
| Presenilin-mediated signaling | R-HSA-418885 | PSEN1, PSEN2, NCSTN | Reactome |
| Cholesterol metabolism | R-HSA-191273 | APOE, CLU | Reactome |
| Innate immune system | R-HSA-168249 | TREM2, CR1 | Reactome |

### Protein-Protein Interactions
[Source: humanbase_ppi_analysis, gene_list=["APP","PSEN1","APOE","TREM2"], tissue="brain"]

**Brain-specific PPI network**: 45 nodes, 128 edges
- Hub genes: APP (degree: 23), PSEN1 (degree: 18)
- Key interactions: APP-PSEN1, APP-BACE1, APOE-CLU

### Expression Patterns
[Source: gtex_get_expression_by_gene, HPA_get_protein_expression]

| Gene | Highest Expression Tissue | TPM | Source |
|------|--------------------------|-----|--------|
| APP | Brain - Cerebellum | 245.3 | GTEx |
| APOE | Brain - Frontal Cortex | 892.1 | GTEx |
| PSEN1 | Brain - Hippocampus | 45.2 | GTEx |

**Sources Used**: Reactome_get_diseases, Reactome_map_uniprot_to_pathways, 
Reactome_get_pathway, Reactome_get_pathway_reactions, humanbase_ppi_analysis,
gtex_get_expression_by_gene, HPA_get_protein_expression, geo_search_datasets

---

## 6. Epidemiology & Research Activity

### Prevalence
[Source: PubMed_search_articles, query="Alzheimer disease epidemiology prevalence"]

- US prevalence: ~6.5 million (2023 estimate)
- Global prevalence: ~55 million
- Projected US (2050): 12.7 million

### Risk Factors
[Source: PubMed_search_articles, gwas_get_associations_for_trait]

| Factor | Evidence Level | Source |
|--------|----------------|--------|
| APOE ε4 allele | Very strong (OR 3.68) | GWAS Catalog |
| Age (>65) | Very strong | PubMed |
| Family history | Strong | PubMed |
| Cardiovascular disease | Moderate | PubMed |
| Type 2 diabetes | Moderate | PubMed |
| Low education | Moderate | PubMed |

### Publication Trends
[Source: PubMed_search_articles]

| Query | Period | Count | Source |
|-------|--------|-------|--------|
| "Alzheimer disease" | 5 years | 78,432 | PubMed |
| "Alzheimer disease" | 1 year | 17,234 | PubMed |
| "Alzheimer disease" mechanism | 5 years | 12,456 | PubMed |
| "Alzheimer disease" treatment | 5 years | 23,891 | PubMed |

**Trend**: Increasing (+22% year-over-year)

### Top Research Institutions
[Source: openalex_search_works]

1. Harvard University
2. University of California system
3. Mayo Clinic
4. Karolinska Institute
5. University College London

**Sources Used**: PubMed_search_articles, PubMed_get_article, PubMed_get_related,
PubMed_get_cited_by, OpenTargets_get_publications_by_disease_efoId, 
openalex_search_works, europe_pmc_search_abstracts, semantic_scholar_search_papers

---

## 7. Similar Diseases & Comorbidities

### Similar Diseases
[Source: OpenTargets_get_similar_entities_by_disease_efoId, efoId="EFO_0000249"]

| Disease | EFO ID | Similarity Score | Shared Genes | Source |
|---------|--------|-----------------|--------------|--------|
| Frontotemporal dementia | EFO:0000621 | 0.78 | MAPT, GRN, C9orf72 | OpenTargets |
| Parkinson's disease | EFO:0002508 | 0.65 | SNCA, LRRK2 | OpenTargets |
| Lewy body dementia | EFO:0002549 | 0.72 | SNCA, GBA | OpenTargets |
| Vascular dementia | EFO:0003914 | 0.58 | NOTCH3, HTRA1 | OpenTargets |
| Mild cognitive impairment | EFO:0003882 | 0.82 | APOE, CLU | OpenTargets |

**Sources Used**: OpenTargets_get_similar_entities_by_disease_efoId

---

## 8. Cancer-Specific Information

*Not applicable - Alzheimer's disease is not a cancer.*

---

## 9. Pharmacological Targets

### Druggable Targets
[Source: GtoPdb_list_diseases, GtoPdb_get_disease]

| Target | Type | Drugs | Source |
|--------|------|-------|--------|
| Acetylcholinesterase (ACHE) | Enzyme | Donepezil, Rivastigmine, Galantamine | GtoPdb |
| NMDA receptor | Ion channel | Memantine | GtoPdb |
| Amyloid beta | Protein | Lecanemab, Aducanumab | GtoPdb |
| BACE1 | Enzyme | (pipeline) | GtoPdb |
| Tau | Protein | (pipeline) | GtoPdb |

**Sources Used**: GtoPdb_list_diseases, GtoPdb_get_disease, GtoPdb_get_targets,
GtoPdb_get_target, GtoPdb_get_target_interactions

---

## 10. Drug Safety & Adverse Events

### Drug Warnings
[Source: OpenTargets_get_drug_warnings_by_chemblId]

| Drug | Warning Type | Description | Source |
|------|--------------|-------------|--------|
| Aducanumab | Boxed warning | ARIA (amyloid-related imaging abnormalities) | OpenTargets |
| Lecanemab | Boxed warning | ARIA-E and ARIA-H | OpenTargets |
| Donepezil | Warning | Bradycardia, syncope | OpenTargets |
| Memantine | Warning | Dizziness, confusion | OpenTargets |

### Clinical Trial Adverse Events
[Source: extract_clinical_trial_adverse_events]

**Lecanemab (CLARITY AD Trial, NCT03887455)**:
| Adverse Event | Drug (%) | Placebo (%) | Source |
|---------------|----------|-------------|--------|
| ARIA-E | 12.6% | 1.7% | ClinicalTrials.gov |
| ARIA-H microhemorrhage | 17.3% | 9.0% | ClinicalTrials.gov |
| Infusion reactions | 26.4% | 7.4% | ClinicalTrials.gov |
| Headache | 11.1% | 8.1% | ClinicalTrials.gov |

**Sources Used**: OpenTargets_get_drug_warnings_by_chemblId, 
OpenTargets_get_drug_blackbox_status_by_chembl_ID, extract_clinical_trial_adverse_events,
FAERS_count_reactions_by_drug_event

---

## References

### Complete Tool Usage Log

| # | Tool | Parameters | Section | Items |
|---|------|------------|---------|-------|
| 1 | OSL_get_efo_id_by_disease_name | disease="Alzheimer disease" | 1 | 1 |
| 2 | ols_get_efo_term | obo_id="EFO:0000249" | 1 | 1 |
| 3 | ols_get_efo_term_children | obo_id="EFO:0000249", size=30 | 1 | 4 |
| 4 | umls_search_concepts | query="Alzheimer disease" | 1 | 1 |
| 5 | umls_get_concept_details | cui="C0002395" | 1 | 1 |
| 6 | icd_search_codes | query="Alzheimer", version="ICD10CM" | 1 | 4 |
| 7 | snomed_search_concepts | query="Alzheimer disease" | 1 | 1 |
| 8 | OpenTargets_get_associated_phenotypes_by_disease_efoId | efoId="EFO_0000249" | 2 | 15 |
| 9 | MedlinePlus_get_genetics_condition_by_name | condition="alzheimer-disease" | 2 | 1 |
| 10 | OpenTargets_get_associated_targets_by_disease_efoId | efoId="EFO_0000249" | 3 | 245 |
| 11 | gwas_get_associations_for_trait | disease_trait="Alzheimer disease", size=50 | 3 | 50 |
| 12 | gwas_get_studies_for_trait | disease_trait="Alzheimer disease", size=30 | 3 | 28 |
| 13 | clinvar_search_variants | condition="Alzheimer", max_results=50 | 3 | 50 |
| 14 | OpenTargets_get_associated_drugs_by_disease_efoId | efoId="EFO_0000249", size=100 | 4 | 45 |
| 15 | search_clinical_trials | condition="Alzheimer disease", pageSize=50 | 4 | 50 |
| 16 | Reactome_map_uniprot_to_pathways | id="P05067" (APP) | 5 | 12 |
| 17 | humanbase_ppi_analysis | gene_list=["APP","PSEN1","APOE","TREM2"], tissue="brain" | 5 | 45 |
| 18 | gtex_get_expression_by_gene | gene="APP" | 5 | 54 |
| 19 | PubMed_search_articles | query="Alzheimer disease", limit=100 | 6 | 100 |
| 20 | openalex_search_works | query="Alzheimer disease", limit=50 | 6 | 50 |
| 21 | OpenTargets_get_similar_entities_by_disease_efoId | efoId="EFO_0000249", size=20 | 7 | 15 |
| 22 | GtoPdb_list_diseases | name="Alzheimer" | 9 | 1 |
| 23 | OpenTargets_get_drug_warnings_by_chemblId | chemblId="CHEMBL4650319" | 10 | 2 |
| 24 | extract_clinical_trial_adverse_events | nct_ids=["NCT03887455"] | 10 | 8 |

### Summary Statistics
- **Total tools used**: 24 unique tools
- **Total API calls**: 58
- **Total data points retrieved**: 847
- **Sections completed**: 10/10
- **Report completeness**: 100%

### Database Versions
- OpenTargets Platform: v24.03
- GWAS Catalog: Release 2024-02-15
- ClinVar: 2024-02
- ClinicalTrials.gov: Live data
- Reactome: v87
- PubMed: Live data

---

*Report generated using ToolUniverse Disease Research Skill*
*All data retrieved from public databases via ToolUniverse API*
```

---

## Example 2: Handling Rare Disease with Limited Data

When some tools return empty results, note this clearly:

```markdown
## 3. Genetic & Molecular Basis

### Associated Genes
[Source: OpenTargets_get_associated_targets_by_disease_efoId, efoId="EFO_XXXXXXX"]

| Gene | Score | Source |
|------|-------|--------|
| GENE1 | 0.75 | OpenTargets |
| GENE2 | 0.68 | OpenTargets |

*Note: Limited genetic data available for this rare disease (2 genes vs typical 50+)*

### GWAS Associations
[Source: gwas_get_associations_for_trait]

**No GWAS associations found** - This is a rare disease without large-scale genetic studies.

### ClinVar Variants
[Source: clinvar_search_variants]

| Variant | Clinical Significance | Source |
|---------|----------------------|--------|
| (3 variants found) | | ClinVar |

*Data gap identified: Consider searching case reports in PubMed for variant information*
```

---

## Example 3: Multi-Disease Comparison Report

When comparing diseases, maintain citations for each:

```markdown
# Comparative Disease Report: Neurodegenerative Disorders

## Disease Comparison Table

| Aspect | Alzheimer's | Parkinson's | ALS | Source |
|--------|-------------|-------------|-----|--------|
| EFO ID | EFO_0000249 | EFO_0002508 | EFO_0000253 | OSL_get_efo_id_by_disease_name |
| Associated genes | 245 | 180 | 95 | OpenTargets_get_associated_targets_by_disease_efoId |
| Approved drugs | 6 | 12 | 4 | OpenTargets_get_associated_drugs_by_disease_efoId |
| Active trials | 342 | 267 | 89 | search_clinical_trials |
| US prevalence | 6.5M | 1M | 30K | PubMed_search_articles |
| 5-year pubs | 78,432 | 52,891 | 18,234 | PubMed_search_articles |

## Shared Genetic Basis
[Source: OpenTargets_get_associated_targets_by_disease_efoId for each disease]

| Gene | Alzheimer's Score | Parkinson's Score | ALS Score |
|------|-------------------|-------------------|-----------|
| MAPT | 0.45 | 0.52 | 0.12 |
| GRN | 0.38 | 0.15 | 0.42 |
```

---

## Citation Best Practices

### DO: Include tool name with every data point
```markdown
The disease affects 6.5 million Americans [Source: PubMed_search_articles, 
query="Alzheimer disease epidemiology prevalence"]
```

### DO: Use table format for structured data
```markdown
| Gene | Score | Source |
|------|-------|--------|
| APOE | 0.92 | OpenTargets_get_associated_targets_by_disease_efoId |
```

### DO: Note when data is unavailable
```markdown
### GWAS Associations
[Source: gwas_get_associations_for_trait]

**No data available** - This query returned 0 results.
```

### DON'T: Present data without source
```markdown
❌ The disease has 245 associated genes.
✓ The disease has 245 associated genes [Source: OpenTargets_get_associated_targets_by_disease_efoId]
```
