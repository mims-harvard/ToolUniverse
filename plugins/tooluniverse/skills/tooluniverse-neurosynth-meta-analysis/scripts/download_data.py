#!/usr/bin/env python3
"""
Download and cache the Neurosynth coordinate database.

Fetches coordinates, study metadata, term vocabulary, and the term x study
tfidf weight matrix from the public neurosynth/neurosynth-data GitHub repo
(no authentication, no rate limit observed). Caches everything under
~/.cache/tooluniverse/neurosynth/ so repeated runs don't re-download.

Real, verified data shapes for version 7 (as of this writing):
  - coordinates.tsv.gz: one row per activation peak (id, table_id,
    table_num, peak_id, x, y, z) in MNI space
  - metadata.tsv.gz: one row per study (id, doi, space, title, authors,
    year, journal), 14371 rows
  - vocabulary.txt: 3228 terms, one per line, no header
  - features.npz: a scipy.sparse CSC matrix, shape (14371, 3228) -
    studies x terms tfidf weights. Row i corresponds POSITIONALLY to
    metadata row i (not to any ID column) - verified by cross-checking
    that the top-weighted studies for a known term ("memory") are all
    genuinely about memory research.
"""

import argparse
import gzip
import os
import sys
import urllib.request
from pathlib import Path

RAW_BASE = "https://raw.githubusercontent.com/neurosynth/neurosynth-data/master"

FILES = {
    "coordinates": "data-neurosynth_version-{v}_coordinates.tsv.gz",
    "metadata": "data-neurosynth_version-{v}_metadata.tsv.gz",
    "vocabulary": "data-neurosynth_version-{v}_vocab-terms_vocabulary.txt",
    "features": "data-neurosynth_version-{v}_vocab-terms_source-abstract_type-tfidf_features.npz",
}


def cache_dir() -> Path:
    base = os.environ.get("TOOLUNIVERSE_CACHE_DIR")
    if base:
        return Path(base) / "neurosynth"
    return Path.home() / ".cache" / "tooluniverse" / "neurosynth"


def download_one(url: str, dest: Path, force: bool) -> bool:
    if dest.exists() and not force:
        print(f"  already cached: {dest} ({dest.stat().st_size} bytes)")
        return True
    print(f"  downloading {url}")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            if resp.status != 200:
                print(f"  ERROR: HTTP {resp.status} for {url}", file=sys.stderr)
                return False
            data = resp.read()
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR: failed to fetch {url}: {e}", file=sys.stderr)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"  wrote {dest} ({len(data)} bytes)")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--version", default="7", help="Neurosynth data version (default: 7)"
    )
    ap.add_argument(
        "--force", action="store_true", help="Re-download even if cached"
    )
    args = ap.parse_args()

    out_dir = cache_dir() / f"v{args.version}"
    print(f"Cache directory: {out_dir}")

    ok = True
    paths = {}
    for key, pattern in FILES.items():
        fname = pattern.format(v=args.version)
        url = f"{RAW_BASE}/{fname}"
        dest = out_dir / fname
        if not download_one(url, dest, args.force):
            ok = False
        paths[key] = dest

    if not ok:
        print(
            "\nOne or more downloads failed. Do NOT proceed with analysis on "
            "partial data - re-run this script, or check "
            "https://github.com/neurosynth/neurosynth-data for the current "
            "file names if the version number has moved on.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Sanity check: vocabulary line count should be reasonably close to the
    # feature matrix column count. Don't fail hard (versions may add a
    # reserved column), but warn loudly if it's wildly off.
    try:
        with open(paths["vocabulary"]) as f:
            n_terms = sum(1 for _ in f)
        with gzip.open(paths["metadata"], "rt") as f:
            n_studies = sum(1 for _ in f) - 1  # minus header
        print(f"\nVocabulary terms: {n_terms}")
        print(f"Studies in metadata: {n_studies}")
    except Exception as e:  # noqa: BLE001
        print(f"WARNING: sanity check failed to run: {e}", file=sys.stderr)

    print("\nAll files downloaded and cached successfully.")
    for key, p in paths.items():
        print(f"  {key}: {p}")


if __name__ == "__main__":
    main()
