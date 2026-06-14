# Spatial Omics Analysis - Reference Data

Reference tables for cell type markers, immune checkpoints, ligand-receptor pairs, and validation methods.

---

## Cell Type Marker Genes

Use these to assign cell types when user does not provide annotations.

| Cell Type | Key Markers | Extended Markers |
|-----------|-------------|-----------------|
| Epithelial | CDH1, EPCAM, KRT18, KRT19 | KRT8, KRT14, MUC1 |
| Mesenchymal/Fibroblast | VIM, COL1A1, COL3A1, FAP, ACTA2 | PDGFRA, PDGFRB |
| Endothelial | PECAM1, VWF, CDH5 | KDR, FLT1 |
| T cell (CD8+) | CD8A, CD8B | GZMA, GZMB, PRF1, IFNG |
| T cell (CD4+) | CD4 | IL2, IL4, IL17A, FOXP3 (Treg) |
| Regulatory T cell | FOXP3, IL2RA | CTLA4, TIGIT |
| B cell | CD19, MS4A1, CD79A | IGHG1, IGHM |
| Plasma cell | SDC1 (CD138), XBP1 | IGHG1, MZB1 |
| M1 Macrophage | CD68, NOS2, TNF | IL1B, CXCL10 |
| M2 Macrophage | CD68, CD163, MRC1 | ARG1, IL10 |
| Dendritic cell | ITGAX (CD11c), HLA-DRA | CD80, CD86 |
| NK cell | NCAM1 (CD56), NKG7 | GNLY, KLRD1 |
| Neutrophil | FCGR3B, CXCR2 | S100A8, S100A9 |
| Mast cell | KIT, TPSAB1 | CPA3, HDC |
| Neuronal | SNAP25, SYP, MAP2, NEFL | RBFOX3, TUBB3 |
| Hepatocyte | ALB, HNF4A, CYP3A4 | APOB, TTR |

### Cell Type Assignment Rules
- Check each gene against known cell type markers
- Use HPA tissue/cell type expression data for validation
- Confidence: high (3+ markers match), medium (2 markers), low (1 marker)

---

## Immune Checkpoint Reference

| Checkpoint | Gene | Ligand | Therapeutic Antibody |
|------------|------|--------|---------------------|
| PD-1/PD-L1 | PDCD1/CD274 | CD274, PDCD1LG2 | Pembrolizumab, Nivolumab, Atezolizumab |
| CTLA-4 | CTLA4 | CD80, CD86 | Ipilimumab |
| TIM-3 | HAVCR2 | LGALS9 | Sabatolimab |
| LAG-3 | LAG3 | HLA class II | Relatlimab |
| TIGIT | TIGIT | PVR, PVRL2 | Tiragolumab |
| VISTA | VSIR | PSGL1 | - |

---

## Ligand-Receptor Pairs

Known ligand-receptor pairs to check in SVG lists:

| Category | Ligand | Receptor |
|----------|--------|----------|
| Growth factors | EGF | EGFR |
| Growth factors | HGF | MET |
| Growth factors | VEGF | KDR |
| Growth factors | FGF | FGFR |
| Growth factors | PDGF | PDGFRA/B |
| Cytokines | TNF | TNFR |
| Cytokines | IL6 | IL6R |
| Cytokines | IFNG | IFNGR |
| Cytokines | TGFB1 | TGFBR1/2 |
| Chemokines | CXCL12 | CXCR4 |
| Chemokines | CCL2 | CCR2 |
| Chemokines | CXCL10 | CXCR3 |
| Immune checkpoints | CD274 (PD-L1) | PDCD1 (PD-1) |
| Immune checkpoints | CD80/CD86 | CTLA4 |
| Immune checkpoints | LGALS9 | HAVCR2 (TIM-3) |
| Notch signaling | DLL1/3/4 | NOTCH1/2/3/4 |
| Notch signaling | JAG1/2 | NOTCH1/2 |
| Wnt signaling | WNT ligands | FZD receptors |
| Adhesion | CDH1 | CDH1 (homotypic) |
| Adhesion | ITGA/B integrins | ECM |
| Hedgehog | SHH | PTCH1 |

---

## Enrichment Interpretation Guide

| Pathway Category | Spatial Interpretation |
|------------------|----------------------|
| Signaling (RTK, Wnt, Notch, Hedgehog) | Cell-cell communication |
| Metabolic pathways | Tissue metabolic zonation |
| Immune pathways | Immune infiltration/exclusion |
| ECM/adhesion | Tissue structure and remodeling |
| Cell cycle/proliferation | Growth zones |
| Apoptosis/stress | Damage zones |

---

## Validation Recommendations Template

| Priority | Target | Method | Rationale | Feasibility |
|----------|--------|--------|-----------|-------------|
| **High** | Key SVG | smFISH / RNAscope | Validate spatial pattern at single-molecule level | Medium |
| **High** | Druggable target | IHC on serial sections | Confirm protein expression in spatial domain | High |
| **High** | Ligand-receptor pair | Proximity ligation assay (PLA) | Confirm physical interaction at tissue level | Medium |
| **Medium** | Domain markers | Multiplexed IF (CODEX/IBEX) | Validate multiple markers simultaneously | Low-Medium |
| **Medium** | Pathway | Spatial metabolomics (MALDI/DESI) | Confirm metabolic pathway activity | Low |
| **Low** | Novel interaction | Co-culture + conditioned media | Functional validation of predicted interaction | Medium |

---

## Literature Search Strategy

1. **Tissue + spatial**: `"{tissue} spatial transcriptomics"`
2. **Disease + spatial**: `"{disease} spatial omics"`
3. **Gene + tissue**: `"{top_gene} {tissue} expression"` for key SVGs
4. **Zonation** (if relevant): `"{tissue} zonation gene expression"`
5. **Technology**: `"{technology} {tissue}"`
