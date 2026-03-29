---
name: tooluniverse-stem-cell-organoid
description: Research stem cells, iPSCs, organoids, and cell differentiation using ToolUniverse tools. Covers pluripotency marker identification, differentiation pathway analysis, organoid model characterization, cell type annotation, and disease modeling. Integrates CellxGene/HCA for single-cell atlas data, CellMarker for cell type markers, GEO for stem cell datasets, and pathway tools for differentiation signaling. Use when asked about stem cells, iPSCs, organoids, cell reprogramming, pluripotency, differentiation protocols, or 3D culture models.
---

# Stem Cell & Organoid Research

Pipeline for investigating stem cell biology, iPSC characterization, organoid models, and cell differentiation using ToolUniverse tools.

## Reasoning Strategy

Stem cell differentiation follows developmental biology — to make any target cell type from iPSCs, the protocol must mimic the embryonic signaling pathway that generates that cell type in vivo. For neural induction: inhibit BMP and TGF-beta (dual SMAD inhibition). For cardiomyocytes: activate WNT then inhibit WNT. For pancreatic beta cells: activate Activin/Nodal → FGF → Notch inhibition → BMP in sequence. The order and timing of growth factors matters critically — adding BMP4 during neural induction will redirect cells toward mesoderm. Mouse and human stem cells differ in their signaling requirements (LIF/STAT3 for mouse naive pluripotency; FGF/ERK for human primed pluripotency), so protocols are not interchangeable. Organoids recapitulate some but not all organ features — always assess maturation state (fetal vs. adult gene expression) before drawing disease-relevance conclusions.

**LOOK UP DON'T GUESS**: Do not assume which markers define a target cell type or which signaling pathway drives differentiation — query `CellMarker_search_by_cell_type` for markers and `kegg_search_pathway` for the relevant pathway. Do not assume organoid fidelity; look up published CellxGene or HCA atlas data for comparison.

**Key principles**:
1. **Marker-based identity** — stem cell identity is defined by marker expression profiles (OCT4, SOX2, NANOG for pluripotency)
2. **Differentiation is a trajectory** — not a binary state; analyze intermediate progenitor stages
3. **Organoid ≠ organ** — organoids recapitulate some but not all organ features; always note limitations
4. **Species matters** — mouse and human stem cells differ in signaling requirements
5. **Evidence grading** — T1: validated in clinical iPSC study, T2: functional assay (teratoma, engraftment), T3: marker expression only, T4: computational prediction

---

## Core Tools

| Tool | Use For |
|------|---------|
| `CellxGene_search_datasets` | Find single-cell atlas data. **Requires `cellxgene-census` package (`pip install cellxgene-census`). May not be installed by default.** |
| `CellMarker_search_by_cell_type` | Cell type marker genes. **Requires `operation="search_by_cell_type"`, `cell_name=` (NOT `cell_type=`)** |
| `CellMarker_search_by_gene` | Which cell types express a gene. **Requires `operation="search_by_gene"`, `gene_symbol=`** |
| `HCA_search_projects` | Human Cell Atlas organoid/development projects |
| `GEO_search_rnaseq_datasets` | Find stem cell RNA-seq datasets |
| `kegg_search_pathway` | Differentiation signaling pathways (WNT, Notch, Hedgehog) |
| `ReactomeAnalysis_pathway_enrichment` | Pathway analysis of stem cell gene sets |
| `STRING_get_network` | Pluripotency/differentiation gene networks |
| `OpenTargets_get_associated_targets_by_disease_efoId` | Disease genes for organoid disease modeling |
| `PubMed_search_articles` | Stem cell and organoid literature |
| `search_clinical_trials` | iPSC-based clinical trials |

---

## Workflow

```
Phase 0: Define the Question
  Pluripotency? Differentiation? Disease modeling? Drug screening?
    |
Phase 1: Cell Identity & Markers
  CellMarker → pluripotency/lineage markers → verify identity
    |
Phase 2: Differentiation Pathways
  KEGG/Reactome → WNT, Notch, BMP, FGF signaling
    |
Phase 3: Atlas & Dataset Discovery
  CellxGene/HCA → reference datasets for target cell type
    |
Phase 4: Disease Modeling (if applicable)
  OpenTargets → disease genes → organoid recapitulation assessment
    |
Phase 5: Report
  Evidence-graded findings with clinical translation potential
```

