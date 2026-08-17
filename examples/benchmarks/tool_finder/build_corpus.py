"""Step 1 - build the corpus snapshot.

Loads the full ToolUniverse catalogue and records the retrieval pool, the per-tool
document text (identical for every embedding system), the test examples used to seed
queries, the source file (an application-area proxy), and a held-out flag derived from
the git date at which each tool file was added.

The held-out flag is what makes the fine-tuning comparison leakage-free: a tool whose
file was added after the fine-tuning cutoff cannot have been in the training data.

Output: data/corpus_snapshot.json

Usage:
    python build_corpus.py
"""

import subprocess

import common as C


def git_add_date(path):
    """First commit date (ISO 8601) that added ``path``, or None if unknown."""
    try:
        out = (
            subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(C.REPO),
                    "log",
                    "--diff-filter=A",
                    "--follow",
                    "--format=%aI",
                    "--",
                    path,
                ],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
            .splitlines()
        )
        return out[-1] if out else None
    except Exception:
        return None


def main():
    C.log(f"Reading catalogue from {C.REPO}")
    tu = C.get_tooluniverse()
    try:
        commit = (
            subprocess.check_output(["git", "-C", str(C.REPO), "rev-parse", "HEAD"])
            .decode()
            .strip()
        )
    except Exception:
        commit = "unknown"

    corpus = C.build_corpus(tu)
    names = corpus["tool_names"]
    meta = corpus["meta"]
    C.log(f"Retrieval pool: {len(names)} tools")

    # A tool is held out when its source file entered the repository after the cutoff.
    file_dates = {}
    for fp in sorted({m["source_file"] for m in meta.values()}):
        file_dates[fp] = None if fp == "unknown" else git_add_date(
            f"src/tooluniverse/data/{fp}.json"
        )

    n_heldout = 0
    for m in meta.values():
        d = file_dates.get(m["source_file"])
        m["added_date"] = d
        m["heldout"] = bool(d is not None and d[:10] > C.HELDOUT_CUTOFF)
        n_heldout += m["heldout"]

    n_seed = sum(1 for m in meta.values() if m["test_examples"])
    snapshot = {
        "commit": commit,
        "n_tools_pool": len(names),
        "n_seed_tools": n_seed,
        "n_heldout_tools": n_heldout,
        "heldout_cutoff": C.HELDOUT_CUTOFF,
        "exclude_tools": C.EXCLUDE_TOOLS,
        "tool_names": names,
        "doc_texts": corpus["doc_texts"],
        "meta": meta,
        "file_add_dates": file_dates,
    }
    C.save_json(C.DATA_DIR / "corpus_snapshot.json", snapshot)
    C.log(
        f"commit={commit[:10]}  pool={len(names)}  seed_tools={n_seed}  held_out={n_heldout}"
    )
    C.log(f"Wrote {C.DATA_DIR / 'corpus_snapshot.json'}")


if __name__ == "__main__":
    main()
