---

name: tooluniverse-metabolomics-analysis
description: "Analyze metabolomics data end-to-end — metabolite identification, quantification (TIC normalization, batch correction), differential analysis, and pathway interpretation. Use for processing mass-spec metabolomics output, normalization choice, untargeted metabolomics workflows, and integrating with other omics layers."
---

# Metabolomics Analysis

Comprehensive analysis of metabolomics data from metabolite identification through quantification, statistical analysis, pathway interpretation, and integration with other omics layers.

## Domain Reasoning

Metabolomics quantification depends critically on normalization. Total ion current (TIC) normalization corrects for sample-loading variation and works well for global abundance changes; internal standard normalization is more accurate for targeted analysis where specific metabolite concentrations matter. Missing values in a peak table may reflect signal below the detection limit — not true absence — and should be imputed or handled explicitly rather than treated as zero. Failing to account for batch effects across instrument runs is a frequent source of spurious differential metabolites.

## LOOK UP DON'T GUESS

- Metabolite identities: use `Metabolite_search` and `Metabolite_get_info` to confirm names, CIDs, and HMDB IDs; never assume identity from m/z alone.
- Pathway memberships: query KEGG, MetaCyc, or Reactome tools; do not list pathways from memory.
- Disease associations: retrieve from CTD via `Metabolite_get_diseases`; do not infer clinical relevance without database evidence.
- CV thresholds and QC criteria: apply the values defined in this workflow (CV < 30%, blank ratio > 3x); do not override with guesses.

---

## When to Use This Skill

**Triggers**:
- User has metabolomics data (LC-MS, GC-MS, NMR)
- Questions about metabolite abundance or concentrations
- Differential metabolite analysis requests
- Metabolic pathway analysis
- Multi-omics integration with metabolomics
- Metabolic biomarker discovery
- Flux balance analysis or metabolic modeling
- Metabolite-enzyme correlation

**Example Questions**:
1. "Analyze this LC-MS metabolomics data for differential metabolites"
2. "Which metabolic pathways are dysregulated between conditions?"
3. "Identify metabolite biomarkers for disease classification"
4. "Correlate metabolite levels with enzyme expression"
5. "Perform pathway enrichment for differential metabolites"
6. "Integrate metabolomics with transcriptomics data"

---

## Core Capabilities

| Capability | Description |
|-----------|-------------|
| **Data Import** | LC-MS, GC-MS, NMR, targeted/untargeted platforms |
| **Metabolite Identification** | Match to HMDB, KEGG, PubChem, spectral libraries |
| **Quality Control** | Peak quality, blank subtraction, internal standard normalization |
| **Normalization** | Probabilistic quotient, total ion current, internal standards |
| **Statistical Analysis** | Univariate and multivariate (PCA, PLS-DA, OPLS-DA) |
| **Differential Analysis** | Identify significant metabolite changes |
| **Pathway Enrichment** | KEGG, Reactome, BioCyc metabolic pathway analysis |
| **Metabolite-Enzyme Integration** | Correlate with expression data |
| **Flux Analysis** | Metabolic flux balance analysis (FBA) |
| **Biomarker Discovery** | Multi-metabolite signatures |

---

## Workflow Overview

```
Input: Metabolomics Data (Peak Table or Spectra)
    |
    v
Phase 1: Data Import & Metabolite Identification
    |-- Load peak table or process raw spectra
    |-- Match features to HMDB, KEGG (accurate mass +/- 5 ppm)
    |-- Confidence scoring (Level 1-4)
    |
    v
Phase 2: Quality Control & Filtering
    |-- CV in QC samples (<30%)
    |-- Blank subtraction (sample/blank > 3)
    |-- Remove features with >50% missing
    |
    v
Phase 3: Normalization
    |-- Sample-wise: TIC, PQN, or internal standards
    |-- Transformation: log2, Pareto, or auto-scaling
    |-- Batch effect correction (if multi-batch)
    |
    v
Phase 4: Exploratory Analysis
    |-- PCA for sample clustering
    |-- PLS-DA for supervised separation
    |-- Outlier detection
    |
    v
Phase 5: Differential Analysis
    |-- t-test / ANOVA / Wilcoxon
    |-- Fold change + FDR correction
    |-- Volcano plots, heatmaps
    |
    v
Phase 6: Pathway Analysis
    |-- Metabolite set enrichment (MSEA)
    |-- KEGG/Reactome pathway mapping
    |-- Pathway topology (hub/bottleneck metabolites)
    |
    v
Phase 7: Multi-Omics Integration
    |-- Metabolite-enzyme Spearman correlation
    |-- Pathway-level concordance scoring
    |-- Metabolic flux inference
    |
    v
Phase 8: Generate Report
    |-- Summary statistics, differential metabolites
    |-- Pathway diagrams, biomarker panel
```

