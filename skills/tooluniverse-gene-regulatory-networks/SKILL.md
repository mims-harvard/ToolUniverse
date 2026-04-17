# Skill: Gene Regulatory Network Analysis

**GRN inference starts with: which TF regulates which gene?** Direct evidence (ChIP-seq binding) is stronger than indirect (co-expression correlation). A TF binding near a gene doesn't prove regulation — check if expression changes when the TF is perturbed. JASPAR provides binding motifs but motif presence in a promoter is only computational evidence (T3); ENCODE ChIP-seq data that places the TF at the locus in the relevant cell type is stronger (T1). eQTLs from GTEx show which variants affect expression but don't identify the upstream regulator — combine with TF motif disruption analysis for mechanistic insight.

**LOOK UP DON'T GUESS**: never assume JASPAR matrix IDs, Enrichr library names, or GTEx tissue identifiers — always search JASPAR by TF name and verify library names before calling enrichr.

## When to Use

Activate this skill when the user asks about:
- Transcription factor (TF) binding sites, motifs, or target genes
- Gene regulatory networks or transcriptional regulation
- Chromatin state and histone modifications in regulatory context
- TF-target relationships and co-regulation
- eQTL effects on gene regulation
- Protein-protein interactions among regulatory factors

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Workflow

### Phase 0: Input Disambiguation

Determine:
- Is the query about a specific TF (e.g., "TP53 regulatory network") or a target gene (e.g., "what regulates CDKN1A")?
- Is a specific tissue/cell type relevant?
- Should the analysis focus on direct binding (motifs) or functional targets (ChIP-seq, enrichment)?

### Phase 1: TF Motif Lookup (JASPAR)

Search JASPAR for the TF's position weight matrix (PWM) and binding motif profile.

**Tool: `jaspar_search_matrices`**
```
Parameters:
  search   string   TF name to search (e.g., "TP53")
  limit    integer  Max results (default 10)
  collection string JASPAR collection filter (e.g., "CORE")
  species  string   Taxonomy ID filter (e.g., "9606" for human)
```

Example:
```json
{"search": "TP53", "limit": 5}
```

Returns `{status, data: {count, results: [{matrix_id, name, collection, base_id, version, sequence_logo}]}}`.

**Tool: `jaspar_get_matrix`** (for detailed motif info)
```
Parameters:
  matrix_id  string  JASPAR matrix ID (e.g., "MA0106.3")
```

Returns PFM (position frequency matrix), species, TF class, UniProt IDs.

### Phase 2: TF Target Genes (Enrichr)

Identify target genes from ChIP-seq experiments via Enrichr.

**Tool: `enrichr_gene_enrichment_analysis`**
```
Parameters:
  gene_list  array   List of gene symbols (REQUIRED)
  library    string  Enrichr library name (default "GO_Biological_Process_2023")
  top_n      integer Top enriched terms to return (default 10)
```

Key libraries for regulatory network analysis:
- `"ENCODE_TF_ChIP-seq_2015"` -- TF binding from ENCODE ChIP-seq
- `"ChEA_2022"` -- ChIP-seq enrichment analysis (broader coverage)
- `"TRRUST_Transcription_Factors_2019"` -- Literature-curated TF-target relationships
- `"ARCHS4_TFs_Coexp"` -- TF co-expression from RNA-seq

Example (find which TFs bind your gene set):
```json
{
  "gene_list": ["CDKN1A", "BAX", "MDM2", "GADD45A", "BBC3"],
  "library": "ENCODE_TF_ChIP-seq_2015",
  "top_n": 10
}
```

Returns `{status, data: {library, gene_count, enriched_terms: [{rank, term, p_value, combined_score, overlapping_genes, adjusted_p_value}]}}`.

**IMPORTANT**: Enrichr takes a gene list and tells you what TFs are enriched. To find targets OF a TF, use the TRRUST library or look up TF ChIP-seq targets directly.

### Phase 3: Regulatory Element Context

#### 3a: Histone Modifications (ENCODE)

