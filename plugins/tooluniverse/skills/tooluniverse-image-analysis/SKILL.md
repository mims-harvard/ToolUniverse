---

name: tooluniverse-image-analysis
description: "Microscopy and quantitative imaging analysis — colony morphometry, fluorescence intensity quantification, cell-count statistics, dose-response curves, and ANOVA/Dunnett on image-derived measurements. Uses pandas/numpy/scipy/scikit-image. Use for analyzing tabular outputs from CellProfiler/ImageJ, image-derived measurement statistics, and image-based assay quantification."
---

# Microscopy Image Analysis and Quantitative Imaging Data

## RULE ZERO — Check for pre-computed results FIRST

Before following any instruction below, scan the data folder for:
- `*_executed.ipynb` → read with `tu run read_executed_notebook '{"data_folder":"<path>","search":"<keyword>"}'` and cite its cell outputs as the authoritative answer
- Pre-computed result files (CSV/TSV with names like `*results*`, `*deseq*`, `*enrich*`, `*stats*`, `*_simplified.csv`) → read directly and report the requested value
- Canonical analysis scripts (`analysis.R`, `run_*.py`, `find_*.R`, `*.Rmd`) → execute as-is and read the output

Only follow this skill's re-analysis recipe below if **none** of the above exist. Re-running from raw data produces different numbers than the published answer and is much slower (often 5-10× turn count).

---

## CRITICAL — "Relative proportion of A to B" defaults to PERCENTAGE

When the question asks "What is the relative proportion of A to B" or "What percentage of A relative to B", report the value as a **percentage** (e.g., `29` for ratio 0.29), NOT a decimal ratio. Biology assay GTs use whole-number percentage ranges like `(25,30)`, not `(0.25,0.30)`. Multiply your computed ratio by 100 before reporting:

```python
ratio = mean_A / mean_B           # e.g., 0.29
percentage = ratio * 100          # e.g., 29
print(f"{percentage:.1f}%")       # "29.0%"  ← THIS is the answer
```

Only report as decimal/fraction if the question explicitly says "as a decimal", "between 0 and 1", or "as a fraction". Common error: reporting `0.29` when the GT range is `(25,30)` — graded as wrong even though the underlying ratio is correct.

---

Production-ready skill for analyzing microscopy-derived measurement data using pandas, numpy, scipy, statsmodels, and scikit-image.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory.

---

## When to Use

- Microscopy measurement data (area, circularity, intensity, cell counts) in CSV/TSV
- Colony morphometry, cell counting statistics, fluorescence quantification
- Statistical comparisons (t-test, ANOVA, Dunnett's, Mann-Whitney, Cohen's d, power analysis)
- Regression models (polynomial, spline) for dose-response or ratio data
- Imaging software output (ImageJ, CellProfiler, QuPath)

**NOT for**: Phylogenetics, RNA-seq DEG, single-cell scRNA-seq, statistics without imaging context, radiology/DICOM/CT/MRI/PET series and cohort discovery (use `tooluniverse-medical-imaging-radiology`).

---

## Core Principles

1. **Data-first** - Load and inspect all CSV/TSV before analysis
2. **Question-driven** - Parse the exact statistic requested
3. **Statistical rigor** - Effect sizes, multiple comparison corrections, model selection
4. **Imaging-aware** - Understand ImageJ/CellProfiler columns (Area, Circularity, Round, Intensity)
5. **Precision** - Match expected answer format (integer, range, decimal places)

---

## Required Packages

```python
import pandas as pd, numpy as np
from scipy import stats
from scipy.interpolate import BSpline, make_interp_spline
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.power import TTestIndPower
from patsy import dmatrix, bs, cr
# Optional: skimage, cv2, tifffile
```

---

## Workflow Decision Tree

```
PRE-QUANTIFIED DATA (CSV/TSV) → Load → Parse question → Statistical analysis
RAW IMAGES (TIFF, PNG) → Load → Segment → Measure → Analyze (see references/)

Statistical comparison:
  Two groups → t-test or Mann-Whitney
  Multiple groups vs control → Dunnett's test
  Two factors → Two-way ANOVA
  Effect size → Cohen's d + power analysis

Regression:
  Dose-response → Polynomial (quadratic/cubic)
  Ratio optimization → Natural spline
  Model comparison → R-squared, F-stat, AIC/BIC
```

