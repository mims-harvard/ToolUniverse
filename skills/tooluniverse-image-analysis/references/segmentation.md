# Colony and Object Segmentation

Complete guide for segmenting and measuring bacterial colonies, biofilms, and other large objects in microscopy images.

---

## Table of Contents

1. [Colony Morphometry Basics](#colony-morphometry-basics)
2. [Threshold Methods](#threshold-methods)
3. [Morphological Operations](#morphological-operations)
4. [Measurement and Analysis](#measurement-and-analysis)
5. [Swarming Assay Analysis](#swarming-assay-analysis)
6. [Time-Lapse Analysis](#time-lapse-analysis)

---

## Colony Morphometry Basics

### Why Colony Morphometry?

Colony morphometry measures:
- **Area**: Colony size (pixels or calibrated units)
- **Circularity**: Shape roundness (4π × area / perimeter²)
- **Roundness**: Alternative shape metric (4 × area / π × major_axis²)
- **Solidity**: Convexity (area / convex_hull_area)
- **Eccentricity**: Elongation (0 = circle, 1 = line)

Used in:
- Bacterial swarming assays
- Biofilm formation studies
- Fungal colony growth
- Cell aggregate analysis

---

## Threshold Methods

### Otsu Threshold (Most Common)

```python
from skimage import filters, measure, morphology
import numpy as np
import pandas as pd

def segment_colonies_otsu(image, min_area=100):
    """Segment colonies using Otsu's method.

    Best for: Well-defined colonies with clear contrast to background.

    Args:
        image: numpy array (grayscale or RGB)
        min_area: minimum colony area in pixels

    Returns: (binary_mask, labeled_image, properties_df)
    """
    # Convert to grayscale if needed
    if image.ndim == 3:
        from skimage.color import rgb2gray
        img = rgb2gray(image)
    else:
        img = image.astype(float)

    # Otsu threshold
    thresh = filters.threshold_otsu(img)
    binary = img > thresh  # or img < thresh if colonies are dark

    # Clean up small objects
    binary = morphology.remove_small_objects(binary, min_size=min_area)
    binary = morphology.binary_fill_holes(binary)

    # Label connected components
    labels = measure.label(binary)

    # Measure properties
    props = measure.regionprops_table(labels, properties=[
        'label', 'area', 'perimeter', 'eccentricity',
        'major_axis_length', 'minor_axis_length', 'solidity'
    ])
    props_df = pd.DataFrame(props)

    # Calculate circularity
    props_df['circularity'] = 4 * np.pi * props_df['area'] / (props_df['perimeter']**2)

    # Calculate roundness
    props_df['roundness'] = 4 * props_df['area'] / (np.pi * props_df['major_axis_length']**2)

    return binary, labels, props_df


# Example usage
import tifffile
image = tifffile.imread("swarming_plate.tif")
binary, labels, props = segment_colonies_otsu(image, min_area=500)
print(f"Found {labels.max()} colonies")
print(props.head())
```

### Li Threshold (More Sensitive)

```python
def segment_colonies_li(image, min_area=100):
    """Segment colonies using Li's method.

    Best for: Low-contrast images, faint colonies.

    Args:
        image: numpy array
        min_area: minimum colony area

    Returns: (binary_mask, labeled_image, properties_df)
    """
    if image.ndim == 3:
        from skimage.color import rgb2gray
        img = rgb2gray(image)
    else:
        img = image.astype(float)

    # Li threshold (more sensitive than Otsu)
    thresh = filters.threshold_li(img)
    binary = img > thresh

    # Cleanup
    binary = morphology.remove_small_objects(binary, min_size=min_area)
    binary = morphology.binary_fill_holes(binary)

    # Label and measure
    labels = measure.label(binary)
    props = measure.regionprops_table(labels, properties=[
        'label', 'area', 'perimeter', 'eccentricity',
        'major_axis_length', 'minor_axis_length', 'solidity'
    ])
    props_df = pd.DataFrame(props)

    # Add shape metrics
    props_df['circularity'] = 4 * np.pi * props_df['area'] / (props_df['perimeter']**2)
    props_df['roundness'] = 4 * props_df['area'] / (np.pi * props_df['major_axis_length']**2)

    return binary, labels, props_df
```

### Adaptive Threshold (Uneven Illumination)

```python
def segment_colonies_adaptive(image, block_size=51, offset=0.01, min_area=100):
    """Segment colonies with adaptive thresholding.

    Best for: Uneven illumination, gradient backgrounds.

    Args:
        image: numpy array
        block_size: size of local region (odd number)
        offset: threshold offset
        min_area: minimum colony area

    Returns: (binary_mask, labeled_image, properties_df)
    """
    if image.ndim == 3:
        from skimage.color import rgb2gray
        img = rgb2gray(image)
    else:
        img = image.astype(float)

    # Adaptive threshold
    local_thresh = filters.threshold_local(img, block_size=block_size, offset=offset)
    binary = img > local_thresh

    # Cleanup
    binary = morphology.remove_small_objects(binary, min_size=min_area)
    binary = morphology.binary_fill_holes(binary)

    # Label and measure
    labels = measure.label(binary)
    props = measure.regionprops_table(labels, properties=[
        'label', 'area', 'perimeter', 'eccentricity',
        'major_axis_length', 'minor_axis_length', 'solidity'
    ])
    props_df = pd.DataFrame(props)

    # Shape metrics
    props_df['circularity'] = 4 * np.pi * props_df['area'] / (props_df['perimeter']**2)
    props_df['roundness'] = 4 * props_df['area'] / (np.pi * props_df['major_axis_length']**2)

    return binary, labels, props_df
```

---

## Morphological Operations

### Fill Holes (Interior Gaps)

```python
from skimage.morphology import binary_fill_holes

# Fill all holes
binary_filled = binary_fill_holes(binary)

# Fill only small holes
from skimage.morphology import remove_small_holes
binary_filled = remove_small_holes(binary, area_threshold=200)
```

### Remove Small Objects

```python
from skimage.morphology import remove_small_objects

# Remove objects smaller than threshold
binary_clean = remove_small_objects(binary, min_size=500)
```

### Opening (Remove Protrusions)

```python
from skimage.morphology import binary_opening, disk

# Remove small protrusions and thin connections
binary_opened = binary_opening(binary, disk(3))
```

### Closing (Fill Gaps)

```python
from skimage.morphology import binary_closing, disk

# Close small gaps between objects
binary_closed = binary_closing(binary, disk(5))
```

### Complete Cleanup Pipeline

```python
def morphological_cleanup(binary, min_area=500, opening_radius=3, closing_radius=5):
    """Apply morphological operations to clean up binary mask.

    Args:
        binary: binary mask
        min_area: minimum object area to keep
        opening_radius: radius for opening operation
        closing_radius: radius for closing operation

    Returns: Cleaned binary mask
    """
    # Remove small objects
    cleaned = morphology.remove_small_objects(binary, min_size=min_area)

    # Opening to remove protrusions
    if opening_radius > 0:
        cleaned = morphology.binary_opening(cleaned, morphology.disk(opening_radius))

    # Closing to fill gaps
    if closing_radius > 0:
        cleaned = morphology.binary_closing(cleaned, morphology.disk(closing_radius))

    # Fill holes
    cleaned = morphology.binary_fill_holes(cleaned)

    return cleaned
```

---

## Measurement and Analysis

### Complete Colony Measurement

```python
def measure_colonies(image, threshold_method='otsu', min_area=500):
    """Segment and measure colonies from image.

    Returns: DataFrame with Area, Circularity, Roundness, Perimeter per colony
    """
    # Convert to grayscale
    if image.ndim == 3:
        from skimage.color import rgb2gray
        gray = rgb2gray(image)
    else:
        gray = image.astype(float)

    # Threshold
    if threshold_method == 'otsu':
        thresh = filters.threshold_otsu(gray)
    elif threshold_method == 'li':
        thresh = filters.threshold_li(gray)
    elif threshold_method == 'triangle':
        thresh = filters.threshold_triangle(gray)
    else:
        thresh = threshold_method  # numeric value

    binary = gray > thresh

    # Clean up
    binary = morphology.remove_small_objects(binary, min_size=min_area)
    binary = morphology.binary_fill_holes(binary)

    # Label and measure
    labels = measure.label(binary)
    props = measure.regionprops_table(labels, properties=[
        'area', 'perimeter', 'eccentricity', 'solidity',
        'major_axis_length', 'minor_axis_length'
    ])

    results = pd.DataFrame(props)

    # Calculate shape metrics
    results['circularity'] = 4 * np.pi * results['area'] / (results['perimeter']**2)
    results['roundness'] = 4 * results['area'] / (np.pi * results['major_axis_length']**2)

    # Rename to match ImageJ/CellProfiler conventions
    results = results.rename(columns={
        'area': 'Area',
        'perimeter': 'Perimeter',
        'circularity': 'Circularity',
        'roundness': 'Round',
        'eccentricity': 'Eccentricity',
        'solidity': 'Solidity'
    })

    return results
```

### Calibrated Measurements

```python
def measure_colonies_calibrated(image, pixel_size_um, threshold_method='otsu', min_area_um2=0.1):
    """Measure colonies with calibrated units.

    Args:
        image: numpy array
        pixel_size_um: size of one pixel in micrometers (e.g., 0.65 for 0.65 µm/pixel)
        threshold_method: 'otsu', 'li', or numeric
        min_area_um2: minimum area in mm² (1 mm² = 1,000,000 µm²)

    Returns: DataFrame with calibrated measurements
    """
    # Convert min_area to pixels
    min_area_pixels = int(min_area_um2 * 1e6 / (pixel_size_um**2))

    # Segment and measure in pixels
    results = measure_colonies(image, threshold_method, min_area_pixels)

    # Convert to calibrated units
    results['Area_um2'] = results['Area'] * (pixel_size_um**2)
    results['Area_mm2'] = results['Area_um2'] / 1e6
    results['Perimeter_um'] = results['Perimeter'] * pixel_size_um

    # Circularity and roundness are dimensionless (no conversion needed)

    return results
```

---

## Swarming Assay Analysis

### Complete Swarming Assay Workflow

```python
def analyze_swarming_plate(image_path, genotype, replicate,
                          pixel_size_um=1.0, min_area_mm2=0.5):
    """Complete analysis of bacterial swarming plate.

    Args:
        image_path: path to image file
        genotype: genotype label
        replicate: replicate number
        pixel_size_um: pixel size in micrometers
        min_area_mm2: minimum colony area in mm²

    Returns: DataFrame with measurements for this plate
    """
    import tifffile
    import os

    # Load image
    image = tifffile.imread(image_path)

    # Measure colonies
    results = measure_colonies_calibrated(
        image,
        pixel_size_um=pixel_size_um,
        threshold_method='otsu',
        min_area_um2=min_area_mm2 * 1e6  # Convert mm² to µm²
    )

    # Add metadata
    results['Genotype'] = genotype
    results['Replicate'] = replicate
    results['Image'] = os.path.basename(image_path)

    return results


# Example: Batch process multiple plates
def batch_analyze_swarming(image_info_df, pixel_size_um=1.0):
    """Analyze multiple swarming plates.

    Args:
        image_info_df: DataFrame with columns: 'image_path', 'genotype', 'replicate'
        pixel_size_um: pixel size

    Returns: Combined DataFrame with all measurements
    """
    all_results = []

    for idx, row in image_info_df.iterrows():
        results = analyze_swarming_plate(
            row['image_path'],
            row['genotype'],
            row['replicate'],
            pixel_size_um=pixel_size_um
        )
        all_results.append(results)

    combined = pd.concat(all_results, ignore_index=True)
    return combined
```

### Colony Morphometry Statistics (BixBench Pattern)

```python
def colony_morphometry_analysis(df, genotype_col='Genotype',
                               area_col='Area', circ_col='Circularity'):
    """Full colony morphometry analysis for swarming assays.

    Reproduces BixBench bix-18 analysis pattern.

    Args:
        df: DataFrame with colony measurements
        genotype_col: column with genotype labels
        area_col: column with area measurements
        circ_col: column with circularity measurements

    Returns: dict with per-genotype summaries and max-area genotype info
    """
    # Group statistics for area
    area_summary = df.groupby(genotype_col)[area_col].agg(
        Mean='mean',
        SD='std',
        Median='median',
        Min='min',
        Max='max',
        N='count'
    ).reset_index()
    area_summary['SEM'] = area_summary['SD'] / np.sqrt(area_summary['N'])

    # Group statistics for circularity
    circ_summary = df.groupby(genotype_col)[circ_col].agg(
        Mean='mean',
        SD='std',
        Median='median',
        N='count'
    ).reset_index()
    circ_summary['SEM'] = circ_summary['SD'] / np.sqrt(circ_summary['N'])

    # Merge area and circularity summaries
    merged = area_summary.merge(
        circ_summary, on=genotype_col, suffixes=('_Area', '_Circ')
    )

    # Find genotype with largest mean area
    max_area_idx = merged['Mean_Area'].idxmax()
    max_area_genotype = merged.loc[max_area_idx, genotype_col]
    max_area_circularity = merged.loc[max_area_idx, 'Mean_Circ']

    return {
        'area_summary': area_summary,
        'circ_summary': circ_summary,
        'merged_summary': merged,
        'max_area_genotype': max_area_genotype,
        'max_area_circularity': max_area_circularity,
    }


# Example usage (BixBench bix-18 pattern)
df = pd.read_csv("Swarm_1.csv")
result = colony_morphometry_analysis(df, 'Genotype', 'Area', 'Circularity')
print(f"Genotype with largest area: {result['max_area_genotype']}")
print(f"Mean circularity: {result['max_area_circularity']:.4f}")
```

---

## Time-Lapse Analysis

### Track Colony Growth Over Time

```python
def analyze_timelapse(image_paths, timepoints_hours):
    """Analyze colony growth from time-lapse images.

    Args:
        image_paths: list of image file paths (sorted by time)
        timepoints_hours: list of timepoint values in hours

    Returns: DataFrame with area vs time for each colony
    """
    import tifffile

    growth_data = []

    for i, (img_path, time_hr) in enumerate(zip(image_paths, timepoints_hours)):
        # Load and measure
        img = tifffile.imread(img_path)
        results = measure_colonies(img, threshold_method='otsu', min_area=100)

        # Add time information
        results['timepoint'] = i
        results['time_hours'] = time_hr

        growth_data.append(results)

    # Combine all timepoints
    combined = pd.concat(growth_data, ignore_index=True)

    return combined


# Example: Plot growth curves
import matplotlib.pyplot as plt

def plot_growth_curves(growth_df, colony_labels=None):
    """Plot colony area vs time.

    Args:
        growth_df: DataFrame from analyze_timelapse
        colony_labels: Optional list of colony IDs to plot
    """
    if colony_labels is None:
        # Plot mean area over time
        summary = growth_df.groupby('time_hours')['Area'].agg(['mean', 'std'])
        plt.errorbar(summary.index, summary['mean'], yerr=summary['std'],
                    marker='o', capsize=5)
        plt.xlabel('Time (hours)')
        plt.ylabel('Mean Colony Area (pixels)')
        plt.title('Colony Growth Over Time')
    else:
        # Plot individual colonies
        for colony_id in colony_labels:
            colony_data = growth_df[growth_df['label'] == colony_id]
            plt.plot(colony_data['time_hours'], colony_data['Area'],
                    marker='o', label=f'Colony {colony_id}')
        plt.xlabel('Time (hours)')
        plt.ylabel('Colony Area (pixels)')
        plt.title('Individual Colony Growth')
        plt.legend()

    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
```

---

## Troubleshooting

### Common Issues

**Multiple colonies merged into one**:
- Use watershed segmentation (see cell_counting.md)
- Increase erosion before labeling
- Try more conservative threshold (Li instead of Otsu)

**Background detected as colony**:
- Increase `min_area` threshold
- Apply morphological opening
- Use adaptive threshold for uneven backgrounds

**Colony edges jagged**:
- Apply Gaussian smoothing before thresholding
- Use morphological closing
- Increase binary dilation

**Small colonies missed**:
- Use Li or Triangle threshold (more sensitive)
- Reduce `min_area` threshold
- Enhance contrast before segmentation

**Uneven illumination affects segmentation**:
- Use adaptive thresholding
- Apply background subtraction first
- Use rolling ball background correction

---

## Threshold Method Selection Guide

| Image Type | Best Method | Notes |
|------------|-------------|-------|
| **High contrast, even illumination** | Otsu | Fast, reliable |
| **Low contrast** | Li | More sensitive |
| **Gradient background** | Adaptive | Block size = ~1/10 image width |
| **Dark background** | Otsu or Li | Colony brighter than background |
| **Bright background** | Otsu or Li | Invert binary result |
| **Multiple colonies, well-separated** | Otsu + cleanup | Simple and effective |
| **Touching colonies** | Watershed | See cell_counting.md |

---

## Parameter Recommendations

### Bacterial Swarming Plates

```python
# Typical parameters for Petri dish images (100mm plates)
params = {
    'threshold_method': 'otsu',
    'min_area': 500,  # pixels (adjust based on magnification)
    'opening_radius': 3,
    'closing_radius': 5,
}
```

### Biofilm Analysis

```python
# Biofilms often have irregular edges
params = {
    'threshold_method': 'li',  # More sensitive
    'min_area': 1000,
    'opening_radius': 5,  # Stronger cleanup
    'closing_radius': 8,
}
```

### Fungal Colonies

```python
# Fungi can have very irregular shapes
params = {
    'threshold_method': 'adaptive',
    'block_size': 51,
    'min_area': 2000,
    'opening_radius': 0,  # Preserve edges
    'closing_radius': 10,
}
```
