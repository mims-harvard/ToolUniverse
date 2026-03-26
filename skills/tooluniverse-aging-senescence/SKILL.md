---
name: tooluniverse-aging-senescence
description: Research aging biology, cellular senescence, and longevity using ToolUniverse. Covers senescence markers and pathways, age-related disease genetics, telomere biology, senolytic drug discovery, epigenetic aging clocks, and longevity gene analysis. Integrates GWAS data, gene expression (GTEx age effects), pathway databases, drug repurposing, and literature. Use when asked about aging mechanisms, senescence, senolytics, longevity genes, age-related diseases, or epigenetic clocks.
---

# Aging & Cellular Senescence Research

Pipeline for investigating aging biology through genetics, gene expression, pathways, drug discovery, and literature integration. Covers the molecular hallmarks of aging and translates them into research actionables.

**Key principles**:
1. **Hallmarks framework** — organize findings around the 12 hallmarks of aging (Lopez-Otin 2023)
2. **Senescence is not just aging** — cellular senescence is one mechanism; distinguish from organismal aging, progeria, and age-related disease
3. **SASP matters** — the senescence-associated secretory phenotype drives much of senescence pathology; always check SASP factors
4. **Evidence grading** — T1: human genetic evidence (GWAS, centenarian studies), T2: model organism lifespan data, T3: cell culture senescence data, T4: computational prediction
5. **Translational focus** — connect biology to senolytic drugs, geroprotectors, and clinical trials

---

## When to Use

- "What genes are associated with longevity?"
- "Find senolytic drug candidates for [disease]"
- "What are the markers of cellular senescence?"
- "How does [gene] relate to aging?"
- "GWAS hits for age-related diseases"
- "Pathways involved in cellular senescence"
- "What drugs target senescent cells?"

**Not this skill**: For rare disease genetics, use `tooluniverse-rare-disease-diagnosis`. For general disease research, use `tooluniverse-disease-research`.

---

## Core Tools

| Tool | Use For |
|------|---------|
| `gwas_search_associations` | Age-related disease GWAS hits |
| `OpenTargets_get_associated_targets_by_disease_efoId` | Genetic targets for age-related diseases |
| `GTEx_get_median_gene_expression` | Age-dependent gene expression |
| `STRING_get_network` | Senescence protein interaction networks |
| `ReactomeAnalysis_pathway_enrichment` | Pathway analysis of aging gene sets |
| `kegg_search_pathway` | Cellular senescence pathway (hsa04218) |
| `KEGG_get_pathway_genes` | Genes in senescence/autophagy/apoptosis pathways |
| `DGIdb_get_drug_gene_interactions` | Drugs targeting senescence genes |
| `ChEMBL_search_drugs` | Senolytic/geroprotector compound details |
| `search_clinical_trials` | Clinical trials for senolytics |
| `PubMed_search_articles` | Aging/senescence literature |
| `DisGeNET_search_gene` | Gene-disease associations for aging genes. **Param: `gene=` (NOT `query=`). Requires `DISGENET_API_KEY`.** |
| `UniProt_get_function_by_accession` | Protein function for aging-related genes |
| `HPO_search_terms` | Aging/progeria phenotype terms |

---

## Workflow

```
Phase 0: Query Parsing — aging gene, senescence marker, age-related disease, or drug query
    |
Phase 1: Hallmarks Classification — map to 12 hallmarks of aging framework
    |
Phase 2: Genetic Evidence — GWAS, longevity loci, model organism data
    |
Phase 3: Pathway Analysis — senescence, autophagy, telomere, epigenetic pathways
    |
Phase 4: Senolytic/Geroprotector Drug Discovery — existing drugs, clinical trials
    |
Phase 5: Literature & Clinical Context — published evidence, ongoing trials
    |
Phase 6: Interpretation & Report — evidence-graded findings with translational potential
```

### Phase 1: Hallmarks of Aging Classification

The 12 hallmarks of aging (Lopez-Otin et al., Cell 2023) provide the organizing framework:

