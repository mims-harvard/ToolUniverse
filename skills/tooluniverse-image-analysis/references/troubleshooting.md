# Troubleshooting Guide

Common issues and solutions for microscopy image analysis.

---

## Segmentation Issues

### Problem: Cells/Colonies Merged Together

**Symptoms**: Multiple objects detected as single object

**Solutions**:
1. Use watershed segmentation
   ```python
   from scipy import ndimage
   from skimage.feature import peak_local_max
   from skimage.segmentation import watershed

   distance = ndimage.distance_transform_edt(binary)
   coords = peak_local_max(distance, min_distance=10)
   mask = np.zeros(distance.shape, dtype=bool)
   mask[tuple(coords.T)] = True
   markers = measure.label(mask)
   labels = watershed(-distance, markers, mask=binary)
   ```

2. Decrease `min_distance` parameter in watershed
3. Apply morphological opening before labeling
4. For very dense images, use CellPose or StarDist

---

### Problem: Cells Split into Multiple Objects

**Symptoms**: One cell detected as 2-3 objects

**Solutions**:
1. Increase `min_distance` in watershed
2. Apply morphological closing before labeling
   ```python
   from skimage.morphology import binary_closing, disk
   binary = binary_closing(binary, disk(5))
   ```
3. Use more conservative threshold (Li instead of Otsu)
4. Smooth image before thresholding

---

### Problem: Background Detected as Objects

**Symptoms**: Many small false positive detections

**Solutions**:
1. Increase `min_area` threshold
   ```python
   binary = morphology.remove_small_objects(binary, min_size=200)
   ```
2. Use more conservative threshold method
3. Apply morphological opening
4. Filter by shape metrics (circularity, eccentricity)

---

### Problem: Dim Objects Not Detected

**Symptoms**: Faint cells/colonies missing

**Solutions**:
1. Use Li or Triangle threshold (more sensitive)
   ```python
   thresh = filters.threshold_li(image)
   ```
2. Use percentile-based threshold
   ```python
   thresh = np.percentile(image[image > 0], 25)
   ```
3. Enhance contrast before thresholding
   ```python
   from skimage import exposure
   enhanced = exposure.equalize_adapthist(image)
   ```
4. Manually set lower threshold value

---

## Image Quality Issues

### Problem: Uneven Illumination

**Symptoms**: Gradient across image, threshold doesn't work globally

**Solutions**:
1. Use adaptive thresholding
   ```python
   from skimage.filters import threshold_local
   local_thresh = threshold_local(image, block_size=51)
   binary = image > local_thresh
   ```

2. Apply background subtraction
   ```python
   from skimage.morphology import white_tophat, disk
   background = white_tophat(image, disk(50))
   corrected = image - background
   ```

3. Use rolling ball background correction
4. Normalize illumination before analysis

---

### Problem: Noisy Images

**Symptoms**: Salt-and-pepper noise, grainy appearance

**Solutions**:
1. Apply Gaussian smoothing
   ```python
   from skimage.filters import gaussian
   smoothed = gaussian(image, sigma=2.0)
   ```

2. Use median filter (better for salt-and-pepper)
   ```python
   from scipy.ndimage import median_filter
   smoothed = median_filter(image, size=3)
   ```

3. Use bilateral filter (edge-preserving)
   ```python
   from skimage.restoration import denoise_bilateral
   smoothed = denoise_bilateral(image, sigma_color=0.05, sigma_spatial=15)
   ```

---

### Problem: Out-of-Focus Images

**Symptoms**: Blurry, low contrast, poor segmentation

**Solutions**:
1. Apply unsharp masking
   ```python
   from skimage.filters import unsharp_mask
   sharpened = unsharp_mask(image, radius=2, amount=1.0)
   ```

2. Enhance edges
   ```python
   from skimage.filters import sobel
   edges = sobel(image)
   enhanced = image + 0.5 * edges
   ```

3. Use deconvolution (if PSF known)
4. Reject out-of-focus images (check Laplacian variance)

---

## Statistical Analysis Issues

### Problem: Results Don't Match R

**Symptoms**: P-values or statistics differ from R output

**Solutions for Dunnett's test**:
- Use `scipy.stats.dunnett()` (requires scipy >= 1.10)
- Ensure group labels match R exactly
- Check control group is correctly specified

**Solutions for natural spline**:
- Use explicit knot placement matching R's `ns()`
  ```python
  n_internal_knots = spline_df - 1
  quantile_pcts = np.linspace(100.0/(n_internal_knots+1),
                               100.0*n_internal_knots/(n_internal_knots+1),
                               n_internal_knots)
  knots = np.percentile(x, quantile_pcts)
  ```

**Solutions for Cohen's d**:
- Verify using pooled standard deviation
- Check pandas `.std()` uses `ddof=1` (sample SD)
- Ensure correct group order (sign matters)

---

### Problem: High P-Values (No Significance)

**Symptoms**: P-values all > 0.05

**Possible causes**:
1. **Insufficient sample size** - Run power analysis
2. **High variability** - Check SD within groups
3. **Small effect size** - Calculate Cohen's d
4. **Wrong statistical test** - Check assumptions (normality, equal variance)
5. **Data quality issues** - Check for outliers, measurement errors

