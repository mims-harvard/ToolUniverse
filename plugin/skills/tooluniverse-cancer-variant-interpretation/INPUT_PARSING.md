# Cancer Variant Interpretation - Input Parsing & Parameter Corrections

## Input Parsing

**Required**: Gene symbol + variant notation
**Optional**: Cancer type (improves specificity)

### Accepted Input Formats

| Format | Example | How to Parse |
|--------|---------|-------------|
| Gene + amino acid change | EGFR L858R | gene=EGFR, variant=L858R |
| Gene + HGVS protein | BRAF p.V600E | gene=BRAF, variant=V600E |
| Gene + exon notation | EGFR exon 19 deletion | gene=EGFR, variant=exon 19 deletion |
| Gene + fusion | EML4-ALK fusion | gene=ALK, variant=EML4-ALK |
| Gene + amplification | HER2 amplification | gene=ERBB2, variant=amplification |
| Full query with cancer | "EGFR L858R in lung adenocarcinoma" | gene=EGFR, variant=L858R, cancer=lung adenocarcinoma |

### Gene Symbol Normalization

Common aliases to resolve:
- HER2 -> ERBB2
- ALK -> ALK (but EML4-ALK is a fusion)
- PD-L1 -> CD274
- VEGF -> VEGFA

## Tool Parameter Corrections (CRITICAL)

**BEFORE calling ANY tool for the first time**, verify its parameters.

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblID` | `ensemblId` (camelCase) |
| `OpenTargets_get_drug_chembId_by_generic_name` | `genericName` | `drugName` |
| `OpenTargets_target_disease_evidence` | `ensemblID` | `ensemblId` + `efoId` |
| `MyGene_query_genes` | `q` | `query` |
| `search_clinical_trials` | `disease`, `biomarker` | `condition`, `query_term` (required) |
| `civic_get_variants_by_gene` | `gene_symbol` | `gene_id` (CIViC numeric ID) |
| `drugbank_*` | any 3 params | ALL 4 required: `query`, `case_sensitive`, `exact_match`, `limit` |
| `ChEMBL_get_drug_mechanisms` | `chembl_id` | `drug_chembl_id__exact` |
| `ensembl_lookup_gene` | no species | `species='homo_sapiens'` is REQUIRED for Ensembl IDs |
