#!/usr/bin/env python3
"""
Find studies most strongly associated with a cognitive/neuroscience term,
and (optionally) their reported activation coordinates.

This is "forward inference lite": which published studies have the highest
tfidf weight for this term in their abstract, and where did they report
activation. It does NOT compute statistical significance - for "which
brain regions are reliably associated with this term across the whole
corpus", that requires aggregating coordinates across many studies and is
better suited to decode_coordinate.py's reverse-direction logic applied at
scale, or the real neurosynth/NiMARE package's dedicated meta-analysis
routines.

Usage:
    python3 search_by_term.py "working memory" --top 10
    python3 search_by_term.py "language" --top 5 --with-coordinates
"""

import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _neurosynth_data import load_all  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("term", help="Term to search for (must match the vocabulary exactly, case-sensitive; e.g. 'memory', 'working memory', 'language')")
    ap.add_argument("--top", type=int, default=10, help="Number of top-weighted studies to return (default 10)")
    ap.add_argument("--version", default="7", help="Neurosynth data version (default 7)")
    ap.add_argument("--with-coordinates", action="store_true", help="Include each study's reported activation coordinates")
    args = ap.parse_args()

    coords, meta, vocab, matrix = load_all(args.version)

    if args.term not in vocab:
        # Fuzzy suggestion, not a guess at the answer - just help find the right term
        # Substring matches first ("lang" -> "language"), then close spellings
        # ("hipocampus" -> "hippocampus"), which substring matching cannot find.
        needle = args.term.lower()
        candidates = [v for v in vocab if needle in v.lower()][:15]
        if not candidates:
            candidates = difflib.get_close_matches(needle, vocab, n=5, cutoff=0.75)
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": f"Term '{args.term}' not found in the {len(vocab)}-term vocabulary.",
                    "did_you_mean": candidates,
                },
                indent=2,
            )
        )
        sys.exit(1)

    term_idx = vocab.index(args.term)
    weights = matrix[:, term_idx].toarray().ravel()

    if (weights > 0).sum() == 0:
        print(
            json.dumps(
                {
                    "status": "success",
                    "term": args.term,
                    "studies": [],
                    "note": "Term exists in vocabulary but has zero weight across all studies in this version's matrix.",
                },
                indent=2,
            )
        )
        return

    top_n = min(args.top, len(weights))
    top_idx = weights.argsort()[::-1][:top_n]

    studies = []
    for i in top_idx:
        row = meta.iloc[i]
        study_id = row["id"]
        entry = {
            "study_id": int(study_id) if str(study_id).isdigit() else str(study_id),
            "title": row.get("title", ""),
            "authors": row.get("authors", ""),
            "year": int(row["year"]) if not str(row.get("year", "")).strip() == "" else None,
            "journal": row.get("journal", ""),
            "term_weight": float(weights[i]),
        }
        if args.with_coordinates:
            study_coords = coords[coords["id"] == study_id][["x", "y", "z"]]
            entry["coordinates_mni"] = study_coords.values.tolist()
        studies.append(entry)

    print(
        json.dumps(
            {
                "status": "success",
                "term": args.term,
                "total_studies_with_nonzero_weight": int((weights > 0).sum()),
                "studies": studies,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
