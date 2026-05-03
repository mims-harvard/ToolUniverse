---
name: tooluniverse-aging-senescence
description: Research aging biology, cellular senescence, and longevity using ToolUniverse. Covers senescence markers and pathways, age-related disease genetics, telomere biology, senolytic drug discovery, epigenetic aging clocks, and longevity gene analysis. Integrates GWAS data, gene expression (GTEx age effects), pathway databases, drug repurposing, and literature. Use when asked about aging mechanisms, senescence, senolytics, longevity genes, age-related diseases, or epigenetic clocks.
---

# Aging & Cellular Senescence Research

## Aging Research Reasoning

Before querying any tool, ask the central question: is this a cause or consequence of aging?

Senescence markers (SA-β-gal, p16/CDKN2A, SASP factors like IL-6 and IL-8) indicate that senescent cells are present. But their presence does not prove that senescence is driving the phenotype. Correlation is easy to establish. Causation requires an intervention. If senolytic drugs (dasatinib+quercetin, fisetin, navitoclax) clear senescent cells and the age-related phenotype improves, that is causal evidence. If clearing senescent cells has no effect, something else is driving the pathology.

Apply this reasoning when interpreting any gene or pathway query: classify it first by hallmark, then ask whether the evidence for its role is correlative (expression data, GWAS association) or causal (functional assay, genetic knockout, senolytic intervention).

Evidence grade the findings: T1 is human genetic evidence (GWAS, centenarian studies). T2 is model organism lifespan data. T3 is cell culture senescence data. T4 is computational prediction. Do not conflate T3 cell culture data with T1 human evidence — they are very different levels of confidence.

A final principle: cellular senescence is one hallmark of aging, not aging itself. Distinguish senescence from organismal aging, from age-related disease, and from progeria (accelerated aging syndromes). These require different tools and different interpretations.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

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

## Workflow

```
Phase 0: Query Parsing — aging gene, senescence marker, age-related disease, or drug query
    |
Phase 1: Hallmarks Classification — map to the 12 hallmarks of aging framework
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

---

## Phase 1: Hallmarks Classification

Organize findings around the 12 hallmarks of aging (Lopez-Otin et al., Cell 2023). When a user asks about an aging gene, first classify which hallmark(s) it belongs to, then investigate that hallmark's pathway and disease connections. This prevents scattershot querying — each hallmark has specific pathways and tool strategies.

The hallmarks most amenable to ToolUniverse investigation are: genomic instability (DNA repair genes: ATM, ATR, BRCA1/2, TP53), telomere attrition (TERT, TERC, POT1), epigenetic alterations (DNMT1/3, TET1-3, SIRT1-7), loss of proteostasis (autophagy pathway hsa04140), deregulated nutrient sensing (mTOR pathway hsa04150, FOXO pathway hsa04068, AMPK, IGF1), mitochondrial dysfunction (PINK1, PARKIN, PGC1α), and cellular senescence (CDKN2A/p16, CDKN1A/p21, TP53, RB — KEGG pathway hsa04218).

For altered intercellular communication, focus on SASP factors: IL6, IL8, MCP1 (CCL2), MMP3, MMP9, PAI1, IGFBP7, VEGF. These are the secreted signals that make senescent cells pathological for surrounding tissue.

---

## Phase 2: Genetic Evidence

The best human evidence for aging genes comes from longevity GWAS and centenarian studies. Well-established loci include: APOE (19q13.32, strongest longevity signal), FOXO3 (5q33.3, replicated across multiple centenarian cohorts), TERT (10q24, telomere length GWAS), and CDKN2A/B (9p21.3, GWAS for CVD, cancer, and T2D — all age-related diseases sharing this locus).

Important caveat: many FOXO3 longevity studies (Willcox 2008, Flachsbart 2009) used targeted genotyping rather than GWAS arrays, so they do not appear in the GWAS Catalog. Always supplement GWAS Catalog queries with PubMed literature searches for centenarian studies.

```python
# Best for gene-centric analysis
gwas_get_snps_for_gene(gene_symbol="FOXO3")

# For trait queries — note "longevity" is not a standard EFO term; try "lifespan" or specific diseases
gwas_search_associations(query="telomere length")

# OpenTargets aggregated evidence
OpenTargets_get_associated_targets_by_disease_efoId(efoId="EFO_0004847", limit=20)