**Solutions**:
1. Increase sample size (if collecting new data)
2. Use non-parametric tests if data not normal
3. Check for and handle outliers
4. Consider effect size rather than just p-value

---

### Problem: Can't Reproduce BixBench Answer

**Symptoms**: Your answer differs from expected BixBench answer

**Check these**:
1. **Data loading** - Correct file? All rows loaded?
2. **Grouping variables** - Exact spelling of group names?
3. **Filter conditions** - Any rows excluded/included incorrectly?
4. **Rounding** - "Nearest thousand" means `int(round(val, -3))`
5. **Direction** - "Reduction" vs "increase", "KD vs CTRL" vs "CTRL vs KD"
6. **Statistical function** - Exact match to R function used?

---

## Performance Issues

### Problem: Analysis Too Slow

**Solutions for large images**:
1. Process tiles instead of whole image
2. Downsample for preview/parameter tuning
3. Use OpenCV for batch processing (faster than scikit-image)
4. Parallelize batch processing
   ```python
   from multiprocessing import Pool
   with Pool(4) as p:
       results = p.map(process_func, image_paths)
   ```

---

### Problem: Out of Memory

**Solutions**:
1. Process images in tiles
2. Load images as memory-mapped arrays
3. Reduce image resolution for analysis
4. Process one at a time instead of loading all
5. Use generators instead of lists

---

## Data Format Issues

### Problem: Image Won't Load

**Symptoms**: Error loading file

**Solutions**:
1. Try different libraries
   ```python
   # Try tifffile first
   try:
       image = tifffile.imread(path)
   except:
       # Try PIL
       from PIL import Image
       image = np.array(Image.open(path))
   ```

2. Check file format (use `file` command on Linux/Mac)
3. Check file corruption
4. Verify file permissions

---

### Problem: Wrong Image Dimensions

**Symptoms**: Image shape not as expected

**Solutions**:
1. Check dimension order (C, Z, T)
   ```python
   print(f"Shape: {image.shape}")
   # Might need to transpose
   image = np.transpose(image, (1, 2, 0))  # Move channels to last
   ```

2. Squeeze singleton dimensions
   ```python
   image = np.squeeze(image)
   ```

3. Verify metadata
   ```python
   with tifffile.TiffFile(path) as tif:
       print(tif.pages[0].tags)
   ```

---

### Problem: CSV/TSV Parse Error

**Symptoms**: pandas can't read measurement file

**Solutions**:
1. Check delimiter (comma vs tab)
   ```python
   df = pd.read_csv(path, sep='\t')  # Try tab
   ```

2. Specify encoding
   ```python
   df = pd.read_csv(path, encoding='utf-8')
   ```

3. Skip header rows if needed
   ```python
   df = pd.read_csv(path, skiprows=2)
   ```

4. Handle missing values
   ```python
   df = pd.read_csv(path, na_values=['NA', 'N/A', ''])
   ```

---

## Measurement Issues

### Problem: Circularity Values > 1

**Symptoms**: Circularity should be 0-1, but getting values > 1

**Cause**: Usually perimeter measurement artifacts

**Solutions**:
1. Smooth binary mask before measuring
   ```python
   from skimage.morphology import binary_closing, disk
   binary = binary_closing(binary, disk(2))
   ```

2. Use different perimeter method
3. Cap circularity at 1.0
   ```python
   circularity = np.minimum(circularity, 1.0)
   ```

---

### Problem: Negative Intensities After Background Correction

**Symptoms**: Mean intensity < 0 after correction

**Solutions**:
1. Clip to zero
   ```python
   corrected = np.clip(image - background, 0, None)
   ```

2. Use more conservative background estimate
3. Check background correction method is appropriate

---

## Visualization Issues

### Problem: Can't See Labels/Overlay

**Symptoms**: Overlay looks wrong or invisible

**Solutions**:
1. Check data types match
2. Normalize intensity ranges
   ```python
   from skimage import exposure
   image_norm = exposure.rescale_intensity(image, out_range=(0, 1))
   ```

3. Use proper overlay function
   ```python
   from skimage.color import label2rgb
   overlay = label2rgb(labels, image=image, bg_label=0, alpha=0.3)
   ```

---

## Getting More Help

If issue persists:

1. **Check the documentation** - Each reference guide has detailed examples
2. **Verify input data** - Print shapes, dtypes, value ranges
3. **Test with simple case** - Try with known-good image
4. **Compare with example** - Use provided example scripts
5. **Check package versions** - Update scikit-image, scipy if needed

### Useful Debugging Code

```python
# Print image properties
print(f"Shape: {image.shape}")
print(f"Dtype: {image.dtype}")
print(f"Range: [{image.min()}, {image.max()}]")
print(f"Mean: {image.mean():.2f}")

# Check for NaN/inf
print(f"NaN values: {np.isnan(image).sum()}")
print(f"Inf values: {np.isinf(image).sum()}")

# Visualize intermediate steps
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
axes[0].imshow(image, cmap='gray')
axes[0].set_title('Original')
axes[1].imshow(binary, cmap='gray')
axes[1].set_title('Binary')
axes[2].imshow(labels, cmap='nipy_spectral')
axes[2].set_title(f'Labels (n={labels.max()})')
plt.show()
```
