"""Shared loading helpers for the Neurosynth analysis scripts.

Not a standalone CLI - imported by search_by_term.py and decode_coordinate.py.
"""

import sys
from pathlib import Path

from download_data import cache_dir, FILES  # noqa: E402


def _missing_data_message(version: str) -> str:
    return (
        f"Neurosynth data (version {version}) is not downloaded yet. Run:\n"
        f"  python3 scripts/download_data.py --version {version}\n"
        "before running any analysis. This skill never fabricates study "
        "results or term associations - it only reports what's actually in "
        "the downloaded database."
    )


def load_all(version: str = "7"):
    """Load coordinates, metadata, vocabulary, and the tfidf feature matrix.

    Returns (coords_df, meta_df, vocab_list, feature_matrix). Raises
    SystemExit with a clear message if the data hasn't been downloaded -
    never silently returns empty/fake data.
    """
    import gzip
    import pandas as pd
    import scipy.sparse as sp

    out_dir = cache_dir() / f"v{version}"
    paths = {key: out_dir / pattern.format(v=version) for key, pattern in FILES.items()}

    missing = [k for k, p in paths.items() if not p.exists()]
    if missing:
        print(_missing_data_message(version), file=sys.stderr)
        sys.exit(1)

    coords = pd.read_csv(paths["coordinates"], sep="\t")
    meta = pd.read_csv(paths["metadata"], sep="\t")
    with open(paths["vocabulary"], encoding="utf-8") as f:
        vocab = [line.rstrip("\n") for line in f if line.strip()]
    matrix = sp.load_npz(paths["features"])

    if matrix.shape[0] != len(meta):
        print(
            f"WARNING: feature matrix has {matrix.shape[0]} rows but "
            f"metadata has {len(meta)} rows - positional alignment between "
            "them (which this skill relies on) may be broken for this "
            "data version. Verify before trusting results.",
            file=sys.stderr,
        )
    if matrix.shape[1] != len(vocab):
        print(
            f"WARNING: feature matrix has {matrix.shape[1]} columns but "
            f"the vocabulary file has {len(vocab)} terms - term-index "
            "alignment (which this skill relies on) may be broken for this "
            "data version. Verify before trusting results.",
            file=sys.stderr,
        )

    return coords, meta, vocab, matrix