### Phase 1: Cell Identity & Markers

**Pluripotency markers** (must be co-expressed): OCT4 (POU5F1), SOX2, NANOG (essential); SSEA-4, TRA-1-60 (human surface markers). KLF4 and MYC are Yamanaka factors but also expressed in somatic cells — do not rely on them alone. Use `CellMarker_search_by_cell_type` to retrieve the full validated marker set for any target cell type.

**Lineage markers**: Ectoderm → PAX6/SOX1 (early), MAP2/TUBB3 (neurons); Mesoderm → TBXT/MIXL1 (early), CD34 (blood); Endoderm → SOX17/FOXA2 (early), PDX1/NKX6.1 (pancreas). Retrieve current marker lists from CellMarker rather than relying on memory.

### Phase 2: Differentiation Pathways

Key signaling pathways for directed differentiation:

| Pathway | KEGG ID | Role in Stem Cells | Common Modulators |
|---------|---------|-------------------|-------------------|
| WNT signaling | hsa04310 | Pluripotency maintenance (canonical) vs differentiation (non-canonical) | CHIR99021 (activator), IWP-2 (inhibitor) |
| Notch signaling | hsa04330 | Lateral inhibition, fate decisions | DAPT (gamma-secretase inhibitor) |
| BMP/TGF-beta | hsa04350 | Mesoderm/trophectoderm induction | BMP4 (activator), Noggin (inhibitor) |
| FGF signaling | hsa04010 | Self-renewal, neural induction | bFGF (activator), SU5402 (inhibitor) |
| Hedgehog | hsa04340 | Patterning, organoid maturation | SAG (activator), cyclopamine (inhibitor) |
| Hippo/YAP | hsa04390 | Mechanotransduction, organoid size | Verteporfin (YAP inhibitor) |

### Phase 3: Atlas & Dataset Discovery

```python
# Find stem cell single-cell datasets
CellxGene_search_datasets(query="iPSC organoid", organism="Homo sapiens")
HCA_search_projects(query="organoid")
GEO_search_rnaseq_datasets(query="iPSC differentiation neural", organism="Homo sapiens")
```

### Phase 4: Organoid Model Assessment

**Organoid fidelity scoring** — how well does the organoid recapitulate the organ?

| Feature | High Fidelity (3) | Moderate (2) | Low (1) |
|---------|------------------|-------------|---------|
| Cell type diversity | All major cell types present | Most cell types, missing rare ones | Only 1-2 cell types |
| Architecture | Self-organized, correct spatial arrangement | Partial organization | Disorganized aggregate |
| Function | Measurable organ function (secretion, contraction, electrophysiology) | Some functional markers | Marker expression only |
| Maturation | Adult-like gene expression profile | Fetal-like | ESC-like (failed differentiation) |
| Disease relevance | Recapitulates patient phenotype | Some disease features | No disease phenotype |

---

## Evidence Grading

| Grade | Criteria | Example |
|-------|---------|---------|
| **T1** | Clinical iPSC study or approved therapy | iPSC-derived RPE for macular degeneration (Mandai 2017) |
| **T2** | Functional validation (teratoma, engraftment, drug response) | Organoid drug screening with patient-specific response |
| **T3** | Marker expression + morphology | iPSC colony expressing OCT4/SOX2/NANOG |
| **T4** | Computational prediction or single-marker evidence | Predicted pluripotent by gene expression classifier |

### Synthesis Questions

1. **Is the cell identity verified?** (co-expression of 3+ pluripotency markers, or lineage-appropriate markers)
2. **Is the differentiation protocol reproducible?** (published, peer-reviewed, with quantified efficiency)
3. **Does the organoid model the disease?** (patient-derived iPSC shows disease phenotype in organoid)
4. **What are the translational barriers?** (scalability, maturation, immune compatibility, tumorigenicity)
5. **What's the best reference dataset?** (CellxGene atlas for comparison)

---

## Limitations

- **No organoid protocol database** — protocols are scattered across publications; use PubMed search
- **Maturation gap** — most organoids resemble fetal, not adult tissue; always note maturation state
- **Batch variability** — iPSC-derived cells vary between passages and donor lines
- **No direct culture tools** — this skill analyzes published data and designs experiments; it does not control bioreactors
- **Species differences** — mouse ESCs require LIF; human ESCs require bFGF. Don't mix protocols
