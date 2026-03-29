---
name: tooluniverse-spatial-transcriptomics
description: Analyze spatial transcriptomics data to map gene expression in tissue architecture. Supports 10x Visium, MERFISH, seqFISH, Slide-seq, and imaging-based platforms. Performs spatial clustering, domain identification, cell-cell proximity analysis, spatial gene expression patterns, tissue architecture mapping, and integration with single-cell data. Use when analyzing spatial transcriptomics datasets, studying tissue organization, identifying spatial expression patterns, mapping cell-cell interactions in tissue context, characterizing tumor microenvironment spatial structure, or integrating spatial and single-cell RNA-seq data for comprehensive tissue analysis.
---

# Spatial Transcriptomics Analysis

Comprehensive analysis of spatially-resolved transcriptomics data to understand gene expression patterns in tissue architecture context. Combines expression profiling with spatial coordinates to reveal tissue organization, cell-cell interactions, and spatially variable genes.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

## When to Use This Skill

**Triggers**:
- User has spatial transcriptomics data (Visium, MERFISH, seqFISH, etc.)
- Questions about tissue architecture or spatial organization
- Spatial gene expression pattern analysis
- Cell-cell proximity or neighborhood analysis requests
- Tumor microenvironment spatial structure questions
- Integration of spatial with single-cell data
- Spatial domain identification
- Tissue morphology correlation with expression

**Example Questions**:
1. "Analyze this 10x Visium dataset to identify spatial domains"
2. "Which genes show spatially variable expression in this tissue?"
3. "Map the tumor microenvironment spatial organization"
4. "Find genes enriched at tissue boundaries"
5. "Identify cell-cell interactions based on spatial proximity"
6. "Integrate spatial transcriptomics with scRNA-seq annotations"

---

## Core Capabilities

- **Data Import**: 10x Visium, MERFISH, seqFISH, Slide-seq, STARmap, Xenium formats
- **Quality Control**: Spot/cell QC, spatial alignment verification, tissue coverage
- **Normalization**: Spatial-aware normalization accounting for tissue heterogeneity
- **Spatial Clustering**: Identify spatial domains with similar expression profiles
- **Spatial Variable Genes**: Find genes with non-random spatial patterns
- **Neighborhood Analysis**: Cell-cell proximity, spatial neighborhoods, niche identification
- **Integration**: Merge with scRNA-seq for cell type mapping (Cell2location, Tangram, SPOTlight)
- **Ligand-Receptor Spatial**: Map cell communication in tissue context via OmniPath

## Supported Platforms

- **10x Visium**: 55um spots (~50 cells/spot), genome-wide, includes H&E image — most common
- **MERFISH/seqFISH**: Single-cell resolution, 100-10,000 targeted genes, imaging-based
- **Slide-seq/V2**: 10um beads, genome-wide — higher resolution than Visium
- **Xenium**: Single-cell/subcellular, 300+ targeted genes (10x platform)

---

## Workflow Overview

```
Input: Spatial Transcriptomics Data + Tissue Image
    |
    v
Phase 1: Data Import & QC
    |-- Load spatial coordinates + expression matrix
    |-- Load tissue histology image
    |-- Quality control per spot/cell (min 200 genes, 500 UMI, <20% MT)
    |-- Align spatial coordinates to tissue
    |
    v
Phase 2: Preprocessing
    |-- Normalization (spatial-aware methods)
    |-- Highly variable gene selection (top 2000)
    |-- Dimensionality reduction (PCA)
    |-- Spatial lag smoothing (optional)
    |
    v
Phase 3: Spatial Clustering
    |-- Build spatial neighbor graph (squidpy)
    |-- Graph-based clustering with spatial constraints (Leiden)
    |-- Annotate domains with marker genes (Wilcoxon)
    |-- Visualize domains on tissue
    |
    v
Phase 4: Spatial Variable Genes
    |-- Test spatial autocorrelation (Moran's I, Geary's C)
    |-- Filter significant spatial genes (FDR < 0.05)
    |-- Classify pattern types (gradient, hotspot, boundary, periodic)
    |
    v
Phase 5: Neighborhood Analysis
    |-- Define spatial neighborhoods (k-NN, radius)
    |-- Calculate neighborhood composition (squidpy nhood_enrichment)
    |-- Identify interaction zones between domains
    |
    v
Phase 6: Integration with scRNA-seq
    |-- Cell type deconvolution (Cell2location, Tangram, SPOTlight)
    |-- Map cell types to spatial locations
    |-- Validate with marker genes
    |
    v
Phase 7: Spatial Cell Communication
    |-- Identify proximal cell type pairs
    |-- Query ligand-receptor database (OmniPath)
    |-- Score spatial interactions (squidpy ligrec)
    |-- Map communication hotspots
    |
    v
Phase 8: Generate Spatial Report
    |-- Tissue overview with domains
    |-- Spatially variable genes
    |-- Cell type spatial maps
    |-- Interaction networks in tissue context
```