**Tool: `ENCODE_search_histone_experiments`**
```
Parameters:
  target   string   Histone mark (e.g., "H3K27ac", "H3K4me3", "H3K27me3")
  tissue   string   Tissue/cell type (e.g., "liver", "brain")
  limit    integer  Max results (default 10)
```

Common histone marks and their meaning:
- `H3K27ac` -- Active enhancers and promoters
- `H3K4me3` -- Active promoters
- `H3K4me1` -- Poised/active enhancers
- `H3K27me3` -- Polycomb-repressed regions
- `H3K9me3` -- Heterochromatin

Example:
```json
{"target": "H3K27ac", "tissue": "liver", "limit": 5}
```

Returns `{status, data: {total, experiments: [{accession, histone_mark, biosample_summary, status, lab}]}}`.

#### 3b: Expression QTLs (GTEx)

**Tool: `GTEx_query_eqtl`**
```
Parameters:
  gene_symbol  string  Gene symbol (e.g., "TP53"). REQUIRED.
```

Returns eQTL SNPs across tissues, showing genetic variants that affect gene expression.

Example:
```json
{"gene_symbol": "TP53"}
```

Returns `{status, data: {singleTissueEqtl: [{snpId, variantId, geneSymbol, pValue, tissueSiteDetailId, nes}]}}`. `nes` = normalized effect size; negative = lower expression with alt allele.

#### 3c: Regulatory Variant Annotation (RegulomeDB)

**Tool: `RegulomeDB_query_variant`**
```
Parameters:
  rsid  string  dbSNP rsID (e.g., "rs7412")
```

Returns regulatory score (1a-7), tissue-specific scores, and overlapping regulatory features.

### Phase 4: Protein Interaction Network

#### 4a: STRING Database

**Tool: `STRING_get_interaction_partners`**
```
Parameters:
  identifiers     string   Protein/gene name (REQUIRED, e.g., "TP53")
  species         integer  NCBI taxonomy ID (default 9606 for human)
  limit           integer  Max partners to return
  required_score  integer  Min combined score 0-1000 (400=medium, 700=high, 900=highest)
```

Example:
```json
{"identifiers": "TP53", "species": 9606, "limit": 10}
```

Returns array of `{preferredName_A, preferredName_B, score, escore, dscore, tscore, ascore}`. Score components: `escore` (experimental), `dscore` (database), `tscore` (text-mining), `ascore` (coexpression).

#### 4b: IntAct Interactions

**Tool: `intact_get_interaction_network`**
```
Parameters:
  gene_symbol  string   Gene symbol (REQUIRED)
  limit        integer  Max results
```

Returns experimentally validated molecular interactions from IntAct.

#### 4c: BioGRID Interactions

**Tool: `BioGRID_get_interactions`**
```
Parameters:
  gene_symbol  string   Gene symbol (REQUIRED)
  limit        integer  Max results
```

Returns physical and genetic interactions with experimental system details.

### Phase 5: Literature Context

**Tool: `EuropePMC_search_articles`**
```
Parameters:
  query  string   Search query (REQUIRED)
  limit  integer  Max results (default 10)
```

Example:
```json
{"query": "TP53 transcription factor regulatory network", "limit": 5}
```

**Tool: `PubMed_search_articles`**
```
Parameters:
  query  string   Search query (REQUIRED)
  limit  integer  Max results (default 10)
```

### Phase 6: Ontology Annotation (Optional)

**Tool: `ols_search_terms`**
```
Parameters:
  query     string  Search term (REQUIRED)
  ontology  string  Ontology ID (e.g., "so" for Sequence Ontology, "go" for Gene Ontology)
  limit     integer Max results
```

Example for regulatory element types:
```json
{"query": "transcription factor binding site", "ontology": "so", "limit": 5}
```

### Phase 7: Functional Enrichment of Network

**Tool: `STRING_functional_enrichment`**
```
Parameters:
  identifiers  string  Comma-separated gene names (REQUIRED)
  species      integer NCBI taxonomy ID (default 9606)
```

