"""Download the released query set and relevance judgments.

The generated queries and the graded judgments are published as a release asset rather
than committed, because together they are far larger than belongs in a git history.
This script fetches and unpacks them into ./data, so the benchmark can be re-scored
without re-running the generation and judging steps (which cost API calls).

Steps 1, 2 and 4 of the pipeline regenerate these files from scratch if you would
rather not trust the release; the corpus snapshot is always rebuilt locally by
build_corpus.py, since it must match the catalogue you are measuring.

Usage:
    python download_data.py
    python download_data.py --url <alternative url>
"""

import argparse
import hashlib
import sys
import tarfile
import urllib.request
from pathlib import Path

import common as C

DEFAULT_URL = (
    "https://github.com/mims-harvard/ToolUniverse/releases/download/"
    "benchmark-data-v1/tool_finder_benchmark_data.tar.gz"
)
# sha256 of the released archive. If you publish a rebuilt archive, update this;
# gzip output is not byte-reproducible, so a re-tar of identical data changes the hash.
EXPECTED_SHA256 = "a7cb01ea9f64087fda34effecb0bfa169f1b4fe8964a792073d1d9a2c1189b6c"

MEMBERS = ("queries.jsonl", "qrels.tsv")

# The judgments in this archive were pooled and graded against the catalogue at this
# commit. Scoring them against a different catalogue is not a like-for-like comparison:
# tools added since were never in the pool and so score as irrelevant, and tools whose
# description changed are no longer the documents that were judged. See the README.
JUDGED_AT_COMMIT = "e2520a9610c9b8a54aed42837929cca7f4659590"


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def safe_extract(tar, dest: Path):
    """Extract only regular files, and only inside dest."""
    dest = dest.resolve()
    for member in tar.getmembers():
        if not member.isfile():
            continue
        target = (dest / Path(member.name).name).resolve()
        if not str(target).startswith(str(dest)):
            raise RuntimeError(f"refusing to extract outside {dest}: {member.name}")
        member.name = Path(member.name).name
        try:
            # "data" rejects anything but regular files and their contents. It became
            # available in 3.11.4 and is the default from 3.14; passing it explicitly
            # keeps the behavior identical across versions instead of shifting under us.
            tar.extract(member, dest, filter="data")
        except TypeError:
            tar.extract(member, dest)  # Python < 3.11.4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--force", action="store_true", help="re-download even if files exist")
    args = ap.parse_args()

    present = [m for m in MEMBERS if (C.DATA_DIR / m).exists()]
    if len(present) == len(MEMBERS) and not args.force:
        C.log(f"Already present in {C.DATA_DIR}: {', '.join(MEMBERS)} (use --force to refetch)")
        return

    archive = C.DATA_DIR / "tool_finder_benchmark_data.tar.gz"
    C.log(f"Downloading {args.url}")
    try:
        urllib.request.urlretrieve(args.url, archive)
    except Exception as e:  # noqa: BLE001
        C.log(f"Download failed: {e}")
        C.log("The release asset may not be published yet; regenerate the data with "
              "build_corpus.py, generate_queries.py, run_systems.py and build_qrels.py.")
        sys.exit(1)

    if EXPECTED_SHA256:
        got = sha256(archive)
        if got != EXPECTED_SHA256:
            archive.unlink(missing_ok=True)
            raise SystemExit(f"checksum mismatch: expected {EXPECTED_SHA256}, got {got}")
        C.log("Checksum verified.")

    with tarfile.open(archive, "r:gz") as tar:
        safe_extract(tar, C.DATA_DIR)
    archive.unlink(missing_ok=True)

    for m in MEMBERS:
        p = C.DATA_DIR / m
        C.log(f"  {m}: {'ok' if p.exists() else 'MISSING'}"
              + (f" ({p.stat().st_size / 1e6:.1f} MB)" if p.exists() else ""))
    C.log(f"Data ready in {C.DATA_DIR}")
    C.log(f"\nThese judgments were graded against catalogue commit {JUDGED_AT_COMMIT[:10]}. "
          "Pin your ToolUniverse checkout to it before scoring, or re-judge the new "
          "candidates with BENCH_JUDGE_INCREMENTAL=1 python build_qrels.py")


if __name__ == "__main__":
    main()
