---
name: tooluniverse-image-analysis
description: Production-ready microscopy image analysis and quantitative imaging data skill for colony morphometry, cell counting, fluorescence quantification, and statistical analysis of imaging-derived measurements. Processes ImageJ/CellProfiler output (area, circularity, intensity, cell counts), performs Dunnett's test, Cohen's d effect size, power analysis, Shapiro-Wilk normality tests, two-way ANOVA, polynomial regression, natural spline regression with confidence intervals, and comparative morphometry. Supports CSV/TSV measurement tables, multi-channel fluorescence data, colony swarming assays, and neuron counting datasets. Use when analyzing microscopy measurement data, colony area/circularity, cell count statistics, swarming assays, co-culture ratio optimization, or answering questions about imaging-derived quantitative data.
---

# Microscopy Image Analysis and Quantitative Imaging Data

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

**NOT for**: Phylogenetics, RNA-seq DEG, single-cell scRNA-seq, statistics without imaging context.

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

## Common BixBench Patterns

| Pattern | Example Question | Workflow |
|---------|-----------------|----------|
| Colony Morphometry (bix-18) | "Mean circularity of genotype with largest area?" | Group by Genotype → max mean Area → report Circularity |
| Cell Counting (bix-19) | "Cohen's d for NeuN counts?" | Filter → split by Condition → pooled SD → Cohen's d |
| Multi-Group (bix-41) | "How many ratios equivalent to control?" | Dunnett's for Area AND Circularity → count non-significant in BOTH |
| Regression (bix-54) | "Peak frequency from natural spline?" | Ratio→frequency → spline(df=4) → grid search peak → CI |

---

## Raw Image Processing

```python
from scripts.segment_cells import count_cells_in_image
result = count_cells_in_image(image_path="cells.tif", channel=0, min_area=50)
```

Segmentation: Nuclei → Otsu+watershed; Colonies → Otsu; Phase contrast → adaptive threshold.
See **references/segmentation.md**, **references/cell_counting.md**, **references/image_processing.md**.

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