Performs GO, KEGG, Reactome enrichment on a gene set from the network.

## Common Mistakes

1. **JASPAR tool name**: Use `jaspar_search_matrices` (lowercase, plural), NOT `jaspar_get_matrix`.

2. **JASPAR search param**: The parameter is `search` (NOT `query` or `name`).

3. **STRING identifiers param**: Use `identifiers` as a **string** (NOT an array). For multiple proteins, use `STRING_get_network` with array `identifiers`.

4. **Enrichr direction**: `enrichr_gene_enrichment_analysis` takes a gene SET and finds enriched TFs/pathways. To find targets of a TF, use `"TRRUST_Transcription_Factors_2019"` library with known target genes, or consult ENCODE ChIP-seq data directly.

5. **Enrichr `gene_list` is required**: Must be a JSON array of strings, not a single string.

6. **GTEx uses `gene_symbol`**: NOT Ensembl ID. The tool resolves it internally.

7. **ENCODE tissue names**: Use lowercase tissue names like `"liver"`, `"brain"`, `"heart"`. Complex queries may fail -- keep tissue names simple.

8. **BioGRID returns interactions as dict**: Keys are interaction IDs, values contain `OFFICIAL_SYMBOL_A` and `OFFICIAL_SYMBOL_B`.

9. **RegulomeDB rsID format**: Must include the "rs" prefix (e.g., `"rs7412"` not `"7412"`).

10. **No TRRUST direct tool**: TRRUST data is accessed via Enrichr library `"TRRUST_Transcription_Factors_2019"`, not a standalone tool.

## Common Use Patterns

### Pattern 1: "What does TF X regulate?"
1. `jaspar_search_matrices` -- Get motif info for TF X
2. `enrichr_gene_enrichment_analysis` with `TRRUST_Transcription_Factors_2019` library -- Use known targets
3. `STRING_get_interaction_partners` -- Find interacting proteins
4. `EuropePMC_search_articles` -- Literature on TF X targets

### Pattern 2: "What regulates gene Y?"
1. `enrichr_gene_enrichment_analysis` with gene Y's co-regulated genes + `ENCODE_TF_ChIP-seq_2015` library
2. `GTEx_query_eqtl` -- Find eQTLs affecting gene Y expression
3. `ENCODE_search_histone_experiments` -- Chromatin context at gene Y locus
4. `RegulomeDB_query_variant` -- Annotate regulatory variants near gene Y

### Pattern 3: "Build a regulatory network around gene set Z"
1. `enrichr_gene_enrichment_analysis` with gene set Z + multiple TF libraries
2. `STRING_get_interaction_partners` for hub genes
3. `STRING_functional_enrichment` -- Pathway context
4. `BioGRID_get_interactions` -- Experimental validation
5. `EuropePMC_search_articles` -- Supporting literature

### Pattern 4: "Tissue-specific regulation of gene X"
1. `GTEx_query_eqtl` -- Tissue-specific eQTLs for gene X
2. `ENCODE_search_histone_experiments` with specific tissue -- Active regulatory marks
3. `RegulomeDB_query_variant` -- Tissue-specific regulatory scores for eQTL SNPs
4. `enrichr_gene_enrichment_analysis` -- Identify TFs active in that tissue

### Pattern 5: "Is variant rs##### regulatory?"
1. `RegulomeDB_query_variant` -- Regulatory score and overlapping features
2. `GTEx_query_eqtl` -- Is this variant an eQTL?
3. `ENCODE_search_histone_experiments` -- Chromatin context at variant locus
4. `EuropePMC_search_articles` -- Literature on the variant

## Evidence Grading

- **T1**: ENCODE ChIP-seq, JASPAR validated motifs, GTEx significant eQTLs
- **T2**: BioGRID/IntAct interactions, TRRUST curated relationships
- **T3**: STRING predicted interactions, Enrichr statistical enrichment
- **T4**: Sequence Ontology terms, literature mentions
