#!/usr/bin/env python3
"""
Meta-analytic "reverse inference": given an MNI coordinate, which cognitive
terms are statistically over-represented in studies that report activation
near that location, compared to the rest of the corpus?

Method (a simplified version of Neurosynth's own reverse-inference test,
not a reimplementation of NiMARE's full pipeline):
  1. Find all studies with >=1 reported peak within `--radius` mm
     (Euclidean distance in MNI space) of the query coordinate.
  2. For each vocabulary term, treat a study as "term-positive" if its
     tfidf weight for that term is > 0.
  3. Two-proportion z-test: is the term-positive rate inside the
     near-coordinate study set significantly higher than in the rest of
     the corpus?
  4. Rank terms by z-score (descending). With ~3228 terms tested
     simultaneously, uncorrected p-values are NOT publication-grade -
     this script reports both raw and Benjamini-Hochberg FDR-corrected
     q-values and says so explicitly.

This is real computed statistics on the actual downloaded data - never
report a term association this script didn't actually compute.

Usage:
    python3 decode_coordinate.py 0 -52 26 --radius 6 --top 15
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _neurosynth_data import load_all  # noqa: E402


def benjamini_hochberg(pvals):
    """Return BH-adjusted q-values, same order as input."""
    import numpy as np

    pvals = np.asarray(pvals)
    n = len(pvals)
    order = np.argsort(pvals)
    ranked = pvals[order]
    q = ranked * n / (np.arange(n) + 1)
    # enforce monotonicity from the largest p-value down
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0, 1)
    out = np.empty(n)
    out[order] = q
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("x", type=float, help="MNI x coordinate")
    ap.add_argument("y", type=float, help="MNI y coordinate")
    ap.add_argument("z", type=float, help="MNI z coordinate")
    ap.add_argument("--radius", type=float, default=6.0, help="Search radius in mm (default 6.0)")
    ap.add_argument("--top", type=int, default=20, help="Number of top terms to return (default 20)")
    ap.add_argument("--min-studies", type=int, default=5, help="Minimum number of near-coordinate studies required to run the test (default 5)")
    ap.add_argument("--version", default="7", help="Neurosynth data version (default 7)")
    args = ap.parse_args()

    import numpy as np
    from scipy import stats

    coords, meta, vocab, matrix = load_all(args.version)

    query = np.array([args.x, args.y, args.z])
    all_xyz = coords[["x", "y", "z"]].to_numpy()
    dists = np.linalg.norm(all_xyz - query, axis=1)
    near_mask = dists <= args.radius
    near_study_ids = set(coords.loc[near_mask, "id"].tolist())

    if len(near_study_ids) < args.min_studies:
        print(
            json.dumps(
                {
                    "status": "error",
                    "error": (
                        f"Only {len(near_study_ids)} studies report a peak within "
                        f"{args.radius}mm of ({args.x}, {args.y}, {args.z}) - "
                        f"below --min-studies={args.min_studies}. Try a larger "
                        "--radius rather than trusting a statistically underpowered result."
                    ),
                    "n_near_studies": len(near_study_ids),
                },
                indent=2,
            )
        )
        sys.exit(1)

    # Map study IDs to positional row indices in meta/matrix (they're aligned)
    id_to_pos = {sid: i for i, sid in enumerate(meta["id"].tolist())}
    near_positions = np.array(
        sorted(id_to_pos[sid] for sid in near_study_ids if sid in id_to_pos)
    )

    n_total = matrix.shape[0]
    n_near = len(near_positions)
    n_far = n_total - n_near

    dense_presence = (matrix > 0).astype(np.int8)  # sparse-safe boolean-ish

    results = []
    for term_idx, term in enumerate(vocab):
        col = dense_presence[:, term_idx].toarray().ravel()
        near_pos_count = int(col[near_positions].sum())
        total_pos_count = int(col.sum())
        far_pos_count = total_pos_count - near_pos_count

        p_near = near_pos_count / n_near
        p_far = far_pos_count / n_far if n_far > 0 else 0.0

        if near_pos_count == 0 and far_pos_count == 0:
            continue

        p_pool = total_pos_count / n_total
        se = (p_pool * (1 - p_pool) * (1 / n_near + 1 / n_far)) ** 0.5 if n_far > 0 else 0.0
        z = (p_near - p_far) / se if se > 0 else 0.0
        p_value = 2 * (1 - stats.norm.cdf(abs(z))) if se > 0 else 1.0

        results.append(
            {
                "term": term,
                "z_score": float(z),
                "p_value": float(p_value),
                "n_near_studies_with_term": near_pos_count,
                "n_near_studies_total": n_near,
                "rate_near": float(p_near),
                "rate_rest_of_corpus": float(p_far),
            }
        )

    if not results:
        print(json.dumps({"status": "error", "error": "No terms had any presence in near or far study sets - this should not happen with real data."}, indent=2))
        sys.exit(1)

    pvals = np.array([r["p_value"] for r in results])
    qvals = benjamini_hochberg(pvals)
    for r, q in zip(results, qvals):
        r["fdr_q_value"] = float(q)

    results.sort(key=lambda r: r["z_score"], reverse=True)
    top = results[: args.top]

    print(
        json.dumps(
            {
                "status": "success",
                "query": {"x": args.x, "y": args.y, "z": args.z, "radius_mm": args.radius},
                "n_studies_near_coordinate": n_near,
                "n_studies_rest_of_corpus": n_far,
                "caveat": (
                    f"{len(results)} terms were tested simultaneously; p_value is "
                    "uncorrected and will produce false positives at this scale - use "
                    "fdr_q_value (Benjamini-Hochberg) for anything resembling a "
                    "publication-grade claim, and note this is real-only positive/negative "
                    "presence testing, not a full activation-likelihood-estimation model."
                ),
                "top_terms": top,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