---

## Phase Summaries

### Phase 1: Data Import & Identification
Load peak tables (CSV/TSV) or process raw spectra (mzML). Match features to HMDB by accurate mass (+/- 5 ppm). Assign confidence levels: L1 (standard match), L2 (MS/MS), L3 (mass only), L4 (unknown).

**MS/MS spectral-library matching for L2 confidence (MassBank Europe)**: when a feature has an unknown identity and only a fragmentation spectrum, use `src/tooluniverse/data/massbank_tools.json`'s 5 tools to search MassBank Europe's open-access reference spectral library (~139,000 records) rather than guessing an identity from mass alone (mass-only matches are L3 at best; only a matching MS/MS fragmentation pattern justifies L2):

| Tool | Use for |
|------|---------|
| `MassBank_spectral_similarity_search` | **Core unknown-ID workflow.** Submit the query MS/MS peak list as comma-separated `mz;intensity` pairs (e.g. `"163.0601;100,145.0495;60,127.0390;30"`) and get back cosine-scored, ranked candidate accessions (score in [0,1], 1.0 = identical spectrum). Default threshold 0.5; raise toward 0.8+ for high-confidence-only matches, lower toward 0.3 to widen candidates. |
| `MassBank_get_record_by_accession` | Resolve a candidate accession (from any of the other 4 tools) into the full record: compound names, formula, exact mass, SMILES/InChI, instrument/acquisition parameters, and cross-references to CAS/CHEBI/KEGG/PubChem. |
| `MassBank_search_by_compound` | Look up reference spectra for an already-suspected identity by name (e.g. `"glucose"`) — useful to confirm a hypothesis or pull a reference spectrum for comparison, not for de novo identification. |
| `MassBank_search_by_formula` | Same idea, filtered by molecular formula (e.g. `"C6H12O6"`) when a formula has been inferred from accurate mass but the specific compound/isomer is still unknown. |
| `MassBank_search_records_advanced` | Narrow a large candidate set with AND-combined filters: `exact_mass`+`mass_tolerance`, a required fragment `peaks` value, a `neutral_loss`, `ion_mode`, `ms_type`, `instrument_type`, or a SMILES/SMARTS `substructure` match. Returns accessions only — resolve each with `MassBank_get_record_by_accession`. |

Verified live (MassBank Europe API, `tu test`/`tu run`, all 5 tools, 11/11 examples pass): a real search for `"glucose"` returns spectra for glucose and its biological derivatives (e.g. glucose-6-phosphate, `MSBNK-Antwerp_Univ-METOX_P100333_9EE2`, formula `C6H13O9P`, mass 260.0297, with `CAS`/`CHEBI`/`KEGG`/`PUBCHEM`/`INCHIKEY` cross-references) — search results are not limited to the exact queried compound, so check each candidate's `formula`/`mass` before treating a hit as a confirmed match. Note this is genuinely different from `tooluniverse-metabolomics`'s HMDB-based lookup: use MassBank when identity is unknown and you only have a spectrum; use `tooluniverse-metabolomics`/HMDB once a name or ID is already suspected and you want pathway/biological context instead.

**A second MS/MS spectral library (GNPS), plus natural-product biosynthetic classification**: `src/tooluniverse/data/gnps_tools.json`'s 4 tools cover GNPS (Global Natural Products Social Molecular Networking) — a sibling reference library to MassBank, not a replacement. Both are open, community-curated MS/MS libraries; GNPS's own community and contribution pipeline (molecular networking) skews its coverage toward natural products and microbial/environmental metabolites, while MassBank Europe's contributor base skews toward standards-run instrument labs — in practice this means a compound absent from one may well be present in the other, so for a genuinely unidentified feature it is worth checking both rather than treating a MassBank miss as conclusive.

| Tool | Use for |
|------|---------|
| `GNPS_get_spectrum` | Retrieve a GNPS reference spectrum by its **USI** (Universal Spectrum Identifier, format `mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB{id}` — a cross-repository spectrum-addressing standard, not GNPS-specific notation). Returns precursor m/z/charge, peak count, m/z range, and the top 20 peaks by intensity. |
| `GNPS_compare_spectra` | Compare two USIs side by side (precursor m/z + peak count for each) and get a `mirror_plot_url` for the interactive visual comparison — use to sanity-check a proposed match visually before committing to it. |
| `GNPS_get_library_record` | Resolve a `CCMSLIB` accession (from a molecular-networking hit or a `GNPS_get_spectrum` USI) into its full compound annotation: name, adduct, SMILES, InChI/InChIKey, instrument, ion mode, contributing PI, and library membership. This is the GNPS equivalent of `MassBank_get_record_by_accession`. |
| `GNPS_npclassifier_from_smiles` | **Not spectral matching** — a separate, later step. Takes a SMILES (e.g. already resolved via `GNPS_get_library_record`, MassBank, or HMDB) and returns its natural-product biosynthetic classification: `pathway` (e.g. Alkaloids, Shikimates and Phenylpropanoids), `superclass`, `class` (each an array — a structure can carry more than one class, e.g. morphine returns both `Isoquinoline alkaloids` and `Morphinan alkaloids`), and an `is_glycoside` flag. Works on *any* SMILES with no library lookup needed, so it's useful even for a structure proposed from first-principles fragment interpretation rather than a database hit. Use this once you have (or are proposing) a structure and want its natural-product context — not for identifying an unknown spectrum in the first place.