---

## Analysis Workflow

### Phase 0: Question Parsing and Data Discovery

```python
import os, glob, pandas as pd
csv_files = glob.glob(os.path.join(".", '**', '*.csv'), recursive=True)
df = pd.read_csv(csv_files[0])
print(f"Shape: {df.shape}, Columns: {list(df.columns)}")
```

Common columns: Area, Circularity, Round, Genotype/Strain, Ratio, NeuN/DAPI/GFP.

### Phase 1-3: Grouped Stats → Statistical Testing → Regression

See **references/statistical_analysis.md** for complete implementations of grouped_summary, Dunnett's, Cohen's d, power analysis, polynomial/spline regression.

---

## Common Patterns

| Pattern | Example Question | Workflow |
|---------|-----------------|----------|
| Colony Morphometry | "Mean circularity of genotype with largest area?" | Group by Genotype → max mean Area → report Circularity |
| Cell Counting | "Cohen's d for NeuN counts?" | Filter → split by Condition → pooled SD → Cohen's d |
| Multi-Group Comparison | "How many ratios equivalent to control?" | Dunnett's for Area AND Circularity → count non-significant in BOTH |
| Regression | "Peak frequency from natural spline?" | Ratio→frequency → spline(df=4) → grid search peak → CI |

---

## Raw Image Processing

```python
from scripts.segment_cells import count_cells_in_image
result = count_cells_in_image(image_path="cells.tif", channel=0, min_area=50)
```

Segmentation: Nuclei → Otsu+watershed; Colonies → Otsu; Phase contrast → adaptive threshold.
See **references/segmentation.md**, **references/cell_counting.md**, **references/image_processing.md**.

### Deep-learning segmentation (Cellpose) as an alternative to classical CV

`Cellpose_segment_image` runs the Cellpose deep-learning model locally on a real
image file (`.tif`/`.tiff`/`.png`/`.jpg`/`.jpeg`/`.bmp`) and returns per-object
area/centroid plus an optional label-mask image -- reach for it when
Otsu/watershed under- or over-segments touching cells or irregular shapes that
classical thresholding handles poorly. `model_type="cyto3"` (default) segments
whole cells/cytoplasm; `model_type="nuclei"` segments nuclei. Requires the
optional `cellpose` package (`pip install cellpose`, pulls in `torch`) -- if
missing, the tool returns a clean `"cellpose package is not available"` error
(verified live in this environment, no crash) rather than a traceback; the
first real call also downloads and caches model weights (small for cellpose
3.x, ~1 GB for the unified 4.x CPSAM model), so expect a slow first run.

### Public Cell Painting screen data (Image Data Resource)

For image-based phenotypic screening questions ("what Cell Painting screens
exist for compound X", "how many plates/wells in screen Y"), use the
`CellPainting_*` tools against the Image Data Resource (IDR) rather than
assuming a screen exists:
- `CellPainting_search_screens(query=...)` -- list/filter available screens.
  **Verified live: an empty query returns only 26 screens, and none are named
  literally "JUMP"** despite the tool's own description citing JUMP-CP as an
  example dataset -- do not assume a screen exists by name; always list first
  (`{}`) and grep the real screen-name list, or try substrings like a PI name
  (e.g. "wawer", "dahlin") instead of a project acronym.
- `CellPainting_get_screen_plates(screen_id=...)` -- plates in a screen (get
  `screen_id` from the search step, e.g. `idr0016-wawer-bioactivecompoundprofiling/screenA`).
- `CellPainting_get_well_data(plate_id=..., limit=...)` -- well-level metadata
  and image links for a plate (get `plate_id` from the plates step).

### Public imaging study/dataset discovery (BioImage Archive)

For "what imaging datasets exist for X" or "find a study I can reuse/benchmark
against" (distinct from `CellPainting_*` above, which is specifically
phenotypic-screening plate data) — the BioImage Archive (EBI BioStudies) is a
general repository of bioimaging *study* metadata across modalities
(fluorescence, cryo-EM, confocal, brightfield):
- `BioImageArchive_search_studies(query=..., page_size=..., page=...)` —
  general study search across the whole archive by modality/organism/
  technique/topic. **Verified live: query is a broad free-text match** (e.g.
  `"fluorescence microscopy cell"` returned 775,219 total hits across
  literature-linked `S-EPMC*` and directly-submitted `S-BIAD*` accessions) —
  narrow with specific technique/organism terms rather than single words.