---

## Phase Summaries

### Phase 1: Data Import & QC
Load platform-specific data (scanpy read_visium for Visium). Apply QC filters: min 200 genes/spot, min 500 UMI/spot, max 20% mitochondrial. Verify spatial alignment with tissue image overlay.

### Phase 2: Preprocessing
Normalize to median total counts, log-transform, select top 2000 HVGs. Optional spatial smoothing via neighbor averaging (useful for noisy data but blurs boundaries).

### Phase 3: Spatial Clustering
PCA (50 components) followed by spatial neighbor graph construction (squidpy). Leiden clustering with spatial constraints yields spatial domains. Find domain markers via Wilcoxon rank-sum test.

### Phase 4: Spatially Variable Genes
Moran's I statistic tests spatial autocorrelation: I > 0 = clustering, I ~ 0 = random, I < 0 = checkerboard. Filter by FDR < 0.05. Classify patterns as gradient, hotspot, boundary, or periodic.

### Phase 5: Neighborhood Analysis
Neighborhood enrichment analysis (squidpy) tests whether cell types/domains are co-localized beyond random expectation. Identify interaction zones at domain boundaries using k-NN spatial graphs.

### Phase 6: scRNA-seq Integration
Cell type deconvolution maps single-cell annotations to spatial spots. Methods: Cell2location (recommended for Visium), Tangram, SPOTlight. Produces cell type fraction estimates per spot.

### Phase 7: Spatial Cell Communication

Combine spatial proximity with ligand-receptor databases. Key ToolUniverse tools:
- `OmniPath_get_ligand_receptor_interactions` — 14,000+ L-R pairs from CellPhoneDB, CellChatDB, etc. Use `partners` param for specific genes.
- `OmniPath_get_intercell_roles` — classify proteins as ligand/receptor/ECM. Use `proteins` param.
- `OmniPath_get_cell_communication_annotations` — CellPhoneDB/CellChatDB pathway annotations. Use `proteins` param.
- `OmniPath_get_signaling_interactions` — intracellular signaling downstream of receptors.

Score interactions by co-expression of L-R pairs in proximal cells. Map hotspots where interaction scores peak.

### Phase 7.5: Data Discovery & Gene Context (ToolUniverse API tools)

For dataset discovery and gene annotation (API-based, no local computation needed):
- `geo_search_datasets` / `OmicsDI_search_datasets` / `NCBI_SRA_search_runs` — find spatial TX datasets
- `UniProt_get_function_by_accession` — protein function for stroma/immune markers
- `STRING_get_network` — protein interaction networks for key markers
- `kegg_search_pathway` / `kegg_get_pathway_info` — relevant metabolic/signaling pathways
- `DGIdb_get_drug_gene_interactions` — druggable targets in the spatial context
- `PubMed_search_articles` — literature for spatial biology context

> **API tools vs. local computation**: Phases 1-2 (data import, QC) and Phases 3-6 (clustering, SVGs, neighborhoods, deconvolution) require local Python with squidpy/scanpy. Phase 7 L-R databases and Phase 7.5 gene context use ToolUniverse API tools.

### Phase 8: Report Generation
See [report_template.md](report_template.md) for full example output.

---

## Integration with ToolUniverse Skills

- `tooluniverse-single-cell`: scRNA-seq reference for deconvolution (Phase 6) and L-R database (Phase 7)
- `tooluniverse-gene-enrichment`: Pathway enrichment for spatial domain marker genes (Phase 3)
- `tooluniverse-multi-omics-integration`: Integration with other omics layers (Phase 8)

## ToolUniverse Data Retrieval Tools

### HuBMAP Spatial Atlas Tools

Use HuBMAP tools to discover published spatial biology datasets for reference, validation, or cross-study comparison.

