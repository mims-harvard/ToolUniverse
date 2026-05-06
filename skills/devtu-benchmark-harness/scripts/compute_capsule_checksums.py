#!/usr/bin/env python3
"""Compute SHA256 of every file in bixbench_clean/data/CapsuleFolder-*.

Writes the result to bixbench_clean/checksums.json. This file is the
canonical fingerprint for the clean capsules — the harness verifies it
before each run to detect accidental modification.

Usage:
    python compute_capsule_checksums.py
"""

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLEAN = REPO / "temp_docs_and_tests" / "bixbench_clean" / "data"
OUT = REPO / "temp_docs_and_tests" / "bixbench_clean" / "checksums.json"


def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if not CLEAN.exists():
        print(f"ERROR: clean dir not found: {CLEAN}", file=sys.stderr)
        sys.exit(1)

    capsules = sorted(CLEAN.glob("CapsuleFolder-*"))
    print(f"Hashing {len(capsules)} capsules...")
    result = {}
    for cap in capsules:
        files = {}
        for f in sorted(cap.rglob("*")):
            if f.is_file():
                rel = str(f.relative_to(cap))
                files[rel] = file_sha256(f)
        result[cap.name] = files
        print(f"  {cap.name}: {len(files)} files", flush=True)

    OUT.write_text(json.dumps(result, indent=2, sort_keys=True))
    n_files = sum(len(v) for v in result.values())
    print(f"\nWrote {n_files} file hashes across {len(result)} capsules to {OUT}")


if __name__ == "__main__":
    main()
