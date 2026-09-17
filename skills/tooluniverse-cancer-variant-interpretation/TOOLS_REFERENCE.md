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

## Variant Annotation & Cancer Hotspot Tools (Genome Nexus)

Genome Nexus (Memorial Sloan Kettering, genomenexus.org — the same annotator behind cBioPortal) aggregates VEP consequence prediction, SIFT, PolyPhen-2, AlphaMissense, and the Chang et al. cancer hotspot database into one call. **All coordinate-based inputs require GRCh37/hg19** — do not pass GRCh38 coordinates.

### GenomeNexus_annotate_variant
**Purpose**: Full annotation from an HGVS genomic variant
**Parameters**: `hgvsg` (string, REQUIRED): GRCh37 HGVS genomic notation, e.g. `'7:g.140453136A>T'` (BRAF V600E), `'17:g.7577120C>T'` (TP53 R273H)

**Response** (live-verified, BRAF V600E): `{status, data: {variant, hgvsg, assembly_name: "GRCh37", most_severe_consequence: "missense_variant", annotation_summary: {genomicLocation, canonicalTranscriptId, transcriptConsequences: [...]}, transcript_consequences: [{gene_symbol, transcript_id, hgvsp, hgvsc, amino_acids, sift_prediction, sift_score, polyphen_prediction, polyphen_score, alphaMissense: {score, pathogenicity}, canonical, exon}], hotspots: {annotation: [[{hugoSymbol, residue, tumorCount, type}], ...]}, colocated_variants: [{dbSnpId}]}, metadata}`
```python
result = tu.tools.GenomeNexus_annotate_variant(hgvsg="7:g.140453136A>T")
# transcript_consequences[0] (canonical) = {
#   gene_symbol: "BRAF", hgvsp: "ENSP00000288602.6:p.Val600Glu", hgvsc: "ENST00000288602.6:c.1799T>A",
#   sift_prediction: "deleterious", sift_score: 0.0,
#   polyphen_prediction: "probably_damaging", polyphen_score: 0.963,
#   alphaMissense: {score: 0.9927, pathogenicity: "pathogenic"}, canonical: "1"
# }
# Non-canonical transcripts in the same list often have alphaMissense: null and canonical: null --
# always read the canonical="1" entry for the headline call.
```

### GenomeNexus_annotate_mutation
**Purpose**: Same annotation as `annotate_variant`, from separate coordinate fields instead of an HGVS string
**Parameters**: `chromosome` (string, no 'chr' prefix), `start` (int, GRCh37, 1-based), `end` (int), `reference_allele` (string), `variant_allele` (string) — all REQUIRED
**Response**: identical shape to `GenomeNexus_annotate_variant`. Use when your upstream source (e.g. a VCF row) already gives you chrom/pos/ref/alt separately rather than an HGVS string.

### GenomeNexus_annotate_dbsnp
**Purpose**: Same annotation, resolved from a dbSNP rsID instead of coordinates
**Parameters**: `rsid` (string, REQUIRED): e.g. `'rs121913529'` (KRAS G12 codon). A bare numeric ID is accepted and auto-prefixed with `'rs'`.
**Response**: identical shape, but `hgvsg`/`assembly_name` may come back `null` if Genome Nexus can't uniquely resolve the rsID to one genomic position — check for `null` before assuming the lookup fully succeeded.

### GenomeNexus_get_cancer_hotspots
**Purpose**: Direct hotspot-only lookup (a filtered subset of what `annotate_variant`'s `hotspots` field already contains) — use this when you only need a yes/no answer plus tumor counts, without the full VEP annotation payload
**Parameters**: `hgvsg` (string, REQUIRED, GRCh37)
**Response** (live-verified, BRAF V600E): `{status, data: {variant, gene_symbol: "BRAF", is_hotspot: true, hotspots: [{hugoSymbol: "BRAF", residue: "V600", tumorCount: 897, type: "single residue"}, {..., tumorCount: 545, type: "3d"}]}, metadata}`. `type: "3d"` means the residue clusters spatially in the folded protein with other recurrently-mutated residues even if not individually as frequent — still evidence of a functional hotspot region.

### GenomeNexus_get_canonical_transcript
**Purpose**: Resolve a gene symbol to its canonical Ensembl transcript/protein and Pfam domain architecture — useful before annotation to confirm which transcript ID should be treated as canonical, or for a quick domain-architecture overview
**Parameters**: `gene_symbol` (string, REQUIRED): HUGO symbol, e.g. `'BRAF'`, `'TP53'`
**Response** (live-verified, BRAF): `{status, data: {transcriptId: "ENST00000288602", geneId: "ENSG00000157764", proteinId: "ENSP00000288602", proteinLength: 766, hugoSymbols: ["BRAF"], refseqMrnaId: "NM_004333", ccdsId: "CCDS5863", pfamDomains: [{pfamDomainId, pfamDomainStart, pfamDomainEnd, pfamDomainDescription}]}}`. Note `pfamDomainDescription` was `null` for every domain in this live response even though the fields are populated — do not assume a human-readable domain name will always be present; fall back to reporting the raw Pfam ID (e.g. `PF07714` = protein kinase domain, look up via Pfam/InterPro if a name is needed).

---

## Known CIViC Gene IDs (Common Cancer Genes)

These are pre-verified CIViC gene IDs to bypass the search limitation:

| Gene | CIViC Gene ID | Entrez ID |
|------|--------------|-----------|
| ABL1 | 4 | 25 |
| ALK | 1 | 238 |
| BRAF | 5 | 673 |

Note: For genes not in this table, use `civic_search_genes(limit=100)` and search results client-side. If gene starts with a letter beyond 'C', it may not be in the first 100 results.