> **Availability Note**: `HuBMAP_search_datasets`, `HuBMAP_list_organs`, and `HuBMAP_get_dataset` may not be registered in your ToolUniverse instance. Verify with `tu.list_tools()` before use. If unavailable, use **OmicsDI** (`OmicsDI_search_datasets(query="spatial transcriptomics kidney")`) or **CELLxGENE** (`CELLxGENE_get_cell_metadata`) as reliable alternatives for spatial dataset discovery.

- `HuBMAP_search_datasets`: Search published datasets by `organ` (code, e.g. "LK"=Left Kidney, "BR"=Brain), `dataset_type`, `query`, `limit`
- `HuBMAP_list_organs`: List all organs with codes and UBERON IDs (no required params)
- `HuBMAP_get_dataset`: Get detailed metadata for a specific `hubmap_id` (e.g. "HBM626.FHJD.938")

Organ codes: LK/RK=Kidney, LI=Large Intestine, SI=Small Intestine, HT=Heart, LV=Liver, LU=Lung, SP=Spleen, BR=Brain, PA=Pancreas, SK=Skin.

**When to use**:
- Finding reference spatial datasets for a given organ/tissue
- Identifying available spatial assay types (Visium, CODEX, MERFISH) for a tissue
- Cross-referencing donor metadata (age, sex) for spatial datasets
- Retrieving DOI links for published spatial atlas datasets

**Fallback if HuBMAP tools unavailable**:
```python
# Use OmicsDI for spatial dataset discovery
result = tu.tools.OmicsDI_search_datasets(query="spatial transcriptomics kidney Visium")

# Use CELLxGENE for cell-level expression context
result = tu.tools.CELLxGENE_get_cell_metadata(tissue="kidney")
```

```python
# Example: Find spatial datasets for kidney (if HuBMAP tools available)
result = tu.tools.HuBMAP_search_datasets(organ="LK", limit=5)
# Returns: {data: {total, returned, datasets: [{hubmap_id, title, dataset_type, organ, doi_url, ...}]}}

# Example: Get all available organs
organs = tu.tools.HuBMAP_list_organs()
# Returns: {data: {total, organs: [{code, term, organ_uberon, rui_supported}]}}
```

---

## Example Use Cases

### Use Case 1: Tumor Microenvironment Mapping
**Question**: "Map the spatial organization of tumor, immune, and stromal cells"
**Workflow**: Load Visium -> QC -> Spatial clustering -> Deconvolution -> Interaction zones -> L-R analysis -> Report

### Use Case 2: Developmental Gradient Analysis
**Question**: "Identify spatial gene expression gradients in developing tissue"
**Workflow**: Load spatial data -> SVG analysis -> Classify gradient patterns -> Map morphogens -> Correlate with cell fate -> Report

### Use Case 3: Brain Region Identification
**Question**: "Automatically segment brain tissue into anatomical regions"
**Workflow**: Load Visium brain -> High-resolution clustering -> Match to known regions -> Validate with Allen Brain Atlas -> Report

---

## Quantified Minimums

- At least 500 spatial locations after QC
- Filter low-quality spots (min 200 genes, min 500 UMI, <20% MT) and verify alignment
- At least one spatial clustering method (graph-based with spatial constraints)
- Spatially variable genes tested with Moran's I or equivalent (FDR < 0.05)
- Spatial plots on tissue images for all major findings
- Report covers: domains, spatial genes, cell type maps, key interactions

---

## Reasoning Framework

### Starting Point: What Is the Spatial Question?

Spatial data adds location to expression. The key question: is the spatial pattern driven by cell type composition (trivial) or by spatially-regulated gene expression within the same cell type (interesting)? Deconvolution helps distinguish these.

Before interpreting any spatially variable gene (SVG), ask:
1. Does this gene simply mark a cell type that is spatially restricted? (e.g., a T-cell marker enriched in immune infiltrate zones — expected, not informative)
2. Or is the gene differentially expressed within the same cell type depending on its spatial position? (e.g., a fibroblast gene upregulated at the tumor-stroma boundary — spatially regulated, biologically interesting)

To distinguish these: (a) run deconvolution (Cell2location, Tangram) to get cell type fractions per spot; (b) regress SVG expression against cell type fraction; (c) if the spatial pattern persists after controlling for cell type composition, it reflects genuine spatial regulation. Always look up the gene's known biology before interpreting — check UniProt function and STRING interactions rather than guessing.