# Essential for centenarian studies not in GWAS Catalog
PubMed_search_articles(query="FOXO3 GWAS longevity centenarian meta-analysis")
```

---

## Phase 3: Pathway Analysis

The central senescence pathway is KEGG hsa04218. Start there when investigating any senescence-related gene. Supporting pathways: autophagy (hsa04140, implicated in senescence clearance and proteostasis), mTOR signaling (hsa04150, rapamycin target), FOXO signaling (hsa04068, stress resistance and autophagy), and p53 signaling (hsa04115, DNA damage response).

```python
KEGG_get_pathway_genes(pathway_id="hsa04218")   # Cellular senescence
kegg_search_pathway(keyword="autophagy")          # hsa04140
kegg_search_pathway(keyword="mTOR signaling")     # hsa04150
kegg_search_pathway(keyword="FOXO signaling")     # hsa04068
kegg_search_pathway(keyword="p53 signaling")      # hsa04115
```

For SASP network analysis, STRING and Reactome are the right tools:

```python
sasp_genes = ["IL6", "IL8", "MCP1", "MMP3", "MMP9", "PAI1", "IGFBP7", "VEGF", "CCL2"]
STRING_get_network(identifiers="\r".join(sasp_genes), species=9606)
ReactomeAnalysis_pathway_enrichment(identifiers=" ".join(sasp_genes))
```

### Interpreting Senescence Markers

Markers must be interpreted together, not individually. p16 (CDKN2A) upregulation is the closest to a gold standard — it marks irreversible cell cycle arrest — but it is also elevated in some cancers. p21 (CDKN1A) can reflect either transient quiescence or permanent senescence, so it is not specific. SA-β-gal is a lysosomal activity assay that can give false positives in high-confluence cultures. SASP factors (IL-6, IL-8) are also elevated in infection and autoimmunity. γH2AX foci are transient in normal DNA damage but persistent in senescence. Telomere shortening is only relevant for replicative senescence, not for oncogene-induced senescence.

Use a panel. A cell with p16↑ + SA-β-gal↑ + SASP↑ + γH2AX↑ is senescent. A cell with only one marker may not be.

---

## Phase 4: Senolytic and Geroprotector Drug Discovery

Senolytics selectively kill senescent cells. The most clinically advanced combination is dasatinib + quercetin (D+Q), currently in Phase II trials for idiopathic pulmonary fibrosis and diabetic kidney disease. Navitoclax (BCL-2/BCL-XL inhibitor) has strong preclinical data but causes thrombocytopenia, limiting clinical use. Fisetin has Phase II trials for frailty. UBX0101 failed Phase II for osteoarthritis.

Geroprotectors slow aging rather than removing senescent cells. Rapamycin (mTOR inhibitor) extends mouse lifespan and is FDA-approved for transplant. Metformin (AMPK activator) is being tested in the TAME trial. NAD+ precursors (NMN, NR) are in Phase II trials.

```python
DGIdb_get_drug_gene_interactions(genes=["BCL2", "BCL2L1", "TP53", "CDKN2A"])
search_clinical_trials(condition="senescence", query_term="senolytic")
search_clinical_trials(condition="aging", query_term="dasatinib quercetin")
ChEMBL_search_drugs(query="navitoclax")
```

When evaluating a drug candidate, always check clinical status: preclinical data in mice does not translate reliably to humans (telomere biology differs substantially between species). Prioritize T1 human evidence.

---

## Phase 5: Literature and Clinical Context

```python
PubMed_search_articles(query="cellular senescence senolytics clinical trial", max_results=20)
search_clinical_trials(condition="cellular senescence")
search_clinical_trials(query_term="rapamycin aging")
```

---

## Phase 6: Report Structure

1. **Hallmarks Classification** — which hallmarks are relevant and why
2. **Genetic Evidence** — GWAS loci, longevity genes, evidence grade (T1-T4)
3. **Pathway Analysis** — relevant pathways with key genes
4. **Senescence Markers** — expression evidence with interpretation caveats
5. **Drug Candidates** — senolytics and geroprotectors with evidence grade and clinical status
6. **Clinical Trials** — ongoing trials
7. **Mechanistic Model** — how the gene/pathway contributes to aging (cause or consequence?)
8. **Research Gaps** — what interventional data would resolve the causal question

---

## Age-Dependent Expression Analysis

GTEx provides tissue-level median expression but not directly age-stratified data. For age-dependent expression analysis, search PubMed for published GTEx age studies, or use GEO datasets with age metadata.

```python
# GTEx tissue expression (not age-stratified directly)
GTEx_get_median_gene_expression(gene_symbol="CDKN2A")

# Search for published age-expression analyses
PubMed_search_articles(query="GTEx age-dependent expression CDKN2A")
```

---

## Limitations

- Aging is multifactorial — no single gene or pathway explains it; this skill investigates specific aspects
- Mouse lifespan data does not reliably translate to humans (different telomere biology, metabolic rate)
- No single senescence marker is definitive; use a panel (p16 + SA-β-gal + SASP + γH2AX)
- No FDA-approved senolytic exists yet; most trials are Phase I/II
- Epigenetic clocks (Horvath/Hannum) require methylation array data processing not directly queryable via ToolUniverse
