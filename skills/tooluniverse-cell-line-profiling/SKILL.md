---
name: tooluniverse-cell-line-profiling
description: Help researchers select and characterize cancer cell lines for experiments. Given a cancer type, gene of interest, or cell line name, profiles molecular features (mutations, expression, CNV), gene dependencies (CRISPR screens), drug sensitivities (IC50/AUC), and genetic backgrounds using DepMap, Cellosaurus, PharmacoDB, COSMIC, CellMarker, CLUE, and SYNERGxDB. Generates a decision-support report for cell line selection. Use when researchers ask about which cell line to use, cell line characterization, DepMap dependencies, drug sensitivity profiles, or cancer model selection.
---

# Cancer Cell Line Profiling and Selection

Comprehensive profiling of cancer cell lines for experimental model selection. Transforms a query (cancer type, gene, or cell line name) into an actionable report covering identity verification, molecular features, gene dependencies, drug sensitivities, and druggable targets.

**KEY PRINCIPLES**:
1. **Decision-first** - Answer "which cell line should I use?" not "here is all the data"
2. **Multi-source validation** - Cross-reference DepMap, Cellosaurus, COSMIC, PharmacoDB
3. **Actionable output** - Ranked cell line recommendations with rationale
4. **Practical focus** - Include availability, growth characteristics, common pitfalls
5. **Gene-aware** - When a gene of interest is given, prioritize lines with relevant mutations/dependencies
6. **Source-referenced** - Cite database sources for every claim
7. **English-first queries** - Always use English terms in tool calls, even if the user writes in another language

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Apply for: cell line selection by cancer type/gene, cell line profiling, gene dependencies, drug sensitivity queries, cell line comparisons, mutation checks.

---

## Phase 0: Tool Parameter Reference (CRITICAL)

**BEFORE calling ANY tool**, verify parameters against this table.

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `DepMap_search_cell_lines` | `query` (required) | Search by name, e.g., "A549", "MCF" |
| `DepMap_get_cell_line` | `model_name` OR `model_id` | Name: "A549"; ID: "SIDM00001" |
| `DepMap_get_cell_lines` | `tissue`, `cancer_type`, `page_size` | Filter by tissue (e.g., "Lung") |
| `DepMap_get_gene_dependencies` | `gene_symbol` (required), `model_id` | Gene effect scores; negative = essential |
| `DepMap_search_genes` | `query` (required) | Validate gene symbol in DepMap first |
| `cellosaurus_search_cell_lines` | `q` (required), `size` | Solr syntax: `id:HeLa`, `ox:9606 AND char:cancer` |
| `cellosaurus_get_cell_line_info` | `accession` (required, CVCL_ format) | Full cell line record |
| `cellosaurus_query_converter` | `query` (required) | Natural language to Solr syntax |
| `COSMIC_search_mutations` | `terms` OR `query`, `max_results` | Search "BRAF V600E" or gene name |
| `COSMIC_get_mutations_by_gene` | `gene` OR `gene_name`, `max_results` | All mutations for a gene |
| `PharmacoDB_get_cell_line` | `operation="get_cell_line"`, `cell_name` | Cell line metadata + datasets |
| `PharmacoDB_get_experiments` | `operation="get_experiments"`, `compound_name`, `cell_line_name`, `dataset_name`, `per_page` | Drug response data (IC50, AAC, EC50) |
| `PharmacoDB_get_biomarker_assoc` | `operation="get_biomarker_associations"`, `compound_name`, `tissue_name`, `mdata_type`, `per_page` | Gene-drug sensitivity correlations |
| `PharmacoDB_search` | `operation="search"`, `query` | Find PharmacoDB IDs |
| `CellMarker_search_cancer_markers` | `operation="search_cancer_markers"`, `cancer_type`, `gene_symbol`, `cell_type` | Cancer cell markers |
| `CellMarker_search_by_gene` | `operation="search_by_gene"`, `gene_symbol` (required), `species` | Cell types expressing a gene |
| `HPA_get_comparative_expression_by_gene_and_cellline` | `gene_name` (required), `cell_line` (required) | Supported lines: ishikawa, hela, mcf7, a549, hepg2, jurkat, pc3, rh30, siha, u251 |
| `CLUE_get_cell_lines` | `operation="get_cell_lines"`, `cell_id` | L1000 CMap cell line info (requires CLUE_API_KEY) |
| `SYNERGxDB_search_combos` | `drug_name_1`, `drug_name_2`, `sample` (tissue or cell ID) | Drug combination synergy (ZIP, Bliss, Loewe) |
| `SYNERGxDB_list_cell_lines` | - | All cell lines in SYNERGxDB |
| `DGIdb_get_drug_gene_interactions` | `genes: list[str]` | Druggable gene interactions |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblId`, `size` | Drugs targeting a gene |
| `STRING_get_network` | `protein_ids: list[str]`, `species: int` (9606) | PPI network for gene context |
| `MyGene_query_genes` | `query` (NOT `q`) | Resolve gene symbol to Ensembl ID |
| `cBioPortal_get_mutations` | `study_id`, `gene_list` (STRING, not array) | Cell line mutations from CCLE |

---

## Workflow Overview

```
Input: Cancer type AND/OR Gene of interest AND/OR Cell line name(s)

