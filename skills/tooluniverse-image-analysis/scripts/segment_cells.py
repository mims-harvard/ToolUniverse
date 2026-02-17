#!/usr/bin/env python3
"""
Cell Segmentation and Counting Script

Segment and count cells/nuclei in fluorescence or brightfield images.
Supports DAPI, phase contrast, and fluorescence marker images.

Usage:
    python segment_cells.py input.tif --channel 0 --min-area 50 --method watershed
    python segment_cells.py input_folder/ --output results.csv --batch
"""

import argparse
import numpy as np
import pandas as pd
import tifffile
from pathlib import Path
from skimage import filters, measure, morphology
from skimage.color import rgb2gray
from scipy import ndimage
from skimage.feature import peak_local_max
from skimage.segmentation import watershed


def count_cells_watershed(image, channel=None, min_area=50, min_distance=10):
    """Count cells using watershed segmentation (for touching cells).

    Args:
        image: numpy array
        channel: channel index for multi-channel images
        min_area: minimum cell area in pixels
        min_distance: minimum distance between cell centers

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

    # Find local maxima (cell centers)
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
        'major_axis_length', 'minor_axis_length', 'eccentricity'
    ])
    props_df = pd.DataFrame(props)

    count = labels.max()

    return count, labels, props_df


def count_cells_basic(image, channel=None, threshold_method='otsu', min_area=50):
    """Count cells using simple thresholding (for well-separated cells).

    Args:
        image: numpy array
        channel: channel index
        threshold_method: 'otsu', 'li', 'triangle', or numeric value
        min_area: minimum cell area

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
    if threshold_method == 'otsu':
        thresh = filters.threshold_otsu(img)
    elif threshold_method == 'li':
        thresh = filters.threshold_li(img)
    elif threshold_method == 'triangle':
        thresh = filters.threshold_triangle(img)
    else:
        thresh = float(threshold_method)

    binary = img > thresh
    binary = morphology.remove_small_objects(binary, min_size=min_area)

    # Label
    labels = measure.label(binary)

    # Measure
    props = measure.regionprops_table(labels, img, properties=[
        'label', 'area', 'mean_intensity', 'centroid',
        'major_axis_length', 'minor_axis_length', 'eccentricity'
    ])
    props_df = pd.DataFrame(props)

    count = labels.max()

    return count, labels, props_df


def process_single_image(image_path, args):
    """Process a single image.

    Args:
        image_path: Path to image file
        args: Command-line arguments

    Returns: dict with results
    """
    # Load image
    image = tifffile.imread(image_path)

    # Count cells
    if args.method == 'watershed':
        count, labels, props = count_cells_watershed(
            image,
            channel=args.channel,
            min_area=args.min_area,
            min_distance=args.min_distance
        )
    else:
        count, labels, props = count_cells_basic(
            image,
            channel=args.channel,
            threshold_method=args.threshold,
            min_area=args.min_area
        )

    # Save labeled image if requested
    if args.save_labels:
        label_path = Path(image_path).stem + '_labels.tif'
        tifffile.imwrite(label_path, labels.astype(np.uint16))
        print(f"Saved labels to {label_path}")

    return {
        'filename': Path(image_path).name,
        'cell_count': count,
        'mean_area': props['area'].mean(),
        'std_area': props['area'].std(),
        'mean_intensity': props['mean_intensity'].mean()
    }


def process_batch(input_folder, args):
    """Process all images in folder.

    Args:
        input_folder: Path to folder with images
        args: Command-line arguments

    Returns: DataFrame with results
    """
    input_path = Path(input_folder)

    # Find all image files
    image_files = list(input_path.glob('*.tif')) + \
                  list(input_path.glob('*.tiff')) + \
                  list(input_path.glob('*.png'))

    if len(image_files) == 0:
        print(f"No image files found in {input_folder}")
        return None

    print(f"Processing {len(image_files)} images...")

    results = []
    for img_path in image_files:
        print(f"  {img_path.name}...")
        result = process_single_image(img_path, args)
        results.append(result)

    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(
        description='Segment and count cells in microscopy images'
    )
    parser.add_argument('input', help='Input image file or folder')
    parser.add_argument('--output', '-o', default='cell_counts.csv',
                       help='Output CSV file (default: cell_counts.csv)')
    parser.add_argument('--method', choices=['basic', 'watershed'], default='watershed',
                       help='Segmentation method (default: watershed)')
    parser.add_argument('--channel', '-c', type=int, default=None,
                       help='Channel index for multi-channel images')
    parser.add_argument('--min-area', type=int, default=50,
                       help='Minimum cell area in pixels (default: 50)')
    parser.add_argument('--min-distance', type=int, default=10,
                       help='Minimum distance between cell centers for watershed (default: 10)')
    parser.add_argument('--threshold', default='otsu',
                       help='Threshold method: otsu, li, triangle, or numeric value (default: otsu)')
    parser.add_argument('--save-labels', action='store_true',
                       help='Save labeled images')
    parser.add_argument('--batch', action='store_true',
                       help='Process all images in input folder')

    args = parser.parse_args()

    # Process
    if args.batch or Path(args.input).is_dir():
        results = process_batch(args.input, args)
    else:
        result = process_single_image(args.input, args)
        results = pd.DataFrame([result])

    # Save results
    if results is not None:
        results.to_csv(args.output, index=False)
        print(f"\nResults saved to {args.output}")
        print(f"\nSummary:")
        print(f"  Total images: {len(results)}")
        print(f"  Total cells: {results['cell_count'].sum()}")
        print(f"  Mean cells per image: {results['cell_count'].mean():.1f}")
        print(f"  Mean cell area: {results['mean_area'].mean():.1f} pixels")


if __name__ == '__main__':
    main()
