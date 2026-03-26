---
name: tooluniverse-spatial-transcriptomics
description: Analyze spatial transcriptomics data to map gene expression in tissue architecture. Supports 10x Visium, MERFISH, seqFISH, Slide-seq, and imaging-based platforms. Performs spatial clustering, domain identification, cell-cell proximity analysis, spatial gene expression patterns, tissue architecture mapping, and integration with single-cell data. Use when analyzing spatial transcriptomics datasets, studying tissue organization, identifying spatial expression patterns, mapping cell-cell interactions in tissue context, characterizing tumor microenvironment spatial structure, or integrating spatial and single-cell RNA-seq data for comprehensive tissue analysis.
---

# Spatial Transcriptomics Analysis

Comprehensive analysis of spatially-resolved transcriptomics data to understand gene expression patterns in tissue architecture context. Combines expression profiling with spatial coordinates to reveal tissue organization, cell-cell interactions, and spatially variable genes.

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

| Capability | Description |
|-----------|-------------|
| **Data Import** | 10x Visium, MERFISH, seqFISH, Slide-seq, STARmap, Xenium formats |
| **Quality Control** | Spot/cell QC, spatial alignment verification, tissue coverage |
| **Normalization** | Spatial-aware normalization accounting for tissue heterogeneity |
| **Spatial Clustering** | Identify spatial domains with similar expression profiles |
| **Spatial Variable Genes** | Find genes with non-random spatial patterns |
| **Neighborhood Analysis** | Cell-cell proximity, spatial neighborhoods, niche identification |
| **Spatial Patterns** | Gradients, boundaries, hotspots, expression waves |
| **Integration** | Merge with scRNA-seq for cell type mapping |
| **Ligand-Receptor Spatial** | Map cell communication in tissue context |
| **Visualization** | Spatial plots, heatmaps on tissue, 3D reconstruction |

---

## Supported Platforms

| Platform | Resolution | Genes | Notes |
|----------|-----------|-------|-------|
| **10x Visium** | 55um spots (~50 cells/spot) | Genome-wide | Most common, includes H&E image |
| **MERFISH/seqFISH** | Single-cell | 100-10,000 (targeted) | Imaging-based, absolute coordinates |
| **Slide-seq/V2** | 10um beads | Genome-wide | Higher resolution than Visium |
| **Xenium** | Single-cell, subcellular | 300+ (targeted) | 10x single-cell spatial |

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

| Skill | Used For | Phase |
|-------|----------|-------|
| `tooluniverse-single-cell` | scRNA-seq reference for deconvolution | Phase 6 |
| `tooluniverse-single-cell` (Phase 10) | L-R database for communication | Phase 7 |
| `tooluniverse-gene-enrichment` | Pathway enrichment for spatial domains | Phase 3 |
| `tooluniverse-multi-omics-integration` | Integrate with other omics | Phase 8 |

## ToolUniverse Data Retrieval Tools

### HuBMAP Spatial Atlas Tools

Use HuBMAP tools to discover published spatial biology datasets for reference, validation, or cross-study comparison.

> **Availability Note**: `HuBMAP_search_datasets`, `HuBMAP_list_organs`, and `HuBMAP_get_dataset` may not be registered in your ToolUniverse instance. Verify with `tu.list_tools()` before use. If unavailable, use **OmicsDI** (`OmicsDI_search_datasets(query="spatial transcriptomics kidney")`) or **CELLxGENE** (`CELLxGENE_get_cell_metadata`) as reliable alternatives for spatial dataset discovery.

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `HuBMAP_search_datasets` | Search HuBMAP published datasets by organ, assay, or keyword | `organ` (code, e.g. "LK"="Left Kidney", "BR"="Brain"), `dataset_type` (e.g. "RNAseq", "CODEX", "MALDI"), `query` (free text), `limit` (default 10) |
| `HuBMAP_list_organs` | List all organs with codes and UBERON IDs | (no required params) |
| `HuBMAP_get_dataset` | Get detailed metadata for a specific dataset | `hubmap_id` (e.g. "HBM626.FHJD.938") |

**Organ codes**: LK=Left Kidney, RK=Right Kidney, LI=Large Intestine, SI=Small Intestine, HT=Heart, LV=Liver, LU=Lung, SP=Spleen, TH=Thymus, LY=Lymph Node, BL=Bladder, PA=Pancreas, SK=Skin, BR=Brain, BM=Bone Marrow, MU=Muscle.

**Assay types**: RNAseq, CODEX, MALDI, snATACseq, LC-MS, scRNAseq-10xGenomics-v3, and more.

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

| Component | Requirement |
|-----------|-------------|
| Spots/cells | At least 500 spatial locations |
| QC | Filter low-quality spots, verify alignment |
| Spatial clustering | At least one method (graph-based or spatial) |
| Spatial genes | Moran's I or similar spatial test |
| Visualization | Spatial plots on tissue images |
| Report | Domains, spatial genes, visualizations |

---

## Reasoning Framework

### Evidence Grading

| Tier | Description | Example |
|------|-------------|---------|
| **T1** | Validated by orthogonal method (IHC, smFISH, known anatomy) | Spatial domain matches histology-confirmed tumor margin |
| **T2** | Statistically significant, biologically consistent | SVG with Moran's I > 0.3 and FDR < 0.01 in expected tissue region |
| **T3** | Computationally identified, awaiting validation | Novel spatial domain from clustering with no histological correlate |
| **T4** | Exploratory or artifact-prone | Low-UMI edge spots, domains driven by batch effects |

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
