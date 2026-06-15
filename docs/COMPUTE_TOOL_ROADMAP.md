# Compute-Tool Roadmap

**Date:** 2026-06-15 · **Author:** coverage audit
**Question it answers:** *From the perspective of what tools and skills cover, what is ToolUniverse still missing?*

---

## Executive summary

ToolUniverse's coverage is **lopsided**, and the lopsidedness is the opportunity:

| Layer | Inventory | Verdict |
|---|---|---|
| **Knowledge / database-access tools** (query an API by ID/region/name) | 568 source APIs, ~2,534 tools | ✅ Comprehensive — *not* the gap |
| **Local-compute tools** (run a deterministic analysis on the user's own file) | **5 of 2,539** tools (`phykit_batch_analysis`, `run_deseq2_analysis`, `VCF_summary_stats`, `VCF_count_variants`, `VCF_normalize`) | ❌ Structural hole |
| **Analysis capability locked in skill scripts** (real compute, but not a callable tool) | **86 scripts across 33 skills** | ⚠️ Agent must re-discover and run ad-hoc every time → non-reproducible |

The plugin already *knows how* to do most standard analyses — the procedures live in 86 `skills/*/scripts/*.py`. But because they are not registered tools, an MCP agent either re-derives them as throwaway code (the root cause of non-deterministic counts, e.g. BixBench bix-61 indel totals) or never finds them. **The highest-leverage work is promoting the genuine compute scripts into validated, callable tools** — the pattern just established by `VCFStatsTool`.

This document is the prioritized backlog. It is **not** a commitment to build all of it; it is the map to choose from.

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

### Dependency status on this machine (drives the Effort column)

`Rscript ✓  samtools ✓  bcftools ✓  bwa ✓  gatk ✓  mafft ✓` · missing `seqkit ✗  fastp ✗  minimap2 ✗  iqtree ✗`
`scipy ✓  numpy ✓  pandas ✓  statsmodels ✓  lifelines ✓  scikit-learn ✓  scanpy ✓  anndata ✓  gseapy ✓  biopython ✓  pysam ✓  cyvcf2 ✓  rdkit ✓` · missing `scikit-bio ✗  cellpose ✗  pyopenms ✗`

> "Effort" assumes the script already exists and the dependency is installed = **S** (small, ~½ day: wrap + schema + test). Add a dependency = **M**. New compute from scratch = **L**.
> "Impact" proxy = BixBench category weight (RNA-seq 69 · WGS/variant 64 · enrichment 32 · phylogenetics 33 · imaging 21 · stats 17 · single-cell) + field ubiquity. No real usage telemetry exists; treat as a planning heuristic.

---

## Part A — Promote skill scripts to callable tools

Grouped by value tier. Each row: the script that becomes the implementation, what it computes, the dependency, effort, impact.

### Tier 1 — broad impact, dependency installed, build first

| Proposed tool | From script(s) | Computes | Dep | Effort | Impact |
|---|---|---|---|---|---|
| **`Stats_test`** (richer engine; existing `Statistics_test` is pure-Python chi-square only) | `statistical-modeling/stat_tests.py`, `logistic_regression_or.py`, `power_analysis.py` | t-test / Mann–Whitney / Wilcoxon / one-way & two-way ANOVA / linear & logistic (incl. ordinal) regression / power & sample-size, on a user table | scipy, statsmodels ✓ | S–M | ★★★★★ touches nearly every analysis |
| **`Survival_analysis`** | (stats skill; lifelines) | Kaplan–Meier curves, median survival, log-rank, Cox PH hazard ratios from a survival table | lifelines ✓ | S | ★★★★ clinical + oncology |
| **`Enrichment_run`** | `gene-enrichment/enrichgo_runner.py`, `gseapy_enrichment_runner.py` | Deterministic GO/pathway over-representation (clusterProfiler::enrichGO) and GSEA/prerank (gseapy) from a gene list | Rscript ✓, gseapy ✓ | S–M | ★★★★★ BixBench enrichment=32 |
| **`RNAseq_DE_edger_limma`** | `rnaseq-deseq2/r_edger_limma_wrapper.py` | edgeR / limma-voom DE on a count matrix (complements the existing DESeq2 tool) | Rscript ✓ | S | ★★★★ RNA-seq=69 |
| **`Expr_matrix_stats`** | **rebuild clean** (`one_way_anova_f.py` is fine; PCA method only — do **not** port `pca_variance.py`/`gene_length_correlation.py`, which fail the gate) | PCA %-variance per PC (single orientation; transform as a parameter) and per-gene one-way ANOVA F/p on a matrix | numpy, scipy ✓ | S–M | ★★★ recurring RNA-seq sub-questions, but trim the answer-sweep scripts |
| **`Variant_call_gatk`** | `variant-analysis/gatk_haplotypecaller_pipeline.py` | BAM→VCF SNP/indel calling (BWA align → sort → HaplotypeCaller), with canonical counts; pairs with the new `VCF_*` tools | gatk, bwa, samtools ✓ | M | ★★★★ WGS/variant questions, the bix-61 family |
| **`ROC_analysis`** | `diagnostic-test-evaluation/roc_analysis.py` | ROC curve, AUC, Youden-optimal cutoff, sensitivity/specificity from scores+labels | scikit-learn ✓ | S | ★★★★ diagnostics + any classifier eval |

### Tier 2 — valuable compute, narrower or one extra dependency

| Proposed tool | From script(s) | Computes | Dep | Effort | Impact |
|---|---|---|---|---|---|
| **`Curve_fit`** (dose-response + enzyme kinetics) | `dose-response/fit_dose_response.py`, `enzyme-kinetics/fit_michaelis_menten.py` | 4-param logistic (IC50/EC50/Hill) and Michaelis–Menten (Km/Vmax/Ki) nonlinear fits | scipy ✓ | S | ★★★ pharmacology, assays |
| **`SingleCell_qc_cluster`** | `single-cell/scrna_qc.py`, `qc_metrics.py`, `normalize_data.py`, `find_markers.py` | scRNA QC gating, normalization, Leiden clustering, marker/cell-type annotation on an h5ad | scanpy, anndata ✓ | M | ★★★ huge field, low BixBench weight |
| **`Image_segment`** | `image-analysis/segment_cells.py`, `measure_fluorescence.py` | Cell/nucleus segmentation + count, fluorescence intensity quantification | scikit-image ✓ (classical); cellpose ✗ (DL) | M | ★★★ imaging=21 |
| **`PK_nca`** | `pharmacokinetics/nca_from_csv.py` | Non-compartmental PK (AUC, Cmax, Tmax, t½, CL/F) from concentration–time CSV | numpy, scipy ✓ | S | ★★★ pharmacometrics |
| **`PopGen_calc`** | `population-genetics/popgen_calculator.py` | Hardy–Weinberg, Fst, inbreeding coefficient, haplotype frequencies | numpy ✓ | S | ★★★ pop-gen |
| **`Meta_analysis`** | `meta-analysis/meta_analysis.py` | Fixed/random-effects pooled effect, heterogeneity (I²), forest-plot data | scipy ✓ | S | ★★★ evidence synthesis |
| **`dNdS`** | `comparative-genomics/dnds.py` | dN/dS (Ka/Ks, Nei–Gojobori) between two coding sequences | biopython ✓ | S | ★★ molecular evolution |
| **`FASTQ_qc`** | `fastq-qc/run_fastq_qc.py` | Read count, length, GC, per-base quality, Q20/Q30, duplication, adapter — entry point of every sequencing pipeline | biopython/pysam ✓ (seqkit/fastp ✗ for speed) | S–M | ★★★ ubiquitous first step |
| **`Methylation_density`** | `epigenomics/methylation_density.py` | CpG methylation density stats from a long-format methylation CSV | pandas ✓ | S | ★★ epigenomics=12 |
| **`Network_proximity`** | `network-pharmacology/network_proximity.py` | Network proximity Z-score between drug targets and a disease gene set | numpy ✓ | S | ★★ network pharmacology |
| **`HLA_population_coverage`** | `vaccine-design/population_coverage.py` | IEDB-style population coverage for a set of T-cell epitopes | numpy ✓ | S | ★★ vaccine design |
| **`Antibody_developability`** | `antibody-engineering/developability.py` | Aggregation/charge/hydrophobicity liability flags from an antibody sequence | biopython ✓ | S | ★★ antibody engineering |

### Tier 3 — pure calculators (extend the existing calculator family, lower urgency)

`computational-biophysics/` ships 8 deterministic calculators (`enzyme_kinetics`, `epidemiology` R0/NNT/Bayes, `radioactive_decay`, `herd_immunity`, `iv_drip_rate`, `fluid_calculations`, `burn_fluids`, `env_risk_assessment`) and `inorganic-physical-chemistry/equilibrium_solver.py`. These match the **already-shipped** `ClinicalCalculatorTool` pattern and could be folded into a `ScientificCalculator` family. Medium-low priority — they are short and self-contained.

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
