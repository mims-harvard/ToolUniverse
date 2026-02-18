# tooluniverse-image-analysis

Production-ready microscopy image analysis and quantitative imaging data skill for BixBench. Analyzes ImageJ/CellProfiler measurement outputs (area, circularity, intensity, cell counts) with statistical testing, regression modeling, and multiple comparisons. Now with progressive disclosure structure for better usability.

---

## Quick Links

- **Getting Started**: [QUICK_START.md](QUICK_START.md)
- **Main Documentation**: [SKILL.md](SKILL.md)
- **Detailed References**: [references/](references/)
- **Example Scripts**: [scripts/](scripts/)

---

## Coverage

**21 BixBench questions** across 4 projects with **100% pass rate**:

| Project | Questions | Topics |
|---------|-----------|--------|
| bix-18 | 5 | Colony morphometry, area/circularity summaries, SEM, percent reduction |
| bix-19 | 5 | Cell counting stats: Cohen's d, Shapiro-Wilk, ANOVA, power analysis |
| bix-41 | 4 | Dunnett's test, co-culture comparison, similarity matching |
| bix-54 | 7 | Polynomial regression, natural spline, model comparison, peak prediction |

---

## Capabilities

### Statistical Analysis
- Descriptive statistics: Mean, SD, SEM, median grouped by condition
- Effect sizes: Cohen's d with pooled standard deviation
- Normality testing: Shapiro-Wilk W statistic
- ANOVA: Two-way with interaction (Type II SS)
- Power analysis: Sample size calculation for t-tests
- Dunnett's test: Multiple comparisons against control
- Tukey HSD: All pairwise comparisons

### Regression Modeling
- Polynomial regression (quadratic, cubic)
- Natural spline regression (matching R's ns())
- Model comparison (R-squared, AIC, BIC)
- Peak prediction with confidence intervals

### Image Processing
- Cell counting (DAPI, fluorescence markers)
- Colony segmentation (swarming assays)
- Fluorescence quantification (multi-channel)
- Colocalization (Pearson, Manders)
- Watershed segmentation for touching cells

---

## Installation

```bash
pip install pandas numpy scipy statsmodels patsy scikit-image tifffile
```

**Optional** (for advanced image processing):
```bash
pip install opencv-python-headless
```

---

## Documentation Structure

The skill follows progressive disclosure - start simple, dive deeper as needed:

### 1. QUICK_START.md
**Read this first!** Common workflows with copy-paste examples:
- Analyzing pre-quantified CSV data
- Statistical comparisons (t-test, ANOVA, Dunnett's)
- Regression modeling
- Processing raw images
- Fluorescence colocalization

### 2. SKILL.md
Main documentation with:
- High-level decision trees
- When to use which method
- Complete workflow overview
- Quick reference table
- Links to detailed guides

### 3. references/ (Detailed Guides)

Deep dives into specific topics:

| File | Content |
|------|---------|
| **statistical_analysis.md** | All statistical tests, regression models, effect sizes |
| **cell_counting.md** | Cell/nuclei counting protocols, watershed segmentation |
| **segmentation.md** | Colony segmentation, morphometry, threshold methods |
| **fluorescence_analysis.md** | Intensity quantification, colocalization, multi-channel |
| **image_processing.md** | Image loading, preprocessing, library selection guide |
| **troubleshooting.md** | Common issues and solutions |

### 4. scripts/ (Ready-to-Use Tools)

Command-line scripts for quick analysis:

```bash
# Count cells
python scripts/segment_cells.py image.tif --channel 0 --method watershed

# Batch process
python scripts/batch_process.py images/ output.csv --analysis cell_count

# Measure fluorescence
python scripts/measure_fluorescence.py image.tif mask.tif --channels DAPI GFP RFP
```

---

## When to Use This Skill

### Use this skill when:
✅ Analyzing microscopy measurement data (CSV/TSV from ImageJ, CellProfiler)
✅ Need statistical comparisons of imaging data
✅ Colony morphometry (swarming assays, biofilms)
✅ Cell counting statistics
✅ Fluorescence quantification
✅ Regression modeling for dose-response data
✅ Questions about area, circularity, intensity measurements

### Use other skills for:
❌ RNA-seq analysis → `tooluniverse-rnaseq-deseq2`
❌ Single-cell RNA-seq → `tooluniverse-single-cell`
❌ Phylogenetics → `tooluniverse-phylogenetics`
❌ Pure statistical modeling (no imaging) → `tooluniverse-statistical-modeling`

---

## Quick Examples

### Example 1: Colony Morphometry
```python
import pandas as pd

df = pd.read_csv("colonies.csv")
summary = df.groupby("Genotype")["Area"].agg(['mean', 'std', 'count'])
print(summary)
```

### Example 2: Statistical Test
```python
from scipy import stats

control = df[df["Group"] == "Control"]["Measurement"]
treatment = df[df["Group"] == "Treatment"]["Measurement"]
t_stat, p_val = stats.ttest_ind(control, treatment)
print(f"p-value: {p_val:.4f}")
```

### Example 3: Count Cells
```python
from skimage import filters, measure, morphology
import tifffile

image = tifffile.imread("cells.tif")
thresh = filters.threshold_otsu(image)
binary = image > thresh
labels = measure.label(binary)
print(f"Found {labels.max()} cells")
```

---

## Key Technical Features

### scikit-image vs OpenCV
- **scikit-image**: Scientific measurements, regionprops, easier syntax
- **OpenCV**: Faster batch processing, advanced computer vision
- **Both work for**: Thresholding, filtering, morphological operations

See: [references/image_processing.md](references/image_processing.md) "Library Selection Guide"

### Matching R Statistical Functions

Some BixBench questions use R. Python equivalents:
- **R's Dunnett**: `scipy.stats.dunnett()` (scipy ≥ 1.10)
- **R's ns() spline**: `patsy.cr()` with explicit quantile knots
- **R's ANOVA**: `statsmodels.formula.api.ols()` + `sm.stats.anova_lm()`

See: [references/statistical_analysis.md](references/statistical_analysis.md)

---

## Testing

```bash
python test_image_analysis.py
```

All 21 tests pass with exact matches to BixBench expected answers.

---

## File Structure

```
tooluniverse-image-analysis/
├── SKILL.md                    # Main documentation (439 lines, down from 1120)
├── QUICK_START.md              # Quick examples and navigation
├── README.md                   # This file
├── test_image_analysis.py      # Test suite (21 tests)
├── references/                 # Detailed reference guides
│   ├── statistical_analysis.md
│   ├── cell_counting.md
│   ├── segmentation.md
│   ├── fluorescence_analysis.md
│   ├── image_processing.md
│   └── troubleshooting.md
└── scripts/                    # Command-line tools
    ├── segment_cells.py
    ├── measure_fluorescence.py
    └── batch_process.py
```

---

## Common Workflows

1. **Pre-quantified data** → Load CSV → Statistical analysis → Extract answer
2. **Raw images** → Load → Segment → Measure → Export CSV
3. **Fluorescence** → Load multi-channel → Segment → Quantify → Colocalization

See [QUICK_START.md](QUICK_START.md) for complete workflow examples.

---

## Getting Help

1. **Quick start**: [QUICK_START.md](QUICK_START.md)
2. **Main guide**: [SKILL.md](SKILL.md)
3. **Detailed topics**: [references/](references/)
4. **Issues**: [references/troubleshooting.md](references/troubleshooting.md)

All code is copy-paste ready and tested with real microscopy data.
