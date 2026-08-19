#!/usr/bin/env python3
"""Offline administrator conversion of a reviewed CellTypist pickle model.

This script necessarily invokes the upstream pickle loader. Run it only in an
isolated provisioning environment after independently verifying the supplied
SHA-256. The live MCP server never imports or calls this module.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from celltypist.models import Model
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    expected = args.expected_sha256.lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        parser.error("--expected-sha256 must be 64 lowercase hexadecimal characters")
    observed = hashlib.sha256(args.input.read_bytes()).hexdigest()
    if observed != expected:
        raise SystemExit(f"source digest mismatch: observed {observed}")

    model = Model.load(str(args.input))
    classifier = model.classifier
    scaler = model.scaler
    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        coef=np.asarray(classifier.coef_, dtype=np.float64),
        intercept=np.asarray(classifier.intercept_, dtype=np.float64),
        classes=np.asarray(classifier.classes_, dtype=str),
        features=np.asarray(classifier.features, dtype=str),
        scaler_mean=np.asarray(scaler.mean_, dtype=np.float64),
        scaler_scale=np.asarray(scaler.scale_, dtype=np.float64),
        scaler_var=np.asarray(scaler.var_, dtype=np.float64),
        with_mean=np.asarray([bool(scaler.with_mean)], dtype=np.bool_),
        source_sha256=np.asarray([observed], dtype=str),
    )
    print(f"wrote {args.output} from source sha256 {observed}")


if __name__ == "__main__":
    main()
