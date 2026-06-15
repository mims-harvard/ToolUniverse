# Compute-Tool Roadmap

**Date:** 2026-06-15 · **Author:** coverage audit
**Question it answers:** *From the perspective of what tools and skills cover, what is ToolUniverse still missing?*

---

## Executive summary

> **Correction (2026-06-15).** An earlier draft of this file claimed "only 5 of 2,539 tools are local-compute." **That was wrong** — it counted only tools with `requires_local_input: true` (file inputs) and missed every *inline-data* compute tool. A proper `find_tools`/registry audit shows **58 local-compute tools across 17 classes**. The compute layer is real and decently populated; the genuine gaps are a focused list, not a structural hole. Two roadmap items below (`Survival_analysis`, `PopGen`, `PK_nca`, `Curve_fit`, `Meta_analysis`) were found to **already exist** and must not be rebuilt. Always run `tu.find_tools(query="<capability>")` before building — see the audit table.

ToolUniverse's coverage:

| Layer | Inventory | Verdict |
|---|---|---|
| **Knowledge / database-access tools** (query an API by ID/region/name) | 568 source APIs, ~2,480 tools | ✅ Comprehensive |
| **Local-compute tools** (deterministic analysis on user-provided data, inline or file) | **58 tools across 17 classes** — `SurvivalTool`, `PopGenTool`, `NCATool`, `DoseResponseTool`, `DrugSynergyTool`, `EpidemiologyTool`, `DNATool`, `ScientificCalculatorTool` (incl. `EnzymeKinetics_calculate`), `ClinicalCalculatorTool`, `MetaAnalysisTool`, `DESeq2Tool`, `ROCAnalysisTool`, `VCFStatsTool`, … | ✅ More mature than first claimed; gaps are specific |
| **Analysis capability still only in skill scripts** (real compute, not a callable tool) | a subset of the 86 `skills/*/scripts/*.py` | ⚠️ The genuine opportunity — but only for capabilities with NO existing tool |

The genuine remaining work is **narrower than a "promote all 86 scripts" sweep**: most common analyses (survival, dose-response, enzyme kinetics, PK NCA, popgen, meta-analysis, DESeq2, sequence utilities, drug synergy, clinical calculators) already have tools. Build only where `find_tools` confirms a true blank — and promote the *method*, not the script (next section).

This document is the prioritized backlog. It is **not** a commitment to build all of it; it is the map to choose from.

### Search before you build (MANDATORY — this rule was learned the hard way)

`Survival_analysis` was started, then found to duplicate the existing `Survival_kaplan_meier`/`Survival_log_rank_test`/`Survival_cox_regression` (`SurvivalTool`, numpy/scipy, *more* thorough) — and reverted. Run `tu.find_tools(query="<capability, not brand>")` for every candidate. Audit as of 2026-06-15:

| Roadmap candidate | Status | Existing tool(s) |
|---|---|---|
| Survival (KM/log-rank/Cox) | ❌ ALREADY EXISTS | `Survival_kaplan_meier`, `Survival_log_rank_test`, `Survival_cox_regression` |
| Dose-response / IC50 | ❌ ALREADY EXISTS | `DoseResponse_fit_curve`, `DoseResponse_calculate_ic50`, `DoseResponse_compare_potency` |
| Enzyme kinetics (Km/Vmax) | ❌ ALREADY EXISTS | `EnzymeKinetics_calculate` (ScientificCalculatorTool) |
| PK NCA (AUC/Cmax) | ❌ ALREADY EXISTS | `NCA_compute_parameters`, `NCA_fit_one_compartment`, `NCA_calculate_bioavailability` |
| Population genetics (HWE/Fst) | ❌ ALREADY EXISTS | `PopGen_hwe_test`, `PopGen_fst`, `PopGen_inbreeding`, `PopGen_haplotype_count` |
| Meta-analysis | ❌ ALREADY EXISTS | `MetaAnalysis_run` |
| Bulk RNA-seq DE (DESeq2) | ❌ ALREADY EXISTS | `run_deseq2_analysis` |
| Sequence utils (translate/ORF/GC/revcomp) | ❌ ALREADY EXISTS | `DNATool` (10 tools) |
| Drug synergy (Bliss/HSA/ZIP/Loewe) | ❌ ALREADY EXISTS | `DrugSynergyTool` (5 tools) |
| Generic stats | ⚠️ PARTIAL | `Statistics_test` (thin: chi-square/fisher/OLS), `expression_anova_per_gene`, `Epidemiology_*` |
| **ROC / AUC** | ✅ TRUE GAP → built | shipped as `ROC_analysis` (PR #260) |
| edgeR / limma DE | ✅ TRUE GAP | only DESeq2 exists |
| Expression-matrix PCA | ✅ TRUE GAP | none |
| FASTQ QC | ✅ TRUE GAP | none (SRA/ENA hits are DB search, not QC compute) |
| Single-cell QC/clustering compute | ✅ TRUE GAP | none (CellMarker hits are DB lookups) |
| Network proximity | ✅ TRUE GAP | none |
| Methylation density | ✅ TRUE GAP | none |
| dN/dS | ✅ TRUE GAP | none |
| Variant calling (GATK BAM→VCF) | ✅ TRUE GAP | none (`VCFStatsTool` counts an existing VCF; doesn't call) |
| Microbiome diversity / MS metabolomics / MS proteomics / image segmentation | ✅ TRUE GAP (Part B) | none |

### Generality gate — read before promoting ANY script

A skill script existing is **not** sufficient reason to make it a tool. Many of these scripts were written to hit one benchmark question and bake in that question's conventions, file format, or — worst — pre-compute a menu of answer variants. Promoting those verbatim would encode answers, the exact anti-pattern to avoid. **Promote the *method*, not the script.** A candidate passes only if all three hold:

1. **Standard input shape** — accepts any VCF / any count matrix / any score-label pair, not one benchmark's column names or a 2-row VarSeq Excel layout.
2. **Conventions are parameters** — analysis choices (denominator definition, transform, orientation, filters) are exposed as arguments with sane defaults, not hardcoded to one question's "correct convention."
3. **Returns one standard result** — the canonical output of a method, **not** a menu of pre-computed variants whose purpose is "so the agent can match the published value."

Any script whose docstring says it emits many variants *to match GT*, or that hardcodes a single benchmark's convention/format, **fails** the gate. Its underlying method may still be worth building — but cleanly, from the engine, with the convention as a parameter. The benchmark-specific gotcha stays in the **skill** as guidance, never inside the tool.

Worked classification of the scripts audited 2026-06-15:

| Script | Verdict | Reason |
|---|---|---|
| `gatk_haplotypecaller_pipeline.py` | ✅ promote as-is | any ref/BAM/FASTQ; ploidy/threads as params; canonical counts |
| `r_edger_limma_wrapper.py` | ✅ promote as-is | any matrix+design+contrast; method/thresholds as params |
| `VCFStatsTool` (shipped) | ✅ general | any VCF; filters as params; standard bcftools output |
| `enrichgo_runner.py` | ⚠️ extract method only | core enrichGO+simplify is general; drop the "emit raw+simplified to pick" and `--candidate` answer-crutches |
| `stat_tests.py` | ⚠️ rebuild on scipy | inputs general, but pure-stdlib reimplementation is a sandbox artifact |
| `pca_variance.py` | ❌ do NOT promote | "emits MANY variants so the agent can match the published value"; default `projid` |
| `gene_length_correlation.py` | ❌ do NOT promote | same "emit both to match published value" answer-sweep |
| `variant_fraction.py` | ❌ do NOT promote | hardcodes coding-denominator convention + VarSeq 2-row format |
| `coding_variant_filter.py` | ❌ do NOT promote | specific VarSeq format + filter convention |

### Design pattern for every item below (mirror `VCFStatsTool`)

- Pure local compute, **no network / no API key**; never raise from `run()` — return `{"status": "error", "error": ...}`.
- `requires_local_input: true` so `scripts/test_new_tools.py` skips live execution (no shippable fixture).
- Config key is **`"type"`** (not `"class"`); register in **both** `default_config.py` (`default_tool_files`) and `_lazy_registry_static.py` (`STATIC_LAZY_REGISTRY`).
- `return_schema` with `oneOf` (success + error); unit test in `tests/unit/` that generates a fixture and skips when the binary/lib is absent.
- **Reuse the existing skill script** as the implementation core — this is a promotion, not a rewrite. The skill keeps the script *and* gains a one-call tool form (as `variant-analysis` now does for VCF).

#### Dependencies — use the framework's optional-dependency design

**Only `numpy>=2.2` and `pandas>=2.2` are core deps.** `scipy`, `statsmodels`, `lifelines`, `scikit-learn`, `scikit-bio`, `scanpy`, `gseapy` are **optional extras** (`pyproject.toml` groups `ml`/`singlecell`/`bioinformatics`/`all`) — absent on a default install and in the CI core-test env.

ToolUniverse has a **first-class design** for this — don't fight it:

- **Lazy-loader graceful degradation** (`tool_registry.py`): when `lazy_import_tool` hits an `ImportError` importing a tool's module, it calls `mark_tool_unavailable(...)`, which records the failure and uses `_extract_missing_package()` to capture the missing package name. The tool is dropped from the registry; the rest of ToolUniverse keeps working. Users/agents can query `get_tool_errors()` to see exactly which package a tool needs.
- **`required_packages` config field** — declarative; surfaced in `get_tool_info`/CLI as `Required: …`. (It documents the need; the *enforcement* is the lazy-loader path above, not this field.)
- **`pyproject.toml` optional extras** — add the lib to the right group (`ml`/`bioinformatics`/`singlecell`/`all`) so installers/CI can opt in with `pip install tooluniverse[ml]`.
- **Tool-side guard** — module-level `try: import heavy_lib; FLAG=True except ImportError: FLAG=False` (the `blast_tool` `BIOPYTHON_AVAILABLE` pattern), or a guarded import inside `run()` returning a clean `{"status":"error","error":"pip install …"}` (the `cellxgene` pattern). Never raise.

Decision, per tool:
1. **If the math is simple, reimplement on numpy/pandas (core)** so the tool works for *everyone* — strictly better than an optional dep, which makes the tool gracefully *unavailable* on default installs. ROC/AUC (tie-aware Mann-Whitney rank sum), HWE/Fst, dN/dS, network proximity, NCA trapezoids, fold-changes, basic curve fits all qualify. This is why the shipped `ROC_analysis` uses numpy, not sklearn.
2. **If it genuinely needs a heavy library** (lifelines Cox, scanpy clustering, R DESeq2/edgeR, gseapy), use the framework design: **declare `required_packages` + add to a `pyproject` extra + module-level/guarded import + `pytest.mark.skipif` the unit test when absent** (mirror the bcftools `needs_bcftools` guard). The tool is then cleanly "needs `lifelines`" rather than broken.

External **binaries** (bcftools, GATK, bwa) have no `required_packages` analogue — guard with `shutil.which(...)` + a clear error, as `VCFStatsTool` does.

### Dependency status (drives the Effort column)

**Core ToolUniverse deps (always present — safe to import in a tool):** `numpy>=2.2`, `pandas>=2.2`.

**Optional extras — installed on *this dev machine* but NOT on a default install / in CI core-tests** (so importing one needs the three guards above): `scipy`, `statsmodels`, `lifelines`, `scikit-learn`, `scanpy`, `anndata`, `gseapy`, `biopython`, `pysam`, `cyvcf2`, `rdkit`. Not installed even here: `scikit-bio ✗`, `cellpose ✗`, `pyopenms ✗`.

**External binaries on this machine:** `Rscript ✓  samtools ✓  bcftools ✓  bwa ✓  gatk ✓  mafft ✓` · missing `seqkit ✗  fastp ✗  minimap2 ✗  iqtree ✗` (binaries are guarded with `shutil.which`, not `required_packages`).

> "Effort" — reimplementable on numpy/pandas = **S** (½ day). Needs an optional Python lib (declare + guard + skipif) or an installed binary = **M**. New compute from scratch / new dependency to add = **L**.
> "Impact" proxy = BixBench category weight (RNA-seq 69 · WGS/variant 64 · enrichment 32 · phylogenetics 33 · imaging 21 · stats 17 · single-cell) + field ubiquity. No real usage telemetry exists; treat as a planning heuristic.

---

## Part A — Build tools ONLY for confirmed gaps

The audit table above already removed everything that exists. What remains below is **only the `find_tools`-confirmed true gaps.** Each row: implementation basis, what it computes, dependency, effort, impact. (Rows for Survival, dose-response, enzyme kinetics, PK NCA, popgen, meta-analysis, DESeq2 were deleted — those tools already exist.)

### Tier 1 — broad impact, build first

| Proposed tool | Basis | Computes | Dep | Effort | Impact |
|---|---|---|---|---|---|
| **`Stats_test`** (EXTEND existing `Statistics_test`, which is thin: chi-square/fisher/OLS only) | `statistical-modeling/stat_tests.py` (+ scipy/statsmodels) | add t-test / Mann–Whitney / Wilcoxon / one-way & two-way ANOVA / logistic & ordinal regression on a user table | scipy, statsmodels (optional) | S–M | ★★★★★ touches nearly every analysis |
| **`Enrichment_run`** (check overlap with existing `Enrichr_enrich`/`PANTHER_enrichment`, which are API-based; this is a LOCAL clusterProfiler/gseapy path) | `gene-enrichment/enrichgo_runner.py` (method only — drop the answer-crutches) | local GO over-representation + GSEA/prerank from a gene list | Rscript / gseapy (optional) | S–M | ★★★★ enrichment=32 |
| **`RNAseq_DE_edger_limma`** | `rnaseq-deseq2/r_edger_limma_wrapper.py` | edgeR / limma-voom DE on a count matrix (complements existing `run_deseq2_analysis`) | Rscript (optional) | S | ★★★★ RNA-seq=69 |
| **`Expr_matrix_pca`** | rebuild clean (do **not** port the answer-sweep `pca_variance.py`) | PCA %-variance per PC on a matrix (single orientation; transform as a parameter) | numpy (core) | S | ★★★ recurring RNA-seq sub-question |
| **`Variant_call_gatk`** | `variant-analysis/gatk_haplotypecaller_pipeline.py` | BAM→VCF SNP/indel calling (BWA → sort → HaplotypeCaller); pairs with `VCF_*` | gatk/bwa/samtools (binaries) | M | ★★★★ WGS/variant, the bix-61 family |
| ~~`ROC_analysis`~~ | — | **DONE** — shipped pure-numpy in PR #260 | numpy (core) | — | ✅ |

### Tier 2 — valuable compute, narrower

| Proposed tool | Basis | Computes | Dep | Effort | Impact |
|---|---|---|---|---|---|
| **`SingleCell_qc_cluster`** | `single-cell/scrna_qc.py`, `qc_metrics.py`, `normalize_data.py`, `find_markers.py` | scRNA QC gating, normalization, Leiden clustering, marker/cell-type annotation on an h5ad | scanpy, anndata (optional) | M | ★★★ huge field |
| **`Image_segment`** | `image-analysis/segment_cells.py`, `measure_fluorescence.py` | cell/nucleus segmentation + count, fluorescence quantification | scikit-image (classical); cellpose ✗ (DL) | M | ★★★ imaging=21 |
| **`dNdS`** | `comparative-genomics/dnds.py` | dN/dS (Ka/Ks, Nei–Gojobori) between two coding sequences | biopython (optional) | S | ★★ molecular evolution |
| **`FASTQ_qc`** | `fastq-qc/run_fastq_qc.py` | read count, length, GC, per-base quality, Q20/Q30, duplication, adapter | biopython/pysam (seqkit/fastp ✗ for speed) | S–M | ★★★ ubiquitous first step |
| **`Methylation_density`** | `epigenomics/methylation_density.py` | CpG methylation density stats from a long-format methylation CSV | pandas (core) | S | ★★ epigenomics=12 |
| **`Network_proximity`** | `network-pharmacology/network_proximity.py` | network proximity Z-score between drug targets and a disease gene set | numpy (core) | S | ★★ network pharmacology |
| **`Network_proximity`** | `network-pharmacology/network_proximity.py` | Network proximity Z-score between drug targets and a disease gene set | numpy ✓ | S | ★★ network pharmacology |
| **`HLA_population_coverage`** | `vaccine-design/population_coverage.py` | IEDB-style population coverage for a set of T-cell epitopes | numpy ✓ | S | ★★ vaccine design |
| **`Antibody_developability`** | `antibody-engineering/developability.py` | Aggregation/charge/hydrophobicity liability flags from an antibody sequence | biopython ✓ | S | ★★ antibody engineering |

### Tier 3 — pure calculators (mostly ALREADY exist)

The big calculator families are already tools: `ClinicalCalculatorTool` (10), `ScientificCalculatorTool` (incl. `EnzymeKinetics_calculate`, `EquilibriumSolver_calculate`, `MolecularFormula_analyze`), `EpidemiologyTool` (R0/NNT/Bayes/diagnostic), `DrugSynergyTool` (5). The only `computational-biophysics/` calculators without an obvious tool home are the clinical-dosing ones (`radioactive_decay`, `iv_drip_rate`, `fluid_calculations`, `burn_fluids`) — low priority, and arguably belong in `ClinicalCalculatorTool` if anywhere. Confirm with `find_tools` before adding any.

### Explicitly **do NOT** promote — two categories

**(i) Benchmark answer-sweepers** — see the Generality gate table: `pca_variance.py`, `gene_length_correlation.py`, `variant_fraction.py`, `coding_variant_filter.py`. These bake in one question's convention/format or emit a menu of variants to match a hidden GT. Build the underlying method cleanly if it's worth having; never wrap these.

**(ii) Reference-lookup "facts" scripts

These are static knowledge crutches for multiple-choice benchmarks, not compute-on-data. Turning them into tools would just freeze a snapshot of facts the model already knows (and risks the answer-memorization anti-pattern). Leave them as skill helpers: `organic-chemistry/chemistry_facts.py`, `sequence-analysis/biology_facts.py` + `amino_acids.py`, `drug-drug-interaction/pharmacology_ref.py`, `metabolomics/metabolism_ref.py`, `rare-disease-diagnosis/clinical_patterns.py`, `drug-synergy/synergy_reference.py`, `crispr-screen-analysis/reference_gene_sets.py`, `computational-biophysics/mc_analyzer.py`.

> Several scripts are simple sequence/format utilities (`sequence-analysis/translate_dna.py`, `sequence_tools.py`; `phylogenetics/format_alignment.py`; `rnaseq-deseq2/load_count_matrix.py`, `convert_rds_to_csv.py`). Worth promoting **only** if bundled into a broader `Sequence_utils` / `File_convert` tool rather than one tool each.

---

## Part B — Net-new gaps (no script **and** no tool)

| Capability | Why it matters | Suggested basis | Dep | Effort |
|---|---|---|---|---|
| **Microbiome α/β diversity** | Core of every 16S/shotgun study; `microbiome-research` & `metagenomics-analysis` skills have **zero** compute scripts | Shannon/Simpson/Chao1, Bray–Curtis/UniFrac, PCoA from a feature table | scikit-bio ✗ (pip) or pure numpy | M |
| **Metabolomics MS peak-picking / feature extraction** | `metabolomics` skill only has a *reference* script; no way to process raw spectra | centWave/feature detection, alignment, annotation from mzML | pyopenms ✗ / matchms | L |
| **Proteomics MS quantification** | Major omics layer with no compute tool (only PRIDE/UniProt lookups) | mzML/MaxQuant parse → label-free / TMT quant, limma DE | pyteomics / pyopenms ✗ | L |
| **Long-read / structural-variant calling on a BAM** | Short-read SNV calling will exist (Tier 1 `Variant_call_gatk`); SV/long-read is uncovered | Sniffles/cuteSV-style SV calls from aligned long reads | minimap2 ✗, sniffles ✗ | L |
| **Molecular-dynamics simulation** | Requested in older gap analyses; no tool | short OpenMM equilibration + trajectory metrics | openmm ✗, heavy compute | L (likely out of scope) |

---

## Recommended sequencing

**Wave 1 (highest leverage, all deps installed, S–M effort) — the "analysis core":**
`Stats_test` + `Survival_analysis` → `Enrichment_run` → `Variant_call_gatk` (closes the BAM→VCF→stats chain alongside the new `VCF_*` tools) → `ROC_analysis`.
These five cover the analysis steps that recur across the largest share of real questions and currently force ad-hoc code.

**Wave 2 (round out the omics compute layer):**
`RNAseq_DE_edger_limma` + `Expr_matrix_stats` → `SingleCell_qc_cluster` → `FASTQ_qc` → `Curve_fit` + `PK_nca`.

**Wave 3 (net-new, accept a new dependency):**
`Microbiome_diversity` (pip `scikit-bio`) → `Image_segment` (classical first, cellpose optional) → metabolomics/proteomics MS (the heavy L items).

**One PR per tool family** (not per script), each: tool class + JSON + dual registration + unit test + the owning skill updated to point at the new tool (as `variant-analysis` now does for VCF). Run the anti-overfitting check (`check_memorization.py`) before each ship — no benchmark names or GT values in tool/skill content.

---

## What is **not** missing (so we don't re-chase it)

Knowledge/database breadth is strong and was spot-checked: clinical terminology (SNOMED/ICD/LOINC/UMLS), DepMap & GDSC cell-line dependency/drug-response, antibody/TCR-BCR & IMGT, nutrition/food, exposome/environmental, wearables/ECG-EEG, Hi-C/3D-genome lookups, docking (NvidiaNIM DiffDock), and the omics *databases* (PRIDE, MetabolomicsWorkbench, MGnify, CELLxGENE, GTEx, ENCODE) are all present. The recently-shipped skills (spatial, proteomics, multi-omics, structural-variant, metagenomics) also closed the 2026-02 skill-level gaps. The remaining work is the **compute layer**, not breadth.
