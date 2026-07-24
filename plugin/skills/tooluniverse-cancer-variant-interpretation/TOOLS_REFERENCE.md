# Cancer Variant Interpretation - Tools Reference

Verified tool parameters and response structures for all tools used in this skill.

## Gene Resolution Tools

### MyGene_query_genes
**Purpose**: Resolve gene symbol to Ensembl, Entrez IDs
**Parameters**:
- `query` (string, REQUIRED): Gene symbol, name, or ID (e.g., 'EGFR')
- `species` (string, default='human'): Species filter
- `fields` (string): Comma-separated fields to return

**Response**: `{took, total, max_score, hits: [{_id, _score, ensembl: {gene}, entrezgene, name, symbol}]}`

**Example**:
```python
result = tu.tools.MyGene_query_genes(query='EGFR', species='human')
# hits[0] = {symbol: 'EGFR', ensembl: {gene: 'ENSG00000146648'}, entrezgene: '1956', name: 'epidermal growth factor receptor'}
```

### UniProt_search
**Purpose**: Find protein accession
**Parameters**:
- `query` (string, REQUIRED): e.g., 'gene:EGFR'
- `organism` (string): e.g., 'human'
- `limit` (integer)

**Response**: `{total_results, returned, results: [{accession, id, protein_name, gene_names, organism, length}]}`

### UniProt_get_function_by_accession
**Purpose**: Get protein function description
**Parameters**: `accession` (string, REQUIRED): e.g., 'P00533'

**Response**: Returns a **list of strings** (NOT a dict). Each string is a function description paragraph.
```python
# Example: ['Receptor tyrosine kinase binding ligands of the EGF family...', ...]
```

### UniProt_get_disease_variants_by_accession
**Purpose**: Get known disease-associated variants
**Parameters**: `accession` (string, REQUIRED)

### OpenTargets_get_target_id_description_by_name
**Purpose**: Resolve gene name to Ensembl ID in OpenTargets
**Parameters**: `targetName` (string, REQUIRED)

**Response**: `{data: {search: {hits: [{id (ensemblId), name, description}]}}}`

### OpenTargets_get_disease_id_description_by_name
**Purpose**: Resolve disease/cancer type to EFO ID
**Parameters**: `diseaseName` (string, REQUIRED)

**Response**: `{data: {search: {hits: [{id (efoId), name, description}]}}}`

### ensembl_lookup_gene
**Purpose**: Get gene details including version number
**Parameters**:
- `gene_id` (string, REQUIRED): Ensembl ID or gene symbol
- `species` (string, **REQUIRED for Ensembl IDs**): e.g., 'homo_sapiens' -- will error without this!

**Response**: `{status: 'success', data: {id, version, display_name, species, biotype, start, end, seq_region_name, strand, canonical_transcript, assembly_name}}`

---

## CIViC Clinical Evidence Tools

### civic_search_genes
**Purpose**: List genes in CIViC database
**Parameters**:
- `query` (string): Filter query (NOTE: does NOT filter in GraphQL, returns all genes alphabetically)
- `limit` (integer, default=10, max=100): Number to return

**Response**: `{data: {genes: {nodes: [{id, name, description, entrezId}]}}}`

**LIMITATION**: Returns genes alphabetically, max 100 per call. No server-side filtering. Genes beyond alphabetical position 100 (E-Z) require multiple paginated calls or known CIViC gene IDs.

### civic_get_variants_by_gene
**Purpose**: Get all variants for a gene in CIViC
**Parameters**:
- `gene_id` (integer, REQUIRED): CIViC gene ID (NOT Entrez ID)
- `limit` (integer, default=50): Max variants to return

**Response**: `{data: {gene: {variants: {nodes: [{id, name}]}}}}`

### civic_get_variant
**Purpose**: Get variant details
**Parameters**: `variant_id` (integer, REQUIRED)

**Response**: `{data: {variant: {id, name}}}`

### civic_get_molecular_profile
**Purpose**: Get molecular profile details
**Parameters**: `molecular_profile_id` (integer, REQUIRED)

### civic_search_evidence_items
**Purpose**: List evidence items
**Parameters**: `limit` (integer, default=20)

**Response**: `{data: {evidenceItems: {nodes: [{id, description, evidenceLevel, evidenceType}]}}}`

### civic_search_assertions
**Purpose**: List assertions
**Parameters**: `limit` (integer, default=20)

### civic_search_therapies
**Purpose**: List therapies
**Parameters**: `limit` (integer, default=20)

---

## cBioPortal Mutation Prevalence Tools

### cBioPortal_get_mutations
**Purpose**: Get mutation data for genes in a study
**Parameters**:
- `study_id` (string): Cancer study ID (e.g., 'luad_tcga')
- `gene_list` (string): Comma-separated gene symbols (e.g., 'EGFR,KRAS')

**Response**: `{status: 'success', data: [{proteinChange, mutationType, sampleId, entrezGeneId, studyId, mutationStatus, chr, startPosition, endPosition, ...}]}`

**IMPORTANT**: Extract mutations via `result.get('data', [])`, NOT treating result as a list directly.

### cBioPortal_get_cancer_studies
**Purpose**: List available cancer studies
**Parameters**: `limit` (integer, default=20)

**Response**: Array of `[{studyId, name, description, cancerTypeId, ...}]`

### cBioPortal_get_molecular_profiles
**Purpose**: Get molecular profiles for a study
**Parameters**: `study_id` (string, REQUIRED)

### cBioPortal_get_gene_info
**Purpose**: Get gene info by Entrez ID
**Parameters**: `entrez_gene_id` (integer, REQUIRED)

### cBioPortal_get_samples
**Purpose**: Get samples from a study
**Parameters**: `study_id` (string, REQUIRED)

---

## Drug Information Tools

