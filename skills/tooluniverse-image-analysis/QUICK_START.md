# Quick Start: Microscopy Image Analysis

Get started with microscopy image analysis in minutes. This guide shows common workflows and points you to detailed references.

---

## Installation

```bash
pip install pandas numpy scipy statsmodels patsy scikit-image tifffile
```

---

## Quick Decision Guide

**Have pre-quantified data (CSV/TSV)?** → Jump to [Use Case 1](#use-case-1-analyzing-pre-quantified-data-csv)

**Have raw images to process?** → Jump to [Use Case 4](#use-case-4-processing-raw-images)

**Need statistical analysis only?** → See [references/statistical_analysis.md](references/statistical_analysis.md)

---

## Use Case 1: Analyzing Pre-Quantified Data (CSV)

Most BixBench imaging questions provide CSV files with measurements already done by ImageJ or CellProfiler.

### Colony Morphometry (bix-18 pattern)

```python
import pandas as pd
import numpy as np

# Load ImageJ measurements
df = pd.read_csv("Swarm_1.csv")
# Columns: Genotype, Area, Circularity, Round

# Summary statistics by genotype
summary = df.groupby("Genotype").agg(
    Mean_Area=("Area", "mean"),
    Mean_Circ=("Circularity", "mean"),
    SD_Circ=("Circularity", "std"),
    N=("Circularity", "count"),
).reset_index()
summary["SEM_Circ"] = summary["SD_Circ"] / np.sqrt(summary["N"])

# Find genotype with largest area
max_area_row = summary.loc[summary["Mean_Area"].idxmax()]
print(f"Genotype with largest area: {max_area_row['Genotype']}")
print(f"Mean circularity: {max_area_row['Mean_Circ']:.3f}")
```

**For more**: See [references/statistical_analysis.md](references/statistical_analysis.md) "Descriptive Statistics"

---

## Use Case 2: Statistical Comparisons

### Two-Group Comparison (Cohen's d)

```python
from scipy import stats
import numpy as np

# Load data
df = pd.read_csv("NeuN_quantification.csv")
kd = df[df["Condition"] == "KD"]["NeuN_count"]
ctrl = df[df["Condition"] == "CTRL"]["NeuN_count"]

# Cohen's d with pooled SD
n_kd, n_ctrl = len(kd), len(ctrl)
sd_pooled = np.sqrt(((n_kd-1)*kd.std()**2 + (n_ctrl-1)*ctrl.std()**2) / (n_kd+n_ctrl-2))
cohens_d = (kd.mean() - ctrl.mean()) / sd_pooled
print(f"Cohen's d: {cohens_d:.3f}")
```

### Multiple Group Comparison (Dunnett's Test)

```python
from scipy import stats

# Compare multiple treatments to control
control_data = df[df["Group"] == "Control"]["Measurement"]
treatment_groups = ["T1", "T2", "T3"]
treatment_data = [df[df["Group"] == g]["Measurement"] for g in treatment_groups]

# Dunnett's test (requires scipy >= 1.10)
result = stats.dunnett(*treatment_data, control=control_data, alternative='two-sided')

for i, group in enumerate(treatment_groups):
    significant = "✓" if result.pvalue[i] < 0.05 else "✗"
    print(f"{group} vs Control: p={result.pvalue[i]:.4f} {significant}")
```

**For more**: See [references/statistical_analysis.md](references/statistical_analysis.md)

---

## Use Case 3: Regression Modeling

### Polynomial and Spline Regression

```python
import pandas as pd
import numpy as np
import statsmodels.api as sm
from patsy import dmatrix

df = pd.read_csv("dose_response.csv")
x = df["Frequency"]
y = df["Area"]

# Fit polynomial model
X_poly = np.column_stack([x**i for i in range(1, 3)])  # Quadratic
X = sm.add_constant(X_poly)
model = sm.OLS(y, X).fit()
print(f"R-squared: {model.rsquared:.4f}")

# Find peak
b1, b2 = model.params[1], model.params[2]
peak_x = -b1 / (2 * b2)
print(f"Peak at x={peak_x:.3f}")
```

**For more**: See [references/statistical_analysis.md](references/statistical_analysis.md) "Regression Modeling"

---

## Use Case 4: Processing Raw Images

### Option A: Using Command-Line Scripts (Easiest)

```bash
# Count cells in images
python scripts/segment_cells.py cells.tif --channel 0 --min-area 50

# Batch process folder
python scripts/batch_process.py images/ results.csv --analysis cell_count

# Measure fluorescence
python scripts/measure_fluorescence.py image.tif mask.tif --channels DAPI GFP RFP
```

### Option B: Python Code

```python
import tifffile
from skimage import filters, measure, morphology

# Load image
image = tifffile.imread("cells.tif")

# Segment nuclei (DAPI channel)
dapi = image[:, :, 0]
thresh = filters.threshold_otsu(dapi)
binary = dapi > thresh
binary = morphology.remove_small_objects(binary, min_size=50)
binary = morphology.binary_fill_holes(binary)

# Label and count
labels = measure.label(binary)
count = labels.max()
print(f"Found {count} nuclei")

# Measure properties
props = measure.regionprops_table(labels, dapi, properties=[
    'area', 'mean_intensity', 'centroid'
])
import pandas as pd
df = pd.DataFrame(props)
print(df.head())
```

**For more**:
- Cell counting: [references/cell_counting.md](references/cell_counting.md)
- Colony segmentation: [references/segmentation.md](references/segmentation.md)
- Fluorescence: [references/fluorescence_analysis.md](references/fluorescence_analysis.md)

---

## Use Case 5: Fluorescence Colocalization

```python
import tifffile
from scipy import stats
from skimage.filters import threshold_otsu

# Load multi-channel image
image = tifffile.imread("colocalization.tif")
gfp = image[:, :, 1]
rfp = image[:, :, 2]

# Pearson correlation
mask = labels > 0  # Optional: restrict to cells
r, p = stats.pearsonr(gfp[mask].flatten(), rfp[mask].flatten())
print(f"Pearson r = {r:.3f}, p = {p:.2e}")

# Manders coefficients
def manders_coefficients(ch1, ch2, thresh1, thresh2):
    mask1 = ch1 > thresh1
    mask2 = ch2 > thresh2
    overlap = mask1 & mask2
    M1 = ch1[overlap].sum() / ch1[mask1].sum() if ch1[mask1].sum() > 0 else 0
    M2 = ch2[overlap].sum() / ch2[mask2].sum() if ch2[mask2].sum() > 0 else 0
    return M1, M2

thresh_gfp = threshold_otsu(gfp)
thresh_rfp = threshold_otsu(rfp)
M1, M2 = manders_coefficients(gfp, rfp, thresh_gfp, thresh_rfp)
print(f"Manders: M1={M1:.3f}, M2={M2:.3f}")
```

**For more**: [references/fluorescence_analysis.md](references/fluorescence_analysis.md) "Colocalization"

---

## Navigation Guide

### I want to...

**Count cells** → [references/cell_counting.md](references/cell_counting.md)
- DAPI nuclei counting
- Watershed for touching cells
- High-density cell counting

**Segment colonies** → [references/segmentation.md](references/segmentation.md)
- Bacterial swarming assays
- Colony morphometry (area, circularity)
- Threshold method selection

**Measure fluorescence** → [references/fluorescence_analysis.md](references/fluorescence_analysis.md)
- Multi-channel quantification
- Colocalization (Pearson, Manders)
- Background correction

**Run statistical tests** → [references/statistical_analysis.md](references/statistical_analysis.md)
- t-tests, ANOVA, Dunnett's
- Cohen's d, power analysis
- Regression models

**Load/preprocess images** → [references/image_processing.md](references/image_processing.md)
- Format handling (TIFF, PNG, multi-channel)
- scikit-image vs OpenCV
- Batch processing

**Troubleshoot issues** → [references/troubleshooting.md](references/troubleshooting.md)
- Segmentation problems
- Statistical issues
- Performance tips

---

## Common Workflows

### Workflow 1: Colony Analysis (Pre-quantified)

```
1. Load CSV with Area, Circularity measurements
2. Group by Genotype/Condition
3. Calculate statistics (mean, SEM)
4. Run statistical tests (t-test, ANOVA, Dunnett's)
5. Extract specific answers (e.g., mean circularity of max-area genotype)
```

See: [SKILL.md](SKILL.md) "Quantitative Data Analysis Workflow"

### Workflow 2: Cell Counting (Raw Images)

```
1. Load TIFF image
2. Extract DAPI channel
3. Threshold (Otsu or Li)
4. Watershed segmentation (if touching)
5. Label and count
6. Measure properties (area, intensity)
```

See: [references/cell_counting.md](references/cell_counting.md) "Watershed Segmentation"

### Workflow 3: Fluorescence Quantification

```
1. Load multi-channel image
2. Segment nuclei from DAPI channel
3. Quantify all channels per object
4. Calculate ratios (e.g., GFP/RFP)
5. Export to CSV
```

See: [references/fluorescence_analysis.md](references/fluorescence_analysis.md) "Multi-Channel Analysis"

---

## Example Scripts

Ready-to-use command-line tools in `scripts/`:

```bash
# Segment and count cells
python scripts/segment_cells.py image.tif --channel 0 --method watershed

# Batch process folder
python scripts/batch_process.py images/ output.csv --analysis cell_count

# Measure fluorescence
python scripts/measure_fluorescence.py image.tif mask.tif --channels DAPI GFP RFP
```

---

## Getting Help

1. **Start with decision tree** in [SKILL.md](SKILL.md)
2. **Check relevant reference** for detailed protocol
3. **Use example scripts** as templates
4. **See troubleshooting** for common issues

All code is copy-paste ready and tested with real microscopy data.
