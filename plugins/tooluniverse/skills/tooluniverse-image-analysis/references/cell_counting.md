# Cell Counting Protocols

Complete guide for counting cells and nuclei in fluorescence and brightfield microscopy images.

---

## Table of Contents

1. [Overview](#overview)
2. [DAPI/Nuclear Staining](#dapinuclear-staining)
3. [Watershed Segmentation](#watershed-segmentation)
4. [Fluorescence Marker Counting](#fluorescence-marker-counting)
5. [Brightfield Cell Counting](#brightfield-cell-counting)
6. [High-Density Counting](#high-density-counting)
7. [Quality Control](#quality-control)

---

## Overview

### When to Use Each Method

| Cell Type | Staining | Density | Best Method |
|-----------|----------|---------|-------------|
| Nuclei | DAPI/Hoechst | Low-Medium | Otsu + watershed |
| Nuclei | DAPI/Hoechst | High | Watershed with distance transform |
| Neurons | NeuN, MAP2 | Any | Threshold + watershed |
| Immune cells | CD markers | Low-Medium | Adaptive threshold |
| Cells (brightfield) | Phase contrast | Low | Adaptive threshold |
| Cells (brightfield) | Phase contrast | High | Edge detection + watershed |
| Touching/clustered | Any | High | CellPose or StarDist (external) |

---

## DAPI/Nuclear Staining

### Basic Nuclear Counting

```python
from skimage import filters, measure, morphology
from skimage.color import rgb2gray
import numpy as np
import pandas as pd

def count_nuclei_basic(image, channel=None, threshold_method='otsu', min_area=50):
    """Count nuclei in DAPI/Hoechst-stained images.

    Args:
        image: numpy array (H, W) or (H, W, C)
        channel: int, channel index for multi-channel images (e.g., 0 for DAPI)
        threshold_method: 'otsu', 'li', 'triangle', or numeric value
        min_area: minimum nucleus area in pixels (default 50)

    Returns: (count, labeled_image, properties_df)
    """
    # Extract channel if needed
    if channel is not None and image.ndim >= 3:
        img = image[..., channel].astype(float)
    elif image.ndim == 3:
        img = rgb2gray(image)
    else:
        img = image.astype(float)

    # Threshold
    if threshold_method == 'otsu':
        thresh = filters.threshold_otsu(img)
    elif threshold_method == 'li':
        thresh = filters.threshold_li(img)
    elif threshold_method == 'triangle':
        thresh = filters.threshold_triangle(img)
    else:
        thresh = threshold_method  # Use numeric value directly

    binary = img > thresh

    # Clean up small objects
    binary = morphology.remove_small_objects(binary, min_size=min_area)

    # Label connected components
    labels = measure.label(binary)

    # Measure properties
    props = measure.regionprops_table(labels, img, properties=[
        'label', 'area', 'mean_intensity', 'perimeter',
        'major_axis_length', 'minor_axis_length', 'eccentricity'
    ])
    props_df = pd.DataFrame(props)

    count = labels.max()

    return count, labels, props_df


# Example usage
import tifffile
image = tifffile.imread("dapi_image.tif")
count, labels, props = count_nuclei_basic(image, channel=0, min_area=50)
print(f"Found {count} nuclei")
print(props.head())
```

---

## Watershed Segmentation

### For Touching/Clustered Nuclei

```python
from scipy import ndimage
from skimage.feature import peak_local_max
from skimage.segmentation import watershed

def count_nuclei_watershed(image, channel=None, min_area=50, min_distance=10):
    """Count nuclei using watershed segmentation (for touching nuclei).

    Args:
        image: numpy array
        channel: int, channel index for multi-channel
        min_area: minimum nucleus area in pixels
        min_distance: minimum distance between nuclei centers (pixels)

    Returns: (count, labeled_image, properties_df)
    """
    # Extract channel
    if channel is not None and image.ndim >= 3:
        img = image[..., channel].astype(float)
    elif image.ndim == 3:
        img = rgb2gray(image)
    else:
        img = image.astype(float)

    # Threshold
    thresh = filters.threshold_otsu(img)
    binary = img > thresh
    binary = morphology.remove_small_objects(binary, min_size=min_area)

    # Distance transform
    distance = ndimage.distance_transform_edt(binary)

    # Find local maxima (nucleus centers)
    coords = peak_local_max(distance, min_distance=min_distance, labels=binary)
    mask = np.zeros(distance.shape, dtype=bool)
    mask[tuple(coords.T)] = True

    # Create markers
    markers = measure.label(mask)

    # Watershed
    labels = watershed(-distance, markers, mask=binary)

    # Measure properties
    props = measure.regionprops_table(labels, img, properties=[
        'label', 'area', 'mean_intensity', 'centroid',
        'major_axis_length', 'minor_axis_length'
    ])
    props_df = pd.DataFrame(props)

    count = labels.max()

    return count, labels, props_df


# Example usage
count, labels, props = count_nuclei_watershed(
    image,
    channel=0,
    min_area=50,
    min_distance=10
)
print(f"Found {count} nuclei (watershed)")
```

---

## Fluorescence Marker Counting

### NeuN, MAP2, or Other Neuronal Markers

```python
def count_marker_positive_cells(image, channel, threshold_percentile=75, min_area=30):
    """Count marker-positive cells (e.g., NeuN, MAP2).

    Uses percentile-based thresholding for better adaptability.

    Args:
        image: numpy array
        channel: int, channel index for marker
        threshold_percentile: percentile for threshold (default 75)
        min_area: minimum cell area

    Returns: (count, labeled_image, properties_df)
    """
    # Extract channel
    img = image[..., channel].astype(float)

    # Percentile-based threshold (more robust than Otsu for sparse markers)
    thresh = np.percentile(img[img > 0], threshold_percentile)
    binary = img > thresh

    # Morphological cleanup
    binary = morphology.remove_small_objects(binary, min_size=min_area)
    binary = morphology.binary_opening(binary, morphology.disk(2))
    binary = morphology.binary_closing(binary, morphology.disk(3))

    # Label
    labels = measure.label(binary)

    # Measure
    props = measure.regionprops_table(labels, img, properties=[
        'label', 'area', 'mean_intensity', 'max_intensity',
        'centroid', 'bbox'
    ])
    props_df = pd.DataFrame(props)

    count = labels.max()

    return count, labels, props_df


# Example usage
neun_count, neun_labels, neun_props = count_marker_positive_cells(
    image,
    channel=1,  # NeuN channel
    threshold_percentile=75,
    min_area=30
)
print(f"NeuN+ cells: {neun_count}")
```

---

## Brightfield Cell Counting

### Phase Contrast or Brightfield Images

```python
def count_cells_brightfield(image, adaptive_block_size=51, min_area=100):
    """Count cells in brightfield/phase contrast images.

    Uses adaptive thresholding to handle uneven illumination.

    Args:
        image: numpy array (grayscale or RGB)
        adaptive_block_size: block size for adaptive threshold (odd number)
        min_area: minimum cell area

    Returns: (count, labeled_image, properties_df)
    """
    # Convert to grayscale
    if image.ndim == 3:
        img = rgb2gray(image)
    else:
        img = image.astype(float)

    # Adaptive threshold
    local_thresh = filters.threshold_local(img, block_size=adaptive_block_size, offset=0.01)
    binary = img < local_thresh  # Note: cells are usually darker than background

    # Clean up
    binary = morphology.remove_small_objects(binary, min_size=min_area)
    binary = morphology.remove_small_holes(binary, area_threshold=min_area)

    # Morphological opening to separate touching cells
    binary = morphology.binary_opening(binary, morphology.disk(3))

    # Label
    labels = measure.label(binary)

    # Measure
    props = measure.regionprops_table(labels, img, properties=[
        'label', 'area', 'perimeter', 'eccentricity',
        'solidity', 'extent'
    ])
    props_df = pd.DataFrame(props)

    count = labels.max()

    return count, labels, props_df


# Example usage
count, labels, props = count_cells_brightfield(
    image,
    adaptive_block_size=51,
    min_area=100
)
print(f"Found {count} cells (brightfield)")
```

---

## High-Density Counting

### Advanced Watershed with Gaussian Filtering

```python
from skimage.filters import gaussian

def count_high_density_cells(image, channel=None, sigma=2.0, min_distance=5, min_area=20):
    """Count cells in high-density images.

    Uses Gaussian smoothing before watershed for better separation.

    Args:
        image: numpy array
        channel: channel index
        sigma: Gaussian smoothing sigma (default 2.0)
        min_distance: minimum distance between cell centers
        min_area: minimum cell area

    Returns: (count, labeled_image, properties_df)
    """
    # Extract channel
    if channel is not None and image.ndim >= 3:
        img = image[..., channel].astype(float)
    else:
        img = image.astype(float)

    # Smooth to reduce noise
    img_smooth = gaussian(img, sigma=sigma)

    # Threshold
    thresh = filters.threshold_li(img_smooth)  # Li works better for high density
    binary = img_smooth > thresh
    binary = morphology.remove_small_objects(binary, min_size=min_area)

    # Distance transform
    distance = ndimage.distance_transform_edt(binary)
    distance_smooth = gaussian(distance, sigma=1.0)  # Smooth distance map

    # Find peaks
    coords = peak_local_max(
        distance_smooth,
        min_distance=min_distance,
        labels=binary,
        exclude_border=False
    )
    mask = np.zeros(distance.shape, dtype=bool)
    mask[tuple(coords.T)] = True

    # Markers and watershed
    markers = measure.label(mask)
    labels = watershed(-distance_smooth, markers, mask=binary)

    # Measure
    props = measure.regionprops_table(labels, img, properties=[
        'label', 'area', 'mean_intensity'
    ])
    props_df = pd.DataFrame(props)

    count = labels.max()

    return count, labels, props_df
```

---

## Quality Control

### Filter by Size and Shape

```python
def filter_by_morphology(props_df, min_area=50, max_area=1000,
                        min_circularity=0.5, max_eccentricity=0.95):
    """Filter detected objects by morphological criteria.

    Args:
        props_df: DataFrame from regionprops_table
        min_area: minimum area (pixels)
        max_area: maximum area (pixels)
        min_circularity: minimum circularity (0-1)
        max_eccentricity: maximum eccentricity (0-1)

    Returns: Filtered DataFrame
    """
    # Calculate circularity if not present
    if 'circularity' not in props_df.columns and 'perimeter' in props_df.columns:
        props_df['circularity'] = 4 * np.pi * props_df['area'] / (props_df['perimeter']**2)

    # Apply filters
    filtered = props_df.copy()

    # Size filters
    filtered = filtered[filtered['area'] >= min_area]
    filtered = filtered[filtered['area'] <= max_area]

    # Shape filters
    if 'circularity' in filtered.columns:
        filtered = filtered[filtered['circularity'] >= min_circularity]

    if 'eccentricity' in filtered.columns:
        filtered = filtered[filtered['eccentricity'] <= max_eccentricity]

    return filtered


# Example usage
count, labels, props = count_nuclei_watershed(image, channel=0)
props_filtered = filter_by_morphology(
    props,
    min_area=50,
    max_area=500,
    min_circularity=0.6
)
print(f"Before filtering: {len(props)} objects")
print(f"After filtering: {len(props_filtered)} nuclei")
```

### Visual Quality Check

```python
import matplotlib.pyplot as plt
from skimage.color import label2rgb

def visualize_segmentation(image, labels, title="Segmentation Result"):
    """Visualize segmentation overlay on original image.

    Args:
        image: Original image (2D grayscale)
        labels: Labeled image from segmentation
        title: Plot title
    """
    # Create overlay
    overlay = label2rgb(labels, image=image, bg_label=0, alpha=0.3)

    # Plot
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    axes[0].imshow(image, cmap='gray')
    axes[0].set_title("Original")
    axes[0].axis('off')

    axes[1].imshow(labels, cmap='nipy_spectral')
    axes[1].set_title(f"Labels (n={labels.max()})")
    axes[1].axis('off')

    axes[2].imshow(overlay)
    axes[2].set_title("Overlay")
    axes[2].axis('off')

    plt.suptitle(title)
    plt.tight_layout()
    plt.show()


# Example usage
count, labels, props = count_nuclei_watershed(image, channel=0)
visualize_segmentation(image[..., 0], labels, title=f"Nuclei: {count} cells")
```

---

## Multi-Sample Analysis

### Batch Counting Across Multiple Images

```python
def batch_count_cells(image_paths, count_function, **kwargs):
    """Count cells in multiple images.

    Args:
        image_paths: List of image file paths
        count_function: Function to use for counting (e.g., count_nuclei_watershed)
        **kwargs: Arguments to pass to count_function

    Returns: DataFrame with results per image
    """
    results = []

    for img_path in image_paths:
        # Load image
        img = tifffile.imread(img_path)

        # Count
        count, labels, props = count_function(img, **kwargs)

        # Store result
        results.append({
            'image': os.path.basename(img_path),
            'count': count,
            'mean_area': props['area'].mean(),
            'std_area': props['area'].std(),
            'mean_intensity': props['mean_intensity'].mean() if 'mean_intensity' in props else np.nan
        })

    return pd.DataFrame(results)


# Example usage
import glob
image_paths = glob.glob("images/*.tif")
results = batch_count_cells(
    image_paths,
    count_nuclei_watershed,
    channel=0,
    min_area=50,
    min_distance=10
)
print(results)
results.to_csv("cell_counts.csv", index=False)
```

---

## Troubleshooting

### Common Issues

**Under-segmentation (cells merged)**:
- Decrease `min_distance` in watershed
- Use stronger Gaussian smoothing before watershed
- Try CellPose or StarDist for very dense images

**Over-segmentation (cells split)**:
- Increase `min_distance` in watershed
- Reduce Gaussian smoothing
- Use more aggressive morphological closing

**Background noise detected as cells**:
- Increase `min_area` threshold
- Use more conservative threshold method (Li instead of Otsu)
- Apply morphological opening

**Dim cells not detected**:
- Use Li or Triangle threshold instead of Otsu
- Reduce threshold manually (e.g., percentile-based)
- Enhance contrast before segmentation

**Uneven illumination**:
- Use adaptive thresholding (`filters.threshold_local()`)
- Apply background subtraction
- Use rolling ball background subtraction (from scikit-image)

---

## Parameter Selection Guide

### Starting Parameters by Image Type

| Image Type | Threshold | min_area | min_distance | Notes |
|------------|-----------|----------|--------------|-------|
| **DAPI (confocal)** | otsu | 50 | 10 | Well-separated nuclei |
| **DAPI (widefield)** | li | 50 | 8 | More variable intensity |
| **DAPI (high-density)** | li | 30 | 5 | Touching nuclei |
| **NeuN (sparse)** | percentile 75 | 40 | 15 | Sparse marker |
| **Phase contrast** | adaptive | 100 | 15 | Uneven illumination |
| **Brightfield** | adaptive | 150 | 20 | Large cells, halo artifacts |

Adjust based on your specific images!
