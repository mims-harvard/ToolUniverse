# Spatial Transcriptomics Report Template

## Example Report: Breast Cancer Tumor Section

```markdown
# Spatial Transcriptomics Analysis Report

## Dataset Summary
- **Platform**: 10x Visium
- **Tissue**: Breast cancer tumor section
- **Spots**: 3,562 (after QC filtering)
- **Genes**: 18,432 detected
- **Resolution**: 55um spot diameter (~50 cells/spot)

## Quality Control
- **Mean genes per spot**: 3,245
- **Mean UMI counts**: 12,543
- **Mitochondrial content**: 8.2% average
- **Tissue coverage**: 85% of capture area

## Spatial Domains Identified
- **7 distinct spatial domains** detected via graph-based clustering
  - Domain 1: Tumor core (32% of tissue)
  - Domain 2: Invasive margin (18%)
  - Domain 3: Stromal region (25%)
  - Domain 4: Immune infiltrate (12%)
  - Domain 5: Necrotic region (8%)
  - Domain 6: Normal epithelium (3%)
  - Domain 7: Adipose tissue (2%)

## Top Marker Genes per Domain

### Domain 1 (Tumor Core)
- EPCAM, KRT19, MKI67, CCNB1, TOP2A (proliferative tumor)

### Domain 2 (Invasive Margin)
- VIM, FN1, MMP2, SNAI2 (EMT signature)

### Domain 4 (Immune Infiltrate)
- CD3D, CD8A, CD4, PTPRC (T cell enriched)
- CD68, CD14 (macrophage enriched)

## Spatially Variable Genes
- **456 genes with significant spatial patterns** (Moran's I, FDR < 0.05)

### Top 10 Spatial Genes
1. **MKI67** (I=0.82) - Hotspot pattern in tumor core
2. **CD8A** (I=0.78) - Gradient from margin to stroma
3. **VIM** (I=0.75) - Boundary enrichment at invasive margin
4. **COL1A1** (I=0.71) - Stromal-specific expression
5. **EPCAM** (I=0.69) - Tumor region pattern

## Cell Type Deconvolution
Integration with scRNA-seq reference (Bassez et al. 2021)

### Cell Type Spatial Distributions
- **Tumor cells**: Concentrated in core, sparse at margin
- **T cells**: Enriched at invasive margin and infiltrate zones
- **CAFs**: Stromal region and invasive margin
- **Macrophages**: Scattered, enriched near necrosis
- **B cells**: Lymphoid aggregates (2% of tissue)

### Tumor Microenvironment Composition
- Tumor core: 85% tumor cells, 10% CAFs, 5% immune
- Invasive margin: 45% tumor, 30% CAFs, 25% immune (T cell rich)
- Immune infiltrate: 70% T cells, 20% macrophages, 10% B cells

## Spatial Cell Communication

### Top L-R Interactions (Spatially Proximal)
1. **Tumor -> T cell**: CD274 (PD-L1) -> PDCD1 (PD-1)
   - Hotspot: Invasive margin
   - Interpretation: Immune checkpoint evasion
2. **CAF -> Tumor**: TGFB1 -> TGFBR2
   - Hotspot: Stromal-tumor interface
   - Interpretation: TGF-B-driven EMT
3. **Macrophage -> Tumor**: TNF -> TNFRSF1A
   - Scattered across tumor
   - Interpretation: Inflammatory signaling

### Interaction Zones
- **Tumor-Immune Interface**: 245 spots (7% of tissue)
  - High expression: CXCL10, CXCL9 (chemokines)
  - T cell recruitment and activation
- **Stromal-Tumor Interface**: 387 spots (11% of tissue)
  - High expression: MMP2, MMP9 (matrix remodeling)
  - Invasion-promoting niche

## Spatial Gradients
- **Hypoxia gradient**: HIF1A, VEGFA increase toward tumor core
- **Proliferation gradient**: MKI67, TOP2A decrease from core to margin
- **Immune gradient**: CD8A, GZMB peak at invasive margin

## Biological Interpretation
Spatial analysis reveals distinct tumor microenvironment organization:

1. **Tumor core**: Highly proliferative, hypoxic, immune-excluded
2. **Invasive margin**: Active EMT, high immune infiltration, checkpoint expression
3. **Stromal barrier**: CAF-rich, matrix remodeling, immunosuppressive signals

The invasive margin shows hallmarks of immune-tumor interaction with
PD-L1/PD-1 checkpoint engagement, suggesting potential for checkpoint
blockade therapy. CAF-mediated TGF-B signaling may drive EMT and therapy
resistance at tumor-stroma interface.

## Clinical Relevance
- **Checkpoint inhibitor response**: High immune infiltration at margin suggests potential
- **Resistance mechanisms**: CAF barrier and TGF-B signaling
- **Biomarkers**: Spatial arrangement of immune cells more predictive than bulk tumor metrics
```