Phase 1: Cell Line Identification
  - Search and verify cell line identity (Cellosaurus)
  - Get metadata: species, disease, STR profile, cross-references
  - If cancer type given without cell line: find candidate lines (DepMap)

Phase 2: Molecular Profiling
  - Mutation landscape (COSMIC, cBioPortal CCLE)
  - Gene expression (HPA, DepMap)
  - Cancer markers (CellMarker)

Phase 3: Gene Dependencies (CRISPR Screens)
  - Gene essentiality scores from DepMap
  - Identify selectively essential genes
  - Compare across cell lines if multiple candidates

Phase 4: Drug Sensitivity
  - IC50/AAC from PharmacoDB (GDSC, CCLE, CTRPv2, PRISM)
  - Biomarker associations for drug response
  - Drug combination synergy (SYNERGxDB)

Phase 5: Target Druggability & Recommendations
  - Druggable targets (DGIdb, OpenTargets)
  - Final ranked recommendation with rationale
```

---

## Phase 1: Cell Line Identification

**Goal**: Verify cell line identity and find candidates.

**If specific cell line given**: (1) `cellosaurus_search_cell_lines(q="id:<NAME>")` → get CVCL accession, species, disease, contamination flags. (2) `cellosaurus_get_cell_line_info(accession="CVCL_XXXX")` for STR profile. (3) `DepMap_get_cell_line(model_name="...")` for tissue, cancer_type, MSI, ploidy. (4) `PharmacoDB_get_cell_line(operation="get_cell_line", cell_name="...")` for datasets.

**If cancer type only**: (1) `DepMap_get_cell_lines(tissue="Lung", page_size=20)`. (2) Narrow by gene mutations/dependencies in Phases 2-3. (3) `CellMarker_search_cancer_markers(operation="search_cancer_markers", cancer_type="Lung")`.

**OUTPUT**: Table of candidate cell lines with: name, tissue, cancer type, key identifiers.

---

## Phase 2: Molecular Profiling

**Goal**: Characterize mutational and expression landscape.

**2A Mutations**: `COSMIC_get_mutations_by_gene(gene="EGFR")` + `cBioPortal_get_mutations(study_id="ccle_broad_2019", gene_list="EGFR,KRAS,TP53")`. Note: `gene_list` is a comma-separated STRING. CCLE study ID: `ccle_broad_2019`.

**2B Expression**: `HPA_get_comparative_expression_by_gene_and_cellline(gene_name="EGFR", cell_line="a549")`. Only 10 lines supported: hela, mcf7, a549, hepg2, jurkat, pc3, rh30, siha, u251, ishikawa.

**2C Cancer markers**: `CellMarker_search_by_gene(operation="search_by_gene", gene_symbol="EGFR", species="Human")`

**OUTPUT**: Mutation table (gene, AA change, type) + expression summary per cell line.

---

## Phase 3: Gene Dependencies (CRISPR Screens)

**Goal**: Determine which genes are essential in candidate cell lines.

**LIMITATION**: `DepMap_get_gene_dependencies` returns gene metadata (HGNC ID, Ensembl ID) but NOT per-cell-line CRISPR scores. Full Chronos scores require depmap.org download.

**Available tools**: (1) `DepMap_search_genes(query="EGFR")` — validate gene exists. (2) `DepMap_get_gene_dependencies(gene_symbol="EGFR")` — metadata only. (3) **Alternatives**: cBioPortal CCLE for mutation data, PubMed for published screens, or direct user to depmap.org/portal.

**Interpreting Chronos scores** (from DepMap portal): <-0.5 = essential; ~0 = not essential; ~-1.0 = strongly essential. Selective dependency (essential in some lineages only) indicates therapeutic window.

**OUTPUT**: Gene validation + mutation status per cell line.

**Offline DepMap analysis** (when API lacks CRISPR scores): Download `CRISPRGeneEffect.csv` + `Model.csv` from https://depmap.org/portal/download/all/. Load with pandas, find gene column (format: "KRAS (3845)"), merge with metadata, filter by lineage, sort by score. Most negative Chronos score = most dependent.

**If DepMap data is unavailable**: Use `cBioPortal_get_mutations(study_id="ccle_broad_2019", gene_list="KRAS")` for mutation data, and the Quick Reference table below for common recommendations.

---

## Phase 4: Drug Sensitivity

**Goal**: Profile drug response data.

**4A PharmacoDB**: `PharmacoDB_get_experiments(operation="get_experiments", compound_name="Erlotinib", cell_line_name="A549", per_page=20)` for dose-response (IC50, AAC, EC50). Omit `compound_name` to get all drugs for a cell line. Use `PharmacoDB_get_biomarker_assoc(compound_name="...", tissue_name="...", mdata_type="mutation")` for sensitivity biomarkers.

**4B SYNERGxDB**: `SYNERGxDB_search_combos(drug_name_1="gemcitabine", drug_name_2="erlotinib", sample="lung")`. Positive ZIP = synergy. Covers cytotoxic agents only (not targeted therapies/biologics).

**4C CLUE**: `CLUE_get_cell_lines(operation="get_cell_lines", cell_id="MCF7")` — requires CLUE_API_KEY.

**OUTPUT**: Drug sensitivity table (drug, IC50, AAC, dataset) + synergy data if available.

---

## Phase 5: Target Druggability and Recommendations

**5A Druggability**: `DGIdb_get_drug_gene_interactions(genes=["EGFR", "KRAS"])` + `MyGene_query_genes(query="EGFR")` → `OpenTargets_get_associated_drugs_by_target_ensemblID(ensemblId="...", size=10)` + `STRING_get_network(protein_ids=["EGFR"], species=9606)`.

**5B Final Recommendation**: Synthesize all phases. **Explain WHY one line is better for this specific use case.**

#### Decision Criteria with Concrete Thresholds

| Criterion | Weight | Score 3 (Best) | Score 2 (Acceptable) | Score 1 (Poor) |
|-----------|--------|----------------|---------------------|----------------|
| **Mutation match** | x3 | Exact mutation (e.g., KRAS G12D) | Same gene, different mutation | No mutation in gene of interest |
| **Co-mutation simplicity** | x2 | Few co-mutations (cleaner background) | Moderate co-mutations | Complex background (3+ driver mutations) |
| **Gene dependency** | x2 | DepMap score < -0.5 (essential) | Score -0.5 to -0.2 (moderately essential) | Score > -0.2 (not essential) |
| **Drug sensitivity data** | x1 | In GDSC + CCLE + PRISM (3+ datasets) | In 1-2 datasets | No drug response data |
| **Practical factors** | x1 | Adherent, well-characterized, widely used | Suspension or less common | Hard to culture, contamination-prone |

**Total score** = sum of (criterion score × weight). Max = 27. Rank cell lines by total score.

#### Use-Case-Specific Guidance

The best cell line depends on what you're doing with it:

| Use Case | Key Requirements | Extra Considerations |
|----------|-----------------|---------------------|
| **CRISPR knockout screen** | Adherent growth, good lentiviral transduction, pre-existing Cas9 clones (check Cellosaurus for "-Cas9" derivatives) | Doubling time matters for library coverage; <72h ideal |
| **Drug sensitivity testing** | In PharmacoDB/GDSC, known IC50 for reference compounds | Check SYNERGxDB for combo data |
| **Xenograft model** | Known tumorigenicity in mice, available PDX data | Check if line forms tumors in nude/NSG mice (Cellosaurus often notes this) |
| **Mechanism of action** | Clean genetic background, gene dependency confirmed | Fewer co-mutations = easier to attribute phenotypes |
| **Biomarker discovery** | Isogenic pairs available, well-characterized omics | Check if isogenic knockouts exist (Cellosaurus) |
| **Drug combination** | In SYNERGxDB with combo data, known single-agent responses | ZIP score available for synergy assessment |

#### Cellosaurus Derivative Lines

**Check for pre-made derivatives** — this can save months of lab work:
- `cellosaurus_search_cell_lines(q="ca:<PARENT_LINE>", size=20)` — finds all derivatives
- Look for: Cas9-expressing clones, drug-resistant derivatives, knockout lines, fluorescent reporter lines
- Example: PANC-1-Cas9-554 through PANC-1-Cas9-559 (CVCL_WL48-WL53) are pre-validated Cas9 clones

#### DepMap API Fallbacks

**If DepMap_get_gene_dependencies fails** (common for some genes):
- The Sanger Cell Model Passports API may not index all genes. Note this limitation.
- Recommend the user check DepMap portal (depmap.org) directly for CRISPR dependency data.
- Use `cBioPortal_get_mutations(study_id="ccle_broad_2019", gene_list="<GENE>")` as an alternative source for cell line mutation data.

**OUTPUT**: Ranked cell line table with total scores, per-criterion breakdown, and a text recommendation explaining the top pick and runner-up with biological reasoning.

---

## Common Use Patterns

| Pattern | Question Type | Key Tools (in order) |
|---------|--------------|---------------------|
| **1** | "Which cell line for [cancer] + [gene]?" | DepMap_get_cell_lines → DepMap_get_gene_dependencies → COSMIC_get_mutations_by_gene → cBioPortal_get_mutations (ccle_broad_2019) → PharmacoDB_get_experiments → rank by mutation + dependency + drug sensitivity |
| **2** | "Profile cell line X" | cellosaurus_search → DepMap_get_cell_line → PharmacoDB_get_cell_line → cBioPortal_get_mutations → HPA expression (if supported) → PharmacoDB_get_experiments |
| **3** | "Which lines are sensitive to [drug]?" | DepMap_get_cell_lines (tissue filter) → PharmacoDB_get_experiments (compound) → PharmacoDB_get_biomarker_assoc → rank by AAC (higher=sensitive) or IC50 (lower=sensitive) |
| **4** | "Compare A vs B" | Run Pattern 2 for both in parallel → side-by-side comparison table |
| **5** | "Drug combos for [cell line]?" | SYNERGxDB_search_combos → PharmacoDB_get_experiments (single-agent baseline) → report synergistic pairs with ZIP scores |

---

## Quick Reference: Common Cancer Cell Lines by Type

| Cancer Type | Key Cell Lines | Common Mutations |
|-------------|---------------|-----------------|
| NSCLC | A549 (KRAS G12S), H1975 (EGFR L858R/T790M), PC-9 (EGFR del19), HCC827 (EGFR del19/amp), H460 (KRAS Q61H), H1299 (NRAS Q61K, TP53-null) | KRAS, EGFR, TP53, STK11 |
| Breast | MCF7 (ER+/PR+), MDA-MB-231 (TNBC, KRAS G13D), T-47D (ER+), BT-474 (HER2+), SK-BR-3 (HER2+) | PIK3CA, TP53, BRCA1/2 |
| Colorectal | HCT116 (KRAS G13D, MSI-H), SW480 (KRAS G12V), HT-29 (BRAF V600E), Caco-2 (APC), LoVo (KRAS G13D, MSI-H) | APC, KRAS, TP53, BRAF |
| Melanoma | A375 (BRAF V600E), SK-MEL-28 (BRAF V600E), WM266-4 (BRAF V600D), MeWo (WT BRAF) | BRAF, NRAS, TP53 |
| Pancreatic | PANC-1 (KRAS G12D), MIA PaCa-2 (KRAS G12C), AsPC-1 (KRAS G12D), Capan-1 (BRCA2 mut) | KRAS, TP53, CDKN2A, SMAD4 |
| Prostate | PC-3 (AR-negative), LNCaP (AR+, PTEN-null), DU145 (AR-negative), VCaP (AR amp, TMPRSS2-ERG) | AR, PTEN, TP53, RB1 |
| Ovarian | SKOV3 (HER2+, TP53 mut), OVCAR3 (TP53 mut), A2780 (sensitive), A2780cis (cisplatin-resistant) | TP53, BRCA1/2 |
| Leukemia | K562 (CML, BCR-ABL), Jurkat (T-ALL), HL-60 (AML), THP-1 (AML, monocytic) | BCR-ABL, FLT3, NPM1 |
| Glioblastoma | U251 (TP53 mut), U87MG (PTEN-null), T98G (TP53/PTEN mut), LN229 (TP53 mut, PTEN WT) | TP53, PTEN, EGFR, IDH1 |
| Liver | HepG2 (hepatoblastoma, WT TP53), Hep3B (HBV+, TP53-null), Huh7 (HCC, TP53 Y220C) | TP53, CTNNB1, AXIN1 |

---

## Cross-Referencing Cell Line IDs

Use cell line NAME as common key across databases. IDs: DepMap=SIDM, Cellosaurus=CVCL, cBioPortal=sample (e.g. A549_LUNG), PharmacoDB/SYNERGxDB=name string. When names differ ("HCT 116" vs "HCT116"), check Cellosaurus synonyms first.

**Mutation-based filtering**: `cBioPortal_get_mutations(study_id="ccle_broad_2019", gene_list="KRAS")` → filter by `amino_acid_change` → extract cell line names → query other databases.

---

## Error Handling

| Issue | Resolution |
|-------|-----------|
| DepMap returns no results for cell line name | Try alternative names: check Cellosaurus synonyms first |
| cBioPortal CCLE study ID unknown | Use `ccle_broad_2019` as default CCLE study |
| PharmacoDB cell line name mismatch | Use `PharmacoDB_search(operation="search", query="<name>")` to find the canonical name |
| HPA cell line not supported | Only 10 lines supported (hela, mcf7, a549, hepg2, jurkat, pc3, rh30, siha, u251, ishikawa). Skip HPA for other lines |
| CLUE requires API key | Skip CLUE tools if CLUE_API_KEY not set; note in report |
| Gene symbol not found in DepMap | Use `DepMap_search_genes(query="<symbol>")` to check aliases |
| Cellosaurus accession pattern | Must be CVCL_XXXX format; search first if you only have a name |
| SYNERGxDB no results for drug combo | Drug may not be in database; SYNERGxDB covers cytotoxic agents, not most targeted therapies |

---

## Completeness Checklist

Before finalizing the report, verify:

- [ ] Cell line identity verified (Cellosaurus or DepMap)
- [ ] Species confirmed as human (unless otherwise specified)
- [ ] Key mutations documented (COSMIC or cBioPortal)
- [ ] Gene dependency assessed (DepMap CRISPR, if gene of interest provided)
- [ ] Drug sensitivity data included (PharmacoDB, at least one dataset)
- [ ] Druggability of key targets checked (DGIdb or OpenTargets)
- [ ] Practical recommendation provided (not just raw data)
- [ ] All claims cite their source database
- [ ] Known limitations noted (missing data, unsupported lines)
