# Image Processing Basics

Complete guide for image loading, preprocessing, and format handling.

---

## Table of Contents

1. [Image Loading](#image-loading)
2. [Library Selection Guide](#library-selection-guide)
3. [Preprocessing](#preprocessing)
4. [Format Conversions](#format-conversions)

---

## Image Loading

### Load TIFF Files

```python
import tifffile
import numpy as np

# Load single-page TIFF
image = tifffile.imread("image.tif")

# Load multi-page TIFF (Z-stack, time series)
stack = tifffile.imread("stack.tif")  # Returns (T/Z, H, W) or (T/Z, H, W, C)

# Load specific page from multi-page TIFF
with tifffile.TiffFile("stack.tif") as tif:
    page_3 = tif.pages[3].asarray()

# Load with metadata
with tifffile.TiffFile("image.tif") as tif:
    image = tif.asarray()
    metadata = tif.pages[0].tags
    print(metadata)
```

### Load PNG/JPG

```python
from PIL import Image
import numpy as np

# Using PIL
img = Image.open("image.png")
image_array = np.array(img)

# Using scikit-image
from skimage import io
image = io.imread("image.png")
```

### Load from scikit-image

```python
from skimage import io

# Many formats supported
image = io.imread("image.png")  # or .jpg, .tif, .bmp, etc.

# Load image collection
from skimage.io import ImageCollection
ic = ImageCollection("folder/*.tif")
images = [img for img in ic]
```

---

## Library Selection Guide

### scikit-image vs OpenCV

#### Use scikit-image when:

✅ **Scientific measurements needed**
- `regionprops` for area, perimeter, circularity
- Shape metrics (eccentricity, solidity, moments)
- Publication-quality analysis

✅ **Easier syntax for scientists**
```python
from skimage import filters, measure
thresh = filters.threshold_otsu(image)
binary = image > thresh
labels = measure.label(binary)
props = measure.regionprops(labels)
```

✅ **Integration with scipy/numpy**
- Natural workflow with scientific Python stack
- Good documentation with examples

#### Use OpenCV when:

✅ **Speed is critical**
- Real-time processing
- Large image batches
- Video analysis

✅ **Advanced computer vision**
- Feature detection (SIFT, SURF, ORB)
- Template matching
- Object tracking

✅ **GPU acceleration available**
- CUDA support for specific operations

#### Both work for:

- Thresholding
- Morphological operations
- Filtering (Gaussian, median, etc.)
- Edge detection
- Image transformations

---

## Preprocessing

### Convert to Grayscale

```python
from skimage.color import rgb2gray

# scikit-image (returns float 0-1)
gray = rgb2gray(image_rgb)

# OpenCV
import cv2
gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)

# Manual (weighted average)
gray = 0.299 * image[:, :, 0] + 0.587 * image[:, :, 1] + 0.114 * image[:, :, 2]
```

### Enhance Contrast

```python
from skimage import exposure

# Histogram equalization
enhanced = exposure.equalize_hist(image)

# Adaptive histogram equalization (CLAHE)
enhanced = exposure.equalize_adapthist(image, clip_limit=0.03)

# Rescale intensity
enhanced = exposure.rescale_intensity(image, in_range=(low, high))

# Gamma correction
enhanced = exposure.adjust_gamma(image, gamma=1.5)
```

### Noise Reduction

```python
from skimage import filters
from skimage.restoration import denoise_bilateral, denoise_tv_chambolle

# Gaussian blur
smoothed = filters.gaussian(image, sigma=2.0)

# Median filter (good for salt-and-pepper noise)
from scipy.ndimage import median_filter
smoothed = median_filter(image, size=3)

# Bilateral filter (edge-preserving)
smoothed = denoise_bilateral(image, sigma_color=0.05, sigma_spatial=15)

# Total variation denoising
smoothed = denoise_tv_chambolle(image, weight=0.1)
```

### Sharpening

```python
from scipy.ndimage import convolve

# Unsharp masking
from skimage.filters import unsharp_mask
sharpened = unsharp_mask(image, radius=2, amount=1.0)

# Laplacian sharpening
laplacian_kernel = np.array([[0, -1, 0],
                             [-1, 5, -1],
                             [0, -1, 0]])
sharpened = convolve(image, laplacian_kernel)
```

---

## Format Conversions

### Data Type Conversions

```python
from skimage import img_as_float, img_as_ubyte, img_as_uint

# Convert to float (0.0 - 1.0)
image_float = img_as_float(image_uint8)

# Convert to uint8 (0 - 255)
image_uint8 = img_as_ubyte(image_float)

# Convert to uint16 (0 - 65535)
image_uint16 = img_as_uint(image_float)

# Manual conversion with scaling
image_uint8 = ((image_float - image_float.min()) /
               (image_float.max() - image_float.min()) * 255).astype(np.uint8)
```

### Channel Manipulations

```python
# Extract channel from multi-channel image
channel_0 = image[:, :, 0]

# Merge channels
merged = np.stack([ch1, ch2, ch3], axis=-1)

# Split RGB
r, g, b = image[:, :, 0], image[:, :, 1], image[:, :, 2]

# Convert RGB to BGR (OpenCV uses BGR)
bgr = image[:, :, [2, 1, 0]]
```

### Resize and Rescale

```python
from skimage.transform import resize, rescale

# Resize to specific dimensions
resized = resize(image, (512, 512), anti_aliasing=True)

# Rescale by factor
scaled = rescale(image, scale=0.5, anti_aliasing=True)

# OpenCV resize
import cv2
resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_LINEAR)
```

---

## Batch Processing

### Process Multiple Images

```python
import os
import glob
import tifffile
import pandas as pd

def batch_process_images(input_folder, output_csv, process_func):
    """Process all images in folder.

    Args:
        input_folder: Path to folder with images
        output_csv: Path to save results
        process_func: Function that takes image, returns dict of results

    Returns: DataFrame with results
    """
    # Find all images
    image_paths = glob.glob(os.path.join(input_folder, "*.tif"))
    image_paths += glob.glob(os.path.join(input_folder, "*.png"))

    results = []

    for img_path in image_paths:
        print(f"Processing {os.path.basename(img_path)}...")

        # Load image
        image = tifffile.imread(img_path)

        # Process
        result = process_func(image)
        result['filename'] = os.path.basename(img_path)

        results.append(result)

    # Combine and save
    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False)

    return df


# Example process function
def count_cells_in_image(image):
    from skimage import filters, measure, morphology

    # Segment
    thresh = filters.threshold_otsu(image)
    binary = image > thresh
    binary = morphology.remove_small_objects(binary, min_size=50)
    labels = measure.label(binary)

    return {
        'cell_count': labels.max(),
        'mean_cell_area': np.mean([r.area for r in measure.regionprops(labels)])
    }


# Run batch processing
results = batch_process_images("images/", "results.csv", count_cells_in_image)
```

---

## Memory Management

### Handle Large Images

```python
# Load image in chunks
import tifffile

def process_large_image_tiles(image_path, tile_size=512):
    """Process large image in tiles to save memory.

    Args:
        image_path: Path to image
        tile_size: Size of tiles

    Returns: Results from processing
    """
    with tifffile.TiffFile(image_path) as tif:
        image_shape = tif.pages[0].shape

        results = []

        for y in range(0, image_shape[0], tile_size):
            for x in range(0, image_shape[1], tile_size):
                # Define tile bounds
                y_end = min(y + tile_size, image_shape[0])
                x_end = min(x + tile_size, image_shape[1])

                # Load tile
                tile = tif.pages[0].asarray()[y:y_end, x:x_end]

                # Process tile
                result = process_tile(tile, x, y)
                results.append(result)

        return results


def process_tile(tile, offset_x, offset_y):
    """Process a single tile."""
    # Your processing here
    from skimage import filters, measure
    thresh = filters.threshold_otsu(tile)
    binary = tile > thresh
    labels = measure.label(binary)

    # Adjust coordinates by offset
    props = []
    for r in measure.regionprops(labels):
        props.append({
            'centroid_x': r.centroid[1] + offset_x,
            'centroid_y': r.centroid[0] + offset_y,
            'area': r.area
        })

    return props
```

---

## Calibration

### Convert Pixels to Physical Units

```python
def pixels_to_microns(pixel_value, pixel_size_um):
    """Convert pixels to micrometers.

    Args:
        pixel_value: Value in pixels (area, length, etc.)
        pixel_size_um: Size of one pixel in micrometers

    Returns: Value in micrometers (or µm²)
    """
    return pixel_value * pixel_size_um


def calibrate_measurements(results_df, pixel_size_um, area_cols=None, length_cols=None):
    """Add calibrated measurements to DataFrame.

    Args:
        results_df: DataFrame with pixel measurements
        pixel_size_um: Pixel size in micrometers
        area_cols: List of area column names
        length_cols: List of length column names

    Returns: DataFrame with calibrated columns added
    """
    df = results_df.copy()

    if area_cols:
        for col in area_cols:
            df[f'{col}_um2'] = df[col] * (pixel_size_um ** 2)
            df[f'{col}_mm2'] = df[f'{col}_um2'] / 1e6

    if length_cols:
        for col in length_cols:
            df[f'{col}_um'] = df[col] * pixel_size_um

    return df


# Example
results = pd.DataFrame({
    'area': [100, 200, 150],
    'perimeter': [40, 60, 50]
})

calibrated = calibrate_measurements(
    results,
    pixel_size_um=0.65,
    area_cols=['area'],
    length_cols=['perimeter']
)
print(calibrated)
```

---

## Quality Checks

### Detect Focus Issues

```python
from skimage.filters import laplace

def check_image_focus(image):
    """Check if image is in focus using Laplacian variance.

    Args:
        image: Grayscale image

    Returns: Focus score (higher = better focus)
    """
    laplacian = laplace(image)
    variance = laplacian.var()
    return variance


# Example: Check all images in folder
import glob

focus_scores = []
for img_path in glob.glob("images/*.tif"):
    img = tifffile.imread(img_path)
    score = check_image_focus(img)
    focus_scores.append({
        'filename': os.path.basename(img_path),
        'focus_score': score,
        'in_focus': score > 100  # Threshold depends on your images
    })

focus_df = pd.DataFrame(focus_scores)
print(focus_df)
```

### Detect Saturation

```python
def check_saturation(image, threshold=0.01):
    """Check if image has saturated pixels.

    Args:
        image: Image array
        threshold: Fraction of pixels allowed to be saturated

    Returns: (is_saturated, fraction_saturated)
    """
    if image.dtype == np.uint8:
        max_val = 255
    elif image.dtype == np.uint16:
        max_val = 65535
    else:
        max_val = image.max()

    saturated = image >= max_val
    fraction = saturated.sum() / image.size

    return fraction > threshold, fraction


# Check all channels
for i in range(image.shape[-1]):
    is_sat, frac = check_saturation(image[..., i])
    if is_sat:
        print(f"Channel {i}: {frac*100:.2f}% pixels saturated!")
```

---

## Troubleshooting Common Issues

### Image orientation wrong

```python
# Rotate
from skimage.transform import rotate
rotated = rotate(image, angle=90)

# Flip
flipped_ud = np.flipud(image)  # Up-down
flipped_lr = np.fliplr(image)  # Left-right
```

### Image too dark/bright

```python
# Auto-adjust contrast
from skimage import exposure
adjusted = exposure.rescale_intensity(image, in_range='image', out_range=(0, 255))
```

### Uneven illumination

```python
# Background subtraction
from skimage.morphology import white_tophat, disk
background = white_tophat(image, disk(50))
corrected = image - background
```

### File won't load

```python
# Try different libraries
try:
    image = tifffile.imread(path)
except:
    from PIL import Image
    image = np.array(Image.open(path))
```