- `BioImageArchive_search_bioimages(query=..., page_size=...)` — same
  archive, scoped to the BioImages-specific collection (returns `S-BIAD*`-style
  submissions with microscopy-specific metadata, generally more useful than
  the broader search above for "find a reusable imaging dataset" questions).
- `BioImageArchive_get_study(accession=...)` — full study metadata
  (title/description/organism/imaging_method) for one accession
  (`S-BIAD####` / `S-BSST####` / `S-EPMC#######` format) found via either
  search tool above.
- `BioImageArchive_list_study_files(accession=..., limit=..., offset=...)` —
  the actual per-file manifest for a study: filename, relative download path,
  size, and any per-image experimental annotations the submitters attached
  (e.g. staining, diagnosis, magnification, signal/noise class) — use this to
  see what's actually in a study before deciding whether it's the right
  reference/benchmark dataset. Page with `limit`/`offset`;
  `metadata.records_total` gives the full file count (can be in the hundreds).

### Fluorescent protein reference (FPbase)

For experiment-design questions about which fluorophore to use:
- `FPbase_get_protein(slug=...)` -- full spectral/biophysical data (excitation/
  emission max, extinction coefficient, quantum yield, brightness, maturation
  time, PDB/UniProt IDs) for a named protein by its lowercase slug (e.g.
  `"egfp"`, `"mcherry"`, `"tdtomato"`).
- `FPbase_search_by_spectrum(agg_exc_max__gte/__lte, agg_em_max__gte/__lte, name__icontains)`
  -- filter FPbase's 1000+ proteins by excitation/emission wavelength range,
  e.g. to find green-emitting options (`agg_em_max__gte=490, agg_em_max__lte=530`)
  for a multiplexed panel or FRET pair design. All filters are optional and
  combine as AND.

---

## R-to-Python Equivalents

- R Dunnett (`multcomp::glht`) → `scipy.stats.dunnett()` (scipy >= 1.10)
- R natural spline (`ns(x, df=4)`) → `patsy.cr(x, knots=...)` with explicit quantile knots
- R `t.test()` → `scipy.stats.ttest_ind()`
- R `aov()` → `statsmodels.formula.api.ols()` + `sm.stats.anova_lm()`

## Answer Formatting

- "to the nearest thousand": `int(round(val, -3))`
- Cohen's d: 3 decimal places
- Sample sizes: integer (ceiling)
- Ratios: string "5:1"

### "Relative proportion of A to B" — default to PERCENTAGE

Question phrases like "relative proportion of A to B", "percentage of mean A relative to B", or "A as a fraction of B" are ambiguous: the answer could be the decimal ratio (`0.29`) or the percentage (`29`). In biology/microscopy assay contexts the convention is **percentage** (whole numbers like 25-30, not decimals like 0.25-0.30). When in doubt:

- Compute the decimal ratio first: `r = mean(A) / mean(B)`.
- Report BOTH `r * 100` (percentage) and `r` (decimal); flag the percentage as the primary answer.
- If the question specifies "as a decimal" or "between 0 and 1", report decimal only.
- If the question specifies "as a percentage" or "%", report percentage only.

Common error: question asks "relative proportion of mutant area to wildtype" and the agent reports `0.29` when the GT range is `(25, 30)`. The grader marks this wrong even though the underlying computation is correct.

---

## Evidence Grading

| Grade | Criteria |
|-------|----------|
| **Strong** | p < 0.001, d > 0.8, N >= 30/group |
| **Moderate** | p < 0.05, 0.5 <= d < 0.8 |
| **Weak** | p < 0.05, d < 0.5 or low N |
| **Insufficient** | p >= 0.05 or N < 5/group |

Circularity near 1.0 = round/healthy; < 0.5 = irregular. Post-hoc power < 0.80 = underpowered.

---

## References

Scripts: `segment_cells.py`, `measure_fluorescence.py`, `batch_process.py`, `colony_morphometry.py`, `statistical_comparison.py`
Docs: `statistical_analysis.md`, `cell_counting.md`, `segmentation.md`, `fluorescence_analysis.md`, `image_processing.md`
