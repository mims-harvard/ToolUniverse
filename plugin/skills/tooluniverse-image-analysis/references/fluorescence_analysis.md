# Fluorescence Analysis and Quantification

Complete guide for fluorescence intensity measurement and colocalization analysis.

---

## Table of Contents

1. [Intensity Quantification](#intensity-quantification)
2. [Multi-Channel Analysis](#multi-channel-analysis)
3. [Colocalization](#colocalization)
4. [Background Correction](#background-correction)

---

## Intensity Quantification

### Single-Channel Intensity Measurement

```python
from skimage import measure
import numpy as np
import pandas as pd

def quantify_fluorescence(image, labels, channel=None):
    """Quantify fluorescence intensity per segmented object.

    Args:
        image: Image array (2D grayscale or 3D multi-channel)
        labels: Labeled segmentation mask
        channel: Channel index for multi-channel images

    Returns: DataFrame with per-object intensity measurements
    """
    # Extract channel if needed
    if channel is not None and image.ndim >= 3:
        img = image[..., channel]
    else:
        img = image

    # Measure properties
    props = measure.regionprops_table(labels, img, properties=[
        'label', 'area', 'mean_intensity', 'max_intensity', 'min_intensity'
    ])

    results = pd.DataFrame(props)

    # Calculate integrated intensity (total fluorescence)
    results['integrated_intensity'] = results['area'] * results['mean_intensity']

    return results


# Example usage
import tifffile
image = tifffile.imread("fluorescence.tif")
labels = tifffile.imread("segmentation_mask.tif")

intensity_df = quantify_fluorescence(image, labels, channel=0)
print(intensity_df.head())
```

---

## Multi-Channel Analysis

### Quantify All Channels

```python
def quantify_multichannel(image, labels, channel_names=None):
    """Quantify fluorescence across all channels.

    Args:
        image: Multi-channel image (H, W, C)
        labels: Labeled segmentation mask
        channel_names: List of channel names (e.g., ['DAPI', 'GFP', 'RFP'])

    Returns: DataFrame with per-object, per-channel measurements
    """
    if image.ndim == 2:
        # Single channel
        return quantify_fluorescence(image, labels)

    n_channels = image.shape[-1]

    if channel_names is None:
        channel_names = [f'channel_{i}' for i in range(n_channels)]

    # Measure first channel with area
    ch0_props = measure.regionprops_table(labels, image[..., 0], properties=[
        'label', 'area', 'mean_intensity', 'max_intensity'
    ])
    result = pd.DataFrame(ch0_props)
    result = result.rename(columns={
        'mean_intensity': f'mean_{channel_names[0]}',
        'max_intensity': f'max_{channel_names[0]}'
    })

    # Add integrated intensity
    result[f'integrated_{channel_names[0]}'] = result['area'] * result[f'mean_{channel_names[0]}']

    # Measure remaining channels
    for i in range(1, n_channels):
        ch_props = measure.regionprops_table(labels, image[..., i], properties=[
            'label', 'mean_intensity', 'max_intensity'
        ])
        ch_df = pd.DataFrame(ch_props)
        ch_df = ch_df.rename(columns={
            'mean_intensity': f'mean_{channel_names[i]}',
            'max_intensity': f'max_{channel_names[i]}'
        })

        # Add integrated intensity
        ch_df[f'integrated_{channel_names[i]}'] = result['area'] * ch_df[f'mean_{channel_names[i]}']

        # Merge
        result = result.merge(ch_df, on='label')

    return result


# Example usage
image = tifffile.imread("multi_channel.tif")  # Shape: (H, W, 3)
labels = tifffile.imread("nuclei_mask.tif")

results = quantify_multichannel(image, labels, channel_names=['DAPI', 'GFP', 'RFP'])
print(results.head())
```

### Calculate Channel Ratios

```python
def calculate_ratios(intensity_df, numerator_channel, denominator_channel):
    """Calculate ratio of two channels.

    Args:
        intensity_df: DataFrame from quantify_multichannel
        numerator_channel: Numerator channel name
        denominator_channel: Denominator channel name

    Returns: DataFrame with ratio column added
    """
    result = intensity_df.copy()

    # Mean intensity ratio
    num_col = f'mean_{numerator_channel}'
    den_col = f'mean_{denominator_channel}'
    result[f'ratio_{numerator_channel}_{denominator_channel}'] = (
        result[num_col] / result[den_col]
    )

    return result


# Example: GFP/RFP ratio
results = calculate_ratios(results, 'GFP', 'RFP')
print(results[['label', 'ratio_GFP_RFP']].head())
```

---

## Colocalization

### Pearson Correlation Coefficient

```python
from scipy import stats

def pearson_colocalization(channel1, channel2, mask=None):
    """Calculate Pearson correlation coefficient for colocalization.

    Args:
        channel1, channel2: 2D arrays of fluorescence intensities
        mask: Optional binary mask to restrict analysis region

    Returns: (pearson_r, p_value)

    Interpretation:
    - r close to 1: Strong positive correlation (high colocalization)
    - r close to 0: No correlation
    - r close to -1: Strong negative correlation (anti-colocalization)
    """
    if mask is not None:
        c1 = channel1[mask].flatten()
        c2 = channel2[mask].flatten()
    else:
        c1 = channel1.flatten()
        c2 = channel2.flatten()

    return stats.pearsonr(c1, c2)


# Example usage
image = tifffile.imread("colocalization.tif")
ch1 = image[..., 0]  # GFP
ch2 = image[..., 1]  # RFP

# Optional: use cell mask to restrict to cells
mask = labels > 0

r, p = pearson_colocalization(ch1, ch2, mask=mask)
print(f"Pearson r = {r:.3f}, p = {p:.2e}")
```

### Manders Overlap Coefficients

```python
def manders_coefficients(channel1, channel2, threshold1=0, threshold2=0):
    """Calculate Manders overlap coefficients M1 and M2.

    M1: fraction of channel1 intensity overlapping with channel2
    M2: fraction of channel2 intensity overlapping with channel1

    Args:
        channel1, channel2: 2D fluorescence images
        threshold1, threshold2: Intensity thresholds (can use Otsu)

    Returns: (M1, M2)

    Interpretation:
    - M1/M2 = 1.0: Perfect overlap
    - M1/M2 = 0.0: No overlap
    - M1 ≠ M2: Asymmetric colocalization
    """
    mask1 = channel1 > threshold1
    mask2 = channel2 > threshold2

    overlap = mask1 & mask2

    M1 = channel1[overlap].sum() / channel1[mask1].sum() if channel1[mask1].sum() > 0 else 0
    M2 = channel2[overlap].sum() / channel2[mask2].sum() if channel2[mask2].sum() > 0 else 0

    return M1, M2


# Example with automatic thresholding
from skimage.filters import threshold_otsu

ch1 = image[..., 0]
ch2 = image[..., 1]

thresh1 = threshold_otsu(ch1)
thresh2 = threshold_otsu(ch2)

M1, M2 = manders_coefficients(ch1, ch2, thresh1, thresh2)
print(f"Manders M1 = {M1:.3f}, M2 = {M2:.3f}")
```

### Object-Based Colocalization

```python
def object_colocalization(labels, channel1, channel2, overlap_threshold=0.5):
    """Determine which objects are positive for both channels.

    Args:
        labels: Labeled segmentation
        channel1, channel2: Fluorescence images
        overlap_threshold: Manders coefficient threshold for "positive"

    Returns: DataFrame with per-object colocalization metrics
    """
    results = []

    for region in measure.regionprops(labels, intensity_image=channel1):
        obj_id = region.label
        mask = labels == obj_id

        # Extract region from both channels
        c1_roi = channel1[mask]
        c2_roi = channel2[mask]

        # Mean intensities
        mean_c1 = c1_roi.mean()
        mean_c2 = c2_roi.mean()

        # Pearson correlation
        if len(c1_roi) > 1:
            r, p = stats.pearsonr(c1_roi, c2_roi)
        else:
            r, p = np.nan, np.nan

        # Manders (within object)
        thresh_c1 = threshold_otsu(c1_roi) if c1_roi.max() > c1_roi.min() else c1_roi.mean()
        thresh_c2 = threshold_otsu(c2_roi) if c2_roi.max() > c2_roi.min() else c2_roi.mean()
        M1, M2 = manders_coefficients(
            c1_roi.reshape(mask[mask].shape),
            c2_roi.reshape(mask[mask].shape),
            thresh_c1, thresh_c2
        )

        # Classify
        both_positive = (M1 > overlap_threshold) and (M2 > overlap_threshold)

        results.append({
            'object_id': obj_id,
            'mean_ch1': mean_c1,
            'mean_ch2': mean_c2,
            'pearson_r': r,
            'manders_M1': M1,
            'manders_M2': M2,
            'colocalized': both_positive
        })

    return pd.DataFrame(results)


# Example usage
coloc_df = object_colocalization(labels, ch1, ch2, overlap_threshold=0.5)
print(f"Colocalized objects: {coloc_df['colocalized'].sum()} / {len(coloc_df)}")
```

---

## Background Correction

### Rolling Ball Background Subtraction

```python
from skimage.morphology import disk, white_tophat

def rolling_ball_background(image, radius=50):
    """Remove uneven background using rolling ball algorithm.

    Args:
        image: 2D grayscale image
        radius: ball radius (larger = remove more gradual gradients)

    Returns: Background-corrected image
    """
    # White top-hat with large structuring element
    selem = disk(radius)
    background = white_tophat(image, selem)

    # Subtract background
    corrected = image.astype(float) - background.astype(float)
    corrected = np.clip(corrected, 0, None)  # No negative values

    return corrected.astype(image.dtype)
```

### Local Background Subtraction

```python
def local_background_subtraction(image, labels):
    """Subtract local background for each object.

    Args:
        image: Fluorescence image
        labels: Labeled segmentation

    Returns: DataFrame with background-corrected intensities
    """
    results = []

    for region in measure.regionprops(labels, intensity_image=image):
        obj_id = region.label
        bbox = region.bbox

        # Extract ROI (with padding)
        pad = 10
        y1, x1, y2, x2 = bbox
        y1 = max(0, y1 - pad)
        x1 = max(0, x1 - pad)
        y2 = min(image.shape[0], y2 + pad)
        x2 = min(image.shape[1], x2 + pad)

        roi_image = image[y1:y2, x1:x2]
        roi_mask = labels[y1:y2, x1:x2] == obj_id

        # Background = pixels around object (not object itself)
        background_mask = ~roi_mask
        if background_mask.sum() > 0:
            background_mean = roi_image[background_mask].mean()
        else:
            background_mean = 0

        # Corrected intensity
        object_mean = roi_image[roi_mask].mean()
        corrected_mean = object_mean - background_mean

        results.append({
            'object_id': obj_id,
            'raw_mean': object_mean,
            'background_mean': background_mean,
            'corrected_mean': corrected_mean,
            'area': region.area
        })

    return pd.DataFrame(results)
```

### Percentile-Based Background

```python
def percentile_background_correction(image, percentile=5):
    """Subtract background estimated from low percentile.

    Args:
        image: Fluorescence image
        percentile: Percentile to use as background (default 5th)

    Returns: Background-corrected image
    """
    background = np.percentile(image, percentile)
    corrected = image.astype(float) - background
    corrected = np.clip(corrected, 0, None)
    return corrected.astype(image.dtype)
```

---

## Visualization

### Overlay Channels

```python
import matplotlib.pyplot as plt

def visualize_channels(image, channel_names=['Ch1', 'Ch2', 'Ch3'],
                      colors=['blue', 'green', 'red']):
    """Visualize multi-channel image.

    Args:
        image: Multi-channel image (H, W, C)
        channel_names: List of channel names
        colors: List of colors for each channel
    """
    n_channels = min(image.shape[-1], len(channel_names))

    fig, axes = plt.subplots(1, n_channels + 1, figsize=(4*(n_channels+1), 4))

    # Individual channels
    for i in range(n_channels):
        axes[i].imshow(image[..., i], cmap='gray')
        axes[i].set_title(channel_names[i])
        axes[i].axis('off')

    # Composite (RGB overlay)
    if n_channels >= 3:
        rgb = np.stack([
            image[..., 0] / image[..., 0].max(),
            image[..., 1] / image[..., 1].max(),
            image[..., 2] / image[..., 2].max()
        ], axis=-1)
        axes[n_channels].imshow(rgb)
        axes[n_channels].set_title('Composite')
        axes[n_channels].axis('off')

    plt.tight_layout()
    plt.show()
```

### Scatter Plot for Colocalization

```python
def plot_colocalization(channel1, channel2, mask=None):
    """Create scatter plot for colocalization analysis.

    Args:
        channel1, channel2: Fluorescence images
        mask: Optional mask to restrict analysis
    """
    if mask is not None:
        c1 = channel1[mask].flatten()
        c2 = channel2[mask].flatten()
    else:
        c1 = channel1.flatten()
        c2 = channel2.flatten()

    # Sample for speed (if too many pixels)
    if len(c1) > 10000:
        idx = np.random.choice(len(c1), 10000, replace=False)
        c1 = c1[idx]
        c2 = c2[idx]

    # Calculate Pearson
    r, p = stats.pearsonr(c1, c2)

    # Plot
    plt.figure(figsize=(6, 6))
    plt.hexbin(c1, c2, gridsize=50, cmap='viridis', mincnt=1)
    plt.colorbar(label='Count')
    plt.xlabel('Channel 1 Intensity')
    plt.ylabel('Channel 2 Intensity')
    plt.title(f'Colocalization (r = {r:.3f}, p = {p:.2e})')
    plt.tight_layout()
    plt.show()
```

---

## Complete Example Workflow

```python
import tifffile
import numpy as np
import pandas as pd
from skimage import filters, measure, morphology

# Load multi-channel image
image = tifffile.imread("cells_3channel.tif")  # (H, W, 3)

# Segment nuclei from DAPI channel
dapi = image[..., 0]
thresh = filters.threshold_otsu(dapi)
binary = dapi > thresh
binary = morphology.remove_small_objects(binary, min_size=50)
binary = morphology.binary_fill_holes(binary)
labels = measure.label(binary)

print(f"Segmented {labels.max()} nuclei")

# Quantify all channels
results = quantify_multichannel(image, labels, channel_names=['DAPI', 'GFP', 'RFP'])
print(results.head())

# Calculate GFP/RFP ratio
results = calculate_ratios(results, 'GFP', 'RFP')

# Colocalization analysis
gfp = image[..., 1]
rfp = image[..., 2]
r, p = pearson_colocalization(gfp, rfp, mask=labels>0)
print(f"GFP-RFP Pearson correlation: r = {r:.3f}, p = {p:.2e}")

M1, M2 = manders_coefficients(gfp, rfp,
                               threshold1=filters.threshold_otsu(gfp),
                               threshold2=filters.threshold_otsu(rfp))
print(f"Manders coefficients: M1 = {M1:.3f}, M2 = {M2:.3f}")

# Save results
results.to_csv("fluorescence_quantification.csv", index=False)
```
