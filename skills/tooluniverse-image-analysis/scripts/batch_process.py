#!/usr/bin/env python3
"""
Batch Image Processing Script

Process multiple microscopy images with various analysis types.
Supports cell counting, colony morphometry, and fluorescence quantification.

Usage:
    python batch_process.py images/ output.csv --analysis cell_count
    python batch_process.py images/ output.csv --analysis colony_morphometry --min-area 500
    python batch_process.py images/ output.csv --analysis fluorescence --channel 0
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


def analyze_cell_count(image, args):
    """Count cells in image.

    Returns: dict with count and statistics
    """
    # Extract channel if multi-channel
    if args.channel is not None and image.ndim >= 3:
        img = image[..., args.channel].astype(float)
    elif image.ndim == 3:
        img = rgb2gray(image)
    else:
        img = image.astype(float)

    # Threshold
    thresh = filters.threshold_otsu(img)
    binary = img > thresh
    binary = morphology.remove_small_objects(binary, min_size=args.min_area)

    # Watershed if requested
    if args.use_watershed:
        distance = ndimage.distance_transform_edt(binary)
        coords = peak_local_max(distance, min_distance=args.min_distance, labels=binary)
        mask = np.zeros(distance.shape, dtype=bool)
        mask[tuple(coords.T)] = True
        markers = measure.label(mask)
        labels = watershed(-distance, markers, mask=binary)
    else:
        labels = measure.label(binary)

    # Measure
    props = measure.regionprops(labels, intensity_image=img)

    return {
        'count': len(props),
        'mean_area': np.mean([r.area for r in props]) if props else 0,
        'std_area': np.std([r.area for r in props]) if props else 0,
        'mean_intensity': np.mean([r.mean_intensity for r in props]) if props else 0
    }


def analyze_colony_morphometry(image, args):
    """Measure colony morphometry (area, circularity, etc.).

    Returns: dict with morphometry statistics
    """
    # Convert to grayscale
    if image.ndim == 3:
        img = rgb2gray(image)
    else:
        img = image.astype(float)

    # Threshold
    thresh = filters.threshold_otsu(img)
    binary = img > thresh
    binary = morphology.remove_small_objects(binary, min_size=args.min_area)
    binary = morphology.binary_fill_holes(binary)

    # Label and measure
    labels = measure.label(binary)
    props = measure.regionprops_table(labels, properties=[
        'area', 'perimeter', 'major_axis_length', 'minor_axis_length',
        'eccentricity', 'solidity'
    ])

    df = pd.DataFrame(props)

    if len(df) == 0:
        return {
            'count': 0,
            'mean_area': 0,
            'mean_circularity': 0,
            'mean_roundness': 0
        }

    # Calculate shape metrics
    df['circularity'] = 4 * np.pi * df['area'] / (df['perimeter']**2)
    df['roundness'] = 4 * df['area'] / (np.pi * df['major_axis_length']**2)

    return {
        'count': len(df),
        'mean_area': df['area'].mean(),
        'std_area': df['area'].std(),
        'mean_circularity': df['circularity'].mean(),
        'std_circularity': df['circularity'].std(),
        'mean_roundness': df['roundness'].mean(),
        'mean_eccentricity': df['eccentricity'].mean(),
        'mean_solidity': df['solidity'].mean()
    }


def analyze_fluorescence(image, args):
    """Measure fluorescence intensity.

    Returns: dict with intensity statistics
    """
    # Extract channel
    if args.channel is not None and image.ndim >= 3:
        img = image[..., args.channel].astype(float)
    else:
        img = image.astype(float)

    # Segment
    thresh = filters.threshold_otsu(img)
    binary = img > thresh
    binary = morphology.remove_small_objects(binary, min_size=args.min_area)
    labels = measure.label(binary)

    # Measure
    props = measure.regionprops(labels, intensity_image=img)

    if len(props) == 0:
        return {
            'object_count': 0,
            'mean_intensity': 0,
            'total_intensity': 0
        }

    mean_intensities = [r.mean_intensity for r in props]
    integrated_intensities = [r.area * r.mean_intensity for r in props]

    return {
        'object_count': len(props),
        'mean_intensity': np.mean(mean_intensities),
        'std_intensity': np.std(mean_intensities),
        'total_intensity': np.sum(integrated_intensities),
        'max_intensity': np.max(mean_intensities)
    }


def process_image(image_path, args):
    """Process a single image.

    Args:
        image_path: Path to image file
        args: Command-line arguments

    Returns: dict with results including filename
    """
    # Load image
    try:
        image = tifffile.imread(image_path)
    except Exception as e:
        print(f"  Error loading {image_path.name}: {e}")
        return None

    # Analyze based on type
    if args.analysis == 'cell_count':
        results = analyze_cell_count(image, args)
    elif args.analysis == 'colony_morphometry':
        results = analyze_colony_morphometry(image, args)
    elif args.analysis == 'fluorescence':
        results = analyze_fluorescence(image, args)
    else:
        print(f"Unknown analysis type: {args.analysis}")
        return None

    # Add metadata
    results['filename'] = image_path.name

    return results


def process_folder(input_folder, args):
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
                  list(input_path.glob('*.png')) + \
                  list(input_path.glob('*.jpg'))

    if len(image_files) == 0:
        print(f"No image files found in {input_folder}")
        return None

    print(f"Found {len(image_files)} images")
    print(f"Analysis type: {args.analysis}")
    print("Processing...")

    results = []
    for img_path in sorted(image_files):
        print(f"  {img_path.name}")
        result = process_image(img_path, args)
        if result is not None:
            results.append(result)

    if len(results) == 0:
        print("No results generated")
        return None

    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(
        description='Batch process microscopy images'
    )
    parser.add_argument('input_folder', help='Folder with input images')
    parser.add_argument('output', help='Output CSV file')
    parser.add_argument('--analysis', '-a',
                       choices=['cell_count', 'colony_morphometry', 'fluorescence'],
                       default='cell_count',
                       help='Analysis type (default: cell_count)')
    parser.add_argument('--channel', '-c', type=int, default=None,
                       help='Channel index for multi-channel images')
    parser.add_argument('--min-area', type=int, default=50,
                       help='Minimum object area in pixels (default: 50)')
    parser.add_argument('--min-distance', type=int, default=10,
                       help='Minimum distance for watershed (default: 10)')
    parser.add_argument('--use-watershed', action='store_true',
                       help='Use watershed segmentation for cell counting')

    args = parser.parse_args()

    # Process
    results = process_folder(args.input_folder, args)

    if results is not None:
        # Save results
        results.to_csv(args.output, index=False)
        print(f"\n✅ Results saved to {args.output}")

        # Print summary
        print(f"\n📊 Summary:")
        print(f"  Images processed: {len(results)}")

        if args.analysis == 'cell_count':
            print(f"  Total cells: {results['count'].sum()}")
            print(f"  Mean cells/image: {results['count'].mean():.1f}")
            print(f"  Mean cell area: {results['mean_area'].mean():.1f} pixels")

        elif args.analysis == 'colony_morphometry':
            print(f"  Total colonies: {results['count'].sum()}")
            print(f"  Mean area: {results['mean_area'].mean():.1f} pixels")
            print(f"  Mean circularity: {results['mean_circularity'].mean():.3f}")

        elif args.analysis == 'fluorescence':
            print(f"  Total objects: {results['object_count'].sum()}")
            print(f"  Mean intensity: {results['mean_intensity'].mean():.1f}")
            print(f"  Total integrated intensity: {results['total_intensity'].sum():.0f}")


if __name__ == '__main__':
    main()