| Hallmark | Key Genes/Pathways | ToolUniverse Query Strategy |
|----------|-------------------|---------------------------|
| **Genomic instability** | ATM, ATR, BRCA1/2, TP53 | `STRING_get_network`, DNA repair pathways |
| **Telomere attrition** | TERT, TERC, POT1, TRF1/2 | `kegg_search_pathway(keyword="telomere")` |
| **Epigenetic alterations** | DNMT1/3, TET1-3, HDAC, SIRT1-7 | ENCODE, epigenomics tools |
| **Loss of proteostasis** | HSP70/90, UPS, autophagy | `kegg_search_pathway(keyword="autophagy")` → hsa04140 |
| **Disabled macroautophagy** | ATG5, BECN1, LC3, mTOR | KEGG autophagy pathway (hsa04140) |
| **Deregulated nutrient sensing** | mTOR, AMPK, IGF1, FOXO, SIRT1 | `KEGG_get_pathway_genes(pathway_id="hsa04150")` (mTOR) |
| **Mitochondrial dysfunction** | PINK1, PARKIN, PGC1α, TFAM | `kegg_search_pathway(keyword="mitophagy")` |
| **Cellular senescence** | p16/CDKN2A, p21/CDKN1A, p53, RB | **KEGG hsa04218** (cellular senescence) |
| **Stem cell exhaustion** | WNT, NOTCH, BMI1, NANOG | Stem cell signaling pathways |
| **Altered intercellular communication** | NF-κB, SASP factors (IL-6, IL-8, MCP-1) | `STRING_get_network` with SASP genes |
| **Chronic inflammation** | TNF, IL-1β, IL-6, NLRP3 | Inflammaging gene sets |
| **Dysbiosis** | Gut microbiome changes | `tooluniverse-metagenomics-analysis` skill |

**How to use this**: When a user asks about an aging gene, first classify which hallmark(s) it belongs to, then investigate that hallmark's pathway and disease connections.

### Phase 2: Genetic Evidence

**Longevity GWAS loci** (well-established):

| Locus | Gene | Effect | Evidence |
|-------|------|--------|---------|
| 9p21.3 | CDKN2A/B (p16/p15) | Senescence regulator | T1: GWAS for CVD, cancer, T2D — all age-related |
| 19q13.32 | APOE (ε2/ε3/ε4) | Lipid metabolism, neurodegeneration | T1: strongest longevity GWAS signal |
| 5q33.3 | FOXO3 | Stress resistance, autophagy | T1: replicated in multiple centenarian studies |
| 6q21 | FOXO3 (enhancer) | Same gene, different signal | T1: fine-mapped to regulatory variant |
| 10q24 | TERT | Telomere maintenance | T1: GWAS for telomere length |

```python
# Strategy 1 (BEST for gene-centric): Get all GWAS SNPs for the gene
gwas_get_snps_for_gene(gene_symbol="FOXO3")  # Returns all associated SNPs at the locus

# Strategy 2: Search by trait (returns studies, not gene-specific)
gwas_search_associations(query="telomere length")  # Works for broad trait queries
# WARNING: gwas_search_associations(query="longevity") may return 0 results —
# "longevity" is not a standard EFO trait term. Try "lifespan" or specific diseases.

# Strategy 3: OpenTargets aggregated genetic evidence
OpenTargets_get_associated_targets_by_disease_efoId(efoId="EFO_0004847", limit=20)  # aging

# Strategy 4: Literature (essential for centenarian studies not in GWAS Catalog)
PubMed_search_articles(query="FOXO3 GWAS longevity centenarian meta-analysis")
# Many FOXO3 longevity studies (Willcox 2008, Flachsbart 2009) are in PubMed
# but NOT in GWAS Catalog because they used targeted genotyping, not GWAS arrays.
```

### Phase 3: Pathway Analysis

**Key senescence pathways**:

```python
# The master senescence pathway
KEGG_get_pathway_genes(pathway_id="hsa04218")  # Cellular senescence
# Returns: CDKN2A, CDKN1A, TP53, RB1, CDK4/6, E2F, TERT, ATM/ATR, etc.

# Supporting pathways
kegg_search_pathway(keyword="autophagy")       # hsa04140 — Autophagy
kegg_search_pathway(keyword="mTOR signaling")  # hsa04150 — mTOR
kegg_search_pathway(keyword="FOXO signaling")  # hsa04068 — FOXO
kegg_search_pathway(keyword="p53 signaling")   # hsa04115 — p53

# SASP network (senescence-associated secretory phenotype)
sasp_genes = ["IL6", "IL8", "MCP1", "MMP3", "MMP9", "PAI1", "IGFBP7", "VEGF", "CCL2"]
STRING_get_network(identifiers="\r".join(sasp_genes), species=9606)
ReactomeAnalysis_pathway_enrichment(identifiers=" ".join(sasp_genes))
```

**Senescence marker interpretation**:

| Marker | What It Means | Caveats |
|--------|--------------|---------|
| p16 (CDKN2A) ↑ | Irreversible cell cycle arrest; gold standard senescence marker | Also elevated in some cancers (paradox) |
| p21 (CDKN1A) ↑ | Cell cycle arrest; can be transient (quiescence) or permanent (senescence) | Not specific to senescence — also DNA damage response |
| SA-β-gal ↑ | Lysosomal activity increase in senescent cells | Assay artifact in high-confluence cultures |
| SASP (IL-6, IL-8) ↑ | Paracrine signaling from senescent cells | Also elevated in infection, autoimmunity |
| γH2AX foci ↑ | DNA double-strand breaks, telomere dysfunction | Transient in DNA damage; persistent = senescence |
| Lamin B1 ↓ | Nuclear envelope disruption | Also disrupted in laminopathies |
| Telomere shortening | Replicative senescence | Only relevant for replicative, not oncogene-induced senescence |

