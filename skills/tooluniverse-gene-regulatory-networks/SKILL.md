# Skill: Gene Regulatory Network Analysis

Analyze gene regulatory networks by integrating transcription factor binding motifs, target genes, regulatory elements, protein interactions, and expression QTLs using ToolUniverse tools.

## When to Use

Activate this skill when the user asks about:
- Transcription factor (TF) binding sites, motifs, or target genes
- Gene regulatory networks or transcriptional regulation
- Chromatin state and histone modifications in regulatory context
- TF-target relationships and co-regulation
- eQTL effects on gene regulation
- Protein-protein interactions among regulatory factors

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

Response structure:
```json
{
  "status": "success",
  "data": {
    "count": 5,
    "results": [
      {
        "matrix_id": "MA0106.3",
        "name": "TP53",
        "collection": "CORE",
        "base_id": "MA0106",
        "version": "3",
        "sequence_logo": "https://jaspar.elixir.no/static/logos/svg/MA0106.3.svg"
      }
    ]
  }
}
```

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

Response structure:
```json
{
  "status": "success",
  "data": {
    "library": "ENCODE_TF_ChIP-seq_2015",
    "gene_count": 5,
    "enriched_terms": [
      {
        "rank": 1,
        "term": "EP300 HeLa-S3 hg19",
        "p_value": 0.00028,
        "combined_score": 337.16,
        "overlapping_genes": ["MYC", "BRCA1", "TP53"],
        "adjusted_p_value": 0.127,
        "overlap_count": 4
      }
    ]
  }
}
```

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

Response structure:
```json
{
  "status": "success",
  "data": {
    "total": 3,
    "experiments": [
      {
        "accession": "ENCSR458RRZ",
        "histone_mark": "H3K27ac",
        "biosample_summary": "Homo sapiens liver tissue male adult (32 years)",
        "status": "released",
        "lab": "Bing Ren, UCSD"
      }
    ]
  }
}
```

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

Response structure:
```json
{
  "status": "success",
  "data": {
    "singleTissueEqtl": [
      {
        "snpId": "rs78378222",
        "variantId": "chr17_7668434_T_G_b38",
        "geneSymbol": "TP53",
        "pValue": 2.05e-10,
        "tissueSiteDetailId": "Skin_Not_Sun_Exposed_Suprapubic",
        "nes": -0.581
      }
    ]
  }
}
```

**NOTE**: `nes` = normalized effect size. Negative = lower expression with alt allele.

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

Response structure:
```json
{
  "status": "success",
  "data": [
    {
      "preferredName_A": "TP53",
      "preferredName_B": "EP300",
      "score": 0.999,
      "escore": 0.999,
      "dscore": 0.9,
      "tscore": 0.998
    }
  ]
}
```

Score components: `escore` (experimental), `dscore` (database), `tscore` (text-mining), `ascore` (coexpression), `nscore` (neighborhood), `fscore` (fusion), `pscore` (phylogenetic).

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

---

## Quick Reference: All Tools and Parameters

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `jaspar_search_matrices` | `search`, `limit`, `collection`, `species` | Search by TF name |
| `jaspar_get_matrix` | `matrix_id` | Full PFM details for one matrix |
| `enrichr_gene_enrichment_analysis` | `gene_list` (array, REQUIRED), `library`, `top_n` | Many TF-related libraries |
| `ENCODE_search_histone_experiments` | `target`, `tissue`, `limit` | Histone mark ChIP-seq |
| `GTEx_query_eqtl` | `gene_symbol` (REQUIRED) | eQTLs across GTEx tissues |
| `RegulomeDB_query_variant` | `rsid` | Regulatory variant scoring |
| `STRING_get_interaction_partners` | `identifiers` (string, REQUIRED), `species`, `limit` | PPI with confidence scores |
| `STRING_functional_enrichment` | `protein_ids` (array), `species`, `category` | GO/KEGG/Reactome enrichment |
| `OmniPath_get_signaling_interactions` | `proteins`, `datasets` ("dorothea") | **Best for TF-target networks**: curated directed TF-target interactions |
| `ChIPAtlas_enrichment_analysis` | `gene_list`, `genome`, `antigen_class` | TF enrichment from 433K+ ChIP-seq experiments |
| `DGIdb_get_drug_gene_interactions` | `genes` (array) | Druggability of network nodes |
| `CTD_get_gene_diseases` | `input_terms` | Disease context for regulatory genes |
| `intact_get_interaction_network` | `gene_symbol`, `limit` | Experimentally validated PPIs |
| `BioGRID_get_interactions` | `gene_symbol`, `limit` | Physical + genetic interactions |
| `EuropePMC_search_articles` | `query`, `limit` | Full-text literature search |
| `PubMed_search_articles` | `query`, `limit` | PubMed indexed articles |
| `ols_search_terms` | `query`, `ontology`, `limit` | Ontology term lookup |

## Common Mistakes

1. **JASPAR tool name**: Use `jaspar_search_matrices` (lowercase, plural), NOT `jaspar_search_matrices`.

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

- **T1 (Regulatory)**: ENCODE ChIP-seq, JASPAR validated motifs, GTEx significant eQTLs
- **T2 (Experimental)**: BioGRID/IntAct interactions, TRRUST curated relationships
- **T3 (Computational)**: STRING predicted interactions, Enrichr statistical enrichment
- **T4 (Annotation)**: Sequence Ontology terms, literature mentions
