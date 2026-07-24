# Cancer Variant Interpretation - Quick Start Guide

## What This Skill Does

Given a cancer gene + variant (e.g., "EGFR L858R"), this skill produces a comprehensive clinical interpretation report covering:
- Clinical evidence and significance
- FDA-approved therapies
- Mutation prevalence
- Resistance mechanisms
- Clinical trials
- Prognostic implications

## Basic Usage

### Simple Variant Query
```
Interpret EGFR L858R for lung adenocarcinoma
```

### Resistance Investigation
```
Patient progressed on osimertinib. EGFR T790M detected. What are the options?
```

### Trial Matching
```
Find clinical trials for KRAS G12C mutation in any cancer type
```

### Tumor Board Preparation
```
Prepare molecular tumor board report: BRAF V600E in colorectal cancer
```

## Step-by-Step Workflow

### Step 1: Gene Resolution

Resolve the gene to all required IDs:

```python
# MyGene: Get Ensembl + Entrez IDs
gene_info = tu.tools.MyGene_query_genes(query='EGFR', species='human')
# -> hits[0]: symbol='EGFR', ensembl.gene='ENSG00000146648', entrezgene='1956'

# UniProt: Get protein accession
uniprot = tu.tools.UniProt_search(query='gene:EGFR', organism='human', limit=3)
# -> results[0].accession = 'P00533'

# OpenTargets: Get ensemblId + description
ot = tu.tools.OpenTargets_get_target_id_description_by_name(targetName='EGFR')
# -> data.search.hits[0].id = 'ENSG00000146648'
```

### Step 2: Clinical Evidence (CIViC)

```python
# Get gene from CIViC (paginate to find)
genes = tu.tools.civic_search_genes(limit=100)
# Find gene by name in results

# Get all variants for the gene
variants = tu.tools.civic_get_variants_by_gene(gene_id=CIVIC_GENE_ID, limit=200)
# Find matching variant by name (e.g., 'V600E')
```

### Step 3: Mutation Prevalence (cBioPortal)

```python
# Get mutations in a TCGA study
mutations = tu.tools.cBioPortal_get_mutations(study_id='luad_tcga', gene_list='EGFR')
# Returns: [{proteinChange: 'L858R', mutationType: 'Missense_Mutation', sampleId: '...'}]
```

### Step 4: Therapeutic Options

```python
# OpenTargets: All drugs targeting the gene
drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
    ensemblId='ENSG00000146648', size=50
)
# Returns: approved drugs, phase info, mechanism of action

# FDA label
fda = tu.tools.FDA_get_indications_by_drug_name(drug_name='osimertinib', limit=3)
# Returns: approved indications, dosing

# DrugBank details
db = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
    query='osimertinib', case_sensitive=False, exact_match=False, limit=3
)
# Returns: drug description, mechanism
```

### Step 5: Clinical Trials

```python
trials = tu.tools.search_clinical_trials(
    query_term='EGFR L858R',
    condition='non-small cell lung cancer',
    pageSize=20
)
# Returns: {studies: [{NCT ID, brief_title, overall_status, phase}]}
```

### Step 6: Resistance & Literature

```python
# Resistance literature
resistance = tu.tools.PubMed_search_articles(
    query='"EGFR" AND "osimertinib" AND resistance',
    limit=10, include_abstract=True
)

# Pathway context
pathways = tu.tools.Reactome_map_uniprot_to_pathways(id='P00533')
```

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| OpenTargets param error | Use `ensemblId` (camelCase), NOT `ensemblID` |
| CIViC gene not found | Gene search returns alphabetically, limited to 100 per page |
| DrugBank error | All 4 params required: `query`, `case_sensitive`, `exact_match`, `limit` |
| MyGene param error | Use `query`, NOT `q` |
| Clinical trials empty | Use broader `query_term` (e.g., "EGFR mutation" instead of "EGFR L858R") |
| ChEMBL mechanisms error | Use `drug_chembl_id__exact`, NOT `chembl_id` |
| GTEx empty results | Use versioned Ensembl ID (e.g., ENSG00000146648.12) |
| OpenTargets drug lookup | Use `drugName` parameter, NOT `genericName` |

## cBioPortal Study IDs (Quick Reference)

| Cancer Type | Study ID |
|-------------|----------|
| Lung Adenocarcinoma | luad_tcga |
| Breast Cancer | brca_tcga |
| Colorectal | coadread_tcga |
| Melanoma | skcm_tcga |
| Pancreatic | paad_tcga |
| Glioblastoma | gbm_tcga |
| Prostate | prad_tcga |

## Output Format

The skill generates a markdown report file named `{GENE}_{VARIANT}_cancer_variant_report.md` with sections:

1. Executive Summary (1-2 sentences + actionability score)
2. Gene & Variant Overview
3. Clinical Variant Evidence
4. Mutation Prevalence
5. Therapeutic Options (prioritized by evidence tier)
6. Resistance Mechanisms
7. Clinical Trials
8. Prognostic Impact
9. Evidence Grading Summary
10. Data Sources
11. Completeness Checklist