### Phase 4: Senolytic & Geroprotector Drug Discovery

**Known senolytics** (drugs that selectively kill senescent cells):

| Drug | Target | Evidence | Clinical Status |
|------|--------|---------|----------------|
| Dasatinib + Quercetin (D+Q) | Src/BCR-ABL + PI3K/AKT | T1: Phase II trials (IPF, diabetic kidney disease) | Most advanced senolytic combo |
| Navitoclax (ABT-263) | BCL-2/BCL-XL | T2: preclinical in mouse models | Thrombocytopenia limits clinical use |
| Fisetin | PI3K/AKT/mTOR | T1: Phase II (frailty, COVID) | Natural flavonoid; bioavailability concerns |
| FOXO4-DRI peptide | p53-FOXO4 interaction | T2: mouse (restored fitness in aged mice) | Preclinical |
| UBX0101 | MDM2/p53 | T1: Phase II for osteoarthritis (FAILED) | Discontinued |
| Cardiac glycosides | Na+/K+-ATPase | T3: in vitro senolytic activity | Narrow therapeutic window |

```python
# Find senolytic drug interactions
DGIdb_get_drug_gene_interactions(genes=["BCL2", "BCL2L1", "TP53", "CDKN2A"])
search_clinical_trials(condition="senescence", query_term="senolytic")
search_clinical_trials(condition="aging", query_term="dasatinib quercetin")
ChEMBL_search_drugs(query="navitoclax")
```

**Geroprotectors** (drugs that slow aging):

| Drug | Mechanism | Evidence |
|------|----------|---------|
| Rapamycin/everolimus | mTOR inhibition | T1: FDA-approved (transplant); T2: lifespan extension in mice |
| Metformin | AMPK activation | T1: TAME trial (ongoing); T2: observational data |
| NAD+ precursors (NMN, NR) | NAD+ restoration, sirtuin activation | T1: Phase II trials; T3: mouse lifespan data |
| Spermidine | Autophagy induction | T2: mouse lifespan; T1: observational (dietary) |

### Phase 5: Literature & Clinical Context

```python
PubMed_search_articles(query="cellular senescence senolytics clinical trial", max_results=20)
search_clinical_trials(condition="cellular senescence")
search_clinical_trials(query_term="rapamycin aging")
```

### Phase 6: Report Structure

1. **Hallmarks Classification** — which of the 12 hallmarks are relevant
2. **Genetic Evidence** — GWAS loci, longevity genes, model organism data
3. **Pathway Analysis** — senescence, autophagy, mTOR, FOXO pathways with gene lists
4. **Senescence Markers** — expression evidence with interpretation caveats
5. **Drug Candidates** — senolytics and geroprotectors with evidence grades and clinical status
6. **Clinical Trials** — ongoing trials for senolytic/geroprotective interventions
7. **Mechanistic Model** — how the investigated gene/pathway contributes to aging
8. **Research Gaps** — what's missing and what experiments would fill the gaps

---

## Computational Procedure: Age-Dependent Expression Analysis

When investigating whether a gene's expression changes with age:

```python
# Use GTEx age data to assess age-dependent expression
# GTEx provides expression by age group (20-29, 30-39, ..., 60-69, 70-79)
# This requires GTEx bulk downloads for full age analysis
import pandas as pd
from scipy.stats import spearmanr

# Example: check if CDKN2A expression increases with age across tissues
# GTEx median expression API gives tissue-level data but not age-stratified
# For age analysis, search PubMed for published GTEx age studies:
# PubMed_search_articles(query="GTEx age-dependent expression CDKN2A")

# Alternative: use GEO datasets with age metadata
# GEO_search_rnaseq_datasets(query="aging human blood transcriptome")
# Then download and analyze the count matrix with age as a covariate
```

---

## Limitations

- **Aging is multifactorial** — no single gene or pathway explains aging; this skill helps investigate specific aspects
- **Model organism translation** — mouse lifespan studies don't always translate to humans (different telomere biology, metabolic rate)
- **Senescence markers are imperfect** — no single marker defines senescence; use a panel (p16 + SA-β-gal + SASP + γH2AX)
- **Clinical senolytics are early-stage** — most trials are Phase I/II; no FDA-approved senolytic yet
- **Epigenetic clocks** — not directly queryable via ToolUniverse tools (Horvath/Hannum clocks require methylation array data processing)
