# Cancer Variant Interpretation - Examples

## Example 1: EGFR L858R in Lung Adenocarcinoma

### Input
```
Interpret EGFR L858R for lung adenocarcinoma
```

### Phase 1: Gene Resolution (verified)

```python
# MyGene
gene_info = tu.tools.MyGene_query_genes(query='EGFR', species='human')
# Result: symbol='EGFR', ensembl='ENSG00000146648', entrez='1956'

# UniProt
uniprot = tu.tools.UniProt_search(query='gene:EGFR', organism='human', limit=3)
# Result: accession='P00533'

# OpenTargets
ot = tu.tools.OpenTargets_get_target_id_description_by_name(targetName='EGFR')
# Result: id='ENSG00000146648', description='epidermal growth factor receptor'

# Cancer type
cancer = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName='lung adenocarcinoma')
# Result: EFO hits with lung adenocarcinoma
```

### Phase 3: Mutation Prevalence (verified)

```python
result = tu.tools.cBioPortal_get_mutations(study_id='luad_tcga', gene_list='EGFR')
# Returns: {status: 'success', data: [{proteinChange: 'R222L', ...}, {proteinChange: 'L858R', ...}, ...]}
# L858R found in TCGA-LUAD cohort
```

### Phase 4: Therapeutic Options (verified)

```python
drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(ensemblId='ENSG00000146648', size=20)
# Returns 1870+ drug entries including:
# - Osimertinib (CHEMBL3353410) - Phase 4, approved, EGFR inhibitor
# - Cetuximab (CHEMBL1201577) - Phase 4, approved
# - Lapatinib (CHEMBL1201179) - Phase 4, approved
# - Neratinib (CHEMBL3989921) - Phase 4, approved

fda = tu.tools.FDA_get_indications_by_drug_name(drug_name='osimertinib', limit=3)
# Returns: FDA label showing indications for:
# - Adjuvant therapy for EGFR exon 19 del or L858R NSCLC
# - First-line metastatic EGFR-mutant NSCLC
# - T790M-positive NSCLC after prior EGFR TKI

db = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
    query='osimertinib', case_sensitive=False, exact_match=False, limit=3
)
# Returns: DB09330, third-generation EGFR TKI description
```

### Phase 6: Clinical Trials (verified)

```python
trials = tu.tools.search_clinical_trials(
    query_term='EGFR L858R mutation',
    condition='non-small cell lung cancer',
    pageSize=10
)
# Returns multiple trials including osimertinib combinations
```

### Expected Report Summary

**Clinical Actionability: HIGH**

EGFR L858R is a well-characterized activating mutation in NSCLC. Osimertinib (Tagrisso) is FDA-approved as first-line therapy for EGFR exon 21 L858R mutation-positive metastatic NSCLC [T1 evidence].

---

## Example 2: BRAF V600E in Melanoma

### Input
```
Interpret BRAF V600E for melanoma
```

### Key Verified Results

```python
# Gene resolution
# BRAF: ENSG00000157764, UniProt P15056

# CIViC (verified: CIViC gene_id=5 for BRAF)
variants = tu.tools.civic_get_variants_by_gene(gene_id=5, limit=200)
# V600E found: CIViC variant_id=12

molecular_profile = tu.tools.civic_get_molecular_profile(molecular_profile_id=12)
# Name: 'BRAF V600E'

# cBioPortal melanoma mutations
mutations = tu.tools.cBioPortal_get_mutations(study_id='skcm_tcga', gene_list='BRAF')
# V600E is the most common BRAF mutation in melanoma

# OpenTargets drugs
drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
    ensemblId='ENSG00000157764', size=20
)
# Returns vemurafenib, dabrafenib, encorafenib, and MEK inhibitors
```

### Expected Report Summary

**Clinical Actionability: HIGH**

BRAF V600E is the most common BRAF mutation in melanoma. FDA-approved therapies include BRAF inhibitors (vemurafenib, dabrafenib, encorafenib) combined with MEK inhibitors (trametinib, cobimetinib, binimetinib) [T1 evidence]. Single-agent BRAF inhibition is no longer recommended due to rapid resistance.

