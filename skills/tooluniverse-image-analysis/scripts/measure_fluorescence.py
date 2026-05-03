#!/usr/bin/env python3
"""
Fluorescence Quantification Script

Measure fluorescence intensity across multiple channels.
Requires segmentation masks (from segment_cells.py or other tools).

Usage:
    python measure_fluorescence.py image.tif mask.tif --channels DAPI GFP RFP
    python measure_fluorescence.py images/ masks/ --output fluorescence.csv --batch
"""

import argparse
import numpy as np
import pandas as pd
import tifffile
from pathlib import Path
from skimage import measure


def quantify_multichannel(image, labels, channel_names=None):
    """Quantify fluorescence across all channels.

    Args:
        image: Multi-channel image (H, W, C) or single channel (H, W)
        labels: Labeled segmentation mask
        channel_names: List of channel names

    Returns: DataFrame with per-object, per-channel measurements
    """
    if image.ndim == 2:
        # Single channel
        image = image[..., np.newaxis]

    n_channels = image.shape[-1]

    if channel_names is None:
        channel_names = [f'channel_{i}' for i in range(n_channels)]
    elif len(channel_names) < n_channels:
        # Pad with generic names
        channel_names += [f'channel_{i}' for i in range(len(channel_names), n_channels)]

    # Measure first channel with area
    ch0_props = measure.regionprops_table(labels, image[..., 0], properties=[
        'label', 'area', 'mean_intensity', 'max_intensity', 'min_intensity'
    ])
    result = pd.DataFrame(ch0_props)
    result = result.rename(columns={
        'mean_intensity': f'mean_{channel_names[0]}',
        'max_intensity': f'max_{channel_names[0]}',
        'min_intensity': f'min_{channel_names[0]}'
    })

    # Add integrated intensity
    result[f'integrated_{channel_names[0]}'] = result['area'] * result[f'mean_{channel_names[0]}']

    # Measure remaining channels
    for i in range(1, n_channels):
        ch_props = measure.regionprops_table(labels, image[..., i], properties=[
            'label', 'mean_intensity', 'max_intensity', 'min_intensity'
        ])
        ch_df = pd.DataFrame(ch_props)
        ch_df = ch_df.rename(columns={
            'mean_intensity': f'mean_{channel_names[i]}',
            'max_intensity': f'max_{channel_names[i]}',
            'min_intensity': f'min_{channel_names[i]}'
        })

        # Add integrated intensity
        ch_df[f'integrated_{channel_names[i]}'] = result['area'] * ch_df[f'mean_{channel_names[i]}']

        # Merge
        result = result.merge(ch_df, on='label')

    return result


def calculate_ratios(intensity_df, channel_names):
    """Calculate all pairwise channel ratios.

    Args:
        intensity_df: DataFrame from quantify_multichannel
        channel_names: List of channel names

    Returns: DataFrame with ratio columns added
    """
    result = intensity_df.copy()

    # Calculate all pairwise ratios
    for i, ch1 in enumerate(channel_names):
        for ch2 in channel_names[i+1:]:
            num_col = f'mean_{ch1}'
            den_col = f'mean_{ch2}'
            if num_col in result.columns and den_col in result.columns:
                result[f'ratio_{ch1}_{ch2}'] = result[num_col] / result[den_col]

    return result


def process_single_pair(image_path, mask_path, args):
    """Process a single image-mask pair.

    Args:
        image_path: Path to fluorescence image
        mask_path: Path to segmentation mask
        args: Command-line arguments

    Returns: DataFrame with measurements
    """
    # Load image and mask
    image = tifffile.imread(image_path)
    labels = tifffile.imread(mask_path)

    # Convert mask to labels if needed
    if labels.dtype == bool:
        from skimage.measure import label
        labels = label(labels)

    # Quantify
    results = quantify_multichannel(image, labels, channel_names=args.channels)

    # Calculate ratios if requested
    if args.ratios and args.channels:
        results = calculate_ratios(results, args.channels)

    # Add metadata
    results['image'] = Path(image_path).name

    return results


def process_batch(image_folder, mask_folder, args):
    """Process all image-mask pairs in folders.

    Args:
        image_folder: Folder with fluorescence images
        mask_folder: Folder with segmentation masks
        args: Command-line arguments

    Returns: Combined DataFrame
    """
    image_path = Path(image_folder)
    mask_path = Path(mask_folder)

    # Find all image files
    image_files = sorted(list(image_path.glob('*.tif')) + list(image_path.glob('*.tiff')))

    if len(image_files) == 0:
        print(f"No image files found in {image_folder}")
        return None

    print(f"Processing {len(image_files)} images...")

    all_results = []

    for img_file in image_files:
        # Find corresponding mask
        mask_file = mask_path / img_file.name
        if not mask_file.exists():
            # Try with _mask suffix
            mask_file = mask_path / (img_file.stem + '_mask.tif')
        if not mask_file.exists():
            # Try with _labels suffix
            mask_file = mask_path / (img_file.stem + '_labels.tif')

        if not mask_file.exists():
            print(f"  Warning: No mask found for {img_file.name}, skipping")
            continue

        print(f"  {img_file.name}...")
        results = process_single_pair(img_file, mask_file, args)
        all_results.append(results)

    if len(all_results) == 0:
        print("No matching image-mask pairs found")
        return None

    return pd.concat(all_results, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(
        description='Measure fluorescence intensity in segmented objects'
    )
    parser.add_argument('image', help='Fluorescence image file or folder')
    parser.add_argument('mask', help='Segmentation mask file or folder')
    parser.add_argument('--output', '-o', default='fluorescence.csv',
                       help='Output CSV file (default: fluorescence.csv)')
    parser.add_argument('--channels', '-c', nargs='+',
                       help='Channel names (e.g., DAPI GFP RFP)')
    parser.add_argument('--ratios', action='store_true',
                       help='Calculate channel ratios')
    parser.add_argument('--batch', action='store_true',
                       help='Process all images in folders')

    args = parser.parse_args()

    # Process
    if args.batch or Path(args.image).is_dir():
        results = process_batch(args.image, args.mask, args)
    else:
        results = process_single_pair(args.image, args.mask, args)

    # Save results
    if results is not None:
        results.to_csv(args.output, index=False)
        print(f"\nResults saved to {args.output}")
        print(f"\nSummary:")
        print(f"  Total objects: {len(results)}")
        if 'image' in results.columns:
            print(f"  Images: {results['image'].nunique()}")

        # Summary statistics per channel
        if args.channels:
            print(f"\nMean intensities:")
            for ch in args.channels:
                col = f'mean_{ch}'
                if col in results.columns:
                    print(f"  {ch}: {results[col].mean():.1f} ± {results[col].std():.1f}")


if __name__ == '__main__':
    main()
