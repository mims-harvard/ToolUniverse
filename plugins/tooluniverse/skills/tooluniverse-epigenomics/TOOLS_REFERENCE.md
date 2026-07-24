# ToolUniverse Tool Parameter Reference

Detailed parameter specifications and return schemas for all ToolUniverse tools used in the epigenomics skill.

---

## Regulatory Annotation Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `ensembl_lookup_gene` | `id: str`, `species: str` (REQUIRED) | `{status, data: {id, display_name, seq_region_name, start, end, strand, biotype}, url}` |
| `ensembl_get_regulatory_features` | `region: str` (no "chr"), `feature: str`, `species: str` | `{status, data: [...features...]}` |
| `ensembl_get_overlap_features` | `region: str`, `feature: str`, `species: str` | Gene/transcript overlap data |
| `SCREEN_get_regulatory_elements` | `gene_name: str`, `element_type: str`, `limit: int` | cCREs (enhancers, promoters, insulators) |
| `ReMap_get_transcription_factor_binding` | `gene_name: str`, `cell_type: str`, `limit: int` | TF binding sites |
| `RegulomeDB_query_variant` | `rsid: str` | `{status, data, url}` regulatory score |
| `jaspar_search_matrices` | `search: str`, `collection: str`, `species: str` | `{count, results: [...matrices...]}` |
| `ENCODE_search_experiments` | `assay_title: str`, `target: str`, `organism: str`, `limit: int` | Experiment metadata |
| `ChIPAtlas_get_experiments` | `operation: str` (REQUIRED: "get_experiment_list"), `genome: str`, `antigen: str`, `cell_type: str`, `limit: int` | Experiment list |
| `ChIPAtlas_search_datasets` | `operation` REQUIRED, `antigenList/celltypeList` | Dataset search results |
| `ChIPAtlas_enrichment_analysis` | Various input types (BED regions, motifs, genes) | Enrichment results |
| `ChIPAtlas_get_peak_data` | `operation` REQUIRED | Peak data download URLs |
| `FourDN_search_data` | `operation: str` (REQUIRED: "search_data"), `assay_title: str`, `limit: int` | Chromatin conformation data |

## Gene Annotation Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `MyGene_query_genes` | `query: str` | `{hits: [{_id, symbol, ensembl, ...}]}` |
| `MyGene_batch_query` | `gene_ids: list[str]`, `fields: str` | `{results: [{query, symbol, ...}]}` |
| `HGNC_fetch_gene_by_symbol` | `symbol: str` | Gene symbol, aliases, IDs |
| `GO_get_annotations_for_gene` | `gene_id: str` | GO annotations |

## Sequencing Data Retrieval Tools (SRA)

| Tool | Parameters | Returns |
|------|-----------|---------|
| `SRA_search_experiments` | `query: str`, `organism: str` (e.g. "Homo sapiens"), `library_strategy: str` ("ChIP-Seq", "Bisulfite-Seq", "ATAC-seq", "RNA-Seq"), `platform: str` ("ILLUMINA"), `limit: int` (default 10) | `{data: {total, returned, query_used, experiments: [{uid, title, organism, platform, library_strategy, experiment_accession, study_accession, bioproject, runs}]}}` |
| `SRA_get_experiment` | `accession: str` (SRX/ERX/DRX/SRP/ERP/DRP/SRS/ERS/DRS) | Full experiment metadata with title, organism, platform, library info, runs |

**Use cases**: Finding raw ChIP-seq/Bisulfite-Seq/ATAC-seq experiments for cross-study comparison, identifying available datasets for a tissue/condition, retrieving SRA accessions for data download.

---

## Critical Tool Notes

- **ensembl_lookup_gene**: REQUIRES `species='homo_sapiens'` parameter -- will fail without it
- **ensembl_get_regulatory_features**: Region format is `"17:start-end"` (NO "chr" prefix)
- **ChIPAtlas tools**: ALL require `operation` parameter (SOAP-style API)
- **FourDN tools**: ALL require `operation` parameter (SOAP-style API)
- **SCREEN**: Returns JSON-LD format with `@context, @graph` keys
- **ENCODE_search_experiments**: `assay_title` must be `"TF ChIP-seq"` not `"ChIP-seq"` (see Feature-73B)
- **RegulomeDB_query_variant**: Use `genome=GRCh38` not `assembly=hg19`; test with real rsIDs like rs4994