### OpenTargets_get_associated_drugs_by_target_ensemblID
**Purpose**: Get ALL drugs targeting a gene (approved + clinical trials)
**Parameters**:
- `ensemblId` (string, REQUIRED): NOTE camelCase
- `size` (integer): Number of drug entries

**Response**: `{data: {target: {id, approvedSymbol, knownDrugs: {count, rows: [{drug: {id, name, tradeNames, maximumClinicalTrialPhase, isApproved, hasBeenWithdrawn}, phase, mechanismOfAction, disease: {id, name}}]}}}}`

### OpenTargets_get_drug_chembId_by_generic_name
**Purpose**: Resolve drug name to ChEMBL ID
**Parameters**: `drugName` (string, REQUIRED)

**Response**: `{data: {search: {hits: [{id (ChEMBL ID), name, description}]}}}`

### OpenTargets_get_drug_mechanisms_of_action_by_chemblId
**Purpose**: Drug mechanism of action
**Parameters**: `chemblId` (string, REQUIRED)

### OpenTargets_get_drug_indications_by_chemblId
**Purpose**: Drug indications
**Parameters**: `chemblId` (string, REQUIRED)

### OpenTargets_get_drug_adverse_events_by_chemblId
**Purpose**: Drug adverse events
**Parameters**: `chemblId` (string, REQUIRED)

### OpenTargets_get_associated_drugs_by_disease_efoId
**Purpose**: Get drugs for a specific disease
**Parameters**: `efoId` (string, REQUIRED), `size` (integer, REQUIRED)

### FDA_get_indications_by_drug_name
**Purpose**: FDA-approved indications
**Parameters**: `drug_name` (string), `limit` (integer)

**Response**: `{meta: {skip, limit, total}, results: [{openfda.brand_name, openfda.generic_name, indications_and_usage}]}`

### FDA_get_mechanism_of_action_by_drug_name
**Purpose**: FDA mechanism of action
**Parameters**: `drug_name` (string), `limit` (integer)

### FDA_get_boxed_warning_info_by_drug_name
**Purpose**: FDA black box warnings
**Parameters**: `drug_name` (string), `limit` (integer)

### FDA_get_clinical_studies_info_by_drug_name
**Purpose**: FDA clinical study data
**Parameters**: `drug_name` (string), `limit` (integer)

### drugbank_get_drug_basic_info_by_drug_name_or_id
**Purpose**: Drug info from DrugBank
**Parameters** (ALL REQUIRED):
- `query` (string): Drug name or DrugBank ID
- `case_sensitive` (boolean): Use False
- `exact_match` (boolean): Use False
- `limit` (integer): e.g., 3

**Response**: `{query, total_matches, total_returned_results, results: [{drug_name, drugbank_id, description, ...}]}`

### drugbank_get_pharmacology_by_drug_name_or_drugbank_id
**Purpose**: Pharmacology details
**Parameters** (ALL REQUIRED): `query`, `case_sensitive`, `exact_match`, `limit`

### drugbank_get_targets_by_drug_name_or_drugbank_id
**Purpose**: Drug targets
**Parameters** (ALL REQUIRED): `query`, `case_sensitive`, `exact_match`, `limit`

### ChEMBL_get_drug_mechanisms
**Purpose**: Drug mechanisms from ChEMBL
**Parameters**: `drug_chembl_id__exact` (string, REQUIRED), `limit`, `offset`

### ChEMBL_search_drugs
**Purpose**: Search drugs
**Parameters**: `pref_name__contains` (string), `max_phase` (integer), `limit`

---

## Clinical Trial Tools

### search_clinical_trials
**Purpose**: Search ClinicalTrials.gov
**Parameters**:
- `query_term` (string, REQUIRED): Search query
- `condition` (string): Disease/condition
- `intervention` (string): Drug/intervention
- `pageSize` (integer): Max results (default 10, max 1000)

**Response**: `{studies: [{NCT ID, brief_title, brief_summary, overall_status, condition, phase}], nextPageToken, total_count}`

---

## Literature & Pathway Tools

### PubMed_search_articles
**Purpose**: Search PubMed literature
**Parameters**:
- `query` (string, REQUIRED): PubMed search query
- `limit` (integer, default=10, max 200)
- `include_abstract` (boolean, default=False)

**Response**: Returns a **plain list** of article dicts (NOT wrapped in `{articles: [...]}`):
```python
# [{pmid, title, authors, journal, pub_date, pub_year, doi, pmcid, article_type, url, abstract, ...}]
```

### Reactome_map_uniprot_to_pathways
**Purpose**: Map protein to biological pathways
**Parameters**: `id` (string, REQUIRED): UniProt accession (e.g., 'P00533')

### GTEx_get_median_gene_expression
**Purpose**: Tissue expression data
**Parameters**:
- `gencode_id` (string, REQUIRED): Versioned Ensembl ID (e.g., 'ENSG00000146648.12')
- `operation` (string): Use 'median'

### OpenTargets_target_disease_evidence
**Purpose**: Evidence for target-disease association
**Parameters**: `efoId` (string, REQUIRED), `ensemblId` (string, REQUIRED)

### OpenTargets_get_publications_by_target_ensemblID
**Purpose**: Publications about target
**Parameters**: `ensemblId` (string, REQUIRED)

---

## Known CIViC Gene IDs (Common Cancer Genes)

These are pre-verified CIViC gene IDs to bypass the search limitation:

| Gene | CIViC Gene ID | Entrez ID |
|------|--------------|-----------|
| ABL1 | 4 | 25 |
| ALK | 1 | 238 |
| BRAF | 5 | 673 |

Note: For genes not in this table, use `civic_search_genes(limit=100)` and search results client-side. If gene starts with a letter beyond 'C', it may not be in the first 100 results.
