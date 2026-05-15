# Cancer Variant Interpretation Report Template

## Report File Naming

```
{GENE}_{VARIANT}_cancer_variant_report.md

Examples:
EGFR_L858R_cancer_variant_report.md
BRAF_V600E_cancer_variant_report.md
KRAS_G12C_cancer_variant_report.md
```

## Report Template

```markdown
# Cancer Variant Interpretation Report: {GENE} {VARIANT}

**Date**: {date}
**Cancer Type**: {cancer_type or "Not specified"}

---

## Executive Summary

{1-2 sentences summarizing the key finding and top recommendation}

**Clinical Actionability**: {Score: HIGH / MODERATE / LOW / UNKNOWN}

---

## 1. Gene & Variant Overview

| Field | Value |
|-------|-------|
| Gene Symbol | {symbol} |
| Full Name | {name} |
| Ensembl ID | {ensembl_id} |
| UniProt | {uniprot_accession} |
| Entrez ID | {entrez_id} |
| Variant | {variant_notation} |
| Protein Function | {function_summary} |

## 2. Clinical Variant Evidence

### 2.1 CIViC Clinical Interpretations

| Evidence Type | Description | Level | Clinical Significance |
|---------------|-------------|-------|----------------------|
| ... | ... | ... | ... |

### 2.2 Evidence Summary

{Summary of clinical evidence from CIViC and other sources}

*Source: CIViC via civic_get_variants_by_gene, civic_get_variant*

## 3. Mutation Prevalence

### 3.1 Frequency Across Cancer Types (cBioPortal)

| Study | Cancer Type | Total Mutated | This Variant | Frequency |
|-------|-------------|---------------|--------------|-----------|
| ... | ... | ... | ... | ... |

### 3.2 Co-occurring Mutations

{Top co-occurring mutations from cBioPortal data}

*Source: cBioPortal via cBioPortal_get_mutations*

## 4. Therapeutic Options

### 4.1 FDA-Approved Therapies (T1 Evidence)

| Drug | Trade Name | Indication | Mechanism | Phase |
|------|-----------|------------|-----------|-------|
| ... | ... | ... | ... | ... |

### 4.2 Clinical Trial Drugs (T2-T3 Evidence)

| Drug | ChEMBL ID | Phase | Mechanism | Disease |
|------|-----------|-------|-----------|---------|
| ... | ... | ... | ... | ... |

### 4.3 Drug Details

{For each recommended drug: mechanism of action, FDA label info, dosing, warnings}

*Sources: OpenTargets, FDA, DrugBank, ChEMBL*

## 5. Resistance Mechanisms

### 5.1 Known Resistance Patterns

| Resistance Mutation | Drug Affected | Mechanism | Strategy to Overcome |
|--------------------|---------------|-----------|---------------------|
| ... | ... | ... | ... |

### 5.2 Bypass Pathways

{Pathway analysis showing potential bypass resistance routes}

*Sources: CIViC, PubMed, Reactome*

## 6. Clinical Trials

### 6.1 Actively Recruiting Trials

| NCT ID | Phase | Agent(s) | Status | Biomarker Required |
|--------|-------|----------|--------|-------------------|
| ... | ... | ... | ... | ... |

### 6.2 Trial Recommendations

{Specific trial recommendations based on patient's mutation and cancer type}

*Source: ClinicalTrials.gov via search_clinical_trials*

## 7. Prognostic Impact

### 7.1 Survival Associations

{Literature-based prognostic data}

### 7.2 Pathway Context

{Pathway analysis and biological context}

### 7.3 Expression Profile

{Tissue expression data for the gene}

*Sources: PubMed, Reactome, GTEx*

## 8. Evidence Grading Summary

| Finding | Evidence Tier | Source | Confidence |
|---------|--------------|--------|------------|
| ... | T1/T2/T3/T4 | ... | High/Moderate/Low |

---

## Data Sources Queried

| Source | Tool(s) Used | Data Retrieved |
|--------|-------------|----------------|
| MyGene | MyGene_query_genes | Gene IDs |
| UniProt | UniProt_search, UniProt_get_function_by_accession | Protein function |
| OpenTargets | OpenTargets_get_associated_drugs_by_target_ensemblID | Drug associations |
| CIViC | civic_search_genes, civic_get_variants_by_gene | Clinical evidence |
| cBioPortal | cBioPortal_get_mutations | Mutation prevalence |
| FDA | FDA_get_indications_by_drug_name | Drug labels |
| DrugBank | drugbank_get_drug_basic_info_by_drug_name_or_id | Drug info |
| ChEMBL | ChEMBL_get_drug_mechanisms | Drug mechanisms |
| ClinicalTrials.gov | search_clinical_trials | Active trials |
| PubMed | PubMed_search_articles | Literature evidence |
| Reactome | Reactome_map_uniprot_to_pathways | Pathway context |
| GTEx | GTEx_get_median_gene_expression | Expression data |

---

## Completeness Checklist

- [ ] Gene resolved to Ensembl, UniProt, and Entrez IDs
- [ ] Clinical variant evidence queried (CIViC or alternative)
- [ ] Mutation prevalence assessed (cBioPortal, at least 1 study)
- [ ] At least 1 therapeutic option identified with evidence tier, OR documented as "no targeted therapy available"
- [ ] FDA label information retrieved for recommended drugs
- [ ] Resistance mechanisms assessed (known patterns + literature search)
- [ ] At least 3 clinical trials listed, OR "no matching trials found"
- [ ] Prognostic literature searched
- [ ] Pathway context provided (Reactome)
- [ ] Executive summary is actionable (says what to DO)
- [ ] All recommendations have source citations
- [ ] Evidence tiers assigned to all findings
```
