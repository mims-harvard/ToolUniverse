#!/usr/bin/env python3
"""Detect benchmark-specific content that has leaked into skill files.

The harness must drive GENERAL improvements, not dataset-specific answer
encoding. This script scans skills for signs of overfitting:
  - Benchmark names (BixBench, bix-N question IDs)
  - Dataset-specific capsule IDs / file names that only exist in one dataset
  - Numeric values suspiciously specific to a single question's ground truth

Run this before accepting a skill edit from devtu-optimize-skills.

Usage:
    python check_memorization.py skills/tooluniverse-*/SKILL.md
    python check_memorization.py --all   # check all tooluniverse-* skills
    python check_memorization.py --strict skills/path/to/skill/SKILL.md
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Patterns that suggest dataset-specific content. Organized by severity.
HARD_PATTERNS = [
    (re.compile(r"\bbix-\d+(?:-q\d+)?\b", re.IGNORECASE), "bix-N question ID"),
    (re.compile(r"\bBixBench\b", re.IGNORECASE), "benchmark name 'BixBench'"),
    (re.compile(r"\bBCG-CORONA\b", re.IGNORECASE), "dataset name 'BCG-CORONA'"),
    (re.compile(r"CapsuleFolder-[a-f0-9-]+"), "capsule UUID path"),
    (re.compile(r"TASK\d{3}_[A-Z-]+"), "TASK-prefixed dataset filename"),
    (re.compile(r"lab-bench[_-]?task"), "lab-bench task name"),
]

# Known benchmark-side GT issues (recorded here only to keep the harness honest
# about what it can/can't improve; NOT to encode answers into skills).
# When reporting scores, these can legitimately be excluded from the denominator.
KNOWN_GT_ISSUES_DOCS = """
Verified-mislabeled or unreproducible BixBench GTs (as of 2026-04-24):
- bix-53-q4: question is 'how many pathways' (integer), GT is '4.25E-04' (p-value)
- bix-31-q4: authoritative script `run_pc_vs_noncoding_ttest.py` gives p=0.481544, GT 0.65 unreproducible
- bix-38-q6: PhyKIT and BioPython independent computations give 1.904, GT 2.178 unreproducible
- bix-9-q3: question wording allows multiple valid answers
- bix-57-q1, bix-1-q1, bix-13-q1, bix-13-q3, bix-13-q4, bix-27-q5, bix-31-q3,
  bix-5-q1, bix-5-q4, bix-52-q3: verified discrepancies
"""


# Soft patterns — flag but don't fail by default
SOFT_PATTERNS = [
    # Specific filenames that appear only in one capsule
    (re.compile(r"BatchCorrectedReadCounts_Zenodo"), "specific dataset filename"),
    (re.compile(r"GeneMetaInfo_Zenodo"), "specific dataset filename"),
    (re.compile(r"Sample_annotated_Zenodo"), "specific dataset filename"),
    # Specific gene names referenced as *the answer* (not as examples)
    (re.compile(r"\bFAM138A\b"), "specific gene (possible GT-answer reference)"),
    (re.compile(r"\bJBX\d+\b"), "specific strain identifier"),
    # Exact numeric ground truths from known questions
    (re.compile(r"\bF\s*[=≈]\s*0\.7[67]\b"), "specific F-statistic (bix-36-q1 GT)"),
    (re.compile(r"\b4,?550\b"), "specific count (bix-14-q3 GT)"),
    (re.compile(r"\b2\.178\b"), "specific median (bix-38-q6 GT)"),
]


def scan_file(path: Path, strict: bool = False):
    """Scan a single file for memorization signals. Returns list of hits."""
    if not path.exists():
        return [("error", f"file not found: {path}")]

    # Skip test files — they are allowed to reference benchmarks
    if "test_" in path.name or path.name.startswith("test_"):
        return []

    text = path.read_text(errors="replace")
    hits = []

    for rx, label in HARD_PATTERNS:
        for m in rx.finditer(text):
            line_no = text[: m.start()].count("\n") + 1
            ctx = text.splitlines()[line_no - 1][:120] if line_no <= len(text.splitlines()) else ""
            hits.append(("hard", f"{path.relative_to(REPO_ROOT)}:{line_no}: {label}: {m.group()}  | {ctx}"))

    if strict:
        for rx, label in SOFT_PATTERNS:
            for m in rx.finditer(text):
                line_no = text[: m.start()].count("\n") + 1
                ctx = text.splitlines()[line_no - 1][:120] if line_no <= len(text.splitlines()) else ""
                hits.append(("soft", f"{path.relative_to(REPO_ROOT)}:{line_no}: {label}: {m.group()}  | {ctx}"))

    return hits


def main():
    parser = argparse.ArgumentParser(description="Detect memorization in skill files")
    parser.add_argument("paths", nargs="*", help="Paths to SKILL.md or similar files")
    parser.add_argument("--all", action="store_true", help="Scan all tooluniverse-*/ skill files")
    parser.add_argument("--strict", action="store_true", help="Include soft patterns (specific gene names, numeric GTs)")
    args = parser.parse_args()

    paths = []
    if args.all:
        for skill_dir in (REPO_ROOT / "skills").glob("tooluniverse-*"):
            for p in skill_dir.rglob("*.md"):
                if "references/" in str(p) or p.name in ("SKILL.md", "QUICK_START.md"):
                    paths.append(p)
            for p in skill_dir.glob("scripts/*.py"):
                paths.append(p)
    else:
        paths = [Path(p) for p in args.paths]

    if not paths:
        parser.print_help()
        sys.exit(1)

    all_hard = []
    all_soft = []
    for p in paths:
        for severity, msg in scan_file(p, strict=args.strict):
            if severity == "hard":
                all_hard.append(msg)
            elif severity == "soft":
                all_soft.append(msg)
            else:
                print(f"[error] {msg}", file=sys.stderr)

    if all_hard:
        print("=" * 60)
        print(f"HARD FAILURES ({len(all_hard)}):")
        print("=" * 60)
        for h in all_hard:
            print(f"  {h}")

    if all_soft and args.strict:
        print()
        print("=" * 60)
        print(f"SOFT WARNINGS ({len(all_soft)}):")
        print("=" * 60)
        for s in all_soft:
            print(f"  {s}")

    print()
    print(f"Scanned {len(paths)} files")
    print(f"Hard failures: {len(all_hard)}")
    if args.strict:
        print(f"Soft warnings: {len(all_soft)}")

    # Exit non-zero if hard failures found
    if all_hard:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
