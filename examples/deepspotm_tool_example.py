#!/usr/bin/env python3
"""
DeepSpot-M Tool Usage Example

Predicts spatial gene expression for a single H&E histology tile with
DeepSpot-M, a multimodal foundation model that represents genes as queryable
embeddings and so spans the protein-coding transcriptome.

The example shows:
1. How to initialize ToolUniverse and load the DeepSpot-M tool
2. How to predict a few marker genes for one tile
3. How to switch the frozen gene-embedding source

Requirements:
- ToolUniverse installed
- pip install deepspotm
- Access to the gated weights: request it at
  https://huggingface.co/ratschlab/DeepSpotM and run `huggingface-cli login`
- A local 224x224 H&E tile cut at roughly 20x (~0.5 microns per pixel)

The predicted values are model output, NOT measured transcriptomics, and the
model is for non-commercial research use only, not for clinical or diagnostic
use. Paper: https://doi.org/10.64898/2026.06.19.26356060
"""

import argparse
import json

from tooluniverse import ToolUniverse


def main():
    """Predict marker-gene expression for one H&E tile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "tile",
        help="Path to a local 224x224 H&E tile (.png/.tif/.jpg) cut at ~20x.",
    )
    parser.add_argument(
        "--genes",
        nargs="+",
        default=["EPCAM", "CD3D", "PTPRC"],
        help="Gene symbols to predict (default: EPCAM CD3D PTPRC).",
    )
    parser.add_argument(
        "--source",
        default="scgpt",
        choices=["evo2", "orthrus", "prott5", "scgpt", "apertus"],
        help="Frozen gene-embedding source to query (default: scgpt).",
    )
    args = parser.parse_args()

    print("🔬 DeepSpot-M Tool Usage Example")
    print("=" * 50)

    print("Initializing ToolUniverse...")
    tooluni = ToolUniverse()
    tooluni.load_tools()
    print("✅ ToolUniverse initialized successfully")

    query = {
        "name": "DeepSpotM_predict_gene_expression",
        "arguments": {
            "image_path": args.tile,
            "genes": args.genes,
            "source": args.source,
        },
    }

    print(f"\nPredicting {', '.join(args.genes)} for {args.tile} ...")
    print("(the first call loads the checkpoint and is slow)")
    result = tooluni.run_one_function(query)

    if isinstance(result, dict) and result.get("status") == "error":
        # Covers a missing package, gated weights you have no access to yet,
        # a wrongly sized tile, or genes outside the model's panel.
        print(f"❌ {result['error']}")
        return

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