Verified live (GNPS API via gnps2, `tu test`/`tu run`, all 4 tools, 7/7 examples pass): `GNPS_get_library_record("CCMSLIB00005435737")` resolves to `"Lovastatin M+H; Mevinolin annotated in standard"` with full SMILES/InChI and an `annotations` array carrying the underlying GNPS record fields (`Scan`, `Library_Class`, `task_id`, etc.) alongside the flattened top-level fields; `GNPS_npclassifier_from_smiles` correctly classified quercetin as `Flavonols`/`Flavonoids`/`Shikimates and Phenylpropanoids` and morphine as the two-class `Isoquinoline alkaloids`+`Morphinan alkaloids` result above — confirming `class` can legitimately hold more than one entry.

### Phase 2: Quality Control
Assess CV in QC samples (reject >30%), compute blank ratios (keep >3x blank), filter features with >50% missing values. Check internal standard recovery (95-105% acceptable).

### Phase 3: Normalization
Three methods available: TIC (simple, assumes similar total abundance), PQN (robust to large changes, recommended), Internal Standard (most accurate with spiked standards). Follow with log2 transform or Pareto scaling.

### Phase 4: Exploratory Analysis
PCA reveals sample grouping and batch effects. PLS-DA provides supervised separation (report R2 and Q2 for model quality). Flag and investigate outliers.

### Phase 5: Differential Analysis
Welch's t-test (two groups) or ANOVA (multiple groups) with Benjamini-Hochberg FDR correction. Significance thresholds: adj. p < 0.05 and |log2FC| > 1.0.

### Phase 6: Pathway Analysis
Map differential metabolites to KEGG compound IDs. Perform MSEA for pathway enrichment. Consider topology: metabolites at pathway hubs (high degree/betweenness centrality) have greater impact.

### Phase 7: Multi-Omics Integration
Correlate metabolite levels with enzyme expression (Spearman). Expected: substrate-enzyme negative correlation (consumption), product-enzyme positive correlation (production). Score pathway dysregulation using combined metabolite + gene evidence.

### Phase 8: Report
See [report_template.md](report_template.md) for full example output.

---

## Integration with ToolUniverse

| Skill | Used For | Phase |
|-------|----------|-------|
| `tooluniverse-gene-enrichment` | Pathway enrichment | Phase 6 |
| `tooluniverse-rnaseq-deseq2` | Enzyme expression for integration | Phase 7 |
| `tooluniverse-proteomics-analysis` | Protein levels for integration | Phase 7 |
| `tooluniverse-multi-omics-integration` | Comprehensive integration | Phase 7 |

---

## Quantified Minimums

| Component | Requirement |
|-----------|-------------|
| Metabolites | At least 50 identified metabolites |
| Replicates | At least 3 per condition |
| QC | CV < 30% in QC samples, blank subtraction |
| Statistical test | t-test or Wilcoxon with FDR correction |
| Pathway analysis | MSEA with KEGG or Reactome |
| Report | QC, differential metabolites, pathways, visualizations |

---

## Limitations

- **Identification**: Many features remain unidentified (Level 4)
- **Coverage**: Cannot detect all metabolites (depends on method)
- **Quantification**: Relative abundance (not absolute without standards)
- **Isomers**: Difficult to distinguish structural isomers
- **Ion suppression**: Matrix effects can affect quantification
- **Dynamic range**: Limited compared to targeted methods

---

## References

**Methods**:
- MetaboAnalyst: https://doi.org/10.1093/nar/gkab382
- XCMS: https://doi.org/10.1021/ac051437y
- MSEA: https://doi.org/10.1186/1471-2105-11-395

**Databases**:
- HMDB: https://hmdb.ca
- KEGG Compound: https://www.genome.jp/kegg/compound/
- Reactome: https://reactome.org

---

## Reference Files

- [code_examples.md](code_examples.md) - Python code for all phases (data loading, QC, normalization, statistics, pathway analysis)
- [report_template.md](report_template.md) - Full example report (LC-MS disease vs control)