---

## Example 3: KRAS G12C (Any Cancer Type)

### Input
```
What targeted therapies exist for KRAS G12C?
```

### Key Verified Results

```python
# Gene resolution
# KRAS: ENSG00000133703, Entrez 3845

# Mutation prevalence in pancreatic cancer
mutations = tu.tools.cBioPortal_get_mutations(study_id='paad_tcga', gene_list='KRAS')
# KRAS is mutated in >90% of pancreatic cancers, G12 variants dominant

# OpenTargets drugs
drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
    ensemblId='ENSG00000133703', size=20
)
# Returns sotorasib and other KRAS-targeting agents

# FDA approval
fda = tu.tools.FDA_get_indications_by_drug_name(drug_name='sotorasib', limit=3)
# Sotorasib (Lumakras): FDA-approved for KRAS G12C NSCLC
```

### Expected Report Summary

**Clinical Actionability: HIGH (for NSCLC), MODERATE (other cancer types)**

KRAS G12C is now targetable with covalent inhibitors. Sotorasib (Lumakras) and adagrasib (Krazati) are FDA-approved for KRAS G12C-mutated NSCLC [T1 evidence]. Clinical trials are expanding to other cancer types including colorectal and pancreatic cancer.

---

## Example 4: TP53 R273H (Complex/VUS-like)

### Input
```
Interpret TP53 R273H
```

### Key Verified Results

```python
# Gene resolution
# TP53: ENSG00000141510

# Drug landscape
drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
    ensemblId='ENSG00000141510', size=20
)
# TP53 has limited direct targeted therapies

# Mutation in LUAD
mutations = tu.tools.cBioPortal_get_mutations(study_id='luad_tcga', gene_list='TP53')
# TP53 is frequently mutated across cancer types; R273H is a hotspot contact mutant
```

### Expected Report Summary

**Clinical Actionability: LOW**

TP53 R273H is a well-known hotspot "contact" mutation that disrupts DNA binding. While TP53 is the most commonly mutated gene in cancer, direct therapeutic targeting remains limited. Experimental approaches include p53 reactivators (APR-246/eprenetapopt) in clinical trials [T2-T3 evidence]. TP53 mutations have broad prognostic significance as markers of aggressive disease.

---

## Response Structure Quick Reference

| Tool | Returns |
|------|---------|
| `MyGene_query_genes` | dict: `{hits: [{symbol, ensembl: {gene}, entrezgene}]}` |
| `UniProt_search` | dict: `{results: [{accession, gene_names}]}` |
| `UniProt_get_function_by_accession` | **list** of strings (NOT dict) |
| `OpenTargets_get_target_id_description_by_name` | dict: `{data: {search: {hits: [{id, name}]}}}` |
| `cBioPortal_get_mutations` | dict: `{status: 'success', data: [{proteinChange, ...}]}` |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | dict: `{data: {target: {knownDrugs: {count, rows}}}}` |
| `FDA_get_indications_by_drug_name` | dict: `{results: [{indications_and_usage}]}` |
| `drugbank_get_drug_basic_info_by_drug_name_or_id` | dict: `{results: [{drug_name, drugbank_id, description}]}` |
| `PubMed_search_articles` | **list** of dicts: `[{pmid, title, authors}]` (NOT wrapped) |
| `search_clinical_trials` | dict: `{studies: [{NCT ID, brief_title, overall_status, phase}]}` |
| `civic_search_genes` | dict: `{data: {genes: {nodes: [{id, name, entrezId}]}}}` |
| `civic_get_variants_by_gene` | dict: `{data: {gene: {variants: {nodes: [{id, name}]}}}}` |
| `ensembl_lookup_gene` | dict: `{status, data: {id, version, display_name}}` (REQUIRES species param) |
| `Reactome_map_uniprot_to_pathways` | pathway mappings |