### Evidence Grading

- **T1**: Validated by orthogonal method (IHC, smFISH, known anatomy) — e.g., spatial domain matches histology-confirmed tumor margin
- **T2**: Statistically significant, biologically consistent — SVG with Moran's I > 0.3 and FDR < 0.01 in expected tissue region
- **T3**: Computationally identified, awaiting validation — novel spatial domain from clustering with no histological correlate
- **T4**: Exploratory or artifact-prone — low-UMI edge spots, domains driven by batch effects

### Interpretation Guidance

**Spatial domains**: Domains represent regions of coherent gene expression, often corresponding to tissue architecture (tumor core, stroma, immune infiltrate, necrosis). A domain is biologically meaningful when its marker genes align with known cell type signatures. Domains at tissue boundaries (e.g., tumor-stroma interface) are particularly informative for microenvironment studies.

**Cell-cell proximity significance**: Neighborhood enrichment z-scores > 2 indicate cell types co-localize more than expected by chance. Negative z-scores indicate spatial avoidance. Interpret in biological context: immune cell enrichment near tumor cells may indicate active immune response or immunosuppressive niche depending on the cell types involved (e.g., CD8+ T cells vs. Tregs).

**Spatially variable genes (SVGs)**: Moran's I > 0.3 with FDR < 0.05 indicates strong spatial patterning. Classify SVGs by pattern: gradients (morphogen signaling, e.g., WNT along crypt-villus axis), hotspots (focal expression in immune aggregates), boundary genes (enriched at domain interfaces, e.g., epithelial-mesenchymal transition markers). SVGs with known spatial biology roles (e.g., tissue polarity genes) are higher confidence than novel candidates.

### Synthesis Questions

A complete spatial transcriptomics report should answer:
1. What spatial domains were identified, and do they correspond to known tissue architecture?
2. Which genes show significant spatial variability, and what pattern types do they exhibit?
3. Are specific cell type pairs enriched or depleted in spatial proximity?
4. What ligand-receptor interactions are active at domain boundaries or cell-cell interfaces?
5. How do spatial findings compare to bulk or single-cell data from the same tissue type?

---

## Programmatic Access (Beyond Tools)

When ToolUniverse tools return metadata but you need the actual expression matrices:

```python
import scanpy as sc, pandas as pd, requests, io

# Load h5ad (most common format for spatial/single-cell)
adata = sc.read_h5ad("spatial_data.h5ad")

# Load 10X Visium output directory
adata = sc.read_visium("path/to/spaceranger_output/")

# Download from GEO supplementary files
geo_id = "GSE123456"
# Check for h5ad or MTX in supplementary files
url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={geo_id}&targ=gsm&view=data"

# Load 10X MTX format (matrix + barcodes + features)
adata = sc.read_10x_mtx("filtered_feature_bc_matrix/", var_names="gene_symbols")

# HuBMAP data portal
# Search at https://portal.hubmapconsortium.org/search then download via globus or direct link
# Human Cell Atlas: https://data.humancellatlas.org/ — download h5ad/loom files
```

See `tooluniverse-data-wrangling` skill for format cookbook and bulk download patterns.

---

## Limitations

- **Resolution**: Visium spots contain multiple cells (not single-cell)
- **Gene coverage**: Imaging methods have limited gene panels
- **3D structure**: Most platforms are 2D sections
- **Tissue quality**: Requires well-preserved tissue for imaging
- **Computational**: Large datasets require significant memory
- **Reference dependency**: Deconvolution quality depends on scRNA-seq reference

---

## References

**Methods**:
- Squidpy: https://doi.org/10.1038/s41592-021-01358-2
- Cell2location: https://doi.org/10.1038/s41587-021-01139-4
- SpatialDE: https://doi.org/10.1038/nmeth.4636

**Platforms**:
- 10x Visium: https://www.10xgenomics.com/products/spatial-gene-expression
- MERFISH: https://doi.org/10.1126/science.aaa6090
- Slide-seq: https://doi.org/10.1126/science.aaw1219

---

## Reference Files

- [code_examples.md](code_examples.md) - Python code for all phases (scanpy, squidpy, cell2location)
- [report_template.md](report_template.md) - Full example report (breast cancer TME)
