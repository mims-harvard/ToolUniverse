#!/usr/bin/env python3
"""Convert a reviewed legacy COMPASS checkpoint into data-only artifacts.

The official COMPASS release serializes a complete ``FineTuner`` object. This
administrator-only utility therefore uses unrestricted PyTorch loading, but
only after an exact source digest check. The public MCP service never imports
this module and only reads safetensors, JSON, and an ``allow_pickle=False`` NPZ.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from safetensors.torch import save_file
import torch

from compass.main import FineTuner


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: _json_value(item) for key, item in value.items()}
    raise TypeError(f"model argument has unsupported type: {type(value).__name__}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--upstream-revision", required=True)
    args = parser.parse_args()

    expected = args.expected_sha256.lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        parser.error("--expected-sha256 must be 64 lowercase hexadecimal characters")
    observed = _sha256(args.input)
    if observed != expected:
        raise SystemExit(f"source digest mismatch: observed {observed}")

    # This is the only unrestricted load in the workflow. It is deliberately
    # isolated from the remotely callable module and occurs after digest pinning.
    finetuner = torch.load(args.input, weights_only=False, map_location="cpu")
    if not isinstance(finetuner, FineTuner):
        raise SystemExit("the pinned checkpoint is not an official COMPASS FineTuner")
    scaler = finetuner.scaler
    if getattr(scaler, "scale_method", None) != "minmax":
        raise SystemExit("only the reviewed COMPASS minmax preprocessing is supported")
    inner = scaler.scaler
    feature_names = np.asarray(finetuner.feature_name, dtype=str)
    scale = np.asarray(inner.scale_, dtype=np.float64)
    minimum = np.asarray(inner.min_, dtype=np.float64)
    if (
        feature_names.ndim != 1
        or scale.shape != feature_names.shape
        or minimum.shape != feature_names.shape
    ):
        raise SystemExit("checkpoint feature and scaler shapes do not agree")

    saved = finetuner.saver.inMemorySave
    state = {
        name: tensor.detach().cpu().contiguous()
        for name, tensor in saved["model_state_dict"].items()
    }
    model_args = _json_value(saved["model_args"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    weights_path = args.output_dir / "model.safetensors"
    preprocessing_path = args.output_dir / "preprocessing.npz"
    metadata_path = args.output_dir / "metadata.json"
    save_file(state, weights_path)
    np.savez_compressed(
        preprocessing_path,
        feature_names=feature_names,
        min=minimum,
        scale=scale,
    )
    metadata = {
        "format": "compass-safe-v1",
        "source_sha256": observed,
        "upstream_revision": args.upstream_revision,
        "model_args": model_args,
        "scale_method": "minmax",
        "weights_sha256": _sha256(weights_path),
        "preprocessing_sha256": _sha256(preprocessing_path),
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {args.output_dir} from source sha256 {observed}; "
        f"weights sha256 {metadata['weights_sha256']}"
    )


if __name__ == "__main__":
    main()
