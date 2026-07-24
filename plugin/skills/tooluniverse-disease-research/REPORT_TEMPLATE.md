# Disease Research Report Template

Use this template when creating the initial report file `{disease_name}_research_report.md`.

---

```markdown
# Disease Research Report: {Disease Name}

**Report Generated**: {date}
**Disease Identifiers**: (to be filled)

---

## Executive Summary

(Brief 3-5 sentence overview - fill after all research complete)

---

## 1. Disease Identity & Classification

### Ontology Identifiers
| System | ID | Source |
|--------|-----|--------|
| EFO | | |
| ICD-10 | | |
| UMLS CUI | | |
| SNOMED CT | | |

### Synonyms & Alternative Names
- (list with source)

### Disease Hierarchy
- Parent:
- Subtypes:

**Sources**: (list tools used)

---

## 2. Clinical Presentation

### Phenotypes (HPO)
| HPO ID | Phenotype | Description | Source |
|--------|-----------|-------------|--------|

### Symptoms & Signs
- (list with source)

### Diagnostic Criteria
- (from literature/MedlinePlus)

**Sources**: (list tools used)

---

## 3. Genetic & Molecular Basis

### Associated Genes
| Gene | Score | Ensembl ID | Evidence | Source |
|------|-------|------------|----------|--------|

### GWAS Associations
| SNP | P-value | Odds Ratio | Study | Source |
|-----|---------|------------|-------|--------|

### Pathogenic Variants (ClinVar)
| Variant | Clinical Significance | Condition | Source |
|---------|----------------------|-----------|--------|

**Sources**: (list tools used)

---

## 4. Treatment Landscape

### Approved Drugs
| Drug | ChEMBL ID | Mechanism | Phase | Target | Source |
|------|-----------|-----------|-------|--------|--------|

### Clinical Trials
| NCT ID | Title | Phase | Status | Intervention | Source |
|--------|-------|-------|--------|--------------|--------|

### Treatment Guidelines
- (from literature)

**Sources**: (list tools used)

---

## 5. Biological Pathways & Mechanisms

### Key Pathways
| Pathway | Reactome ID | Genes Involved | Source |
|---------|-------------|----------------|--------|

### Protein-Protein Interactions
- (tissue-specific networks)

### Expression Patterns
| Tissue | Expression Level | Source |
|--------|------------------|--------|

**Sources**: (list tools used)

---

## 6. Epidemiology & Risk Factors

### Prevalence & Incidence
- (from literature)

### Risk Factors
| Factor | Evidence | Source |
|--------|----------|--------|

### GWAS Studies
| Study | Sample Size | Findings | Source |
|-------|-------------|----------|--------|

**Sources**: (list tools used)

---

## 7. Literature & Research Activity

### Publication Trends
- Total publications (5 years):
- Current year:
- Trend:

### Key Publications
| PMID | Title | Year | Citations | Source |
|------|-------|------|-----------|--------|

### Research Institutions
- (from OpenAlex)

**Sources**: (list tools used)

---

## 8. Similar Diseases & Comorbidities

### Similar Diseases
| Disease | Similarity Score | Shared Genes | Source |
|---------|-----------------|--------------|--------|

### Comorbidities
- (from literature/clinical data)

**Sources**: (list tools used)

---

## 9. Cancer-Specific Information (if applicable)

### CIViC Variants
| Gene | Variant | Evidence Level | Clinical Significance | Source |
|------|---------|----------------|----------------------|--------|

### Molecular Profiles
- (biomarkers)

### Targeted Therapies
| Therapy | Target | Evidence | Source |
|---------|--------|----------|--------|

**Sources**: (list tools used)

---

## 10. Drug Safety & Adverse Events

### Drug Warnings
| Drug | Warning Type | Description | Source |
|------|--------------|-------------|--------|

### Clinical Trial Adverse Events
| Trial | Drug | Adverse Event | Frequency | Source |
|-------|------|---------------|-----------|--------|

### FAERS Reports
- (FDA adverse event data)

**Sources**: (list tools used)

---

## References

### Data Sources Used
| Tool | Query | Section |
|------|-------|---------|

### Database Versions
- OpenTargets: (version/date)
- ClinVar: (version/date)
- GWAS Catalog: (version/date)
```

---

## Citation Format

Every piece of data MUST include its source. Use these formats:

### In Tables
```markdown
| Gene | Score | Source |
|------|-------|--------|
| APOE | 0.92 | OpenTargets_get_associated_targets_by_disease_efoId |
| APP | 0.88 | OpenTargets_get_associated_targets_by_disease_efoId |
```

### In Lists
```markdown
- Memory loss [Source: OpenTargets_get_associated_phenotypes_by_disease_efoId]
- Cognitive decline [Source: MedlinePlus_get_genetics_condition_by_name]
```

### In Prose
```markdown
The disease affects approximately 6.5 million Americans (Source: PubMed_search_articles,
query: "Alzheimer disease epidemiology").
```

### References Section
At the end of the report, include complete tool usage log:

```markdown
## References

### Tools Used
| # | Tool | Parameters | Section | Items Retrieved |
|---|------|------------|---------|-----------------|
| 1 | OSL_get_efo_id_by_disease_name | disease="Alzheimer disease" | Identity | 1 |
| 2 | ols_get_efo_term | obo_id="EFO:0000249" | Identity | 1 |
| 3 | OpenTargets_get_associated_targets_by_disease_efoId | efoId="EFO_0000249" | Genetics | 245 |
| ... | ... | ... | ... | ... |

### Data Retrieved Summary
- Total tools used: 45
- Total API calls: 78
- Sections completed: 10/10
```
